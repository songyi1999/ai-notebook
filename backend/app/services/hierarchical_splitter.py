"""
智能多层次分块器 - 基于LLM的文档分析和分块策略
支持：1.LLM生成摘要层 2.LLM提取大纲层 3.智能内容层
对超长文档使用"分而治之"(Divide and Conquer)策略
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import hashlib
import math

from ..config import settings

logger = logging.getLogger(__name__)

class IntelligentHierarchicalSplitter:
    """基于LLM的智能多层次文本分块器"""
    
    def __init__(self, llm=None):
        self.llm = llm  # LLM实例，从AIService传入
        self.summary_max_length = settings.hierarchical_summary_max_length
        self.outline_max_depth = settings.hierarchical_outline_max_depth
        self.content_target_size = settings.hierarchical_content_target_size
        self.content_max_size = settings.hierarchical_content_max_size
        self.content_overlap = settings.hierarchical_content_overlap
        
        # LLM处理相关配置
        self.llm_context_window = settings.llm_context_window
        self.chunk_for_llm = settings.chunk_for_llm_processing
        self.max_refine_chunks = settings.max_chunks_for_refine
        
        # 用于预分块的文本分割器
        self.pre_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_for_llm,
            chunk_overlap=200,
            length_function=len,
        )
        
        # 用于最终内容分块的分割器
        self.content_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.content_target_size,
            chunk_overlap=self.content_overlap,
            length_function=len,
        )
    
    def split_document(self, content: str, title: str, file_id: int, progress_callback=None) -> Dict[str, List[Document]]:
        """
        智能多层次文档分块
        
        Args:
            content: 文档内容
            title: 文档标题
            file_id: 文件ID
            progress_callback: 进度回调函数
            
        Returns:
            包含三个层次文档的字典
        """
        try:
            logger.info(f"开始智能多层次分块，文件: {title}, 长度: {len(content)} 字符")
            
            if not self.llm:
                logger.warning("LLM不可用，降级到简单分块")
                if progress_callback:
                    progress_callback("降级处理", "LLM不可用，使用简单分块")
                return self._fallback_to_simple_chunking(content, title, file_id)
            
            # 判断是否需要分而治之策略
            needs_divide_conquer = len(content) > self.llm_context_window * 0.8  # 预留20%空间给prompt
            
            if needs_divide_conquer:
                logger.info(f"文档长度 {len(content)} 超过LLM窗口，使用分而治之策略")
                
                if progress_callback:
                    progress_callback("摘要生成", "使用分而治之策略生成摘要")
                summary_docs = self._create_summary_with_divide_conquer(content, title, file_id, progress_callback)
                
                if progress_callback:
                    progress_callback("大纲提取", "使用分而治之策略提取大纲")
                outline_docs = self._create_outline_with_divide_conquer(content, title, file_id, progress_callback)
            else:
                logger.info(f"文档长度 {len(content)} 适中，直接使用LLM分析")
                
                if progress_callback:
                    progress_callback("摘要生成", "直接使用LLM生成摘要")
                summary_docs = self._create_summary_direct(content, title, file_id, progress_callback)
                
                if progress_callback:
                    progress_callback("大纲提取", "直接使用LLM提取大纲")
                outline_docs = self._create_outline_direct(content, title, file_id, progress_callback)
            
            # Level 3: 基于大纲的智能内容分块
            if progress_callback:
                progress_callback("智能分块", "基于大纲进行智能内容分块")
            content_docs = self._create_intelligent_content_layer(content, title, file_id, outline_docs, progress_callback)
            
            result = {
                'summary': summary_docs,
                'outline': outline_docs,
                'content': content_docs
            }
            
            logger.info(f"智能分块完成: 摘要={len(summary_docs)}, 大纲={len(outline_docs)}, 内容={len(content_docs)}")
            return result
            
        except Exception as e:
            logger.error(f"智能分块失败: {e}")
            # 降级到简单分块
            if progress_callback:
                progress_callback("错误降级", f"智能分块失败: {str(e)}")
            return self._fallback_to_simple_chunking(content, title, file_id)
    
    def _create_summary_direct(self, content: str, title: str, file_id: int, progress_callback=None) -> List[Document]:
        """直接使用LLM生成摘要（文档长度适中时）"""
        try:
            prompt = f"""请为以下文档生成一个高质量的摘要，要求：
1. 摘要应该准确概括文档的主要内容和核心观点
2. 长度控制在{self.summary_max_length}字符以内
3. 保持逻辑清晰、信息完整
4. 突出文档的重点和特色

文档标题：{title}
文档内容：
{content}

