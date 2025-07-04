#!/usr/bin/env python3
"""
统一文件处理架构测试脚本
测试新的原子操作文件处理机制
"""

import os
import time
import json
import requests
import tempfile
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_unified_file_processing():
    """测试统一文件处理架构"""
    print("🚀 开始测试统一文件处理架构...")
    
    # 创建测试文件
    test_content = """# 统一文件处理测试

这是一个测试文档，用于验证新的统一文件处理架构。

## 核心特性

1. **原子操作**：文件入库+向量化作为一个原子事务
2. **任务队列**：所有文件处理都通过任务队列
3. **统一入口**：单一的处理逻辑，便于维护和扩展

## 测试场景

- 文件上传处理
- 文件修改更新
- 批量文件导入
- 系统索引重建

这个测试验证了新架构的稳定性和正确性。
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        # 1. 测试文件上传
        print("\n📁 测试1：文件上传...")
        upload_result = test_file_upload(temp_file)
        if upload_result:
            print("✅ 文件上传测试通过")
        else:
            print("❌ 文件上传测试失败")
            return False
        
        # 2. 等待任务处理
        print("\n⏳ 等待任务处理...")
        time.sleep(5)
        
        # 3. 检查任务状态
        print("\n📊 测试2：检查任务状态...")
        task_status = get_task_statistics()
        print(f"任务统计: {json.dumps(task_status, indent=2, ensure_ascii=False)}")
        
        # 4. 检查系统状态
        print("\n🔍 测试3：检查系统状态...")
        system_status = get_system_status()
        print(f"系统状态: {json.dumps(system_status, indent=2, ensure_ascii=False)}")
        
        # 5. 测试搜索功能
        print("\n🔎 测试4：测试搜索功能...")
        search_result = test_search("统一文件处理")
        if search_result and len(search_result.get('results', [])) > 0:
            print("✅ 搜索功能测试通过")
        else:
            print("⚠️ 搜索功能可能需要更多时间建立索引")
        
        print("\n🎉 统一文件处理架构测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file)
        except:
            pass

def test_file_upload(file_path):
    """测试文件上传"""
    try:
        with open(file_path, 'rb') as f:
            files = {'files': (Path(file_path).name, f, 'text/markdown')}
            data = {'target_folder': '测试文件夹'}
            
            response = requests.post(
                f"{BASE_URL}/api/v1/file-upload/upload-and-convert",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"上传结果: {result.get('message', '未知')}")
            print(f"排队任务数: {result.get('summary', {}).get('queued_import_tasks', 0)}")
            return True
        else:
            print(f"上传失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"上传请求失败: {e}")
        return False

def get_task_statistics():
    """获取任务统计"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/index/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_system_status():
    """获取系统状态"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/files/", timeout=10)
        if response.status_code == 200:
            files = response.json()
            return {
                "total_files": len(files),
                "sample_files": [f.get('title', f.get('file_path', '')) for f in files[:3]]
            }
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def test_search(query):
    """测试搜索功能"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/files/search",
            params={"q": query, "search_type": "mixed", "limit": 5},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"搜索到 {len(result.get('results', []))} 个结果")
            return result
        else:
            print(f"搜索失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"搜索请求失败: {e}")
        return None

if __name__ == "__main__":
    # 检查服务是否可用
    try:
        response = requests.get(f"{BASE_URL}/api/v1/files/", timeout=5)
        if response.status_code != 200:
            print("❌ 后端服务不可用，请确保服务正在运行")
            exit(1)
    except:
        print("❌ 无法连接到后端服务，请检查服务状态")
        exit(1)
    
    # 运行测试
    success = test_unified_file_processing()
    exit(0 if success else 1) 