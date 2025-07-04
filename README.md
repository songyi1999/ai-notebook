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
- ✅ **图谱显示修复**：解决了图谱标签页显示为空的问题
- ✅ **数据流修复**：修正了文件和链接数据的加载与渲染时序
- ✅ **统计显示正常**：图谱统计信息（节点数、连接数等）正确显示
- ✅ **数据库结构修复**：修复了links表缺失anchor_text列的问题
- ✅ **API错误修复**：解决了GET /api/v1/links接口500错误
- ✅ **数据库兼容性**：使用ALTER TABLE自动添加缺失列，保持数据完整性
- ✅ 修复了链接创建API的422错误（link_text字段问题）
- ✅ 添加了"链接管理"标签页到主界面
- ✅ 优化了链接数据模型，支持可选的link_text和anchor_text字段
- ✅ 实现了智能默认值生成：自动使用目标文件名作为链接文本
- ✅ 完善了组件集成检查，确保所有功能组件都正确集成到主界面
- ✅ **代码重构**：清理了ai_service_langchain.py中的重复代码实现，从2243行优化到1825行，提升代码可维护性

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

### 📈 系统监控与控制（v1.3.3新增）
- **状态监控**：实时显示系统状态（文件数、嵌入数、待索引任务数）
- **处理器状态**：显示任务处理器运行状态，支持PID检测
- **手动控制**：支持手动启动/停止任务处理器
- **智能提醒**：当有待索引任务且处理器停止时，显示醒目的"开始索引"按钮
- **状态指示器**：绿色●表示运行中，红色○表示已停止
- **自动刷新**：每60秒自动刷新系统状态

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

## 函数调用格式表格

### 🔍 使用状态说明
- ✅ **使用中**：已被前端组件调用的函数
- ⚠️ **未使用**：已实现但未被调用的函数
- ❌ **建议删除**：冗余或无用的函数

### 📚 后端API接口

#### 文件管理API (files.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_file_api` | `file: FileCreate` | `FileResponse` | 创建新文件 | ✅ 使用中 |
| `read_files_api` | `skip: int, limit: int, include_deleted: bool` | `List[FileResponse]` | 获取文件列表 | ⚠️ 未使用 |
| `read_file_by_path_api` | `file_path: str` | `FileResponse` | 通过路径获取文件 | ✅ 使用中 |
| `get_file_tree_api` | `root_path: str` | `List[FileTreeNode]` | 获取文件树结构 | ✅ 使用中 |
| `create_directory_api` | `request: dict` | `dict` | 创建目录 | ✅ 使用中 |
| `search_files_api` | `query: str, search_type: str, limit: int` | `SearchResponse` | 文件搜索 | ✅ 使用中 |
| `get_search_history_api` | `limit: int` | `List[SearchHistory]` | 获取搜索历史 | ✅ 使用中 |
| `get_popular_queries_api` | `limit: int` | `List[PopularQuery]` | 获取热门查询 | ✅ 使用中 |
| `delete_file_by_path_api` | `request: dict` | `dict` | 通过路径删除文件 | ✅ 使用中 |
| `move_file_api` | `request: dict` | `dict` | 移动文件 | ✅ 使用中 |
| `read_file_api` | `file_id: int` | `FileResponse` | 获取文件详情 | ⚠️ 未使用 |
| `update_file_api` | `file_id: int, file: FileUpdate` | `FileResponse` | 更新文件内容 | ✅ 使用中 |
| `update_file_by_path_api` | `file_path: str, file: FileUpdate` | `FileResponse` | 通过路径更新文件 | ⚠️ 未使用 |
| `delete_file_api` | `file_id: int` | `dict` | 删除文件 | ✅ 使用中 |

#### 标签管理API (tags.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_tag_api` | `tag: TagCreate` | `TagResponse` | 创建标签 | ✅ 使用中 |
| `read_tag_api` | `tag_id: int` | `TagResponse` | 获取标签详情 | ⚠️ 未使用 |
| `read_all_tags_api` | `skip: int, limit: int` | `List[TagResponse]` | 获取标签列表 | ✅ 使用中 |
| `read_tags_with_stats_api` | `skip: int, limit: int` | `List[TagWithStats]` | 获取带统计的标签列表 | ✅ 使用中 |
| `get_tag_usage_count_api` | `tag_id: int` | `dict` | 获取标签使用次数 | ⚠️ 未使用 |
| `update_tag_api` | `tag_id: int, tag: TagUpdate` | `TagResponse` | 更新标签 | ✅ 使用中 |
| `delete_tag_api` | `tag_id: int` | `None` | 删除标签 | ✅ 使用中 |
| `create_file_tag_api` | `file_tag: FileTagCreate` | `FileTagResponse` | 为文件添加标签 | ✅ 使用中 |
| `get_file_tags_api` | `file_id: int` | `List[FileTagResponse]` | 获取文件的标签 | ✅ 使用中 |
| `delete_file_tag_api` | `file_id: int, tag_id: int` | `None` | 删除文件标签 | ✅ 使用中 |

