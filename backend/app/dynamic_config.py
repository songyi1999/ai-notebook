"""动态配置系统 - 支持JSON配置文件覆盖环境变量"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Any
from .config import Settings, settings as original_settings

logger = logging.getLogger(__name__)

class DynamicSettings:
    """动态配置类，支持JSON配置文件覆盖"""
    
    def __init__(self):
        self.config_file_path = Path("./config.json")
        self.json_config = None
        self.load_json_config()
    
    def load_json_config(self):
        """加载JSON配置文件"""
        try:
            if self.config_file_path.exists():
                logger.info(f"发现配置文件: {self.config_file_path}")
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self.json_config = json.load(f)
                logger.info("JSON配置文件加载成功")
            else:
                logger.info("未找到JSON配置文件，使用环境变量配置")
                self.json_config = None
        except Exception as e:
            logger.error(f"加载JSON配置文件失败: {e}")
            self.json_config = None
    
    def reload_config(self):
        """重新加载配置"""
        self.load_json_config()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置值，优先从JSON配置读取"""
        # 如果有JSON配置，优先使用
        if self.json_config:
            json_value = self._get_from_json_config(key)
            if json_value is not None:
                logger.debug(f"从JSON配置获取 {key}: {json_value}")
                return json_value
        
        # 回退到原始配置（环境变量）
        original_value = getattr(original_settings, key, default)
        logger.debug(f"从环境变量获取 {key}: {original_value}")
        return original_value
    
    def _get_from_json_config(self, key: str) -> Any:
        """从JSON配置中获取值"""
        if not self.json_config:
            return None
        
        # 映射关系：config.py中的属性名 -> JSON配置路径
        mapping = {
            # AI模型配置
            'openai_api_key': ['ai_settings', 'language_model', 'api_key'],
            'openai_base_url': ['ai_settings', 'language_model', 'base_url'],
            'openai_model': ['ai_settings', 'language_model', 'model_name'],
            
            # 嵌入模型配置  
            'embedding_model_name': ['ai_settings', 'embedding_model', 'model_name'],
            'embedding_base_url': ['ai_settings', 'embedding_model', 'base_url'],
            'embedding_api_key': ['ai_settings', 'embedding_model', 'api_key'],
            'embedding_dimension': ['ai_settings', 'embedding_model', 'dimension'],
            
            # 高级配置
            'semantic_search_threshold': ['advanced', 'search', 'semantic_search_threshold'],
            'search_limit': ['advanced', 'search', 'search_limit'],
            'enable_hierarchical_chunking': ['advanced', 'search', 'enable_hierarchical_chunking'],
            'hierarchical_summary_max_length': ['advanced', 'chunking', 'hierarchical_summary_max_length'],
            'hierarchical_outline_max_depth': ['advanced', 'chunking', 'hierarchical_outline_max_depth'],
            'hierarchical_content_target_size': ['advanced', 'chunking', 'hierarchical_content_target_size'],
            'hierarchical_content_max_size': ['advanced', 'chunking', 'hierarchical_content_max_size'],
            'hierarchical_content_overlap': ['advanced', 'chunking', 'hierarchical_content_overlap'],
            'llm_context_window': ['advanced', 'llm', 'context_window'],
            'chunk_for_llm_processing': ['advanced', 'llm', 'chunk_for_llm_processing'],
            'max_chunks_for_refine': ['advanced', 'llm', 'max_chunks_for_refine']
        }
        
        if key in mapping:
            try:
                # 检查AI是否启用
                ai_enabled = self._get_nested_value(['ai_settings', 'enabled'], default=True)
                if not ai_enabled and key.startswith(('openai_', 'embedding_')):
                    # AI已禁用，返回None使相关功能不可用
                    return None
                
                path = mapping[key]
                value = self._get_nested_value(path)
                return value
            except (KeyError, TypeError):
                return None
        
        return None
    
    def _get_nested_value(self, path: list, default=None):
        """从嵌套字典中获取值"""
        try:
            value = self.json_config
            for key in path:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def is_ai_enabled(self) -> bool:
        """检查AI是否启用"""
        if self.json_config:
            return self._get_nested_value(['ai_settings', 'enabled'], default=True)
        # 如果没有JSON配置，根据是否有API密钥判断
        return bool(original_settings.openai_api_key)

class DynamicSettingsProxy:
    """动态配置代理类，提供与原Settings类相同的接口"""
    
    def __init__(self):
        self.dynamic_settings = DynamicSettings()
        self._original_settings = original_settings
    
    def __getattr__(self, name: str):
        """动态获取配置属性"""
        # 先尝试从动态配置获取
        try:
            value = self.dynamic_settings.get_value(name)
            if value is not None:
                return value
        except Exception as e:
            logger.warning(f"从动态配置获取 {name} 失败: {e}")
        
        # 回退到原始配置
        return getattr(self._original_settings, name)
    
    def reload_config(self):
        """重新加载配置"""
        self.dynamic_settings.reload_config()
    
    def get_embedding_base_url(self) -> Optional[str]:
        """获取嵌入模型API地址，优先使用专用配置，否则回退到通用配置"""
        embedding_base_url = self.dynamic_settings.get_value('embedding_base_url')
        if embedding_base_url:
            return embedding_base_url
        return self.dynamic_settings.get_value('openai_base_url')
    
    def get_embedding_api_key(self) -> Optional[str]:
        """获取嵌入模型API密钥，优先使用专用配置，否则回退到通用配置"""
        embedding_api_key = self.dynamic_settings.get_value('embedding_api_key')
        if embedding_api_key:
            return embedding_api_key
        return self.dynamic_settings.get_value('openai_api_key')
    
    def is_ai_enabled(self) -> bool:
        """检查AI是否启用"""
        return self.dynamic_settings.is_ai_enabled()

# 创建动态配置实例，替换原有的settings
dynamic_settings = DynamicSettingsProxy()

# 保持向后兼容，导出settings名称
settings = dynamic_settings