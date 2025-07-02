import sqlite3
import os
from datetime import datetime

def test_update_operations():
    db_path = "/app/data/ai_notebook.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 测试分步UPDATE ===")
        
        # 测试1: 只更新content
        try:
            cursor.execute("UPDATE files SET content = ? WHERE id = ?", (
                '# 测试自行车\n\n我有一辆自行车。', 7
            ))
            print("✅ 只更新content成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 只更新content失败: {e}")
            
        # 测试2: 只更新content_hash
        try:
            cursor.execute("UPDATE files SET content_hash = ? WHERE id = ?", (
                '31d85f27560020b0b8e51386401c8a38048127e64ac80e2309dd0438a1bb242e', 7
            ))
            print("✅ 只更新content_hash成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 只更新content_hash失败: {e}")
            
        # 测试3: 只更新file_size
        try:
            cursor.execute("UPDATE files SET file_size = ? WHERE id = ?", (43, 7))
            print("✅ 只更新file_size成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 只更新file_size失败: {e}")
            
        # 测试4: 只更新updated_at
        try:
            cursor.execute("UPDATE files SET updated_at = ? WHERE id = ?", (
                '2025-07-01 03:58:39.653544', 7
            ))
            print("✅ 只更新updated_at成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 只更新updated_at失败: {e}")
            
        # 测试5: 更新content + content_hash
        try:
            cursor.execute("UPDATE files SET content = ?, content_hash = ? WHERE id = ?", (
                '# 测试自行车\n\n我有一辆自行车。',
                '31d85f27560020b0b8e51386401c8a38048127e64ac80e2309dd0438a1bb242e',
                7
            ))
            print("✅ 更新content + content_hash成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 更新content + content_hash失败: {e}")
            
        # 测试6: 更新content + content_hash + file_size
        try:
            cursor.execute("UPDATE files SET content = ?, content_hash = ?, file_size = ? WHERE id = ?", (
                '# 测试自行车\n\n我有一辆自行车。',
                '31d85f27560020b0b8e51386401c8a38048127e64ac80e2309dd0438a1bb242e',
                43,
                7
            ))
            print("✅ 更新content + content_hash + file_size成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 更新content + content_hash + file_size失败: {e}")
            
        print("\n=== 测试不同的时间格式 ===")
        
        # 测试7: 使用datetime('now')
        try:
            cursor.execute("UPDATE files SET updated_at = datetime('now') WHERE id = ?", (7,))
            print("✅ 使用datetime('now')成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 使用datetime('now')失败: {e}")
            
        # 测试8: 使用CURRENT_TIMESTAMP
        try:
            cursor.execute("UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (7,))
            print("✅ 使用CURRENT_TIMESTAMP成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 使用CURRENT_TIMESTAMP失败: {e}")
            
        # 测试9: 使用Python datetime
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            cursor.execute("UPDATE files SET updated_at = ? WHERE id = ?", (now, 7))
            print("✅ 使用Python datetime成功")
            conn.rollback()
        except Exception as e:
            print(f"❌ 使用Python datetime失败: {e}")
            
        print("\n=== 检查记录是否被锁定 ===")
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("SELECT * FROM files WHERE id = 7 FOR UPDATE")
            print("✅ 记录未被锁定")
            conn.rollback()
        except Exception as e:
            print(f"❌ 记录可能被锁定: {e}")
            
        conn.close()
        
    except Exception as e:
        print(f"数据库操作失败: {e}")

if __name__ == "__main__":
    test_update_operations() 