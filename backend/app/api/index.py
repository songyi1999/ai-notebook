from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database.session import get_db
from ..services.index_service import IndexService
from ..services.task_processor_service import TaskProcessorService
from ..services.vectorization_manager import VectorizationManager

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局变量存储重建进度
rebuild_progress = {
    "is_running": False,
    "progress": 0,
    "message": "",
    "result": None
}

@router.get("/status", response_model=Dict[str, Any])
def get_index_status(db: Session = Depends(get_db)):
    """获取索引状态"""
    try:
        index_service = IndexService(db)
        status = index_service.get_index_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取索引状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取索引状态失败: {str(e)}"
        )

@router.post("/rebuild", response_model=Dict[str, Any])
def rebuild_index(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """重建索引"""
    global rebuild_progress
    
    if rebuild_progress["is_running"]:
        return {
            "success": False,
            "message": "索引重建正在进行中，请稍候"
        }
    
    try:
        # 启动后台任务
        background_tasks.add_task(run_rebuild_task, db)
        
        return {
            "success": True,
            "message": "索引重建任务已启动，请使用 /progress 端点查看进度"
        }
    except Exception as e:
        logger.error(f"启动索引重建失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动索引重建失败: {str(e)}"
        )

@router.get("/progress", response_model=Dict[str, Any])
def get_rebuild_progress():
    """获取索引重建进度"""
    global rebuild_progress
    return {
        "success": True,
        "data": rebuild_progress
    }

def run_rebuild_task(db: Session):
    """运行重建任务"""
    global rebuild_progress
    
    try:
        rebuild_progress["is_running"] = True
        rebuild_progress["progress"] = 0
        rebuild_progress["message"] = "开始重建索引..."
        rebuild_progress["result"] = None
        
        index_service = IndexService(db)
        
        def progress_callback(progress: float, message: str):
            rebuild_progress["progress"] = progress
            rebuild_progress["message"] = message
            logger.info(f"重建进度: {progress}% - {message}")
        
        result = index_service.rebuild_sqlite_index(progress_callback)
        
        rebuild_progress["result"] = result
        rebuild_progress["is_running"] = False
        
        if result["success"]:
            rebuild_progress["message"] = "索引重建完成"
            rebuild_progress["progress"] = 100
        else:
            rebuild_progress["message"] = f"索引重建失败: {result.get('error', '未知错误')}"
            
    except Exception as e:
        logger.error(f"重建任务执行失败: {e}")
        rebuild_progress["is_running"] = False
        rebuild_progress["message"] = f"重建任务执行失败: {str(e)}"
        rebuild_progress["result"] = {"success": False, "error": str(e)}
    finally:
        db.close()

@router.post("/scan", response_model=Dict[str, Any])
def scan_notes_directory(db: Session = Depends(get_db)):
    """扫描notes目录"""
    try:
        index_service = IndexService(db)
        files_info = index_service.scan_notes_directory()
        
        return {
            "success": True,
            "data": {
                "total_files": len(files_info),
                "files": files_info[:10]  # 只返回前10个文件的信息
            }
        }
    except Exception as e:
        logger.error(f"扫描目录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"扫描目录失败: {str(e)}"
        )

@router.get("/system-status", response_model=Dict[str, Any])
def get_system_status(db: Session = Depends(get_db)):
    """获取系统状态统计信息"""
    try:
        # 获取索引状态
        index_service = IndexService(db)
        index_status = index_service.get_index_status()
        
        # 获取任务统计
        task_processor = TaskProcessorService(db)
        task_stats = task_processor.get_task_statistics()
        
        # 获取待处理任务数
        vectorization_manager = VectorizationManager(db)
        pending_counts = vectorization_manager.get_pending_tasks_count()
        
        return {
            "success": True,
            "data": {
                "total_files": index_status.get("sqlite_files", 0),
                "total_embeddings": index_status.get("vector_files", 0),
                "pending_tasks": pending_counts.get("total", 0),
                "task_details": {
                    "by_status": task_stats.get("by_status", {}),
                    "by_type": task_stats.get("by_type", {}),
                    "pending_details": pending_counts
                },
                "last_updated": index_status.get("last_check")
            }
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}"
        )

@router.get("/processor/status", response_model=Dict[str, Any])
def get_processor_status(db: Session = Depends(get_db)):
    """获取任务处理器运行状态"""
    try:
        task_processor = TaskProcessorService(db)
        processor_status = task_processor.get_processor_status()
        
        return {
            "success": True,
            "data": processor_status
        }
    except Exception as e:
        logger.error(f"获取任务处理器状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务处理器状态失败: {str(e)}"
        )

@router.post("/processor/start", response_model=Dict[str, Any])
def start_processor(
    force: bool = False,
    db: Session = Depends(get_db)
):
    """手动启动任务处理器"""
    try:
        task_processor = TaskProcessorService(db)
        result = task_processor.start_processor(force=force)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "data": result["status"]
            }
        else:
            return {
                "success": False,
                "message": result["message"],
                "data": result["status"]
            }
    except Exception as e:
        logger.error(f"启动任务处理器失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务处理器失败: {str(e)}"
        )

@router.post("/processor/stop", response_model=Dict[str, Any])
def stop_processor(db: Session = Depends(get_db)):
    """停止任务处理器"""
    try:
        task_processor = TaskProcessorService(db)
        result = task_processor.stop_processor()
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "data": result["status"]
            }
        else:
            return {
                "success": False,
                "message": result["message"],
                "data": result["status"]
            }
    except Exception as e:
        logger.error(f"停止任务处理器失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止任务处理器失败: {str(e)}"
        ) 