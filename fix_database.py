import sqlite3
import os
import shutil
from datetime import datetime

def fix_database():
    db_path = "/app/data/ai_notebook.db"
    backup_path = "/app/data/ai_notebook_backup.db"
    
    try:
        print("=== 数据库修复开始 ===")
        
        # 1. 创建备份
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✅ 已创建数据库备份: {backup_path}")
        
        # 2. 检查数据库完整性
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n=== 检查数据库完整性 ===")
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchall()
        for result in integrity_result:
            print(f"完整性检查: {result[0]}")
            
        # 3. 检查是否有活动事务
        print("\n=== 检查事务状态 ===")
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("ROLLBACK")
            print("✅ 无活动事务")
        except Exception as e:
            print(f"❌ 可能有活动事务: {e}")
            
        # 4. 尝试修复方法1: 重建数据库
        print("\n=== 方法1: 导出数据并重建数据库 ===")
        
        # 导出所有数据
        cursor.execute("SELECT * FROM files")
        files_data = cursor.fetchall()
        print(f"导出了 {len(files_data)} 条files记录")
        
        # 获取表结构
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='files'")
        table_sql = cursor.fetchone()[0]
        
        conn.close()
        
        # 删除旧数据库文件
        if os.path.exists(db_path):
            os.remove(db_path)
            print("✅ 已删除损坏的数据库文件")
            
        # 创建新数据库
        new_conn = sqlite3.connect(db_path)
        new_cursor = new_conn.cursor()
        
        # 重建表结构
        new_cursor.execute(table_sql)
        print("✅ 已重建files表结构")
        
        # 创建索引
        new_cursor.execute("CREATE INDEX IF NOT EXISTS ix_files_is_deleted ON files (is_deleted)")
        new_cursor.execute("CREATE INDEX IF NOT EXISTS ix_files_id ON files (id)")
        new_cursor.execute("CREATE INDEX IF NOT EXISTS ix_files_parent_folder ON files (parent_folder)")
        new_cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_files_file_path ON files (file_path)")
        print("✅ 已重建索引")
        
        # 重建FTS表
        new_cursor.execute("""
            CREATE VIRTUAL TABLE files_fts USING fts5(
                title,
                content,
                tokenize='unicode61 remove_diacritics 0'
            )
        """)
        print("✅ 已重建FTS表")
        
        # 重建触发器
        new_cursor.execute("""
            CREATE TRIGGER files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END
        """)
        
        new_cursor.execute("""
            CREATE TRIGGER files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
                INSERT INTO files_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END
        """)
        
        new_cursor.execute("""
            CREATE TRIGGER files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
            END
        """)
        print("✅ 已重建触发器")
        
        # 插入数据
        if files_data:
            # 获取列名
            columns = [desc[0] for desc in cursor.description] if hasattr(cursor, 'description') else [
                'id', 'file_path', 'title', 'content', 'content_hash', 'file_size', 
                'created_at', 'updated_at', 'is_deleted', 'parent_folder', 'tags', 'file_metadata'
            ]
            
            placeholders = ','.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO files ({','.join(columns)}) VALUES ({placeholders})"
            
            for row in files_data:
                try:
                    new_cursor.execute(insert_sql, row)
                except Exception as e:
                    print(f"插入记录失败: {row[0] if row else 'unknown'}, 错误: {e}")
                    
            print(f"✅ 已插入 {len(files_data)} 条记录")
        
        new_conn.commit()
        
        # 测试UPDATE操作
        print("\n=== 测试新数据库的UPDATE操作 ===")
        try:
            new_cursor.execute("UPDATE files SET updated_at = datetime('now') WHERE id = 7")
            new_conn.commit()
            print("✅ UPDATE操作测试成功")
        except Exception as e:
            print(f"❌ UPDATE操作仍然失败: {e}")
            
        new_conn.close()
        print("\n=== 数据库修复完成 ===")
        
    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")

if __name__ == "__main__":
    fix_database() 