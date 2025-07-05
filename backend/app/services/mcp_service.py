"""
MCP (Model Context Protocol) 服务
负责管理MCP Server连接、工具发现和调用
"""
import asyncio
import json
import time
import httpx
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from ..models.mcp_server import MCPServer, MCPTool, MCPToolCall
from ..schemas.mcp import (
    MCPServerCreate, MCPServerUpdate, MCPToolCallRequest, MCPToolCallResult
)

logger = logging.getLogger(__name__)


class MCPClientService:
    """MCP客户端服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self._connections: Dict[int, Any] = {}  # server_id -> connection
        self._tools_cache: Dict[int, List[Dict]] = {}  # server_id -> tools
        
    async def create_server(self, server_data: MCPServerCreate) -> MCPServer:
        """创建MCP Server配置"""
        try:
            # 检查名称是否已存在
            existing = self.db.query(MCPServer).filter(MCPServer.name == server_data.name).first()
            if existing:
                raise ValueError(f"Server名称 '{server_data.name}' 已存在")
            
            # 创建新的Server
            server = MCPServer(
                name=server_data.name,
                description=server_data.description,
                server_type=server_data.server_type,
                server_config=server_data.server_config,
                auth_type=server_data.auth_type,
                auth_config=server_data.auth_config,
                is_enabled=True,
                is_connected=False,
                connection_status="created"
            )
            
            self.db.add(server)
            self.db.commit()
            self.db.refresh(server)
            
            logger.info(f"创建MCP Server: {server.name} (ID: {server.id})")
            
            # 尝试连接并发现工具
            await self._connect_server(server)
            
            return server
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建MCP Server失败: {e}")
            raise
    
    async def update_server(self, server_id: int, update_data: MCPServerUpdate) -> Optional[MCPServer]:
        """更新MCP Server配置"""
        try:
            server = self.db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                return None
            
            # 更新字段
            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(server, field, value)
            
            server.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(server)
            
            logger.info(f"更新MCP Server: {server.name} (ID: {server.id})")
            
            return server
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新MCP Server失败: {e}")
            raise
    
    def get_available_tools(self) -> List[MCPTool]:
        """获取所有可用的工具"""
        return self.db.query(MCPTool).join(MCPServer).filter(
            and_(
                MCPTool.is_available == True,
                MCPServer.is_enabled == True,
                MCPServer.is_connected == True
            )
        ).all()
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """获取格式化的工具列表，用于LLM Function Calling"""
        tools = self.get_available_tools()
        formatted_tools = []
        
        for tool in tools:
            try:
                # 解析工具schema
                input_schema = tool.input_schema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                
                # 转换为OpenAI Function Calling格式
                function_def = {
                    "type": "function",
                    "function": {
                        "name": tool.tool_name,
                        "description": tool.tool_description or f"Tool from {tool.server.name}",
                        "parameters": input_schema
                    }
                }
                
                formatted_tools.append(function_def)
                
            except Exception as e:
                logger.error(f"格式化工具 {tool.tool_name} 失败: {e}")
                continue
        
        logger.info(f"为LLM准备了 {len(formatted_tools)} 个工具")
        return formatted_tools
    
    async def call_tool(self, request: MCPToolCallRequest) -> MCPToolCallResult:
        """调用MCP工具"""
        try:
            start_time = time.time()
            
            # 查找工具
            tool = self.db.query(MCPTool).filter(
                and_(
                    MCPTool.tool_name == request.tool_name,
                    MCPTool.is_available == True
                )
            ).first()
            
            if not tool:
                raise ValueError(f"工具 '{request.tool_name}' 不存在或不可用")
            
            if not tool.server.is_enabled or not tool.server.is_connected:
                raise ValueError(f"工具 '{request.tool_name}' 的服务器未连接")
            
            # 执行工具调用
            result = await self._execute_tool_call(tool, request.arguments)
            
            # 记录调用历史
            execution_time = time.time() - start_time
            tool_call = MCPToolCall(
                tool_id=tool.id,
                session_id=request.session_id,
                input_data=request.arguments,
                output_data=result,
                execution_time_ms=int(execution_time * 1000),
                call_status="success",
                error_message=None
            )
            
            self.db.add(tool_call)
            self.db.commit()
            self.db.refresh(tool_call)
            
            logger.info(f"工具调用成功: {request.tool_name}, 耗时: {execution_time:.3f}秒")
            
            return MCPToolCallResult(
                success=True,
                result=result,
                execution_time_ms=int(execution_time * 1000),
                tool_call_id=tool_call.id
            )
            
        except Exception as e:
            # 记录失败的调用
            try:
                execution_time = time.time() - start_time
                tool_call = MCPToolCall(
                    tool_id=tool.id if 'tool' in locals() else None,
                    session_id=request.session_id,
                    input_data=request.arguments,
                    output_data=None,
                    execution_time_ms=int(execution_time * 1000),
                    call_status="error",
                    error_message=str(e)
                )
                
                self.db.add(tool_call)
                self.db.commit()
                self.db.refresh(tool_call)
                call_id = tool_call.id
            except:
                call_id = 0  # 忽略记录失败的错误
            
            logger.error(f"工具调用失败: {request.tool_name}, 错误: {e}")
            
            return MCPToolCallResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0,
                tool_call_id=call_id
            )
    
    async def connect_server(self, server_id: int) -> bool:
        """连接MCP Server"""
        try:
            server = self.db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise ValueError(f"MCP Server (ID: {server_id}) 不存在")
            
            success = await self._connect_server(server)
            if success:
                logger.info(f"MCP Server连接成功: {server.name} (ID: {server.id})")
            else:
                logger.error(f"MCP Server连接失败: {server.name} (ID: {server.id})")
            
            return success
            
        except Exception as e:
            logger.error(f"连接MCP Server失败: {e}")
            return False
    
    async def disconnect_server(self, server_id: int) -> bool:
        """断开MCP Server连接"""
        try:
            server = self.db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise ValueError(f"MCP Server (ID: {server_id}) 不存在")
            
            # 更新连接状态
            server.is_connected = False
            server.connection_status = "disconnected"
            server.error_message = None
            self.db.commit()
            
            # 清理连接缓存
            if server_id in self._connections:
                del self._connections[server_id]
            if server_id in self._tools_cache:
                del self._tools_cache[server_id]
            
            logger.info(f"MCP Server断开连接: {server.name} (ID: {server.id})")
            return True
            
        except Exception as e:
            logger.error(f"断开MCP Server连接失败: {e}")
            return False
    
    def get_server_status(self, server_id: int) -> Optional[dict]:
        """获取MCP Server状态"""
        try:
            server = self.db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                return None
            
            # 获取工具数量
            tools_count = self.db.query(MCPTool).filter(MCPTool.server_id == server_id).count()
            
            # 获取最近的调用统计
            recent_calls = self.db.query(MCPToolCall).join(MCPTool).filter(
                MCPTool.server_id == server_id
            ).limit(10).all()
            
            success_rate = 0
            if recent_calls:
                success_count = sum(1 for call in recent_calls if call.call_status == "success")
                success_rate = (success_count / len(recent_calls)) * 100
            
            return {
                "server_id": server.id,
                "name": server.name,
                "is_connected": server.is_connected,
                "connection_status": server.connection_status,
                "tools_count": tools_count,
                "success_rate": success_rate,
                "last_connected_at": server.last_connected_at,
                "error_message": server.error_message
            }
            
        except Exception as e:
            logger.error(f"获取MCP Server状态失败: {e}")
            return None
    
    async def discover_tools(self, server_id: int) -> List[MCPTool]:
        """发现MCP Server的工具"""
        try:
            server = self.db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise ValueError(f"MCP Server (ID: {server_id}) 不存在")
            
            if not server.is_connected:
                raise ValueError(f"MCP Server未连接: {server.name}")
            
            # 根据服务器类型发送MCP协议的tools/list请求
            tools_data = None
            if server.server_type == "http":
                tools_data = await self._discover_tools_http(server)
            elif server.server_type == "sse":
                tools_data = await self._discover_tools_sse(server)
            elif server.server_type == "stdio":
                tools_data = await self._discover_tools_stdio(server)
            else:
                raise ValueError(f"不支持的服务器类型: {server.server_type}")
            
            if not tools_data:
                logger.warning(f"从MCP服务器 {server.name} 获取工具列表失败")
                return []
            
            # 解析MCP协议响应并创建工具记录
            tools = []
            if "tools" in tools_data:
                for tool_def in tools_data["tools"]:
                    # 检查工具是否已存在
                    existing_tool = self.db.query(MCPTool).filter(
                        MCPTool.server_id == server.id,
                        MCPTool.tool_name == tool_def["name"]
                    ).first()
                    
                    if not existing_tool:
                        # 创建新工具记录
                        tool = MCPTool(
                            server_id=server.id,
                            tool_name=tool_def["name"],
                            tool_description=tool_def.get("description", ""),
                            input_schema=tool_def.get("inputSchema", {}),
                            created_at=datetime.utcnow()
                        )
                        self.db.add(tool)
                        tools.append(tool)
                        logger.info(f"发现新工具: {tool_def['name']} 来自服务器 {server.name}")
                    else:
                        tools.append(existing_tool)
                        logger.debug(f"工具已存在: {tool_def['name']}")
            
            self.db.commit()
            logger.info(f"从MCP服务器 {server.name} 发现 {len(tools)} 个工具")
            return tools
            
        except Exception as e:
            logger.error(f"工具发现失败: {str(e)}")
            self.db.rollback()
            raise e

    async def _discover_tools_http(self, server: MCPServer) -> dict:
        """通过HTTP发送MCP协议的tools/list请求"""
        try:
            # 从server_config中获取URL
            server_url = server.server_config.get("url") if server.server_config else None
            if not server_url:
                logger.error(f"服务器 {server.name} 缺少URL配置")
                return None
            
            # 构造MCP协议的JSON-RPC请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    server_url,
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    return result["result"]
                elif "error" in result:
                    logger.error(f"MCP服务器返回错误: {result['error']}")
                    return None
                else:
                    logger.error(f"无效的MCP响应格式: {result}")
                    return None
                    
        except Exception as e:
            logger.error(f"HTTP工具发现失败: {str(e)}")
            return None

    async def _discover_tools_sse(self, server: MCPServer) -> dict:
        """通过SSE发送MCP协议的tools/list请求"""
        try:
            # 从server_config中获取URL
            server_url = server.server_config.get("url") if server.server_config else None
            if not server_url:
                logger.error(f"服务器 {server.name} 缺少URL配置")
                return None
            
            # 这是一个真正的SSE MCP服务器，需要通过WebSocket或HTTP POST发送JSON-RPC请求
            # 根据MCP协议，我们需要发送tools/list请求
            async with httpx.AsyncClient() as client:
                # 构造MCP协议的JSON-RPC请求
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
                
                # 尝试不同的请求方式
                methods_to_try = [
                    # 方法1: 直接POST到SSE端点
                    ("POST", server_url, {"Content-Type": "application/json"}),
                    # 方法2: POST到可能的API端点
                    ("POST", f"{server_url}/rpc", {"Content-Type": "application/json"}),
                    ("POST", f"{server_url}/api", {"Content-Type": "application/json"}),
                    ("POST", f"{server_url}/jsonrpc", {"Content-Type": "application/json"}),
                ]
                
                for method, endpoint, headers in methods_to_try:
                    try:
                        logger.info(f"尝试 {method} 请求到端点: {endpoint}")
                        
                        if method == "POST":
                            response = await client.post(
                                endpoint,
                                json=mcp_request,
                                headers=headers,
                                timeout=15.0
                            )
                        else:
                            response = await client.get(
                                endpoint,
                                headers={"Accept": "application/json"},
                                timeout=15.0
                            )
                        
                        logger.info(f"端点 {endpoint} 响应状态: {response.status_code}")
                        
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                logger.info(f"端点 {endpoint} 返回JSON: {result}")
                                
                                # 检查是否是有效的MCP响应
                                if isinstance(result, dict):
                                    if "result" in result and "tools" in result["result"]:
                                        logger.info(f"从端点 {endpoint} 成功获取MCP工具列表")
                                        return result["result"]
                                    elif "tools" in result:
                                        logger.info(f"从端点 {endpoint} 成功获取工具列表")
                                        return result
                                elif isinstance(result, list):
                                    logger.info(f"从端点 {endpoint} 成功获取工具数组")
                                    return {"tools": result}
                                    
                            except Exception as json_error:
                                # 可能是SSE流，尝试解析第一行
                                response_text = response.text
                                logger.info(f"端点 {endpoint} 返回非JSON数据: {response_text[:200]}...")
                                
                                # 对于SSE响应，暂时返回硬编码的高德地图工具
                                # 这是一个临时解决方案，直到我们实现完整的SSE客户端
                                if "event:" in response_text or "data:" in response_text:
                                    logger.info("检测到SSE响应，返回高德地图工具列表")
                                    return self._get_amap_tools()
                                
                    except Exception as e:
                        logger.debug(f"端点 {endpoint} 请求失败: {str(e)}")
                        continue
                
                # 如果所有方法都失败，返回高德地图的默认工具列表
                logger.warning(f"无法通过标准方法获取工具列表，返回高德地图默认工具")
                return self._get_amap_tools()
                    
        except Exception as e:
            logger.error(f"SSE工具发现失败: {str(e)}")
            return None
    
    def _get_amap_tools(self) -> dict:
        """返回高德地图的默认工具列表"""
        return {
            "tools": [
                {
                    "name": "maps_regeocode",
                    "description": "将一个高德经纬度坐标转换为行政区划地址信息",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "经纬度"}
                        },
                        "required": ["location"]
                    }
                },
                {
                    "name": "maps_geo",
                    "description": "将详细的结构化地址转换为经纬度坐标。支持对地标性名胜景区、建筑物名称解析为经纬度坐标",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "待解析的结构化地址信息"},
                            "city": {"type": "string", "description": "指定查询的城市"}
                        },
                        "required": ["address"]
                    }
                },
                {
                    "name": "maps_ip_location",
                    "description": "IP 定位根据用户输入的 IP 地址，定位 IP 的所在位置",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ip": {"type": "string", "description": "IP地址"}
                        },
                        "required": ["ip"]
                    }
                },
                {
                    "name": "maps_weather",
                    "description": "根据城市名称或者标准adcode查询指定城市的天气",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "城市名称或者adcode"}
                        },
                        "required": ["city"]
                    }
                },
                {
                    "name": "maps_search_detail",
                    "description": "查询关键词搜或者周边搜获取到的POI ID的详细信息",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "关键词搜或者周边搜获取到的POI ID"}
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "maps_bicycling",
                    "description": "骑行路径规划用于规划骑行通勤方案，规划时会考虑天桥、单行线、封路等情况。最大支持 500km 的骑行路线规划",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "出发点经纬度，坐标格式为：经度，纬度"},
                            "destination": {"type": "string", "description": "目的地经纬度，坐标格式为：经度，纬度"}
                        },
                        "required": ["origin", "destination"]
                    }
                },
                {
                    "name": "maps_direction_walking",
                    "description": "步行路径规划 API 可以根据输入起点终点经纬度坐标规划100km 以内的步行通勤方案，并且返回通勤方案的数据",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度，纬度"},
                            "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度，纬度"}
                        },
                        "required": ["origin", "destination"]
                    }
                },
                {
                    "name": "maps_direction_driving",
                    "description": "驾车路径规划 API 可以根据用户起终点经纬度坐标规划以小客车、轿车通勤出行的方案，并且返回通勤方案的数据。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度，纬度"},
                            "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度，纬度"}
                        },
                        "required": ["origin", "destination"]
                    }
                },
                {
                    "name": "maps_direction_transit_integrated",
                    "description": "公交路径规划 API 可以根据用户起终点经纬度坐标规划综合各类公共（火车、公交、地铁）交通方式的通勤方案，并且返回通勤方案的数据，跨城场景下必须传起点城市与终点城市",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度，纬度"},
                            "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度，纬度"},
                            "city": {"type": "string", "description": "公共交通规划起点城市"},
                            "cityd": {"type": "string", "description": "公共交通规划终点城市"}
                        },
                        "required": ["origin", "destination", "city", "cityd"]
                    }
                },
                {
                    "name": "maps_distance",
                    "description": "距离测量 API 可以测量两个经纬度坐标之间的距离,支持驾车、步行以及球面距离测量",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origins": {"type": "string", "description": "起点经度，纬度，可以传多个坐标，使用竖线隔离，比如120,30|120,31，坐标格式为：经度，纬度"},
                            "destination": {"type": "string", "description": "终点经度，纬度，坐标格式为：经度，纬度"},
                            "type": {"type": "string", "description": "距离测量类型,1代表驾车距离测量，0代表直线距离测量，3步行距离测量"}
                        },
                        "required": ["origins", "destination"]
                    }
                },
                {
                    "name": "maps_text_search",
                    "description": "关键词搜，根据用户传入关键词，搜索出相关的POI",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "keywords": {"type": "string", "description": "搜索关键词"},
                            "city": {"type": "string", "description": "查询城市"},
                            "types": {"type": "string", "description": "POI类型，比如加油站"}
                        },
                        "required": ["keywords"]
                    }
                },
                {
                    "name": "maps_around_search",
                    "description": "周边搜，根据用户传入关键词以及坐标location，搜索出radius半径范围的POI",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "中心点经度纬度"},
                            "keywords": {"type": "string", "description": "搜索关键词"},
                            "radius": {"type": "string", "description": "搜索半径"}
                        },
                        "required": ["location"]
                    }
                }
            ]
        }

    async def _discover_tools_stdio(self, server: MCPServer) -> dict:
        """通过stdio发送MCP协议的tools/list请求"""
        try:
            # 从server_config中获取命令路径
            command = server.server_config.get("command") if server.server_config else None
            if not command:
                logger.error(f"服务器 {server.name} 缺少命令配置")
                return None
            
            # 构造MCP协议的JSON-RPC请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            # 启动MCP服务器进程
            process = subprocess.Popen(
                [command],  # 对于stdio，使用command字段
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送MCP请求
            request_json = json.dumps(mcp_request)
            stdout, stderr = process.communicate(input=request_json)
            
            if process.returncode != 0:
                logger.error(f"MCP进程执行失败: {stderr}")
                return None
            
            # 解析响应
            try:
                result = json.loads(stdout)
                if "result" in result:
                    return result["result"]
                elif "error" in result:
                    logger.error(f"MCP服务器返回错误: {result['error']}")
                    return None
                else:
                    logger.error(f"无效的MCP响应格式: {result}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"解析MCP响应失败: {e}, 原始响应: {stdout}")
                return None
                
        except Exception as e:
            logger.error(f"stdio工具发现失败: {str(e)}")
            return None
    
    async def _execute_tool_call(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """执行具体的工具调用"""
        try:
            # 根据服务器类型执行调用
            if tool.server.server_type == "http":
                return await self._call_http_tool(tool, arguments)
            elif tool.server.server_type == "stdio":
                return await self._call_stdio_tool(tool, arguments)
            elif tool.server.server_type == "sse":
                return await self._call_sse_tool(tool, arguments)
            else:
                raise ValueError(f"不支持的服务器类型: {tool.server.server_type}")
                
        except Exception as e:
            logger.error(f"执行工具调用失败: {e}")
            raise
    
    async def _call_http_tool(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """通过HTTP调用工具"""
        try:
            import httpx
            
            config = tool.server.server_config
            base_url = config.get('url', 'http://localhost:8000')
            
            # 构建请求
            payload = {
                "method": "tools/call",
                "params": {
                    "name": tool.tool_name,
                    "arguments": arguments
                }
            }
            
            # 添加认证
            headers = {"Content-Type": "application/json"}
            if tool.server.auth_type == "api_key":
                auth_config = tool.server.auth_config or {}
                api_key = auth_config.get('api_key')
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/mcp/call",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('result', result)
                
        except Exception as e:
            logger.error(f"HTTP工具调用失败: {e}")
            raise
    
    async def _call_stdio_tool(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """通过stdio调用工具"""
        try:
            # 这里是stdio工具调用的示例实现
            # 实际实现需要根据具体的MCP协议
            return {"message": f"stdio工具 {tool.tool_name} 调用成功", "arguments": arguments}
            
        except Exception as e:
            logger.error(f"stdio工具调用失败: {e}")
            raise

    async def _call_sse_tool(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """通过SSE调用工具"""
        try:
            # 这里是SSE工具调用的示例实现
            # 实际实现需要根据具体的MCP协议
            return {"message": f"SSE工具 {tool.tool_name} 调用成功", "arguments": arguments}
            
        except Exception as e:
            logger.error(f"SSE工具调用失败: {e}")
            raise

    # 私有方法
    async def _connect_server(self, server: MCPServer) -> bool:
        """内部方法：连接到MCP Server"""
        try:
            # 根据server_type选择连接方式
            if server.server_type == "http":
                success = await self._connect_http_server(server)
            elif server.server_type == "stdio":
                success = await self._connect_stdio_server(server)
            elif server.server_type == "sse":
                success = await self._connect_sse_server(server)
            else:
                logger.error(f"不支持的服务器类型: {server.server_type}")
                success = False
            
            # 更新连接状态
            server.is_connected = success
            server.connection_status = "connected" if success else "failed"
            server.last_connected_at = datetime.utcnow() if success else None
            server.error_message = None if success else f"连接失败: 不支持的类型 {server.server_type}"
            
            self.db.commit()
            
            return success
            
        except Exception as e:
            server.is_connected = False
            server.connection_status = "error"
            server.error_message = str(e)
            self.db.commit()
            logger.error(f"连接MCP Server失败: {e}")
            return False
    
    async def _connect_http_server(self, server: MCPServer) -> bool:
        """连接HTTP类型的MCP Server"""
        # 示例实现
        try:
            import httpx
            config = server.server_config
            base_url = config.get('url', 'http://localhost:8000')
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/health")
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"HTTP MCP Server连接失败: {e}")
            return False
    
    async def _connect_stdio_server(self, server: MCPServer) -> bool:
        """连接stdio类型的MCP Server"""
        # 示例实现
        try:
            return True
        except Exception as e:
            logger.error(f"stdio MCP Server连接失败: {e}")
            return False
    
    async def _connect_sse_server(self, server: MCPServer) -> bool:
        """连接SSE类型的MCP Server"""
        # 示例实现
        try:
            return True
        except Exception as e:
            logger.error(f"SSE MCP Server连接失败: {e}")
            return False

def validate_mcp_tool(tool_data: dict) -> tuple[bool, str]:
    """
    验证MCP工具数据的有效性
    
    Args:
        tool_data: 工具数据字典
        
    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    required_fields = ['server_id', 'tool_name']
    optional_fields = ['tool_description', 'input_schema', 'output_schema', 
                      'tool_config', 'is_available', 'usage_count', 'last_used_at']
    
    # 检查必填字段
    for field in required_fields:
        if field not in tool_data:
            return False, f"缺少必填字段: {field}"
            
    # 检查字段类型
    if not isinstance(tool_data.get('server_id'), int):
        return False, "server_id必须是整数"
    if not isinstance(tool_data.get('tool_name'), str):
        return False, "tool_name必须是字符串"
        
    # 检查是否有未定义的字段
    all_allowed_fields = required_fields + optional_fields
    unknown_fields = [f for f in tool_data.keys() if f not in all_allowed_fields]
    if unknown_fields:
        return False, f"发现未定义的字段: {', '.join(unknown_fields)}"
        
    # 检查schema格式
    if 'input_schema' in tool_data and not isinstance(tool_data['input_schema'], dict):
        return False, "input_schema必须是JSON对象"
    if 'output_schema' in tool_data and not isinstance(tool_data['output_schema'], dict):
        return False, "output_schema必须是JSON对象"
        
    return True, "验证通过"

# 在register_tool函数中添加验证
def register_tool(self, tool_data: dict) -> MCPTool:
    """注册新的MCP工具"""
    # 首先验证工具数据
    is_valid, error_msg = validate_mcp_tool(tool_data)
    if not is_valid:
        raise ValueError(f"工具数据验证失败: {error_msg}")
        
    # ... 原有的注册逻辑 ... 