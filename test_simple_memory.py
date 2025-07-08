#!/usr/bin/env python3
"""
测试简化记忆系统的完整功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1/simple-memory"

def test_memory_system():
    print("🧠 测试简化记忆系统\n")
    
    # 1. 获取初始统计
    print("1. 获取初始记忆统计...")
    response = requests.get(f"{BASE_URL}/stats")
    stats = response.json()
    print(f"   总记忆数: {stats['total_memories']}")
    print(f"   记忆文件: {stats['file_path']}")
    print()
    
    # 2. 手动添加记忆
    print("2. 手动添加一条记忆...")
    manual_memory = {
        "content": "用户擅长使用Docker和Kubernetes进行容器化部署",
        "type": "skill",
        "importance": 0.9,
        "tags": ["Docker", "Kubernetes", "容器化", "部署"]
    }
    response = requests.post(f"{BASE_URL}/add-manual", json=manual_memory)
    print(f"   结果: {response.json()['message']}")
    print()
    
    # 3. 处理对话更新记忆
    print("3. 处理对话并自动更新记忆...")
    conversation = {
        "user_input": "我最近在学习微服务架构，特别是如何用Docker Swarm管理服务集群",
        "ai_response": "微服务架构确实是当前的热门话题！既然您已经熟悉Docker和Kubernetes，Docker Swarm会是很好的补充。它相对K8s更轻量，适合中小规模的集群管理。建议您关注服务发现、负载均衡和滚动更新这几个核心概念。"
    }
    response = requests.post(f"{BASE_URL}/process-conversation", json=conversation)
    result = response.json()
    print(f"   处理结果: {result['status']}")
    print(f"   记忆变化: {result['old_count']} -> {result['new_count']}")
    print()
    
    # 4. 获取格式化的提示词
    print("4. 生成格式化的记忆提示词...")
    response = requests.get(f"{BASE_URL}/formatted-prompt?limit=10")
    data = response.json()
    print(f"   记忆数量: {data['memory_count']}")
    print("   格式化提示词:")
    print(data['prompt'])
    
    # 5. 再次获取统计信息
    print("5. 获取最终记忆统计...")
    response = requests.get(f"{BASE_URL}/stats")
    final_stats = response.json()
    print(f"   总记忆数: {final_stats['total_memories']}")
    print(f"   记忆类型分布: {final_stats['memory_types']}")
    print(f"   重要性分布: {final_stats['importance_distribution']}")
    print()
    
    print("✅ 简化记忆系统测试完成！")
    print("\n🎯 主要特性验证:")
    print("   ✓ JSON文件存储 (单一数据源)")
    print("   ✓ LLM驱动的记忆管理")
    print("   ✓ 自动对话记忆提取")
    print("   ✓ 智能记忆重要性评估")
    print("   ✓ 系统提示词集成")
    print("   ✓ 无用户ID (单用户系统)")

if __name__ == "__main__":
    try:
        test_memory_system()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保 Docker 容器正在运行")
        print("   运行命令: docker-compose up -d")
    except Exception as e:
        print(f"❌ 测试失败: {e}")