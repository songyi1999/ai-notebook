# AI笔记本项目

## 项目概述

一个**纯本地运行、AI增强**的个人知识管理系统，专注于隐私保护和数据安全。

### 核心特性

- 🔒 **纯本地运行**：所有数据保存在本地，确保隐私安全
- 📝 **Markdown编辑**：支持实时预览的专业Markdown编辑器
- 🔗 **智能链接**：双向链接 + AI智能发现 + 手动管理
- 🔍 **混合搜索**：关键词搜索 + 语义搜索，精准定位内容
- 🤖 **AI问答**：基于笔记内容的智能RAG问答系统
- 🏷️ **智能标签**：AI自动提取 + 手动管理标签系统
- 📊 **关系图谱**：可视化笔记间的链接关系网络
- 🛠️ **MCP支持**：集成Model Context Protocol工具生态
- 🐳 **容器化**：Docker一键部署，跨平台兼容

## 功能模块详解

### 📝 笔记编辑器
- **Monaco Editor**：VS Code同款编辑器内核
- **实时预览**：Markdown实时渲染预览
- **语法高亮**：支持代码块语法高亮
- **自动保存**：智能检测修改并自动保存

### 🔗 链接管理系统（已修复）
- **双向链接**：使用 `[[文件名]]` 语法创建双向链接
- **AI智能发现**：自动分析文档关系，建议相关链接
- **手动创建**：通过"链接管理"标签页手动创建任意文件间的链接
- **链接类型**：支持reference、related、follow_up、prerequisite、example、contradiction等类型
- **可视化展示**：在关系图谱中直观查看链接网络

#### 最新修复（2025-01-04）
- ✅ **数据库结构修复**：修复了links表缺失anchor_text列的问题
- ✅ **API错误修复**：解决了GET /api/v1/links接口500错误
- ✅ **数据库兼容性**：使用ALTER TABLE自动添加缺失列，保持数据完整性
- ✅ 修复了链接创建API的422错误（link_text字段问题）
- ✅ 添加了"链接管理"标签页到主界面
- ✅ 优化了链接数据模型，支持可选的link_text和anchor_text字段
- ✅ 实现了智能默认值生成：自动使用目标文件名作为链接文本
- ✅ 完善了组件集成检查，确保所有功能组件都正确集成到主界面

### 🔍 智能搜索
- **关键词搜索**：基于SQLite FTS5全文搜索
- **语义搜索**：基于向量相似度的语义理解
- **混合搜索**：结合关键词和语义的最佳搜索体验
- **搜索历史**：记录和管理搜索历史

### 🤖 AI功能集成
- **RAG问答**：基于笔记内容的智能问答
- **标签生成**：AI分析内容自动生成相关标签
- **链接发现**：AI智能分析文档关系，建议潜在链接
- **内容分析**：深度理解文档内容和结构

### 🏷️ 标签系统
- **AI智能建议**：基于内容自动建议标签
- **手动管理**：创建、编辑、删除标签
- **标签统计**：显示标签使用频率和关联文件
- **颜色分类**：支持自定义标签颜色

### 📊 关系图谱
- **链接可视化**：D3.js驱动的交互式关系图
- **节点交互**：点击节点跳转到对应文件
- **布局算法**：智能布局算法优化图谱展示
- **过滤功能**：按类型、时间等条件过滤显示

### 🛠️ MCP工具集成
- **协议支持**：完整的Model Context Protocol支持
- **服务器管理**：管理和配置MCP服务器
- **工具发现**：自动发现和注册MCP工具
- **调用历史**：记录和管理工具调用历史

## 技术架构

### 前端技术栈
- **React 18** + **TypeScript**：现代化前端框架
- **Ant Design**：企业级UI组件库
- **Monaco Editor**：VS Code编辑器内核
- **D3.js**：数据可视化图表库
- **Zustand**：轻量级状态管理
- **Vite**：快速构建工具

### 后端技术栈
- **FastAPI**：高性能Python Web框架
- **SQLite**：轻量级关系数据库
- **ChromaDB**：向量数据库，支持语义搜索
- **Pydantic**：数据验证和序列化
- **SQLAlchemy**：ORM数据库操作

### AI集成
- **OpenAI兼容接口**：支持本地LLM服务
- **标准嵌入接口**：`/v1/embeddings` 标准接口
- **RAG架构**：检索增强生成问答系统
- **向量搜索**：ChromaDB语义相似度搜索

## 数据库结构

### 核心表结构
- **files**：文件基本信息和内容
- **tags**：标签定义和属性
- **file_tags**：文件标签关联关系
- **links**：文件间链接关系（已优化）
- **search_history**：搜索历史记录
- **pending_tasks**：后台任务队列
- **mcp_servers**：MCP服务器配置
- **mcp_tools**：MCP工具注册信息
- **mcp_tool_calls**：MCP工具调用历史

### 链接表结构（最新优化）
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL,
    target_file_id INTEGER,
    link_text TEXT,                 -- 可选字段，自动生成默认值
    link_type VARCHAR DEFAULT 'wikilink',
    anchor_text TEXT,               -- 新增锚点文本字段
    position_start INTEGER,
    position_end INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE
);
```

## 安装和部署

### 环境要求
- Docker & Docker Compose
- 本地LLM服务（可选，推荐Ollama）

### 快速启动
```bash
# 克隆项目
git clone <repository-url>
cd AI笔记本项目

