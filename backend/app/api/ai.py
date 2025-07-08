from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
import json
import asyncio

from ..services.ai_service_langchain import AIService
from ..services.file_service import FileService
from ..services.intent_service import IntentService, QueryIntent
from ..services.response_evaluator import ResponseEvaluator
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

class OutlineRequest(BaseModel):
    content: str
    max_items: int = 10

class ChatRequest(BaseModel):
    question: str
    max_context_length: int = 3000
    search_limit: int = 5
    enable_tools: bool = True
    use_intent_analysis: bool = True

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
    enable_tools: bool = True
    use_intent_analysis: bool = True

class OpenAIChatResponse(BaseModel):
    """OpenAI兼容的聊天响应模型"""
    model: str  # 返回实际使用的模型名称
    choices: List[Dict]

async def enhanced_stream_chat_response(ai_service: AIService, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True, messages: List[Dict] = None, use_intent_analysis: bool = True, db: Session = None) -> AsyncGenerator:
    """增强的流式响应处理，包含自我评估和后续处理
    
    Args:
        ai_service: AI服务实例
        question: 用户问题
        max_context_length: 最大上下文长度
        search_limit: 搜索结果限制
        enable_tools: 是否启用工具
        messages: 消息历史
        use_intent_analysis: 是否使用意图分析
        db: 数据库会话
    """
    try:
        logger.info(f"开始增强流式处理问题: {question}")
        
        # Initialize response evaluator
        evaluator = ResponseEvaluator(db) if db else None
        
        # Intent analysis for optimization
        use_knowledge_base = True
        if use_intent_analysis:
            intent_service = IntentService()
            intent, confidence, details = intent_service.analyze_intent(question)
            
            # Determine if knowledge base should be used
            use_knowledge_base = intent_service.should_use_knowledge_base(question)
            logger.info(f"Intent analysis: {intent.value} (confidence: {confidence:.2f}), use_kb: {use_knowledge_base}")
        
        # Choose appropriate chat method based on intent
        if use_knowledge_base:
            # Use RAG with knowledge base search
            stream_method = ai_service.streaming_chat_with_context(
                question=question,
                max_context_length=max_context_length,
                search_limit=search_limit,
                enable_tools=enable_tools,
                messages=messages
            )
        else:
            # Use direct chat for faster response
            stream_method = ai_service.direct_chat_streaming(
                question=question,
                messages=messages
            )
        
        # Collect response for evaluation
        collected_response = []
        context_used = ""
        related_documents = []
        
        async for stream_data in stream_method:
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
                collected_response.append(stream_data["chunk"])
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是工具调用开始
            elif "tool_calls_started" in stream_data:
                tool_start_data = {
                    "tool_calls_started": True,
                    "tool_count": stream_data["tool_count"],
                    "metadata": {
                        "related_documents": stream_data.get("related_documents", []),
                        "search_query": stream_data.get("search_query", ""),
                        "context_length": stream_data.get("context_length", 0)
                    }
                }
                related_documents = stream_data.get("related_documents", [])
                yield f"data: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是工具调用进度
            elif "tool_call_progress" in stream_data:
                tool_progress_data = {
                    "tool_call_progress": stream_data["tool_call_progress"]
                }
                yield f"data: {json.dumps(tool_progress_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是工具调用完成
            elif "tool_calls_completed" in stream_data:
                tool_complete_data = {
                    "tool_calls_completed": True,
                    "tool_results": stream_data["tool_results"]
                }
                yield f"data: {json.dumps(tool_complete_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是结束信号
            elif "finished" in stream_data:
                context_used = stream_data.get("search_query", "")
                related_documents = stream_data.get("related_documents", [])
                
                # Perform response evaluation
                full_response = "".join(collected_response)
                evaluation_result = None
                
                if evaluator and full_response.strip():
                    try:
                        evaluation_result = evaluator.evaluate_response(
                            user_question=question,
                            llm_response=full_response,
                            context_used=context_used,
                            available_tools=["search", "mcp_tools"] if enable_tools else ["search"]
                        )
                        
                        logger.info(f"Response evaluation completed: {evaluation_result.get('completeness', 'unknown')}")
                        
                        # Check if follow-up is needed
                        if evaluation_result.get("requires_follow_up", False):
                            suggested_actions = evaluation_result.get("suggested_actions", [])
                            
                            # Send thinking process to user
                            thinking_data = {
                                "thinking_process": {
                                    "evaluation": {
                                        "completeness": evaluation_result.get("completeness"),
                                        "confidence": evaluation_result.get("confidence"),
                                        "reasoning": evaluation_result.get("reasoning")
                                    },
                                    "follow_up_needed": True,
                                    "suggested_actions": suggested_actions
                                }
                            }
                            yield f"data: {json.dumps(thinking_data, ensure_ascii=False)}\n\n"
                            
                            # Perform follow-up actions if auto-follow-up is enabled
                            if evaluator.should_perform_follow_up(evaluation_result):
                                for action in suggested_actions[:2]:  # Limit to 2 actions
                                    async for follow_up_chunk in perform_follow_up_action(action, ai_service, question, full_response):
                                        yield follow_up_chunk
                    
                    except Exception as e:
                        logger.error(f"Response evaluation failed: {e}")
                
                # 发送结束信号和元数据
                final_data = {
                    "choices": [{
                        "delta": {},
                        "finish_reason": "stop"
                    }],
                    "metadata": {
                        "related_documents": related_documents,
                        "processing_time": stream_data.get("processing_time", 0),
                        "search_query": context_used,
                        "context_length": stream_data.get("context_length", 0),
                        "evaluation": evaluation_result
                    }
                }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
    except Exception as e:
        logger.error(f"增强流式响应处理时出错: {str(e)}")
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

