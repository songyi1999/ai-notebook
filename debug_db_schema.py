import sqlite3
import os

def check_database():
    db_path = "/app/data/ai_notebook.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 检查数据库连接 ===")
        cursor.execute("SELECT sqlite_version()")
        print(f"SQLite版本: {cursor.fetchone()[0]}")
        
        print("\n=== Files表结构 ===")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='files'")
        result = cursor.fetchone()
        if result:
            print(result[0])
        else:
            print("Files表不存在")
            
        print("\n=== 检查表约束 ===")
        cursor.execute("PRAGMA table_info(files)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"列: {col[1]}, 类型: {col[2]}, 非空: {col[3]}, 默认值: {col[4]}, 主键: {col[5]}")
            
        print("\n=== 检查索引 ===")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='files'")
        indexes = cursor.fetchall()
        for idx in indexes:
            print(f"索引: {idx[0]}")
            print(f"SQL: {idx[1]}")
            
        print("\n=== 检查触发器 ===")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='files'")
        triggers = cursor.fetchall()
        for trigger in triggers:
            print(f"触发器: {trigger[0]}")
            print(f"SQL: {trigger[1]}")
            
        print("\n=== 检查FTS表 ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
        fts_tables = cursor.fetchall()
        for table in fts_tables:
            print(f"FTS表: {table[0]}")
            
        print("\n=== 测试简单查询 ===")
        try:
            cursor.execute("SELECT COUNT(*) FROM files")
            count = cursor.fetchone()[0]
            print(f"Files表记录数: {count}")
        except Exception as e:
            print(f"查询files表失败: {e}")
            
        print("\n=== 测试UPDATE语句 ===")
        try:
            # 测试一个简单的UPDATE
            cursor.execute("UPDATE files SET updated_at = datetime('now') WHERE id = 999999")
            print("UPDATE测试成功（没有匹配的记录）")
        except Exception as e:
            print(f"UPDATE测试失败: {e}")
            
        conn.close()
        
    except Exception as e:
        print(f"数据库连接失败: {e}")

if __name__ == "__main__":
    check_database() 