from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
import json
import asyncio

from ..services.ai_service_langchain import AIService
from ..services.file_service import FileService
from ..database.session import get_db
from ..config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class SummaryRequest(BaseModel):
    content: str
    max_length: int = 200

class TagSuggestionRequest(BaseModel):
    title: str
    content: str
    max_tags: int = 5

class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    similarity_threshold: float = Field(default_factory=lambda: settings.semantic_search_threshold)

class ContentAnalysisRequest(BaseModel):
    content: str

class RelatedQuestionsRequest(BaseModel):
    content: str
    num_questions: int = 3

class ChatRequest(BaseModel):
    question: str
    max_context_length: int = 3000
    search_limit: int = 5

# OpenAI兼容格式
class Message(BaseModel):
    """聊天消息模型"""
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    """OpenAI兼容的聊天请求模型"""
    model: Optional[str] = None  # 模型名称变为可选参数
    messages: List[Message]
    stream: bool = False
    max_context_length: int = 3000
    search_limit: int = 5
    
class OpenAIChatResponse(BaseModel):
    """OpenAI兼容的聊天响应模型"""
    model: str  # 返回实际使用的模型名称
    choices: List[Dict]

async def stream_chat_response(ai_service: AIService, question: str, max_context_length: int = 3000, search_limit: int = 5) -> AsyncGenerator:
    """处理真正的流式响应
    
    Args:
        ai_service: AI服务实例
        question: 用户问题
        max_context_length: 最大上下文长度
        search_limit: 搜索结果限制
    """
    try:
        logger.info(f"开始流式处理问题: {question}")
        
        # 使用真正的流式RAG问答
        async for stream_data in ai_service.streaming_chat_with_context(
            question=question,
            max_context_length=max_context_length,
            search_limit=search_limit
        ):
            # 检查是否有错误
            if "error" in stream_data:
                error_data = {
                    "error": {
                        "message": stream_data["error"]
                    }
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                continue
            
            # 检查是否是内容块
            if "chunk" in stream_data:
                # 构造与OpenAI兼容的响应格式
                response_data = {
                    "choices": [{
                        "delta": {"content": stream_data["chunk"]},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是结束信号
            elif "finished" in stream_data:
                # 发送结束信号和元数据
                final_data = {
                    "choices": [{
                        "delta": {},
                        "finish_reason": "stop"
                    }],
                    "metadata": {
                        "related_documents": stream_data.get("related_documents", []),
                        "processing_time": stream_data.get("processing_time", 0),
                        "search_query": stream_data.get("search_query", ""),
                        "context_length": stream_data.get("context_length", 0)
                    }
                }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
    except Exception as e:
        logger.error(f"处理流式响应时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        
        error_data = {
            "error": {
                "message": str(e)
            }
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    # 发送结束标记
    yield "data: [DONE]\n\n"

@router.post("/chat/completions")
async def chat_completions(request: OpenAIChatRequest, db: Session = Depends(get_db)):
    """OpenAI兼容的聊天完成接口
    
    Args:
        request: 聊天请求
        
    Returns:
        聊天响应或流式响应
    """
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    try:
        # 获取最后一条用户消息
        if not request.messages or request.messages[-1].role != "user":
            raise HTTPException(
                status_code=400,
                detail="无效的消息格式"
            )
            
        question = request.messages[-1].content
        
        if not question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="问题不能为空"
            )
        
        logger.info(f"处理OpenAI格式问题: {question}")
        
        if request.stream:
            # 返回流式响应
            return StreamingResponse(
                stream_chat_response(ai_service, question, request.max_context_length, request.search_limit),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        
        # 非流式响应
        result = ai_service.chat_with_context(
            question=question,
            max_context_length=request.max_context_length,
            search_limit=request.search_limit
        )
        
        logger.info(f"生成回答: {result.get('answer', '')[:100]}...")
            
        # 返回完整响应，使用配置中的默认模型名称
        return OpenAIChatResponse(
            model=settings.openai_model,  # 使用配置中的模型名称
            choices=[{
                "message": {
                    "role": "assistant",
                    "content": result.get("answer", "")
                },
                "finish_reason": "stop"
            }]
        )
        
    except Exception as e:
        logger.error(f"处理OpenAI格式请求失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求失败: {str(e)}"
        )

@router.post("/ai/summary")
def generate_summary_api(request: SummaryRequest, db: Session = Depends(get_db)):
    """生成内容摘要"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    summary = ai_service.generate_summary(request.content, request.max_length)
    
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="摘要生成失败"
        )
    
    return {"summary": summary}

@router.post("/ai/suggest-tags")
def suggest_tags_api(request: TagSuggestionRequest, db: Session = Depends(get_db)):
    """智能标签建议"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    tags = ai_service.suggest_tags(request.title, request.content, request.max_tags)
    
    return {"tags": tags}

@router.post("/ai/create-embeddings/{file_id}")
def create_embeddings_api(file_id: int, db: Session = Depends(get_db)):
    """为文件创建向量嵌入"""
    ai_service = AIService(db)
    file_service = FileService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    # 获取文件
    file = file_service.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    success = ai_service.create_embeddings(file)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建嵌入失败"
        )
    
    return {"success": True, "message": "嵌入创建成功"}

@router.post("/ai/semantic-search")
def semantic_search_api(request: SemanticSearchRequest, db: Session = Depends(get_db)):
    """语义搜索"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    results = ai_service.semantic_search(
        request.query, 
        request.limit, 
        request.similarity_threshold
    )
    
    return {"results": results}

@router.post("/ai/analyze-content")
def analyze_content_api(request: ContentAnalysisRequest, db: Session = Depends(get_db)):
    """内容分析"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    analysis = ai_service.analyze_content(request.content)
    
    return {"analysis": analysis}

@router.post("/ai/related-questions")
def generate_related_questions_api(request: RelatedQuestionsRequest, db: Session = Depends(get_db)):
    """生成相关问题"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    questions = ai_service.generate_related_questions(request.content, request.num_questions)
    
    return {"questions": questions}

@router.post("/ai/chat")
def chat_api(request: ChatRequest, db: Session = Depends(get_db)):
    """AI智能问答 - 基于RAG的聊天功能"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问题不能为空"
        )
    
    try:
        result = ai_service.chat_with_context(
            question=request.question,
            max_context_length=request.max_context_length,
            search_limit=request.search_limit
        )
        
        return result
        
    except Exception as e:
        logger.error(f"聊天API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="智能问答处理失败"
        )

@router.post("/ai/discover-links/{file_id}")
def discover_smart_links_api(file_id: int, db: Session = Depends(get_db)):
    """智能发现文章间的链接关系"""
    ai_service = AIService(db)
    file_service = FileService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    # 获取文件
    file = file_service.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        suggestions = ai_service.discover_smart_links(file_id, file.content, file.title)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"智能链接发现失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="智能链接发现失败"
        )

@router.get("/ai/status")
def get_ai_status_api(db: Session = Depends(get_db)):
    """获取AI服务状态"""
    ai_service = AIService(db)
    
    return {
        "available": ai_service.is_available(),
        "openai_configured": ai_service.openai_api_key is not None,
        "base_url": ai_service.openai_base_url
    } 