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
import logging

logger = logging.getLogger(__name__)

def init_db():
    """
    初始化数据库，创建所有定义的表，包括FTS5虚拟表。
    """
    logger.info("开始初始化数据库...")
    try:
        # 创建所有非FTS5表
        Base.metadata.create_all(bind=engine)
        logger.info("已创建所有标准数据库表。")

        # 创建FTS5虚拟表
        with engine.connect() as connection:
            # 检查 files_fts 表是否已存在
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='files_fts';"))
            if result.fetchone() is None:
                connection.execute(text("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(title, content, content='files', content_rowid='id');
                """))
                logger.info("已创建 files_fts 全文搜索虚拟表。")
            else:
                logger.info("files_fts 全文搜索虚拟表已存在，跳过创建。")

            # 创建插入触发器
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='files_ai';"))
            if result.fetchone() is None:
                connection.execute(text("""
                    CREATE TRIGGER files_ai AFTER INSERT ON files BEGIN
                        INSERT INTO files_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
                    END;
                """))
                logger.info("已创建 files_ai 插入触发器。")
            else:
                logger.info("files_ai 插入触发器已存在，跳过创建。")
            
            # 创建更新触发器
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='files_au';"))
            if result.fetchone() is None:
                connection.execute(text("""
                    CREATE TRIGGER files_au AFTER UPDATE ON files BEGIN
                        INSERT INTO files_fts(files_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
                        INSERT INTO files_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
                    END;
                """))
                logger.info("已创建 files_au 更新触发器。")
            else:
                logger.info("files_au 更新触发器已存在，跳过创建。")

            # 创建删除触发器
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='files_ad';"))
            if result.fetchone() is None:
                connection.execute(text("""
                    CREATE TRIGGER files_ad AFTER DELETE ON files BEGIN
                        INSERT INTO files_fts(files_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
                    END;
                """))
                logger.info("已创建 files_ad 删除触发器。")
            else:
                logger.info("files_ad 删除触发器已存在，跳过创建。")
            
            connection.commit()
        logger.info("数据库初始化完成。")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False 