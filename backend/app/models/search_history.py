from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Float
from sqlalchemy.sql import func
from .base import Base

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False, index=True)
    search_type = Column(String, default='mixed')
    results_count = Column(Integer, default=0)
    response_time = Column(Float)
    created_at = Column(DateTime, default=func.now(), index=True)
    user_agent = Column(String)
    session_id = Column(String, index=True) 