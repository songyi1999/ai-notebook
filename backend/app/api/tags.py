from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..schemas.tag import TagCreate, TagUpdate, TagResponse, FileTagCreate, FileTagResponse
from ..services.tag_service import TagService, FileTagService
from ..database.session import get_db

router = APIRouter()

@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag_api(tag: TagCreate, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    db_tag = tag_service.create_tag(tag)
    return db_tag

@router.get("/tags/{tag_id}", response_model=TagResponse)
def read_tag_api(tag_id: int, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    db_tag = tag_service.get_tag(tag_id)
    if db_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return db_tag

@router.get("/tags", response_model=List[TagResponse])
def read_all_tags_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    tags = tag_service.get_all_tags(skip=skip, limit=limit)
    return tags

@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag_api(tag_id: int, tag: TagUpdate, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    db_tag = tag_service.update_tag(tag_id=tag_id, tag_update=tag)
    if db_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return db_tag

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_api(tag_id: int, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    db_tag = tag_service.delete_tag(tag_id=tag_id)
    if db_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return

# FileTag API
@router.post("/file_tags", response_model=FileTagResponse, status_code=status.HTTP_201_CREATED)
def create_file_tag_api(file_tag: FileTagCreate, db: Session = Depends(get_db)):
    file_tag_service = FileTagService(db)
    db_file_tag = file_tag_service.create_file_tag(file_tag)
    return db_file_tag

@router.get("/files/{file_id}/tags", response_model=List[FileTagResponse])
def get_file_tags_api(file_id: int, db: Session = Depends(get_db)):
    file_tag_service = FileTagService(db)
    file_tags = file_tag_service.get_file_tags_by_file(file_id)
    return file_tags

@router.delete("/files/{file_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_tag_api(file_id: int, tag_id: int, db: Session = Depends(get_db)):
    file_tag_service = FileTagService(db)
    db_file_tag = file_tag_service.delete_file_tag(file_id=file_id, tag_id=tag_id)
    if db_file_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File-Tag relationship not found")
    return 