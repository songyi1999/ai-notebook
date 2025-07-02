#!/usr/bin/env python3
import sqlite3

def debug_fts():
    """调试FTS搜索问题"""
    db_path = './data/ai_notebook.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print('=== 检查FTS5配置 ===')
    
    # 检查FTS5表的详细信息
    cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'files_fts'")
    fts_sql = cursor.fetchone()
    if fts_sql:
        print('FTS表创建SQL:', fts_sql[0])
    
    print('\n=== 测试不同搜索方式 ===')
    
    # 方式1：搜索英文
    try:
        cursor.execute("SELECT rowid, title FROM files_fts WHERE files_fts MATCH ?", ('AI',))
        results = cursor.fetchall()
        print('搜索AI结果数:', len(results))
        for row in results:
            print('  ', row[0], row[1])
    except Exception as e:
        print('搜索AI失败:', e)
    
    # 方式2：搜索中文单字
    try:
        cursor.execute("SELECT rowid, title FROM files_fts WHERE files_fts MATCH ?", ('本',))
        results = cursor.fetchall()
        print('搜索本结果数:', len(results))
        for row in results:
            print('  ', row[0], row[1])
    except Exception as e:
        print('搜索本失败:', e)
    
    # 方式3：使用LIKE搜索作为对比
    try:
        cursor.execute("SELECT id, title FROM files WHERE content LIKE ?", ('%本地%',))
        results = cursor.fetchall()
        print('LIKE搜索本地结果数:', len(results))
        for row in results:
            print('  ', row[0], row[1])
    except Exception as e:
        print('LIKE搜索失败:', e)
    
    # 方式4：检查实际内容
    print('\n=== 检查实际内容 ===')
    cursor.execute("SELECT rowid, title, substr(content, 1, 200) FROM files_fts WHERE rowid = 1")
    row = cursor.fetchone()
    if row:
        print('第一条记录内容前200字符:')
        print(repr(row[2]))
        print('是否包含本地:', '本地' in row[2])
        
    # 方式5：重新创建FTS表，使用简单分词器
    print('\n=== 重新创建FTS表 ===')
    try:
        # 删除旧的FTS表
        cursor.execute("DROP TABLE IF EXISTS files_fts")
        
        # 创建新的FTS表，使用unicode61分词器
        cursor.execute("""
            CREATE VIRTUAL TABLE files_fts USING fts5(
                title, 
                content, 
                content='files', 
                content_rowid='id',
                tokenize='unicode61'
            )
        """)
        
        # 重新插入数据
        cursor.execute("INSERT INTO files_fts(rowid, title, content) SELECT id, title, content FROM files WHERE is_deleted = 0")
        
        conn.commit()
        print('FTS表重新创建完成')
        
        # 测试搜索
        cursor.execute("SELECT rowid, title FROM files_fts WHERE files_fts MATCH ?", ('本地',))
        results = cursor.fetchall()
        print('重建后搜索本地结果数:', len(results))
        for row in results:
            print('  ', row[0], row[1])
            
    except Exception as e:
        print('重建FTS表失败:', e)
    
    conn.close()

if __name__ == '__main__':
    debug_fts() 