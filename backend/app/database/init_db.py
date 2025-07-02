from sqlalchemy.schema import CreateTable
from sqlalchemy import text
from ..models.base import Base, engine
from ..models.file import File
from ..models.link import Link
from ..models.embedding import Embedding
from ..models.tag import Tag
from ..models.file_tag import FileTag
from ..models.search_history import SearchHistory
from ..models.chat_session import ChatSession
from ..models.chat_message import ChatMessage
from ..models.system_config import SystemConfig
from ..models.pending_task import PendingTask
import logging
import os
import shutil
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)

def clean_existing_data():
    """清理现有的数据库和向量库文件"""
    logger.info("开始清理现有数据...")
    
    try:
        # 1. 删除SQLite数据库文件
        db_path = settings.database_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"已删除SQLite数据库文件: {db_path}")
        
        # 2. 删除ChromaDB向量数据库目录
        chroma_path = Path(settings.chroma_db_path)
        if chroma_path.exists():
            shutil.rmtree(chroma_path)
            logger.info(f"已删除ChromaDB向量数据库目录: {chroma_path}")
        
        # 3. 重新创建ChromaDB向量数据库目录
        chroma_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ChromaDB向量数据库目录已重新创建: {chroma_path}")
        
        logger.info("数据清理完成")
        return True
        
    except Exception as e:
        logger.error(f"清理数据失败: {e}")
        return False

def init_db():
    """
    初始化数据库，每次启动时都重新构建所有索引。
    使用双存储架构：SQLite(元数据) + ChromaDB(向量)
    """
    logger.info("开始初始化数据库...")
    logger.info("架构说明: SQLite存储元数据，ChromaDB存储向量数据")
    
    try:
        # 1. 清理现有数据
        if not clean_existing_data():
            logger.error("清理现有数据失败，但继续初始化...")
        
        # 2. 创建所有非FTS5表
        Base.metadata.create_all(bind=engine)
        logger.info("已创建所有标准数据库表。")


        
        # 4. ChromaDB将由LangChain-Chroma自动管理
        logger.info("ChromaDB将由LangChain-Chroma自动管理")
        logger.info(f"ChromaDB路径: {settings.chroma_db_path}")
        
        # 5. 扫描文件并创建后台索引任务（非阻塞）
        logger.info("开始扫描笔记目录并创建后台索引任务...")
        try:
            from ..services.index_service import IndexService
            from ..services.task_processor_service import TaskProcessorService
            from ..database.session import get_db
            
            db = next(get_db())
            index_service = IndexService(db)
            task_service = TaskProcessorService(db)
            
            # 扫描notes目录中的所有文件
            file_infos = index_service.scan_notes_directory()
            logger.info(f"扫描完成，发现 {len(file_infos)} 个文件")
            
            # 为每个文件创建数据库记录（如果不存在）
            created_count = 0
            task_count = 0
            
            for file_info in file_infos:
                try:
                    # 检查文件是否已存在于数据库中
                    from ..models.file import File
                    existing_file = db.query(File).filter(
                        File.file_path == file_info['file_path']
                    ).first()
                    
                    if not existing_file:
                        # 创建新的文件记录
                        new_file = File(
                            title=file_info['title'],
                            content=file_info['content'],
                            file_path=file_info['file_path'],
                            parent_folder=file_info['parent_folder'],
                            file_size=file_info['file_size']
                        )
                        db.add(new_file)
                        db.flush()  # 获取ID但不提交
                        
                        # 为新文件创建向量索引任务
                        task_service.create_pending_task(
                            file_id=new_file.id,
                            task_type='vector_index',
                            priority=1
                        )
                        
                        created_count += 1
                        task_count += 1
                        
                    else:
                        # 文件已存在，检查是否需要更新索引
                        # 这里可以根据文件修改时间来决定是否重建索引
                        if file_info['size'] != existing_file.file_size:
                            # 文件大小变化，可能内容有更新，重建索引
                            task_service.create_pending_task(
                                file_id=existing_file.id,
                                task_type='vector_index',
                                priority=3
                            )
                            task_count += 1
                
                except Exception as e:
                    logger.error(f"处理文件失败: {file_info.get('file_path', '未知')}, 错误: {e}")
                    continue
            
            db.commit()
            
            logger.info(f"数据库记录创建完成: 新建 {created_count} 个文件记录")
            logger.info(f"后台任务创建完成: 创建 {task_count} 个索引任务")
            logger.info("系统将在后台异步处理ChromaDB索引构建，不影响启动速度")
            
            db.close()
            
        except Exception as e:
            logger.error(f"创建后台索引任务失败: {e}")
            # 不抛出异常，让数据库初始化继续完成
        
        logger.info("数据库初始化完成。")
        logger.info("双存储架构就绪: SQLite(元数据) + ChromaDB(向量)")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False 