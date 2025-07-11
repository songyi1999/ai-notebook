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
    embedding_base_url: Optional[str] = None  # 嵌入模型专用API地址，为空时使用openai_base_url
    embedding_api_key: Optional[str] = None   # 嵌入模型专用API密钥，为空时使用openai_api_key
    
    # 文件存储配置
    notes_directory: str = "./notes"  # 相对于backend目录，在Docker中指向挂载的/app/notes
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # API配置
    api_prefix: str = "/api/v1"
    cors_origins: list = [
        "http://localhost:3000",  # Standard frontend dev port
        "http://localhost:3002",  # Alternative frontend dev port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002",
        "null"  # Allow requests from 'file://' origins
    ]
    
    # 日志配置
    log_level: str = "INFO"
    
    # 搜索配置
    search_limit: int = 50
    embedding_dimension: int = 1536  # OpenAI text-embedding-ada-002
    semantic_search_threshold: float = 1.0  # 语义搜索距离阈值（距离越小越相似，小于此值的结果将被保留）
    
    # LLM配置
    llm_context_window: int = 131072  # LLM上下文窗口长度，默认128K tokens
    
    # 多层次分块配置（始终启用）
    enable_hierarchical_chunking: bool = True  # 始终启用多层次分块
    hierarchical_summary_max_length: int = 2000  # 摘要最大长度
    hierarchical_outline_max_depth: int = 5      # 大纲最大深度
    hierarchical_content_target_size: int = 1000 # 内容块目标大小
    hierarchical_content_max_size: int = 1500    # 内容块最大大小
    hierarchical_content_overlap: int = 100      # 内容块重叠大小
    
    # 智能分块配置
    chunk_for_llm_processing: int = 30000  # 发送给LLM处理的单个块大小（字符数）
    max_chunks_for_refine: int = 20  # Refine策略最大处理块数
    
    def get_embedding_base_url(self) -> Optional[str]:
        """获取嵌入模型API地址，优先使用专用配置，否则回退到通用配置"""
        return self.embedding_base_url or self.openai_base_url
    
    def get_embedding_api_key(self) -> Optional[str]:
        """获取嵌入模型API密钥，优先使用专用配置，否则回退到通用配置"""
        return self.embedding_api_key or self.openai_api_key

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