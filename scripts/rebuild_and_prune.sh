#!/usr/bin/env bash
# scripts/rebuild_and_prune.sh
# ------------------------------------------------------------
# 目的: 开发阶段一键重启 Docker 服务并自动清理旧镜像
# 使用: bash scripts/rebuild_and_prune.sh
# 说明:
#   1. 停止并删除旧容器 (--remove-orphans 同时移除孤立容器)
#   2. 重新构建镜像并启动容器
#   3. 删除所有 <none> (dangling) 镜像, 防止磁盘堆积
# ------------------------------------------------------------
set -euo pipefail

# 编译前端
echo "🔨 编译前端..."
cd frontend
npm run build
cd ..




# 停止并删除旧容器
echo "➡ 停止并删除旧容器..."
docker-compose down --remove-orphans

# 重新构建并启动
echo "🚀 重新构建并启动服务..."
docker-compose up -d --build

# 清理悬挂镜像
echo "🧹 清理悬挂(dangling)镜像..."
docker image prune -f

echo "✅ Docker 服务已重启且旧镜像已清理完毕" 