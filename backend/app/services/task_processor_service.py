import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pathlib import Path

from ..models.pending_task import PendingTask
from ..models.file import File
from ..database.session import get_db
from .ai_service_langchain import AIService
from .index_service import IndexService

logger = logging.getLogger(__name__)

class TaskProcessorService:
    """后台任务处理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.lock_file = Path("data/task_processor.lock")
        self.is_running = False
        
    def _acquire_lock(self) -> bool:
        """获取处理锁，防止重复执行"""
        try:
            if self.lock_file.exists():
                # 检查锁文件是否过期（超过10分钟认为是死锁）
                lock_time = datetime.fromtimestamp(self.lock_file.stat().st_mtime)
                if datetime.now() - lock_time < timedelta(minutes=10):
                    logger.info("任务处理器已在运行中，跳过本次执行")
                    return False
                else:
                    logger.warning("检测到过期的锁文件，清理并继续执行")
                    self.lock_file.unlink()
            
            # 创建锁文件
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file.write_text(str(os.getpid()))
            logger.info("获取任务处理锁成功")
            return True
            
        except Exception as e:
            logger.error(f"获取任务处理锁失败: {e}")
            return False
    
    def _release_lock(self):
        """释放处理锁"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.info("释放任务处理锁成功")
        except Exception as e:
            logger.error(f"释放任务处理锁失败: {e}")
    
    def create_pending_task(self, file_id: int, task_type: str, priority: int = 1) -> bool:
        """创建待处理任务（新方法，用于启动时）"""
        try:
            # 获取文件路径
            file = self.db.query(File).filter(File.id == file_id).first()
            if not file:
                logger.error(f"文件不存在: file_id={file_id}")
                return False
            
            return self.add_task(file_id, file.file_path, task_type, priority)
            
        except Exception as e:
            logger.error(f"创建待处理任务失败: {e}")
            return False
    
    def add_task(self, file_id: int, file_path: str, task_type: str, priority: int = 0) -> bool:
        """
        添加待处理任务（增强去重逻辑）
        
        Args:
            file_id: 文件ID
            file_path: 文件路径
            task_type: 任务类型
            priority: 优先级（数值越大优先级越高）
        
        Returns:
            bool: 是否成功添加任务
        """
        try:
            # 检查是否已存在相同的待处理任务（pending或processing状态）
            existing_task = self.db.query(PendingTask).filter(
                and_(
                    PendingTask.file_id == file_id,
                    PendingTask.task_type == task_type,
                    PendingTask.status.in_(["pending", "processing"])
                )
            ).first()
            
            if existing_task:
                # 如果新任务优先级更高，更新现有任务的优先级
                if priority > existing_task.priority:
                    existing_task.priority = priority
                    self.db.commit()
                    logger.info(f"更新现有任务优先级: file_id={file_id}, task_type={task_type}, 新优先级={priority}")
                else:
                    logger.info(f"任务已存在且优先级不低于新任务，跳过添加: file_id={file_id}, task_type={task_type}")
                return True
            
            # 创建新任务
            task = PendingTask(
                file_id=file_id,
                file_path=file_path,
                task_type=task_type,
                priority=priority,
                status="pending"
            )
            
            self.db.add(task)
            self.db.commit()
            
            logger.info(f"添加待处理任务成功: file_id={file_id}, task_type={task_type}, 优先级={priority}")
            return True
            
        except Exception as e:
            logger.error(f"添加待处理任务失败: {e}")
            self.db.rollback()
            return False
    
    def get_pending_tasks(self, limit: int = 10) -> List[PendingTask]:
        """获取待处理任务列表，按优先级和创建时间排序"""
        try:
            tasks = self.db.query(PendingTask).filter(
                PendingTask.status == "pending"
            ).order_by(
                PendingTask.priority.desc(),
                PendingTask.created_at.asc()
            ).limit(limit).all()
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取待处理任务失败: {e}")
            return []
    
    def process_task(self, task: PendingTask) -> bool:
        """处理单个任务"""
        try:
            # 更新任务状态为处理中
            task.status = "processing"
            task.updated_at = datetime.now()
            self.db.commit()
            
            logger.info(f"开始处理任务: {task.id}, file_path={task.file_path}, task_type={task.task_type}")
            
            # 获取文件信息
            file = self.db.query(File).filter(File.id == task.file_id).first()
            if not file:
                raise Exception(f"文件不存在: file_id={task.file_id}")
            
            success = False
            
            if task.task_type == "vector_index":
                # 处理向量索引任务
                success = self._process_vector_index_task(file)

            else:
                raise Exception(f"未知任务类型: {task.task_type}")
            
            if success:
                # 任务成功完成
                task.status = "completed"
                task.processed_at = datetime.now()
                task.error_message = None
                logger.info(f"任务处理成功: {task.id}")
            else:
                # 任务失败，准备重试
                task.retry_count += 1
                if task.retry_count >= task.max_retries:
                    task.status = "failed"
                    task.error_message = "超过最大重试次数"
                    logger.error(f"任务处理失败，超过最大重试次数: {task.id}")
                else:
                    task.status = "pending"
                    logger.warning(f"任务处理失败，将重试: {task.id}, 重试次数: {task.retry_count}")
            
            task.updated_at = datetime.now()
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"处理任务失败: {task.id}, 错误: {e}")
            
            # 更新任务状态
            task.retry_count += 1
            task.error_message = str(e)
            
            if task.retry_count >= task.max_retries:
                task.status = "failed"
            else:
                task.status = "pending"
            
            task.updated_at = datetime.now()
            self.db.commit()
            return False
    
    def _process_vector_index_task(self, file: File) -> bool:
        """处理向量索引任务"""
        try:
            ai_service = AIService(self.db)
            
            if not ai_service.is_available():
                logger.warning(f"AI服务不可用，跳过向量索引: {file.file_path}")
                return True  # 跳过但不算失败
            
            # 删除旧的向量索引
            ai_service.delete_document_by_file_path(file.file_path)
            
            # 创建新的向量索引
            success = ai_service.create_embeddings(file)
            
            if success:
                logger.info(f"向量索引处理成功: {file.file_path}")
            else:
                logger.error(f"向量索引处理失败: {file.file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理向量索引任务失败: {file.file_path}, 错误: {e}")
            return False
    

    
    def process_all_pending_tasks(self):
        """处理所有待处理任务"""
        if not self._acquire_lock():
            return
        
        try:
            self.is_running = True
            start_time = datetime.now()
            processed_count = 0
            success_count = 0
            
            logger.info("开始处理待处理任务队列")
            
            while True:
                # 获取一批待处理任务
                tasks = self.get_pending_tasks(limit=5)
                
                if not tasks:
                    logger.info("没有待处理任务，结束处理")
                    break
                
                # 处理每个任务
                for task in tasks:
                    if self.process_task(task):
                        success_count += 1
                    processed_count += 1
                    
                    # 检查是否运行时间过长（超过5分钟）
                    if datetime.now() - start_time > timedelta(minutes=5):
                        logger.warning("任务处理时间过长，暂停处理")
                        break
                
                # 短暂休息，避免过度占用资源
                time.sleep(0.1)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"任务处理完成，共处理 {processed_count} 个任务，成功 {success_count} 个，耗时 {duration:.2f} 秒")
            
        except Exception as e:
            logger.error(f"处理待处理任务队列失败: {e}")
        finally:
            self.is_running = False
            self._release_lock()
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧的已完成任务"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            deleted_count = self.db.query(PendingTask).filter(
                and_(
                    PendingTask.status.in_(["completed", "failed"]),
                    PendingTask.updated_at < cutoff_date
                )
            ).delete()
            
            self.db.commit()
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧任务记录")
            
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")
            self.db.rollback() 
    
    def clear_duplicate_pending_tasks(self) -> int:
        """
        清理重复的待处理任务
        对于相同file_id和task_type的pending任务，只保留优先级最高且最新的一个
        
        Returns:
            int: 清理的重复任务数量
        """
        try:
            # 查找重复任务组
            from sqlalchemy import text
            duplicate_groups = self.db.execute(text("""
                SELECT file_id, task_type, COUNT(*) as count
                FROM pending_tasks 
                WHERE status = 'pending'
                GROUP BY file_id, task_type
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            removed_count = 0
            
            for group in duplicate_groups:
                file_id = group.file_id
                task_type = group.task_type
                
                # 获取该组的所有任务，按优先级降序、创建时间降序排序
                tasks = self.db.query(PendingTask).filter(
                    and_(
                        PendingTask.file_id == file_id,
                        PendingTask.task_type == task_type,
                        PendingTask.status == "pending"
                    )
                ).order_by(
                    PendingTask.priority.desc(),
                    PendingTask.created_at.desc()
                ).all()
                
                if len(tasks) > 1:
                    # 保留第一个（优先级最高且最新的），删除其他的
                    keep_task = tasks[0]
                    tasks_to_remove = tasks[1:]
                    
                    for task in tasks_to_remove:
                        self.db.delete(task)
                        removed_count += 1
                    
                    logger.info(f"清理重复任务组: file_id={file_id}, task_type={task_type}, "
                              f"保留任务ID={keep_task.id}(优先级={keep_task.priority}), "
                              f"删除{len(tasks_to_remove)}个重复任务")
            
            self.db.commit()
            logger.info(f"清理重复任务完成，共删除 {removed_count} 个重复任务")
            return removed_count
            
        except Exception as e:
            logger.error(f"清理重复任务失败: {e}")
            self.db.rollback()
            return 0
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务队列统计信息"""
        try:
            from sqlalchemy import text
            stats = {}
            
            # 按状态统计
            status_stats = self.db.execute(text("""
                SELECT status, COUNT(*) as count
                FROM pending_tasks 
                GROUP BY status
            """)).fetchall()
            
            stats['by_status'] = {row.status: row.count for row in status_stats}
            
            # 按任务类型统计
            type_stats = self.db.execute(text("""
                SELECT task_type, COUNT(*) as count
                FROM pending_tasks 
                WHERE status = 'pending'
                GROUP BY task_type
            """)).fetchall()
            
            stats['by_type'] = {row.task_type: row.count for row in type_stats}
            
            # 重复任务统计
            duplicate_stats = self.db.execute(text("""
                SELECT file_id, task_type, COUNT(*) as count
                FROM pending_tasks 
                WHERE status = 'pending'
                GROUP BY file_id, task_type
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            stats['duplicates'] = len(duplicate_stats)
            stats['total_duplicate_tasks'] = sum(row.count - 1 for row in duplicate_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}