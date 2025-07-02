from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from .base import Base

class PendingTask(Base):
    """待处理任务表 - 用于记录需要后台处理的文件任务"""
    __tablename__ = "pending_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, nullable=False, comment="关联的文件ID")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    task_type = Column(String(50), nullable=False, comment="任务类型：vector_index, fts_index")
    status = Column(String(20), default="pending", comment="任务状态：pending, processing, completed, failed")
    priority = Column(Integer, default=0, comment="任务优先级，数字越大优先级越高")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    processed_at = Column(DateTime, nullable=True, comment="处理完成时间")
    
    def __repr__(self):
        return f"<PendingTask(id={self.id}, file_path='{self.file_path}', task_type='{self.task_type}', status='{self.status}')>" 