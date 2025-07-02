#!/bin/bash

# 后台任务处理器启动脚本
# 用于设置定时任务，每5分钟执行一次任务处理

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 任务处理器脚本路径
TASK_PROCESSOR_SCRIPT="$PROJECT_ROOT/backend/app/scripts/task_processor.py"

# Python 环境路径（根据实际情况调整）
PYTHON_PATH="python3"

# 日志文件路径
LOG_DIR="$PROJECT_ROOT/data"
LOG_FILE="$LOG_DIR/task_processor.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "=== 后台任务处理器启动脚本 ==="
echo "项目根目录: $PROJECT_ROOT"
echo "任务处理器脚本: $TASK_PROCESSOR_SCRIPT"
echo "日志文件: $LOG_FILE"

# 检查任务处理器脚本是否存在
if [ ! -f "$TASK_PROCESSOR_SCRIPT" ]; then
    echo "错误: 任务处理器脚本不存在: $TASK_PROCESSOR_SCRIPT"
    exit 1
fi

# 创建 cron 任务条目
CRON_ENTRY="*/5 * * * * cd $PROJECT_ROOT && $PYTHON_PATH $TASK_PROCESSOR_SCRIPT >> $LOG_FILE 2>&1"

echo "准备添加的 cron 任务:"
echo "$CRON_ENTRY"

# 检查是否已存在相同的 cron 任务
if crontab -l 2>/dev/null | grep -q "$TASK_PROCESSOR_SCRIPT"; then
    echo "警告: 已存在相关的 cron 任务，请手动检查并清理重复任务"
    echo "当前 cron 任务:"
    crontab -l 2>/dev/null | grep "$TASK_PROCESSOR_SCRIPT"
else
    # 添加新的 cron 任务
    echo "添加新的 cron 任务..."
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    
    if [ $? -eq 0 ]; then
        echo "✓ cron 任务添加成功"
        echo "任务将每5分钟执行一次"
    else
        echo "✗ cron 任务添加失败"
        exit 1
    fi
fi

echo ""
echo "当前所有 cron 任务:"
crontab -l 2>/dev/null

echo ""
echo "=== 手动测试任务处理器 ==="
echo "可以使用以下命令手动测试任务处理器:"
echo "cd $PROJECT_ROOT && $PYTHON_PATH $TASK_PROCESSOR_SCRIPT"

echo ""
echo "=== 查看日志 ==="
echo "可以使用以下命令查看任务处理器日志:"
echo "tail -f $LOG_FILE"

echo ""
echo "=== 停止定时任务 ==="
echo "如需停止定时任务，请运行:"
echo "crontab -e"
echo "然后删除包含 '$TASK_PROCESSOR_SCRIPT' 的行" 