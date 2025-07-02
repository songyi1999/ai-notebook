import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path

from ..models.file import File
from ..models.pending_task import PendingTask
from .ai_service_langchain import AIService
from .index_service import IndexService
from .task_processor_service import TaskProcessorService

logger = logging.getLogger(__name__)

class VectorizationManager:
    """向量化管理器 - 统一管理文件的向量化和索引流程"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
        self.index_service = IndexService(db)
        self.task_processor = TaskProcessorService(db)
    
    def process_file_update(self, file_path: str, content: str = None, title: str = None) -> bool:
        """
        处理文件更新 - 统一入口点
        
        Args:
            file_path: 文件路径
            content: 文件内容（可选，如果不提供则从文件读取）
            title: 文件标题（可选，如果不提供则从文件路径提取）
        
        Returns:
            bool: 处理是否成功
        """
        try:
            logger.info(f"开始处理文件更新: {file_path}")
            
            # 1. 获取或创建文件记录
            file = self._get_or_create_file_record(file_path, content, title)
            if not file:
                logger.error(f"无法获取或创建文件记录: {file_path}")
                return False
            
            # 2. 添加向量化任务（带去重）
            vector_task_added = self._add_vectorization_task(file.id, file.file_path)
            
            logger.info(f"文件更新处理完成: {file_path}, 向量任务: {vector_task_added}")
            return True
            
        except Exception as e:
            logger.error(f"处理文件更新失败: {file_path}, 错误: {e}")
            return False
    
    def process_file_immediate(self, file_path: str, content: str = None, title: str = None) -> bool:
        """
        立即处理文件（同步处理，不使用任务队列）
        
        Args:
            file_path: 文件路径
            content: 文件内容（可选）
            title: 文件标题（可选）
        
        Returns:
            bool: 处理是否成功
        """
        try:
            logger.info(f"开始立即处理文件: {file_path}")
            
            # 1. 获取或创建文件记录
            file = self._get_or_create_file_record(file_path, content, title)
            if not file:
                logger.error(f"无法获取或创建文件记录: {file_path}")
                return False
            
            # 2. 立即执行向量化
            vector_success = self._execute_vectorization(file)
            
            logger.info(f"文件立即处理完成: {file_path}, 向量化: {vector_success}")
            return vector_success
            
        except Exception as e:
            logger.error(f"立即处理文件失败: {file_path}, 错误: {e}")
            return False
    
    def _get_or_create_file_record(self, file_path: str, content: str = None, title: str = None) -> Optional[File]:
        """获取或创建文件记录"""
        try:
            # 先尝试查找现有文件
            file = self.db.query(File).filter(File.file_path == file_path).first()
            
            if file:
                # 更新现有文件信息
                if content is not None:
                    file.content = content
                if title is not None:
                    file.title = title
                
                # 更新文件大小和修改时间
                file_full_path = Path(file_path)
                if file_full_path.exists():
                    file.file_size = file_full_path.stat().st_size
                    file.updated_at = file.updated_at  # 触发更新
                
                self.db.commit()
                logger.info(f"更新现有文件记录: {file_path}")
                return file
            else:
                # 创建新文件记录
                return self.index_service.create_file_record(file_path, content, title)
                
        except Exception as e:
            logger.error(f"获取或创建文件记录失败: {file_path}, 错误: {e}")
            self.db.rollback()
            return None
    
    def _add_vectorization_task(self, file_id: int, file_path: str, priority: int = 1) -> bool:
        """添加向量化任务（带去重）"""
        return self.task_processor.add_task(file_id, file_path, "vector_index", priority)
    

    
    def _execute_vectorization(self, file: File) -> bool:
        """执行向量化"""
        try:
            if not self.ai_service.is_available():
                logger.warning(f"AI服务不可用，跳过向量化: {file.file_path}")
                return True  # 跳过但不算失败
            
            # 删除旧的向量索引
            self.ai_service.delete_document_by_file_id(file.id)
            
            # 创建新的向量索引
            success = self.ai_service.create_embeddings(file)
            
            if success:
                logger.info(f"向量化处理成功: {file.file_path}")
            else:
                logger.error(f"向量化处理失败: {file.file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"执行向量化失败: {file.file_path}, 错误: {e}")
            return False
    

    
    def get_pending_tasks_count(self) -> Dict[str, int]:
        """获取待处理任务统计"""
        try:
            vector_count = self.db.query(PendingTask).filter(
                PendingTask.task_type == "vector_index",
                PendingTask.status == "pending"
            ).count()
            
            return {
                "vector_index": vector_count,
                "total": vector_count
            }
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {"vector_index": 0, "total": 0}
    
    def clear_duplicate_tasks(self) -> int:
        """清理重复的待处理任务"""
        try:
            # 查找重复任务（相同file_id和task_type的pending任务）
            duplicate_tasks = self.db.execute("""
                SELECT file_id, task_type, MIN(id) as keep_id, COUNT(*) as count
                FROM pending_tasks 
                WHERE status = 'pending'
                GROUP BY file_id, task_type
                HAVING COUNT(*) > 1
            """).fetchall()
            
            removed_count = 0
            for row in duplicate_tasks:
                # 删除除了最早的任务之外的所有重复任务
                deleted = self.db.execute("""
                    DELETE FROM pending_tasks 
                    WHERE file_id = :file_id 
                    AND task_type = :task_type 
                    AND status = 'pending'
                    AND id != :keep_id
                """, {
                    "file_id": row.file_id,
                    "task_type": row.task_type, 
                    "keep_id": row.keep_id
                }).rowcount
                
                removed_count += deleted
                logger.info(f"清理重复任务: file_id={row.file_id}, task_type={row.task_type}, 删除{deleted}个")
            
            self.db.commit()
            logger.info(f"清理重复任务完成，共删除 {removed_count} 个任务")
            return removed_count
            
        except Exception as e:
            logger.error(f"清理重复任务失败: {e}")
            self.db.rollback()
            return 0 