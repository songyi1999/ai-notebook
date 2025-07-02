"""
聊天路由处理模块
"""
from typing import List, Dict, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging
from pydantic import BaseModel
from ..agents.base import agent
from config import settings
from langchain_core.messages import AIMessageChunk

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class Message(BaseModel):
    """聊天消息模型"""
    role: str
    content: str

class ChatRequest(BaseModel):
    """聊天请求模型"""
    model: Optional[str] = None  # 模型名称变为可选参数
    messages: List[Message]
    stream: bool = False
    
class ChatResponse(BaseModel):
    """聊天响应模型"""
    model: str  # 返回实际使用的模型名称
    choices: List[Dict]

async def stream_chat_response(response_generator: AsyncGenerator) -> AsyncGenerator:
    """处理流式响应
    
    Args:
        response_generator: 异步生成器，用于获取模型响应
    """
    try:
        async for chunk in response_generator:
            if isinstance(chunk, AIMessageChunk):
                # 构造与OpenAI兼容的响应格式
                response_data = {
                    "choices": [{
                        "delta": {"content": chunk.content},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                
    except Exception as e:
        logger.error(f"处理流式响应时出错: {str(e)}")
        error_data = {
            "error": {
                "message": str(e)
            }
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    # 发送结束标记
    yield "data: [DONE]\n\n"

@router.post("/chat/completions")
async def chat_completions(request: ChatRequest) -> ChatResponse:
    """聊天完成接口
    
    Args:
        request: 聊天请求
        
    Returns:
        聊天响应
    """
    try:
        # 获取最后一条用户消息
        if not request.messages or request.messages[-1].role != "user":
            raise HTTPException(
                status_code=400,
                detail="无效的消息格式"
            )
            
        question = request.messages[-1].content
        
        # 转换历史记录格式
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages[:-1]  # 不包含最后一条
        ]
        
        # 获取回答
        logger.info(f"处理问题: {question}")
        
        if request.stream:
            # 获取流式响应生成器
            response_generator = agent.get_streaming_answer(question, history)
            return StreamingResponse(
                stream_chat_response(response_generator),
                media_type="text/event-stream"
            )
        
        # 非流式响应
        response = await agent.get_answer(question, history)
        logger.info(f"生成回答: {response}")
            
        # 返回完整响应，使用配置中的默认模型名称
        return ChatResponse(
            model=settings.MODELNAME,  # 始终使用配置中的默认模型名称
            choices=[{
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }]
        )
        
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求失败: {str(e)}"
        ) 