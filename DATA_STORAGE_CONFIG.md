# 数据存储配置统一说明

## 概述

为确保项目数据存储的一致性和可维护性，所有数据存储已统一配置到 `backend/data` 目录下。

## 目录结构

```
AI笔记本项目/
├── backend/
│   ├── data/                    # 🎯 统一数据存储目录
│   │   ├── ai_notebook.db       # SQLite数据库文件
│   │   └── chroma_db/           # ChromaDB向量数据库目录
│   ├── app/
│   │   ├── config.py            # 统一配置文件
│   │   └── ...
│   └── ...
├── notes/                       # 用户笔记文件目录
└── ...
```

## 配置文件修改记录

### 1. backend/app/config.py
**修改内容：**
- 添加 `data_directory: str = "./data"`
- 修改 `database_url: str = "sqlite:///./data/ai_notebook.db"`
- 添加 `chroma_db_path: str = "./data/chroma_db"`
- 修改 `notes_directory: str = "../notes"` (指向项目根目录的notes)
- 添加自动创建目录的逻辑

**作用：** 作为所有数据路径配置的单一来源

### 2. backend/app/models/base.py
**修改内容：**
- 从 `config.py` 导入统一配置
- 使用 `settings.database_url` 替代硬编码路径
- 添加回退机制使用环境变量

**作用：** 确保数据库连接使用统一配置

### 3. backend/app/services/ai_service.py
**修改内容：**
- 从 `config.py` 导入设置
- 使用 `settings.openai_api_key`、`settings.openai_base_url`、`settings.openai_model`
- 添加 `self.chroma_db_path = settings.chroma_db_path`

**作用：** 确保AI服务使用统一的配置和ChromaDB路径

### 4. docker-compose.yml
**修改内容：**
- 更新环境变量名：
  - `API_URL` → `OPENAI_BASE_URL`
  - `API_KEY` → `OPENAI_API_KEY`
  - `LLM_MODEL_NAME` → `OPENAI_MODEL`
- 更新数据库文件名：`notebook.db` → `ai_notebook.db`
- 更新挂载路径：`./data:/app/data` → `./backend/data:/app/data`
- 更新笔记路径：`./notes:/app/data/notes` → `./notes:/app/notes`

**作用：** 确保Docker环境使用统一的数据路径和配置变量

### 5. env.example
**修改内容：**
- 统一环境变量命名：
  - `API_URL` → `OPENAI_BASE_URL`
  - `API_KEY` → `OPENAI_API_KEY`
  - `LLM_MODEL_NAME` → `OPENAI_MODEL`
  - `NOTES_ROOT_PATH` → `NOTES_DIRECTORY`
- 添加 `DATA_DIRECTORY=./data`
- 更新数据库文件名和路径
- 添加新的配置项：`SEARCH_LIMIT`、`API_PREFIX`、`LOG_LEVEL`

**作用：** 为开发者提供统一的环境变量配置示例

## 环境变量统一表

| 配置项 | 环境变量名 | 默认值 | 说明 |
|--------|------------|--------|------|
| 数据目录 | DATA_DIRECTORY | ./data | 数据存储根目录 |
| 数据库URL | DATABASE_URL | sqlite:///./data/ai_notebook.db | SQLite数据库路径 |
| 向量数据库路径 | CHROMA_DB_PATH | ./data/chroma_db | ChromaDB存储路径 |
| 笔记目录 | NOTES_DIRECTORY | ../notes | 用户笔记存储目录 |
| OpenAI API URL | OPENAI_BASE_URL | http://localhost:11434 | AI服务API地址 |
| OpenAI API密钥 | OPENAI_API_KEY | (空) | AI服务API密钥 |
| OpenAI模型 | OPENAI_MODEL | gpt-3.5-turbo | 使用的AI模型名称 |

## 路径说明

### 相对路径基准
- 所有配置中的相对路径都是相对于 `backend/` 目录
- `./data` = `backend/data`
- `../notes` = 项目根目录的 `notes`

### 数据存储规则
1. **数据库文件**：存储在 `backend/data/ai_notebook.db`
2. **向量数据库**：存储在 `backend/data/chroma_db/`
3. **用户笔记**：存储在项目根目录的 `notes/`
4. **临时文件**：如需要，也应存储在 `backend/data/temp/`

## 开发注意事项

### 新增数据存储需求时
1. 在 `backend/app/config.py` 中添加相应配置项
2. 确保路径相对于 `backend/` 目录
3. 在 `env.example` 中添加对应的环境变量示例
4. 更新此文档

### 路径引用规范
1. **禁止硬编码路径**：始终通过 `config.py` 获取路径配置
2. **统一导入方式**：`from ..config import settings`
3. **路径拼接**：使用 `pathlib.Path` 进行路径操作

### 测试和部署
1. **本地开发**：确保 `backend/data` 目录存在
2. **Docker部署**：挂载 `./backend/data:/app/data`
3. **数据备份**：备份整个 `backend/data` 目录即可

## 迁移完成确认

✅ 已完成的操作：
- [x] 移动 `data/chroma_db` → `backend/data/chroma_db`
- [x] 删除项目根目录的 `data` 目录
- [x] 更新 `backend/app/config.py` 配置
- [x] 更新 `backend/app/models/base.py` 数据库配置
- [x] 更新 `backend/app/services/ai_service.py` AI服务配置
- [x] 更新 `docker-compose.yml` Docker配置
- [x] 更新 `env.example` 环境变量示例
- [x] 创建此配置说明文档

## 验证方法

启动后端服务后，检查以下内容：
1. 数据库文件是否在 `backend/data/ai_notebook.db`
2. ChromaDB目录是否在 `backend/data/chroma_db/`
3. 服务是否正常启动且能访问数据
4. 笔记文件操作是否正常

---

**重要提醒：** 此配置统一后，所有开发者和部署环境都应遵循此规范，确保数据存储的一致性。 