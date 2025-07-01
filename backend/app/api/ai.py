from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..database.session import get_db

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
    similarity_threshold: float = 0.7

class ContentAnalysisRequest(BaseModel):
    content: str

class RelatedQuestionsRequest(BaseModel):
    content: str
    num_questions: int = 3

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

@router.get("/ai/status")
def get_ai_status_api(db: Session = Depends(get_db)):
    """获取AI服务状态"""
    ai_service = AIService(db)
    
    return {
        "available": ai_service.is_available(),
        "openai_configured": ai_service.openai_api_key is not None,
        "base_url": ai_service.openai_base_url
    } 