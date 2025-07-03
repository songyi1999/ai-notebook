from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class FileBase(BaseModel):
    file_path: str = Field(..., description="文件路径（相对路径），如 notes/技术/Python.md")
    title: str = Field(..., description="文件标题")
    content: Optional[str] = Field(None, description="文件内容（Markdown格式）")
    content_hash: Optional[str] = Field(None, description="内容哈希值，用于检测变更")
    file_size: int = Field(0, description="文件大小（字节）")
    is_deleted: bool = Field(False, description="软删除标记")
    parent_folder: Optional[str] = Field(None, description="父文件夹路径")
    file_metadata: Optional[dict] = Field(None, description="其他元数据（JSON格式）")

class FileCreate(FileBase):
    pass

class FileUpdate(FileBase):
    file_path: Optional[str] = None
    title: Optional[str] = None
    
class FileResponse(FileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 