#### 链接管理API (links.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_link_api` | `link: LinkCreate` | `LinkResponse` | 创建新链接 | ✅ 使用中 |
| `read_link_api` | `link_id: int` | `LinkResponse` | 获取链接详情 | ⚠️ 未使用 |
| `read_links_by_file_api` | `file_id: int` | `List[LinkResponse]` | 获取文件的链接 | ✅ 使用中 |
| `read_all_links_api` | `skip: int, limit: int` | `List[LinkResponse]` | 获取所有链接 | ✅ 使用中 |
| `update_link_api` | `link_id: int, link: LinkUpdate` | `LinkResponse` | 更新链接 | ✅ 使用中 |
| `delete_link_api` | `link_id: int` | `None` | 删除链接 | ✅ 使用中 |

#### AI服务API (ai.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `generate_summary_api` | `request: SummaryRequest` | `dict` | 内容摘要 | ⚠️ 未使用 |
| `suggest_tags_api` | `request: TagSuggestionRequest` | `List[str]` | AI标签建议 | ✅ 使用中 |
| `create_embeddings_api` | `file_id: int` | `dict` | 创建嵌入 | ⚠️ 未使用 |
| `semantic_search_api` | `request: SemanticSearchRequest` | `dict` | 语义搜索 | ⚠️ 未使用 |
| `analyze_content_api` | `request: ContentAnalysisRequest` | `dict` | 内容分析 | ⚠️ 未使用 |
| `generate_related_questions_api` | `request: RelatedQuestionsRequest` | `List[str]` | 相关问题 | ⚠️ 未使用 |
| `chat_api` | `request: ChatRequest` | `ChatResponse` | RAG智能问答 | ✅ 使用中 |
| `discover_smart_links_api` | `file_id: int` | `List[SmartLinkSuggestion]` | AI链接发现 | ✅ 使用中 |
| `get_ai_status_api` | `None` | `dict` | AI服务状态检查 | ✅ 使用中 |

#### 索引管理API (index.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `get_index_status` | `None` | `dict` | 索引状态 | ⚠️ 未使用 |
| `rebuild_index` | `None` | `dict` | 重建索引 | ✅ 使用中 |
| `get_rebuild_progress` | `None` | `dict` | 重建进度 | ⚠️ 未使用 |
| `scan_notes_directory` | `None` | `dict` | 扫描文件 | ⚠️ 未使用 |
| `get_system_status` | `None` | `dict` | 系统状态 | ✅ 使用中 |
| `get_processor_status` | `None` | `dict` | 获取任务处理器状态（v1.3.3新增）| ✅ 使用中 |
| `start_processor` | `force: bool` | `dict` | 启动任务处理器（v1.3.3新增）| ✅ 使用中 |
| `stop_processor` | `None` | `dict` | 停止任务处理器（v1.3.3新增）| ✅ 使用中 |



#### MCP集成API (mcp.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `get_mcp_servers` | `None` | `List[MCPServerResponse]` | MCP服务器列表 | ✅ 使用中 |
| `get_mcp_server` | `server_id: int` | `MCPServerWithTools` | 获取服务器详情 | ⚠️ 未使用 |
| `delete_mcp_server` | `server_id: int` | `None` | 删除服务器 | ✅ 使用中 |
| `get_mcp_server_status` | `server_id: int` | `MCPServerStatus` | 服务器状态 | ⚠️ 未使用 |
| `get_available_tools` | `None` | `List[MCPToolResponse]` | MCP工具列表 | ✅ 使用中 |
| `get_mcp_tool` | `tool_id: int` | `MCPToolResponse` | 获取工具详情 | ⚠️ 未使用 |
| `get_tool_calls` | `limit: int` | `List[MCPToolCallResponse]` | 工具调用历史 | ⚠️ 未使用 |
| `get_tool_call` | `call_id: int` | `MCPToolCallResponse` | 获取调用详情 | ⚠️ 未使用 |
| `update_tool_call_feedback` | `call_id: int, feedback: dict` | `None` | 调用反馈 | ⚠️ 未使用 |
| `get_mcp_stats` | `None` | `dict` | MCP统计信息 | ✅ 使用中 |

#### 文件上传转换 (file_upload.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `upload_and_convert_files` | `files: List[UploadFile], target_folder: str` | `FileUploadResponse` | 批量上传转换文件为MD | ✅ 使用中 |
| `upload_with_progress` | `files: List[UploadFile], target_folder: str` | `FileUploadResponse` | 带进度的文件上传转换 | ✅ 使用中 |
| `get_supported_formats` | `None` | `SupportedFormatsResponse` | 获取支持的文件格式 | ✅ 使用中 |

### 🔧 后端服务层函数

