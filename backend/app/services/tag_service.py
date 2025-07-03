from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from ..models.tag import Tag
from ..models.file_tag import FileTag
from ..models.file import File
from ..schemas.tag import TagCreate, TagUpdate, FileTagCreate
import logging

logger = logging.getLogger(__name__)

class TagService:
    """标签服务类，处理标签相关的业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_tag(self, tag: TagCreate) -> Tag:
        """创建标签"""
        try:
            db_tag = Tag(
                name=tag.name,
                color=tag.color,
                description=tag.description,
                is_auto_generated=tag.is_auto_generated
            )
            self.db.add(db_tag)
            self.db.commit()
            self.db.refresh(db_tag)
            logger.info(f"创建标签成功: {tag.name}")
            return db_tag
        except Exception as e:
            logger.error(f"创建标签失败: {e}")
            self.db.rollback()
            raise

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """根据ID获取标签"""
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        return self.db.query(Tag).filter(Tag.name == name).first()

    def get_all_tags(self, skip: int = 0, limit: int = 100) -> List[Tag]:
        """获取所有标签"""
        return self.db.query(Tag).offset(skip).limit(limit).all()

    def get_tags_with_usage_stats(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取带使用统计的标签列表"""
        try:
            # 查询标签及其使用次数
            query = self.db.query(
                Tag,
                func.count(FileTag.file_id).label('usage_count')
            ).outerjoin(FileTag, Tag.id == FileTag.tag_id)\
             .group_by(Tag.id)\
             .offset(skip)\
             .limit(limit)
            
            results = query.all()
            
            tags_with_stats = []
            for tag, usage_count in results:
                # 获取最近使用的文件（最多5个）
                recent_files_query = self.db.query(File.title)\
                    .join(FileTag, File.id == FileTag.file_id)\
                    .filter(FileTag.tag_id == tag.id)\
                    .order_by(FileTag.created_at.desc())\
                    .limit(5)
                
                recent_files = [file.title for file in recent_files_query.all()]
                
                tag_dict = {
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color,
                    'description': tag.description,
                    'is_auto_generated': tag.is_auto_generated,
                    'created_at': tag.created_at,
                    'updated_at': tag.updated_at,
                    'usage_count': usage_count or 0,
                    'recent_files': recent_files
                }
                tags_with_stats.append(tag_dict)
            
            logger.info(f"获取带统计的标签列表成功，共 {len(tags_with_stats)} 个标签")
            return tags_with_stats
            
        except Exception as e:
            logger.error(f"获取带统计的标签列表失败: {e}")
            raise

    def get_tag_usage_count(self, tag_id: int) -> int:
        """获取单个标签的使用次数"""
        try:
            count = self.db.query(FileTag).filter(FileTag.tag_id == tag_id).count()
            return count
        except Exception as e:
            logger.error(f"获取标签使用次数失败: {e}")
            return 0

    def update_tag(self, tag_id: int, tag_update: TagUpdate) -> Optional[Tag]:
        """更新标签"""
        try:
            db_tag = self.get_tag(tag_id)
            if db_tag is None:
                return None
            
            # 更新字段
            if tag_update.name is not None:
                db_tag.name = tag_update.name
            if tag_update.color is not None:
                db_tag.color = tag_update.color
            if tag_update.description is not None:
                db_tag.description = tag_update.description
            
            self.db.commit()
            self.db.refresh(db_tag)
            logger.info(f"更新标签成功: {tag_id}")
            return db_tag
        except Exception as e:
            logger.error(f"更新标签失败: {e}")
            self.db.rollback()
            raise

    def delete_tag(self, tag_id: int) -> Optional[Tag]:
        """删除标签"""
        try:
            db_tag = self.get_tag(tag_id)
            if db_tag is None:
                return None
            
            # 先删除所有相关的文件标签关联记录
            from ..models.file_tag import FileTag
            file_tags_count = self.db.query(FileTag).filter(FileTag.tag_id == tag_id).count()
            self.db.query(FileTag).filter(FileTag.tag_id == tag_id).delete()
            logger.info(f"删除标签关联记录: tag_id={tag_id}, count={file_tags_count}")
            
            # 然后删除标签本身
            self.db.delete(db_tag)
            self.db.commit()
            logger.info(f"删除标签成功: {tag_id}")
            return db_tag
        except Exception as e:
            logger.error(f"删除标签失败: {e}")
            self.db.rollback()
            raise

    def search_tags(self, query: str) -> List[Tag]:
        """搜索标签"""
        return self.db.query(Tag).filter(Tag.name.contains(query)).all()


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