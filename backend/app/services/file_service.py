from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional
from pathlib import Path
import hashlib
import logging

from ..models.file import File
from ..schemas.file import FileCreate, FileUpdate

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, db: Session):
        self.db = db

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

    def create_file(self, file: FileCreate) -> File:
        """创建文件（同时写入数据库和磁盘）"""
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
                tags=file.tags,
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
            
            logger.info(f"文件创建成功: {file.file_path}")
            return db_file
        except Exception as e:
            logger.error(f"文件创建失败: {e}")
            self.db.rollback()
            raise

    def get_file(self, file_id: int) -> Optional[File]:
        return self.db.query(File).filter(File.id == file_id, File.is_deleted == False).first()

    def get_file_by_path(self, file_path: str) -> Optional[File]:
        """根据路径获取文件，如果数据库中没有则尝试从磁盘读取"""
        db_file = self.db.query(File).filter(File.file_path == file_path, File.is_deleted == False).first()
        
        if db_file:
            return db_file
        
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

    def update_file(self, file_id: int, file_update: FileUpdate) -> Optional[File]:
        """更新文件（同时更新数据库和磁盘）"""
        try:
            db_file = self.get_file(file_id)
            if not db_file:
                return None
            
            # 更新数据库字段
            update_data = file_update.dict(exclude_unset=True)
            
            # 如果内容有更新，重新计算哈希和大小
            if 'content' in update_data:
                update_data['content_hash'] = self._calculate_content_hash(update_data['content'])
                update_data['file_size'] = len(update_data['content'].encode('utf-8'))
                
                # 写入磁盘
                if not self._write_file_to_disk(db_file.file_path, update_data['content']):
                    raise Exception("文件写入磁盘失败")
            
            for key, value in update_data.items():
                setattr(db_file, key, value)
            
            self.db.commit()
            self.db.refresh(db_file)
            
            logger.info(f"文件更新成功: {db_file.file_path}")
            return db_file
        except Exception as e:
            logger.error(f"文件更新失败: {e}")
            self.db.rollback()
            raise

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

    def search_files_fts(self, query_str: str, limit: int = 50) -> List[File]:
        """使用FTS5进行全文搜索"""
        try:
            # 使用FTS5进行全文搜索
            fts_query = text("""
                SELECT f.* FROM files f
                INNER JOIN files_fts fts ON f.id = fts.rowid
                WHERE files_fts MATCH :query_str AND f.is_deleted = 0
                ORDER BY bm25(files_fts) DESC
                LIMIT :limit
            """)
            
            results = self.db.execute(fts_query, {
                "query_str": query_str, 
                "limit": limit
            }).fetchall()
            
            # 将结果转换为File对象
            files = []
            for row in results:
                file_dict = dict(row._mapping)
                files.append(File(**file_dict))
            
            logger.info(f"FTS搜索完成，查询: {query_str}, 结果数: {len(files)}")
            return files
            
        except Exception as e:
            logger.error(f"FTS搜索失败: {e}")
            # 如果FTS搜索失败，回退到普通搜索
            return self.search_files_fallback(query_str, limit)

    def search_files_fallback(self, query_str: str, limit: int = 50) -> List[File]:
        """回退搜索方法（使用LIKE）"""
        try:
            search_pattern = f"%{query_str}%"
            results = self.db.query(File).filter(
                or_(
                    File.title.like(search_pattern),
                    File.content.like(search_pattern)
                ),
                File.is_deleted == False
            ).limit(limit).all()
            
            logger.info(f"回退搜索完成，查询: {query_str}, 结果数: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"回退搜索失败: {e}")
            return []

    def search_files(self, query_str: str, skip: int = 0, limit: int = 100) -> List[File]:
        """保持原有接口兼容性"""
        return self.search_files_fts(query_str, limit) 