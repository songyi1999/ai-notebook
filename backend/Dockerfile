FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
# RUN apt-get update && apt-get install -y \
#     gcc \
#     g++ \
#     && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install  -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/notes /app/data/chroma_db

# 设置权限
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["./start.sh"] 