async def perform_follow_up_action(action: Dict[str, Any], ai_service: AIService, original_question: str, previous_response: str) -> AsyncGenerator:
    """执行后续补充行动"""
    try:
        action_type = action.get("type", "")
        
        if action_type == "knowledge_search":
            # 发送思考过程信息
            thinking_data = {
                "thinking_process": {
                    "action": "knowledge_search",
                    "description": action.get("description", ""),
                    "search_query": action.get("search_query", "")
                }
            }
            yield f"data: {json.dumps(thinking_data, ensure_ascii=False)}\n\n"
            
            # 执行知识搜索
            search_query = action.get("search_query", original_question)
            
            # 使用改进的搜索进行补充回答
            additional_stream = ai_service.streaming_chat_with_context(
                question=f"基于之前的回答，请补充更多关于'{search_query}'的详细信息",
                max_context_length=2000,
                search_limit=3,
                enable_tools=True,
                messages=[
                    {"role": "user", "content": original_question},
                    {"role": "assistant", "content": previous_response}
                ]
            )
            
            # 发送补充内容
            supplement_data = {
                "supplement_start": True,
                "action_type": action_type
            }
            yield f"data: {json.dumps(supplement_data, ensure_ascii=False)}\n\n"
            
            async for supplement_stream in additional_stream:
                if "chunk" in supplement_stream:
                    response_data = {
                        "choices": [{
                            "delta": {"content": supplement_stream["chunk"]},
                            "finish_reason": None
                        }],
                        "supplement": True
                    }
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
        
        elif action_type == "content_expansion":
            # 发送扩展思考过程
            thinking_data = {
                "thinking_process": {
                    "action": "content_expansion",
                    "description": action.get("description", ""),
                    "expansion_areas": action.get("expansion_areas", [])
                }
            }
            yield f"data: {json.dumps(thinking_data, ensure_ascii=False)}\n\n"
            
            # 生成扩展内容
            expansion_areas = action.get("expansion_areas", [])
            expansion_query = f"请针对以下方面提供更详细的信息：{', '.join(expansion_areas)}"
            
            expansion_stream = ai_service.direct_chat_streaming(
                question=expansion_query,
                messages=[
                    {"role": "user", "content": original_question},
                    {"role": "assistant", "content": previous_response}
                ]
            )
            
            # 发送扩展内容
            supplement_data = {
                "supplement_start": True,
                "action_type": action_type
            }
            yield f"data: {json.dumps(supplement_data, ensure_ascii=False)}\n\n"
            
            async for expansion_chunk in expansion_stream:
                if "chunk" in expansion_chunk:
                    response_data = {
                        "choices": [{
                            "delta": {"content": expansion_chunk["chunk"]},
                            "finish_reason": None
                        }],
                        "supplement": True
                    }
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    
    except Exception as e:
        logger.error(f"Follow-up action failed: {e}")
        error_data = {
            "error": {
                "message": f"后续处理失败: {str(e)}"
            }
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

async def stream_chat_response(ai_service: AIService, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True, messages: List[Dict] = None, use_intent_analysis: bool = True) -> AsyncGenerator:
    """处理真正的流式响应
    
    Args:
        ai_service: AI服务实例
        question: 用户问题
        max_context_length: 最大上下文长度
        search_limit: 搜索结果限制
    """
    try:
        logger.info(f"开始流式处理问题: {question}")
        
        # Intent analysis for optimization
        use_knowledge_base = True
        if use_intent_analysis:
            intent_service = IntentService()
            intent, confidence, details = intent_service.analyze_intent(question)
            
            # Determine if knowledge base should be used
            use_knowledge_base = intent_service.should_use_knowledge_base(question)
            logger.info(f"Intent analysis: {intent.value} (confidence: {confidence:.2f}), use_kb: {use_knowledge_base}")
        
        # Choose appropriate chat method based on intent
        if use_knowledge_base:
            # Use RAG with knowledge base search
            stream_method = ai_service.streaming_chat_with_context(
                question=question,
                max_context_length=max_context_length,
                search_limit=search_limit,
                enable_tools=enable_tools,
                messages=messages
            )
        else:
            # Use direct chat for faster response
            stream_method = ai_service.direct_chat_streaming(
                question=question,
                messages=messages
            )
        
        async for stream_data in stream_method:
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
            
            # 检查是否是工具调用开始
            elif "tool_calls_started" in stream_data:
                tool_start_data = {
                    "tool_calls_started": True,
                    "tool_count": stream_data["tool_count"],
                    "metadata": {
                        "related_documents": stream_data.get("related_documents", []),
                        "search_query": stream_data.get("search_query", ""),
                        "context_length": stream_data.get("context_length", 0)
                    }
                }
                yield f"data: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是工具调用进度
            elif "tool_call_progress" in stream_data:
                tool_progress_data = {
                    "tool_call_progress": stream_data["tool_call_progress"]
                }
                yield f"data: {json.dumps(tool_progress_data, ensure_ascii=False)}\n\n"
            
            # 检查是否是工具调用完成
            elif "tool_calls_completed" in stream_data:
                tool_complete_data = {
                    "tool_calls_completed": True,
                    "tool_results": stream_data["tool_results"]
                }
                yield f"data: {json.dumps(tool_complete_data, ensure_ascii=False)}\n\n"
            
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
        
        # 将消息转换为字典格式
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        logger.info(f"处理OpenAI格式问题: {question}，消息历史: {len(messages_dict)} 条")
        
        if request.stream:
            # 返回增强的流式响应
            return StreamingResponse(
                enhanced_stream_chat_response(ai_service, question, request.max_context_length, request.search_limit, request.enable_tools, messages_dict, request.use_intent_analysis, db),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        
        # 非流式响应
        # Intent analysis for optimization
        use_knowledge_base = True
        if request.use_intent_analysis:
            intent_service = IntentService()
            use_knowledge_base = intent_service.should_use_knowledge_base(question)
            logger.info(f"Non-streaming intent analysis: use_kb={use_knowledge_base}")
        
        if use_knowledge_base:
            result = ai_service.chat_with_context(
                question=question,
                max_context_length=request.max_context_length,
                search_limit=request.search_limit,
                enable_tools=request.enable_tools,
                messages=messages_dict
            )
        else:
            result = ai_service.direct_chat(
                question=question,
                messages=messages_dict
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

@router.post("/ai/outline")
def generate_outline_api(request: OutlineRequest, db: Session = Depends(get_db)):
    """生成内容提纲"""
    ai_service = AIService(db)
    
    if not ai_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用，请检查配置"
        )
    
    outline = ai_service.generate_outline(request.content, request.max_items)
    
    if outline is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提纲生成失败"
        )
    
    return {"outline": outline}

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
        # Intent analysis for optimization
        use_knowledge_base = True
        if request.use_intent_analysis:
            intent_service = IntentService()
            use_knowledge_base = intent_service.should_use_knowledge_base(request.question)
            logger.info(f"Legacy chat intent analysis: use_kb={use_knowledge_base}")
        
        if use_knowledge_base:
            result = ai_service.chat_with_context(
                question=request.question,
                max_context_length=request.max_context_length,
                search_limit=request.search_limit,
                enable_tools=request.enable_tools,
            )
        else:
            result = ai_service.direct_chat(
                question=request.question,
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