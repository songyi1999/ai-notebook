from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
from pathlib import Path
import shutil
import logging

from ..schemas.file import FileCreate, FileUpdate, FileResponse
from ..services.file_service import FileService
from ..database.session import get_db
from ..services.search_service import SearchService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def create_file_api(file: FileCreate, db: Session = Depends(get_db)):
    """创建文件"""
    file_service = FileService(db)
    db_file = file_service.create_file(file)
    return db_file

@router.get("/files", response_model=List[FileResponse])
def read_files_api(skip: int = 0, limit: int = 100, include_deleted: bool = False, db: Session = Depends(get_db)):
    """获取文件列表"""
    file_service = FileService(db)
    files = file_service.get_files(skip=skip, limit=limit, include_deleted=include_deleted)
    return files

@router.get("/files/by-path/{file_path:path}", response_model=FileResponse)
def read_file_by_path_api(file_path: str, db: Session = Depends(get_db)):
    """根据路径获取文件"""
    file_service = FileService(db)
    db_file = file_service.get_file_by_path(file_path)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

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
    q: str = Query(..., description="搜索查询"),
    search_type: str = Query("mixed", description="搜索类型: keyword, semantic, mixed"),
    limit: int = Query(50, ge=1, le=100, description="结果数量限制"),
    similarity_threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="语义搜索相似度阈值"),
    db: Session = Depends(get_db)
):
    """
    统一搜索API - 支持关键词、语义和混合搜索
    
    - **keyword**: 全文关键词搜索，返回所有匹配的文件
    - **semantic**: 语义相似度搜索，返回前N个最相关的文件
    - **mixed**: 混合搜索（默认），结合关键词和语义搜索结果
    """
    # 验证搜索查询
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索查询至少需要2个字符"
        )
    
    try:
        search_service = SearchService(db)
        
        # 强制使用配置中的默认值，忽略前端传递的值
        similarity_threshold = settings.semantic_search_threshold
        
        # 执行搜索
        search_results = search_service.search(
            query=q.strip(),
            search_type=search_type,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return search_results
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # 重新抛出HTTP异常，保持原始状态码
        raise
    except Exception as e:
        logger.error(f"搜索API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索服务暂时不可用"
        )

@router.get("/files/search/history")
def get_search_history_api(
    limit: int = Query(20, ge=1, le=100, description="历史记录数量"),
    db: Session = Depends(get_db)
):
    """获取搜索历史记录"""
    try:
        search_service = SearchService(db)
        history = search_service.get_search_history(limit)
        return {"history": history}
    except Exception as e:
        logger.error(f"获取搜索历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取搜索历史失败"
        )

@router.get("/files/search/popular")
def get_popular_queries_api(
    limit: int = Query(10, ge=1, le=50, description="热门查询数量"),
    db: Session = Depends(get_db)
):
    """获取热门搜索查询"""
    try:
        search_service = SearchService(db)
        popular = search_service.get_popular_queries(limit)
        return {"popular_queries": popular}
    except Exception as e:
        logger.error(f"获取热门查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取热门查询失败"
        )

@router.post("/files/delete-by-path")
def delete_file_by_path_api(request: dict, db: Session = Depends(get_db)):
    """通过路径删除文件或文件夹（同时删除数据库记录和向量索引）"""
    try:
        file_path = request.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="文件路径不能为空")
        
        path = Path(file_path)
        
        # 检查路径是否存在
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"路径不存在: {file_path}")
        
        file_service = FileService(db)
        
        if path.is_file():
            # 删除单个文件
            # 先从数据库中删除记录
            db_file = file_service.get_file_by_path(file_path)
            if db_file:
                file_service.delete_file(db_file.id)
            
            # 删除物理文件
            path.unlink()
            logger.info(f"删除文件成功: {file_path}")
            
        elif path.is_dir():
            # 删除文件夹及其所有内容
            # 递归删除数据库中的所有文件记录
            for file_path_in_dir in path.rglob("*.md"):
                relative_path = str(file_path_in_dir)
                db_file = file_service.get_file_by_path(relative_path)
                if db_file:
                    file_service.delete_file(db_file.id)
            
            # 删除物理文件夹
            shutil.rmtree(path)
            logger.info(f"删除文件夹成功: {file_path}")
        
        # 删除后重新构建索引
        from ..services.index_service import IndexService
        index_service = IndexService(db)
        index_service.rebuild_all_indexes()
        
        return {"success": True, "message": f"删除成功: {file_path}"}
        
    except Exception as e:
        logger.error(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/files/move")
def move_file_api(request: dict, db: Session = Depends(get_db)):
    """移动/重命名文件或目录"""
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
            
        final_destination = str(destination)
        
        # 检查是否是文件重命名/移动
        if source.is_file() and source_path.endswith('.md'):
            # 使用FileService的重命名方法
            file_service = FileService(db)
            success = file_service.rename_file(source_path, final_destination)
            
            if success:
                return {
                    "success": True,
                    "message": f"文件重命名成功: {source_path} -> {final_destination}",
                    "new_path": final_destination
                }
        else:
            # 对于目录或非.md文件，使用原来的移动方法
            # 确保目标父目录存在
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行移动操作
            shutil.move(str(source), str(destination))
            
            return {
                "success": True,
                "message": f"移动成功: {source_path} -> {final_destination}",
                "new_path": final_destination
            }
        
    except Exception as e:
        logger.error(f"移动/重命名失败: {e}")
        raise HTTPException(status_code=500, detail=f"移动文件/目录失败: {str(e)}")

# 将 {file_id} 路由放在最后，避免与具体路由冲突
@router.get("/files/{file_id}", response_model=FileResponse)
def read_file_api(file_id: int, db: Session = Depends(get_db)):
    """根据ID获取文件"""
    file_service = FileService(db)
    db_file = file_service.get_file(file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.put("/files/{file_id}", response_model=FileResponse)
def update_file_api(file_id: int, file: FileUpdate, db: Session = Depends(get_db)):
    """更新文件"""
    file_service = FileService(db)
    db_file = file_service.update_file(file_id=file_id, file_update=file)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return db_file

@router.put("/files/by-path/{file_path:path}", response_model=FileResponse)
def update_file_by_path_api(file_path: str, file: FileUpdate, db: Session = Depends(get_db)):
    """通过路径更新文件"""
    file_service = FileService(db)
    
    # 先获取文件
    db_file = file_service.get_file_by_path(file_path)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    # 更新文件
    updated_file = file_service.update_file(file_id=db_file.id, file_update=file)
    if updated_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return updated_file

@router.delete("/files/{file_id}")
def delete_file_api(
    file_id: int, 
    complete: bool = Query(False, description="是否完整删除（包括物理文件）"),
    db: Session = Depends(get_db)
):
    """删除文件"""
    file_service = FileService(db)
    
    if complete:
        # 完整删除（数据库记录 + 物理文件 + 向量索引）
        db_file = file_service.delete_file_completely(file_id=file_id, delete_physical=True)
        if db_file is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return {"success": True, "message": f"文件已完整删除: {db_file.file_path}"}
    else:
        # 软删除
        db_file = file_service.delete_file(file_id=file_id)
        if db_file is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return {"success": True, "message": f"文件已软删除: {db_file.file_path}"} 
 