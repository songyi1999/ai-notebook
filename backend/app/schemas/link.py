from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LinkBase(BaseModel):
    source_file_id: int = Field(..., description="源文件ID")
    target_file_id: Optional[int] = Field(None, description="目标文件ID（可能为空，表示链接到不存在的文件）")
    link_text: Optional[str] = Field(None, description="链接文本（如 [[目标文件]]）")
    link_type: str = Field('wikilink', description="链接类型：wikilink, external, image等")
    anchor_text: Optional[str] = Field(None, description="锚点文本（可选）")
    position_start: Optional[int] = Field(None, description="链接在源文件中的起始位置")
    position_end: Optional[int] = Field(None, description="链接在源文件中的结束位置")
    is_valid: bool = Field(True, description="链接是否有效")

class LinkCreate(LinkBase):
    pass

class LinkUpdate(LinkBase):
    source_file_id: Optional[int] = None
    link_text: Optional[str] = None

class LinkResponse(LinkBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 