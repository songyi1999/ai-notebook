from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas.file import FileCreate, FileUpdate, FileResponse
from ..services.file_service import FileService
from ..database.session import get_db

router = APIRouter()

@router.post("/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def create_file_api(file: FileCreate, db: Session = Depends(get_db)):
    file_service = FileService(db)
    db_file = file_service.create_file(file)
    return db_file

@router.get("/files/{file_id}", response_model=FileResponse)
def read_file_api(file_id: int, db: Session = Depends(get_db)):
    file_service = FileService(db)
    db_file = file_service.get_file(file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.get("/files", response_model=List[FileResponse])
def read_files_api(skip: int = 0, limit: int = 100, include_deleted: bool = False, db: Session = Depends(get_db)):
    file_service = FileService(db)
    files = file_service.get_files(skip=skip, limit=limit, include_deleted=include_deleted)
    return files

@router.put("/files/{file_id}", response_model=FileResponse)
def update_file_api(file_id: int, file: FileUpdate, db: Session = Depends(get_db)):
    file_service = FileService(db)
    db_file = file_service.update_file(file_id=file_id, file_update=file)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_api(file_id: int, db: Session = Depends(get_db)):
    file_service = FileService(db)
    db_file = file_service.delete_file(file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return 