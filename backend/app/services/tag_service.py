from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from ..models.tag import Tag
from ..models.file_tag import FileTag
from ..models.file import File
from ..schemas.tag import TagCreate, TagUpdate, FileTagCreate
import logging

logger = logging.getLogger(__name__)

from ..services.base_service import BaseService




class FileTagService:
    """文件标签关联服务类"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_file_tag(self, file_tag: FileTagCreate) -> FileTag:
        """创建文件标签关联"""
        try:
            db_file_tag = FileTag(
                file_id=file_tag.file_id,
                tag_id=file_tag.tag_id,
                relevance_score=file_tag.relevance_score,
                is_manual=file_tag.is_manual
            )
            self.db.add(db_file_tag)
            self.db.commit()
            self.db.refresh(db_file_tag)
            logger.info(f"创建文件标签关联成功: file_id={file_tag.file_id}, tag_id={file_tag.tag_id}")
            return db_file_tag
        except Exception as e:
            logger.error(f"创建文件标签关联失败: {e}")
            self.db.rollback()
            raise

    def get_file_tag(self, file_id: int, tag_id: int) -> Optional[FileTag]:
        """获取文件标签关联"""
        return self.db.query(FileTag).filter(
            FileTag.file_id == file_id,
            FileTag.tag_id == tag_id
        ).first()

    def get_file_tags_by_file(self, file_id: int) -> List[FileTag]:
        """获取文件的所有标签"""
        return self.db.query(FileTag).filter(FileTag.file_id == file_id).all()

    def get_file_tags_by_tag(self, tag_id: int) -> List[FileTag]:
        """获取标签关联的所有文件"""
        return self.db.query(FileTag).filter(FileTag.tag_id == tag_id).all()

    def delete_file_tag(self, file_id: int, tag_id: int) -> Optional[FileTag]:
        """删除文件标签关联"""
        try:
            db_file_tag = self.get_file_tag(file_id, tag_id)
            if db_file_tag is None:
                return None
            
            self.db.delete(db_file_tag)
            self.db.commit()
            logger.info(f"删除文件标签关联成功: file_id={file_id}, tag_id={tag_id}")
            return db_file_tag
        except Exception as e:
            logger.error(f"删除文件标签关联失败: {e}")
            self.db.rollback()
            raise

    def delete_all_file_tags(self, file_id: int) -> int:
        """删除文件的所有标签关联"""
        try:
            count = self.db.query(FileTag).filter(FileTag.file_id == file_id).count()
            self.db.query(FileTag).filter(FileTag.file_id == file_id).delete()
            self.db.commit()
            logger.info(f"删除文件所有标签关联成功: file_id={file_id}, count={count}")
            return count
        except Exception as e:
            logger.error(f"删除文件所有标签关联失败: {e}")
            self.db.rollback()
            raise 