#### 文件服务 (FileService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_file` | `file: FileCreate, fast_mode: bool` | `File` | 创建文件并保存到磁盘 | ✅ 使用中 |
| `get_file` | `file_id: int` | `Optional[File]` | 获取文件记录 | ✅ 使用中 |
| `get_file_by_path` | `file_path: str` | `Optional[File]` | 通过路径获取文件 | ✅ 使用中 |
| `get_files` | `skip: int, limit: int, include_deleted: bool` | `List[File]` | 获取文件列表 | ✅ 使用中 |
| `update_file` | `file_id: int, file_update: FileUpdate, fast_mode: bool` | `Optional[File]` | 更新文件内容 | ✅ 使用中 |
| `_calculate_content_hash` | `content: str` | `str` | 计算内容哈希 | ✅ 使用中 |
| `_write_file_to_disk` | `file_path: str, content: str` | `bool` | 写入文件到磁盘 | ✅ 使用中 |
| `_read_file_from_disk` | `file_path: str` | `Optional[str]` | 从磁盘读取文件 | ✅ 使用中 |

#### 标签服务 (TagService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_tag` | `tag: TagCreate` | `Tag` | 创建标签 | ✅ 使用中 |
| `get_tag` | `tag_id: int` | `Optional[Tag]` | 获取标签 | ✅ 使用中 |
| `get_tag_by_name` | `name: str` | `Optional[Tag]` | 通过名称获取标签 | ✅ 使用中 |
| `get_all_tags` | `skip: int, limit: int` | `List[Tag]` | 获取所有标签 | ✅ 使用中 |
| `get_tags_with_usage_stats` | `skip: int, limit: int` | `List[dict]` | 获取带统计的标签 | ✅ 使用中 |
| `update_tag` | `tag_id: int, tag_update: TagUpdate` | `Optional[Tag]` | 更新标签 | ✅ 使用中 |
| `delete_tag` | `tag_id: int` | `Optional[Tag]` | 删除标签 | ✅ 使用中 |
| `search_tags` | `query: str` | `List[Tag]` | 搜索标签 | ⚠️ 未使用 |

#### 文件标签服务 (FileTagService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_file_tag` | `file_tag: FileTagCreate` | `FileTag` | 创建文件标签关联 | ✅ 使用中 |
| `get_file_tag` | `file_id: int, tag_id: int` | `Optional[FileTag]` | 获取文件标签 | ✅ 使用中 |
| `get_file_tags_by_file` | `file_id: int` | `List[FileTag]` | 获取文件的所有标签 | ✅ 使用中 |
| `get_file_tags_by_tag` | `tag_id: int` | `List[FileTag]` | 获取标签的所有文件 | ✅ 使用中 |
| `delete_file_tag` | `file_id: int, tag_id: int` | `Optional[FileTag]` | 删除文件标签关联 | ✅ 使用中 |
| `delete_all_file_tags` | `file_id: int` | `int` | 删除文件的所有标签 | ✅ 使用中 |

#### 链接服务 (LinkService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_link` | `link: LinkCreate` | `Link` | 创建链接 | ✅ 使用中 |
| `get_link` | `link_id: int` | `Optional[Link]` | 获取链接 | ✅ 使用中 |
| `get_links_by_source_file` | `source_file_id: int` | `List[Link]` | 获取源文件的链接 | ✅ 使用中 |
| `get_links_by_target_file` | `target_file_id: int` | `List[Link]` | 获取目标文件的链接 | ✅ 使用中 |
| `get_all_links` | `skip: int, limit: int` | `List[Link]` | 获取所有链接 | ✅ 使用中 |
| `update_link` | `link_id: int, link_update: LinkUpdate` | `Optional[Link]` | 更新链接 | ✅ 使用中 |
| `delete_link` | `link_id: int` | `Optional[Link]` | 删除链接 | ✅ 使用中 |

#### AI服务 (AIService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `is_available` | `None` | `bool` | 检查AI服务是否可用 | ✅ 使用中 |
| `create_embeddings` | `file: File, progress_callback=None` | `bool` | 创建文件嵌入（v1.3.2支持进度回调）| ✅ 使用中 |
| `semantic_search` | `query: str, limit: int, similarity_threshold: float` | `List[dict]` | 语义搜索 | ✅ 使用中 |
| `suggest_tags` | `title: str, content: str, max_tags: int` | `List[str]` | AI标签建议 | ✅ 使用中 |
| `discover_smart_links` | `file_id: int, content: str, title: str` | `List[dict]` | AI链接发现 | ✅ 使用中 |
| `chat_with_context` | `question: str, max_context_length: int, search_limit: int` | `dict` | RAG问答 | ✅ 使用中 |
| `streaming_chat_with_context` | `question: str, max_context_length: int, search_limit: int` | `AsyncGenerator` | 流式RAG问答 | ✅ 使用中 |
| `generate_summary` | `content: str, max_length: int` | `Optional[str]` | 生成摘要 | ⚠️ 未使用 |
| `analyze_content` | `content: str` | `dict` | 内容分析 | ⚠️ 未使用 |
| `generate_related_questions` | `content: str, num_questions: int` | `List[str]` | 生成相关问题 | ⚠️ 未使用 |

