#!/usr/bin/env python3
import sys
sys.path.append('.')
from app.database.session import get_db
from app.models.file import File
from app.models.embedding import Embedding

# 获取数据库连接
db = next(get_db())

# 统计向量数据
summary_count = db.query(Embedding).filter(Embedding.chunk_type == 'summary').count()
outline_count = db.query(Embedding).filter(Embedding.chunk_type == 'outline').count()
content_count = db.query(Embedding).filter(Embedding.chunk_type == 'content').count()

print('=== 数据库向量统计 ===')
print(f'📊 摘要块: {summary_count}')
print(f'📊 大纲块: {outline_count}')
print(f'📊 内容块: {content_count}')
print(f'📊 总计: {summary_count + outline_count + content_count}')

# 检查最新的向量数据
latest_embeddings = db.query(Embedding).order_by(Embedding.id.desc()).limit(5).all()
print(f'\n=== 最新向量数据 ===')
for emb in latest_embeddings:
    file_info = db.query(File).filter(File.id == emb.file_id).first()
    print(f'📄 文件: {file_info.title if file_info else "Unknown"} (ID: {emb.file_id})')
    print(f'🏷️  类型: {emb.chunk_type}, 级别: {emb.chunk_level}')
    print(f'🎯 章节: {emb.section_path or "N/A"}')
    print(f'📝 内容: {emb.chunk_text[:100]}...')
    print('---')

db.close() 