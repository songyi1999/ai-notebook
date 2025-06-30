from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, LargeBinary, Float
from datetime import datetime
import os

# 从环境变量获取数据库URL，如果未设置则使用默认值
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/notebook.db")

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