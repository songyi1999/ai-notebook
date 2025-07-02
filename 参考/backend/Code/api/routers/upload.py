"""
文件上传路由处理模块
支持图片、PDF、DOCX文件的上传和处理
"""
import os
import uuid
import tempfile
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path
import time
import httpx
import json
from config import settings

# 文档处理相关导入
try:
    from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"文档处理依赖未安装: {e}")
    DOCUMENT_PROCESSING_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 支持的文件格式
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.docx'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (文档文件可能较大)

# 创建上传目录
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# OCR服务配置
OCR_BASE_URL = "http://ocr:7860"

class DocumentService:
    """文档处理服务类"""
    
    def __init__(self):
        if DOCUMENT_PROCESSING_AVAILABLE:
            # 配置文本分割器，用于处理大文档
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                length_function=len,
            )
        else:
            self.text_splitter = None
    
    async def process_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        处理上传的文档文件并提取其内容
        
        Args:
            file_content: 文件的二进制内容
            filename: 文件名
            
        Returns:
            包含提取文本和元数据的字典
        """
        if not DOCUMENT_PROCESSING_AVAILABLE:
            raise Exception("文档处理功能不可用，请安装相关依赖")
        
        # 保存到临时文件
        file_extension = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(file_content)
        
        try:
            # 根据文件类型选择加载器
            if file_extension == '.pdf':
                docs, metadata = self._process_pdf(temp_file_path)
            elif file_extension == '.docx':
                docs, metadata = self._process_docx(temp_file_path)
            else:
                raise ValueError(f"不支持的文件类型: {file_extension}")
            
            # 提取文本内容
            full_text = "\n\n".join([doc.page_content for doc in docs])
            
            # 返回解析结果
            return {
                "filename": filename,
                "content": full_text,
                "page_count": metadata.get("page_count", 1),
                "file_type": metadata.get("file_type", "unknown"),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)} - 文件: {__file__} - 函数: process_document")
            raise Exception(f"文档处理失败: {str(e)}")
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {str(e)} - 文件: {__file__} - 函数: process_document")
    
    def _process_pdf(self, file_path: str) -> Tuple[List[Any], Dict[str, Any]]:
        """处理PDF文件"""
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            # 提取元数据
            metadata = {
                "page_count": len(docs),
                "file_type": "PDF"
            }
            
            return docs, metadata
        except Exception as e:
            logger.error(f"PDF处理失败: {str(e)} - 文件: {__file__} - 函数: _process_pdf")
            raise Exception(f"PDF文件解析失败: {str(e)}")
    
    def _process_docx(self, file_path: str) -> Tuple[List[Any], Dict[str, Any]]:
        """处理DOCX文件"""
        try:
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            
            # 提取元数据 (DOCX加载器通常只返回一个文档对象)
            metadata = {
                "page_count": 1,  # DOCX通常不分页
                "file_type": "DOCX"
            }
            
            return docs, metadata
        except Exception as e:
            logger.error(f"DOCX处理失败: {str(e)} - 文件: {__file__} - 函数: _process_docx")
            raise Exception(f"DOCX文件解析失败: {str(e)}")

# 初始化文档服务
document_service = DocumentService()

def is_image_file(filename: str) -> bool:
    """检查是否为支持的图片格式"""
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS

def is_document_file(filename: str) -> bool:
    """检查是否为支持的文档格式"""
    return Path(filename).suffix.lower() in ALLOWED_DOCUMENT_EXTENSIONS

def is_supported_file(filename: str) -> bool:
    """检查是否为支持的文件格式"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def get_file_type(filename: str) -> str:
    """获取文件类型"""
    extension = Path(filename).suffix.lower()
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    elif extension in ALLOWED_DOCUMENT_EXTENSIONS:
        return "document"
    else:
        return "unknown"

