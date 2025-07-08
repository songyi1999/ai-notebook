"""配置管理API"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from ..schemas.config import (
    AppConfig, ConfigUpdateRequest, ConfigValidationResult,
    ConfigTestResult, AISettings
)
from ..services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

@router.get("/", response_model=AppConfig)
async def get_config():
    """获取当前配置"""
    try:
        config = config_service.get_config()
        return config
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )

@router.post("/update")
async def update_config(update_request: ConfigUpdateRequest):
    """更新配置"""
    try:
        success = config_service.update_config(update_request)
        
        if success:
            return {"success": True, "message": "配置更新成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="配置更新失败"
            )
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新配置失败: {str(e)}"
        )

@router.post("/validate", response_model=ConfigValidationResult)
async def validate_config(config: AppConfig = None):
    """验证配置"""
    try:
        if config is None:
            # 验证当前配置
            result = config_service.validate_config()
        else:
            # 验证指定配置
            result = config_service.validate_config(config)
        
        return result
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置验证失败: {str(e)}"
        )

@router.get("/test", response_model=ConfigTestResult)
async def test_ai_connectivity():
    """测试AI连接性"""
    try:
        result = config_service.test_ai_connectivity()
        return result
    except Exception as e:
        logger.error(f"AI连接测试失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI连接测试失败: {str(e)}"
        )

@router.post("/test", response_model=ConfigTestResult)
async def test_config_connectivity(config: AppConfig):
    """测试指定配置的AI连接性"""
    try:
        result = config_service.test_ai_connectivity(config)
        return result
    except Exception as e:
        logger.error(f"配置连接测试失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置连接测试失败: {str(e)}"
        )

@router.get("/presets")
async def get_presets():
    """获取可用的预设配置"""
    try:
        presets = config_service.get_available_presets()
        return {"presets": presets}
    except Exception as e:
        logger.error(f"获取预设失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预设失败: {str(e)}"
        )

@router.post("/presets/{preset_name}/apply")
async def apply_preset(preset_name: str):
    """应用预设配置"""
    try:
        success = config_service.apply_preset(preset_name)
        
        if success:
            return {"success": True, "message": f"预设 '{preset_name}' 应用成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"预设 '{preset_name}' 不存在或应用失败"
            )
    except Exception as e:
        logger.error(f"应用预设失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"应用预设失败: {str(e)}"
        )

@router.post("/reset")
async def reset_config():
    """重置为默认配置"""
    try:
        success = config_service.reset_to_default()
        
        if success:
            return {"success": True, "message": "配置已重置为默认值"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重置配置失败"
            )
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置配置失败: {str(e)}"
        )

@router.get("/status")
async def get_ai_status():
    """获取当前AI状态"""
    try:
        status_info = config_service.get_current_ai_status()
        return status_info
    except Exception as e:
        logger.error(f"获取AI状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取AI状态失败: {str(e)}"
        )

@router.post("/ai/enable")
async def enable_ai(ai_settings: AISettings):
    """启用AI功能"""
    try:
        update_request = ConfigUpdateRequest(ai_settings=ai_settings)
        success = config_service.update_config(update_request)
        
        if success:
            return {"success": True, "message": "AI功能已启用"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="启用AI功能失败"
            )
    except Exception as e:
        logger.error(f"启用AI功能失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启用AI功能失败: {str(e)}"
        )

@router.post("/ai/disable")
async def disable_ai():
    """禁用AI功能"""
    try:
        from ..schemas.config import FallbackMode
        
        ai_settings = AISettings(
            enabled=False,
            fallback_mode=FallbackMode.NOTES_ONLY
        )
        
        update_request = ConfigUpdateRequest(ai_settings=ai_settings)
        success = config_service.update_config(update_request)
        
        if success:
            return {"success": True, "message": "AI功能已禁用，切换为纯笔记模式"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="禁用AI功能失败"
            )
    except Exception as e:
        logger.error(f"禁用AI功能失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"禁用AI功能失败: {str(e)}"
        )

@router.get("/export")
async def export_config():
    """导出配置文件"""
    try:
        config = config_service.get_config()
        return {
            "config": config.dict(),
            "exported_at": config.meta.last_updated,
            "version": config.meta.config_version
        }
    except Exception as e:
        logger.error(f"导出配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出配置失败: {str(e)}"
        )

@router.post("/import")
async def import_config(config_data: Dict[str, Any]):
    """导入配置文件"""
    try:
        # 验证并解析配置
        config = AppConfig(**config_data)
        
        # 验证配置有效性
        validation_result = config_service.validate_config(config)
        
        if not validation_result.valid:
            return {
                "success": False,
                "message": "配置验证失败",
                "errors": validation_result.errors
            }
        
        # 更新配置
        config_service._app_config = config
        success = config_service.save_config()
        
        if success:
            return {"success": True, "message": "配置导入成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存导入的配置失败"
            )
    except Exception as e:
        logger.error(f"导入配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入配置失败: {str(e)}"
        )