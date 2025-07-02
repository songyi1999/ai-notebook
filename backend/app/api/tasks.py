from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database.session import get_db
from ..services.task_processor_service import TaskProcessorService
from ..services.vectorization_manager import VectorizationManager

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["任务管理"])

@router.get("/statistics")
def get_task_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取任务队列统计信息"""
    try:
        task_processor = TaskProcessorService(db)
        stats = task_processor.get_task_statistics()
        
        # 添加向量化管理器的统计
        vectorization_manager = VectorizationManager(db)
        pending_counts = vectorization_manager.get_pending_tasks_count()
        
        stats['pending_details'] = pending_counts
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")

@router.post("/cleanup/duplicates")
def cleanup_duplicate_tasks(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """清理重复的待处理任务"""
    try:
        task_processor = TaskProcessorService(db)
        removed_count = task_processor.clear_duplicate_pending_tasks()
        
        return {
            "success": True,
            "message": f"成功清理 {removed_count} 个重复任务",
            "removed_count": removed_count
        }
        
    except Exception as e:
        logger.error(f"清理重复任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理重复任务失败: {str(e)}")

@router.post("/cleanup/old")
def cleanup_old_tasks(
    days: int = 7,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """清理旧的已完成/失败任务"""
    try:
        task_processor = TaskProcessorService(db)
        task_processor.cleanup_old_tasks(days)
        
        return {
            "success": True,
            "message": f"成功清理 {days} 天前的旧任务"
        }
        
    except Exception as e:
        logger.error(f"清理旧任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理旧任务失败: {str(e)}")

@router.post("/process/file")
def process_file_vectorization(
    file_path: str,
    immediate: bool = False,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """处理文件的向量化和索引"""
    try:
        vectorization_manager = VectorizationManager(db)
        
        if immediate:
            # 立即处理
            success = vectorization_manager.process_file_immediate(file_path)
            message = "文件立即处理完成" if success else "文件处理失败"
        else:
            # 添加到任务队列
            success = vectorization_manager.process_file_update(file_path)
            message = "文件已添加到处理队列" if success else "添加到队列失败"
        
        return {
            "success": success,
            "message": message,
            "file_path": file_path,
            "immediate": immediate
        }
        
    except Exception as e:
        logger.error(f"处理文件向量化失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理文件向量化失败: {str(e)}")

@router.get("/health")
def get_task_processor_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取任务处理器健康状态"""
    try:
        task_processor = TaskProcessorService(db)
        
        # 检查锁文件状态
        lock_exists = task_processor.lock_file.exists()
        is_running = task_processor.is_running
        
        # 获取基本统计
        stats = task_processor.get_task_statistics()
        
        return {
            "success": True,
            "data": {
                "lock_exists": lock_exists,
                "is_running": is_running,
                "pending_tasks": stats.get('by_status', {}).get('pending', 0),
                "processing_tasks": stats.get('by_status', {}).get('processing', 0),
                "failed_tasks": stats.get('by_status', {}).get('failed', 0),
                "duplicate_tasks": stats.get('total_duplicate_tasks', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"获取任务处理器健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}") 