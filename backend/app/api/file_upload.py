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
        
        # 为成功转换的文件创建文件导入任务（入库+向量化）
        import_tasks = []
        task_processor = TaskProcessorService(db)
        
        for success_result in conversion_result['successful_conversions']:
            try:
                # 计算相对路径
                file_path = Path(success_result['target_path'])
                relative_path = str(file_path.relative_to(Path("./notes")))
                
                # 添加文件导入任务到队列（避免并发写库冲突）
                task_success = task_processor.add_task(
                    file_id=0,  # 文件还未入库，暂时使用0
                    file_path=relative_path,
                    task_type="file_import",  # 新的任务类型：文件导入
                    priority=2  # 高优先级，优先处理新文件
                )
                
                if task_success:
                    import_tasks.append({
                        'file_path': relative_path,
                        'original_filename': success_result['original_filename'],
                        'converted_filename': success_result['converted_filename']
                    })
                    logger.info(f"文件导入任务已加入队列: {relative_path}")
                else:
                    logger.error(f"文件导入任务添加失败: {relative_path}")
                
            except Exception as e:
                logger.error(f"添加文件导入任务失败: {success_result['converted_filename']} - {str(e)}")
                continue
        
        # 启动后台任务处理器
        if import_tasks:
            background_tasks.add_task(
                task_processor.process_all_pending_tasks
            )
        
        # 构造响应
        response_data = {
            'success': True,
            'message': '文件批量转换完成，导入任务已加入队列',
            'summary': {
                'total_files': conversion_result['total_files'],
                'processed_count': conversion_result['processed_count'],
                'successful_count': conversion_result['successful_count'],
                'failed_count': conversion_result['failed_count'],
                'ignored_count': conversion_result['ignored_count'],
                'queued_import_tasks': len(import_tasks)
            },
            'details': {
                'successful_conversions': conversion_result['successful_conversions'],
                'failed_conversions': conversion_result['failed_conversions'],
                'ignored_files': conversion_result['ignored_files'],
                'import_tasks': import_tasks
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
                    'queued_import_tasks': 0
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