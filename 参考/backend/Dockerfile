FROM docker.yifus.win/python:3.11-slim

WORKDIR /app

# 复制整个目录
COPY . .

# 安装Python依赖
RUN pip install  -r Code/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 设置环境变量
ENV PYTHONPATH=/app/Code


# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "Code.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 