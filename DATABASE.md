# 数据库结构文档

## 数据库概述

AI笔记本项目使用 **SQLite** 作为主数据库，配合 **ChromaDB** 作为向量搜索引擎。数据库设计遵循以下原则：

- **简洁性**：尽量减少表的数量和复杂度
- **扩展性**：支持后续功能扩展
- **性能**：优化查询性能和索引设计
- **一致性**：保证数据完整性和一致性

## 核心数据表

### 1. files (文件表)

存储所有笔记文件的元信息。

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,           -- 文件路径（相对路径）
    title TEXT NOT NULL,                      -- 文件标题
    content TEXT,                             -- 文件内容（Markdown格式）
    content_hash TEXT,                        -- 内容哈希值，用于检测变更
    file_size INTEGER DEFAULT 0,             -- 文件大小（字节）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,         -- 软删除标记
    parent_folder TEXT,                       -- 父文件夹路径
    tags TEXT,                                -- 标签（JSON格式）
    metadata TEXT                             -- 其他元数据（JSON格式）
);

-- 索引
CREATE INDEX idx_files_file_path ON files(file_path);
CREATE INDEX idx_files_created_at ON files(created_at);
CREATE INDEX idx_files_updated_at ON files(updated_at);
CREATE INDEX idx_files_parent_folder ON files(parent_folder);
CREATE INDEX idx_files_is_deleted ON files(is_deleted);
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER NOT NULL,         -- 源文件ID
    target_file_id INTEGER,                  -- 目标文件ID（可能为空，表示链接到不存在的文件）
    link_text TEXT NOT NULL,                 -- 链接文本（如 [[目标文件]]）
    link_type TEXT DEFAULT 'wikilink',       -- 链接类型：wikilink, external, image等
    position_start INTEGER,                  -- 链接在源文件中的起始位置
    position_end INTEGER,                    -- 链接在源文件中的结束位置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,           -- 链接是否有效
    
    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (target_file_id) REFERENCES files(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX idx_links_source_file ON links(source_file_id);
CREATE INDEX idx_links_target_file ON links(target_file_id);
CREATE INDEX idx_links_type ON links(link_type);
CREATE INDEX idx_links_is_valid ON links(is_valid);
```

**字段说明：**
- `link_text`: 原始链接文本，如 "[[Python基础知识]]"
- `link_type`: 链接类型，支持 wikilink（双向链接）、external（外部链接）、image（图片链接）等
- `position_start/end`: 用于在编辑器中高亮显示链接位置

### 3. embeddings (嵌入向量表)

存储文本块的向量嵌入，用于语义搜索。

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,                -- 关联的文件ID
    chunk_index INTEGER NOT NULL,            -- 文本块在文件中的索引
    chunk_text TEXT NOT NULL,                -- 文本块内容
    chunk_hash TEXT NOT NULL,                -- 文本块哈希值
    embedding_vector BLOB,                   -- 向量数据（二进制格式）
    vector_model TEXT NOT NULL,              -- 使用的嵌入模型名称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(file_id, chunk_index)
);

-- 索引
CREATE INDEX idx_embeddings_file_id ON embeddings(file_id);
CREATE INDEX idx_embeddings_chunk_hash ON embeddings(chunk_hash);
CREATE INDEX idx_embeddings_model ON embeddings(vector_model);
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,         -- 配置键
    config_value TEXT,                       -- 配置值
    config_type TEXT DEFAULT 'string',       -- 配置类型：string, integer, boolean, json
    description TEXT,                        -- 配置描述
    is_encrypted BOOLEAN DEFAULT FALSE,      -- 是否加密存储
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_system_config_key ON system_config(config_key);
```

### 10. 搜索功能说明

关键词搜索现在使用SQLite的LIKE操作符进行模糊匹配，支持标题和内容的全文搜索。

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

## 视图定义

### 1. file_stats_view (文件统计视图)

```sql
CREATE VIEW file_stats_view AS
SELECT 
    f.id,
    f.file_path,
    f.title,
    f.created_at,
    f.updated_at,
    LENGTH(f.content) as content_length,
    (LENGTH(f.content) - LENGTH(REPLACE(f.content, ' ', ''))) as word_count,
    COUNT(DISTINCT l1.id) as outbound_links,
    COUNT(DISTINCT l2.id) as inbound_links,
    COUNT(DISTINCT ft.tag_id) as tags_count
FROM files f
LEFT JOIN links l1 ON f.id = l1.source_file_id AND l1.is_valid = TRUE
LEFT JOIN links l2 ON f.id = l2.target_file_id AND l2.is_valid = TRUE
LEFT JOIN file_tags ft ON f.id = ft.file_id
WHERE f.is_deleted = FALSE
GROUP BY f.id;
```

### 2. tag_stats_view (标签统计视图)

```sql
CREATE VIEW tag_stats_view AS
SELECT 
    t.id,
    t.name,
    t.is_auto_generated,
    COUNT(DISTINCT ft.file_id) as tagged_files_count,
    AVG(ft.relevance_score) as avg_relevance_score,
    t.usage_count
FROM tags t
LEFT JOIN file_tags ft ON t.id = ft.tag_id
GROUP BY t.id;
```

## 数据库初始化脚本

```sql
-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 设置日志模式
PRAGMA journal_mode = WAL;

-- 设置同步模式
PRAGMA synchronous = NORMAL;

-- 设置缓存大小
PRAGMA cache_size = 10000;

-- 设置临时存储
PRAGMA temp_store = memory;

-- 创建所有表和索引
-- （在这里执行上述所有CREATE TABLE和CREATE INDEX语句）

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('app_version', '0.1.0', 'string', '应用版本号'),
('embedding_model', 'bge-m3', 'string', '默认嵌入模型'),
('llm_model', 'llama3', 'string', '默认大语言模型'),
('chunk_size', '1000', 'integer', '文本分块大小'),
('chunk_overlap', '200', 'integer', '文本分块重叠大小'),
('max_search_results', '20', 'integer', '最大搜索结果数'),
('enable_auto_index', 'true', 'boolean', '是否启用自动索引'),
('search_timeout', '30', 'integer', '搜索超时时间（秒）');
```

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

**注意**：这个数据库结构是基于当前需求设计的，在实际开发过程中可能会根据具体需求进行调整和优化。所有的结构变更都应该通过迁移脚本来管理，确保数据的一致性和完整性。 