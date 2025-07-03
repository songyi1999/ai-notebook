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
from ..models.mcp_server import MCPServer, MCPTool, MCPToolCall
import logging
import os
import shutil
from pathlib import Path
from ..config import settings
from sqlalchemy import inspect

logger = logging.getLogger(__name__)

def check_database_health() -> dict:
    """检查数据库健康状态"""
    logger.info("开始检查数据库健康状态...")
    
    health_status = {
        "sqlite_healthy": False,
        "chromadb_healthy": False,
        "tables_exist": False,
        "can_connect": False,
        "error_message": None,
        "missing_tables": [],
        "integrity_issues": []
    }
    
    try:
        # 1. 检查SQLite数据库文件是否存在
        db_path = settings.database_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            health_status["error_message"] = f"SQLite数据库文件不存在: {db_path}"
            logger.warning(health_status["error_message"])
            return health_status
        
        # 2. 检查数据库连接
        try:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            health_status["can_connect"] = True
            logger.info("SQLite数据库连接正常")
        except Exception as e:
            health_status["error_message"] = f"无法连接SQLite数据库: {e}"
            logger.error(health_status["error_message"])
            return health_status
        
        # 3. 检查核心表是否存在
        required_tables = ['files', 'tags', 'links', 'embeddings', 'pending_tasks']
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            health_status["error_message"] = f"缺少核心表: {missing_tables}"
            health_status["missing_tables"] = missing_tables
            logger.warning(health_status["error_message"])
        else:
            health_status["tables_exist"] = True
            logger.info("SQLite数据库表结构完整")
        
        # 4. 检查数据库完整性
        try:
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA integrity_check"))
                integrity_result = result.fetchone()
                if integrity_result and integrity_result[0] != "ok":
                    health_status["integrity_issues"].append(str(integrity_result[0]))
                    health_status["error_message"] = f"数据库完整性检查失败: {integrity_result[0]}"
                    logger.warning(health_status["error_message"])
                else:
                    logger.info("数据库完整性检查通过")
        except Exception as e:
            health_status["integrity_issues"].append(str(e))
            health_status["error_message"] = f"数据库完整性检查异常: {e}"
            logger.warning(health_status["error_message"])
        
        # 5. 检查ChromaDB目录
        chroma_path = Path(settings.chroma_db_path)
        if not chroma_path.exists():
            health_status["error_message"] = f"ChromaDB目录不存在: {chroma_path}"
            logger.warning(health_status["error_message"])
        else:
            # 测试ChromaDB目录访问权限
            try:
                if os.access(chroma_path, os.R_OK | os.W_OK):
                    health_status["chromadb_healthy"] = True
                    logger.info("ChromaDB目录访问正常")
                else:
                    health_status["error_message"] = f"ChromaDB目录无法访问: {chroma_path}"
                    logger.warning(health_status["error_message"])
            except Exception as e:
                health_status["error_message"] = f"ChromaDB检测失败: {e}"
                logger.warning(health_status["error_message"])
                health_status["chromadb_healthy"] = False
        
        # 6. 执行数据库查询测试
        try:
            from ..database.session import get_db
            db = next(get_db())
            
            # 测试查询files表
            file_count = db.query(File).count()
            logger.info(f"数据库查询测试成功，文件记录数: {file_count}")
            
            db.close()
        except Exception as e:
            health_status["error_message"] = f"数据库查询测试失败: {e}"
            logger.error(health_status["error_message"])
            return health_status
        
        # 7. 综合评估健康状态
        if (health_status["can_connect"] and 
            health_status["tables_exist"] and 
            not health_status["integrity_issues"] and
            health_status["chromadb_healthy"]):
            health_status["sqlite_healthy"] = True
            logger.info("数据库健康检查完成 - 状态良好")
        else:
            logger.warning("数据库健康检查完成 - 发现问题")
        
        return health_status
        
    except Exception as e:
        health_status["error_message"] = f"健康检查异常: {e}"
        logger.error(health_status["error_message"])
        return health_status

