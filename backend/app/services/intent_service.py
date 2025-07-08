"""
Intent Recognition Service for AI Chat
Determines whether a query requires knowledge base search or can be answered directly
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Query intent types"""
    KNOWLEDGE_SEARCH = "knowledge_search"  # Requires knowledge base search
    DIRECT_CHAT = "direct_chat"           # Can be answered directly
    MIXED = "mixed"                       # May benefit from both

class IntentService:
    """Intent recognition service to optimize chat response routing"""
    
    def __init__(self):
        # Knowledge-seeking keywords - Chinese and English with weights
        self.knowledge_keywords = {
            # High-weight query words
            "什么": 0.8, "如何": 0.9, "怎么": 0.9, "为什么": 0.8, "哪里": 0.7, "哪个": 0.6, "什么时候": 0.7, "谁": 0.6, "多少": 0.6,
            "what": 0.8, "how": 0.9, "why": 0.8, "where": 0.7, "which": 0.6, "when": 0.7, "who": 0.6, "how much": 0.6, "how many": 0.6,
            # Information seeking
            "解释": 0.8, "说明": 0.8, "介绍": 0.7, "告诉我": 0.8, "帮我找": 0.9, "查找": 0.9, "搜索": 0.9, "详细": 0.6, "具体": 0.6,
            "说说": 0.8, "讲讲": 0.8, "谈谈": 0.7, "究竟": 0.8, "到底": 0.8, "会议": 0.9, "开会": 0.9,
            "explain": 0.8, "describe": 0.8, "tell me": 0.8, "help me find": 0.9, "search": 0.9, "details": 0.6, "specific": 0.6,
            # Documentation references
            "文档": 0.8, "资料": 0.8, "笔记": 0.9, "记录": 0.7, "内容": 0.5, "文件": 0.8, "资源": 0.7,
            "document": 0.8, "note": 0.9, "record": 0.7, "content": 0.5, "file": 0.8, "resource": 0.7,
            # Technical terms
            "实现": 0.8, "代码": 0.8, "方法": 0.7, "步骤": 0.7, "流程": 0.7, "配置": 0.8, "设置": 0.7, "教程": 0.8,
            "implement": 0.8, "code": 0.8, "method": 0.7, "step": 0.7, "process": 0.7, "config": 0.8, "setup": 0.7, "tutorial": 0.8,
            # Context-specific terms
            "定义": 0.8, "原理": 0.8, "概念": 0.8, "理论": 0.7, "案例": 0.7, "例子": 0.7, "示例": 0.7,
            "definition": 0.8, "principle": 0.8, "concept": 0.8, "theory": 0.7, "case": 0.7, "example": 0.7,
            # Research and analysis
            "分析": 0.7, "比较": 0.7, "对比": 0.7, "总结": 0.7, "归纳": 0.7,
            "analysis": 0.7, "compare": 0.7, "summarize": 0.7, "conclude": 0.7
        }
        
        # Direct chat keywords with weights
        self.direct_chat_keywords = {
            # Greetings
            "你好": 0.9, "您好": 0.9, "早上好": 0.9, "下午好": 0.9, "晚上好": 0.9, "hi": 0.9, "hello": 0.9, "good morning": 0.9, "good afternoon": 0.9, "good evening": 0.9,
            # Opinions and feelings
            "觉得": 0.8, "认为": 0.8, "感觉": 0.8, "想": 0.6, "希望": 0.7, "喜欢": 0.7, "不喜欢": 0.7, "同意": 0.7, "不同意": 0.7,
            "think": 0.8, "feel": 0.8, "like": 0.7, "dislike": 0.7, "agree": 0.7, "disagree": 0.7, "opinion": 0.8, "believe": 0.8,
            # General conversation
            "聊天": 0.9, "谈话": 0.8, "讨论": 0.6, "交流": 0.6, "分享": 0.6, "chat": 0.9, "talk": 0.8, "discuss": 0.6, "share": 0.6,
            # Creative tasks
            "创造": 0.8, "创作": 0.8, "写": 0.7, "编写": 0.7, "生成": 0.7, "制作": 0.7, "设计": 0.7,
            "create": 0.8, "write": 0.7, "generate": 0.7, "make": 0.7, "design": 0.7, "compose": 0.7
        }
        
        # Question patterns that usually need knowledge base
        self.knowledge_patterns = [
            r".*在.*哪里.*",        # Where is X in Y
            r".*怎么.*实现.*",       # How to implement X
            r".*如何.*配置.*",       # How to configure X
            r".*什么是.*",          # What is X
            r".*how\s+to.*",       # How to do X
            r".*what\s+is.*",      # What is X
            r".*where\s+is.*",     # Where is X
            r".*explain.*",        # Explain X
            r".*告诉我.*关于.*",     # Tell me about X
            r".*有.*教程.*吗",      # Is there a tutorial for X
            r".*支持.*吗",          # Does it support X
        ]
        
        # Direct chat patterns
        self.direct_patterns = [
            r"^你好.*",             # Greetings
            r"^hi.*",
            r"^hello.*",
            r".*你觉得.*",          # Opinion questions
            r".*你认为.*",
            r".*what.*think.*",
            r".*帮我.*写.*",        # Creative writing
            r".*help.*write.*",
            r".*生成.*",            # Generate content
            r".*generate.*",
            r".*翻译.*",            # Translation
            r".*translate.*",
        ]
    
    def analyze_intent(self, query: str) -> Tuple[QueryIntent, float, Dict]:
        """
        Analyze query intent and return confidence score
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (intent, confidence_score, details)
        """
        if not query or not query.strip():
            return QueryIntent.DIRECT_CHAT, 0.5, {"reason": "empty_query"}
        
        query_lower = query.lower().strip()
        
        # Calculate scores for different intent types
        knowledge_score = self._calculate_knowledge_score(query_lower)
        direct_score = self._calculate_direct_score(query_lower)
        
        # Determine intent based on scores
        intent, confidence = self._determine_intent(knowledge_score, direct_score)
        
        details = {
            "knowledge_score": knowledge_score,
            "direct_score": direct_score,
            "query_length": len(query),
            "has_question_mark": "?" in query or "？" in query,
            "keywords_found": self._extract_keywords(query_lower)
        }
        
        logger.info(f"Intent analysis: {intent.value} (conf: {confidence:.2f}) - {query[:50]}...")
        logger.info(f"📊 Intent details: knowledge_score={details['knowledge_score']:.3f}, direct_score={details['direct_score']:.3f}")
        logger.info(f"🔍 Found keywords: {details['keywords_found'][:5]}")
        
        return intent, confidence, details
    
    def _calculate_knowledge_score(self, query: str) -> float:
        """Calculate knowledge-seeking score with weighted keywords"""
        score = 0.0
        
        # Check knowledge keywords with weights
        for kw, weight in self.knowledge_keywords.items():
            if kw in query:
                score += weight * 0.15  # Reduced individual impact
        
        # Check knowledge patterns with higher weight
        pattern_matches = sum(1 for pattern in self.knowledge_patterns 
                            if re.search(pattern, query))
        score += pattern_matches * 0.25
        
        # File/document references with context sensitivity
        doc_terms = ["文件", "文档", "笔记", "记录", "file", "document", "note", "record"]
        doc_matches = sum(1 for term in doc_terms if term in query)
        if doc_matches > 0:
            score += min(doc_matches * 0.2, 0.4)  # Cap at 0.4
        
        # Technical terms with enhanced detection
        technical_terms = ["代码", "配置", "设置", "API", "数据库", "算法", "框架", "函数", "变量", "类", "接口"]
        tech_matches = sum(1 for term in technical_terms if term in query)
        if tech_matches > 0:
            score += min(tech_matches * 0.15, 0.3)  # Cap at 0.3
        
        # Question structure with position sensitivity
        question_starters = ["什么", "如何", "怎么", "为什么", "哪里", "哪个", "什么时候", "谁", "说说", "讲讲", "谈谈",
                           "what", "how", "why", "where", "which", "when", "who", "tell", "talk about", "explain"]
        for starter in question_starters:
            if query.startswith(starter):
                score += 0.25
                logger.debug(f"🎯 Knowledge indicator found: starts with '{starter}', +0.25")
                break
        
        # Context length bonus (longer queries more likely to be knowledge-seeking)
        if len(query) > 20:
            score += 0.1
        if len(query) > 50:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_direct_score(self, query: str) -> float:
        """Calculate direct chat score with weighted keywords"""
        score = 0.0
        
        # Check direct chat keywords with weights
        for kw, weight in self.direct_chat_keywords.items():
            if kw in query:
                score += weight * 0.15  # Reduced individual impact
        
        # Check direct patterns with higher weight
        pattern_matches = sum(1 for pattern in self.direct_patterns 
                            if re.search(pattern, query))
        score += pattern_matches * 0.3
        
        # Greeting detection with position sensitivity
        greeting_terms = ["你好", "您好", "hi", "hello", "早上好", "下午好", "晚上好"]
        for greeting in greeting_terms:
            if query.startswith(greeting):
                score += 0.4
                break
        
        # Opinion/feeling expressions
        opinion_terms = ["觉得", "认为", "感觉", "想法", "think", "feel", "opinion", "believe"]
        opinion_matches = sum(1 for term in opinion_terms if term in query)
        if opinion_matches > 0:
            score += min(opinion_matches * 0.2, 0.3)
        
        # Creative tasks detection
        creative_terms = ["写", "创作", "生成", "设计", "编写", "制作", "write", "create", "generate", "design", "compose"]
        creative_matches = sum(1 for term in creative_terms if term in query)
        if creative_matches > 0:
            score += min(creative_matches * 0.15, 0.25)
        
        # Short casual queries (but not questions)
        if len(query) < 20:
            question_indicators = ["什么", "如何", "怎么", "为什么", "哪里", "what", "how", "why", "where", "?", "？"]
            if not any(indicator in query for indicator in question_indicators):
                score += 0.2
        
        # Conversational indicators
        if any(word in query for word in ["聊天", "谈话", "chat", "talk", "谢谢", "thanks", "thank you"]):
            score += 0.3
        
        return min(score, 1.0)
    
    def _determine_intent(self, knowledge_score: float, direct_score: float) -> Tuple[QueryIntent, float]:
        """Determine final intent based on scores with enhanced logic"""
        
        # Very high confidence thresholds
        if knowledge_score >= 0.7 and knowledge_score > direct_score + 0.3:
            return QueryIntent.KNOWLEDGE_SEARCH, knowledge_score
        
        if direct_score >= 0.7 and direct_score > knowledge_score + 0.3:
            return QueryIntent.DIRECT_CHAT, direct_score
        
        # Moderate confidence thresholds
        if knowledge_score >= 0.5 and knowledge_score > direct_score + 0.15:
            return QueryIntent.KNOWLEDGE_SEARCH, knowledge_score
        
        if direct_score >= 0.5 and direct_score > knowledge_score + 0.15:
            return QueryIntent.DIRECT_CHAT, direct_score
        
        # Close scores - analyze context more carefully
        score_diff = abs(knowledge_score - direct_score)
        if score_diff < 0.1:
            # Very ambiguous - use additional heuristics
            if knowledge_score > 0.3 or direct_score > 0.3:
                # If either score is decent, prefer mixed approach
                return QueryIntent.MIXED, (knowledge_score + direct_score) / 2
        
        # Mixed intent for moderate scores on both sides
        if knowledge_score > 0.3 and direct_score > 0.3:
            return QueryIntent.MIXED, (knowledge_score + direct_score) / 2
        
        # Default decision with slight preference for knowledge search
        # This ensures users get comprehensive answers when in doubt
        if knowledge_score >= direct_score - 0.05:  # Small tolerance for knowledge search
            return QueryIntent.KNOWLEDGE_SEARCH, max(knowledge_score, 0.3)
        else:
            return QueryIntent.DIRECT_CHAT, direct_score
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from query"""
        found_keywords = []
        
        # Knowledge keywords
        for kw in self.knowledge_keywords:
            if kw in query:
                found_keywords.append(f"knowledge:{kw}")
        
        # Direct chat keywords
        for kw in self.direct_chat_keywords:
            if kw in query:
                found_keywords.append(f"direct:{kw}")
        
        return found_keywords[:5]  # Limit to top 5 keywords
    
    def should_use_knowledge_base(self, query: str, confidence_threshold: float = 0.4) -> bool:
        """
        Quick method to determine if knowledge base should be used
        
        Args:
            query: User query
            confidence_threshold: Minimum confidence for knowledge search
            
        Returns:
            True if knowledge base should be used
        """
        intent, confidence, _ = self.analyze_intent(query)
        
        # Always use knowledge base for KNOWLEDGE_SEARCH intent
        if intent == QueryIntent.KNOWLEDGE_SEARCH:
            return True
        
        # For MIXED intent, use knowledge base if confidence is high enough
        if intent == QueryIntent.MIXED and confidence >= confidence_threshold:
            return True
        
        # For DIRECT_CHAT, only use knowledge base if specifically requested
        if intent == QueryIntent.DIRECT_CHAT:
            # Check for explicit knowledge requests even in casual chat
            explicit_knowledge = any(word in query.lower() for word in 
                                   ["查找", "搜索", "找到", "search", "find", "lookup"])
            return explicit_knowledge
        
        return False