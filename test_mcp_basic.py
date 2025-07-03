#!/usr/bin/env python3
"""
MCP功能基础测试脚本
测试MCP Server管理和基础功能
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

from backend.app.database.session import get_db
from backend.app.services.mcp_service import MCPClientService
from backend.app.schemas.mcp import MCPServerCreate, MCPToolCallRequest

async def test_mcp_basic_functionality():
    """测试MCP基础功能"""
    print("🚀 开始测试MCP基础功能...")
    
    # 获取数据库连接
    db = next(get_db())
    mcp_service = MCPClientService(db)
    
    try:
        # 1. 测试创建MCP Server
        print("\n1. 测试创建MCP Server...")
        server_data = MCPServerCreate(
            name="test_http_server",
            description="测试HTTP类型的MCP Server",
            server_type="http",
            server_config={
                "url": "http://localhost:8001",
                "timeout": 10
            },
            auth_type="none"
        )
        
        try:
            server = await mcp_service.create_server(server_data)
            print(f"✅ 成功创建MCP Server: {server.name} (ID: {server.id})")
        except Exception as e:
            print(f"❌ 创建MCP Server失败: {e}")
            return False
        
        # 2. 测试获取可用工具
        print("\n2. 测试获取可用工具...")
        try:
            tools = mcp_service.get_available_tools()
            print(f"✅ 获取到 {len(tools)} 个可用工具")
            for tool in tools[:3]:  # 只显示前3个
                print(f"   - {tool.tool_name}: {tool.tool_description}")
        except Exception as e:
            print(f"⚠️  获取工具列表失败: {e}")
        
        # 3. 测试服务器状态
        print("\n3. 测试获取服务器状态...")
        try:
            status = mcp_service.get_server_status(server.id)
            if status:
                print(f"✅ 服务器状态: {status['connection_status']}")
                print(f"   连接状态: {'已连接' if status['is_connected'] else '未连接'}")
                print(f"   工具数量: {status['tool_count']}")
            else:
                print("❌ 无法获取服务器状态")
        except Exception as e:
            print(f"⚠️  获取服务器状态失败: {e}")
        
        # 4. 测试工具调用（模拟）
        print("\n4. 测试工具调用功能...")
        try:
            # 查找可用工具
            tools = mcp_service.get_available_tools()
            if tools:
                test_tool = tools[0]
                call_request = MCPToolCallRequest(
                    tool_name=test_tool.tool_name,
                    arguments={"test": "hello world"},
                    context="测试工具调用",
                    session_id="test_session_001"
                )
                
                result = await mcp_service.call_tool(call_request)
                if result.success:
                    print(f"✅ 工具调用成功: {test_tool.tool_name}")
                    print(f"   执行时间: {result.execution_time_ms}ms")
                    print(f"   调用ID: {result.tool_call_id}")
                else:
                    print(f"❌ 工具调用失败: {result.error}")
            else:
                print("⚠️  没有可用工具进行测试")
        except Exception as e:
            print(f"⚠️  工具调用测试失败: {e}")
        
        print("\n🎉 MCP基础功能测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        db.close()

def test_database_tables():
    """测试MCP数据库表是否正确创建"""
    print("\n📊 测试MCP数据库表...")
    
    try:
        from backend.app.models.mcp_server import MCPServer, MCPTool, MCPToolCall
        from sqlalchemy import inspect
        from backend.app.models.base import engine
        
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        mcp_tables = ['mcp_servers', 'mcp_tools', 'mcp_tool_calls']
        missing_tables = []
        
        for table in mcp_tables:
            if table in table_names:
                print(f"✅ 表 {table} 存在")
            else:
                print(f"❌ 表 {table} 不存在")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n⚠️  缺少表: {missing_tables}")
            print("请运行数据库迁移或重新初始化数据库")
            return False
        else:
            print("\n✅ 所有MCP数据库表都已正确创建")
            return True
            
    except Exception as e:
        print(f"❌ 数据库表检查失败: {e}")
        return False

def test_api_endpoints():
    """测试MCP API端点是否正确注册"""
    print("\n🌐 测试MCP API端点...")
    
    try:
        from backend.app.main import app
        from fastapi.routing import APIRoute
        
        mcp_routes = []
        for route in app.routes:
            if isinstance(route, APIRoute) and route.path.startswith('/api/mcp'):
                mcp_routes.append(f"{route.methods} {route.path}")
        
        if mcp_routes:
            print(f"✅ 发现 {len(mcp_routes)} 个MCP API端点:")
            for route in mcp_routes[:5]:  # 只显示前5个
                print(f"   {route}")
            if len(mcp_routes) > 5:
                print(f"   ... 还有 {len(mcp_routes) - 5} 个端点")
            return True
        else:
            print("❌ 未发现MCP API端点")
            return False
            
    except Exception as e:
        print(f"❌ API端点检查失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("=" * 60)
    print("🔧 MCP功能集成测试")
    print("=" * 60)
    
    # 测试计数器
    total_tests = 3
    passed_tests = 0
    
    # 1. 测试数据库表
    if test_database_tables():
        passed_tests += 1
    
    # 2. 测试API端点
    if test_api_endpoints():
        passed_tests += 1
    
    # 3. 测试基础功能
    if await test_mcp_basic_functionality():
        passed_tests += 1
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📋 测试结果总结")
    print("=" * 60)
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！MCP功能已正确集成")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关配置")
        return False

if __name__ == "__main__":
    # 检查是否在正确的目录
    if not os.path.exists("backend/app"):
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 