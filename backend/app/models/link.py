from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    source_file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    target_file_id = Column(Integer, ForeignKey("files.id", ondelete="SET NULL"), index=True)
    link_text = Column(Text, nullable=False)
    link_type = Column(String, default='wikilink', index=True)
    position_start = Column(Integer)
    position_end = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    is_valid = Column(Boolean, default=True, index=True)

    source_file = relationship("File", foreign_keys=[source_file_id], backref="outgoing_links")
    target_file = relationship("File", foreign_keys=[target_file_id], backref="incoming_links") 