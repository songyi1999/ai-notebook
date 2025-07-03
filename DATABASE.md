# 数据库结构文档

## 数据库概述

AI笔记本项目使用 **SQLite** 作为主数据库，配合 **ChromaDB** 作为向量搜索引擎。数据库设计遵循以下原则：

- **简洁性**：尽量减少表的数量和复杂度
- **扩展性**：支持后续功能扩展
- **性能**：优化查询性能和索引设计
- **一致性**：保证数据完整性和一致性

## 数据库架构

### 双存储架构
- **SQLite**：存储文件元数据、链接关系、标签、聊天记录等结构化数据
- **ChromaDB**：存储文档向量嵌入，由LangChain-Chroma自动管理

### 数据库文件位置
- SQLite数据库：`./data/ai_notebook.db`
- ChromaDB目录：`./data/chroma_db/`
- 笔记文件目录：`./notes/`

## 核心数据表

### 1. files (文件表)

存储所有笔记文件的元信息。

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL UNIQUE,       -- 文件路径（相对路径）
    title VARCHAR NOT NULL,                  -- 文件标题
    content TEXT,                            -- 文件内容（Markdown格式）
    content_hash VARCHAR,                    -- 内容哈希值，用于检测变更
    file_size INTEGER DEFAULT 0,            -- 文件大小（字节）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,        -- 软删除标记
    parent_folder VARCHAR,                   -- 父文件夹路径
    tags JSON,                               -- 标签（JSON格式）
    file_metadata JSON                       -- 其他元数据（JSON格式）
);

-- 索引
CREATE UNIQUE INDEX ix_files_file_path ON files(file_path);
CREATE INDEX ix_files_id ON files(id);
CREATE INDEX ix_files_is_deleted ON files(is_deleted);
CREATE INDEX ix_files_parent_folder ON files(parent_folder);
```

**字段说明：**
- `file_path`: 文件的相对路径，如 "notes/技术/Python.md"
- `title`: 从文件名或第一个标题提取的标题
- `content`: 完整的Markdown内容
- `content_hash`: SHA256哈希值，用于检测文件是否被外部修改
- `tags`: JSON数组格式，如 `["技术", "Python", "编程"]`
- `metadata`: 扩展元数据，如文档统计信息等

### 2. links (链接表)

存储文件间的双向链接关系。

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL,         -- 源文件ID
    target_file_id INTEGER,                  -- 目标文件ID（可能为空，表示链接到不存在的文件）
    link_text TEXT NOT NULL,                 -- 链接文本（如 [[目标文件]]）
    link_type VARCHAR DEFAULT 'wikilink',    -- 链接类型：wikilink, external, image等
    position_start INTEGER,                  -- 链接在源文件中的起始位置
    position_end INTEGER,                    -- 链接在源文件中的结束位置
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,           -- 链接是否有效
    
    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (target_file_id) REFERENCES files(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX ix_links_id ON links(id);
CREATE INDEX ix_links_source_file_id ON links(source_file_id);
CREATE INDEX ix_links_target_file_id ON links(target_file_id);
CREATE INDEX ix_links_link_type ON links(link_type);
CREATE INDEX ix_links_is_valid ON links(is_valid);
```

**字段说明：**
- `link_text`: 原始链接文本，如 "[[Python基础知识]]"
- `link_type`: 链接类型，支持 wikilink（双向链接）、external（外部链接）、image（图片链接）等
- `position_start/end`: 用于在编辑器中高亮显示链接位置

### 3. embeddings (嵌入向量表)

存储文本块的向量嵌入，用于语义搜索。

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,                -- 关联的文件ID
    chunk_index INTEGER NOT NULL,            -- 文本块在文件中的索引
    chunk_text TEXT NOT NULL,                -- 文本块内容
    chunk_hash VARCHAR NOT NULL,             -- 文本块哈希值
    embedding_vector BLOB,                   -- 向量数据（二进制格式）
    vector_model VARCHAR NOT NULL,           -- 使用的嵌入模型名称
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(file_id, chunk_index)
);

-- 索引
CREATE INDEX ix_embeddings_id ON embeddings(id);
CREATE INDEX ix_embeddings_file_id ON embeddings(file_id);
CREATE INDEX ix_embeddings_vector_model ON embeddings(vector_model);
```

**字段说明：**
- `chunk_index`: 文本块在文件中的顺序索引，从0开始
- `chunk_text`: 分块后的文本内容，通常1000-2000字符
- `embedding_vector`: 向量数据，使用pickle或numpy格式序列化后存储
- `vector_model`: 生成向量的模型名称，如 "bge-m3"

### 4. tags (标签表)

存储智能提取和用户创建的标签。

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,               -- 标签名称
    color TEXT,                              -- 标签颜色
    description TEXT,                        -- 标签描述
    is_auto_generated BOOLEAN DEFAULT FALSE, -- 是否自动生成
    usage_count INTEGER DEFAULT 0,           -- 使用次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_usage_count ON tags(usage_count);
```

