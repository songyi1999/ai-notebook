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
            
            logger.info("🧠 开始第三层：基于大纲的智能内容分块")
            content_docs = self._create_intelligent_content_layer(content, title, file_id, outline_docs, progress_callback)
            logger.info(f"✅ 第三层完成，内容层生成: {len(content_docs)} 个文档")
            
            # 组装最终结果
            result = {
                'summary': summary_docs,
                'outline': outline_docs,
                'content': content_docs
            }
            
            # 最终统计和验证
            total_docs = len(summary_docs) + len(outline_docs) + len(content_docs)
            logger.info(f"📊 智能分块最终统计:")
            logger.info(f"  📝 摘要层: {len(summary_docs)} 个文档")
            logger.info(f"  📋 大纲层: {len(outline_docs)} 个文档") 
            logger.info(f"  📄 内容层: {len(content_docs)} 个文档")
            logger.info(f"  📊 总计: {total_docs} 个文档")
            
            # 验证结果的完整性
            if total_docs == 0:
                logger.error("❌ 智能分块最终结果为空，这不应该发生")
                raise Exception("智能分块结果为空")
            
            if len(summary_docs) == 0:
                logger.warning("⚠️ 没有生成摘要文档")
            
            if len(content_docs) == 0:
                logger.warning("⚠️ 没有生成内容文档")
            
            logger.info(f"🎉 智能分块完成: 摘要={len(summary_docs)}, 大纲={len(outline_docs)}, 内容={len(content_docs)}")
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
                    "generation_method": "direct_llm",
                    "vector_model": "hierarchical_summary"
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
                        "processed_chunks": min(len(chunks), self.max_refine_chunks),
                        "vector_model": "hierarchical_summary"
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
                            "generation_method": generation_method,
                            "vector_model": "hierarchical_outline"
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
                            "generation_method": generation_method,
                            "vector_model": "hierarchical_outline"
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
                            "generation_method": generation_method,
                            "vector_model": "hierarchical_outline"
                        }
                    )
                    outline_docs.append(doc)
            
            return outline_docs
            
        except Exception as e:
            logger.error(f"解析大纲失败: {e}")
            return []
    
    def _create_intelligent_content_layer(self, content: str, title: str, file_id: int, outline_docs: List[Document], progress_callback=None) -> List[Document]:
        """创建智能内容层（基于大纲的语义分块）"""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"🔄 开始创建智能内容层 - 文件ID: {file_id}, 标题: {title}")
            logger.info(f"📄 内容长度: {len(content)} 字符")
            logger.info(f"📋 大纲文档数量: {len(outline_docs) if outline_docs else 0}")
            
            # 验证输入参数
            if not content or not content.strip():
                logger.error("❌ 内容为空，无法进行智能分块")
                return []
            
            if not outline_docs:
                # 没有大纲时，使用递归字符分块
                logger.info("⚠️ 没有大纲文档，降级使用递归字符分块")
                if progress_callback:
                    progress_callback("递归分块", "没有大纲，使用基本递归分块")
                return self._recursive_chunk_content(content, title, file_id)
            
            # 基于大纲进行智能分块
            logger.info(f"🧠 基于 {len(outline_docs)} 个大纲项目进行智能分块")
            
            # 输出大纲文档的详细信息
            for i, outline_doc in enumerate(outline_docs[:3]):  # 只显示前3个
                logger.info(f"  📝 大纲 {i+1}: {outline_doc.page_content[:50]}...")
                logger.info(f"      章节路径: {outline_doc.metadata.get('section_path', 'N/A')}")
            
            if progress_callback:
                progress_callback("智能分块", f"基于 {len(outline_docs)} 个大纲项目进行智能分块")
            
            # 使用内容分割器进行分块
            logger.info("🔪 开始使用内容分割器进行分块...")
            try:
                chunks = self.content_splitter.split_text(content)
                logger.info(f"✅ 分块完成，共生成 {len(chunks)} 个内容块")
                
                # 验证分块结果
                if not chunks:
                    logger.error("❌ 分块结果为空，降级到递归分块")
                    return self._recursive_chunk_content(content, title, file_id)
                
                # 统计分块信息
                total_chars = sum(len(chunk) for chunk in chunks)
                avg_length = total_chars / len(chunks) if chunks else 0
                logger.info(f"📊 分块统计 - 总字符数: {total_chars}, 平均长度: {avg_length:.0f}, 块数: {len(chunks)}")
                
            except Exception as e:
                logger.error(f"❌ 内容分割器失败: {e}")
                logger.error(f"📋 内容分割器配置: chunk_size={self.content_splitter.chunk_size}, overlap={self.content_splitter.chunk_overlap}")
                return self._recursive_chunk_content(content, title, file_id)
            
            # 创建内容文档
            logger.info("🏗️ 开始创建内容文档并匹配大纲...")
            content_docs = []
            matched_outlines = 0
            
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"🔍 处理第 {i+1}/{len(chunks)} 个内容块 (长度: {len(chunk)} 字符)")
                    
                    # 验证内容块
                    if not chunk or not chunk.strip():
                        logger.warning(f"⚠️ 第 {i+1} 个内容块为空，跳过")
                        continue
                    
                    # 为每个内容块找到最相关的大纲项目
                    best_outline = self._find_best_outline_for_chunk(chunk, outline_docs)
                    
                    if best_outline:
                        matched_outlines += 1
                        logger.info(f"✅ 为内容块 {i+1} 匹配到大纲: {best_outline.get('section_path', 'N/A')}")
                    else:
                        logger.info(f"⚠️ 内容块 {i+1} 未匹配到相关大纲")
                    
                    # 创建文档对象
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
                            "related_outline": best_outline.get('content') if best_outline else None,
                            "vector_model": "hierarchical_intelligent"
                        }
                    )
                    content_docs.append(doc)
                    
                    # 每10个块输出一次进度
                    if (i + 1) % 10 == 0:
                        logger.info(f"📈 进度: {i+1}/{len(chunks)} 个内容块已处理")
                
                except Exception as e:
                    logger.error(f"❌ 处理第 {i+1} 个内容块时发生错误: {e}")
                    import traceback
                    logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
                    continue
            
            # 统计结果
            processing_time = time.time() - start_time
            logger.info(f"📊 智能内容分块统计:")
            logger.info(f"  ✅ 成功创建: {len(content_docs)} 个内容文档")
            logger.info(f"  🎯 大纲匹配: {matched_outlines}/{len(content_docs)} 个内容块")
            logger.info(f"  ⏱️ 处理时间: {processing_time:.2f} 秒")
            logger.info(f"  📊 匹配率: {matched_outlines/len(content_docs)*100:.1f}%")
            
            if progress_callback:
                progress_callback("分块完成", f"智能内容分块完成，生成 {len(content_docs)} 个内容块")
            
            # 验证最终结果
            if not content_docs:
                logger.error("❌ 智能内容分块结果为空，降级到递归分块")
                return self._recursive_chunk_content(content, title, file_id)
            
            logger.info(f"🎉 智能内容分块完成，生成 {len(content_docs)} 个内容块")
            return content_docs
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ 智能内容分块失败 (耗时: {processing_time:.2f}s): {e}")
            import traceback
            logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
            
            if progress_callback:
                progress_callback("降级处理", f"智能分块失败: {str(e)}")
            
            # 降级到递归分块
            logger.info("🔄 降级到递归分块处理...")
            return self._recursive_chunk_content(content, title, file_id)
    
    def _find_best_outline_for_chunk(self, chunk: str, outline_docs: List[Document]) -> Optional[Dict[str, str]]:
        """为内容块找到最相关的大纲项目"""
        try:
            if not chunk or not chunk.strip():
                logger.warning("⚠️ 输入的内容块为空，无法匹配大纲")
                return None
            
            if not outline_docs:
                logger.warning("⚠️ 没有大纲文档可供匹配")
                return None
            
            # 改进的匹配算法：多维度匹配
            best_match = None
            best_score = 0
            match_details = []
            
            # 预处理内容块
            chunk_clean = self._clean_text_for_matching(chunk)
            chunk_keywords = self._extract_keywords(chunk_clean)
            
            logger.debug(f"🔍 开始匹配大纲，内容块长度: {len(chunk)} 字符")
            logger.debug(f"🔤 提取关键词: {list(chunk_keywords)[:10]}...")  # 只显示前10个关键词
            
            for i, outline_doc in enumerate(outline_docs):
                try:
                    outline_content = outline_doc.page_content
                    if not outline_content or not outline_content.strip():
                        logger.debug(f"⚠️ 大纲 {i+1} 内容为空，跳过")
                        continue
                    
                    # 预处理大纲内容
                    outline_clean = self._clean_text_for_matching(outline_content)
                    outline_keywords = self._extract_keywords(outline_clean)
                    
                    # 计算多维度匹配得分
                    score = self._calculate_match_score(chunk_clean, outline_clean, chunk_keywords, outline_keywords)
                    
                    match_details.append({
                        'outline_index': i,
                        'outline_content': outline_content[:50] + '...' if len(outline_content) > 50 else outline_content,
                        'section_path': outline_doc.metadata.get('section_path', 'N/A'),
                        'score': score,
                        'keywords_intersection': len(chunk_keywords & outline_keywords)
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'content': outline_content,
                            'section_path': outline_doc.metadata.get('section_path', ''),
                            'score': score,
                            'keywords_intersection': len(chunk_keywords & outline_keywords)
                        }
                    
                except Exception as e:
                    logger.warning(f"⚠️ 处理大纲 {i+1} 时发生错误: {e}")
                    continue
            
            # 输出匹配详情 (调试模式)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("🔍 大纲匹配详情:")
                sorted_details = sorted(match_details, key=lambda x: x['score'], reverse=True)
                for detail in sorted_details[:3]:  # 只显示前3个最佳匹配
                    logger.debug(f"  📝 大纲: {detail['outline_content']}")
                    logger.debug(f"      路径: {detail['section_path']}")
                    logger.debug(f"      得分: {detail['score']:.3f}, 关键词交集: {detail['keywords_intersection']}")
            
            # 设置匹配阈值
            min_score_threshold = 0.1  # 最低匹配得分
            
            if best_match and best_score >= min_score_threshold:
                logger.debug(f"✅ 找到最佳匹配 - 章节: {best_match['section_path']}")
                logger.debug(f"    综合得分: {best_match['score']:.3f}, 关键词交集: {best_match['keywords_intersection']}")
                return best_match
            else:
                logger.debug(f"❌ 未找到满足阈值({min_score_threshold})的匹配，最高得分: {best_score:.3f}")
                return None
            
        except Exception as e:
            logger.error(f"❌ 大纲匹配过程发生错误: {e}")
            import traceback
            logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
            return None
    
    def _clean_text_for_matching(self, text: str) -> str:
        """清理文本用于匹配"""
        import re
        # 移除markdown标记、特殊符号和多余空格
        text = re.sub(r'[#*\-\[\](){}「」《》\'""]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词（支持中文）"""
        import re
        # 提取中文词汇（2-4个字符）和英文单词
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        english_words = re.findall(r'[a-zA-Z]{2,}', text.lower())
        
        # 过滤常用词
        stop_words = {
            # 中文常用词
            '的', '了', '在', '是', '和', '与', '或', '等', '及', '以', '为', '有', '无', '可', '能', '要', '用',
            '这', '那', '对', '中', '不', '也', '就', '都', '而', '然', '但', '因', '所', '会', '到', '说', '很',
            '其', '如', '由', '时', '上', '下', '内', '外', '前', '后', '左', '右', '大', '小', '多', '少',
            # 英文常用词
            'the', 'of', 'and', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'is', 'are', 'was', 'were',
            'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'this', 'that', 'these', 'those', 'a', 'an', 'or', 'but', 'if', 'then'
        }
        
        # 合并关键词并过滤
        keywords = set()
        for word in chinese_words + english_words:
            if word.lower() not in stop_words and len(word) >= 2:
                keywords.add(word.lower())
        
        return keywords
    
    def _calculate_match_score(self, chunk_text: str, outline_text: str, chunk_keywords: set, outline_keywords: set) -> float:
        """计算匹配得分"""
        import re
        scores = []
        
        # 1. 关键词重叠得分
        if chunk_keywords and outline_keywords:
            intersection = chunk_keywords & outline_keywords
            union = chunk_keywords | outline_keywords
            jaccard_score = len(intersection) / len(union) if union else 0
            scores.append(jaccard_score * 0.4)  # 权重0.4
        
        # 2. 文本包含关系得分
        contains_score = 0
        outline_lower = outline_text.lower()
        chunk_lower = chunk_text.lower()
        
        # 检查大纲关键词在内容中的出现情况
        outline_important_words = [word for word in outline_keywords if len(word) >= 2]
        if outline_important_words:
            found_words = sum(1 for word in outline_important_words if word in chunk_lower)
            contains_score = found_words / len(outline_important_words)
            scores.append(contains_score * 0.3)  # 权重0.3
        
        # 3. 长度相似性得分（避免极端长度差异）
        len_chunk = len(chunk_text)
        len_outline = len(outline_text)
        if len_chunk > 0 and len_outline > 0:
            len_ratio = min(len_chunk, len_outline) / max(len_chunk, len_outline)
            # 对于大纲通常较短，调整长度相似性计算
            if len_outline < len_chunk * 0.1:  # 大纲很短
                length_score = 0.5  # 给一个中等分数
            else:
                length_score = len_ratio
            scores.append(length_score * 0.2)  # 权重0.2
        
        # 4. 特殊匹配：医学术语和数字标识
        special_score = 0
        # 查找医学相关术语
        medical_terms = re.findall(r'[\u4e00-\u9fff]{2,}(?:症|病|治|疗|方|药|汤|散|丸|膏)', chunk_text + outline_text)
        if medical_terms:
            special_score = 0.1  # 医学文档额外加分
        
        # 查找章节标识
        if re.search(r'[一二三四五六七八九十\d]+[、．.]', outline_text):
            special_score += 0.1  # 章节标识加分
        
        scores.append(special_score * 0.1)  # 权重0.1
        
        # 综合得分
        final_score = sum(scores)
        return final_score
    
    def _recursive_chunk_content(self, content: str, title: str, file_id: int) -> List[Document]:
        """递归分块内容（兼容模式）"""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"🔄 开始递归分块内容 - 文件ID: {file_id}, 标题: {title}")
            logger.info(f"📄 内容长度: {len(content)} 字符")
            
            # 验证输入参数
            if not content or not content.strip():
                logger.error("❌ 内容为空，无法进行递归分块")
                return []
            
            # 进行分块
            logger.info("🔪 开始使用递归字符分割器进行分块...")
            logger.info(f"📋 分割器配置: chunk_size={self.content_splitter.chunk_size}, overlap={self.content_splitter.chunk_overlap}")
            
            try:
                chunks = self.content_splitter.split_text(content)
                logger.info(f"✅ 递归分块完成，共生成 {len(chunks)} 个内容块")
                
                # 验证分块结果
                if not chunks:
                    logger.error("❌ 递归分块结果为空")
                    return []
                
                # 统计分块信息
                total_chars = sum(len(chunk) for chunk in chunks)
                avg_length = total_chars / len(chunks) if chunks else 0
                min_length = min(len(chunk) for chunk in chunks) if chunks else 0
                max_length = max(len(chunk) for chunk in chunks) if chunks else 0
                
                logger.info(f"📊 递归分块统计:")
                logger.info(f"  📏 总字符数: {total_chars}")
                logger.info(f"  📊 平均长度: {avg_length:.0f} 字符")
                logger.info(f"  📉 最小长度: {min_length} 字符")
                logger.info(f"  📈 最大长度: {max_length} 字符")
                logger.info(f"  🔢 分块数量: {len(chunks)}")
                
            except Exception as e:
                logger.error(f"❌ 递归分块过程失败: {e}")
                import traceback
                logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
                return []
            
            # 创建文档对象
            logger.info("🏗️ 开始创建递归分块文档...")
            content_docs = []
            
            for i, chunk in enumerate(chunks):
                try:
                    # 验证内容块
                    if not chunk or not chunk.strip():
                        logger.warning(f"⚠️ 第 {i+1} 个内容块为空，跳过")
                        continue
                    
                    # 创建文档
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
                            "section_path": f"内容块-{i+1}",
                            "vector_model": "recursive_fallback"
                        }
                    )
                    content_docs.append(doc)
                    
                    # 每20个块输出一次进度
                    if (i + 1) % 20 == 0:
                        logger.info(f"📈 递归分块进度: {i+1}/{len(chunks)} 个内容块已处理")
                    
                except Exception as e:
                    logger.error(f"❌ 创建第 {i+1} 个递归分块文档时发生错误: {e}")
                    import traceback
                    logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
                    continue
            
            # 最终统计
            processing_time = time.time() - start_time
            logger.info(f"📊 递归分块最终统计:")
            logger.info(f"  ✅ 成功创建: {len(content_docs)} 个内容文档")
            logger.info(f"  ⏱️ 处理时间: {processing_time:.2f} 秒")
            logger.info(f"  📊 成功率: {len(content_docs)/len(chunks)*100:.1f}%")
            
            # 验证最终结果
            if not content_docs:
                logger.error("❌ 递归分块最终结果为空")
                return []
            
            logger.info(f"🎉 递归分块完成，生成 {len(content_docs)} 个内容块")
            return content_docs
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ 递归分块过程失败 (耗时: {processing_time:.2f}s): {e}")
            import traceback
            logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
            return []
    
    def _fallback_to_simple_chunking(self, content: str, title: str, file_id: int) -> Dict[str, List[Document]]:
        """降级到简单分块（保持兼容性）"""
        import time
        start_time = time.time()
        
        try:
            logger.warning("⚠️ 开始降级到简单分块模式")
            logger.warning(f"📄 文件ID: {file_id}, 标题: {title}")
            logger.warning(f"📏 内容长度: {len(content)} 字符")
            
            # 验证输入参数
            if not content or not content.strip():
                logger.error("❌ 内容为空，无法进行简单分块")
                return {
                    'summary': [],
                    'outline': [],
                    'content': []
                }
            
            # 创建简单摘要块
            logger.info("📝 开始创建简单摘要块...")
            try:
                preview_length = min(500, len(content))
                simple_summary = f"标题：{title}\n内容预览：{content[:preview_length]}..."
                
                if len(content) <= preview_length:
                    simple_summary = f"标题：{title}\n完整内容：{content}"
                
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
                        "generation_method": "fallback",
                        "vector_model": "simple_fallback"
                    }
                )
                
                logger.info(f"✅ 简单摘要块创建成功，长度: {len(simple_summary)} 字符")
                
            except Exception as e:
                logger.error(f"❌ 创建简单摘要块失败: {e}")
                import traceback
                logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
                summary_doc = None
            
            # 创建内容块
            logger.info("🔄 开始创建内容块...")
            try:
                content_docs = self._recursive_chunk_content(content, title, file_id)
                logger.info(f"✅ 内容块创建完成，共 {len(content_docs)} 个")
                
            except Exception as e:
                logger.error(f"❌ 创建内容块失败: {e}")
                import traceback
                logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
                content_docs = []
            
            # 组装结果
            result = {
                'summary': [summary_doc] if summary_doc else [],
                'outline': [],  # 简单分块模式不提供大纲
                'content': content_docs
            }
            
            # 统计结果
            processing_time = time.time() - start_time
            total_docs = len(result['summary']) + len(result['outline']) + len(result['content'])
            
            logger.info(f"📊 简单分块最终统计:")
            logger.info(f"  📝 摘要块: {len(result['summary'])} 个")
            logger.info(f"  📋 大纲块: {len(result['outline'])} 个")
            logger.info(f"  📄 内容块: {len(result['content'])} 个")
            logger.info(f"  📊 总文档数: {total_docs} 个")
            logger.info(f"  ⏱️ 处理时间: {processing_time:.2f} 秒")
            
            # 验证最终结果
            if total_docs == 0:
                logger.error("❌ 简单分块最终结果为空")
                return {
                    'summary': [],
                    'outline': [],
                    'content': []
                }
            
            logger.info(f"🎉 简单分块完成，总共生成 {total_docs} 个文档")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ 简单分块过程失败 (耗时: {processing_time:.2f}s): {e}")
            import traceback
            logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
            
            # 返回空结果
            return {
                'summary': [],
                'outline': [],
                'content': []
            }

# 向后兼容的类名别名
HierarchicalTextSplitter = IntelligentHierarchicalSplitter 