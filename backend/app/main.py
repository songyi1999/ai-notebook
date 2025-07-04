from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database.init_db import init_db
from .api import files, links, tags, ai, index, mcp, file_upload
from .config import settings
import logging

# 配置日志
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI笔记本后端API",
    description="纯本地、AI增强的个人知识管理系统后端服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
        logger.info(f"笔记目录: {settings.notes_directory}")
        logger.info(f"OpenAI配置状态: {'已配置' if settings.openai_api_key else '未配置'}")
        
        # 启动后台任务处理（非阻塞）
        import asyncio
        import threading
        def start_background_tasks():
            try:
                from .services.task_processor_service import TaskProcessorService
                from .database.session import get_db
                
                db = next(get_db())
                task_service = TaskProcessorService(db)
                
                logger.info("开始处理后台索引任务...")
                task_service.process_all_pending_tasks()
                logger.info("后台索引任务处理完成")
                
                db.close()
                
            except Exception as e:
                logger.error(f"后台任务处理失败: {e}")
        
        # 在单独的线程中启动后台任务，不阻塞应用启动
        background_thread = threading.Thread(target=start_background_tasks, daemon=True)
        background_thread.start()
        logger.info("后台任务处理线程已启动")
        
    else:
        logger.error("数据库初始化失败，请检查日志。")

# 注册API路由
app.include_router(files.router, prefix=settings.api_prefix, tags=["files"])
app.include_router(links.router, prefix=settings.api_prefix, tags=["links"])
app.include_router(tags.router, prefix=settings.api_prefix, tags=["tags"])
app.include_router(ai.router, prefix=settings.api_prefix, tags=["ai"])
app.include_router(index.router, prefix=f"{settings.api_prefix}/index", tags=["index"])
app.include_router(mcp.router, prefix=settings.api_prefix, tags=["mcp"])
app.include_router(file_upload.router, prefix=f"{settings.api_prefix}/file-upload", tags=["file-upload"])

@app.get("/")
async def root():
    return {
        "message": "AI笔记本后端服务运行中", 
        "version": "1.0.0",
        "ai_enabled": settings.openai_api_key is not None,
        "mcp_enabled": True
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "ai-notebook-backend",
        "notes_directory": settings.notes_directory,
        "ai_configured": settings.openai_api_key is not None,
        "mcp_configured": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 