摘要："""
            
            response = self.llm.invoke(prompt)
            summary = response.content.strip()
            
            doc = Document(
                page_content=summary,
                metadata={
                    "file_id": file_id,
                    "chunk_type": "summary",
                    "chunk_level": 1,
                    "chunk_index": 0,
                    "title": title,
                    "chunk_hash": hashlib.sha256(summary.encode()).hexdigest(),
                    "parent_heading": None,
                    "section_path": "全文摘要",
                    "generation_method": "direct_llm"
                }
            )
            
            if progress_callback:
                progress_callback("摘要完成", f"摘要生成成功，长度: {len(summary)}字符")
            
            logger.info(f"LLM直接生成摘要成功，长度: {len(summary)}")
            return [doc]
            
        except Exception as e:
            logger.error(f"LLM直接生成摘要失败: {e}")
            return []
    
    def _create_summary_with_divide_conquer(self, content: str, title: str, file_id: int, progress_callback=None) -> List[Document]:
        """使用分而治之策略生成摘要（超长文档）"""
        try:
            logger.info("开始分而治之摘要生成")
            
            # 1. 将文档分块
            chunks = self.pre_splitter.split_text(content)
            logger.info(f"文档分为 {len(chunks)} 个块进行处理")
            
            if len(chunks) == 1:
                # 如果只有一个块，直接处理
                return self._create_summary_direct(content, title, file_id, progress_callback)
            
            # 2. 使用Refine策略迭代生成摘要
            current_summary = None
            
            for i, chunk in enumerate(chunks[:self.max_refine_chunks]):  # 限制处理块数
                if progress_callback:
                    progress_callback("分块摘要", f"处理第 {i+1}/{min(len(chunks), self.max_refine_chunks)} 个文档片段")
                
                if current_summary is None:
                    # 第一个块：生成初始摘要
                    prompt = f"""请为以下文档片段生成一个详细的摘要，这是一个长文档的第一部分：

文档标题：{title}
文档片段 (第{i+1}部分)：
{chunk}

摘要："""
                else:
                    # 后续块：基于已有摘要进行精炼
                    prompt = f"""你已有的摘要是：
{current_summary}

现在请阅读以下新的文档片段，并将其信息融入到已有摘要中，生成一个更完整、更准确的摘要：

新的文档片段 (第{i+1}部分)：
{chunk}

要求：
1. 保留原摘要中的重要信息
2. 融入新片段的关键内容
3. 确保摘要逻辑连贯、信息完整
4. 控制长度在{self.summary_max_length}字符以内

更新后的摘要："""
                
                response = self.llm.invoke(prompt)
                current_summary = response.content.strip()
                logger.info(f"处理第 {i+1} 块，当前摘要长度: {len(current_summary)}")
            
            if current_summary:
                doc = Document(
                    page_content=current_summary,
                    metadata={
                        "file_id": file_id,
                        "chunk_type": "summary",
                        "chunk_level": 1,
                        "chunk_index": 0,
                        "title": title,
                        "chunk_hash": hashlib.sha256(current_summary.encode()).hexdigest(),
                        "parent_heading": None,
                        "section_path": "全文摘要",
                        "generation_method": "divide_conquer_refine",
                        "processed_chunks": min(len(chunks), self.max_refine_chunks)
                    }
                )
                
                logger.info(f"分而治之摘要生成成功，处理了 {min(len(chunks), self.max_refine_chunks)} 个块")
                return [doc]
            
            return []
            
        except Exception as e:
            logger.error(f"分而治之摘要生成失败: {e}")
            return []
    
    def _create_outline_direct(self, content: str, title: str, file_id: int, progress_callback=None) -> List[Document]:
        """直接使用LLM提取大纲（文档长度适中时）"""
        try:
            prompt = f"""请为以下文档提取详细的大纲结构，要求：
1. 识别文档的层次结构和章节划分
2. 提取每个章节的标题和主要内容点
3. 保持逻辑层次清晰
4. 如果文档没有明显的章节结构，请根据内容主题自行组织合理的大纲
5. 每个大纲项目应该包含足够的信息以便后续检索

文档标题：{title}
文档内容：
{content}

请以以下格式返回大纲，每行一个大纲项目：
1. [一级标题]
   1.1 [二级标题]
   1.2 [二级标题]
2. [一级标题]
   2.1 [二级标题]

