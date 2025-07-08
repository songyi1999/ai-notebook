"""
Response Evaluation Service
Evaluates if LLM responses fully answer user questions and determines if follow-up actions are needed
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from enum import Enum

from ..dynamic_config import settings
from .ai_service_langchain import AIService

logger = logging.getLogger(__name__)

class ResponseCompleteness(Enum):
    """Response completeness levels"""
    COMPLETE = "complete"           # Fully answers the question
    PARTIALLY_COMPLETE = "partial"  # Partially answers, needs more info
    INCOMPLETE = "incomplete"       # Does not adequately answer
    REQUIRES_TOOLS = "requires_tools" # Needs tool calls for completion

class ResponseEvaluator:
    """Service to evaluate LLM response completeness and suggest follow-up actions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
    
    def evaluate_response(
        self, 
        user_question: str, 
        llm_response: str, 
        context_used: str = "",
        available_tools: List[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate if the LLM response fully answers the user's question
        
        Args:
            user_question: Original user question
            llm_response: LLM's response
            context_used: Context that was used to generate the response
            available_tools: List of available tools for follow-up
            
        Returns:
            Evaluation result with completeness, confidence, and suggested actions
        """
        if not self.ai_service.is_available():
            logger.warning("AI service not available for response evaluation")
            return self._fallback_evaluation()
        
        try:
            logger.info(f"🔍 开始评估回复质量...")
            logger.info(f"📝 用户问题: {user_question[:100]}...")
            logger.info(f"💬 AI回复长度: {len(llm_response)} 字符")
            logger.info(f"📚 使用的上下文: {context_used[:100]}..." if context_used else "📚 未使用上下文")
            
            # Perform the evaluation using LLM
            evaluation_result = self._llm_evaluate_response(
                user_question, llm_response, context_used
            )
            
            logger.info(f"📊 评估结果: {evaluation_result.get('completeness', 'unknown')} - 综合评分: {evaluation_result.get('overall_score', 0):.2f}")
            logger.info(f"🎯 缺失方面: {evaluation_result.get('missing_aspects', [])}")
            
            # Determine follow-up actions based on evaluation
            suggested_actions = self._determine_follow_up_actions(
                evaluation_result, user_question, llm_response, available_tools
            )
            
            if suggested_actions:
                logger.info(f"🔧 建议后续行动: {len(suggested_actions)} 个")
                for i, action in enumerate(suggested_actions, 1):
                    logger.info(f"   {i}. {action.get('type', 'unknown')} - {action.get('description', '')}")
            else:
                logger.info("✅ 回复质量满足要求，无需后续行动")
            
            # Combine results
            result = {
                **evaluation_result,
                "suggested_actions": suggested_actions,
                "requires_follow_up": len(suggested_actions) > 0
            }
            
            logger.info(f"🏁 评估完成: {result['completeness']} (confidence: {result['confidence']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Response evaluation failed: {e}")
            return self._fallback_evaluation()
    
    def _llm_evaluate_response(
        self, 
        user_question: str, 
        llm_response: str, 
        context_used: str
    ) -> Dict[str, Any]:
        """Use LLM to evaluate response completeness"""
        
        evaluation_prompt = f"""请评估以下AI回复是否完全回答了用户的问题。

用户问题：
{user_question}

AI回复：
{llm_response}

使用的上下文：
{context_used[:500] if context_used else "无"}

请从以下几个维度评估：
1. 完整性：回复是否完全回答了用户的问题？
2. 准确性：回复内容是否准确可靠？
3. 相关性：回复是否与问题直接相关？
4. 深度：回复是否提供了足够的细节？

请按以下JSON格式回复：
{{
    "completeness_score": 0.0-1.0的数值,
    "accuracy_score": 0.0-1.0的数值,
    "relevance_score": 0.0-1.0的数值,
    "depth_score": 0.0-1.0的数值,
    "overall_score": 0.0-1.0的数值,
    "completeness": "complete/partial/incomplete/requires_tools",
    "missing_aspects": ["缺失的方面1", "缺失的方面2"],
    "confidence": 0.0-1.0的数值,
    "reasoning": "评估理由的简短说明"
}}"""

        try:
            # Use direct chat to avoid recursive evaluation
            response = self.ai_service.direct_chat(evaluation_prompt)
            
            if not response or "answer" not in response:
                return self._fallback_evaluation()
            
            # Try to parse JSON response
            import json
            import re
            
            answer = response["answer"]
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if json_match:
                try:
                    evaluation_data = json.loads(json_match.group())
                    
                    # Validate and normalize the response
                    return self._normalize_evaluation_result(evaluation_data)
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse evaluation JSON")
            
            # Fallback to text analysis if JSON parsing fails
            return self._analyze_evaluation_text(answer)
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return self._fallback_evaluation()
    
    def _normalize_evaluation_result(self, evaluation_data: Dict) -> Dict[str, Any]:
        """Normalize and validate evaluation result"""
        
        # Default values
        result = {
            "completeness_score": 0.5,
            "accuracy_score": 0.5,
            "relevance_score": 0.5,
            "depth_score": 0.5,
            "overall_score": 0.5,
            "completeness": ResponseCompleteness.PARTIALLY_COMPLETE.value,
            "missing_aspects": [],
            "confidence": 0.5,
            "reasoning": "默认评估"
        }
        
        # Update with actual values, ensuring they're in valid ranges
        for key in ["completeness_score", "accuracy_score", "relevance_score", "depth_score", "overall_score", "confidence"]:
            if key in evaluation_data:
                try:
                    value = float(evaluation_data[key])
                    result[key] = max(0.0, min(1.0, value))
                except (ValueError, TypeError):
                    pass
        
        # Update completeness enum
        if "completeness" in evaluation_data:
            completeness_value = evaluation_data["completeness"]
            if completeness_value in [e.value for e in ResponseCompleteness]:
                result["completeness"] = completeness_value
        
        # Update lists and strings
        if "missing_aspects" in evaluation_data and isinstance(evaluation_data["missing_aspects"], list):
            result["missing_aspects"] = evaluation_data["missing_aspects"][:5]  # Limit to 5 items
        
        if "reasoning" in evaluation_data and isinstance(evaluation_data["reasoning"], str):
            result["reasoning"] = evaluation_data["reasoning"][:200]  # Limit length
        
        return result
    
    def _analyze_evaluation_text(self, evaluation_text: str) -> Dict[str, Any]:
        """Fallback text analysis for evaluation"""
        
        # Simple keyword-based analysis
        positive_keywords = ["完整", "准确", "详细", "全面", "充分", "complete", "accurate", "detailed", "comprehensive"]
        negative_keywords = ["不完整", "缺少", "不足", "incomplete", "missing", "insufficient", "lacking"]
        
        positive_score = sum(1 for kw in positive_keywords if kw in evaluation_text)
        negative_score = sum(1 for kw in negative_keywords if kw in evaluation_text)
        
        # Calculate basic score
        if positive_score > negative_score:
            overall_score = 0.7
            completeness = ResponseCompleteness.COMPLETE.value
        elif negative_score > positive_score:
            overall_score = 0.3
            completeness = ResponseCompleteness.INCOMPLETE.value
        else:
            overall_score = 0.5
            completeness = ResponseCompleteness.PARTIALLY_COMPLETE.value
        
        return {
            "completeness_score": overall_score,
            "accuracy_score": overall_score,
            "relevance_score": overall_score,
            "depth_score": overall_score,
            "overall_score": overall_score,
            "completeness": completeness,
            "missing_aspects": [],
            "confidence": 0.6,
            "reasoning": "基于关键词的文本分析"
        }
    
    def _determine_follow_up_actions(
        self, 
        evaluation_result: Dict, 
        user_question: str, 
        llm_response: str,
        available_tools: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Determine what follow-up actions are needed"""
        
        actions = []
        completeness = evaluation_result.get("completeness", "partial")
        overall_score = evaluation_result.get("overall_score", 0.5)
        missing_aspects = evaluation_result.get("missing_aspects", [])
        
        # If response is complete and high quality, no follow-up needed
        if completeness == ResponseCompleteness.COMPLETE.value and overall_score > 0.7:
            return actions
        
        # Determine specific actions based on missing aspects and available tools
        if available_tools is None:
            available_tools = ["search", "mcp_tools"]
        
        # Knowledge search action
        if completeness in [ResponseCompleteness.INCOMPLETE.value, ResponseCompleteness.PARTIALLY_COMPLETE.value]:
            if overall_score < 0.6:
                actions.append({
                    "type": "knowledge_search",
                    "priority": "high",
                    "description": "进行更深入的知识库搜索以获取更完整的信息",
                    "search_query": self._generate_follow_up_search_query(user_question, missing_aspects)
                })
        
        # Tool usage action
        if completeness == ResponseCompleteness.REQUIRES_TOOLS.value and "mcp_tools" in available_tools:
            actions.append({
                "type": "tool_usage",
                "priority": "medium", 
                "description": "使用专门工具获取更准确的信息",
                "suggested_tools": self._suggest_relevant_tools(user_question, missing_aspects)
            })
        
        # Content expansion action
        if overall_score < 0.5 or len(missing_aspects) > 2:
            actions.append({
                "type": "content_expansion",
                "priority": "medium",
                "description": "扩展回答内容，提供更多相关细节",
                "expansion_areas": missing_aspects[:3]
            })
        
        return actions
    
    def _generate_follow_up_search_query(self, original_question: str, missing_aspects: List[str]) -> str:
        """Generate a refined search query for follow-up"""
        
        if missing_aspects:
            # Combine original question with missing aspects
            aspects_text = " ".join(missing_aspects)
            return f"{original_question} {aspects_text}"
        else:
            # Add more specific terms to the original question
            specific_terms = ["详细", "具体", "实现", "方法", "步骤"]
            return f"{original_question} {''.join(specific_terms[:2])}"
    
    def _suggest_relevant_tools(self, question: str, missing_aspects: List[str]) -> List[str]:
        """Suggest relevant tools based on question and missing aspects"""
        
        suggested_tools = []
        
        # Simple keyword-based tool suggestion
        if any(term in question.lower() for term in ["文件", "搜索", "查找", "file", "search"]):
            suggested_tools.append("file_search")
        
        if any(term in question.lower() for term in ["链接", "关系", "连接", "link", "relationship"]):
            suggested_tools.append("link_analysis")
        
        if any(term in question.lower() for term in ["标签", "分类", "tag", "category"]):
            suggested_tools.append("tag_management")
        
        # Default to general search if no specific tools identified
        if not suggested_tools:
            suggested_tools.append("general_search")
        
        return suggested_tools
    
    def _fallback_evaluation(self) -> Dict[str, Any]:
        """Fallback evaluation when AI service is unavailable"""
        return {
            "completeness_score": 0.5,
            "accuracy_score": 0.5,
            "relevance_score": 0.5,
            "depth_score": 0.5,
            "overall_score": 0.5,
            "completeness": ResponseCompleteness.PARTIALLY_COMPLETE.value,
            "missing_aspects": [],
            "confidence": 0.3,
            "reasoning": "AI服务不可用，使用默认评估",
            "suggested_actions": [],
            "requires_follow_up": False
        }
    
    def should_perform_follow_up(self, evaluation_result: Dict, confidence_threshold: float = 0.6) -> bool:
        """Determine if follow-up actions should be performed automatically"""
        
        overall_score = evaluation_result.get("overall_score", 0.5)
        confidence = evaluation_result.get("confidence", 0.5)
        completeness = evaluation_result.get("completeness", "partial")
        
        # Perform follow-up if:
        # 1. Low overall score and high confidence in evaluation
        # 2. Incomplete response with moderate confidence
        # 3. Specifically requires tools
        
        if overall_score < 0.5 and confidence > confidence_threshold:
            return True
        
        if completeness == ResponseCompleteness.INCOMPLETE.value and confidence > 0.4:
            return True
        
        if completeness == ResponseCompleteness.REQUIRES_TOOLS.value:
            return True
        
        return False