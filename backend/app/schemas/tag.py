from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TagBase(BaseModel):
    name: str = Field(..., description="标签名称")
    color: Optional[str] = Field(None, description="标签颜色")
    description: Optional[str] = Field(None, description="标签描述")
    is_auto_generated: bool = Field(False, description="是否自动生成")
    usage_count: int = Field(0, description="使用次数")

class TagCreate(TagBase):
    pass

class TagUpdate(TagBase):
    name: Optional[str] = None

class TagResponse(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FileTagBase(BaseModel):
    file_id: int = Field(..., description="文件ID")
    tag_id: int = Field(..., description="标签ID")
    relevance_score: float = Field(1.0, description="关联度评分")
    is_manual: bool = Field(True, description="是否手动添加")

class FileTagCreate(FileTagBase):
    pass

class FileTagResponse(FileTagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 