大纲："""
            
            response = self.llm.invoke(prompt)
            outline_text = response.content.strip()
            
            # 解析大纲为独立的文档
            outline_docs = self._parse_outline_to_documents(outline_text, title, file_id)
            
            if progress_callback:
                progress_callback("大纲完成", f"大纲提取成功，生成 {len(outline_docs)} 个大纲项目")
            
            logger.info(f"LLM直接提取大纲成功，生成 {len(outline_docs)} 个大纲项目")
            return outline_docs
            
        except Exception as e:
            logger.error(f"LLM直接提取大纲失败: {e}")
            return []
    
    def _create_outline_with_divide_conquer(self, content: str, title: str, file_id: int, progress_callback=None) -> List[Document]:
        """使用分而治之策略提取大纲（超长文档）"""
        try:
            logger.info("开始分而治之大纲提取")
            
            # 1. 将文档分块
            chunks = self.pre_splitter.split_text(content)
            logger.info(f"文档分为 {len(chunks)} 个块进行大纲提取")
            
            if len(chunks) == 1:
                return self._create_outline_direct(content, title, file_id, progress_callback)
            
            # 2. 使用Refine策略迭代构建大纲
            current_outline = None
            
            for i, chunk in enumerate(chunks[:self.max_refine_chunks]):
                if progress_callback:
                    progress_callback("分块大纲", f"分析第 {i+1}/{min(len(chunks), self.max_refine_chunks)} 个文档片段")
                
                if current_outline is None:
                    # 第一个块：生成初始大纲
                    prompt = f"""请为以下文档片段提取大纲结构，这是一个长文档的第一部分：

文档标题：{title}
文档片段 (第{i+1}部分)：
{chunk}

请提取这部分的大纲结构："""
                else:
                    # 后续块：基于已有大纲进行扩展
                    prompt = f"""你已有的大纲是：
{current_outline}

现在请阅读以下新的文档片段，并将其结构信息融入到已有大纲中：

新的文档片段 (第{i+1}部分)：
{chunk}

要求：
1. 保留原大纲的结构
2. 添加新片段中的章节和要点
3. 确保大纲逻辑连贯、层次清晰
4. 合并相似的章节，避免重复

