#!/bin/bash

# 等待数据库目录创建
mkdir -p /app/data/notes /app/data/chroma_db

# 启动FastAPI应用
uvicorn app.main:app --host 0.0.0.0 --port 8000 