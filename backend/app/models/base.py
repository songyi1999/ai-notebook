from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, LargeBinary, Float
from datetime import datetime
import os

# 从配置文件导入设置，如果失败则使用环境变量或默认值
try:
    from ..config import settings
    DATABASE_URL = settings.database_url
except ImportError:
    # 回退到环境变量或默认值
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/ai_notebook.db")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False # 设置为True可以看到SQL日志
)

# 创建一个会话Local类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类，所有模型将继承自它
Base = declarative_base() 