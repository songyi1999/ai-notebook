from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from .base import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    context_files = Column(JSON) # 存储相关文件列表（JSON格式）
    model_name = Column(String)
    tokens_used = Column(Integer)
    response_time = Column(Float)
    created_at = Column(DateTime, default=func.now(), index=True)
    message_metadata = Column(JSON)

    session = relationship("ChatSession", backref="messages") 