#### 搜索服务 (SearchService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `search` | `query: str, search_type: str, limit: int, similarity_threshold: float` | `dict` | 混合搜索 | ✅ 使用中 |
| `_keyword_search` | `query: str, limit: int` | `List[dict]` | 关键词搜索 | ✅ 使用中 |
| `_semantic_search` | `query: str, limit: int, similarity_threshold: float` | `List[dict]` | 语义搜索 | ✅ 使用中 |
| `_mixed_search` | `query: str, limit: int, similarity_threshold: float` | `List[dict]` | 混合搜索 | ✅ 使用中 |
| `get_search_history` | `limit: int` | `List[dict]` | 获取搜索历史 | ✅ 使用中 |
| `get_popular_queries` | `limit: int` | `List[dict]` | 获取热门查询 | ✅ 使用中 |

#### MCP服务 (MCPClientService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_server` | `server_data: MCPServerCreate` | `MCPServer` | 创建MCP服务器 | ✅ 使用中 |
| `update_server` | `server_id: int, update_data: MCPServerUpdate` | `Optional[MCPServer]` | 更新MCP服务器 | ✅ 使用中 |
| `get_available_tools` | `None` | `List[MCPTool]` | 获取可用工具 | ✅ 使用中 |
| `call_tool` | `request: MCPToolCallRequest` | `MCPToolCallResult` | 调用MCP工具 | ⚠️ 未使用 |
| `connect_server` | `server_id: int` | `bool` | 连接服务器 | ✅ 使用中 |
| `disconnect_server` | `server_id: int` | `bool` | 断开服务器 | ✅ 使用中 |
| `discover_tools` | `server_id: int` | `List[MCPTool]` | 发现工具 | ✅ 使用中 |
| `get_server_status` | `server_id: int` | `Optional[dict]` | 获取服务器状态 | ✅ 使用中 |

#### 索引服务 (IndexService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `get_index_status` | `None` | `dict` | 获取索引状态 | ✅ 使用中 |
| `scan_notes_directory` | `None` | `List[dict]` | 扫描笔记目录 | ✅ 使用中 |
| `rebuild_sqlite_index` | `progress_callback: callable` | `dict` | 重建SQLite索引 | ✅ 使用中 |
| `rebuild_vector_index` | `progress_callback: callable` | `dict` | 重建向量索引 | ✅ 使用中 |
| `rebuild_all_indexes` | `progress_callback: callable` | `dict` | 重建所有索引 | ✅ 使用中 |

#### 智能分块服务 (IntelligentHierarchicalSplitter) - v1.3.2新增
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `split_document` | `content: str, title: str, file_id: int, progress_callback=None` | `Dict[str, List[Document]]` | 智能多层次文档分块（v1.3.2支持进度回调）| ✅ 使用中 |
| `_create_summary_direct` | `content: str, title: str, file_id: int, progress_callback=None` | `List[Document]` | 直接生成摘要（v1.3.2支持进度回调）| ✅ 使用中 |
| `_create_summary_with_divide_conquer` | `content: str, title: str, file_id: int, progress_callback=None` | `List[Document]` | 分而治之生成摘要（v1.3.2支持进度回调）| ✅ 使用中 |
| `_create_outline_direct` | `content: str, title: str, file_id: int, progress_callback=None` | `List[Document]` | 直接提取大纲（v1.3.2支持进度回调）| ✅ 使用中 |
| `_create_outline_with_divide_conquer` | `content: str, title: str, file_id: int, progress_callback=None` | `List[Document]` | 分而治之提取大纲（v1.3.2支持进度回调）| ✅ 使用中 |
| `_create_intelligent_content_layer` | `content: str, title: str, file_id: int, outline_docs: List[Document], progress_callback=None` | `List[Document]` | 智能内容分块（v1.3.2支持进度回调）| ✅ 使用中 |
| `_fallback_to_simple_chunking` | `content: str, title: str, file_id: int` | `Dict[str, List[Document]]` | 降级到简单分块 | ✅ 使用中 |

