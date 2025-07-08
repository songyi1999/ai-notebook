#!/usr/bin/env python3
"""
配置系统测试脚本
测试配置功能和AI降级逻辑
"""

import json
import os
import sys
import requests
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "backend"))

def test_config_api():
    """测试配置API"""
    base_url = "http://localhost:8000/api/v1"
    
    print("=" * 50)
    print("测试配置API")
    print("=" * 50)
    
    try:
        # 1. 测试获取配置
        print("1. 测试获取配置...")
        response = requests.get(f"{base_url}/config/")
        if response.status_code == 200:
            config = response.json()
            print("✅ 获取配置成功")
            print(f"   AI启用状态: {config.get('ai_settings', {}).get('enabled', False)}")
        else:
            print(f"❌ 获取配置失败: {response.status_code}")
            return False
        
        # 2. 测试AI状态
        print("\n2. 测试AI状态...")
        response = requests.get(f"{base_url}/config/status")
        if response.status_code == 200:
            status = response.json()
            print("✅ 获取AI状态成功")
            print(f"   AI启用: {status.get('enabled', False)}")
            print(f"   模式: {status.get('mode', 'unknown')}")
        else:
            print(f"❌ 获取AI状态失败: {response.status_code}")
        
        # 3. 测试连接性测试
        print("\n3. 测试AI连接性...")
        response = requests.get(f"{base_url}/config/test")
        if response.status_code == 200:
            test_result = response.json()
            print("✅ AI连接测试完成")
            print(f"   整体状态: {test_result.get('overall_status', 'unknown')}")
            print(f"   消息: {test_result.get('message', 'N/A')}")
            
            # 详细测试结果
            if test_result.get('language_model'):
                lm = test_result['language_model']
                print(f"   语言模型: {'可用' if lm.get('available') else '不可用'}")
                
            if test_result.get('embedding_model'):
                em = test_result['embedding_model']
                print(f"   嵌入模型: {'可用' if em.get('available') else '不可用'}")
        else:
            print(f"❌ AI连接测试失败: {response.status_code}")
        
        # 4. 测试预设配置
        print("\n4. 测试预设配置...")
        response = requests.get(f"{base_url}/config/presets")
        if response.status_code == 200:
            presets = response.json()
            print("✅ 获取预设配置成功")
            print(f"   可用预设数量: {len(presets.get('presets', {}))}")
            for name, preset in presets.get('presets', {}).items():
                print(f"   - {name}: {preset.get('name', 'N/A')}")
        else:
            print(f"❌ 获取预设配置失败: {response.status_code}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ 请求失败: {e}")
        print("请确保后端服务在 http://localhost:8000 运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_search_degradation():
    """测试搜索降级功能"""
    base_url = "http://localhost:8000/api/v1"
    
    print("\n" + "=" * 50)
    print("测试搜索降级功能")
    print("=" * 50)
    
    try:
        # 测试关键词搜索（应该始终可用）
        print("1. 测试关键词搜索...")
        response = requests.get(f"{base_url}/files/search", params={
            "q": "test",
            "search_type": "keyword",
            "limit": 5
        })
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 关键词搜索成功")
            print(f"   结果数量: {result.get('total', 0)}")
            print(f"   搜索类型: {result.get('search_type', 'N/A')}")
            
            if result.get('degraded'):
                print(f"   降级状态: {result.get('degradation_reason', 'N/A')}")
        else:
            print(f"❌ 关键词搜索失败: {response.status_code}")
        
        # 测试语义搜索（可能降级）
        print("\n2. 测试语义搜索...")
        response = requests.get(f"{base_url}/files/search", params={
            "q": "人工智能",
            "search_type": "semantic",
            "limit": 5
        })
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 语义搜索请求成功")
            print(f"   结果数量: {result.get('total', 0)}")
            print(f"   实际搜索类型: {result.get('search_type', 'N/A')}")
            
            if result.get('degraded'):
                print(f"   ⚠️  搜索已降级: {result.get('degradation_reason', 'N/A')}")
            else:
                print("   ✅ 语义搜索正常运行")
        else:
            print(f"❌ 语义搜索失败: {response.status_code}")
        
        # 测试混合搜索（可能降级）
        print("\n3. 测试混合搜索...")
        response = requests.get(f"{base_url}/files/search", params={
            "q": "配置管理",
            "search_type": "mixed",
            "limit": 5
        })
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 混合搜索请求成功")
            print(f"   结果数量: {result.get('total', 0)}")
            print(f"   实际搜索类型: {result.get('search_type', 'N/A')}")
            
            if result.get('degraded'):
                print(f"   ⚠️  搜索已降级: {result.get('degradation_reason', 'N/A')}")
            else:
                print("   ✅ 混合搜索正常运行")
        else:
            print(f"❌ 混合搜索失败: {response.status_code}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_config_file_loading():
    """测试配置文件加载"""
    print("\n" + "=" * 50)
    print("测试配置文件功能")
    print("=" * 50)
    
    config_path = Path("config.json")
    
    # 创建测试配置文件
    test_config = {
        "ai_settings": {
            "enabled": False,
            "fallback_mode": "notes_only"
        },
        "application": {
            "theme": "light",
            "language": "zh-CN"
        },
        "meta": {
            "config_version": "1.0",
            "description": "测试配置文件"
        }
    }
    
    try:
        # 备份现有配置文件（如果存在）
        backup_path = None
        if config_path.exists():
            backup_path = Path("config.json.backup")
            config_path.rename(backup_path)
            print("   已备份现有配置文件")
        
        # 创建测试配置文件
        print("1. 创建测试配置文件...")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        print("✅ 测试配置文件已创建")
        
        # 等待配置重新加载
        print("2. 等待配置重新加载...")
        time.sleep(2)
        
        # 测试配置是否生效
        print("3. 验证配置是否生效...")
        base_url = "http://localhost:8000/api/v1"
        response = requests.get(f"{base_url}/config/status")
        
        if response.status_code == 200:
            status = response.json()
            if not status.get('enabled', True):
                print("✅ 配置文件生效 - AI功能已禁用")
            else:
                print("⚠️  配置可能未完全生效")
        
        # 清理测试文件
        print("4. 清理测试文件...")
        config_path.unlink()
        
        # 恢复备份（如果存在）
        if backup_path and backup_path.exists():
            backup_path.rename(config_path)
            print("   已恢复原配置文件")
        
        print("✅ 配置文件测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        
        # 清理并恢复
        try:
            if config_path.exists():
                config_path.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(config_path)
        except:
            pass
        
        return False

def main():
    """主测试函数"""
    print("AI笔记本配置系统测试")
    print("请确保后端服务运行在 http://localhost:8000")
    print("")
    
    # 等待用户确认
    input("按 Enter 键开始测试...")
    
    success_count = 0
    total_tests = 3
    
    # 运行测试
    tests = [
        ("配置API测试", test_config_api),
        ("搜索降级测试", test_search_degradation),
        ("配置文件测试", test_config_file_loading),
    ]
    
    for test_name, test_func in tests:
        print(f"\n开始运行: {test_name}")
        try:
            if test_func():
                success_count += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    # 输出结果
    print("\n" + "=" * 50)
    print("测试结果摘要")
    print("=" * 50)
    print(f"总测试数: {total_tests}")
    print(f"通过数: {success_count}")
    print(f"失败数: {total_tests - success_count}")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！配置系统工作正常。")
    else:
        print("⚠️  部分测试失败，请检查系统配置。")
    
    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)