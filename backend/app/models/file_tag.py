from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, Float, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class FileTag(Base):
    __tablename__ = "file_tags"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_score = Column(Float, default=1.0)
    is_manual = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    file = relationship("File", backref="file_tags")
    tag = relationship("Tag", backref="file_tags")

    __table_args__ = (
        UniqueConstraint("file_id", "tag_id", name="uq_file_tag"),
    ) 