### 5. file_tags (文件标签关联表)

记录文件和标签的关联关系。

```sql
CREATE TABLE file_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,                -- 文件ID
    tag_id INTEGER NOT NULL,                 -- 标签ID
    relevance_score REAL DEFAULT 1.0,        -- 关联度评分
    is_manual BOOLEAN DEFAULT TRUE,          -- 是否手动添加
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(file_id, tag_id)
);

-- 索引
CREATE INDEX idx_file_tags_file ON file_tags(file_id);
CREATE INDEX idx_file_tags_tag ON file_tags(tag_id);
CREATE INDEX idx_file_tags_relevance ON file_tags(relevance_score);
```

### 6. search_history (搜索历史表)

记录用户的搜索历史。

```sql
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,                     -- 搜索查询
    search_type TEXT DEFAULT 'mixed',        -- 搜索类型：keyword, semantic, mixed
    results_count INTEGER DEFAULT 0,         -- 结果数量
    response_time REAL,                      -- 响应时间（毫秒）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,                         -- 用户代理信息
    session_id TEXT                          -- 会话ID
);

-- 索引
CREATE INDEX idx_search_history_query ON search_history(query);
CREATE INDEX idx_search_history_created_at ON search_history(created_at);
CREATE INDEX idx_search_history_session ON search_history(session_id);
```

### 7. chat_sessions (聊天会话表)

存储AI问答的会话信息。

```sql
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,         -- 会话唯一标识
    title TEXT,                              -- 会话标题
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,          -- 是否为活跃会话
    metadata TEXT                            -- 会话元数据（JSON格式）
);

-- 索引
CREATE INDEX idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX idx_chat_sessions_is_active ON chat_sessions(is_active);
```

### 8. chat_messages (聊天消息表)

存储具体的问答消息。

```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,                -- 会话ID
    message_type TEXT NOT NULL,              -- 消息类型：user, assistant, system
    content TEXT NOT NULL,                   -- 消息内容
    context_files TEXT,                      -- 相关文件列表（JSON格式）
    model_name TEXT,                         -- 使用的AI模型
    tokens_used INTEGER,                     -- 使用的token数量
    response_time REAL,                      -- 响应时间（毫秒）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                           -- 消息元数据（JSON格式）
    
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_type ON chat_messages(message_type);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

### 9. system_config (系统配置表)

存储系统配置信息。

```sql
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY,
    config_key VARCHAR NOT NULL UNIQUE,      -- 配置键
    config_value TEXT,                       -- 配置值
    config_type VARCHAR DEFAULT 'string',    -- 配置类型：string, integer, boolean, json
    description TEXT,                        -- 配置描述
    is_encrypted BOOLEAN DEFAULT FALSE,      -- 是否加密存储
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX ix_system_config_id ON system_config(id);
CREATE UNIQUE INDEX ix_system_config_config_key ON system_config(config_key);
```

### 10. pending_tasks (待处理任务表)

存储后台处理任务的队列信息。

```sql
CREATE TABLE pending_tasks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,                -- 关联的文件ID
    file_path VARCHAR(500) NOT NULL,         -- 文件路径
    task_type VARCHAR(50) NOT NULL,          -- 任务类型：vector_index, fts_index
    status VARCHAR(20) DEFAULT 'pending',    -- 任务状态：pending, processing, completed, failed
    priority INTEGER DEFAULT 0,              -- 任务优先级，数字越大优先级越高
    retry_count INTEGER DEFAULT 0,           -- 重试次数
    max_retries INTEGER DEFAULT 3,           -- 最大重试次数
    error_message TEXT,                      -- 错误信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME                    -- 处理完成时间
);

-- 索引
CREATE INDEX ix_pending_tasks_id ON pending_tasks(id);
```

**字段说明：**
- `task_type`: 任务类型，主要是 `vector_index`（向量索引）
- `status`: 任务状态，支持待处理、处理中、完成、失败等状态
- `priority`: 任务优先级，用于调度任务处理顺序

## 搜索功能说明

### 关键词搜索
使用SQLite的LIKE操作符进行模糊匹配，支持标题和内容的全文搜索。

```sql
-- 关键词搜索示例
SELECT * FROM files 
WHERE (title LIKE '%keyword%' OR content LIKE '%keyword%') 
AND is_deleted = FALSE 
LIMIT 50;
```

**搜索特点：**
- **简单可靠**：使用LIKE操作符，兼容性好，不依赖FTS扩展
- **中文友好**：对中文搜索支持良好，无分词问题
- **模糊匹配**：支持部分关键词匹配
- **性能适中**：对于中等规模数据集性能表现良好

### 语义搜索
通过ChromaDB存储和检索向量嵌入，由LangChain-Chroma自动管理。

**特点：**
- **语义理解**：基于文本语义而非字面匹配
- **智能检索**：能理解同义词和相关概念
- **向量存储**：使用高效的向量数据库
- **自动管理**：向量的创建、更新、删除由系统自动处理

## 数据库配置

### SQLite配置
```python
# 数据库URL
database_url = "sqlite:///./data/ai_notebook.db"

