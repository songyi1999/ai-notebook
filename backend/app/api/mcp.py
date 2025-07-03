"""
MCP (Model Context Protocol) 相关API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.mcp_server import MCPServer, MCPTool, MCPToolCall
from ..schemas.mcp import (
    MCPServerCreate, MCPServerUpdate, MCPServerResponse, MCPServerWithTools,
    MCPToolResponse, MCPToolCallResponse, MCPServerStatus,
    MCPToolCallRequest, MCPToolCallResult
)
from ..services.mcp_service import MCPClientService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.post("/servers", response_model=MCPServerResponse)
async def create_mcp_server(
    server_data: MCPServerCreate,
    db: Session = Depends(get_db)
):
    """创建MCP Server配置"""
    try:
        mcp_service = MCPClientService(db)
        server = await mcp_service.create_server(server_data)
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建MCP Server失败: {e}")
        raise HTTPException(status_code=500, detail="创建MCP Server失败")


@router.get("/servers", response_model=List[MCPServerResponse])
def get_mcp_servers(db: Session = Depends(get_db)):
    """获取所有MCP Server列表"""
    servers = db.query(MCPServer).all()
    return servers


@router.get("/servers/{server_id}", response_model=MCPServerWithTools)
def get_mcp_server(server_id: int, db: Session = Depends(get_db)):
    """获取指定MCP Server详情（包含工具列表）"""
    server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server不存在")
    
    # 构造响应数据
    server_data = MCPServerWithTools.model_validate(server)
    server_data.tools = server.tools
    return server_data


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: int,
    update_data: MCPServerUpdate,
    db: Session = Depends(get_db)
):
    """更新MCP Server配置"""
    try:
        mcp_service = MCPClientService(db)
        server = await mcp_service.update_server(server_id, update_data)
        if not server:
            raise HTTPException(status_code=404, detail="MCP Server不存在")
        return server
    except Exception as e:
        logger.error(f"更新MCP Server失败: {e}")
        raise HTTPException(status_code=500, detail="更新MCP Server失败")


@router.delete("/servers/{server_id}")
def delete_mcp_server(server_id: int, db: Session = Depends(get_db)):
    """删除MCP Server"""
    server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server不存在")
    
    try:
        db.delete(server)
        db.commit()
        return {"message": "MCP Server删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除MCP Server失败: {e}")
        raise HTTPException(status_code=500, detail="删除MCP Server失败")


@router.post("/servers/{server_id}/connect")
async def connect_mcp_server(server_id: int, db: Session = Depends(get_db)):
    """连接MCP Server"""
    try:
        mcp_service = MCPClientService(db)
        success = await mcp_service.connect_server(server_id)
        if success:
            return {"message": "连接成功"}
        else:
            raise HTTPException(status_code=400, detail="连接失败")
    except Exception as e:
        logger.error(f"连接MCP Server失败: {e}")
        raise HTTPException(status_code=500, detail="连接MCP Server失败")


@router.post("/servers/{server_id}/disconnect")
async def disconnect_mcp_server(server_id: int, db: Session = Depends(get_db)):
    """断开MCP Server连接"""
    try:
        mcp_service = MCPClientService(db)
        success = await mcp_service.disconnect_server(server_id)
        if success:
            return {"message": "断开连接成功"}
        else:
            raise HTTPException(status_code=400, detail="断开连接失败")
    except Exception as e:
        logger.error(f"断开MCP Server连接失败: {e}")
        raise HTTPException(status_code=500, detail="断开MCP Server连接失败")


@router.get("/servers/{server_id}/status", response_model=MCPServerStatus)
def get_mcp_server_status(server_id: int, db: Session = Depends(get_db)):
    """获取MCP Server状态"""
    mcp_service = MCPClientService(db)
    status_data = mcp_service.get_server_status(server_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="MCP Server不存在")
    return status_data


@router.post("/servers/{server_id}/discover-tools")
async def discover_mcp_tools(server_id: int, db: Session = Depends(get_db)):
    """发现MCP Server的工具"""
    try:
        mcp_service = MCPClientService(db)
        tools = await mcp_service.discover_tools(server_id)
        return {"message": f"发现 {len(tools)} 个工具", "tools_count": len(tools)}
    except Exception as e:
        logger.error(f"发现MCP工具失败: {e}")
        raise HTTPException(status_code=500, detail="发现MCP工具失败")


@router.get("/tools", response_model=List[MCPToolResponse])
def get_available_tools(db: Session = Depends(get_db)):
    """获取所有可用的MCP工具"""
    mcp_service = MCPClientService(db)
    tools = mcp_service.get_available_tools()
    return tools


@router.get("/tools/{tool_id}", response_model=MCPToolResponse)
def get_mcp_tool(tool_id: int, db: Session = Depends(get_db)):
    """获取指定MCP工具详情"""
    tool = db.query(MCPTool).filter(MCPTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="MCP工具不存在")
    return tool


@router.post("/tools/call", response_model=MCPToolCallResult)
async def call_mcp_tool(
    request: MCPToolCallRequest,
    db: Session = Depends(get_db)
):
    """调用MCP工具"""
    try:
        mcp_service = MCPClientService(db)
        result = await mcp_service.call_tool(request)
        return result
    except Exception as e:
        logger.error(f"调用MCP工具失败: {e}")
        raise HTTPException(status_code=500, detail="调用MCP工具失败")


@router.get("/tool-calls", response_model=List[MCPToolCallResponse])
def get_tool_calls(
    limit: int = 50,
    tool_id: Optional[int] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取工具调用历史"""
    query = db.query(MCPToolCall)
    
    if tool_id:
        query = query.filter(MCPToolCall.tool_id == tool_id)
    if session_id:
        query = query.filter(MCPToolCall.session_id == session_id)
    
    calls = query.order_by(MCPToolCall.created_at.desc()).limit(limit).all()
    return calls