更新后的大纲："""
                
                response = self.llm.invoke(prompt)
                current_outline = response.content.strip()
                logger.info(f"处理第 {i+1} 块，当前大纲长度: {len(current_outline)}")
            
            if current_outline:
                # 解析最终大纲为文档
                outline_docs = self._parse_outline_to_documents(current_outline, title, file_id, generation_method="divide_conquer_refine")
                
                if progress_callback:
                    progress_callback("大纲完成", f"分而治之大纲提取成功，生成 {len(outline_docs)} 个大纲项目")
                
                logger.info(f"分而治之大纲提取成功，生成 {len(outline_docs)} 个大纲项目")
                return outline_docs
            
            return []
            
        except Exception as e:
            logger.error(f"分而治之大纲提取失败: {e}")
            return []
    
    def _parse_outline_to_documents(self, outline_text: str, title: str, file_id: int, generation_method: str = "direct_llm") -> List[Document]:
        """将大纲文本解析为独立的文档"""
        try:
            lines = outline_text.split('\n')
            outline_docs = []
            current_level_1 = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 简单的大纲解析逻辑
                if re.match(r'^\d+\.', line):  # 一级标题 (1. 2. 3.)
                    current_level_1 = line
                    doc = Document(
                        page_content=line,
                        metadata={
                            "file_id": file_id,
                            "chunk_type": "outline",
                            "chunk_level": 2,
                            "chunk_index": i,
                            "title": title,
                            "chunk_hash": hashlib.sha256(line.encode()).hexdigest(),
                            "parent_heading": None,
                            "section_path": line,
                            "outline_level": 1,
                            "generation_method": generation_method
                        }
                    )
                    outline_docs.append(doc)
                    
                elif re.match(r'^\s+\d+\.\d+', line):  # 二级标题 (1.1 1.2)
                    doc = Document(
                        page_content=line,
                        metadata={
                            "file_id": file_id,
                            "chunk_type": "outline",
                            "chunk_level": 2,
                            "chunk_index": i,
                            "title": title,
                            "chunk_hash": hashlib.sha256(line.encode()).hexdigest(),
                            "parent_heading": current_level_1,
                            "section_path": f"{current_level_1} / {line.strip()}" if current_level_1 else line.strip(),
                            "outline_level": 2,
                            "generation_method": generation_method
                        }
                    )
                    outline_docs.append(doc)
                
                elif line and not re.match(r'^\s*$', line):  # 其他非空行
                    doc = Document(
                        page_content=line,
                        metadata={
                            "file_id": file_id,
                            "chunk_type": "outline",
                            "chunk_level": 2,
                            "chunk_index": i,
                            "title": title,
                            "chunk_hash": hashlib.sha256(line.encode()).hexdigest(),
                            "parent_heading": current_level_1,
                            "section_path": f"{current_level_1} / {line.strip()}" if current_level_1 else line.strip(),
                            "outline_level": 3,
                            "generation_method": generation_method
                        }
                    )
                    outline_docs.append(doc)
            
            return outline_docs
            
        except Exception as e:
            logger.error(f"解析大纲失败: {e}")
            return []
    
    def _create_intelligent_content_layer(self, content: str, title: str, file_id: int, outline_docs: List[Document], progress_callback=None) -> List[Document]:
        """创建智能内容层（基于大纲的语义分块）"""
        try:
            if not outline_docs:
                # 没有大纲时，使用递归字符分块
                logger.info("没有大纲，使用递归字符分块")
                if progress_callback:
                    progress_callback("递归分块", "没有大纲，使用基本递归分块")
                return self._recursive_chunk_content(content, title, file_id)
            
            # 基于大纲进行智能分块
            logger.info(f"基于 {len(outline_docs)} 个大纲项目进行智能分块")
            
            if progress_callback:
                progress_callback("智能分块", f"基于 {len(outline_docs)} 个大纲项目进行智能分块")
            
            # 简化实现：使用递归分块，但保留大纲信息
            chunks = self.content_splitter.split_text(content)
            content_docs = []
            
            for i, chunk in enumerate(chunks):
                # 为每个内容块找到最相关的大纲项目
                best_outline = self._find_best_outline_for_chunk(chunk, outline_docs)
                
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "file_id": file_id,
                        "chunk_type": "content",
                        "chunk_level": 3,
                        "chunk_index": i,
                        "title": title,
                        "chunk_hash": hashlib.sha256(chunk.encode()).hexdigest(),
                        "parent_heading": best_outline.get('section_path') if best_outline else None,
                        "section_path": f"内容块-{i+1}",
                        "related_outline": best_outline.get('content') if best_outline else None
                    }
                )
                content_docs.append(doc)
            
            if progress_callback:
                progress_callback("分块完成", f"智能内容分块完成，生成 {len(content_docs)} 个内容块")
            
            logger.info(f"智能内容分块完成，生成 {len(content_docs)} 个内容块")
            return content_docs
            
        except Exception as e:
            logger.error(f"智能内容分块失败: {e}")
            if progress_callback:
                progress_callback("降级处理", f"智能分块失败: {str(e)}")
            return self._recursive_chunk_content(content, title, file_id)
    
    def _find_best_outline_for_chunk(self, chunk: str, outline_docs: List[Document]) -> Optional[Dict[str, str]]:
        """为内容块找到最相关的大纲项目"""
        try:
            # 简单实现：基于关键词匹配
            chunk_words = set(chunk.lower().split())
            best_match = None
            best_score = 0
            
            for outline_doc in outline_docs:
                outline_words = set(outline_doc.page_content.lower().split())
                # 计算交集得分
                intersection = len(chunk_words & outline_words)
                if intersection > best_score:
                    best_score = intersection
                    best_match = {
                        'content': outline_doc.page_content,
                        'section_path': outline_doc.metadata.get('section_path', '')
                    }
            
            return best_match
        except:
            return None
    
    def _recursive_chunk_content(self, content: str, title: str, file_id: int) -> List[Document]:
        """递归分块内容（兼容模式）"""
        chunks = self.content_splitter.split_text(content)
        content_docs = []
        
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "file_id": file_id,
                    "chunk_type": "content",
                    "chunk_level": 3,
                    "chunk_index": i,
                    "title": title,
                    "chunk_hash": hashlib.sha256(chunk.encode()).hexdigest(),
                    "parent_heading": None,
                    "section_path": f"内容块-{i+1}"
                }
            )
            content_docs.append(doc)
        
        return content_docs
    
    def _fallback_to_simple_chunking(self, content: str, title: str, file_id: int) -> Dict[str, List[Document]]:
        """降级到简单分块（保持兼容性）"""
        logger.warning("LLM不可用，降级到简单分块模式")
        
        # 至少创建一个简单的摘要块
        simple_summary = f"标题：{title}\n内容预览：{content[:500]}..."
        summary_doc = Document(
            page_content=simple_summary,
            metadata={
                "file_id": file_id,
                "chunk_type": "summary",
                "chunk_level": 1,
                "chunk_index": 0,
                "title": title,
                "chunk_hash": hashlib.sha256(simple_summary.encode()).hexdigest(),
                "parent_heading": None,
                "section_path": "简单摘要",
                "generation_method": "fallback"
            }
        )
        
        content_docs = self._recursive_chunk_content(content, title, file_id)
        
        return {
            'summary': [summary_doc],
            'outline': [],
            'content': content_docs
        }

# 向后兼容的类名别名
HierarchicalTextSplitter = IntelligentHierarchicalSplitter 