#### 任务处理服务 (TaskProcessorService)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `create_pending_task` | `file_id: int, task_type: str, priority: int` | `bool` | 创建待处理任务 | ✅ 使用中 |
| `add_task` | `file_id: int, file_path: str, task_type: str, priority: int` | `bool` | 添加任务到队列 | ✅ 使用中 |
| `get_pending_tasks` | `limit: int` | `List[PendingTask]` | 获取待处理任务 | ✅ 使用中 |
| `process_task` | `task: PendingTask` | `bool` | 处理任务 | ✅ 使用中 |
| `_process_vector_index_task` | `file: File` | `bool` | 处理向量索引任务 | ✅ 使用中 |
| `_process_file_import_task` | `task: PendingTask` | `bool` | 处理文件导入任务（入库+向量化原子操作）| ✅ 使用中 |
| `_get_pending_tasks_count` | `None` | `int` | 获取待处理任务数量（v1.3.2新增）| ✅ 使用中 |
| `_log_chunking_progress` | `file_path: str, step: str, message: str` | `None` | 记录分块进度（v1.3.2新增）| ✅ 使用中 |
| `_is_process_running` | `pid: int` | `bool` | 检查进程是否运行（v1.3.2新增）| ✅ 使用中 |
| `process_all_pending_tasks` | `None` | `None` | 处理所有待处理任务 | ✅ 使用中 |
| `cleanup_old_tasks` | `days: int` | `None` | 清理旧任务 | ✅ 使用中 |
| `clear_duplicate_pending_tasks` | `None` | `int` | 清理重复任务 | ✅ 使用中 |
| `get_task_statistics` | `None` | `dict` | 获取任务统计 | ✅ 使用中 |
| `get_processor_status` | `None` | `dict` | 获取任务处理器状态（v1.3.3新增）| ✅ 使用中 |
| `start_processor` | `force: bool` | `dict` | 启动任务处理器（v1.3.3新增）| ✅ 使用中 |
| `stop_processor` | `None` | `dict` | 停止任务处理器（v1.3.3新增）| ✅ 使用中 |

### 🎨 前端组件函数

#### 主应用组件 (App.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `handleFileSelect` | `filePath: string, fileName: string` | `void` | 处理文件选择 | ✅ 使用中 |
| `handleSearchModalOpen` | `None` | `void` | 打开搜索模态框 | ✅ 使用中 |
| `handleChatModalOpen` | `None` | `void` | 打开聊天模态框 | ✅ 使用中 |
| `toggleSider` | `None` | `void` | 切换侧边栏 | ✅ 使用中 |
| `handleKeyDown` | `event: KeyboardEvent` | `void` | 处理键盘事件 | ✅ 使用中 |

#### 笔记编辑器 (NoteEditor.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadFileContent` | `filePath: string` | `Promise<void>` | 加载文件内容 | ✅ 使用中 |
| `handleContentChange` | `value: string` | `void` | 处理内容变化 | ✅ 使用中 |
| `handleTitleChange` | `e: React.ChangeEvent<HTMLInputElement>` | `void` | 处理标题变化 | ✅ 使用中 |
| `handleSave` | `None` | `Promise<void>` | 保存文件 | ✅ 使用中 |
| `wikiLinkPlugin` | `md: MarkdownIt` | `void` | Wiki链接插件 | ✅ 使用中 |
| `renderMarkdown` | `content: string` | `string` | 渲染Markdown | ✅ 使用中 |
| `getWordCount` | `None` | `string` | 获取字数统计 | ✅ 使用中 |

#### 文件树组件 (FileTree.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadFileTree` | `None` | `Promise<void>` | 加载文件树 | ✅ 使用中 |
| `handleSelect` | `keys: React.Key[], info: any` | `void` | 处理文件选择 | ✅ 使用中 |
| `handleCreate` | `None` | `Promise<void>` | 创建文件/目录 | ✅ 使用中 |
| `handleRename` | `None` | `Promise<void>` | 重命名文件 | ✅ 使用中 |
| `handleDelete` | `nodePath: string` | `Promise<void>` | 删除文件 | ✅ 使用中 |
| `handleRebuildIndex` | `None` | `Promise<void>` | 重建索引 | ✅ 使用中 |
| `convertToTreeData` | `nodes: FileTreeNode[]` | `DataNode[]` | 转换树数据 | ✅ 使用中 |

#### 标签管理器 (TagManager.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadTags` | `None` | `Promise<void>` | 加载标签列表 | ✅ 使用中 |
| `loadFileTags` | `None` | `Promise<void>` | 加载文件标签 | ✅ 使用中 |
| `handleSaveTag` | `values: any` | `Promise<void>` | 保存标签 | ✅ 使用中 |
| `handleDeleteTag` | `tagId: number` | `Promise<void>` | 删除标签 | ✅ 使用中 |
| `handleAddTagToFile` | `tagId: number` | `Promise<void>` | 添加标签到文件 | ✅ 使用中 |
| `handleRemoveTagFromFile` | `tagId: number` | `Promise<void>` | 从文件移除标签 | ✅ 使用中 |
| `handleAISuggestTags` | `None` | `Promise<void>` | AI标签建议 | ✅ 使用中 |

#### 链接管理器 (LinkManager.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadAllLinks` | `None` | `Promise<void>` | 加载所有链接 | ✅ 使用中 |
| `loadFileLinks` | `None` | `Promise<void>` | 加载文件链接 | ✅ 使用中 |
| `handleCreateLink` | `values: any` | `Promise<void>` | 创建链接 | ✅ 使用中 |
| `handleUpdateLink` | `values: any` | `Promise<void>` | 更新链接 | ✅ 使用中 |
| `handleDeleteLink` | `linkId: number` | `Promise<void>` | 删除链接 | ✅ 使用中 |
| `handleSmartDiscovery` | `None` | `Promise<void>` | 智能链接发现 | ✅ 使用中 |
| `applyLinkSuggestion` | `suggestion: SmartLinkSuggestion` | `Promise<void>` | 应用链接建议 | ✅ 使用中 |

