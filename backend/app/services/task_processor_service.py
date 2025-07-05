import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from pathlib import Path

from ..models.pending_task import PendingTask
from ..models.file import File
from ..database.session import get_db
from .ai_service_langchain import AIService
from .index_service import IndexService

logger = logging.getLogger(__name__)

# 添加任务统计缓存
_task_stats_cache = {
    "data": None,
    "last_update": None,
    "cache_duration": 15  # 缓存15秒
}

class TaskProcessorService:
    """后台任务处理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.lock_file = Path("data/task_processor.lock")
        self.is_running = False
        
        # 不在初始化时自动清理锁文件，避免误清理正在运行的任务处理器
    
    def _cleanup_stale_lock_on_startup(self):
        """
        容器启动时清理过期的锁文件
        
        在Docker容器中，上次运行的锁文件可能会因为卷挂载而持久化，
        但锁文件中的PID在新容器中可能被其他进程占用，导致误判。
        因此在启动时应该清理过期的锁文件。
        """
        try:
            if self.lock_file.exists():
                # 读取锁文件中的PID
                try:
                    lock_pid = int(self.lock_file.read_text().strip())
                    
                    # 在Docker容器启动场景下，任何现有的锁文件都应该被清理
                    # 因为真正的任务处理器进程不会在容器启动时就存在
                    logger.info(f"容器启动时发现过期锁文件(PID: {lock_pid})，清理中...")
                    self.lock_file.unlink()
                    logger.info("过期锁文件已清理")
                    
                except (ValueError, IOError) as e:
                    logger.warning(f"锁文件格式错误，清理中: {e}")
                    self.lock_file.unlink()
                    logger.info("格式错误的锁文件已清理")
                    
        except Exception as e:
            logger.error(f"清理启动锁文件失败: {e}")
        
    def _acquire_lock(self) -> bool:
        """获取处理锁，防止重复执行"""
        try:
            if self.lock_file.exists():
                # 读取锁文件中的PID
                try:
                    lock_pid = int(self.lock_file.read_text().strip())
                    
                    # 检查进程是否还在运行
                    if self._is_process_running(lock_pid):
                        logger.info(f"任务处理器已在运行中(PID: {lock_pid})，跳过本次执行")
                        return False
                    else:
                        logger.warning(f"发现死锁文件(PID: {lock_pid}已退出)，清理并继续执行")
                        self.lock_file.unlink()
                except (ValueError, IOError) as e:
                    logger.warning(f"锁文件格式错误，清理并继续: {e}")
                    self.lock_file.unlink()
            
            # 创建锁文件
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            current_pid = os.getpid()
            self.lock_file.write_text(str(current_pid))
            logger.info(f"获取任务处理锁成功(PID: {current_pid})")
            return True
            
        except Exception as e:
            logger.error(f"获取任务处理锁失败: {e}")
            return False
    
    def _is_task_processor_running(self, pid: int) -> bool:
        """
        检查指定PID是否是正在运行的任务处理器进程
        
        改进的检查逻辑：
        1. 检查进程是否存在
        2. 检查进程是否是Python进程
        3. 检查进程命令行是否包含任务处理器相关信息
        """
        try:
            import psutil
            
            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                return False
            
            # 获取进程信息
            try:
                process = psutil.Process(pid)
                
                # 检查是否是Python进程
                if 'python' not in process.name().lower():
                    logger.debug(f"PID {pid} 不是Python进程: {process.name()}")
                    return False
                
                # 检查命令行参数，看是否包含任务处理器相关信息
                cmdline = ' '.join(process.cmdline())
                if 'task_processor' in cmdline.lower() or 'TaskProcessorService' in cmdline:
                    logger.debug(f"PID {pid} 确实是任务处理器进程")
                    return True
                else:
                    logger.debug(f"PID {pid} 是Python进程但不是任务处理器: {cmdline}")
                    return False
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
                
        except ImportError:
            # 如果没有psutil，使用保守的检查方式
            try:
                import signal
                # 发送0信号检查进程是否存在
                os.kill(pid, 0)
                # 在没有psutil的情况下，假设进程存在但不确定是否是任务处理器
                # 为了避免误判，返回False，让锁文件被清理
                logger.debug(f"无法确定PID {pid} 是否是任务处理器，清理锁文件")
                return False
            except (OSError, ProcessLookupError):
                return False
        except Exception as e:
            # 如果检查失败，为了安全起见清理锁文件
            logger.debug(f"检查任务处理器进程失败: {e}，清理锁文件")
            return False
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否正在运行（保留原方法以兼容其他地方的调用）"""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            # 如果没有psutil，使用系统方法检查
            try:
                import signal
                # 发送0信号检查进程是否存在
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False
        except Exception:
            # 如果检查失败，为了安全起见假设进程还在运行
            return True
    
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
            
            success = False
            
            if task.task_type == "vector_index":
                # 处理向量索引任务（兼容旧任务）- 需要先查找文件
                file = self.db.query(File).filter(File.id == task.file_id).first()
                if not file:
                    raise Exception(f"文件不存在: file_id={task.file_id}")
                success = self._process_vector_index_task(file)
            elif task.task_type == "file_import":
                # 处理文件导入任务（统一原子操作：入库+向量化）- 不需要预先查找文件
                success = self._process_file_import_task(task)
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
            
            # 创建或更新向量索引
            # 注意：create_embeddings 方法内部会自动处理现有索引的清理
            success = ai_service.create_embeddings(file)
            
            if success:
                logger.info(f"向量索引处理成功: {file.file_path}")
            else:
                logger.error(f"向量索引处理失败: {file.file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理向量索引任务失败: {file.file_path}, 错误: {e}")
            return False
    
    def _process_file_import_task(self, task: PendingTask) -> bool:
        """
        处理文件导入任务（入库+向量化）
        这是一个原子操作，包含：
        1. 读取文件内容
        2. 创建数据库记录
        3. 智能多层次向量分块
        
        统一入口点：所有文件处理场景都应该使用这个原子操作
        - 文件上传后处理
        - 文件修改后更新
        - 系统启动时扫描
        - 重建索引时处理
        """
        try:
            from pathlib import Path
            from ..models.file import File
            from ..schemas.file import FileCreate
            from .ai_service_langchain import AIService
            import hashlib
            
            # 获取当前任务队列状态
            pending_count = self._get_pending_tasks_count()
            logger.info(f"📋 开始处理文件导入任务: {task.file_path} (待处理任务: {pending_count})")
            
            # 1. 读取文件内容
            # 智能处理路径：如果task.file_path已包含notes前缀则直接使用，否则添加
            if task.file_path.startswith("notes/") or task.file_path.startswith("./notes/"):
                # 已包含完整路径，直接使用
                file_path = Path(task.file_path)
            else:
                # 相对路径，需要添加notes前缀
                file_path = Path("./notes") / task.file_path
            
            if not file_path.exists():
                raise Exception(f"文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"📖 文件内容读取完成: {task.file_path} (大小: {len(content)}字符)")
            
            # 2. 计算文件哈希
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # 3. 检查是否已存在相同的文件记录
            # 确保查询时使用标准化的路径格式
            normalized_path = task.file_path
            if not normalized_path.startswith("notes/"):
                normalized_path = f"notes/{normalized_path}"
            
            existing_file = self.db.query(File).filter(
                File.file_path == normalized_path,
                File.is_deleted == False
            ).first()
            
            if existing_file:
                # 如果文件已存在，检查内容是否有变化
                if existing_file.content_hash == content_hash:
                    logger.info(f"✅ 文件内容未变化，跳过导入: {normalized_path}")
                    return True
                else:
                    # 内容有变化，更新记录
                    existing_file.content = content
                    existing_file.content_hash = content_hash
                    existing_file.file_size = len(content.encode('utf-8'))
                    existing_file.updated_at = datetime.now()
                    db_file = existing_file
                    logger.info(f"🔄 更新现有文件记录: {normalized_path}")
            else:
                # 创建新的文件记录
                title = Path(task.file_path).stem
                
                # 确保数据库中存储的路径格式一致（始终包含notes前缀）
                normalized_path = task.file_path
                if not normalized_path.startswith("notes/"):
                    normalized_path = f"notes/{normalized_path}"
                
                db_file = File(
                    file_path=normalized_path,
                    title=title,
                    content=content,
                    content_hash=content_hash,
                    file_size=len(content.encode('utf-8')),
                    is_deleted=False
                )
                self.db.add(db_file)
                logger.info(f"📝 创建新文件记录: {normalized_path}")
            
            # 4. 提交数据库事务
            self.db.commit()
            self.db.refresh(db_file)
            logger.info(f"💾 数据库记录保存成功: {normalized_path}")
            
            # 5. 开始智能多层次向量分块
            ai_service = AIService(self.db)
            if ai_service.is_available():
                logger.info(f"🤖 开始智能多层次向量分块: {normalized_path}")
                
                # 调用智能分块，并传递进度回调
                vector_success = ai_service.create_embeddings(
                    db_file, 
                    progress_callback=lambda step, message: self._log_chunking_progress(
                        normalized_path, step, message
                    )
                )
                
                if vector_success:
                    # 获取最新的任务队列状态
                    remaining_count = self._get_pending_tasks_count()
                    logger.info(f"🎉 文件处理完全成功: {normalized_path} | 剩余任务: {remaining_count}")
                else:
                    logger.error(f"❌ 向量索引创建失败: {normalized_path}")
                    return False
            else:
                logger.warning(f"⚠️ AI服务不可用，跳过向量索引: {normalized_path}")
            
            return True
            
        except Exception as e:
            # 尝试获取标准化路径用于错误日志
            try:
                normalized_path = task.file_path
                if not normalized_path.startswith("notes/"):
                    normalized_path = f"notes/{normalized_path}"
                logger.error(f"💥 文件导入任务失败: {normalized_path}, 错误: {e}")
            except:
                logger.error(f"💥 文件导入任务失败: {task.file_path}, 错误: {e}")
            self.db.rollback()
            return False
    
    def _get_pending_tasks_count(self) -> int:
        """获取待处理任务数量"""
        try:
            return self.db.query(PendingTask).filter(
                PendingTask.status == "pending"
            ).count()
        except Exception:
            return 0
    
    def _log_chunking_progress(self, file_path: str, step: str, message: str):
        """记录分块进度"""
        remaining_count = self._get_pending_tasks_count()
        logger.info(f"🔧 [{step}] {message} | 文件: {file_path} | 剩余任务: {remaining_count}")
    
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
                    task_start_time = datetime.now()
                    logger.info(f"🚀 开始处理任务: {task.id}, 文件: {task.file_path}, 类型: {task.task_type}")
                    
                    try:
                        if self.process_task(task):
                            success_count += 1
                            task_duration = (datetime.now() - task_start_time).total_seconds()
                            logger.info(f"✅ 任务处理成功: {task.id}, 耗时: {task_duration:.2f}秒")
                        else:
                            task_duration = (datetime.now() - task_start_time).total_seconds()
                            logger.error(f"❌ 任务处理失败: {task.id}, 耗时: {task_duration:.2f}秒")
                    except Exception as e:
                        task_duration = (datetime.now() - task_start_time).total_seconds()
                        logger.error(f"💥 任务处理异常: {task.id}, 耗时: {task_duration:.2f}秒, 错误: {e}")
                    
                    processed_count += 1
                    
                    # 检查是否运行时间过长（增加到15分钟）
                    total_duration = (datetime.now() - start_time).total_seconds()
                    if total_duration > 900:  # 15分钟 = 900秒
                        logger.warning(f"任务处理时间过长({total_duration:.1f}秒)，暂停处理以避免阻塞")
                        break
                    
                    # 检查单个任务是否超时（5分钟）
                    if task_duration > 300:  # 5分钟 = 300秒
                        logger.warning(f"⏰ 单个任务处理超时: {task.id}, 耗时: {task_duration:.2f}秒")
                
                # 短暂休息，避免过度占用资源
                time.sleep(0.1)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"🎉 任务处理完成，共处理 {processed_count} 个任务，成功 {success_count} 个，耗时 {duration:.2f} 秒")
            
        except Exception as e:
            logger.error(f"💥 处理待处理任务队列失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
        finally:
            self.is_running = False
            self._release_lock()
            logger.info("🔓 任务处理器已释放锁并停止")
    
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
            # 检查缓存是否过期
            if _task_stats_cache["data"] and datetime.now() - _task_stats_cache["last_update"] < timedelta(seconds=_task_stats_cache["cache_duration"]):
                return _task_stats_cache["data"]
            
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
            
            # 更新缓存
            _task_stats_cache["data"] = stats
            _task_stats_cache["last_update"] = datetime.now()
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}
    
    def get_processor_status(self) -> Dict[str, Any]:
        """获取任务处理器运行状态"""
        try:
            # 检查是否有待处理任务
            pending_count = self._get_pending_tasks_count()
            
            # 检查锁文件
            if not self.lock_file.exists():
                if pending_count > 0:
                    return {
                        "running": False,
                        "pid": None,
                        "status": "idle",
                        "message": f"任务处理器空闲中，有 {pending_count} 个待处理任务",
                        "pending_tasks": pending_count
                    }
                else:
                    return {
                        "running": False,
                        "pid": None,
                        "status": "idle",
                        "message": "任务处理器空闲中，暂无待处理任务",
                        "pending_tasks": 0
                    }
            
            # 读取锁文件中的PID
            try:
                with open(self.lock_file, 'r') as f:
                    pid_str = f.read().strip()
                    if not pid_str:
                        # 空锁文件，清理并返回空闲状态
                        self.lock_file.unlink()
                        return {
                            "running": False,
                            "pid": None,
                            "status": "idle",
                            "message": "锁文件损坏已清理，任务处理器空闲中",
                            "pending_tasks": pending_count
                        }
                    
                    pid = int(pid_str)
                    
                    # 检查进程是否真的在运行
                    if self._is_process_running(pid):
                        # 进程还在运行，假设是任务处理器（保守策略）
                        return {
                            "running": True,
                            "pid": pid,
                            "status": "running",
                            "message": f"任务处理器正在运行 (PID: {pid})",
                            "pending_tasks": pending_count
                        }
                    else:
                        # 进程确实已死，安全清理锁文件
                        logger.info(f"检测到死锁文件(PID: {pid}已退出)，清理锁文件")
                        self.lock_file.unlink()
                        return {
                            "running": False,
                            "pid": None,
                            "status": "idle",
                            "message": "任务处理器进程已停止，现在空闲中",
                            "pending_tasks": pending_count
                        }
                        
            except (ValueError, OSError) as e:
                # 锁文件格式错误或读取失败
                logger.error(f"读取锁文件失败: {e}")
                try:
                    self.lock_file.unlink()
                except:
                    pass
                return {
                    "running": False,
                    "pid": None,
                    "status": "error",
                    "message": f"锁文件读取失败: {e}",
                    "pending_tasks": pending_count
                }
                
        except Exception as e:
            logger.error(f"获取任务处理器状态失败: {e}")
            return {
                "running": False,
                "pid": None,
                "status": "error",
                "message": f"状态检查失败: {e}",
                "pending_tasks": 0
            }
    
    def start_processor(self, force: bool = False) -> Dict[str, Any]:
        """手动启动任务处理器"""
        try:
            # 检查当前状态
            current_status = self.get_processor_status()
            
            if current_status["running"] and not force:
                return {
                    "success": False,
                    "message": f"任务处理器已在运行中 (PID: {current_status['pid']})",
                    "status": current_status
                }
            
            # 如果force=True，先清理可能的死锁
            if force:
                logger.info("🧹 强制启动，清理可能的死锁文件")
                self._release_lock()
            
            # 启动处理器
            logger.info("🚀 手动启动任务处理器")
            self.process_all_pending_tasks()
            
            return {
                "success": True,
                "message": "任务处理器启动成功",
                "status": self.get_processor_status()
            }
            
        except Exception as e:
            logger.error(f"启动任务处理器失败: {e}")
            return {
                "success": False,
                "message": f"启动失败: {e}",
                "status": self.get_processor_status()
            }
    
    def stop_processor(self) -> Dict[str, Any]:
        """停止任务处理器（通过删除锁文件）"""
        try:
            current_status = self.get_processor_status()
            
            if not current_status["running"]:
                return {
                    "success": False,
                    "message": "任务处理器未运行",
                    "status": current_status
                }
            
            # 删除锁文件来停止处理器
            self._release_lock()
            
            logger.info("🛑 手动停止任务处理器")
            
            return {
                "success": True,
                "message": "任务处理器停止信号已发送",
                "status": self.get_processor_status()
            }
            
        except Exception as e:
            logger.error(f"停止任务处理器失败: {e}")
            return {
                "success": False,
                "message": f"停止失败: {e}",
                "status": self.get_processor_status()
            }