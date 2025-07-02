"""
智能体基础实现，包含意图识别和回答生成
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import logging
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from config import settings
from datetime import datetime

import pytz  # 添加时区支持

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置北京时区
CN_TZ = pytz.timezone('Asia/Shanghai')

# 意图识别模板
INTENT_TEMPLATE = """你是一个医疗评价助手，需要判断用户的问题类型。

用户的问题是: {question}

请判断这个问题属于以下哪种类型:
1. atmp - 询问医疗评价相关内容，包括医疗质量评价、医疗项目分析等
2. other - 其他类型的问题

只需要返回类型名称，不需要解释。例如: atmp"""


class ATMPAgent:
    """医疗评价智能体"""
    
    def __init__(self):
        """初始化智能体"""
        # 初始化意图识别模型
        self.intent_model = ChatOpenAI(
            model=settings.MODELNAME,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            max_tokens=1000  # 添加最大token限制
           
        )
        
        # 初始化回答生成模型,用deepseek-r1:1.5b
        self.answer_model = ChatOpenAI(
            model=settings.MODELNAME_WITH_CHAIN,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            max_tokens=1000
        )
        self.streaming_answer_model = ChatOpenAI(
            model=settings.MODELNAME_WITH_CHAIN,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            streaming=True,
            max_tokens=1000
        )
        
        # 初始化医疗评价专用模型
        self.atmp_model = ChatOpenAI(
            model=settings.ATMPMODEL,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            max_tokens=1000
        )
        # 初始化医疗评价专用流式模型
        self.streaming_atmp_model = ChatOpenAI(
            model=settings.ATMPMODEL,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            streaming=True,
            max_tokens=1000
        )
        
        # 创建意图识别Chain
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_TEMPLATE),
            ("human", "{question}")
        ])
        self.intent_chain = self.intent_prompt | self.intent_model
        
        
    
    
    async def _get_intent(self, question: str) -> str:
        """识别问题意图
        
        Args:
            question: 用户问题
            
        Returns:
            意图类型: atmp/other
        """
        try:
            logger.info(f"开始识别意图: {question}")
            result = await self.intent_chain.ainvoke({"question": question})
            intent = result.content.strip().lower()
            logger.info(f"意图识别结果: {intent}")
            return intent
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            return "other"
            
    async def get_streaming_answer(
        self, 
        question: str,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator:
        """获取流式回答
        
        Args:
            question: 用户问题
            messages: 消息列表（包含系统提示、历史记录等）
            
        Returns:
            异步生成器，用于获取流式回答
        """
        try:
            # 如果提供了完整的messages列表，直接使用
            if messages and len(messages) > 1:
                # 转换为LangChain消息格式
                langchain_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        langchain_messages.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        langchain_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        langchain_messages.append(AIMessage(content=msg["content"]))
                
                # 检查是否包含文档内容（通过系统消息判断）
                has_document_context = any(
                    msg["role"] == "system" and "参考文档" in msg["content"] 
                    for msg in messages
                )
                
                if has_document_context:
                    # 有文档上下文，使用医疗评价专用模型
                    async for chunk in self.streaming_atmp_model.astream(langchain_messages):
                        yield chunk
                else:
                    # 没有文档上下文，识别意图
                    intent = await self._get_intent(question)
                    if "atmp" in intent:
                        async for chunk in self.streaming_atmp_model.astream(langchain_messages):
                            yield chunk
                    else:
                        async for chunk in self.streaming_answer_model.astream(langchain_messages):
                            yield chunk
                return
            
            # 兼容原有的调用方式
            # 识别意图
            intent = await self._get_intent(question)
            
            # 根据意图选择搜索类型和模型
            if "atmp" in intent:
                # 使用医疗评价专用模型直接回答
                async for chunk in self.streaming_atmp_model.astream(question):
                    yield chunk
                return
            else:
                # 其他问题直接使用模型回答
                langchain_messages = []
                
                # 添加历史记录（如果messages是历史记录格式）
                if messages:
                    for msg in messages[-3:]:  # 只使用最近3轮对话
                        if msg["role"] == "user":
                            langchain_messages.append(HumanMessage(content=msg["content"]))
                        else:
                            langchain_messages.append(AIMessage(content=msg["content"]))
                            
                # 添加当前问题
                langchain_messages.append(HumanMessage(content=question))
                
                # 生成流式回答
                async for chunk in self.streaming_answer_model.astream(langchain_messages):
                    yield chunk
                return
                
        except Exception as e:
            logger.error(f"生成流式回答失败: {str(e)} - 文件: {__file__} - 函数: get_streaming_answer")
            raise
            
    async def get_answer(
        self, 
        question: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """获取问题的答案
        
        Args:
            question: 用户问题
            history: 历史对话记录
            
        Returns:
            回答内容
        """
        try:
            # 识别意图
            intent = await self._get_intent(question)
            
            # 根据意图选择搜索类型和模型
            if "atmp" in intent:
                # 使用医疗评价专用模型直接回答
                answer = await self.atmp_model.ainvoke(question)
                return answer.content.strip()
            else:
                # 其他问题直接使用模型回答
                messages = []
                
                # 添加历史记录
                if history:
                    for msg in history[-3:]:  # 只使用最近3轮对话
                        if msg["role"] == "user":
                            messages.append(HumanMessage(content=msg["content"]))
                        else:
                            messages.append(AIMessage(content=msg["content"]))
                            
                # 添加当前问题
                messages.append(HumanMessage(content=question))
                
                answer = await self.answer_model.ainvoke(messages)
                return answer.content.strip()
        except Exception as e:
            logger.error(f"获取答案失败: {str(e)}")
            raise
            
# 创建全局智能体实例
agent = ATMPAgent()

