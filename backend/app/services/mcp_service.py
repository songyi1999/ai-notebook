"""
MCP (Model Context Protocol) 服务
负责管理MCP Server连接、工具发现和调用
"""
import asyncio
import json
import time
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
            
            # 这里是工具发现的示例实现
            # 实际实现需要根据MCP协议规范
            tools = []
            
            # 为不同类型的服务器创建测试工具
            if server.server_type == "http":
                test_tool = MCPTool(
                    server_id=server.id,
                    tool_name=f"test_tool_{server.id}",
                    tool_description=f"测试工具来自 {server.name}",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "测试消息"}
                        },
                        "required": ["message"]
                    },
                    is_available=True
                )
                tools.append(test_tool)
                
            elif server.server_type == "sse":
                # 为SSE类型服务器创建完整的高德地图工具列表
                # 基于实际的高德地图MCP服务器，包含所有12个工具
                map_tools = [
                    {
                        "name": "maps_regeocode",
                        "description": "将经纬度坐标转换为行政区划地址信息",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "经纬度坐标，格式：经度,纬度"}
                            },
                            "required": ["location"]
                        }
                    },
                    {
                        "name": "maps_geo",
                        "description": "将详细的结构化地址转换为经纬度坐标",
                        "schema": {
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
                        "description": "IP定位，根据用户输入的IP地址，定位IP的所在位置",
                        "schema": {
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
                        "schema": {
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
                        "schema": {
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
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "出发点经纬度，坐标格式为：经度,纬度"},
                                "destination": {"type": "string", "description": "目的地经纬度，坐标格式为：经度,纬度"}
                            },
                            "required": ["origin", "destination"]
                        }
                    },
                    {
                        "name": "maps_direction_walking",
                        "description": "步行路径规划 API 可以根据输入起点终点经纬度坐标规划100km 以内的步行通勤方案，并且返回通勤方案的数据",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度,纬度"},
                                "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度,纬度"}
                            },
                            "required": ["origin", "destination"]
                        }
                    },
                    {
                        "name": "maps_direction_driving",
                        "description": "驾车路径规划 API 可以根据用户起终点经纬度坐标规划以小客车、轿车通勤出行的方案，并且返回通勤方案的数据",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度,纬度"},
                                "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度,纬度"}
                            },
                            "required": ["origin", "destination"]
                        }
                    },
                    {
                        "name": "maps_direction_transit_integrated",
                        "description": "公交路径规划 API 可以根据用户起终点经纬度坐标规划综合各类公共（火车、公交、地铁）交通方式的通勤方案，并且返回通勤方案的数据，跨城场景下必须传起点城市与终点城市",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "出发点经度，纬度，坐标格式为：经度,纬度"},
                                "destination": {"type": "string", "description": "目的地经度，纬度，坐标格式为：经度,纬度"},
                                "city": {"type": "string", "description": "公共交通规划起点城市"},
                                "cityd": {"type": "string", "description": "公共交通规划终点城市"}
                            },
                            "required": ["origin", "destination", "city", "cityd"]
                        }
                    },
                    {
                        "name": "maps_distance",
                        "description": "距离测量 API 可以测量两个经纬度坐标之间的距离,支持驾车、步行以及球面距离测量",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origins": {"type": "string", "description": "起点经度，纬度，可以传多个坐标，使用竖线隔离，比如120,30|120,31，坐标格式为：经度,纬度"},
                                "destination": {"type": "string", "description": "终点经度，纬度，坐标格式为：经度,纬度"},
                                "type": {"type": "string", "description": "距离测量类型,1代表驾车距离测量，0代表直线距离测量，3步行距离测量"}
                            },
                            "required": ["origins", "destination"]
                        }
                    },
                    {
                        "name": "maps_text_search",
                        "description": "关键词搜，根据用户传入关键词，搜索出相关的POI",
                        "schema": {
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
                        "schema": {
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
                
                for tool_info in map_tools:
                    test_tool = MCPTool(
                        server_id=server.id,
                        tool_name=tool_info["name"],
                        tool_description=tool_info["description"],
                        input_schema=tool_info["schema"],
                        is_available=True
                    )
                    tools.append(test_tool)
                    
            elif server.server_type == "stdio":
                test_tool = MCPTool(
                    server_id=server.id,
                    tool_name=f"stdio_tool_{server.id}",
                    tool_description=f"Stdio工具来自 {server.name}",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"}
                        },
                        "required": ["command"]
                    },
                    is_available=True
                )
                tools.append(test_tool)
            
            # 保存工具到数据库
            saved_tools = []
            for tool in tools:
                # 检查工具是否已存在
                existing_tool = self.db.query(MCPTool).filter(
                    and_(
                        MCPTool.server_id == server.id,
                        MCPTool.tool_name == tool.tool_name
                    )
                ).first()
                
                if not existing_tool:
                    self.db.add(tool)
                    self.db.commit()
                    saved_tools.append(tool)
                else:
                    saved_tools.append(existing_tool)
            
            logger.info(f"发现 {len(saved_tools)} 个工具来自 {server.name}")
            return saved_tools
            
        except Exception as e:
            logger.error(f"发现MCP工具失败: {e}")
            raise
    
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