# 启动时重建索引功能验证指南

## 功能概述

每次容器重启时，系统会自动：
1. 删除现有的SQLite数据库文件
2. 删除现有的向量数据库目录
3. 重新创建数据库表结构和FTS索引
4. 扫描notes目录中的所有文件
5. 重建SQLite索引和FTS全文搜索
6. 重建向量索引和嵌入

## 验证步骤

### 1. 启动容器并观察日志

```bash
# 启动容器
docker-compose up --build

# 或者只查看后端日志
docker-compose logs -f backend
```

### 2. 检查启动日志

启动时应该看到以下关键日志信息：

```
================================================
AI笔记本项目 - 后端服务启动
================================================
启动时将执行以下操作：
1. 清理现有SQLite数据库文件
2. 清理现有向量数据库目录
3. 重新创建数据库表结构
4. 扫描notes目录中的所有文件
5. 重建SQLite索引和FTS全文搜索
6. 重建向量索引
================================================

INFO:app.database.init_db:开始初始化数据库...
INFO:app.database.init_db:开始清理现有数据...
INFO:app.database.init_db:已删除SQLite数据库文件: ./data/ai_notebook.db
INFO:app.database.init_db:已删除向量数据库目录: ./data/chroma_db
INFO:app.database.init_db:向量数据库目录已重新创建
INFO:app.database.init_db:数据清理完成
INFO:app.database.init_db:已创建所有标准数据库表。
INFO:app.database.init_db:已创建 files_fts 全文搜索虚拟表。
INFO:app.database.init_db:已创建 files_ai 插入触发器。
INFO:app.database.init_db:已创建 files_au 更新触发器。
INFO:app.database.init_db:已创建 files_ad 删除触发器。
INFO:app.database.init_db:开始扫描笔记目录并重建索引...
INFO:app.services.index_service:开始重建SQLite索引...
INFO:app.services.index_service:扫描notes目录: ../notes
INFO:app.services.index_service:找到 X 个Markdown文件
INFO:app.services.index_service:SQLite索引重建完成，处理了 X 个文件
INFO:app.services.index_service:开始重建向量索引...
INFO:app.services.index_service:向量索引重建完成，处理了 X 个文件
INFO:app.database.init_db:文件索引重建成功。
INFO:app.database.init_db:数据库初始化完成。
```

### 3. 验证功能正常

启动完成后，验证以下功能：

#### 3.1 搜索功能
- 打开前端界面 http://localhost:3000
- 按 `Ctrl+K` 打开搜索框
- 搜索已知存在的内容（如"本地"、"测试"等）
- 验证能够返回正确的搜索结果

#### 3.2 文件保存功能
- 创建或编辑一个笔记文件
- 按 `Ctrl+S` 保存
- 验证保存成功，没有500错误

#### 3.3 索引状态检查
访问索引状态API：
```bash
curl http://localhost:8000/api/v1/index/status
```

应该返回类似：
```json
{
  "sqlite_files": 5,
  "vector_embeddings": 5,
  "disk_files": 5,
  "needs_rebuild": false,
  "last_scan_time": "2024-01-01T12:00:00"
}
```

## 常见问题排查

### 1. 启动时间过长
- 正常情况下，重建索引需要一定时间
- 文件数量越多，重建时间越长
- 可以通过日志观察进度

### 2. 重建失败
如果看到以下错误日志：
```
ERROR:app.database.init_db:重建索引失败: ...
```

可能的原因：
- notes目录不可访问
- 磁盘空间不足
- 文件权限问题

### 3. 搜索功能异常
- 检查FTS表是否正确创建
- 检查触发器是否正确创建
- 查看向量数据库是否有数据

### 4. 文件保存失败
- 检查数据库文件是否可写
- 检查磁盘空间是否充足
- 查看数据库表结构是否正确

## 优势与注意事项

### 优势
1. **数据一致性**：每次启动都是全新的索引，避免数据不一致
2. **简化维护**：不需要复杂的增量更新逻辑
3. **问题自愈**：任何数据库问题都会在下次重启时自动修复
4. **易于调试**：启动日志清晰显示每个步骤的状态

### 注意事项
1. **启动时间**：首次启动或文件较多时重建时间较长
2. **资源消耗**：重建过程会消耗CPU和内存资源
3. **数据丢失**：搜索历史等运行时数据会在重启时丢失
4. **网络依赖**：如果使用远程AI服务，需要网络连接

## 性能优化建议

1. **文件组织**：合理组织notes目录结构，避免过深的嵌套
2. **文件大小**：单个文件不要过大，建议控制在100KB以内
3. **文件数量**：如果文件数量过多（>1000），考虑分批处理
4. **资源配置**：为Docker容器分配足够的内存和CPU资源 