#### 自动处理器 (AutoProcessor.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadFiles` | `None` | `Promise<void>` | 加载文件列表 | ✅ 使用中 |
| `processFile` | `file: FileData` | `Promise<ProcessingResult>` | 处理单个文件 | ✅ 使用中 |
| `handleBatchProcess` | `None` | `Promise<void>` | 批量处理文件 | ✅ 使用中 |
| `handlePauseResume` | `None` | `void` | 暂停/恢复处理 | ✅ 使用中 |
| `handleStop` | `None` | `void` | 停止处理 | ✅ 使用中 |

#### 搜索模态框 (SearchModal.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `handleSearch` | `query: string` | `Promise<void>` | 执行搜索 | ✅ 使用中 |
| `loadSearchHistory` | `None` | `Promise<void>` | 加载搜索历史 | ✅ 使用中 |
| `loadPopularQueries` | `None` | `Promise<void>` | 加载热门查询 | ✅ 使用中 |
| `handleSelectResult` | `result: SearchResult` | `void` | 选择搜索结果 | ✅ 使用中 |

#### 聊天模态框 (ChatModal.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `handleSendMessage` | `None` | `Promise<void>` | 发送消息 | ✅ 使用中 |
| `handleClearChat` | `None` | `void` | 清空聊天记录 | ✅ 使用中 |
| `handleDocumentClick` | `doc: any` | `void` | 点击文档 | ✅ 使用中 |

#### 关系图谱 (LinkGraph.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `initializeGraph` | `None` | `void` | 初始化图谱 | ✅ 使用中 |
| `updateGraphData` | `None` | `void` | 更新图谱数据 | ✅ 使用中 |
| `fitNetwork` | `None` | `void` | 适应网络布局 | ✅ 使用中 |
| `zoomIn` | `None` | `void` | 放大图谱 | ✅ 使用中 |
| `zoomOut` | `None` | `void` | 缩小图谱 | ✅ 使用中 |
| `focusCurrentFile` | `None` | `void` | 聚焦当前文件 | ✅ 使用中 |

#### MCP管理器 (MCPManager.tsx)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `loadServers` | `None` | `Promise<void>` | 加载MCP服务器 | ✅ 使用中 |
| `loadTools` | `None` | `Promise<void>` | 加载MCP工具 | ✅ 使用中 |
| `loadStats` | `None` | `Promise<void>` | 加载MCP统计 | ✅ 使用中 |
| `handleCreateServer` | `None` | `void` | 创建服务器 | ✅ 使用中 |
| `handleDeleteServer` | `serverId: number` | `Promise<void>` | 删除服务器 | ✅ 使用中 |
| `handleConnectServer` | `serverId: number` | `Promise<void>` | 连接服务器 | ✅ 使用中 |
| `handleDisconnectServer` | `serverId: number` | `Promise<void>` | 断开服务器 | ✅ 使用中 |

### 🗄️ 数据库操作函数

#### 数据库初始化 (init_db.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `check_database_health` | `None` | `dict` | 检查数据库健康状态 | ✅ 使用中 |
| `repair_database` | `health_status: dict` | `bool` | 修复数据库 | ✅ 使用中 |
| `init_db` | `None` | `None` | 初始化数据库 | ✅ 使用中 |
| `clean_existing_data` | `None` | `None` | 清理现有数据 | ✅ 使用中 |

#### 数据库会话 (session.py)
| 函数名称 | 输入参数 | 输出 | 说明 | 使用情况 |
|---------|---------|------|------|----------|
| `get_db` | `None` | `Generator[Session, None, None]` | 获取数据库会话 | ✅ 使用中 |

### 📋 优化建议

#### 🔴 已删除的冗余函数 ✅
1. **任务管理模块** - ✅ 已删除所有tasks.py中的5个API接口
2. **部分AI功能** - 内容分析、相关问题生成等功能未被使用
3. **部分标签功能** - 标签搜索功能未被使用
4. **部分MCP功能** - 工具调用历史等功能未被使用

#### 🟡 需要评估的函数
1. **文件API重复** - `update_file_by_path_api` 与 `update_file_api` 功能重复
2. **标签详情API** - `read_tag_api` 和 `get_tag_usage_count_api` 未被使用
3. **链接详情API** - `read_link_api` 未被使用

#### 🟢 核心业务函数
1. **文件管理** - 文件CRUD操作、文件树管理
2. **标签系统** - 标签创建、文件标签关联、AI标签建议
3. **链接系统** - 链接创建、智能链接发现
4. **搜索功能** - 混合搜索、搜索历史
5. **AI集成** - RAG问答、标签建议、链接发现
6. **MCP集成** - 服务器管理、工具发现

### 📊 统计摘要

