#!/usr/bin/env python3
"""
后台任务处理脚本
用于定时处理待处理任务队列，每5分钟执行一次
"""

import sys
import os
import logging
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.database.session import SessionLocal
from backend.app.services.task_processor_service import TaskProcessorService

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/task_processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("启动后台任务处理器")
    
    try:
        # 创建数据库会话
        db = SessionLocal()
        
        try:
            # 创建任务处理服务
            task_processor = TaskProcessorService(db)
            
            # 处理所有待处理任务
            task_processor.process_all_pending_tasks()
            
            # 清理旧任务（保留7天）
            task_processor.cleanup_old_tasks(days=7)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"后台任务处理器执行失败: {e}")
        sys.exit(1)
    
    logger.info("后台任务处理器执行完成")

if __name__ == "__main__":
    main() 