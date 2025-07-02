"""
FastAPI应用主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from config import settings
from .routers import chat, upload

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    chat.router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)

# 注册文件上传路由
app.include_router(
    upload.router,
    prefix=settings.API_V1_STR,
    tags=["upload"]
)

@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "欢迎使用医疗评价大模型API",
        "version": "1.0.0"
    }
    
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "Code.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式下启用热重载
    ) 