def generate_unique_filename(original_filename: str) -> str:
    """生成唯一的文件名"""
    # 获取文件扩展名
    file_extension = Path(original_filename).suffix
    # 生成唯一ID
    unique_id = str(uuid.uuid4())
    # 添加时间戳
    timestamp = str(int(time.time()))
    return f"{timestamp}_{unique_id}{file_extension}"

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
) -> dict:
    """文件上传接口
    
    Args:
        request: FastAPI请求对象
        file: 上传的文件
        
    Returns:
        上传结果信息
    """
    try:
        # 检查文件是否存在
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="未选择文件"
            )
        
        # 检查文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大支持 {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # 检查文件类型
        if not is_supported_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 生成唯一文件名
        unique_filename = generate_unique_filename(file.filename)
        file_path = UPLOAD_DIR / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 构造文件访问URL
        file_url = f"/api/v1/files/{unique_filename}"
        file_type = get_file_type(file.filename)
        
        logger.info(f"文件上传成功: {file.filename} -> {unique_filename}, 类型: {file_type} - 文件: {__file__} - 函数: upload_file")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "data": {
                "filename": unique_filename,
                "original_filename": file.filename,
                "file_url": file_url,
                "file_size": len(content),
                "file_type": file_type,
                "content_type": file.content_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)} - 文件: {__file__} - 函数: upload_file")
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )

@router.get("/files/{filename}")
async def get_file(filename: str):
    """获取上传的文件
    
    Args:
        filename: 文件名
        
    Returns:
        文件响应
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="文件不存在"
            )
        
        # 检查文件是否为支持的类型
        if not is_supported_file(filename):
            raise HTTPException(
                status_code=400,
                detail="不支持的文件类型"
            )
        
        # 根据文件类型设置合适的媒体类型
        file_type = get_file_type(filename)
        if file_type == "image":
            media_type = "image/*"
        elif file_type == "document":
            extension = Path(filename).suffix.lower()
            if extension == '.pdf':
                media_type = "application/pdf"
            elif extension == '.docx':
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                media_type = "application/octet-stream"
        else:
            media_type = "application/octet-stream"
        
        logger.info(f"访问文件: {filename}, 类型: {file_type} - 文件: {__file__} - 函数: get_file")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {str(e)} - 文件: {__file__} - 函数: get_file")
        raise HTTPException(
            status_code=500,
            detail=f"获取文件失败: {str(e)}"
        )

@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """删除上传的文件
    
    Args:
        filename: 文件名
        
    Returns:
        删除结果
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="文件不存在"
            )
        
        # 删除文件
        file_path.unlink()
        
        logger.info(f"文件删除成功: {filename} - 文件: {__file__} - 函数: delete_file")
        
        return {
            "success": True,
            "message": "文件删除成功",
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件删除失败: {str(e)} - 文件: {__file__} - 函数: delete_file")
        raise HTTPException(
            status_code=500,
            detail=f"文件删除失败: {str(e)}"
        )

@router.get("/files")
async def list_files():
    """获取所有上传的文件列表
    
    Returns:
        文件列表
    """
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file() and is_supported_file(file_path.name):
                file_stat = file_path.stat()
                file_type = get_file_type(file_path.name)
                files.append({
                    "filename": file_path.name,
                    "size": file_stat.st_size,
                    "file_type": file_type,
                    "created_time": file_stat.st_ctime,
                    "modified_time": file_stat.st_mtime
                })
        
        # 按创建时间排序（最新的在前）
        files.sort(key=lambda x: x["created_time"], reverse=True)
        
        logger.info(f"获取文件列表成功，共 {len(files)} 个文件 - 文件: {__file__} - 函数: list_files")
        
        return {
            "success": True,
            "data": {
                "files": files,
                "total": len(files)
            }
        }
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)} - 文件: {__file__} - 函数: list_files")
        raise HTTPException(
            status_code=500,
            detail=f"获取文件列表失败: {str(e)}"
        )

