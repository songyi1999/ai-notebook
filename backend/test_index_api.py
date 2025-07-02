#!/usr/bin/env python3
import requests
import time

def test_index_api():
    """测试索引API和搜索功能"""
    
    print('=== 测试索引状态API ===')
    try:
        response = requests.get('http://localhost:8000/api/v1/index/status')
        print('状态码:', response.status_code)
        if response.status_code == 200:
            data = response.json()
            print('响应成功:', data['success'])
            status_data = data['data']
            print(f'SQLite文件数: {status_data["sqlite_files"]}')
            print(f'FTS文件数: {status_data["fts_files"]}')
            print(f'磁盘文件数: {status_data["disk_files"]}')
            print(f'需要重建: {status_data["needs_rebuild"]}')
        else:
            print('响应错误:', response.text)
    except Exception as e:
        print('请求失败:', e)

    print()
    print('=== 测试搜索功能 ===')
    try:
        response = requests.get('http://localhost:8000/api/v1/files/search?q=本地&search_type=keyword')
        print('搜索状态码:', response.status_code)
        if response.status_code == 200:
            result = response.json()
            print(f'搜索结果数: {len(result.get("results", []))}')
            for item in result.get('results', [])[:2]:
                print(f'  - {item.get("title")} ({item.get("file_path")})')
        else:
            print('搜索错误:', response.text)
    except Exception as e:
        print('搜索请求失败:', e)

    print()
    print('=== 测试混合搜索 ===')
    try:
        response = requests.get('http://localhost:8000/api/v1/files/search?q=AI&search_type=mixed')
        print('混合搜索状态码:', response.status_code)
        if response.status_code == 200:
            result = response.json()
            print(f'混合搜索结果数: {len(result.get("results", []))}')
            for item in result.get('results', [])[:2]:
                print(f'  - {item.get("title")} ({item.get("file_path")})')
        else:
            print('混合搜索错误:', response.text)
    except Exception as e:
        print('混合搜索请求失败:', e)

if __name__ == '__main__':
    test_index_api() 