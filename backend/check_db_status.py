#!/usr/bin/env python3
import sys
sys.path.append('.')
from app.database.session import get_db
from app.models.embedding import Embedding
from app.models.file import File

db = next(get_db())

# 检查embedding表的结构
print('=== Embedding表结构 ===')
print(f'表名: {Embedding.__tablename__}')
for column in Embedding.__table__.columns:
    print(f'列: {column.name} - 类型: {column.type}')

# 检查是否有embedding数据
total_embeddings = db.query(Embedding).count()
print(f'\n=== 数据统计 ===')
print(f'总嵌入数: {total_embeddings}')

# 检查是否有文件数据
total_files = db.query(File).filter(File.is_deleted == False).count()
print(f'总文件数: {total_files}')

# 检查最新的embedding数据
if total_embeddings > 0:
    latest_emb = db.query(Embedding).order_by(Embedding.id.desc()).first()
    print(f'\n=== 最新嵌入数据 ===')
    print(f'ID: {latest_emb.id}')
    print(f'File ID: {latest_emb.file_id}')
    print(f'Chunk Type: {getattr(latest_emb, "chunk_type", "NOT FOUND")}')
    print(f'内容: {latest_emb.chunk_text[:100]}...')

db.close() 