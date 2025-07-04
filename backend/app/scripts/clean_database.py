#!/usr/bin/env python3
"""
数据库清理脚本：删除旧的SQLite和向量库文件
用于开发阶段重新开始，清理所有旧数据
"""
import os
import shutil
import logging
import argparse
from pathlib import Path
import sys

# 添加parent目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

logger = logging.getLogger(__name__)

def clean_sqlite_database():
    """清理SQLite数据库文件"""
    try:
        # 从DATABASE_URL中提取数据库文件路径
        db_url = settings.database_url
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            
            # 处理相对路径
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(__file__), '..', '..', db_path)
            
            db_path = os.path.normpath(db_path)
            
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"✅ 已删除SQLite数据库文件: {db_path}")
                logger.info(f"✅ 已删除SQLite数据库文件: {db_path}")
                return True
            else:
                print(f"ℹ️ SQLite数据库文件不存在: {db_path}")
                logger.info(f"ℹ️ SQLite数据库文件不存在: {db_path}")
                return True
        else:
            print(f"⚠️ 不支持的数据库URL格式: {db_url}")
            logger.warning(f"⚠️ 不支持的数据库URL格式: {db_url}")
            return False
            
    except Exception as e:
        print(f"❌ 清理SQLite数据库失败: {e}")
        logger.error(f"❌ 清理SQLite数据库失败: {e}")
        return False

def clean_chroma_database():
    """清理ChromaDB向量数据库"""
    try:
        chroma_path = settings.chroma_db_path
        
        # 处理相对路径
        if not os.path.isabs(chroma_path):
            chroma_path = os.path.join(os.path.dirname(__file__), '..', '..', chroma_path)
        
        chroma_path = os.path.normpath(chroma_path)
        
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)
            print(f"✅ 已删除ChromaDB向量数据库目录: {chroma_path}")
            logger.info(f"✅ 已删除ChromaDB向量数据库目录: {chroma_path}")
            return True
        else:
            print(f"ℹ️ ChromaDB向量数据库目录不存在: {chroma_path}")
            logger.info(f"ℹ️ ChromaDB向量数据库目录不存在: {chroma_path}")
            return True
            
    except Exception as e:
        print(f"❌ 清理ChromaDB向量数据库失败: {e}")
        logger.error(f"❌ 清理ChromaDB向量数据库失败: {e}")
        return False

def recreate_directories():
    """重新创建必要的目录"""
    try:
        # 重新创建数据目录
        data_dir = settings.data_directory
        if not os.path.isabs(data_dir):
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', data_dir)
        data_dir = os.path.normpath(data_dir)
        
        os.makedirs(data_dir, exist_ok=True)
        print(f"✅ 已重新创建数据目录: {data_dir}")
        logger.info(f"✅ 已重新创建数据目录: {data_dir}")
        
        # 重新创建ChromaDB目录
        chroma_dir = settings.chroma_db_path
        if not os.path.isabs(chroma_dir):
            chroma_dir = os.path.join(os.path.dirname(__file__), '..', '..', chroma_dir)
        chroma_dir = os.path.normpath(chroma_dir)
        
        os.makedirs(chroma_dir, exist_ok=True)
        print(f"✅ 已重新创建ChromaDB目录: {chroma_dir}")
        logger.info(f"✅ 已重新创建ChromaDB目录: {chroma_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 重新创建目录失败: {e}")
        logger.error(f"❌ 重新创建目录失败: {e}")
        return False

def main():
    """主清理函数"""
    parser = argparse.ArgumentParser(description='数据库清理工具')
    parser.add_argument('--force', '-f', action='store_true', help='跳过确认提示，强制执行清理')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 50)
    print("🗑️  数据库清理工具")
    print("=" * 50)
    print("⚠️  警告：此操作将删除所有数据库文件和向量数据！")
    print("✅ 适用于开发阶段的数据重置")
    print("=" * 50)
    
    # 确认操作（除非使用--force参数）
    if not args.force:
        try:
            confirm = input("确认要清理所有数据吗？输入 'yes' 继续: ").strip().lower()
            if confirm != 'yes':
                print("❌ 操作已取消")
                return
        except (KeyboardInterrupt, EOFError):
            print("\n❌ 操作已取消")
            return
    else:
        print("🚀 强制模式：跳过确认")
    
    print("\n🚀 开始清理数据库...")
    
    # 执行清理操作
    success_count = 0
    total_operations = 3
    
    if clean_sqlite_database():
        success_count += 1
    
    if clean_chroma_database():
        success_count += 1
    
    if recreate_directories():
        success_count += 1
    
    print(f"\n📊 清理完成: {success_count}/{total_operations} 个操作成功")
    
    if success_count == total_operations:
        print("✅ 所有数据库文件已成功清理！")
        print("🔄 现在可以重新启动应用程序，系统将创建新的数据库")
        print("💡 提示：重新启动Docker容器以应用更改")
    else:
        print("⚠️ 部分操作失败，请检查日志信息")

if __name__ == "__main__":
    main() 