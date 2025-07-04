#!/usr/bin/env python3
import sys
sys.path.append('.')
from app.database.session import get_db
from app.models.pending_task import PendingTask
from app.services.task_processor_service import TaskProcessorService

db = next(get_db())
task_service = TaskProcessorService(db)

# 检查待处理任务
pending_tasks = db.query(PendingTask).order_by(PendingTask.created_at.desc()).limit(10).all()
print(f'=== 待处理任务 ({len(pending_tasks)}) ===')
for task in pending_tasks:
    print(f'ID: {task.id}, 文件ID: {task.file_id}, 类型: {task.task_type}, 状态: {task.status}')
    print(f'文件路径: {task.file_path}')
    print(f'创建时间: {task.created_at}')
    print('---')

# 检查所有待处理任务数量
total_pending = db.query(PendingTask).filter(PendingTask.status == 'pending').count()
print(f'\n=== 统计信息 ===')
print(f'总待处理任务数: {total_pending}')

# 检查任务处理器状态
status = task_service.get_processor_status()
print(f'\n=== 任务处理器状态 ===')
print(f'运行中: {status.get("running", "未知")}')
print(f'状态: {status.get("status", "未知")}')
print(f'PID: {status.get("pid", "N/A")}')
print(f'消息: {status.get("message", "N/A")}')

db.close() 