"""
文件上传转换API
支持批量上传并转换文件为Markdown格式
"""
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import logging
from pathlib import Path

from ..database.session import get_db
from ..services.document_converter import DocumentConverter
from ..services.file_service import FileService
from ..services.task_processor_service import TaskProcessorService
from ..models.file import File as FileModel
from ..schemas.file import FileCreate

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化文档转换器
document_converter = DocumentConverter()

@router.post("/upload-and-convert")
async def upload_and_convert_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    target_folder: Optional[str] = Form(""),
    db: Session = Depends(get_db)
):
    """
    批量上传并转换文件为Markdown格式
    
    Args:
        background_tasks: FastAPI后台任务
        files: 上传的文件列表
        target_folder: 目标文件夹路径（相对于notes目录）
        db: 数据库会话
        
    Returns:
        转换结果汇总
    """
    try:
        start_time = logger.info(f"开始批量文件上传转换，文件数量: {len(files)}")
        
        # 确定目标目录
        notes_base_dir = Path("./notes")
        if target_folder and target_folder.strip():
            target_dir = notes_base_dir / target_folder.strip()
        else:
            target_dir = notes_base_dir
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备文件数据
        files_data = []
        total_size = 0
        
        for file in files:
            if not file.filename:
                continue
                
            # 读取文件内容
            file_content = await file.read()
            total_size += len(file_content)
            
            files_data.append((file_content, file.filename))
        
        logger.info(f"准备转换 {len(files_data)} 个文件，总大小: {total_size / (1024*1024):.2f}MB")
        
        # 批量转换文件
        conversion_result = await document_converter.batch_convert_files(
            files_data, str(target_dir)
        )
        
        # 为成功转换的文件创建数据库记录和索引任务
        created_files = []
        file_service = FileService(db)
        task_processor = TaskProcessorService(db)
        
        for success_result in conversion_result['successful_conversions']:
            try:
                # 读取转换后的文件内容
                file_path = Path(success_result['target_path'])
                relative_path = str(file_path.relative_to(Path("./notes")))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 创建文件记录
                file_create = FileCreate(
                    file_path=relative_path,
                    title=Path(success_result['converted_filename']).stem,
                    content=content
                )
                
                # 保存到数据库
                db_file = file_service.create_file(file_create, fast_mode=True)
                if db_file:
                    created_files.append({
                        'file_id': db_file.id,
                        'file_path': relative_path,
                        'original_filename': success_result['original_filename'],
                        'converted_filename': success_result['converted_filename']
                    })
                    
                    # 添加后台索引任务
                    background_tasks.add_task(
                        task_processor.create_pending_task,
                        db_file.id,
                        "vector_index",
                        1  # 高优先级
                    )
                    
                    logger.info(f"文件已保存到数据库: {relative_path}")
                
            except Exception as e:
                logger.error(f"保存文件到数据库失败: {success_result['converted_filename']} - {str(e)}")
                # 转换成功但保存失败，仍然算作转换成功
                continue
        
        # 构造响应
        response_data = {
            'success': True,
            'message': '文件批量转换完成',
            'summary': {
                'total_files': conversion_result['total_files'],
                'processed_count': conversion_result['processed_count'],
                'successful_count': conversion_result['successful_count'],
                'failed_count': conversion_result['failed_count'],
                'ignored_count': conversion_result['ignored_count'],
                'created_db_records': len(created_files)
            },
            'details': {
                'successful_conversions': conversion_result['successful_conversions'],
                'failed_conversions': conversion_result['failed_conversions'],
                'ignored_files': conversion_result['ignored_files'],
                'created_files': created_files
            },
            'target_folder': str(target_dir.relative_to(notes_base_dir)) if target_folder else ""
        }
        
        logger.info(f"批量转换完成: 总计{conversion_result['total_files']}个文件，"
                   f"成功{conversion_result['successful_count']}个，"
                   f"失败{conversion_result['failed_count']}个，"
                   f"忽略{conversion_result['ignored_count']}个")
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"批量文件上传转换失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f'批量文件上传转换失败: {str(e)}',
                'summary': {
                    'total_files': len(files) if files else 0,
                    'processed_count': 0,
                    'successful_count': 0,
                    'failed_count': 0,
                    'ignored_count': 0,
                    'created_db_records': 0
                }
            }
        )

@router.post("/upload-progress")
async def upload_with_progress(
    files: List[UploadFile] = File(...),
    target_folder: Optional[str] = Form(""),
    db: Session = Depends(get_db)
):
    """
    带进度的文件上传转换（流式响应）
    
    Args:
        files: 上传的文件列表
        target_folder: 目标文件夹路径
        db: 数据库会话
        
    Returns:
        逐步返回处理进度
    """
    try:
        # 这个版本先简化，直接返回最终结果
        # 后续可以改为 StreamingResponse 实现真正的流式进度
        return await upload_and_convert_files(
            BackgroundTasks(), files, target_folder, db
        )
        
    except Exception as e:
        logger.error(f"带进度的文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )

@router.get("/supported-formats")
async def get_supported_formats():
    """
    获取支持的文件格式
    
    Returns:
        支持的文件格式列表
    """
    return {
        'supported_extensions': list(document_converter.supported_extensions),
        'max_file_size_mb': document_converter.max_file_size // (1024 * 1024),
        'description': {
            '.txt': 'TXT文本文件（自动检测编码）',
            '.md': 'Markdown文件',
            '.docx': 'Word文档',
            '.pdf': 'PDF文档'
        }
    } 