def repair_database(health_status: dict) -> bool:
    """尝试修复数据库问题"""
    logger.info("开始尝试修复数据库...")
    repair_success = True
    
    try:
        # 1. 修复缺失的表
        if health_status.get("missing_tables"):
            logger.info(f"尝试修复缺失的表: {health_status['missing_tables']}")
            try:
                # 只创建缺失的表，不影响现有数据
                Base.metadata.create_all(bind=engine)
                logger.info("成功创建缺失的表")
            except Exception as e:
                logger.error(f"创建缺失表失败: {e}")
                repair_success = False
        
        # 2. 修复数据库完整性问题
        if health_status.get("integrity_issues"):
            logger.info("尝试修复数据库完整性问题...")
            try:
                with engine.connect() as conn:
                    # 尝试重建索引
                    conn.execute(text("REINDEX"))
                    logger.info("重建数据库索引完成")
                    
                    # 再次检查完整性
                    result = conn.execute(text("PRAGMA integrity_check"))
                    integrity_result = result.fetchone()
                    if integrity_result and integrity_result[0] == "ok":
                        logger.info("数据库完整性修复成功")
                    else:
                        logger.warning(f"数据库完整性修复后仍有问题: {integrity_result[0]}")
                        repair_success = False
            except Exception as e:
                logger.error(f"修复数据库完整性失败: {e}")
                repair_success = False
        
        # 3. 修复ChromaDB目录问题
        chroma_path = Path(settings.chroma_db_path)
        if not chroma_path.exists():
            logger.info("尝试修复ChromaDB目录...")
            try:
                chroma_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"成功创建ChromaDB目录: {chroma_path}")
            except Exception as e:
                logger.error(f"创建ChromaDB目录失败: {e}")
                repair_success = False
        
        # 4. 修复ChromaDB目录权限
        if chroma_path.exists() and not os.access(chroma_path, os.R_OK | os.W_OK):
            logger.info("尝试修复ChromaDB目录权限...")
            try:
                os.chmod(chroma_path, 0o755)
                logger.info("ChromaDB目录权限修复成功")
            except Exception as e:
                logger.error(f"修复ChromaDB目录权限失败: {e}")
                repair_success = False
        
        # 5. 清理可能损坏的临时文件
        try:
            db_path = settings.database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            
            # 清理SQLite临时文件
            for temp_file in [f"{db_path}-wal", f"{db_path}-shm", f"{db_path}-journal"]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.info(f"已清理临时文件: {temp_file}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {temp_file}, 错误: {e}")
        except Exception as e:
            logger.warning(f"清理临时文件时出错: {e}")
        
        if repair_success:
            logger.info("数据库修复完成")
        else:
            logger.warning("数据库修复部分失败，可能需要重建")
        
        return repair_success
        
    except Exception as e:
        logger.error(f"数据库修复过程异常: {e}")
        return False

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
    智能初始化数据库：检查健康状态 -> 尝试修复 -> 重建（如果修复失败）。
    使用双存储架构：SQLite(元数据) + ChromaDB(向量)
    """
    logger.info("开始智能初始化数据库...")
    logger.info("架构说明: SQLite存储元数据，ChromaDB存储向量数据")
    
    try:
        # 1. 检查数据库健康状态
        health_status = check_database_health()
        
        need_repair = False
        need_rebuild = False
        
        # 2. 判断是否需要修复或重建
        if not health_status["sqlite_healthy"]:
            if health_status["can_connect"]:
                # 数据库可连接但有问题，尝试修复
                need_repair = True
                logger.warning("检测到数据库问题，尝试修复...")
            else:
                # 数据库无法连接，直接重建
                need_rebuild = True
                logger.warning("数据库无法连接，需要重建")
        elif not health_status["chromadb_healthy"]:
            # ChromaDB问题，尝试修复
            need_repair = True
            logger.warning("检测到ChromaDB问题，尝试修复...")
        else:
            logger.info("数据库状态良好，跳过修复和重建")
        
        # 3. 尝试修复
        if need_repair and not need_rebuild:
            logger.info("开始尝试修复数据库...")
            repair_success = repair_database(health_status)
            
            if repair_success:
                # 修复后重新检查健康状态
                logger.info("修复完成，重新检查数据库健康状态...")
                new_health_status = check_database_health()
                
                if new_health_status["sqlite_healthy"] and new_health_status["chromadb_healthy"]:
                    logger.info("数据库修复成功，健康状态良好")
                    need_rebuild = False
                else:
                    logger.warning("修复后数据库仍有问题，需要重建")
                    need_rebuild = True
            else:
                logger.warning("数据库修复失败，需要重建")
                need_rebuild = True
        
        # 4. 如果修复失败或无法修复，则重建
        if need_rebuild:
            logger.info("开始重建数据库...")
            if not clean_existing_data():
                logger.error("清理现有数据失败，但继续初始化...")
        elif not need_repair:
            logger.info("数据库健康，保持现有数据")
        
        # 5. 创建或确保所有表存在
        Base.metadata.create_all(bind=engine)
        if need_rebuild:
            logger.info("已重新创建所有数据库表")
        elif need_repair:
            logger.info("已确保所有数据库表存在（修复模式）")
        else:
            logger.info("已确认所有数据库表存在")

        # 6. 确保ChromaDB目录存在
        chroma_path = Path(settings.chroma_db_path)
        if not chroma_path.exists():
            chroma_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"已创建ChromaDB目录: {chroma_path}")
        
        logger.info("ChromaDB将由LangChain-Chroma自动管理")
        logger.info(f"ChromaDB路径: {settings.chroma_db_path}")
        
        # 7. 扫描文件并创建后台索引任务（非阻塞）
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
            updated_count = 0
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
                        if file_info['file_size'] != existing_file.file_size:
                            # 文件大小变化，可能内容有更新，更新记录并重建索引
                            existing_file.content = file_info['content']
                            existing_file.title = file_info['title']
                            existing_file.file_size = file_info['file_size']
                            
                            task_service.create_pending_task(
                                file_id=existing_file.id,
                                task_type='vector_index',
                                priority=2
                            )
                            updated_count += 1
                            task_count += 1
                        elif need_rebuild:
                            # 如果是重建模式，为所有文件创建索引任务
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
            
            logger.info(f"数据库记录处理完成: 新建 {created_count} 个，更新 {updated_count} 个")
            logger.info(f"后台任务创建完成: 创建 {task_count} 个索引任务")
            
            if need_rebuild:
                logger.info("重建模式：系统将在后台重建所有向量索引")
            elif need_repair:
                logger.info("修复模式：系统将在后台处理受影响的文件索引")
            else:
                logger.info("增量模式：系统将在后台处理新增和修改的文件索引")
            
            db.close()
            
        except Exception as e:
            logger.error(f"创建后台索引任务失败: {e}")
            # 不抛出异常，让数据库初始化继续完成
        
        logger.info("数据库初始化完成。")
        if need_rebuild:
            logger.info("双存储架构重建完成: SQLite(元数据) + ChromaDB(向量)")
        elif need_repair:
            logger.info("双存储架构修复完成: SQLite(元数据) + ChromaDB(向量)")
        else:
            logger.info("双存储架构检查完成: SQLite(元数据) + ChromaDB(向量)")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False 