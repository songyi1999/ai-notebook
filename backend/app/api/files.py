from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
from pathlib import Path
import shutil

from ..schemas.file import FileCreate, FileUpdate, FileResponse
from ..services.file_service import FileService
from ..database.session import get_db

router = APIRouter()

@router.post("/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def create_file_api(file: FileCreate, db: Session = Depends(get_db)):
    """创建文件"""
    file_service = FileService(db)
    db_file = file_service.create_file(file)
    return db_file

@router.get("/files/{file_id}", response_model=FileResponse)
def read_file_api(file_id: int, db: Session = Depends(get_db)):
    """根据ID获取文件"""
    file_service = FileService(db)
    db_file = file_service.get_file(file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.get("/files/by-path/{file_path:path}", response_model=FileResponse)
def read_file_by_path_api(file_path: str, db: Session = Depends(get_db)):
    """根据路径获取文件"""
    file_service = FileService(db)
    db_file = file_service.get_file_by_path(file_path)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.get("/files", response_model=List[FileResponse])
def read_files_api(skip: int = 0, limit: int = 100, include_deleted: bool = False, db: Session = Depends(get_db)):
    """获取文件列表"""
    file_service = FileService(db)
    files = file_service.get_files(skip=skip, limit=limit, include_deleted=include_deleted)
    return files

@router.put("/files/{file_id}", response_model=FileResponse)
def update_file_api(file_id: int, file: FileUpdate, db: Session = Depends(get_db)):
    """更新文件"""
    file_service = FileService(db)
    db_file = file_service.update_file(file_id=file_id, file_update=file)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_api(file_id: int, db: Session = Depends(get_db)):
    """删除文件"""
    file_service = FileService(db)
    db_file = file_service.delete_file(file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return

@router.get("/files/tree/{root_path:path}")
def get_file_tree_api(root_path: str = "notes"):
    """获取文件树结构"""
    try:
        # 确保根路径存在
        root_dir = Path(root_path)
        if not root_dir.exists():
            root_dir.mkdir(parents=True, exist_ok=True)
        
        def build_tree(path: Path) -> dict:
            """递归构建文件树"""
            if path.is_file():
                return {
                    "name": path.name,
                    "path": str(path),
                    "type": "file",
                    "size": path.stat().st_size,
                    "modified": path.stat().st_mtime
                }
            elif path.is_dir():
                children = []
                try:
                    for child in sorted(path.iterdir()):
                        # 跳过隐藏文件和系统文件
                        if not child.name.startswith('.'):
                            children.append(build_tree(child))
                except PermissionError:
                    pass  # 跳过没有权限的目录
                
                return {
                    "name": path.name,
                    "path": str(path),
                    "type": "directory",
                    "children": children
                }
        
        tree = build_tree(root_dir)
        # 如果是根目录，返回其子项
        if tree["type"] == "directory":
            return tree["children"]
        else:
            return [tree]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件树失败: {str(e)}")

@router.post("/files/create-directory")
def create_directory_api(request: dict):
    """创建目录"""
    try:
        dir_path = request.get("path")
        if not dir_path:
            raise HTTPException(status_code=400, detail="目录路径不能为空")
        
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        
        return {"success": True, "message": f"目录创建成功: {dir_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建目录失败: {str(e)}")

@router.get("/files/search")
def search_files_api(
    q: str = Query(..., description="搜索关键词"),
    search_type: str = Query("mixed", description="搜索类型: keyword, semantic, mixed"),
    limit: int = Query(50, description="结果数量限制"),
    db: Session = Depends(get_db)
):
    """搜索文件"""
    file_service = FileService(db)
    
    if search_type == "keyword":
        results = file_service.search_files_fts(q, limit)
    elif search_type == "semantic":
        # TODO: 实现语义搜索
        results = file_service.search_files_fts(q, limit)  # 暂时使用关键词搜索
    else:  # mixed
        results = file_service.search_files_fts(q, limit)
    
    return results

@router.post("/files/move")
def move_file_api(request: dict):
    """移动文件或目录"""
    try:
        source_path = request.get("source_path")
        destination_path = request.get("destination_path")
        
        if not source_path or not destination_path:
            raise HTTPException(status_code=400, detail="源路径和目标路径不能为空")
        
        source = Path(source_path)
        destination = Path(destination_path)
        
        # 确保源文件/目录存在
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"源路径不存在: {source_path}")
            
        # 如果目标是目录，将源文件/目录移动到其中
        if destination.is_dir():
            destination = destination / source.name
            
        # 确保目标父目录存在
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # 执行移动操作
        shutil.move(str(source), str(destination))
        
        return {
            "success": True,
            "message": f"移动成功: {source_path} -> {destination_path}",
            "new_path": str(destination)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移动文件/目录失败: {str(e)}") 