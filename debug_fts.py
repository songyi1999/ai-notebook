import sqlite3
import os

def check_fts_issues():
    db_path = "/app/data/ai_notebook.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 检查FTS表状态 ===")
        try:
            cursor.execute("SELECT COUNT(*) FROM files_fts")
            fts_count = cursor.fetchone()[0]
            print(f"FTS表记录数: {fts_count}")
        except Exception as e:
            print(f"FTS表查询失败: {e}")
            
        print("\n=== 检查files表中的具体记录 ===")
        try:
            cursor.execute("SELECT id, file_path, title, content_hash, updated_at FROM files WHERE id = 7")
            record = cursor.fetchone()
            if record:
                print(f"ID: {record[0]}")
                print(f"Path: {record[1]}")
                print(f"Title: {record[2]}")
                print(f"Hash: {record[3]}")
                print(f"Updated: {record[4]}")
            else:
                print("ID=7的记录不存在")
        except Exception as e:
            print(f"查询ID=7记录失败: {e}")
            
        print("\n=== 测试具体的UPDATE操作 ===")
        try:
            # 尝试执行与错误日志相同的UPDATE
            cursor.execute("""
                UPDATE files 
                SET content=?, content_hash=?, file_size=?, updated_at=? 
                WHERE id = ?
            """, (
                '# 测试自行车\n\n我有一辆自行车。',
                '31d85f27560020b0b8e51386401c8a38048127e64ac80e2309dd0438a1bb242e',
                43,
                '2025-07-01 03:58:39.653544',
                7
            ))
            print("UPDATE操作成功")
            conn.rollback()  # 回滚，不实际保存
        except Exception as e:
            print(f"UPDATE操作失败: {e}")
            
        print("\n=== 测试FTS触发器 ===")
        try:
            # 临时禁用触发器测试
            cursor.execute("PRAGMA recursive_triggers = OFF")
            cursor.execute("""
                UPDATE files 
                SET content=?, content_hash=?, file_size=?, updated_at=? 
                WHERE id = ?
            """, (
                '# 测试自行车\n\n我有一辆自行车。',
                '31d85f27560020b0b8e51386401c8a38048127e64ac80e2309dd0438a1bb242e',
                43,
                '2025-07-01 03:58:39.653544',
                7
            ))
            print("禁用触发器后UPDATE成功")
            conn.rollback()
        except Exception as e:
            print(f"禁用触发器后UPDATE仍失败: {e}")
            
        print("\n=== 检查FTS表结构 ===")
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE name='files_fts'")
            fts_sql = cursor.fetchone()
            if fts_sql:
                print(f"FTS表结构: {fts_sql[0]}")
        except Exception as e:
            print(f"检查FTS表结构失败: {e}")
            
        print("\n=== 测试FTS表操作 ===")
        try:
            cursor.execute("INSERT INTO files_fts(rowid, title, content) VALUES (999999, 'test', 'test content')")
            cursor.execute("DELETE FROM files_fts WHERE rowid = 999999")
            print("FTS表操作测试成功")
        except Exception as e:
            print(f"FTS表操作测试失败: {e}")
            
        conn.close()
        
    except Exception as e:
        print(f"数据库操作失败: {e}")

if __name__ == "__main__":
    check_fts_issues() 