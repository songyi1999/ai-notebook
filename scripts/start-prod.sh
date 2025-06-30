#!/bin/bash

echo "启动AI笔记本项目..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: 请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 请先安装Docker Compose"
    exit 1
fi

# 创建数据目录
mkdir -p ./data/notes ./data/chroma_db

# 设置权限
chmod 755 ./data

# 启动服务
echo "启动容器服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

echo "启动完成！"
echo ""
echo "注意: 请确保主机上已安装并启动Ollama服务"
echo "如需安装Ollama，请访问: https://ollama.ai"
echo "前端访问地址: http://localhost:3000"
echo "后端API地址: http://localhost:8000"
echo "API文档地址: http://localhost:8000/docs" 