| 模块 | 总函数数 | 使用中 | 未使用 | 已删除 |
|------|---------|--------|--------|----------|
| 后端API | 72 | 48 | 24 | 5 |
| 后端服务 | 104 | 91 | 13 | 0 |
| 前端组件 | 52 | 52 | 0 | 0 |
| 数据库操作 | 4 | 4 | 0 | 0 |
| **总计** | **232** | **195** | **37** | **5** |

**使用率**: 84.1% (195/232)
**v1.3.2更新**: 新增智能分块服务(7个方法) + 任务处理监控(3个方法)，优化进度回调机制

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

### v1.3.3 (2025-01-05) - TXT转MD自动标题问题修复 🔧
- ✅ **修复txt转md自动标题问题**：解决txt文件转换时自动添加多余##符号的问题
- ✅ **移除过于宽泛的标题检测**：不再自动识别短行为标题，保持原始文本格式
- ✅ **同时修复txt和docx转换**：两种格式都不再进行自动标题检测
- ✅ **保持用户控制权**：用户可以手动添加Markdown标记，转换结果更可预测
- ✅ **修复Docker构建问题**：移除引起哈希冲突的mypy依赖
- ✅ **完整测试验证**：确保转换后的文件与原始文件内容完全一致

#### 🔧 技术修复详情

**问题分析**：
原来的转换逻辑中存在过于宽泛的标题检测：
```python
# 原问题代码
if len(line) < 50 and not line.endswith(('。', '.', '！', '!', '？', '?')):
    markdown_lines.append(f"## {line}")  # 自动添加##符号
```

**修复方案**：
```python
# 修复后的代码
# 不做自动标题识别，保持原始文本格式
# 用户可以手动添加Markdown标记
markdown_lines.append(line)
```

**影响范围**：
- `_convert_txt_to_md()` - TXT文件转换逻辑
- `_convert_docx_to_md()` - DOCX文件转换逻辑

**修复效果**：
- ✅ 转换后的文件与原始文件内容完全一致
- ✅ 不再添加任何多余的##符号
- ✅ 用户可以按需手动添加Markdown格式
- ✅ 提高转换结果的可预测性和一致性

### v1.3.2 (2025-01-05) - 任务处理器修复与日志增强 🛠️
- ✅ **修复任务处理器锁定问题**：解决Docker重启后"任务处理器已运行但实际未运行"的假运行问题
- ✅ **改进进程检测机制**：使用psutil检查进程真实状态，避免死锁文件导致的处理停滞
- ✅ **详细智能分块日志**：在每个智能分块步骤（摘要生成、大纲提取、内容分块、向量存储）输出详细日志
- ✅ **任务队列状态监控**：每完成一个任务都会显示剩余待处理任务数量，便于进度跟踪
- ✅ **进度回调机制**：从任务处理器到AI服务再到智能分块器，全链路支持进度回调
- ✅ **分而治之策略日志**：对超长文档的分块处理过程进行详细日志记录
- ✅ **添加psutil依赖**：确保进程状态检测功能的稳定运行
- ✅ **错误降级处理**：智能分块失败时的降级处理过程也会输出相应日志

#### 🔧 技术改进详情

##### 1. 任务处理器锁定机制修复
**问题**：Docker重启后锁文件残留，导致新的任务处理器无法启动，出现"任务处理器已运行"但实际未运行的假运行状态。

**解决方案**：
```python
# 原来基于时间的检测（不准确）
if datetime.now() - lock_time > timedelta(minutes=10):
    # 认为锁过期

# 改为基于PID的真实进程检测
def _is_process_running(self, pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)  # 精确检测进程状态
    except ImportError:
        os.kill(pid, 0)  # 降级策略
        return True
```

**核心逻辑**：
- 锁文件存储进程PID而非时间戳
- 启动时检查PID对应的进程是否真实存在
- 发现死锁文件时自动清理并继续执行
- 显示当前进程PID和锁定状态

##### 2. 详细智能分块日志系统
**原子操作**：为文件导入任务（`file_import`）添加完整的进度监控链路

**进度回调链路**：
```python
# 1. 任务处理器层
TaskProcessor._process_file_import_task(task)
    ↓ progress_callback
# 2. AI服务层  
AIService.create_embeddings(file, progress_callback)
    ↓ progress_callback
# 3. 智能分块层
HierarchicalSplitter.split_document(content, title, file_id, progress_callback)
    ↓ 各个子方法
_create_summary_direct/with_divide_conquer(progress_callback)
_create_outline_direct/with_divide_conquer(progress_callback)
_create_intelligent_content_layer(progress_callback)
```

**函数变动**：为以下8个核心方法添加 `progress_callback` 参数支持
1. `AIService.create_embeddings(file, progress_callback=None)`
2. `HierarchicalSplitter.split_document(content, title, file_id, progress_callback=None)`
3. `_create_summary_direct(content, title, file_id, progress_callback=None)`
4. `_create_summary_with_divide_conquer(content, title, file_id, progress_callback=None)`
5. `_create_outline_direct(content, title, file_id, progress_callback=None)`
6. `_create_outline_with_divide_conquer(content, title, file_id, progress_callback=None)`
7. `_create_intelligent_content_layer(content, title, file_id, outline_docs, progress_callback=None)`
8. `_create_basic_fallback_chunks(file, progress_callback=None)`

