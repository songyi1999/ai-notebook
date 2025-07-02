#!/usr/bin/env python3
import requests
import time

def test_services():
    """测试前后端服务和搜索功能"""
    
    # 等待服务完全启动
    time.sleep(5)

    print('=== 测试后端健康检查 ===')
    try:
        response = requests.get('http://localhost:8000/health')
        print('后端健康检查:', response.json())
    except Exception as e:
        print('后端健康检查失败:', e)

    print()
    print('=== 测试索引状态API ===')
    try:
        response = requests.get('http://localhost:8000/api/v1/index/status')
        print('索引状态码:', response.status_code)
        if response.status_code == 200:
            data = response.json()
            print('索引状态:', data)
        else:
            print('索引状态错误:', response.text)
    except Exception as e:
        print('索引状态请求失败:', e)

    print()
    print('=== 测试搜索功能 ===')
    try:
        response = requests.get('http://localhost:8000/api/v1/files/search?q=本地&search_type=keyword')
        print('搜索状态码:', response.status_code)
        if response.status_code == 200:
            result = response.json()
            results_count = len(result.get('results', []))
            print(f'搜索"本地"结果数: {results_count}')
            for item in result.get('results', [])[:2]:
                title = item.get('title', '')
                file_path = item.get('file_path', '')
                print(f'  - {title} ({file_path})')
        else:
            print('搜索错误:', response.text)
    except Exception as e:
        print('搜索请求失败:', e)

    print()
    print('=== 测试前端页面 ===')
    try:
        response = requests.get('http://localhost:3000')
        print('前端页面状态码:', response.status_code)
        if response.status_code == 200:
            print('前端页面正常运行')
        else:
            print('前端页面错误')
    except Exception as e:
        print('前端页面请求失败:', e)

if __name__ == '__main__':
    test_services() 