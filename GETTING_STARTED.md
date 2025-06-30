# AI笔记本项目启动指南

## 项目概述

AI笔记本是一个纯本地、AI增强的个人知识管理系统。项目基础架构已搭建完成，包含前端、后端和AI服务的完整容器化部署方案。

## 项目结构

```
AI笔记本项目/
├── frontend/              # React前端应用
├── backend/               # FastAPI后端应用
├── scripts/               # 启动和部署脚本
├── data/                  # 数据存储目录
├── notes/                 # Markdown笔记文件
├── docker-compose.yml     # 生产环境服务编排
└── env.example           # 环境变量示例
```

## 快速启动

### 前置要求

- Docker 和 Docker Compose
- 一个在主机上运行的、提供OpenAI兼容API的本地AI服务（如Ollama, LM Studio等）

> **重要**: 请先确保您的本地AI服务已启动。详细安装指南请参考 [LOCAL_LLM_SETUP.md](LOCAL_LLM_SETUP.md)

### 生产环境启动

```bash
# 复制并配置环境变量
cp env.example .env
# 根据 LOCAL_LLM_SETUP.md 指南修改 .env 文件中的 API_URL 和模型名称

# 编译前端(需在 frontend 目录执行)
cd frontend
npm install
npm run build
cd ..

# 启动生产环境
./scripts/start-prod.sh
```

### 开发环境启动

```bash
# 启动开发环境（支持热重载）
./scripts/start-dev.sh
```

## 服务访问

启动成功后，可以通过以下地址访问各服务：

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **本地AI服务**: (取决于您的配置, 例如 http://localhost:11434)

## 项目状态

### ✅ 已完成

- 项目目录结构搭建
- Docker容器化配置
- 前端React+TypeScript基础框架
- 后端FastAPI基础框架
- 2服务架构（frontend, backend），可连接到外部AI服务
- 开发和生产环境配置
- 启动脚本和工具

### 🚧 开发中

- 核心功能模块
- 数据库模型
- API接口
- 前端组件

### 📋 待开发

- Markdown编辑器
- 文件管理系统
- 搜索功能
- AI问答功能
- 双向链接
- 链接图谱

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design
- **后端**: FastAPI + Python 3.11 + SQLAlchemy
- **数据库**: SQLite + ChromaDB
- **AI模型**: 通过OpenAI兼容接口连接本地AI服务
- **部署**: Docker + Docker Compose

## 开发指南

详细的开发指南请参考：

- [开发规范](.cursor/rules/development-standards.mdc)
- [架构设计指导](.cursor/rules/architecture-guide.mdc)
- [前端开发指导](.cursor/rules/frontend-guide.mdc)
- [后端开发指导](.cursor/rules/backend-guide.mdc)
- [AI集成指导](.cursor/rules/ai-integration.mdc)
- [Docker部署指导](.cursor/rules/docker-deployment.mdc)

## 故障排除

### 常见问题

1. **端口冲突**: 确保3000、8000以及您本地AI服务所用端口未被占用。
2. **Docker权限**: 确保Docker服务正常运行且有足够权限。
3. **内存不足**: 本地AI模型服务需要较多内存，建议至少8GB可用内存。

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs frontend
docker-compose logs backend
```

## 贡献指南

1. 遵循项目的开发规范
2. 提交前运行测试
3. 更新相关文档
4. 保持代码简洁和注释完整

## 联系方式

如有问题，请查看项目文档或提交Issue。 