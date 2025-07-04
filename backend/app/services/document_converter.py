"""
文档转换服务
支持将 txt、docx、pdf、md 文件转换为 markdown 格式
"""
import os
import tempfile
import chardet
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

# LangChain 导入
try:
    from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LangChain依赖未安装: {e}")
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)

class DocumentConverter:
    """文档转换器类"""
    
    def __init__(self):
        self.supported_extensions = {'.txt', '.md', '.docx', '.pdf'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                length_function=len,
            )
        else:
            self.text_splitter = None
    
    def is_supported_file(self, filename: str) -> bool:
        """检查文件是否支持转换"""
        return Path(filename).suffix.lower() in self.supported_extensions
    
    def get_unique_filename(self, target_dir: str, base_name: str) -> str:
        """生成唯一的文件名，避免重名冲突"""
        target_path = Path(target_dir)
        base_path = Path(base_name)
        
        # 获取基础名称和扩展名
        name_without_ext = base_path.stem
        ext = '.md'  # 所有文件都转换为md
        
        # 检查是否已存在
        full_path = target_path / f"{name_without_ext}{ext}"
        if not full_path.exists():
            return f"{name_without_ext}{ext}"
        
        # 如果存在，添加数字后缀
        counter = 1
        while True:
            new_name = f"{name_without_ext}_{counter}{ext}"
            full_path = target_path / new_name
            if not full_path.exists():
                return new_name
            counter += 1
    
    async def convert_file(self, file_content: bytes, original_filename: str, target_dir: str) -> Dict[str, Any]:
        """
        转换文件为 Markdown 格式
        
        Args:
            file_content: 文件二进制内容
            original_filename: 原始文件名
            target_dir: 目标目录
            
        Returns:
            转换结果字典
        """
        try:
            file_extension = Path(original_filename).suffix.lower()
            
            # 检查文件大小
            if len(file_content) > self.max_file_size:
                return {
                    'success': False,
                    'error': f'文件过大，最大支持 {self.max_file_size // (1024*1024)}MB',
                    'original_filename': original_filename
                }
            
            # 检查文件格式
            if not self.is_supported_file(original_filename):
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_extension}',
                    'original_filename': original_filename
                }
            
            # 生成唯一文件名
            md_filename = self.get_unique_filename(target_dir, original_filename)
            target_path = Path(target_dir) / md_filename
            
            # 根据文件类型进行转换
            if file_extension == '.txt':
                markdown_content = await self._convert_txt_to_md(file_content, original_filename)
            elif file_extension == '.md':
                markdown_content = await self._convert_md_to_md(file_content, original_filename)
            elif file_extension == '.docx':
                markdown_content = await self._convert_docx_to_md(file_content, original_filename)
            elif file_extension == '.pdf':
                markdown_content = await self._convert_pdf_to_md(file_content, original_filename)
            else:
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_extension}',
                    'original_filename': original_filename
                }
            
            # 保存转换后的文件
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"文件转换成功: {original_filename} -> {md_filename}")
            
            return {
                'success': True,
                'original_filename': original_filename,
                'converted_filename': md_filename,
                'target_path': str(target_path),
                'content_length': len(markdown_content),
                'file_type': file_extension
            }
            
        except Exception as e:
            logger.error(f"文件转换失败: {original_filename} - {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original_filename': original_filename
            }
    
    async def _convert_txt_to_md(self, file_content: bytes, filename: str) -> str:
        """转换 TXT 文件为 Markdown"""
        try:
            # 检测编码
            detected = chardet.detect(file_content)
            encoding = detected.get('encoding', 'utf-8')
            confidence = detected.get('confidence', 0)
            
            logger.info(f"检测到编码: {encoding}, 置信度: {confidence} - 文件: {filename}")
            
            # 尝试解码
            text_content = None
            
            # 按优先级尝试不同编码
            encodings_to_try = [encoding] if encoding else []
            encodings_to_try.extend(['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1'])
            
            for enc in encodings_to_try:
                try:
                    text_content = file_content.decode(enc)
                    logger.info(f"成功使用编码 {enc} 解码文件: {filename}")
                    break
                except (UnicodeDecodeError, TypeError):
                    continue
            
            if text_content is None:
                raise Exception("无法检测文件编码，请确保文件为文本格式")
            
            # 基本的格式化处理，保留原始文本结构
            lines = text_content.split('\n')
            markdown_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # 不做自动标题识别，保持原始文本格式
                    # 用户可以手动添加Markdown标记
                    markdown_lines.append(line)
                else:
                    markdown_lines.append("")
            
            return '\n'.join(markdown_lines)
            
        except Exception as e:
            logger.error(f"TXT转换失败: {filename} - {str(e)}")
            raise Exception(f"TXT文件转换失败: {str(e)}")
    
    async def _convert_md_to_md(self, file_content: bytes, filename: str) -> str:
        """转换 MD 文件（主要是编码检测和规范化）"""
        try:
            # 检测编码
            detected = chardet.detect(file_content)
            encoding = detected.get('encoding', 'utf-8')
            
            # 尝试解码
            encodings_to_try = [encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for enc in encodings_to_try:
                try:
                    text_content = file_content.decode(enc)
                    return text_content
                except (UnicodeDecodeError, TypeError):
                    continue
            
            raise Exception("无法解码 Markdown 文件")
            
        except Exception as e:
            logger.error(f"MD转换失败: {filename} - {str(e)}")
            raise Exception(f"Markdown文件处理失败: {str(e)}")
    
    async def _convert_docx_to_md(self, file_content: bytes, filename: str) -> str:
        """转换 DOCX 文件为 Markdown"""
        if not LANGCHAIN_AVAILABLE:
            raise Exception("LangChain依赖未安装，无法处理DOCX文件")
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(file_content)
        
        try:
            # 使用 LangChain 加载器
            loader = Docx2txtLoader(temp_file_path)
            docs = loader.load()
            
            # 提取文本内容
            full_text = "\n\n".join([doc.page_content for doc in docs])
            
            # 基本的 Markdown 格式化，保留原始文本结构
            lines = full_text.split('\n')
            markdown_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # 不做自动标题识别，保持原始文本格式
                    # 用户可以手动添加Markdown标记
                    markdown_lines.append(line)
                else:
                    markdown_lines.append("")
            
            return '\n'.join(markdown_lines)
            
        except Exception as e:
            logger.error(f"DOCX转换失败: {filename} - {str(e)}")
            raise Exception(f"DOCX文件转换失败: {str(e)}")
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {str(e)}")
    
    async def _convert_pdf_to_md(self, file_content: bytes, filename: str) -> str:
        """转换 PDF 文件为 Markdown"""
        if not LANGCHAIN_AVAILABLE:
            raise Exception("LangChain依赖未安装，无法处理PDF文件")
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(file_content)
        
        try:
            # 使用 LangChain 加载器
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()
            
            # 提取文本内容
            markdown_lines = []
            
            for i, doc in enumerate(docs):
                # 添加页面标记
                if len(docs) > 1:
                    markdown_lines.append(f"## 第 {i+1} 页")
                    markdown_lines.append("")
                
                # 处理页面内容
                content = doc.page_content.strip()
                if content:
                    # 按段落分割
                    paragraphs = content.split('\n\n')
                    for paragraph in paragraphs:
                        paragraph = paragraph.strip().replace('\n', ' ')
                        if paragraph:
                            markdown_lines.append(paragraph)
                            markdown_lines.append("")
            
            return '\n'.join(markdown_lines)
            
        except Exception as e:
            logger.error(f"PDF转换失败: {filename} - {str(e)}")
            raise Exception(f"PDF文件转换失败: {str(e)}")
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {str(e)}")
    
    async def batch_convert_files(self, files_data: List[Tuple[bytes, str]], target_dir: str) -> Dict[str, Any]:
        """
        批量转换文件
        
        Args:
            files_data: 文件数据列表，每个元素为 (文件内容, 文件名)
            target_dir: 目标目录
            
        Returns:
            批量转换结果
        """
        total_files = len(files_data)
        processed_files = []
        successful_conversions = []
        failed_conversions = []
        ignored_files = []
        
        for file_content, filename in files_data:
            # 检查是否支持的格式
            if not self.is_supported_file(filename):
                ignored_files.append({
                    'filename': filename,
                    'reason': f'不支持的文件格式: {Path(filename).suffix}'
                })
                continue
            
            # 转换文件
            result = await self.convert_file(file_content, filename, target_dir)
            processed_files.append(result)
            
            if result['success']:
                successful_conversions.append(result)
            else:
                failed_conversions.append(result)
        
        return {
            'total_files': total_files,
            'processed_count': len(processed_files),
            'successful_count': len(successful_conversions),
            'failed_count': len(failed_conversions),
            'ignored_count': len(ignored_files),
            'successful_conversions': successful_conversions,
            'failed_conversions': failed_conversions,
            'ignored_files': ignored_files
        } 