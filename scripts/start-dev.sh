#!/bin/bash

echo "启动开发环境..."

# 创建数据目录
mkdir -p ./data/notes ./data/chroma_db

# 启动容器（与生产环境一致）
docker-compose up -d

echo "开发环境启动完成！"
echo ""
echo "注意: 请确保主机上已安装并启动Ollama服务"
echo "如需安装Ollama，请访问: https://ollama.ai"
echo ""
echo "前端开发服务器: http://localhost:3000"
echo "后端开发服务器: http://localhost:8000"
echo "API文档地址: http://localhost:8000/docs" 