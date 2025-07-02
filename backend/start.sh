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
echo "1. 清理现有SQLite数据库文件"
echo "2. 清理现有向量数据库目录"
echo "3. 重新创建数据库表结构"
echo "4. 扫描notes目录中的所有文件"
echo "5. 重建SQLite索引和FTS全文搜索"
echo "6. 重建向量索引"
echo "================================================"

# 强制清理损坏的数据库文件
echo "清理现有数据库文件..."
rm -f data/*.db
rm -f data/*.db-*
rm -rf data/chroma_db
mkdir -p data/chroma_db

# 启动FastAPI应用
echo "启动FastAPI应用..."
echo "监听地址: 0.0.0.0:8000"
echo "API文档: http://localhost:8000/docs"
echo "================================================"

# 使用uvicorn启动，启用重载和详细日志
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info 