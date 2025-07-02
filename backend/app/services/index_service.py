from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import logging
import hashlib
from datetime import datetime
import asyncio

from ..models.file import File
from ..schemas.file import FileCreate
from ..database.session import get_db
from .ai_service_langchain import AIService

logger = logging.getLogger(__name__)

class IndexService:
    """文件索引服务，负责管理SQLite和ChromaDB向量数据库的索引"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
        
    def get_index_status(self) -> Dict[str, Any]:
        """获取索引状态 - 支持ChromaDB"""
        try:
            # 检查SQLite中的文件数量
            sqlite_count = self.db.query(File).filter(File.is_deleted == False).count()
            
            # 检查FTS表中的文件数量
            fts_result = self.db.execute(text("SELECT COUNT(*) FROM files_fts")).fetchone()
            fts_count = fts_result[0] if fts_result else 0
            
            # 检查notes目录中的文件数量
            notes_path = Path("../notes")
            if notes_path.exists():
                file_extensions = ['.md', '.txt', '.markdown']
                disk_files = []
                for ext in file_extensions:
                    disk_files.extend(notes_path.rglob(f'*{ext}'))
                disk_count = len(disk_files)
            else:
                disk_count = 0
                
            # 检查ChromaDB向量数据库状态
            try:
                vector_count = self.ai_service.get_vector_count()
                chroma_status = "connected"
            except Exception as e:
                logger.warning(f"获取ChromaDB状态失败: {e}")
                vector_count = 0
                chroma_status = f"error: {str(e)}"
                
            return {
                "sqlite_files": sqlite_count,
                "fts_files": fts_count,
                "disk_files": disk_count,
                "vector_files": vector_count,
                "chroma_status": chroma_status,
                "needs_rebuild": sqlite_count != disk_count or fts_count != sqlite_count,
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return {
                "error": str(e),
                "last_check": datetime.now().isoformat()
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
    
    def rebuild_sqlite_index(self, progress_callback=None) -> Dict[str, Any]:
        """重建SQLite索引"""
        try:
            logger.info("开始重建SQLite索引...")
            
            # 扫描文件
            files_info = self.scan_notes_directory()
            if progress_callback:
                progress_callback(10, f"扫描到 {len(files_info)} 个文件")
            
            # 清空现有数据（软删除）
            self.db.query(File).update({"is_deleted": True})
            self.db.commit()
            if progress_callback:
                progress_callback(20, "清空现有索引")
            
            # 重建FTS表
            self._rebuild_fts_table()
            if progress_callback:
                progress_callback(30, "重建FTS表")
            
            # 插入新数据
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
                        progress = 30 + (i + 1) / len(files_info) * 60
                        progress_callback(progress, f"处理文件 {i + 1}/{len(files_info)}")
                        
                except Exception as e:
                    logger.error(f"处理文件失败: {file_info['file_path']}, 错误: {e}")
                    continue
            
            self.db.commit()
            if progress_callback:
                progress_callback(95, "提交数据库更改")
            
            # 重建FTS索引
            self._rebuild_fts_index()
            if progress_callback:
                progress_callback(100, "重建完成")
            
            logger.info(f"SQLite索引重建完成，处理了 {created_count} 个文件")
            return {
                "success": True,
                "processed_files": created_count,
                "total_files": len(files_info)
            }
            
        except Exception as e:
            logger.error(f"重建SQLite索引失败: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _rebuild_fts_table(self):
        """重建FTS表，使用自定义中文分词方案"""
        try:
            # 删除现有FTS表和触发器
            self.db.execute(text("DROP TRIGGER IF EXISTS files_ai"))
            self.db.execute(text("DROP TRIGGER IF EXISTS files_au"))
            self.db.execute(text("DROP TRIGGER IF EXISTS files_ad"))
            self.db.execute(text("DROP TABLE IF EXISTS files_fts"))
            
            # 重新创建FTS表，不使用content链接，这样可以更好地控制中文分词
            self.db.execute(text("""
                CREATE VIRTUAL TABLE files_fts USING fts5(
                    title, 
                    content,
                    tokenize='unicode61 remove_diacritics 0'
                )
            """))
            
            self.db.commit()
            logger.info("FTS表重建完成")
            
        except Exception as e:
            logger.error(f"重建FTS表失败: {e}")
            raise
    
    def _rebuild_fts_index(self):
        """重建FTS索引"""
        try:
            # 清空FTS表
            self.db.execute(text("DELETE FROM files_fts"))
            
            # 手动插入数据，为每个文件创建FTS记录
            files = self.db.query(File).filter(File.is_deleted == False).all()
            for file in files:
                self.db.execute(text("""
                    INSERT INTO files_fts(rowid, title, content) 
                    VALUES (:file_id, :title, :content)
                """), {
                    "file_id": file.id,
                    "title": file.title,
                    "content": file.content
                })
            
            self.db.commit()
            logger.info("FTS索引重建完成")
            
        except Exception as e:
            logger.error(f"重建FTS索引失败: {e}")
            raise
    
    def rebuild_vector_index(self, progress_callback=None) -> Dict[str, Any]:
        """重建ChromaDB向量索引"""
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
            
            # 处理每个文件
            processed_count = 0
            failed_count = 0
            for i, file in enumerate(files):
                try:
                    # 生成向量并保存到ChromaDB
                    success = self.ai_service.add_document_to_vector_db(
                        file.id,
                        file.title,
                        file.content,
                        {"file_path": file.file_path, "parent_folder": file.parent_folder}
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                    
                    if progress_callback and (i + 1) % 5 == 0:
                        progress = 20 + (i + 1) / len(files) * 70
                        progress_callback(progress, f"处理文件 {i + 1}/{len(files)} (成功: {processed_count}, 失败: {failed_count})")
                        
                except Exception as e:
                    logger.error(f"处理文件向量失败: {file.file_path}, 错误: {e}")
                    failed_count += 1
                    continue
            
            if progress_callback:
                progress_callback(100, f"ChromaDB向量索引重建完成 (成功: {processed_count}, 失败: {failed_count})")
            
            logger.info(f"ChromaDB向量索引重建完成，成功处理 {processed_count} 个文件，失败 {failed_count} 个")
            return {
                "success": True,
                "processed_files": processed_count,
                "failed_files": failed_count,
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
    
    def search_with_chinese_support(self, query: str, limit: int = 50) -> List[File]:
        """支持中文的FTS搜索"""
        try:
            # 使用FTS5进行搜索
            sql = text("""
                SELECT f.id, f.file_path, f.title, f.content, f.created_at, f.updated_at,
                       snippet(files_fts, 1, '<mark>', '</mark>', '...', 50) as snippet,
                       rank as score
                FROM files_fts 
                JOIN files f ON files_fts.rowid = f.id
                WHERE files_fts MATCH :query
                AND f.is_deleted = 0
                ORDER BY rank
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, {"query": query, "limit": limit})
            rows = result.fetchall()
            
            # 转换为File对象
            files = []
            for row in rows:
                file = File(
                    id=row.id,
                    file_path=row.file_path,
                    title=row.title,
                    content=row.content,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
                # 添加搜索相关信息
                file.snippet = row.snippet
                file.score = row.score
                files.append(file)
            
            return files
            
        except Exception as e:
            logger.error(f"FTS搜索失败: {e}")
            return []
    
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