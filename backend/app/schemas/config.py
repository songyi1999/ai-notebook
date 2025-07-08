"""配置相关的Pydantic模型"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class AIProvider(str, Enum):
    """AI服务提供商"""
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    DISABLED = "disabled"

class FallbackMode(str, Enum):
    """降级模式"""
    NOTES_ONLY = "notes_only"  # 纯笔记模式
    LIMITED_AI = "limited_ai"  # 有限AI功能
    OFFLINE = "offline"        # 离线模式

class LanguageModelConfig(BaseModel):
    """语言模型配置"""
    provider: AIProvider = AIProvider.OPENAI_COMPATIBLE
    base_url: Optional[str] = "http://localhost:11434/v1"
    api_key: Optional[str] = "ollama"
    model_name: str = "qwen2.5:0.5b"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    timeout: int = Field(default=30, gt=0)
    
    class Config:
        use_enum_values = True

class EmbeddingModelConfig(BaseModel):
    """嵌入模型配置"""
    provider: AIProvider = AIProvider.OPENAI_COMPATIBLE
    base_url: Optional[str] = "http://localhost:11434/v1"
    api_key: Optional[str] = "ollama"
    model_name: str = "quentinz/bge-large-zh-v1.5:latest"
    dimension: int = Field(default=1024, gt=0)
    
    class Config:
        use_enum_values = True

class AISettings(BaseModel):
    """AI设置"""
    enabled: bool = True
    fallback_mode: FallbackMode = FallbackMode.NOTES_ONLY
    language_model: Optional[LanguageModelConfig] = None
    embedding_model: Optional[EmbeddingModelConfig] = None
    
    class Config:
        use_enum_values = True

class ConfigPreset(BaseModel):
    """配置预设"""
    name: str
    description: str
    ai_settings: AISettings

class SearchConfig(BaseModel):
    """搜索配置"""
    semantic_search_threshold: float = Field(default=1.0, ge=0.0, le=2.0)
    search_limit: int = Field(default=50, gt=0, le=500)
    enable_hierarchical_chunking: bool = True

class ChunkingConfig(BaseModel):
    """分块配置"""
    hierarchical_summary_max_length: int = Field(default=2000, gt=0)
    hierarchical_outline_max_depth: int = Field(default=5, gt=0, le=10)
    hierarchical_content_target_size: int = Field(default=1000, gt=0)
    hierarchical_content_max_size: int = Field(default=1500, gt=0)
    hierarchical_content_overlap: int = Field(default=100, ge=0)

class LLMConfig(BaseModel):
    """LLM高级配置"""
    context_window: int = Field(default=131072, gt=0)
    chunk_for_llm_processing: int = Field(default=30000, gt=0)
    max_chunks_for_refine: int = Field(default=20, gt=0)

class AdvancedConfig(BaseModel):
    """高级配置"""
    search: SearchConfig = SearchConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    llm: LLMConfig = LLMConfig()

class ApplicationConfig(BaseModel):
    """应用程序配置"""
    theme: str = "light"
    language: str = "zh-CN"
    auto_save: bool = True
    backup_enabled: bool = True

class ConfigMeta(BaseModel):
    """配置元数据"""
    config_version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.now)
    created_by: str = "user"
    description: str = "AI笔记本配置文件"

class AppConfig(BaseModel):
    """完整的应用配置"""
    ai_settings: AISettings = AISettings()
    presets: Dict[str, ConfigPreset] = {}
    application: ApplicationConfig = ApplicationConfig()
    advanced: AdvancedConfig = AdvancedConfig()
    meta: ConfigMeta = ConfigMeta()

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    ai_settings: Optional[AISettings] = None
    application: Optional[ApplicationConfig] = None
    advanced: Optional[AdvancedConfig] = None

class ConfigValidationResult(BaseModel):
    """配置验证结果"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    ai_available: bool = False
    embedding_available: bool = False

class ConfigTestResult(BaseModel):
    """配置测试结果"""
    language_model: Dict[str, Any] = {}
    embedding_model: Dict[str, Any] = {}
    overall_status: str = "unknown"
    message: str = ""