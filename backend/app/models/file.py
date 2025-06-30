from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
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
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, index=True)
    parent_folder = Column(String, index=True)
    tags = Column(JSON)
    metadata = Column(JSON) 