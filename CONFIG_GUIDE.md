# AI笔记本配置指南

## 概述

AI笔记本现在支持两种配置方式：
1. **JSON配置文件** - 推荐方式，提供图形化配置界面
2. **环境变量** - 传统方式，向后兼容

## 配置优先级

JSON配置文件（如果存在）> 环境变量 > 默认值

## 使用方法

### 方法一：图形化配置（推荐）

1. 启动应用后，点击右上角的设置按钮（⚙️）或按 `Ctrl+,`
2. 在配置界面中设置AI模型、嵌入模型等参数
3. 可以选择预设配置或自定义配置
4. 点击"保存配置"，系统会自动生成 `config.json` 文件

### 方法二：手动创建配置文件

在项目根目录创建 `config.json` 文件：

```json
{
  "ai_settings": {
    "enabled": true,
    "language_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "qwen2.5:0.5b",
      "temperature": 0.7,
      "max_tokens": 2048
    },
    "embedding_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "quentinz/bge-large-zh-v1.5:latest",
      "dimension": 1024
    }
  }
}
```

## 预设配置

### 本地 Ollama 配置
适用于使用本地 Ollama 服务的用户：

```json
{
  "ai_settings": {
    "enabled": true,
    "language_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "qwen2.5:0.5b"
    },
    "embedding_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "quentinz/bge-large-zh-v1.5:latest",
      "dimension": 1024
    }
  }
}
```

### OpenAI 云服务配置
适用于使用 OpenAI 官方 API 的用户：

```json
{
  "ai_settings": {
    "enabled": true,
    "language_model": {
      "provider": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "your_openai_api_key",
      "model_name": "gpt-3.5-turbo"
    },
    "embedding_model": {
      "provider": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "your_openai_api_key",
      "model_name": "text-embedding-ada-002",
      "dimension": 1536
    }
  }
}
```

### 纯笔记模式配置
禁用所有AI功能，仅作为笔记管理工具：

```json
{
  "ai_settings": {
    "enabled": false,
    "fallback_mode": "notes_only"
  }
}
```

## Docker 部署配置

### 使用 JSON 配置文件

1. 在项目根目录创建 `config.json` 文件
2. 使用 docker-compose 启动：

```bash
docker-compose up -d
```

配置文件会自动挂载到容器中，覆盖环境变量设置。

### 使用环境变量（传统方式）

如果不提供 `config.json` 文件，系统会使用 `docker-compose.yml` 中的环境变量配置。

## 配置项说明

### AI设置 (ai_settings)

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| enabled | boolean | 是否启用AI功能 | true |
| fallback_mode | string | 降级模式（notes_only/limited_ai/offline） | notes_only |

### 语言模型配置 (language_model)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| provider | string | 服务提供商 | openai_compatible |
| base_url | string | API地址 | http://localhost:11434/v1 |
| api_key | string | API密钥 | ollama |
| model_name | string | 模型名称 | qwen2.5:0.5b |
| temperature | number | 温度参数 (0-2) | 0.7 |
| max_tokens | number | 最大令牌数 | 2048 |
| timeout | number | 超时时间（秒） | 30 |

### 嵌入模型配置 (embedding_model)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| provider | string | 服务提供商 | openai_compatible |
| base_url | string | API地址 | http://localhost:11434/v1 |
| api_key | string | API密钥 | ollama |
| model_name | string | 模型名称 | quentinz/bge-large-zh-v1.5:latest |
| dimension | number | 嵌入维度 | 1024 |

### 高级配置 (advanced)

#### 搜索配置 (search)
- `semantic_search_threshold`: 语义搜索阈值 (默认: 1.0)
- `search_limit`: 搜索结果限制 (默认: 50)
- `enable_hierarchical_chunking`: 启用分层分块 (默认: true)

#### 分块配置 (chunking)
- `hierarchical_summary_max_length`: 摘要最大长度 (默认: 2000)
- `hierarchical_outline_max_depth`: 大纲最大深度 (默认: 5)
- `hierarchical_content_target_size`: 内容块目标大小 (默认: 1000)
- `hierarchical_content_max_size`: 内容块最大大小 (默认: 1500)
- `hierarchical_content_overlap`: 内容块重叠 (默认: 100)

#### LLM配置 (llm)
- `context_window`: 上下文窗口 (默认: 131072)
- `chunk_for_llm_processing`: LLM处理块大小 (默认: 30000)
- `max_chunks_for_refine`: 最大精炼块数 (默认: 20)

## 故障排除

### 配置不生效
1. 确认 `config.json` 文件格式正确
2. 检查文件是否在正确的位置（项目根目录）
3. 重启应用服务

### AI功能不可用
1. 在配置界面点击"测试连接"
2. 检查API地址和密钥是否正确
3. 确认AI服务是否运行正常

### Docker容器中配置问题
1. 确认配置文件已正确挂载
2. 检查文件权限（配置文件需要可读权限）
3. 查看容器日志排查问题

## API接口

系统提供以下配置管理API：

- `GET /api/v1/config/` - 获取当前配置
- `POST /api/v1/config/update` - 更新配置
- `GET /api/v1/config/test` - 测试AI连接
- `GET /api/v1/config/presets` - 获取预设配置
- `POST /api/v1/config/presets/{name}/apply` - 应用预设配置
- `POST /api/v1/config/reset` - 重置为默认配置

## 安全注意事项

1. API密钥等敏感信息会存储在配置文件中，请确保文件安全
2. 在生产环境中，建议将配置文件权限设置为只读
3. 不要将包含真实API密钥的配置文件提交到版本控制系统

## 迁移指南

### 从环境变量迁移到JSON配置

1. 记录当前的环境变量配置
2. 启动应用，打开配置界面
3. 根据环境变量设置配置项
4. 保存配置，系统会生成 `config.json` 文件
5. 可选：移除不必要的环境变量

这样可以确保平滑迁移到新的配置系统。