# 配置环境变量
cp env.example .env
# 编辑.env文件，配置AI服务地址

# 启动服务
docker-compose up -d --build

# 访问应用
http://localhost:3000
```

### 本地LLM配置
```bash
# 安装Ollama（推荐）
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 配置.env
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=ollama
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=nomic-embed-text
```

## 使用指南

### 基础操作
1. **创建笔记**：在文件树中右键创建新文件
2. **编辑内容**：使用Markdown语法编写内容
3. **保存文件**：Ctrl+S或点击保存按钮
4. **搜索内容**：Ctrl+K打开搜索框
5. **AI问答**：Ctrl+/打开AI助手

### 链接管理
1. **双向链接**：在编辑器中使用 `[[文件名]]` 语法
2. **手动创建**：在"链接管理"标签页点击"新建链接"
3. **AI发现**：在"AI处理"标签页开启"自动发现和创建链接"
4. **查看关系**：在"图谱"标签页查看链接关系网络

### 标签系统
1. **AI生成**：在"标签"标签页点击"AI建议标签"
2. **手动添加**：直接输入标签名称添加
3. **批量处理**：在"AI处理"标签页批量处理多个文件

## 函数列表

### 后端API接口

#### 文件管理
- `GET /api/v1/files` - 获取文件列表
- `POST /api/v1/files` - 创建新文件
- `GET /api/v1/files/{file_id}` - 获取文件详情
- `PUT /api/v1/files/{file_id}` - 更新文件内容
- `DELETE /api/v1/files/{file_id}` - 删除文件

#### 搜索功能
- `GET /api/v1/search` - 混合搜索接口
- `GET /api/v1/search/history` - 搜索历史
- `GET /api/v1/search/popular` - 热门查询

#### 标签管理
- `GET /api/v1/tags` - 获取标签列表
- `POST /api/v1/tags` - 创建标签
- `POST /api/v1/files/{file_id}/tags` - 为文件添加标签
- `POST /api/v1/ai/suggest-tags` - AI标签建议

#### 链接管理（已修复）
- `GET /api/v1/links` - 获取所有链接
- `POST /api/v1/links` - 创建新链接（支持可选link_text）
- `GET /api/v1/files/{file_id}/links` - 获取文件的链接
- `PUT /api/v1/links/{link_id}` - 更新链接
- `DELETE /api/v1/links/{link_id}` - 删除链接
- `POST /api/v1/ai/discover-links/{file_id}` - AI智能链接发现

#### AI服务
- `POST /api/v1/ai/chat` - RAG智能问答
- `GET /api/v1/ai/status` - AI服务状态检查
- `POST /api/v1/ai/suggest-tags` - AI标签建议
- `POST /api/v1/ai/discover-links/{file_id}` - AI链接发现

#### MCP集成
- `GET /api/v1/mcp/servers` - MCP服务器列表
- `POST /api/v1/mcp/servers` - 创建MCP服务器
- `GET /api/v1/mcp/tools` - MCP工具列表
- `POST /api/v1/mcp/tool-calls` - MCP工具调用

### 前端组件

#### 主要组件
- `NoteEditor` - 主编辑器组件（包含6个标签页）
- `FileTree` - 文件树组件
- `SearchModal` - 搜索模态框
- `ChatModal` - AI聊天模态框

#### 功能组件
- `TagManager` - 标签管理组件
- `LinkManager` - 链接管理组件（已集成）
- `AutoProcessor` - AI批量处理组件
- `LinkGraph` - 关系图谱组件
- `MCPManager` - MCP工具管理组件

## 变量说明

### 环境变量
- `OPENAI_BASE_URL` - AI服务基础URL
- `OPENAI_API_KEY` - AI服务API密钥
- `EMBEDDING_BASE_URL` - 嵌入服务URL
- `EMBEDDING_API_KEY` - 嵌入服务密钥
- `EMBEDDING_MODEL` - 嵌入模型名称
- `SEMANTIC_SEARCH_THRESHOLD` - 语义搜索相似度阈值

### 配置参数
- `max_tags_per_file` - 每个文件最大标签数（默认5）
- `link_similarity_threshold` - 链接相似度阈值（默认0.6）
- `search_limit` - 搜索结果限制（默认50）
- `context_length` - AI问答上下文长度（默认3000）

## 开发和贡献

### 开发环境设置
```bash
# 前端开发
cd frontend
npm install
npm run dev

# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 代码规范
- 前端：ESLint + Prettier
- 后端：Black + isort
- 提交：遵循Conventional Commits规范

### 测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 更新日志

### v1.2.0 (2025-01-04) - 链接管理修复
- ✅ 修复链接创建API 422错误
- ✅ 优化链接数据模型，支持可选字段
- ✅ 添加"链接管理"标签页到主界面
- ✅ 实现智能默认值生成
- ✅ 完善链接类型支持

### v1.1.0 (2024-12-XX) - MCP集成
- ✅ 完整MCP协议支持
- ✅ MCP服务器管理界面
- ✅ 工具发现和调用功能

### v1.0.0 (2024-12-XX) - 基础版本
- ✅ 核心笔记管理功能
- ✅ AI问答和搜索
- ✅ 标签和链接系统
- ✅ 容器化部署

## 许可证

MIT License

## 支持

如有问题或建议，请提交Issue或Pull Request。