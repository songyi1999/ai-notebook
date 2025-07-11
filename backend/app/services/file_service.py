from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional
from pathlib import Path
import hashlib
import logging

from ..models.file import File
from ..schemas.file import FileCreate, FileUpdate

logger = logging.getLogger(__name__)

from ..services.base_service import BaseService

class FileService(BaseService):

    def _calculate_content_hash(self, content: str) -> str:
        """计算内容的SHA256哈希值"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _write_file_to_disk(self, file_path: str, content: str) -> bool:
        """将文件内容写入磁盘"""
        try:
            path = Path(file_path)
            # 确保父目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            # 写入文件
            path.write_text(content, encoding='utf-8')
            logger.info(f"文件写入磁盘成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"文件写入磁盘失败: {file_path}, 错误: {e}")
            return False

    def _read_file_from_disk(self, file_path: str) -> Optional[str]:
        """从磁盘读取文件内容"""
        try:
            path = Path(file_path)
            if path.exists():
                content = path.read_text(encoding='utf-8')
                logger.info(f"文件从磁盘读取成功: {file_path}")
                return content
            return None
        except Exception as e:
            logger.error(f"文件从磁盘读取失败: {file_path}, 错误: {e}")
            return None

    def create_file(self, file: FileCreate, fast_mode: bool = True) -> File:
        """创建文件（同时写入数据库和磁盘）
        
        Args:
            file: 文件创建数据
            fast_mode: 快速模式，先保存文件和基本信息，向量索引等后台处理
        """
        try:
            # 计算内容哈希
            content_hash = self._calculate_content_hash(file.content)
            
            # 获取文件大小
            file_size = len(file.content.encode('utf-8'))
            
            # 创建数据库记录
            db_file = File(
                file_path=file.file_path,
                title=file.title,
                content=file.content,
                content_hash=content_hash,
                file_size=file_size,
                parent_folder=file.parent_folder,
                file_metadata=file.file_metadata
            )
            
            self.db.add(db_file)
            self.db.commit()
            self.db.refresh(db_file)
            
            # 写入磁盘
            if not self._write_file_to_disk(file.file_path, file.content):
                # 如果磁盘写入失败，回滚数据库操作
                self.db.delete(db_file)
                self.db.commit()
                raise Exception("文件写入磁盘失败")
            
            # 根据模式处理向量索引
            if fast_mode:
                # 快速模式：将向量索引任务加入后台队列
                logger.info(f"文件创建成功，添加向量索引任务到队列: {file.file_path}")
                self._add_vector_index_task(db_file)
            else:
                # 同步模式：立即创建向量索引
                logger.info(f"文件创建成功，开始创建向量索引: {file.file_path}")
                self._create_vector_index_sync(db_file)
            
            logger.info(f"文件创建成功: {file.file_path}")
            return db_file
        except Exception as e:
            logger.error(f"文件创建失败: {e}")
            self.db.rollback()
            raise
    
    def _create_vector_index_sync(self, file: File):
        """同步创建向量索引（使用统一原子操作）"""
        try:
            # 使用统一的文件处理原子操作
            self._add_vector_index_task(file)
            logger.info(f"向量索引创建任务已添加到队列: {file.file_path}")
        except Exception as e:
            logger.error(f"添加向量索引创建任务失败: {file.file_path}, 错误: {e}")
            # 任务添加失败不应该影响文件创建，所以不抛出异常

    def get_file(self, file_id: int) -> Optional[File]:
        return self.db.query(File).filter(File.id == file_id, File.is_deleted == False).first()

    def get_file_by_path(self, file_path: str) -> Optional[File]:
        """根据路径获取文件，如果数据库中没有则尝试从磁盘读取"""
        db_file = self.db.query(File).filter(File.file_path == file_path, File.is_deleted == False).first()
        
        if db_file:
            return db_file
        
        # 检查是否有软删除的记录
        deleted_file = self.db.query(File).filter(File.file_path == file_path, File.is_deleted == True).first()
        if deleted_file:
            # 如果有软删除的记录，先硬删除它
            logger.info(f"发现软删除记录，先清理: {file_path}")
            self.db.delete(deleted_file)
            self.db.commit()
        
        # 如果数据库中没有，尝试从磁盘读取
        content = self._read_file_from_disk(file_path)
        if content:
            # 从文件路径提取标题
            title = Path(file_path).stem
            parent_folder = str(Path(file_path).parent)
            
            # 创建文件记录
            file_create = FileCreate(
                file_path=file_path,
                title=title,
                content=content,
                parent_folder=parent_folder
            )
            return self.create_file(file_create)
        
        return None

    def get_files(self, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[File]:
        query = self.db.query(File)
        if not include_deleted:
            query = query.filter(File.is_deleted == False)
        return query.offset(skip).limit(limit).all()

    def update_file(self, file_id: int, file_update: FileUpdate, fast_mode: bool = True) -> Optional[File]:
        """更新文件
        
        Args:
            file_id: 文件ID
            file_update: 更新数据
            fast_mode: 快速模式，先保存文件和基本信息，向量索引等后台处理
        """
        try:
            db_file = self.get_file(file_id)
            if not db_file:
                return None
            
            # 更新数据库字段
            update_data = file_update.dict(exclude_unset=True)
            
            # 检查内容是否有变化
            content_changed = False
            if 'content' in update_data:
                new_content_hash = self._calculate_content_hash(update_data['content'])
                content_changed = new_content_hash != db_file.content_hash
                
                if content_changed:
                    update_data['content_hash'] = new_content_hash
                    update_data['file_size'] = len(update_data['content'].encode('utf-8'))
                    
                    # 写入磁盘
                    if not self._write_file_to_disk(db_file.file_path, update_data['content']):
                        raise Exception("文件写入磁盘失败")
            
            # 手动设置更新时间，避免SQLAlchemy时间戳问题
            from datetime import datetime
            update_data['updated_at'] = datetime.now()
            
            for key, value in update_data.items():
                setattr(db_file, key, value)
            
            # 先提交数据库更改（FTS索引会通过触发器自动更新）
            self.db.commit()
            self.db.refresh(db_file)
            
            # 如果内容有变化，根据模式处理向量索引
            if content_changed:
                if fast_mode:
                    # 快速模式：将向量索引任务加入后台队列
                    logger.info(f"文件内容已变化，添加向量索引任务到队列: {db_file.file_path}")
                    self._add_vector_index_task(db_file)
                else:
                    # 同步模式：立即更新向量索引
                    logger.info(f"文件内容已变化，开始更新向量索引: {db_file.file_path}")
                    self._update_vector_index_async(db_file)
            
            logger.info(f"文件更新成功: {db_file.file_path}")
            return db_file
        except Exception as e:
            logger.error(f"文件更新失败: {e}")
            self.db.rollback()
            raise
    
    def _add_vector_index_task(self, file: File):
        """将文件处理任务添加到后台队列（统一原子操作）"""
        try:
            from .task_processor_service import TaskProcessorService
            task_processor = TaskProcessorService(self.db)
            
            # 添加文件导入任务（统一原子操作：入库+向量化）
            success = task_processor.add_task(
                file_id=file.id,
                file_path=file.file_path,
                task_type="file_import",  # 使用统一的原子操作
                priority=1  # 普通优先级
            )
            
            if success:
                logger.info(f"向量索引任务添加成功: {file.file_path}")
                
                # 检查索引进程是否在运行，如果没有运行则启动
                self._ensure_task_processor_running(task_processor)
                
            else:
                logger.error(f"向量索引任务添加失败: {file.file_path}")
                
        except Exception as e:
            logger.error(f"添加向量索引任务失败: {file.file_path}, 错误: {e}")
            # 任务添加失败不应该影响文件保存，所以不抛出异常

    def _ensure_task_processor_running(self, task_processor):
        """确保任务处理器正在运行，如果没有运行则启动"""
        try:
            # 检查是否有锁文件存在（表示有进程在运行）
            if task_processor.lock_file.exists():
                from datetime import datetime, timedelta
                # 检查锁文件是否过期（超过10分钟认为是死锁）
                lock_time = datetime.fromtimestamp(task_processor.lock_file.stat().st_mtime)
                if datetime.now() - lock_time < timedelta(minutes=10):
                    logger.debug("任务处理器已在运行中，无需启动新进程")
                    return
                else:
                    logger.warning("检测到过期的锁文件，将启动新的任务处理器")
            
            # 没有运行中的任务处理器，启动一个新的后台线程来处理任务
            import threading
            
            def background_task_processor():
                try:
                    # 创建新的数据库会话（避免线程间共享）
                    from ..database.session import SessionLocal
                    from .task_processor_service import TaskProcessorService
                    
                    bg_db = SessionLocal()
                    try:
                        bg_task_processor = TaskProcessorService(bg_db)
                        logger.info("启动后台任务处理器...")
                        bg_task_processor.process_all_pending_tasks()
                        logger.info("后台任务处理器执行完成")
                    finally:
                        bg_db.close()
                except Exception as e:
                    logger.error(f"后台任务处理器执行失败: {e}")
            
            # 启动后台线程（daemon=True 确保主进程退出时线程也会退出）
            background_thread = threading.Thread(target=background_task_processor, daemon=True)
            background_thread.start()
            logger.info("后台任务处理器线程已启动")
            
        except Exception as e:
            logger.error(f"启动任务处理器失败: {e}")
            # 启动失败不应该影响文件保存，所以不抛出异常

    def _update_vector_index_async(self, file: File):
        """异步更新向量索引（使用统一原子操作）"""
        try:
            # 使用统一的文件处理原子操作
            self._add_vector_index_task(file)
            logger.info(f"向量索引更新任务已添加到队列: {file.file_path}")
        except Exception as e:
            logger.error(f"添加向量索引更新任务失败: {file.file_path}, 错误: {e}")
            # 任务添加失败不应该影响文件保存，所以不抛出异常

    def delete_file(self, file_id: int) -> Optional[File]:
        db_file = self.get_file(file_id)
        if not db_file:
            return None
        db_file.is_deleted = True # 软删除
        self.db.commit()
        self.db.refresh(db_file)
        return db_file

    def hard_delete_file(self, file_id: int) -> Optional[File]:
        db_file = self.db.query(File).filter(File.id == file_id).first()
        if not db_file:
            return None
        self.db.delete(db_file)
        self.db.commit()
        return db_file
    
    def delete_file_completely(self, file_id: int, delete_physical: bool = True) -> Optional[File]:
        """完整删除文件（数据库记录 + 物理文件 + 向量索引）"""
        try:
            db_file = self.db.query(File).filter(File.id == file_id).first()
            if not db_file:
                return None
            
            file_path = db_file.file_path
            
            # 1. 手动删除相关的embedding记录（避免外键约束问题）
            try:
                from ..models.embedding import Embedding
                embeddings_count = self.db.query(Embedding).filter(Embedding.file_id == file_id).count()
                if embeddings_count > 0:
                    self.db.query(Embedding).filter(Embedding.file_id == file_id).delete()
                    logger.info(f"删除了 {embeddings_count} 个embedding记录: {file_path}")
            except Exception as e:
                logger.warning(f"删除embedding记录失败: {e}")
            
            # 2. 删除数据库记录
            self.db.delete(db_file)
            self.db.commit()
            logger.info(f"数据库记录删除成功: {file_path}")
            
            # 3. 删除物理文件
            if delete_physical:
                try:
                    from pathlib import Path
                    physical_path = Path(file_path)
                    if physical_path.exists():
                        physical_path.unlink()
                        logger.info(f"物理文件删除成功: {file_path}")
                    else:
                        logger.warning(f"物理文件不存在: {file_path}")
                except Exception as e:
                    logger.error(f"删除物理文件失败: {file_path}, 错误: {e}")
                    # 物理文件删除失败不回滚数据库操作
            
            return db_file
        except Exception as e:
            logger.error(f"完整删除文件失败: {e}")
            self.db.rollback()
            raise
    
    def rename_file(self, old_path: str, new_path: str) -> bool:
        """重命名文件（同时更新数据库记录和物理文件）"""
        try:
            from pathlib import Path
            import shutil
            
            old_physical_path = Path(old_path)
            new_physical_path = Path(new_path)
            
            # 检查源文件是否存在
            if not old_physical_path.exists():
                raise Exception(f"源文件不存在: {old_path}")
            
            # 检查目标路径是否已存在
            if new_physical_path.exists():
                raise Exception(f"目标路径已存在: {new_path}")
            
            # 确保目标目录存在
            new_physical_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 1. 更新数据库记录
            db_file = self.db.query(File).filter(File.file_path == old_path, File.is_deleted == False).first()
            if db_file:
                # 更新文件路径
                db_file.file_path = new_path
                
                # 从新路径提取标题
                new_title = new_physical_path.stem
                db_file.title = new_title
                
                # 更新父文件夹
                db_file.parent_folder = str(new_physical_path.parent)
                
                # 更新时间戳
                from datetime import datetime
                db_file.updated_at = datetime.now()
                
                self.db.commit()
                logger.info(f"数据库记录重命名成功: {old_path} -> {new_path}")
            
            # 2. 移动物理文件
            shutil.move(str(old_physical_path), str(new_physical_path))
            logger.info(f"物理文件重命名成功: {old_path} -> {new_path}")
            
            # 3. 更新向量索引中的文件路径信息
            if db_file:
                try:
                    from .ai_service_langchain import AIService
                    ai_service = AIService(self.db)
                    success = ai_service.update_file_path_in_vectors(
                        file_id=db_file.id,
                        old_path=old_path,
                        new_path=new_path,
                        new_title=new_title
                    )
                    if success:
                        logger.info(f"向量索引路径更新成功: {old_path} -> {new_path}")
                    else:
                        logger.warning(f"向量索引路径更新失败: {old_path} -> {new_path}")
                except Exception as e:
                    logger.error(f"更新向量索引路径时出错: {e}")
                    # 不抛出异常，因为文件重命名本身已成功
            
            return True
            
        except Exception as e:
            logger.error(f"重命名文件失败: {e}")
            self.db.rollback()
            raise

    def search_files(self, query_str: str, skip: int = 0, limit: int = 100) -> List[File]:
        """使用LIKE进行关键词搜索"""
        try:
            search_pattern = f"%{query_str}%"
            results = self.db.query(File).filter(
                or_(
                    File.title.like(search_pattern),
                    File.content.like(search_pattern)
                ),
                File.is_deleted == False
            ).limit(limit).all()
            
            logger.info(f"关键词搜索完成，查询: {query_str}, 结果数: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return [] 