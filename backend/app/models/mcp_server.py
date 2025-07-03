"""
MCP Server相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class MCPServer(Base):
    """MCP服务器配置表"""
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="Server名称")
    description = Column(Text, comment="Server描述")
    server_type = Column(String(50), nullable=False, comment="Server类型：http, stdio, sse等")
    server_config = Column(JSON, nullable=False, comment="Server配置（URL、认证等）")
    auth_type = Column(String(50), comment="认证类型：none, api_key, bearer等")
    auth_config = Column(JSON, comment="认证配置")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_connected = Column(Boolean, default=False, comment="连接状态")
    connection_status = Column(String(50), comment="连接状态详情")
    last_connected_at = Column(DateTime, comment="最后连接时间")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    tools = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MCPServer(id={self.id}, name='{self.name}', type='{self.server_type}')>"


class MCPTool(Base):
    """MCP工具表"""
    __tablename__ = "mcp_tools"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, comment="关联的MCP Server ID")
    tool_name = Column(String(100), nullable=False, comment="工具名称")
    tool_description = Column(Text, comment="工具描述")
    input_schema = Column(JSON, comment="输入参数schema")
    output_schema = Column(JSON, comment="输出结果schema")
    tool_config = Column(JSON, comment="工具配置")
    is_available = Column(Boolean, default=True, comment="是否可用")
    usage_count = Column(Integer, default=0, comment="使用次数")
    last_used_at = Column(DateTime, comment="最后使用时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    server = relationship("MCPServer", back_populates="tools")
    tool_calls = relationship("MCPToolCall", back_populates="tool", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MCPTool(id={self.id}, name='{self.tool_name}', server_id={self.server_id})>"


class MCPToolCall(Base):
    """MCP工具调用历史表"""
    __tablename__ = "mcp_tool_calls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_id = Column(Integer, ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False, comment="关联的工具ID")
    session_id = Column(String(100), comment="聊天会话ID")
    call_context = Column(Text, comment="调用上下文（用户问题等）")
    input_data = Column(JSON, nullable=False, comment="调用输入参数")
    output_data = Column(JSON, comment="调用输出结果")
    call_status = Column(String(50), nullable=False, comment="调用状态：success, error, timeout")
    error_message = Column(Text, comment="错误信息")
    execution_time_ms = Column(Integer, comment="执行时间（毫秒）")
    ai_reasoning = Column(Text, comment="AI选择该工具的推理过程")
    user_feedback = Column(Integer, comment="用户反馈：1好评，0差评，NULL未评价")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    # 关联关系
    tool = relationship("MCPTool", back_populates="tool_calls")
    
    def __repr__(self):
        return f"<MCPToolCall(id={self.id}, tool_id={self.tool_id}, status='{self.call_status}')>" 