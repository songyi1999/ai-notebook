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
                tool_schema = json.loads(tool.tool_schema) if isinstance(tool.tool_schema, str) else tool.tool_schema
                
                # 转换为OpenAI Function Calling格式
                function_def = {
                    "type": "function",
                    "function": {
                        "name": tool.tool_name,
                        "description": tool.description or f"Tool from {tool.server.name}",
                        "parameters": tool_schema.get("inputSchema", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                }
                
                formatted_tools.append(function_def)
                
            except Exception as e:
                logger.error(f"格式化工具 {tool.tool_name} 失败: {e}")
                continue
        
        logger.info(f"为LLM准备了 {len(formatted_tools)} 个工具")
        return formatted_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: str = None) -> MCPToolCallResult:
        """调用MCP工具"""
        try:
            start_time = time.time()
            
            # 查找工具
            tool = self.db.query(MCPTool).filter(
                and_(
                    MCPTool.tool_name == tool_name,
                    MCPTool.is_available == True
                )
            ).first()
            
            if not tool:
                raise ValueError(f"工具 '{tool_name}' 不存在或不可用")
            
            if not tool.server.is_enabled or not tool.server.is_connected:
                raise ValueError(f"工具 '{tool_name}' 的服务器未连接")
            
            # 执行工具调用
            result = await self._execute_tool_call(tool, arguments)
            
            # 记录调用历史
            execution_time = time.time() - start_time
            tool_call = MCPToolCall(
                tool_id=tool.id,
                session_id=session_id,
                input_data=arguments,
                output_data=result,
                execution_time=execution_time,
                status="success",
                error_message=None
            )
            
            self.db.add(tool_call)
            self.db.commit()
            
            logger.info(f"工具调用成功: {tool_name}, 耗时: {execution_time:.3f}秒")
            
            return MCPToolCallResult(
                success=True,
                result=result,
                execution_time=execution_time,
                tool_name=tool_name
            )
            
        except Exception as e:
            # 记录失败的调用
            try:
                execution_time = time.time() - start_time
                tool_call = MCPToolCall(
                    tool_id=tool.id if 'tool' in locals() else None,
                    session_id=session_id,
                    input_data=arguments,
                    output_data=None,
                    execution_time=execution_time,
                    status="error",
                    error_message=str(e)
                )
                
                self.db.add(tool_call)
                self.db.commit()
            except:
                pass  # 忽略记录失败的错误
            
            logger.error(f"工具调用失败: {tool_name}, 错误: {e}")
            
            return MCPToolCallResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time if 'start_time' in locals() else 0,
                tool_name=tool_name
            )
    
    async def _execute_tool_call(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """执行具体的工具调用"""
        try:
            # 根据服务器类型执行调用
            if tool.server.server_type == "http":
                return await self._call_http_tool(tool, arguments)
            elif tool.server.server_type == "stdio":
                return await self._call_stdio_tool(tool, arguments)
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

    # 私有方法
    async def _connect_server(self, server: MCPServer) -> bool:
        """内部方法：连接到MCP Server"""
        try:
            # 根据server_type选择连接方式
            if server.server_type == "http":
                success = await self._connect_http_server(server)
            elif server.server_type == "stdio":
                success = await self._connect_stdio_server(server)
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