# 连接配置
PRAGMA foreign_keys = ON;          # 启用外键约束
PRAGMA journal_mode = WAL;         # 启用WAL模式
PRAGMA synchronous = NORMAL;       # 设置同步模式
PRAGMA cache_size = 10000;         # 设置缓存大小
PRAGMA temp_store = memory;        # 临时存储在内存
```

### ChromaDB配置
```python
# ChromaDB路径
chroma_db_path = "./data/chroma_db"

# 向量维度（取决于嵌入模型）
embedding_dimension = 1536  # OpenAI text-embedding-ada-002
```

## 当前数据库状态

### 表统计信息
- **files**: 13 条记录
- **tags**: 0 条记录  
- **links**: 0 条记录
- **embeddings**: 数据由ChromaDB管理
- **chat_sessions**: 0 条记录
- **chat_messages**: 0 条记录
- **pending_tasks**: 21 条记录
- **search_history**: 0 条记录
- **system_config**: 0 条记录
- **file_tags**: 0 条记录

### 索引统计
- **用户定义索引**: 33 个
- **视图**: 无
- **触发器**: 无

## 后台任务处理

### 任务队列机制
系统使用 `pending_tasks` 表管理后台任务：

1. **任务创建**：文件创建/修改时自动添加向量索引任务
2. **任务处理**：后台线程定期处理待处理任务
3. **状态跟踪**：实时跟踪任务执行状态和结果
4. **错误处理**：支持任务重试和错误记录
5. **优先级调度**：支持任务优先级排序

### 自动索引机制
- **文件变更检测**：通过content_hash检测文件内容变化
- **智能启动**：检查索引进程状态，按需启动后台处理
- **避免重复**：使用文件锁机制防止重复执行
- **非阻塞处理**：索引在独立线程中进行，不影响文件操作

## 数据迁移策略

### 版本控制

使用简单的版本控制机制管理数据库schema变更：

```sql
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- 记录当前版本
INSERT INTO schema_migrations (version, description) VALUES 
('001_initial_schema', '初始数据库结构');
```

### 迁移脚本示例

```python
# backend/app/database/migrations/001_initial_schema.py
def upgrade():
    """升级到版本001"""
    # 执行CREATE TABLE语句
    pass

def downgrade():
    """降级到上一版本"""
    # 执行DROP TABLE语句
    pass
```

## 性能优化建议

### 1. 索引优化
- 为经常查询的字段创建索引
- 考虑复合索引以优化复杂查询
- 定期分析查询计划并优化

### 2. 查询优化
- 使用EXPLAIN QUERY PLAN分析查询性能
- 避免SELECT *，只选择需要的字段
- 合理使用LIMIT和OFFSET

### 3. 数据维护
- 定期运行VACUUM清理数据库
- 监控数据库大小和增长趋势
- 实现数据归档策略

### 4. 缓存策略
- 在应用层实现查询结果缓存 (Python字典缓存)
- 使用LRU缓存机制缓存热点数据
- 实现智能预加载机制

## 备份和恢复

### 备份策略
```bash
# 完整备份
sqlite3 notebook.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 增量备份（基于WAL文件）
cp notebook.db-wal backup_wal_$(date +%Y%m%d_%H%M%S).wal
```

### 恢复策略
```bash
# 从备份恢复
cp backup_20240101_120000.db notebook.db

# 检查数据完整性
sqlite3 notebook.db "PRAGMA integrity_check;"
```

## 监控和维护

### 关键指标监控
- 数据库文件大小
- 查询响应时间
- 并发连接数
- 错误日志

### 定期维护任务
- 清理软删除的数据
- 重建搜索索引
- 更新统计信息
- 检查数据一致性

---

**注意**：这个数据库结构基于当前系统的实际实现，包含了完整的文件管理、链接关系、向量搜索、AI问答和后台任务处理功能。所有的结构变更都通过SQLAlchemy的ORM模型管理，确保数据的一致性和完整性。

**更新时间**：2024年12月 