@router.post("/upload-and-convert")
async def upload_and_convert_to_markdown(
    request: Request,
    file: UploadFile = File(...)
) -> dict:
    """文件上传并转换为文本接口
    支持图片（通过OCR）、PDF、DOCX文件的处理
    
    Args:
        request: FastAPI请求对象
        file: 上传的文件（图片、PDF、DOCX）
        
    Returns:
        包含文本内容的聊天格式响应
    """
    try:
        start_time = time.time()
        logger.info(f"开始处理文件转换: {file.filename} - 文件: {__file__} - 函数: upload_and_convert_to_markdown")
        
        # 检查文件是否存在
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="未选择文件"
            )
        
        # 检查文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大支持 {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # 检查文件类型
        if not is_supported_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 生成唯一文件名并保存
        unique_filename = generate_unique_filename(file.filename)
        file_path = UPLOAD_DIR / unique_filename
        file_type = get_file_type(file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"文件保存成功: {unique_filename}, 类型: {file_type} - 文件: {__file__} - 函数: upload_and_convert_to_markdown")
        
        # 根据文件类型选择处理方式
        try:
            if file_type == "image":
                # 图片文件 - 使用OCR服务
                text_content = await call_ocr_service(file_path, file.filename)
                processing_type = "图片OCR分析"
                content_icon = "📷"
            elif file_type == "document":
                # 文档文件 - 使用文档处理服务
                doc_result = await document_service.process_document(content, file.filename)
                text_content = doc_result['content']
                processing_type = f"{doc_result['file_type']}文档解析"
                content_icon = "📄" if doc_result['file_type'] == "PDF" else "📝"
            else:
                raise Exception(f"不支持的文件类型: {file_type}")
            
            logger.info(f"{processing_type}成功，用时: {time.time() - start_time:.2f}秒 - 文件: {__file__} - 函数: upload_and_convert_to_markdown")
            
            # 构造聊天格式的响应 - 优化医疗评价场景
            chat_response = {
                "success": True,
                "message": f"{processing_type}成功",
                "data": {
                    "type": "chat_message",
                    "role": "assistant", 
                    "content": f"{content_icon} **{processing_type}完成**\n\n我已经分析了您上传的{file_type}文件 `{file.filename}`，以下是提取的内容：\n\n---\n\n{text_content}\n\n---\n\n💡 **说明**: 如果您需要对此内容进行医疗评价分析，请告诉我具体需要分析的方面（如质量评价、项目评估、风险分析等）。",
                    "original_filename": file.filename,
                    "file_url": f"/api/v1/files/{unique_filename}",
                    "processing_time": f"{time.time() - start_time:.2f}秒",
                    "file_type": file_type,
                    "processing_type": processing_type
                }
            }
            
            return chat_response
            
        except Exception as processing_error:
            logger.error(f"{processing_type if 'processing_type' in locals() else '文件处理'}失败: {str(processing_error)} - 文件: {__file__} - 函数: upload_and_convert_to_markdown")
            
            # 根据文件类型生成不同的错误消息
            if file_type == "image":
                error_content = f"❌ **图片分析失败**\n\n抱歉，无法解析图片 `{file.filename}` 的内容。\n\n**可能的原因：**\n- 📷 图片内容过于复杂或模糊\n- 🔍 图片分辨率不足，建议使用高清图片\n- 🌐 OCR服务暂时不可用\n- 📄 图片中可能没有可识别的文字内容\n\n**建议：**\n- 请尝试上传更清晰的图片\n- 确保图片中包含清晰的文字内容\n- 如果问题持续，请联系技术支持\n\n您也可以直接描述图片内容，我会基于您的描述进行医疗评价分析。"
            elif file_type == "document":
                error_content = f"❌ **文档解析失败**\n\n抱歉，无法解析文档 `{file.filename}` 的内容。\n\n**可能的原因：**\n- 📄 文档格式损坏或不标准\n- 🔒 文档可能有密码保护\n- 🌐 文档处理服务暂时不可用\n- 📝 文档内容过于复杂\n\n**建议：**\n- 请确保文档格式正确且未损坏\n- 如果是PDF，请确保没有密码保护\n- 如果是DOCX，请确保是标准格式\n- 如果问题持续，请联系技术支持\n\n您也可以直接复制粘贴文档内容，我会基于您提供的文本进行医疗评价分析。"
            else:
                error_content = f"❌ **文件处理失败**\n\n抱歉，无法处理文件 `{file.filename}`。\n\n错误信息：{str(processing_error)}"
            
            return {
                "success": False,
                "message": f"{file_type}处理失败",
                "data": {
                    "type": "chat_message",
                    "role": "assistant",
                    "content": error_content,
                    "error": str(processing_error),
                    "original_filename": file.filename,
                    "file_url": f"/api/v1/files/{unique_filename}",
                    "file_type": file_type,
                    "analysis_failed": True
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传和转换失败: {str(e)} - 文件: {__file__} - 函数: upload_and_convert_to_markdown")
        raise HTTPException(
            status_code=500,
            detail=f"文件上传和转换失败: {str(e)}"
        )

async def call_ocr_service(file_path: Path, original_filename: str) -> str:
    """调用OCR服务进行图片转markdown转换
    
    Args:
        file_path: 文件路径
        original_filename: 原始文件名
        
    Returns:
        转换后的markdown内容
    """
    try:
        logger.info(f"调用OCR服务: {original_filename} - 文件: {__file__} - 函数: call_ocr_service")
        
        # 调用OCR API
        timeout = httpx.Timeout(180.0, connect=30.0)  # 增加超时时间，CPU模式可能较慢
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            # OCR服务的API端点 (优先使用我们的标准OCR接口)
            api_endpoints = [
                f"{OCR_BASE_URL}/ocr/upload",  # 优先使用标准OCR上传端点
                f"{OCR_BASE_URL}/extract"      # 备用兼容DocExt格式的端点
            ]
            
            last_error = None
            
            for endpoint in api_endpoints:
                try:
                    logger.info(f"尝试调用端点: {endpoint} - 文件: {__file__} - 函数: call_ocr_service")
                    
                    # 使用标准的FastAPI文件上传格式
                    with open(file_path, 'rb') as f:
                        files = {'file': (original_filename, f, 'image/*')}
                        data = {
                            'max_new_tokens': '4096',  # 增加生成长度，确保能识别长文本
                            'extract_type': 'ocr'  # 兼容参数
                        }
                        
                        response = await client.post(
                            endpoint,
                            files=files,
                            data=data
                        )
                    
                    logger.info(f"端点 {endpoint} 响应状态: {response.status_code} - 文件: {__file__} - 函数: call_ocr_service")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            logger.info(f"端点 {endpoint} 响应数据类型: {type(result)} - 文件: {__file__} - 函数: call_ocr_service")
                            
                            # 处理我们OCR服务的标准响应格式
                            if isinstance(result, dict):
                                if result.get('success') and result.get('text'):
                                    markdown_content = result['text'].strip()
                                    if len(markdown_content) > 10:
                                        logger.info(f"OCR转换成功，使用端点: {endpoint}，内容长度: {len(markdown_content)} - 文件: {__file__} - 函数: call_ocr_service")
                                        return markdown_content
                                elif result.get('error'):
                                    logger.error(f"OCR服务返回错误: {result['error']} - 文件: {__file__} - 函数: call_ocr_service")
                                    last_error = result['error']
                                    continue
                            
                            # 兼容其他格式的响应
                            markdown_content = extract_markdown_from_response(result)
                            if markdown_content and len(markdown_content.strip()) > 10:
                                logger.info(f"OCR转换成功(兼容格式)，使用端点: {endpoint}，内容长度: {len(markdown_content)} - 文件: {__file__} - 函数: call_ocr_service")
                                return markdown_content
                            else:
                                logger.warning(f"端点 {endpoint} 返回内容过短或为空 - 文件: {__file__} - 函数: call_ocr_service")
                                continue
                                
                        except Exception as parse_error:
                            # 如果不是JSON，尝试作为文本处理
                            text_content = response.text.strip()
                            if text_content and len(text_content) > 10:
                                logger.info(f"OCR转换成功(文本格式)，使用端点: {endpoint} - 文件: {__file__} - 函数: call_ocr_service")
                                return text_content
                            else:
                                logger.warning(f"端点 {endpoint} 解析失败: {parse_error} - 文件: {__file__} - 函数: call_ocr_service")
                                continue
                    
                    elif response.status_code == 404:
                        logger.warning(f"端点 {endpoint} 不存在 (404) - 文件: {__file__} - 函数: call_ocr_service")
                        continue
                    
                    elif response.status_code == 422:
                        logger.warning(f"端点 {endpoint} 参数错误 (422): {response.text} - 文件: {__file__} - 函数: call_ocr_service")
                        last_error = f"参数错误: {response.text}"
                        continue
                    
                    else:
                        logger.warning(f"端点 {endpoint} 返回错误: {response.status_code} - {response.text} - 文件: {__file__} - 函数: call_ocr_service")
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        continue
                        
                except httpx.ConnectError as e:
                    logger.warning(f"无法连接到端点 {endpoint}: {str(e)} - 文件: {__file__} - 函数: call_ocr_service")
                    last_error = f"连接错误: {str(e)}"
                    continue
                    
                except httpx.TimeoutException as e:
                    logger.warning(f"端点 {endpoint} 超时: {str(e)} - 文件: {__file__} - 函数: call_ocr_service")
                    last_error = f"请求超时: {str(e)}"
                    continue
                    
                except Exception as e:
                    logger.warning(f"调用端点 {endpoint} 时出错: {str(e)} - 文件: {__file__} - 函数: call_ocr_service")
                    last_error = str(e)
                    continue
            
            # 所有端点都失败了
            raise Exception(f"所有OCR端点都无法访问。OCR服务可能未启动或配置错误。最后的错误: {last_error}")
            
    except Exception as e:
        logger.error(f"调用OCR服务失败: {str(e)} - 文件: {__file__} - 函数: call_ocr_service")
        raise Exception(f"图片转换服务暂时不可用: {str(e)}")

@router.post("/chat-with-documents")
async def chat_with_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    message: str = Form(""),
    history: str = Form("[]")
) -> StreamingResponse:
    """
    文档聊天接口 - 处理文档和消息的组合请求
    支持多文档上传，并基于文档内容回答用户问题
    
    Args:
        request: FastAPI请求对象
        files: 上传的文档文件列表
        message: 用户问题
        history: 聊天历史记录（JSON字符串）
        
    Returns:
        流式聊天响应
    """
    try:
        start_time = time.time()
        logger.info(f"开始处理文档聊天请求，文件数量: {len(files)}, 消息: {message[:100]}... - 文件: {__file__} - 函数: chat_with_documents")
        
        # 解析历史记录
        try:
            chat_history = json.loads(history) if history else []
        except json.JSONDecodeError:
            chat_history = []
        
        # 处理所有文档
        all_document_contents = []
        document_summaries = []
        
        for file in files:
            # 检查文件
            if not file.filename:
                continue
                
            if not is_supported_file(file.filename):
                logger.warning(f"跳过不支持的文件: {file.filename} - 文件: {__file__} - 函数: chat_with_documents")
                continue
            
            # 读取文件内容
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                logger.warning(f"文件过大，跳过: {file.filename} - 文件: {__file__} - 函数: chat_with_documents")
                continue
            
            file_type = get_file_type(file.filename)
            logger.info(f"处理文件: {file.filename}, 类型: {file_type} - 文件: {__file__} - 函数: chat_with_documents")
            
            # 根据文件类型处理
            if file_type == "image":
                # 图片文件 - 使用OCR
                try:
                    # 保存临时文件
                    unique_filename = generate_unique_filename(file.filename)
                    temp_file_path = UPLOAD_DIR / unique_filename
                    with open(temp_file_path, "wb") as buffer:
                        buffer.write(content)
                    
                    # 调用OCR服务
                    text_content = await call_ocr_service(temp_file_path, file.filename)
                    all_document_contents.append({
                        "filename": file.filename,
                        "type": "图片OCR",
                        "content": text_content
                    })
                    
                    # 清理临时文件
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                        
                except Exception as e:
                    logger.error(f"图片处理失败: {file.filename} - {str(e)} - 文件: {__file__} - 函数: chat_with_documents")
                    continue
                    
            elif file_type == "document":
                # 文档文件 - 使用文档处理
                try:
                    doc_result = await document_service.process_document(content, file.filename)
                    text_content = doc_result['content']
                    
                    all_document_contents.append({
                        "filename": file.filename,
                        "type": doc_result['file_type'],
                        "content": text_content,
                        "page_count": doc_result.get('page_count', 1)
                    })
                    
                except Exception as e:
                    logger.error(f"文档处理失败: {file.filename} - {str(e)} - 文件: {__file__} - 函数: chat_with_documents")
                    continue
        
        if not all_document_contents:
            # 没有成功处理的文档
            async def error_generator():
                error_response = {
                    "choices": [{
                        "delta": {
                            "content": "❌ **文档处理失败**\n\n抱歉，无法处理您上传的文档。请检查文档格式是否正确，或稍后重试。"
                        }
                    }]
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                error_generator(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        
        # 处理文档内容 - 判断长度并进行总结
        processed_contents = []
        for doc in all_document_contents:
            content = doc['content']
            
            # 判断内容长度
            if len(content) > 2000:  # 超过2k字符
                logger.info(f"文档内容过长({len(content)}字符)，开始总结: {doc['filename']} - 文件: {__file__} - 函数: chat_with_documents")
                
                # 调用大模型进行总结
                try:
                    summary = await summarize_long_document(content, doc['filename'])
                    processed_contents.append({
                        "filename": doc['filename'],
                        "type": doc['type'],
                        "content": summary,
                        "is_summary": True,
                        "original_length": len(content)
                    })
                    logger.info(f"文档总结完成: {doc['filename']}, 原长度: {len(content)}, 总结长度: {len(summary)} - 文件: {__file__} - 函数: chat_with_documents")
                except Exception as e:
                    logger.error(f"文档总结失败: {doc['filename']} - {str(e)} - 文件: {__file__} - 函数: chat_with_documents")
                    # 总结失败，截取前2000字符
                    processed_contents.append({
                        "filename": doc['filename'],
                        "type": doc['type'],
                        "content": content[:2000] + "...(内容过长，已截取)",
                        "is_summary": False,
                        "original_length": len(content)
                    })
            else:
                # 内容不长，直接使用
                processed_contents.append({
                    "filename": doc['filename'],
                    "type": doc['type'],
                    "content": content,
                    "is_summary": False,
                    "original_length": len(content)
                })
        
        # 构建提示词
        prompt = build_document_chat_prompt(processed_contents, message, chat_history)
        
        # 调用聊天API
        from config import settings
        
        async def stream_generator():
            try:
                # 导入聊天相关模块
                from api.agents.base import ATMPAgent
                
                # 创建智能体实例
                agent = ATMPAgent()
                
                # 构建消息列表
                messages = []
                
                # 添加系统提示
                messages.append({
                    "role": "system",
                    "content": prompt
                })
                
                # 添加历史记录
                for hist_msg in chat_history[-4:]:  # 只保留最近4条历史记录
                    messages.append(hist_msg)
                
                # 添加当前问题
                if message:
                    messages.append({
                        "role": "user", 
                        "content": message
                    })
                
                # 流式生成回答
                async for chunk in agent.get_streaming_answer(message, messages):
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        response_data = {
                            "choices": [{
                                "delta": {
                                    "content": chunk.content
                                }
                            }]
                        }
                        yield f"data: {json.dumps(response_data)}\n\n"
                
                # 发送结束标志
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"流式生成失败: {str(e)} - 文件: {__file__} - 函数: stream_generator")
                error_response = {
                    "choices": [{
                        "delta": {
                            "content": f"抱歉，生成回答时出现错误：{str(e)}"
                        }
                    }]
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                yield "data: [DONE]\n\n"
        
        logger.info(f"文档聊天处理完成，用时: {time.time() - start_time:.2f}秒 - 文件: {__file__} - 函数: chat_with_documents")
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except Exception as e:
        logger.error(f"文档聊天请求处理失败: {str(e)} - 文件: {__file__} - 函数: chat_with_documents")
        
        async def error_generator():
            error_response = {
                "choices": [{
                    "delta": {
                        "content": f"抱歉，处理您的请求时发生了错误：{str(e)}"
                    }
                }]
            }
            yield f"data: {json.dumps(error_response)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            error_generator(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

async def summarize_long_document(content: str, filename: str) -> str:
    """
    对长文档进行总结
    
    Args:
        content: 文档内容
        filename: 文件名
        
    Returns:
        总结后的内容
    """
    try:
        from langchain_openai import ChatOpenAI
        from config import settings
        
        # 使用轻量级模型进行总结
        summarizer = ChatOpenAI(
            model=settings.MODELNAME,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.3
        )
        
        # 构建总结提示词
        summarize_prompt = f"""请对以下文档内容进行总结和提炼，保留关键信息和要点：

文档名称：{filename}
文档内容：
{content}

请按以下格式输出总结：

## 📋 文档总结

### 🎯 核心要点
[列出3-5个核心要点]

### 📊 关键信息
[提取重要的数据、结论、建议等]

### 🔍 详细内容
[保留重要的细节信息，但要简洁明了]

要求：
1. 保留所有重要的医疗评价相关信息
2. 突出关键数据和结论
3. 保持逻辑清晰，结构完整
4. 总结长度控制在1500字以内
"""
        
        # 调用模型进行总结
        response = await summarizer.ainvoke(summarize_prompt)
        summary = response.content.strip()
        
        return summary
        
    except Exception as e:
        logger.error(f"文档总结失败: {filename} - {str(e)} - 文件: {__file__} - 函数: summarize_long_document")
        # 总结失败，返回截取的内容
        return content[:1500] + "\n\n...(原文档内容过长，已截取关键部分)"

def build_document_chat_prompt(documents: List[Dict], user_message: str, chat_history: List[Dict]) -> str:
    """
    构建文档聊天的提示词
    
    Args:
        documents: 处理后的文档内容列表
        user_message: 用户问题
        chat_history: 聊天历史
        
    Returns:
        构建的提示词
    """
    # 构建文档内容部分
    docs_content = ""
    for i, doc in enumerate(documents, 1):
        summary_note = " (已总结)" if doc.get('is_summary') else ""
        docs_content += f"""
## 📄 文档 {i}: {doc['filename']} ({doc['type']}{summary_note})

{doc['content']}

---
"""
    
    # 构建完整提示词
    prompt = f"""你是一个专业的医疗评价助手，擅长分析医疗项目、临床试验、药物评估等相关文档。

## 📚 参考文档
用户已上传了以下文档，请基于这些文档内容来回答问题：

{docs_content}

## 🎯 任务要求
1. **基于文档内容回答**：主要参考上述文档内容来回答用户问题
2. **专业性**：使用专业的医疗评价术语和标准
3. **准确性**：确保回答准确，避免过度解读或推测
4. **结构化**：使用清晰的格式组织回答，便于阅读
5. **引用说明**：在回答中适当引用具体的文档内容

## 💡 回答格式建议
- 使用标题和子标题组织内容
- 重要信息用**粗体**标记
- 使用列表展示要点
- 必要时提供表格或图表说明
- 在回答末尾注明参考的文档

请基于以上文档内容，专业、准确地回答用户的问题。如果问题超出文档范围，请明确说明并提供一般性的专业建议。"""

    return prompt

def extract_markdown_from_response(response_data) -> str:
    """从DocExt响应中提取markdown内容
    
    Args:
        response_data: DocExt API响应数据
        
    Returns:
        提取的markdown内容
    """
    try:
        logger.info(f"处理响应数据，类型: {type(response_data)} - 文件: {__file__} - 函数: extract_markdown_from_response")
        
        # 如果直接是字符串，返回
        if isinstance(response_data, str):
            return response_data.strip()
        
        # 如果是列表（Gradio API通常返回列表）
        if isinstance(response_data, list):
            for item in response_data:
                if isinstance(item, str) and len(item.strip()) > 10:
                    return item.strip()
                elif isinstance(item, dict):
                    nested_result = extract_markdown_from_response(item)
                    if nested_result and len(nested_result.strip()) > 10:
                        return nested_result
        
        # 如果是字典
        if isinstance(response_data, dict):
            # Gradio API常见的响应格式
            gradio_keys = [
                'data',      # Gradio标准响应格式
                'prediction', # 预测结果
                'output',    # 输出结果
                'result'     # 结果
            ]
            
            # 首先尝试Gradio标准格式
            for key in gradio_keys:
                if key in response_data:
                    value = response_data[key]
                    if isinstance(value, list) and value:
                        # 通常Gradio的data是一个列表
                        nested_result = extract_markdown_from_response(value)
                        if nested_result and len(nested_result.strip()) > 10:
                            return nested_result
                    elif isinstance(value, str) and len(value.strip()) > 10:
                        return value.strip()
            
            # 然后尝试其他可能的键名
            other_keys = [
                'markdown',
                'content', 
                'text',
                'extracted_text',
                'markdown_content',
                'ocr_result',
                'document_text'
            ]
            
            for key in other_keys:
                if key in response_data and response_data[key]:
                    content = response_data[key]
                    if isinstance(content, str) and len(content.strip()) > 10:
                        return content.strip()
                    elif isinstance(content, list):
                        nested_result = extract_markdown_from_response(content)
                        if nested_result and len(nested_result.strip()) > 10:
                            return nested_result
            
            # 深层递归查找
            for key, value in response_data.items():
                if isinstance(value, (dict, list)):
                    nested_result = extract_markdown_from_response(value)
                    if nested_result and len(nested_result.strip()) > 10:
                        return nested_result
                elif isinstance(value, str) and len(value.strip()) > 50:  # 假设有意义的内容至少50字符
                    return value.strip()
        
        # 如果都找不到，返回调试信息
        logger.warning(f"无法从响应中提取markdown内容，响应格式: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)} - 文件: {__file__} - 函数: extract_markdown_from_response")
        
        # 返回格式化的调试信息
        if isinstance(response_data, dict):
            return f"响应格式不符合预期。响应键: {list(response_data.keys())}\n响应内容: {str(response_data)[:500]}..."
        else:
            return f"响应格式不符合预期。响应类型: {type(response_data)}\n响应内容: {str(response_data)[:500]}..."
        
    except Exception as e:
        logger.error(f"提取markdown内容失败: {str(e)} - 文件: {__file__} - 函数: extract_markdown_from_response")
        return f"内容提取失败: {str(e)}" 