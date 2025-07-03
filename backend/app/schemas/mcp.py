"""
MCP相关的数据传输对象(DTO)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class MCPServerBase(BaseModel):
    """MCP Server基础Schema"""
    name: str = Field(..., description="Server名称")
    description: Optional[str] = Field(None, description="Server描述")
    server_type: str = Field(..., description="Server类型：http, stdio, sse等")
    server_config: Dict[str, Any] = Field(..., description="Server配置")
    auth_type: Optional[str] = Field(None, description="认证类型")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")


class MCPServerCreate(MCPServerBase):
    """创建MCP Server的Schema"""
    pass


class MCPServerUpdate(BaseModel):
    """更新MCP Server的Schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    server_type: Optional[str] = None
    server_config: Optional[Dict[str, Any]] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class MCPServerResponse(MCPServerBase):
    """MCP Server响应Schema"""
    id: int
    is_enabled: bool
    is_connected: bool
    connection_status: Optional[str]
    last_connected_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPToolBase(BaseModel):
    """MCP Tool基础Schema"""
    tool_name: str = Field(..., description="工具名称")
    tool_description: Optional[str] = Field(None, description="工具描述")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数schema")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="输出结果schema")
    tool_config: Optional[Dict[str, Any]] = Field(None, description="工具配置")


class MCPToolCreate(MCPToolBase):
    """创建MCP Tool的Schema"""
    server_id: int = Field(..., description="关联的Server ID")


class MCPToolUpdate(BaseModel):
    """更新MCP Tool的Schema"""
    tool_description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    tool_config: Optional[Dict[str, Any]] = None
    is_available: Optional[bool] = None


class MCPToolResponse(MCPToolBase):
    """MCP Tool响应Schema"""
    id: int
    server_id: int
    is_available: bool
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPToolCallBase(BaseModel):
    """MCP Tool Call基础Schema"""
    call_context: Optional[str] = Field(None, description="调用上下文")
    input_data: Dict[str, Any] = Field(..., description="调用输入参数")


class MCPToolCallCreate(MCPToolCallBase):
    """创建MCP Tool Call的Schema"""
    tool_id: int = Field(..., description="工具ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    ai_reasoning: Optional[str] = Field(None, description="AI推理过程")


class MCPToolCallResponse(MCPToolCallBase):
    """MCP Tool Call响应Schema"""
    id: int
    tool_id: int
    session_id: Optional[str]
    output_data: Optional[Dict[str, Any]]
    call_status: str
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    ai_reasoning: Optional[str]
    user_feedback: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MCPServerWithTools(MCPServerResponse):
    """包含工具列表的MCP Server Schema"""
    tools: List[MCPToolResponse] = []


class MCPToolWithCalls(MCPToolResponse):
    """包含调用历史的MCP Tool Schema"""
    recent_calls: List[MCPToolCallResponse] = []


class MCPServerStatus(BaseModel):
    """MCP Server状态Schema"""
    server_id: int
    name: str
    is_enabled: bool
    is_connected: bool
    connection_status: str
    tool_count: int
    last_connected_at: Optional[datetime]
    error_message: Optional[str]


class MCPToolCallRequest(BaseModel):
    """工具调用请求Schema"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")
    context: Optional[str] = Field(None, description="调用上下文")
    session_id: Optional[str] = Field(None, description="会话ID")


class MCPToolCallResult(BaseModel):
    """工具调用结果Schema"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int
    tool_call_id: int 