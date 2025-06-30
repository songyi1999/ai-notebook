from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database.init_db import init_db
from .api import files, links, tags
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI笔记本后端API",
    description="纯本地、AI增强的个人知识管理系统后端服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("应用启动事件: 正在初始化数据库...")
    success = init_db()
    if success:
        logger.info("数据库初始化成功。")
    else:
        logger.error("数据库初始化失败，请检查日志。")

# 注册API路由
app.include_router(files.router, prefix="/api/v1", tags=["files"])
app.include_router(links.router, prefix="/api/v1", tags=["links"])
app.include_router(tags.router, prefix="/api/v1", tags=["tags"])

@app.get("/")
async def root():
    return {"message": "AI笔记本后端服务运行中", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-notebook-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 