@router.get("/tool-calls/{call_id}", response_model=MCPToolCallResponse)
def get_tool_call(call_id: int, db: Session = Depends(get_db)):
    """获取指定工具调用详情"""
    call = db.query(MCPToolCall).filter(MCPToolCall.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="工具调用记录不存在")
    return call


@router.post("/tool-calls/{call_id}/feedback")
def update_tool_call_feedback(
    call_id: int,
    feedback: int,  # 1为好评，0为差评
    db: Session = Depends(get_db)
):
    """更新工具调用反馈"""
    if feedback not in [0, 1]:
        raise HTTPException(status_code=400, detail="反馈值必须为0或1")
    
    call = db.query(MCPToolCall).filter(MCPToolCall.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="工具调用记录不存在")
    
    try:
        call.user_feedback = feedback
        db.commit()
        return {"message": "反馈更新成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"更新工具调用反馈失败: {e}")
        raise HTTPException(status_code=500, detail="更新反馈失败")


@router.get("/stats")
def get_mcp_stats(db: Session = Depends(get_db)):
    """获取MCP使用统计"""
    server_count = db.query(MCPServer).count()
    enabled_server_count = db.query(MCPServer).filter(MCPServer.is_enabled == True).count()
    connected_server_count = db.query(MCPServer).filter(MCPServer.is_connected == True).count()
    
    tool_count = db.query(MCPTool).count()
    available_tool_count = db.query(MCPTool).filter(MCPTool.is_available == True).count()
    
    call_count = db.query(MCPToolCall).count()
    success_call_count = db.query(MCPToolCall).filter(MCPToolCall.call_status == "success").count()
    
    return {
        "servers": {
            "total": server_count,
            "enabled": enabled_server_count,
            "connected": connected_server_count
        },
        "tools": {
            "total": tool_count,
            "available": available_tool_count
        },
        "calls": {
            "total": call_count,
            "success": success_call_count,
            "success_rate": round(success_call_count / call_count * 100, 2) if call_count > 0 else 0
        }
    } 