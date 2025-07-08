"""配置管理服务"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..schemas.config import (
    AppConfig, AISettings, ConfigUpdateRequest, 
    ConfigValidationResult, ConfigTestResult,
    AIProvider, FallbackMode
)
from ..config import settings
import requests
from ..services.ai_service_langchain import OpenAICompatibleEmbeddings

logger = logging.getLogger(__name__)

class ConfigService:
    """配置管理服务"""
    
    def __init__(self):
        self.config_file_path = Path("./config.json")
        self.config_backup_dir = Path("./data/config_backups")
        self.config_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._app_config = None
        self.load_config()
    
    def load_config(self) -> AppConfig:
        """加载配置文件"""
        try:
            if self.config_file_path.exists():
                logger.info(f"从文件加载配置: {self.config_file_path}")
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._app_config = AppConfig(**config_data)
                logger.info("配置文件加载成功")
            else:
                logger.info("配置文件不存在，使用默认配置")
                self._app_config = self._create_default_config()
                self.save_config()
            
            return self._app_config
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 使用默认配置
            self._app_config = self._create_default_config()
            return self._app_config
    
    def get_config(self) -> AppConfig:
        """获取当前配置"""
        if self._app_config is None:
            self.load_config()
        return self._app_config
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 创建备份
            self._create_backup()
            
            # 更新元数据
            self._app_config.meta.last_updated = datetime.now()
            
            # 保存配置
            config_dict = self._app_config.dict()
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"配置已保存到: {self.config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_config(self, update_request: ConfigUpdateRequest) -> bool:
        """更新配置"""
        try:
            if update_request.ai_settings:
                self._app_config.ai_settings = update_request.ai_settings
            
            if update_request.application:
                self._app_config.application = update_request.application
            
            if update_request.advanced:
                self._app_config.advanced = update_request.advanced
            
            return self.save_config()
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def validate_config(self, config: Optional[AppConfig] = None) -> ConfigValidationResult:
        """验证配置"""
        if config is None:
            config = self.get_config()
        
        result = ConfigValidationResult(valid=True)
        
        try:
            # 检查AI设置
            if config.ai_settings.enabled:
                # 验证语言模型配置
                if config.ai_settings.language_model:
                    lm_errors = self._validate_language_model(config.ai_settings.language_model)
                    result.errors.extend(lm_errors)
                else:
                    result.errors.append("AI已启用但未配置语言模型")
                
                # 验证嵌入模型配置
                if config.ai_settings.embedding_model:
                    em_errors = self._validate_embedding_model(config.ai_settings.embedding_model)
                    result.errors.extend(em_errors)
                else:
                    result.errors.append("AI已启用但未配置嵌入模型")
            
            # 检查高级配置
            if config.advanced:
                adv_errors = self._validate_advanced_config(config.advanced)
                result.errors.extend(adv_errors)
            
            result.valid = len(result.errors) == 0
            
            # 测试AI可用性
            if config.ai_settings.enabled and result.valid:
                ai_test = self.test_ai_connectivity(config)
                result.ai_available = ai_test.language_model.get('available', False)
                result.embedding_available = ai_test.embedding_model.get('available', False)
            
            return result
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            result.valid = False
            result.errors.append(f"验证过程出错: {str(e)}")
            return result
    
    def test_ai_connectivity(self, config: Optional[AppConfig] = None) -> ConfigTestResult:
        """测试AI连接性"""
        if config is None:
            config = self.get_config()
        
        result = ConfigTestResult()
        
        # 测试语言模型
        if config.ai_settings.enabled and config.ai_settings.language_model:
            result.language_model = self._test_language_model(config.ai_settings.language_model)
        
        # 测试嵌入模型
        if config.ai_settings.enabled and config.ai_settings.embedding_model:
            result.embedding_model = self._test_embedding_model(config.ai_settings.embedding_model)
        
        # 评估整体状态
        lm_available = result.language_model.get('available', False)
        em_available = result.embedding_model.get('available', False)
        
        if not config.ai_settings.enabled:
            result.overall_status = "disabled"
            result.message = "AI功能已禁用"
        elif lm_available and em_available:
            result.overall_status = "fully_available"
            result.message = "所有AI功能正常"
        elif lm_available or em_available:
            result.overall_status = "partially_available"
            result.message = "部分AI功能可用"
        else:
            result.overall_status = "unavailable"
            result.message = "AI功能不可用"
        
        return result
    
    def apply_preset(self, preset_name: str) -> bool:
        """应用预设配置"""
        try:
            config = self.get_config()
            
            if preset_name not in config.presets:
                logger.error(f"预设不存在: {preset_name}")
                return False
            
            preset = config.presets[preset_name]
            config.ai_settings = preset.ai_settings
            
            return self.save_config()
            
        except Exception as e:
            logger.error(f"应用预设失败: {e}")
            return False
    
    def get_available_presets(self) -> Dict[str, Any]:
        """获取可用的预设配置"""
        config = self.get_config()
        return {
            name: {
                "name": preset.name,
                "description": preset.description
            }
            for name, preset in config.presets.items()
        }
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self._create_backup()
            self._app_config = self._create_default_config()
            return self.save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def get_current_ai_status(self) -> Dict[str, Any]:
        """获取当前AI状态"""
        config = self.get_config()
        
        if not config.ai_settings.enabled:
            return {
                "enabled": False,
                "mode": "notes_only",
                "language_model": None,
                "embedding_model": None
            }
        
        return {
            "enabled": True,
            "mode": "ai_enabled",
            "language_model": {
                "provider": config.ai_settings.language_model.provider if config.ai_settings.language_model else None,
                "model_name": config.ai_settings.language_model.model_name if config.ai_settings.language_model else None
            },
            "embedding_model": {
                "provider": config.ai_settings.embedding_model.provider if config.ai_settings.embedding_model else None,
                "model_name": config.ai_settings.embedding_model.model_name if config.ai_settings.embedding_model else None
            }
        }
    
    def _create_default_config(self) -> AppConfig:
        """创建默认配置"""
        from ..schemas.config import (
            LanguageModelConfig, EmbeddingModelConfig, 
            ConfigPreset, AIProvider
        )
        
        # 默认AI设置（基于现有环境变量）
        default_ai = AISettings(
            enabled=bool(settings.openai_api_key),
            language_model=LanguageModelConfig(
                provider=AIProvider.OPENAI_COMPATIBLE,
                base_url=settings.openai_base_url or "http://localhost:11434/v1",
                api_key=settings.openai_api_key or "ollama",
                model_name=settings.openai_model
            ),
            embedding_model=EmbeddingModelConfig(
                provider=AIProvider.OPENAI_COMPATIBLE,
                base_url=settings.get_embedding_base_url() or "http://localhost:11434/v1", 
                api_key=settings.get_embedding_api_key() or "ollama",
                model_name=settings.embedding_model_name,
                dimension=settings.embedding_dimension
            )
        )
        
        # 预设配置
        presets = {
            "local_ollama": ConfigPreset(
                name="本地 Ollama",
                description="使用本地 Ollama 服务（推荐）",
                ai_settings=AISettings(
                    enabled=True,
                    language_model=LanguageModelConfig(
                        provider=AIProvider.OPENAI_COMPATIBLE,
                        base_url="http://localhost:11434/v1",
                        api_key="ollama",
                        model_name="qwen2.5:0.5b"
                    ),
                    embedding_model=EmbeddingModelConfig(
                        provider=AIProvider.OPENAI_COMPATIBLE,
                        base_url="http://localhost:11434/v1",
                        api_key="ollama",
                        model_name="quentinz/bge-large-zh-v1.5:latest",
                        dimension=1024
                    )
                )
            ),
            "notes_only": ConfigPreset(
                name="纯笔记模式",
                description="禁用所有AI功能，仅作为笔记管理工具",
                ai_settings=AISettings(
                    enabled=False,
                    fallback_mode=FallbackMode.NOTES_ONLY
                )
            )
        }
        
        return AppConfig(
            ai_settings=default_ai,
            presets=presets
        )
    
    def _create_backup(self):
        """创建配置备份"""
        try:
            if self.config_file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.config_backup_dir / f"config_backup_{timestamp}.json"
                
                import shutil
                shutil.copy2(self.config_file_path, backup_path)
                
                # 只保留最近10个备份
                backups = sorted(self.config_backup_dir.glob("config_backup_*.json"))
                if len(backups) > 10:
                    for old_backup in backups[:-10]:
                        old_backup.unlink()
                
                logger.info(f"配置备份已创建: {backup_path}")
        except Exception as e:
            logger.warning(f"创建配置备份失败: {e}")
    
    def _validate_language_model(self, lm_config) -> List[str]:
        """验证语言模型配置"""
        errors = []
        
        if not lm_config.base_url:
            errors.append("语言模型base_url不能为空")
        
        if not lm_config.model_name:
            errors.append("语言模型model_name不能为空")
        
        if lm_config.temperature < 0 or lm_config.temperature > 2:
            errors.append("temperature必须在0-2之间")
        
        if lm_config.max_tokens <= 0:
            errors.append("max_tokens必须大于0")
        
        return errors
    
    def _validate_embedding_model(self, em_config) -> List[str]:
        """验证嵌入模型配置"""
        errors = []
        
        if not em_config.base_url:
            errors.append("嵌入模型base_url不能为空")
        
        if not em_config.model_name:
            errors.append("嵌入模型model_name不能为空")
        
        if em_config.dimension <= 0:
            errors.append("嵌入模型dimension必须大于0")
        
        return errors
    
    def _validate_advanced_config(self, adv_config) -> List[str]:
        """验证高级配置"""
        errors = []
        
        # 验证搜索配置
        if adv_config.search.semantic_search_threshold < 0:
            errors.append("语义搜索阈值不能为负数")
        
        if adv_config.search.search_limit <= 0:
            errors.append("搜索限制必须大于0")
        
        # 验证分块配置
        if adv_config.chunking.hierarchical_content_overlap < 0:
            errors.append("内容重叠不能为负数")
        
        return errors
    
    def _test_language_model(self, lm_config) -> Dict[str, Any]:
        """测试语言模型连接"""
        try:
            # 构建测试URL
            base_url = lm_config.base_url.rstrip('/')
            if base_url.endswith('/v1'):
                test_url = f"{base_url}/models"
            else:
                test_url = f"{base_url}/v1/models"
            
            headers = {
                "Authorization": f"Bearer {lm_config.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model.get('id', '') for model in models_data.get('data', [])]
                
                return {
                    "available": True,
                    "status_code": response.status_code,
                    "message": "语言模型服务可用",
                    "available_models": available_models,
                    "configured_model_found": lm_config.model_name in available_models
                }
            else:
                return {
                    "available": False,
                    "status_code": response.status_code,
                    "message": f"服务返回错误: {response.text}",
                    "available_models": [],
                    "configured_model_found": False
                }
                
        except Exception as e:
            return {
                "available": False,
                "status_code": None,
                "message": f"连接失败: {str(e)}",
                "available_models": [],
                "configured_model_found": False
            }
    
    def _test_embedding_model(self, em_config) -> Dict[str, Any]:
        """测试嵌入模型连接"""
        try:
            # 使用嵌入API测试
            embeddings = OpenAICompatibleEmbeddings(
                base_url=em_config.base_url,
                api_key=em_config.api_key,
                model=em_config.model_name
            )
            
            # 测试嵌入一小段文本
            test_embedding = embeddings.embed_query("测试文本")
            
            if test_embedding and len(test_embedding) > 0:
                return {
                    "available": True,
                    "message": "嵌入模型服务可用",
                    "dimension": len(test_embedding),
                    "configured_dimension_match": len(test_embedding) == em_config.dimension
                }
            else:
                return {
                    "available": False,
                    "message": "嵌入模型返回空结果",
                    "dimension": 0,
                    "configured_dimension_match": False
                }
                
        except Exception as e:
            return {
                "available": False,
                "message": f"嵌入模型测试失败: {str(e)}",
                "dimension": 0,
                "configured_dimension_match": False
            }

# 全局配置服务实例
config_service = ConfigService()