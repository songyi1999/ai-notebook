from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional

from ..models.file import File
from ..schemas.file import FileCreate, FileUpdate

class FileService:
    def __init__(self, db: Session):
        self.db = db

    def create_file(self, file: FileCreate) -> File:
        db_file = File(**file.dict())
        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)
        return db_file

    def get_file(self, file_id: int) -> Optional[File]:
        return self.db.query(File).filter(File.id == file_id, File.is_deleted == False).first()

    def get_file_by_path(self, file_path: str) -> Optional[File]:
        return self.db.query(File).filter(File.file_path == file_path, File.is_deleted == False).first()

    def get_files(self, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[File]:
        query = self.db.query(File)
        if not include_deleted:
            query = query.filter(File.is_deleted == False)
        return query.offset(skip).limit(limit).all()

    def update_file(self, file_id: int, file_update: FileUpdate) -> Optional[File]:
        db_file = self.get_file(file_id)
        if not db_file:
            return None
        for key, value in file_update.dict(exclude_unset=True).items():
            setattr(db_file, key, value)
        self.db.commit()
        self.db.refresh(db_file)
        return db_file

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

    def search_files(self, query_str: str, skip: int = 0, limit: int = 100) -> List[File]:
        # 使用FTS5进行全文搜索
        # SQLite FTS5 的 MATCH 语法与 SQL LIKE 不同
        # 这里直接使用 text() 来执行 FTS5 查询
        fts_query = f"SELECT rowid FROM files_fts WHERE files_fts MATCH :query_str ORDER BY rank DESC LIMIT :limit OFFSET :skip;"
        
        # 执行FTS5查询获取匹配的rowid
        fts_results = self.db.execute(text(fts_query), {"query_str": query_str, "limit": limit, "skip": skip}).fetchall()
        
        # 从FTS5结果中提取文件ID
        file_ids = [row[0] for row in fts_results]
        
        if not file_ids:
            return []
            
        # 根据文件ID从files表中获取完整的文件对象，并确保未被软删除
        return self.db.query(File).filter(
            File.id.in_(file_ids),
            File.is_deleted == False
        ).all() 