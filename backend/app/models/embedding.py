from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, LargeBinary, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_hash = Column(String, nullable=False)
    embedding_vector = Column(LargeBinary) # 存储序列化后的向量数据
    vector_model = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # 多层次分块扩展字段
    chunk_type = Column(String, default='content', index=True)  # 'summary', 'outline', 'content'
    chunk_level = Column(Integer, default=3, index=True)        # 1=摘要, 2=大纲, 3=内容
    parent_heading = Column(Text, nullable=True)                # 父级标题/章节
    section_path = Column(Text, nullable=True)                  # 章节路径，如 "第一章/第二节"

    file = relationship("File", backref="embeddings")

    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunk"),
    ) 