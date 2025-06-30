# 本地大语言模型(LLM)服务安装与配置指南

## 概述

AI笔记本项目设计为可连接到任何提供**OpenAI兼容API**的本地AI服务。这种设计带来了极大的灵活性：

- **模型自由**：您可以使用任何您喜欢的本地模型服务，如Ollama、LM Studio、Jan等。
- **配置独立**：AI服务的配置独立于本项目，方便管理和共享。
- **性能优化**：将AI服务运行在主机上，可以更好地利用硬件资源（如GPU）。

本指南将以**Ollama**和**LM Studio**为例，说明如何配置本地AI服务。

---

## 方案一：使用Ollama（推荐）

Ollama是一个轻量级、可扩展的本地大语言模型运行框架。

### 1. 安装Ollama

- **Windows/macOS**: 访问 [Ollama官网](https://ollama.ai) 下载并安装。
- **Linux**: `curl -fsSL https://ollama.ai/install.sh | sh`

### 2. 下载模型

启动Ollama后，通过命令行下载所需的模型。

```bash
# 下载一个语言模型 (例如 Llama 3.1 8B)
ollama pull llama3.1:8b

# 下载一个嵌入模型 (例如 BGE-M3)
ollama pull mxbai-embed-large
```

### 3. 运行Ollama服务

Ollama安装后通常会自动运行。您可以通过以下命令检查服务状态：

```bash
# Ollama服务默认运行在 http://localhost:11434
curl http://localhost:11434
```

Ollama本身就提供OpenAI兼容的API接口。

---

## 方案二：使用LM Studio

LM Studio是一个功能丰富的图形化本地LLM运行工具。

### 1. 安装LM Studio

从 [LM Studio官网](https://lmstudio.ai/) 下载并安装。

### 2. 下载模型

在LM Studio的图形化界面中，搜索并下载您需要的模型。

### 3. 启动本地服务

1.  切换到 "Local Server" 标签页。
2.  在顶部选择您要加载的模型。
3.  点击 "Start Server" 按钮。

LM Studio将启动一个OpenAI兼容的服务器，通常地址是 `http://localhost:1234/v1`。

---

## 配置AI笔记本项目

无论您使用哪种服务，最后都需要在本项目中配置正确的API地址。

### 1. 创建环境变量文件

如果文件不存在，请从示例文件复制：

```bash
cp env.example .env
```

### 2. 修改`.env`文件

打开`.env`文件，修改以下变量：

```ini
# --- AI模型配置 ---

# 根据您的本地服务地址修改
# 如果使用Ollama，默认为 http://localhost:11434
# 如果使用LM Studio，默认为 http://localhost:1234/v1
# 在Docker容器中运行时，需要使用host.docker.internal访问宿主机
API_URL=http://host.docker.internal:11434

# 通常本地服务不需要API Key
API_KEY=

# 设置您下载并加载的模型名称
LLM_MODEL_NAME=llama3.1:8b
EMBEDDING_MODEL_NAME=mxbai-embed-large
```

**关键点**：`API_URL` 必须指向您本地运行的AI服务的正确地址和端口。当在Docker中运行本项目时，使用 `host.docker.internal` 来代替 `localhost`，以便容器可以访问到主机上的服务。

## 验证连接

项目启动后，后端服务会自动尝试连接您配置的AI服务。您可以检查后端日志来确认连接是否成功。

## 常见问题

### Q: 容器无法连接到本地AI服务
A:
- **检查URL**：确保在`docker-compose.yml`或`.env`中使用了`http://host.docker.internal:<端口>` 而不是 `localhost`。
- **检查防火墙**：确保您的系统防火墙没有阻止Docker访问该端口。

### Q: 模型返回错误
A:
- **模型名称**：检查`.env`中的`LLM_MODEL_NAME`是否与您在本地服务中加载的模型完全一致。
- **服务日志**：查看Ollama或LM Studio的日志，获取详细的错误信息。 