from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """应用配置"""
    
    # 数据存储根目录配置
    data_directory: str = "./data"  # 相对于backend目录
    
    # 数据库配置
    database_url: str = "sqlite:///./data/ai_notebook.db"
    
    # 向量数据库配置
    chroma_db_path: str = "./data/chroma_db"
    
    # OpenAI配置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # 嵌入模型配置
    embedding_model_name: str = "text-embedding-ada-002"  # 默认OpenAI模型
    
    # 文件存储配置
    notes_directory: str = "./notes"  # 相对于backend目录，在Docker中指向挂载的/app/notes
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # API配置
    api_prefix: str = "/api/v1"
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002"
    ]
    
    # 日志配置
    log_level: str = "INFO"
    
    # 搜索配置
    search_limit: int = 50
    embedding_dimension: int = 1536  # OpenAI text-embedding-ada-002
    semantic_search_threshold: float = 1.0  # 语义搜索距离阈值（距离越小越相似，小于此值的结果将被保留）
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 创建全局配置实例
settings = Settings()

# 确保数据目录存在
data_dir = Path(settings.data_directory)
data_dir.mkdir(parents=True, exist_ok=True)

# 确保chroma_db目录存在
chroma_dir = Path(settings.chroma_db_path)
chroma_dir.mkdir(parents=True, exist_ok=True)

# 确保笔记目录存在
notes_dir = Path(settings.notes_directory)
notes_dir.mkdir(parents=True, exist_ok=True) 