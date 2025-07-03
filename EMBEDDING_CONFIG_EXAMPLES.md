# 嵌入模型独立配置示例

本文档展示如何为嵌入模型单独指定 API 地址和密钥，实现灵活的AI服务配置。

## 配置方式

### 方式一：统一配置（默认方式）
只配置语言模型的API，嵌入模型会自动使用相同配置。

```yaml
# docker-compose.yml
environment:
  - OPENAI_BASE_URL=http://host.docker.internal:11434/v1
  - OPENAI_API_KEY=ollama
  - OPENAI_MODEL=qwen2.5:0.5b
  - EMBEDDING_MODEL_NAME=quentinz/bge-large-zh-v1.5:latest
```

### 方式二：嵌入模型独立配置
为嵌入模型指定专用的API地址和密钥。

```yaml
# docker-compose.yml
environment:
  # 语言模型配置
  - OPENAI_BASE_URL=https://api.openai.com/v1
  - OPENAI_API_KEY=your-openai-api-key
  - OPENAI_MODEL=gpt-4
  
  # 嵌入模型独立配置
  - EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
  - EMBEDDING_API_KEY=ollama
  - EMBEDDING_MODEL_NAME=quentinz/bge-large-zh-v1.5:latest
```

## 使用场景

### 场景一：成本优化
- **语言模型**：使用OpenAI GPT-4（高质量回答）
- **嵌入模型**：使用本地Ollama（节省成本）

```yaml
environment:
  # 高性能语言模型（付费）
  - OPENAI_BASE_URL=https://api.openai.com/v1
  - OPENAI_API_KEY=sk-your-openai-key
  - OPENAI_MODEL=gpt-4
  
  # 本地嵌入模型（免费）
  - EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
  - EMBEDDING_API_KEY=ollama
  - EMBEDDING_MODEL_NAME=quentinz/bge-large-zh-v1.5:latest
```

### 场景二：服务商分离
- **语言模型**：使用Claude（Anthropic）
- **嵌入模型**：使用OpenAI

```yaml
environment:
  # Claude语言模型
  - OPENAI_BASE_URL=https://api.anthropic.com/v1
  - OPENAI_API_KEY=your-anthropic-key
  - OPENAI_MODEL=claude-3-sonnet
  
  # OpenAI嵌入模型
  - EMBEDDING_BASE_URL=https://api.openai.com/v1
  - EMBEDDING_API_KEY=your-openai-key
  - EMBEDDING_MODEL_NAME=text-embedding-ada-002
```

### 场景三：多环境部署
- **开发环境**：全部使用本地Ollama
- **生产环境**：语言模型用云服务，嵌入模型用本地

```yaml
# 开发环境
environment:
  - OPENAI_BASE_URL=http://host.docker.internal:11434/v1
  - OPENAI_API_KEY=ollama
  - OPENAI_MODEL=qwen2.5:0.5b
  - EMBEDDING_MODEL_NAME=quentinz/bge-large-zh-v1.5:latest

# 生产环境
environment:
  # 云端语言模型
  - OPENAI_BASE_URL=https://api.openai.com/v1
  - OPENAI_API_KEY=your-production-key
  - OPENAI_MODEL=gpt-4-turbo
  
  # 本地嵌入模型
  - EMBEDDING_BASE_URL=http://localhost:11434/v1
  - EMBEDDING_API_KEY=ollama
  - EMBEDDING_MODEL_NAME=quentinz/bge-large-zh-v1.5:latest
```

## 配置验证

### 1. 检查配置加载
```bash
cd backend
python -c "
from app.config import settings
print(f'语言模型 Base URL: {settings.openai_base_url}')
print(f'语言模型 API Key: {settings.openai_api_key[:10]}...')
print(f'嵌入模型 Base URL: {settings.get_embedding_base_url()}')
print(f'嵌入模型 API Key: {settings.get_embedding_api_key()[:10]}...')
"
```

### 2. 测试连接
启动服务后，查看后端日志确认AI服务连接状态：
```bash
docker-compose logs backend | grep -i "embedding\|ai\|openai"
```

## 注意事项

1. **向后兼容**：现有配置无需修改，系统会自动使用统一配置
2. **优先级**：嵌入专用配置优先级高于通用配置
3. **密钥安全**：生产环境建议使用环境变量文件或密钥管理服务
4. **模型匹配**：确保模型名称与服务商支持的模型一致
5. **网络访问**：Docker容器访问宿主机服务需要使用 `host.docker.internal`

## 故障排除

### 问题：嵌入模型连接失败
1. 检查 `EMBEDDING_BASE_URL` 是否正确
2. 确认 `EMBEDDING_API_KEY` 是否有效
3. 验证模型名称 `EMBEDDING_MODEL_NAME` 是否正确

### 问题：配置不生效
1. 重启Docker容器：`docker-compose down && docker-compose up -d`
2. 检查环境变量是否正确设置
3. 查看后端启动日志确认配置加载情况 