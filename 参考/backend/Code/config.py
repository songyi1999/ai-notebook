"""
统一配置文件
"""
import os
from pydantic_settings import BaseSettings

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


class Settings(BaseSettings):
    """应用配置"""
    PROJECT_NAME: str = "医疗评价大模型"
    API_V1_STR: str = "/api/v1"
    
    # 模型配置
    MODELNAME: str = os.getenv("MODELNAME", "qwen2.5")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-nYWcgh582Okjdv0aE47c3f0c61B24dF6Bf6bD57fF41eA7Ee")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "http://openai.sz-hgy.com:9002/v1")
    MODELNAME_WITH_CHAIN: str = os.getenv("MODELNAME_WITH_CHAIN", "deepseek-r1")
    ATMPMODEL: str = os.getenv("ATMPMODEL", "deepseek-r1")  # 专门用于ATMP相关问题的微调模型
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))
    
    # OCR服务配置
    OCR_SERVICE_URL: str = os.getenv("OCR_SERVICE_URL", "http://ocr:7860")
    
    
    
    class Config:
        case_sensitive = True
        env_file = ".env"  # 可以从.env文件读取环境变量
        env_file_encoding = "utf-8"

# 创建全局配置实例
settings = Settings()






