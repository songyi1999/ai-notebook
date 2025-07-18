from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    content_hash = Column(String)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    is_deleted = Column(Boolean, default=False, index=True)
    parent_folder = Column(String, index=True)
    file_metadata = Column(JSON) 
    
    # 关联关系
    # Note: Memory relationships removed (using simple JSON file-based memory system now) 