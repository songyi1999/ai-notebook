from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from .base import Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(Text)
    config_type = Column(String, default='string')
    description = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 