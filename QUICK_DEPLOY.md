# 🚀 快速部署指南

## 一键部署

### Linux/macOS 用户
```bash
chmod +x setup.sh
./setup.sh
```

### Windows 用户
```cmd
setup.bat
```

## 手动部署

如果自动脚本遇到问题，可以按以下步骤手动部署：

### 1. 检查系统要求
- ✅ Docker 已安装
- ✅ Docker Compose 已安装

### 2. 创建必要目录
```bash
mkdir -p notes
mkdir -p backend/data/chroma_db
mkdir -p backend/data/uploads
```

### 3. 复制配置文件
```bash
cp docker-compose.yml.example docker-compose.yml
cp env.example .env
```

### 4. 配置AI服务
编辑 `.env` 文件，配置以下AI服务之一：

#### 选项1：Ollama (推荐)
```env
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.1:8b
```

#### 选项2：LM Studio
```env
OPENAI_BASE_URL=http://host.docker.internal:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL=your-model-name
```

#### 选项3：OpenAI API
```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-3.5-turbo
```

### 5. 启动服务
```bash
docker-compose up -d --build
```

### 6. 访问应用
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 常见问题

### Q: 端口被占用怎么办？
A: 修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "3001:80"  # 前端改为3001端口
  - "8001:8000"  # 后端改为8001端口
```

### Q: AI服务连接失败？
A: 检查以下几点：
1. AI服务是否正在运行
2. 端口是否正确
3. 模型是否已加载
4. 网络连接是否正常

### Q: 前端无法连接后端？
A: 检查：
1. 后端服务是否启动成功
2. 防火墙是否阻止连接
3. 环境变量 `REACT_APP_API_BASE_URL` 是否正确

### Q: 数据库初始化失败？
A: 删除数据目录重新启动：
```bash
rm -rf backend/data
docker-compose down
docker-compose up -d --build
```

## 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build

# 清理数据（慎用）
docker-compose down -v
rm -rf backend/data
```

## 故障排除

### 1. 检查Docker服务
```bash
docker --version
docker-compose --version
docker ps
```

### 2. 检查日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
```

### 3. 检查网络连接
```bash
# 测试后端健康检查
curl http://localhost:8000/health

# 测试前端
curl http://localhost:3000
```

### 4. 重置环境
```bash
# 完全重置（会删除所有数据）
docker-compose down -v
rm -rf backend/data
rm -rf notes/*
./setup.sh  # 或 setup.bat
```

## 更多帮助

- 📖 [项目说明](README.md)
- 🤖 [AI服务配置](LOCAL_LLM_SETUP.md)
- 🏁 [快速开始](GETTING_STARTED.md)
- 🐛 [问题反馈](https://github.com/your-repo/issues) 