##### 3. 任务队列状态监控
**新增方法**：
- `_get_pending_tasks_count()` - 获取待处理任务数量
- `_log_chunking_progress(file_path, step, message)` - 记录分块进度

**日志分类标识**：
- 📋 **任务开始**：`开始处理文件导入任务 (待处理任务: X)`
- 📖 **文件读取**：`文件内容读取完成 (大小: X字符)`
- 💾 **数据库操作**：`数据库记录保存成功`
- 🤖 **AI处理**：`开始智能多层次向量分块`
- 🔧 **分块步骤**：`[摘要生成/大纲提取/内容分块] 具体步骤进度`
- 🎉 **完成标识**：`文件处理完全成功 | 剩余任务: X`

##### 4. 分而治之策略增强
**超长文档处理**：
- 文档长度超过 `llm_context_window * 0.8` 时自动启用分而治之策略
- 摘要生成：使用Refine策略迭代处理多个文档片段
- 大纲提取：逐块处理后合并为完整大纲
- 每个处理步骤都有详细的进度日志

**错误降级处理**：
- 智能分块失败时自动降级到基本分块策略
- 降级过程也会输出相应的日志信息
- 确保每个文件都能成功处理

##### 5. 依赖管理优化
**新增依赖**：
```txt
# 进程状态检测
psutil>=5.9.0
```

**移除依赖**：
```txt
# 类型检查（开发环境不需要）
- mypy>=1.7.1
```

#### 🎯 验证结果
**修复效果**：
- ✅ 任务处理器真实状态检测：不再出现假运行问题
- ✅ 详细智能分块日志：每个步骤都有清晰的进度显示  
- ✅ 任务队列监控：实时显示剩余待处理任务数量
- ✅ 全链路进度跟踪：从文件导入到智能分块的完整进度监控
- ✅ emoji图标分类：不同类型日志有清晰的视觉标识
- ✅ 错误降级日志：智能分块失败时也有相应的日志输出

**实际日志示例**：
```
INFO:app.services.task_processor_service:📋 开始处理文件导入任务: 医学/男科病名医验案解析.md (待处理任务: 2)
INFO:app.services.task_processor_service:📖 文件内容读取完成: 医学/男科病名医验案解析.md (大小: 144872字符)
INFO:app.services.task_processor_service:💾 数据库记录保存成功: 医学/男科病名医验案解析.md
INFO:app.services.task_processor_service:🤖 开始智能多层次向量分块: 医学/男科病名医验案解析.md
INFO:app.services.task_processor_service:🔧 [摘要生成] 使用分而治之策略生成摘要 | 文件: 医学/男科病名医验案解析.md | 剩余任务: 1
INFO:app.services.task_processor_service:🔧 [大纲提取] 使用分而治之策略提取大纲 | 文件: 医学/男科病名医验案解析.md | 剩余任务: 1
INFO:app.services.task_processor_service:🔧 [智能分块] 基于大纲进行智能内容分块 | 文件: 医学/男科病名医验案解析.md | 剩余任务: 1
INFO:app.services.task_processor_service:🔧 [向量存储] 正在保存 16 个分块到向量数据库 | 文件: 医学/男科病名医验案解析.md | 剩余任务: 1
INFO:app.services.task_processor_service:🎉 文件处理完全成功: 医学/男科病名医验案解析.md | 剩余任务: 0
```

#### 📊 代码修改统计
- **修改文件数**：5个核心文件
- **新增/修改代码**：约200行代码
- **函数签名变更**：8个方法添加progress_callback参数
- **新增方法**：2个监控方法
- **依赖变更**：+1个新依赖，-1个开发依赖

### v1.3.1 (2025-01-05) - 批量文件上传优化
- ✅ **修复数据库锁定问题**：解决批量文件上传时的数据库锁定冲突
- ✅ **新增文件导入任务**：创建`file_import`任务类型，实现"入库+向量化"原子操作
- ✅ **优化任务队列机制**：文件转换后不再立即写数据库，而是添加到任务队列
- ✅ **防止并发冲突**：任务处理器串行处理文件导入任务，确保数据一致性
- ✅ **改进错误处理**：完善文件导入失败的回滚机制
- ✅ **提升系统稳定性**：解决大量文件上传时的系统不稳定问题

### v1.3.0 (2025-01-04) - 文件拖拽上传转换功能
- ✅ 新增文件拖拽上传转换功能
- ✅ 支持 TXT、MD、DOCX、PDF 格式文件
- ✅ 智能编码检测（支持 UTF-8、GBK、GB2312 等）
- ✅ 批量文件处理和进度显示
- ✅ 重名文件自动重命名
- ✅ 转换结果汇总显示
- ✅ 自动添加索引任务
- ✅ 修改 nginx 配置支持大文件上传

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