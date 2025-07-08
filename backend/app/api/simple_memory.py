from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
import logging

from ..services.simple_memory_service import SimpleMemoryService

router = APIRouter(tags=["simple-memory"])
logger = logging.getLogger(__name__)


@router.post("/process-conversation")
async def process_conversation(request_data: dict):
    """处理对话并更新记忆"""
    try:
        user_input = request_data.get("user_input", "")
        ai_response = request_data.get("ai_response", "")
        
        if not user_input or not ai_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户输入和AI回复不能为空"
            )
        
        memory_service = SimpleMemoryService()
        result = memory_service.process_conversation(user_input, ai_response)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理对话记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理对话记忆失败: {str(e)}"
        )


@router.get("/memories")
async def get_memories(limit: int = 10):
    """获取记忆用于上下文"""
    try:
        memory_service = SimpleMemoryService()
        memories = memory_service.get_memories_for_context(limit)
        return {"memories": memories}
        
    except Exception as e:
        logger.error(f"获取记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取记忆失败: {str(e)}"
        )


@router.get("/formatted-prompt")
async def get_formatted_prompt(limit: int = 10):
    """获取格式化的记忆提示词"""
    try:
        memory_service = SimpleMemoryService()
        prompt = memory_service.format_memories_for_prompt(limit)
        return {"prompt": prompt, "memory_count": len(memory_service.get_memories_for_context(limit))}
        
    except Exception as e:
        logger.error(f"获取格式化提示词失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取格式化提示词失败: {str(e)}"
        )


@router.get("/stats")
async def get_memory_stats():
    """获取记忆统计信息"""
    try:
        memory_service = SimpleMemoryService()
        stats = memory_service.get_memory_stats()
        return stats
        
    except Exception as e:
        logger.error(f"获取记忆统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取记忆统计失败: {str(e)}"
        )


@router.post("/add-manual")
async def add_manual_memory(request_data: dict):
    """手动添加记忆"""
    try:
        content = request_data.get("content", "")
        memory_type = request_data.get("type", "fact")
        importance = request_data.get("importance", 0.5)
        tags = request_data.get("tags", [])
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="记忆内容不能为空"
            )
        
        memory_service = SimpleMemoryService()
        success = memory_service.add_manual_memory(content, memory_type, importance, tags)
        
        if success:
            return {"message": "手动添加记忆成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加记忆失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动添加记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手动添加记忆失败: {str(e)}"
        )


@router.delete("/clear")
async def clear_memories():
    """清空所有记忆"""
    try:
        memory_service = SimpleMemoryService()
        success = memory_service.clear_memories()
        
        if success:
            return {"message": "清空记忆成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="清空记忆失败"
            )
            
    except Exception as e:
        logger.error(f"清空记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空记忆失败: {str(e)}"
        )


@router.post("/export")
async def export_memories(request_data: dict = None):
    """导出记忆到文件"""
    try:
        export_path = None
        if request_data:
            export_path = request_data.get("export_path")
        
        memory_service = SimpleMemoryService()
        file_path = memory_service.export_memories(export_path)
        
        if file_path:
            return {"message": "导出记忆成功", "file_path": file_path}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="导出记忆失败"
            )
            
    except Exception as e:
        logger.error(f"导出记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出记忆失败: {str(e)}"
        )