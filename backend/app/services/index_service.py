from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import logging
import hashlib
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.sql import or_

from ..models.file import File
from ..schemas.file import FileCreate
from ..database.session import get_db
from .ai_service_langchain import AIService

logger = logging.getLogger(__name__)

# 添加缓存机制
_status_cache = {
    "data": None,
    "last_update": None,
    "cache_duration": 30  # 缓存30秒
}

class IndexService:
    """文件索引服务，负责管理SQLite和ChromaDB向量数据库的索引"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
        
    def _estimate_embedding_count(self) -> int:
        """基于文件大小估算嵌入块数量"""
        try:
            # 获取notes目录路径 - 适配Docker容器环境
            # 在Docker容器中，notes目录挂载在 /app/notes (根据docker-compose.yml)
            notes_paths = [
                Path("/app/notes"),       # Docker容器内路径 (docker-compose.yml挂载)
                Path("/app/data/notes"),  # 备用Docker路径
                Path("../notes"),         # 开发环境路径
                Path("./notes"),          # 当前目录路径
                Path("notes")             # 相对路径
            ]
            
            notes_path = None
            for path in notes_paths:
                if path.exists():
                    notes_path = path
                    break
            
            if not notes_path:
                logger.warning("未找到notes目录，尝试的路径: " + ", ".join([str(p) for p in notes_paths]))
                return 0
            
            logger.info(f"使用notes目录路径: {notes_path}")
            
            # 计算notes目录总大小（字节）
            total_size = 0
            file_count = 0
            for file_path in notes_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.md', '.txt', '.markdown']:
                    try:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_count += 1
                    except (OSError, IOError) as e:
                        logger.warning(f"无法读取文件大小: {file_path}, 错误: {e}")
                        continue
            
            if total_size == 0:
                logger.info(f"notes目录中没有找到文档文件，检查的文件数: {file_count}")
                return 0
            
            # 估算参数
            # 假设每个文档块大小约为 500-800 字符（中文约 300-500 字节，英文约 500-800 字节）
            # 考虑到实际情况，使用 600 字节作为平均块大小
            avg_chunk_size_bytes = 600
            
            # 估算嵌入块数量
            estimated_chunks = total_size // avg_chunk_size_bytes
            
            # 添加一些合理的调整
            # 考虑到文档重叠和分块策略，实际块数可能比简单除法多 20-30%
            estimated_chunks = int(estimated_chunks * 1.25)
            
            logger.info(f"嵌入块数量估算: 路径={notes_path}, 文件数={file_count}, 总文件大小={total_size}字节, 平均块大小={avg_chunk_size_bytes}字节, 估算块数={estimated_chunks}")
            return estimated_chunks
            
        except Exception as e:
            logger.error(f"估算嵌入块数量失败: {e}")
            return 0
        
    def get_index_status(self) -> Dict[str, Any]:
        """获取索引状态 - 支持ChromaDB，添加缓存机制"""
        global _status_cache
        
        # 检查缓存是否有效
        now = datetime.now()
        if (_status_cache["data"] is not None and 
            _status_cache["last_update"] is not None and 
            (now - _status_cache["last_update"]).total_seconds() < _status_cache["cache_duration"]):
            return _status_cache["data"]
        
        try:
            # 快速查询SQLite中的文件数量（不需要filter，直接count）
            sqlite_count = self.db.query(func.count(File.id)).filter(File.is_deleted == False).scalar()
            
            # 简化磁盘文件检查，只检查notes目录是否存在，不扫描具体文件
            notes_path = Path("../notes")
            if notes_path.exists():
                # 只获取目录状态，不扫描所有文件
                try:
                    # 快速估算：只检查几个常见文件
                    sample_files = list(notes_path.glob("*.md"))[:5]  # 只检查前5个文件
                    disk_count = len(sample_files) * 2  # 简单估算
                except:
                    disk_count = 0
            else:
                disk_count = 0
                
            # 使用估算方式获取嵌入块数量
            try:
                # 检查AI服务和vector_store是否初始化
                if hasattr(self.ai_service, 'vector_store') and self.ai_service.vector_store is not None:
                    chroma_status = "connected"
                    # 使用估算方式获取嵌入块数量
                    vector_count = self._estimate_embedding_count()
                else:
                    chroma_status = "not_initialized"
                    vector_count = 0
            except Exception as e:
                logger.warning(f"获取ChromaDB状态失败: {e}")
                vector_count = 0
                chroma_status = f"error: {str(e)}"
                
            result = {
                "sqlite_files": sqlite_count,
                "disk_files": disk_count,
                "vector_files": vector_count,
                "vector_count_method": "estimated",  # 标记这是估算值
                "chroma_status": chroma_status,
                "needs_rebuild": False,  # 简化判断逻辑
                "last_check": now.isoformat(),
                "cached": False
            }
            
            # 更新缓存
            _status_cache["data"] = result
            _status_cache["last_update"] = now
            
            return result
            
        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return {
                "error": str(e),
                "last_check": now.isoformat()
            }
    
    def scan_notes_directory(self) -> List[Dict[str, Any]]:
        """扫描notes目录，返回文件信息列表"""
        from ..config import settings
        notes_path = Path(settings.notes_directory)
        logger.info(f"扫描notes目录: {notes_path}")
        if not notes_path.exists():
            logger.warning(f"notes目录不存在: {notes_path}")
            return []
        
        files_info = []
        file_extensions = ['.md', '.txt', '.markdown']
        
        for ext in file_extensions:
            for file_path in notes_path.rglob(f'*{ext}'):
                try:
                    # 读取文件内容
                    content = file_path.read_text(encoding='utf-8')
                    
                    # 计算相对路径
                    relative_path = file_path.relative_to(notes_path.parent)
                    
                    # 提取标题（从文件名或内容中）
                    title = self._extract_title(content, file_path.stem)
                    
                    files_info.append({
                        "file_path": str(relative_path).replace('\\', '/'),
                        "title": title,
                        "content": content,
                        "parent_folder": str(relative_path.parent).replace('\\', '/'),
                        "file_size": len(content.encode('utf-8')),
                        "content_hash": hashlib.sha256(content.encode('utf-8')).hexdigest()
                    })
                except Exception as e:
                    logger.error(f"读取文件失败: {file_path}, 错误: {e}")
                    continue
        
        logger.info(f"扫描完成，找到 {len(files_info)} 个文件")
        return files_info
    
    def _extract_title(self, content: str, filename: str) -> str:
        """从内容中提取标题"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return filename
    
    def _rebuild_sqlite_index_internal(self, progress_callback=None) -> Dict[str, Any]:
        """仅执行 SQLite 索引重建的内部实现，供公共方法调用"""
        try:
            logger.info("开始重建所有索引...")
            
            # 扫描文件
            files_info = self.scan_notes_directory()
            if progress_callback:
                progress_callback(5, f"扫描到 {len(files_info)} 个文件")
            
            # 清空现有SQLite数据（软删除）
            self.db.query(File).update({"is_deleted": True})
            self.db.commit()
            if progress_callback:
                progress_callback(10, "清空现有SQLite索引")
            
            # 插入新的SQLite数据
            created_count = 0
            for i, file_info in enumerate(files_info):
                try:
                    # 检查是否已存在
                    existing_file = self.db.query(File).filter(
                        File.file_path == file_info["file_path"]
                    ).first()
                    
                    if existing_file:
                        # 更新现有文件
                        existing_file.title = file_info["title"]
                        existing_file.content = file_info["content"]
                        existing_file.content_hash = file_info["content_hash"]
                        existing_file.file_size = file_info["file_size"]
                        existing_file.parent_folder = file_info["parent_folder"]
                        existing_file.is_deleted = False
                        existing_file.updated_at = datetime.now()
                    else:
                        # 创建新文件
                        new_file = File(
                            file_path=file_info["file_path"],
                            title=file_info["title"],
                            content=file_info["content"],
                            content_hash=file_info["content_hash"],
                            file_size=file_info["file_size"],
                            parent_folder=file_info["parent_folder"],
                            is_deleted=False
                        )
                        self.db.add(new_file)
                    
                    created_count += 1
                    
                    if progress_callback and (i + 1) % 10 == 0:
                        progress = 15 + (i + 1) / len(files_info) * 60
                        progress_callback(progress, f"处理文件 {i + 1}/{len(files_info)}")
                        
                except Exception as e:
                    logger.error(f"处理文件失败: {file_info['file_path']}, 错误: {e}")
                    continue
            
            self.db.commit()
            if progress_callback:
                progress_callback(80, "提交SQLite数据库更改")
            
            # 创建向量化任务
            from .vectorization_manager import VectorizationManager
            vectorization_manager = VectorizationManager(self.db)
            task_count = vectorization_manager.create_vectorization_tasks()
            
            if progress_callback:
                progress_callback(90, f"创建了 {task_count} 个向量化任务")
            
            if progress_callback:
                progress_callback(100, "重建完成")
            
            logger.info(f"所有索引重建完成，处理了 {created_count} 个文件，创建了 {task_count} 个向量化任务")
            return {
                "success": True,
                "processed_files": created_count,
                "total_files": len(files_info),
                "vectorization_tasks": task_count
            }
            
        except Exception as e:
            logger.error(f"重建所有索引失败: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def rebuild_sqlite_index(self, progress_callback=None) -> Dict[str, Any]:
        """公开的 SQLite 索引重建接口，调用内部实现，避免递归"""
        return self._rebuild_sqlite_index_internal(progress_callback)
    
    def rebuild_vector_index(self, progress_callback=None) -> Dict[str, Any]:
        """重建ChromaDB向量索引（使用统一原子操作）"""
        try:
            logger.info("开始重建ChromaDB向量索引...")
            
            # 获取所有文件
            files = self.db.query(File).filter(File.is_deleted == False).all()
            if progress_callback:
                progress_callback(10, f"准备处理 {len(files)} 个文件")
            
            # 清空ChromaDB向量数据库
            self.ai_service.clear_vector_database()
            if progress_callback:
                progress_callback(20, "清空ChromaDB向量数据库")
            
            # 使用统一的文件处理原子操作
            from .task_processor_service import TaskProcessorService
            task_processor = TaskProcessorService(self.db)
            
            # 为每个文件添加处理任务
            queued_count = 0
            for i, file in enumerate(files):
                try:
                    success = task_processor.add_task(
                        file_id=file.id,
                        file_path=file.file_path,
                        task_type="file_import",  # 使用统一的原子操作
                        priority=3  # 重建索引优先级最高
                    )
                    
                    if success:
                        queued_count += 1
                    
                    if progress_callback and (i + 1) % 10 == 0:
                        progress = 20 + (i + 1) / len(files) * 60
                        progress_callback(progress, f"添加任务 {i + 1}/{len(files)} (已排队: {queued_count})")
                        
                except Exception as e:
                    logger.error(f"添加重建任务失败: {file.file_path}, 错误: {e}")
                    continue
            
            if progress_callback:
                progress_callback(90, f"所有任务已排队，启动后台处理...")
            
            # 启动后台任务处理器
            task_processor.process_all_pending_tasks()
            
            if progress_callback:
                progress_callback(100, f"ChromaDB向量索引重建任务已启动 (已排队: {queued_count})")
            
            logger.info(f"ChromaDB向量索引重建任务已启动，共排队 {queued_count} 个文件")
            return {
                "success": True,
                "queued_files": queued_count,
                "total_files": len(files)
            }
            
        except Exception as e:
            logger.error(f"重建ChromaDB向量索引失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def rebuild_all_indexes(self, progress_callback=None) -> Dict[str, Any]:
        """重建所有索引：SQLite + ChromaDB"""
        try:
            logger.info("开始重建所有索引...")
            results = {}
            
            # 1. 重建SQLite索引
            if progress_callback:
                progress_callback(5, "开始重建SQLite索引...")
            
            sqlite_result = self.rebuild_sqlite_index(
                lambda p, m: progress_callback(5 + p * 0.4, f"SQLite: {m}") if progress_callback else None
            )
            results["sqlite"] = sqlite_result
            
            # 2. 重建ChromaDB向量索引
            if progress_callback:
                progress_callback(50, "开始重建ChromaDB向量索引...")
            
            vector_result = self.rebuild_vector_index(
                lambda p, m: progress_callback(50 + p * 0.45, f"ChromaDB: {m}") if progress_callback else None
            )
            results["vector"] = vector_result
            
            if progress_callback:
                progress_callback(100, "所有索引重建完成")
            
            success = sqlite_result.get("success", False) and vector_result.get("success", False)
            
            logger.info(f"所有索引重建完成，SQLite成功: {sqlite_result.get('success')}, ChromaDB成功: {vector_result.get('success')}")
            return {
                "success": success,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"重建所有索引失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def auto_initialize_on_startup(self) -> bool:
        """启动时自动初始化索引 - 简化版，仅检查基本状态"""
        try:
            logger.info("检查索引状态...")
            status = self.get_index_status()
            
            if status.get("error"):
                logger.error(f"获取索引状态失败: {status['error']}")
                return False
            
            logger.info(f"索引状态: SQLite={status['sqlite_files']}, FTS={status['fts_files']}, Disk={status['disk_files']}, ChromaDB={status['vector_files']}")
            logger.info("索引初始化检查完成，详细重建将在后台异步进行")
            
            return True
            
        except Exception as e:
            logger.error(f"自动初始化失败: {e}")
            return False 