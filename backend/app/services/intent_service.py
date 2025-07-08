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
        # Knowledge-seeking keywords - Chinese and English
        self.knowledge_keywords = {
            # Query words
            "什么", "如何", "怎么", "为什么", "哪里", "哪个", "什么时候", "谁", "多少",
            "what", "how", "why", "where", "which", "when", "who", "how much", "how many",
            # Information seeking
            "解释", "说明", "介绍", "告诉我", "帮我找", "查找", "搜索", "详细", "具体",
            "explain", "describe", "tell me", "help me find", "search", "details", "specific",
            # Documentation references
            "文档", "资料", "笔记", "记录", "内容", "文件", "资源",
            "document", "note", "record", "content", "file", "resource",
            # Technical terms
            "实现", "代码", "方法", "步骤", "流程", "配置", "设置", "教程",
            "implement", "code", "method", "step", "process", "config", "setup", "tutorial"
        }
        
        # Direct chat keywords - conversational
        self.direct_chat_keywords = {
            # Greetings
            "你好", "您好", "早上好", "下午好", "晚上好", "hi", "hello", "good morning", "good afternoon", "good evening",
            # Opinions and feelings
            "觉得", "认为", "感觉", "想", "希望", "喜欢", "不喜欢", "同意", "不同意",
            "think", "feel", "like", "dislike", "agree", "disagree", "opinion", "believe",
            # General conversation
            "聊天", "谈话", "讨论", "交流", "分享", "chat", "talk", "discuss", "share",
            # Creative tasks
            "创造", "创作", "写", "编写", "生成", "制作", "设计",
            "create", "write", "generate", "make", "design", "compose"
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
        
        return intent, confidence, details
    
    def _calculate_knowledge_score(self, query: str) -> float:
        """Calculate knowledge-seeking score"""
        score = 0.0
        
        # Check knowledge keywords
        keyword_matches = sum(1 for kw in self.knowledge_keywords if kw in query)
        score += keyword_matches * 0.2
        
        # Check knowledge patterns
        pattern_matches = sum(1 for pattern in self.knowledge_patterns 
                            if re.search(pattern, query))
        score += pattern_matches * 0.3
        
        # File/document references
        if any(word in query for word in ["文件", "文档", "笔记", "file", "document", "note"]):
            score += 0.4
        
        # Technical terms bonus
        technical_terms = ["代码", "配置", "设置", "API", "数据库", "算法", "框架"]
        if any(term in query for term in technical_terms):
            score += 0.3
        
        # Question structure bonus
        if query.startswith(("什么", "如何", "怎么", "为什么", "哪里", "what", "how", "why", "where")):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_direct_score(self, query: str) -> float:
        """Calculate direct chat score"""
        score = 0.0
        
        # Check direct chat keywords
        keyword_matches = sum(1 for kw in self.direct_chat_keywords if kw in query)
        score += keyword_matches * 0.2
        
        # Check direct patterns
        pattern_matches = sum(1 for pattern in self.direct_patterns 
                            if re.search(pattern, query))
        score += pattern_matches * 0.4
        
        # Greeting detection
        if query.startswith(("你好", "hi", "hello", "早上好", "下午好", "晚上好")):
            score += 0.5
        
        # Opinion/feeling expressions
        if any(word in query for word in ["觉得", "认为", "感觉", "think", "feel", "opinion"]):
            score += 0.3
        
        # Creative tasks
        if any(word in query for word in ["写", "创作", "生成", "设计", "write", "create", "generate", "design"]):
            score += 0.3
        
        # Short casual queries
        if len(query) < 20 and not any(char in query for char in ["什么", "如何", "怎么", "what", "how", "why"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _determine_intent(self, knowledge_score: float, direct_score: float) -> Tuple[QueryIntent, float]:
        """Determine final intent based on scores"""
        
        # Clear knowledge-seeking intent
        if knowledge_score >= 0.6 and knowledge_score > direct_score + 0.2:
            return QueryIntent.KNOWLEDGE_SEARCH, knowledge_score
        
        # Clear direct chat intent
        if direct_score >= 0.6 and direct_score > knowledge_score + 0.2:
            return QueryIntent.DIRECT_CHAT, direct_score
        
        # Mixed or ambiguous - prefer knowledge search for better user experience
        if knowledge_score > 0.3 and direct_score > 0.3:
            return QueryIntent.MIXED, (knowledge_score + direct_score) / 2
        
        # Default to knowledge search if uncertain
        if knowledge_score >= direct_score:
            return QueryIntent.KNOWLEDGE_SEARCH, knowledge_score
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