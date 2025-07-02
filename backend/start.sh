#!/bin/bash

echo "================================================"
echo "AI笔记本项目 - 后端服务启动"
echo "================================================"

# 检查Python环境
echo "检查Python环境..."
python --version

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 创建必要的目录
echo "创建数据目录..."
mkdir -p data
mkdir -p data/chroma_db
mkdir -p ../notes

echo "================================================"
echo "启动时将执行以下操作："
echo "1. 检查数据库健康状态"
echo "2. 如果数据库损坏，则清理并重建"
echo "3. 如果数据库正常，则保持现有数据"
echo "4. 扫描notes目录中的所有文件"
echo "5. 增量更新数据库索引"
echo "6. 在后台处理向量索引更新"
echo "================================================"

# 启动FastAPI应用
echo "启动FastAPI应用..."
echo "监听地址: 0.0.0.0:8000"
echo "API文档: http://localhost:8000/docs"
echo "================================================"

# 使用uvicorn启动，启用重载和详细日志
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info 