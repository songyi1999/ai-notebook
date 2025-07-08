# LangChain-Chroma版本的AIService

from typing import List, Optional, Dict, Any, AsyncGenerator
import logging
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import requests
import os
import hashlib
import threading
import time
import json
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.file import File
from ..models.embedding import Embedding
from ..models.tag import Tag
from ..dynamic_config import settings
from .mcp_service import MCPClientService
from .simple_memory_service import SimpleMemoryService
from ..schemas.mcp import MCPToolCallRequest

logger = logging.getLogger(__name__)

class OpenAICompatibleEmbeddings(Embeddings):
    """OpenAI兼容的嵌入模型包装器，用于LangChain"""
    
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            if embedding:
                embeddings.append(embedding)
            else:
                # 如果某个文档嵌入失败，用零向量占位
                embeddings.append([0.0] * settings.embedding_dimension)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        embedding = self._get_embedding(text)
        return embedding if embedding else [0.0] * settings.embedding_dimension
    
    def _get_embedding(self, text: str) -> List[float]:
        """使用OpenAI兼容接口获取嵌入向量"""
        try:
            # 确保URL格式正确，避免重复的/v1
            base_url = self.base_url.rstrip('/')
            if base_url.endswith('/v1'):
                url = f"{base_url}/embeddings"
            else:
                url = f"{base_url}/v1/embeddings"
            payload = {
                "model": self.model,
                "input": text,
                "encoding_format": "float"
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "data" in result and result["data"] and len(result["data"]) > 0:
                return result["data"][0]["embedding"]
            else:
                logger.error(f"嵌入响应格式错误: {result}")
                return []
                
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            return []

class ChromaDBManager:
    """ChromaDB单例管理器，避免多实例冲突"""
    _instance = None
    _lock = threading.Lock()
    _vector_store = None
    _embeddings = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChromaDBManager, cls).__new__(cls)
        return cls._instance
    
    def get_vector_store(self):
        """获取向量存储实例"""
        if self._vector_store is None:
            with self._lock:
                if self._vector_store is None:
                    try:
                        # 初始化嵌入模型
                        if self._embeddings is None:
                            self._embeddings = OpenAICompatibleEmbeddings(
                                base_url=settings.get_embedding_base_url(),
                                api_key=settings.get_embedding_api_key(),
                                model=settings.embedding_model_name
                            )
                        
                        # 初始化向量存储
                        self._vector_store = Chroma(
                            collection_name="document_embeddings",
                            embedding_function=self._embeddings,
                            persist_directory=settings.chroma_db_path,
                            collection_metadata={"description": "AI笔记本文档嵌入向量"}
                        )
                        logger.info("ChromaDB单例初始化成功")
                        
                    except Exception as e:
                        logger.error(f"ChromaDB单例初始化失败: {e}")
                        self._vector_store = None
        
        return self._vector_store
    
    def clear_collection(self):
        """清空ChromaDB collection中的所有向量"""
        try:
            if self._vector_store is not None:
                # 获取collection中的所有文档ID
                collection = self._vector_store._collection
                # 删除所有文档
                all_docs = collection.get()
                if all_docs['ids']:
                    collection.delete(ids=all_docs['ids'])
                    logger.info(f"已清空ChromaDB collection，删除了 {len(all_docs['ids'])} 个向量")
                else:
                    logger.info("ChromaDB collection已经为空")
                return True
        except Exception as e:
            logger.error(f"清空ChromaDB collection失败: {e}")
            return False
    
    def reset(self):
        """重置单例（用于测试或重新初始化）"""
        with self._lock:
            self._vector_store = None
            self._embeddings = None

class AIService:
    """AI服务类，使用LangChain-Chroma进行向量存储 - 单例版本"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = settings.openai_api_key
        self.openai_base_url = settings.openai_base_url
        
        # 初始化简化的记忆服务
        self.memory_service = SimpleMemoryService()
        
        # 初始化LLM
        if self.openai_api_key:
            self.llm = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=settings.openai_model
            )
            # 初始化流式LLM
            self.streaming_llm = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=settings.openai_model,
                streaming=True
            )
        else:
            logger.warning("未配置OpenAI API密钥，AI功能将不可用")
            self.llm = None
            self.streaming_llm = None
        
        # 初始化嵌入模型
        self.embeddings = OpenAICompatibleEmbeddings(
            base_url=settings.get_embedding_base_url(),
            api_key=settings.get_embedding_api_key(),
            model=settings.embedding_model_name
        )
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        
        # 使用单例管理器获取向量存储
        self.chroma_manager = ChromaDBManager()
        self.vector_store = self.chroma_manager.get_vector_store()
        
        # 添加查询向量缓存
        self._query_cache = {}
        self._cache_lock = threading.Lock()
        self._max_cache_size = 100  # 最大缓存100个查询
        
        # 初始化MCP服务
        self.mcp_service = MCPClientService(db)

    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        # 检查AI是否在配置中启用
        if not settings.is_ai_enabled():
            return False
        return bool(self.openai_api_key and self.vector_store)

    def clear_all_embeddings(self) -> bool:
        """清空所有向量嵌入"""
        try:
            logger.info("开始清空所有向量嵌入...")
            
            # 清空ChromaDB collection
            success = self.chroma_manager.clear_collection()
            
            if success:
                # 清空SQLite中的嵌入元数据
                from ..models.embedding import Embedding
                deleted_count = self.db.query(Embedding).delete()
                self.db.commit()
                logger.info(f"已清空SQLite中的 {deleted_count} 条嵌入元数据")
                
                logger.info("所有向量嵌入清空完成")
                return True
            else:
                logger.error("清空ChromaDB collection失败")
                return False
                
        except Exception as e:
            logger.error(f"清空向量嵌入失败: {e}")
            self.db.rollback()
            return False

    def create_embeddings(self, file: File, progress_callback=None) -> bool:
        """为文件创建向量嵌入 - 使用智能多层次分块"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法创建嵌入")
            return False
        
        try:
            logger.info(f"开始为文件创建智能嵌入: {file.file_path}")
            
            # 1. 检查是否存在现有的嵌入记录
            existing_embeddings_count = self.db.query(Embedding).filter(Embedding.file_id == file.id).count()
            
            if existing_embeddings_count > 0:
                logger.info(f"文件 {file.id} 存在 {existing_embeddings_count} 个现有嵌入，需要清理")
                
                # 1.1 删除现有的向量存储中的文档（先删除向量存储）
                try:
                    existing_docs = self.vector_store.get(
                        where={"file_id": file.id}
                    )
                    if existing_docs and existing_docs.get('ids'):
                        self.vector_store.delete(ids=existing_docs['ids'])
                        logger.info(f"从LangChain向量存储删除文件 {file.id} 的文档: {len(existing_docs['ids'])} 个")
                except Exception as e:
                    logger.warning(f"删除现有向量存储时出错: {e}")
                
                # 1.2 删除现有的SQLite嵌入记录（然后删除SQLite记录）
                try:
                    deleted_count = self.db.query(Embedding).filter(Embedding.file_id == file.id).delete()
                    self.db.commit()  # 立即提交删除操作
                    logger.info(f"成功删除文件的向量索引: file_id={file.id}, SQLite删除了 {deleted_count} 个记录")
                except Exception as e:
                    logger.warning(f"删除SQLite嵌入记录时出错: {e}")
                    self.db.rollback()
            else:
                logger.info(f"文件 {file.id} 没有现有嵌入，直接创建新的")
                
            # 等待一小段时间确保删除操作完全完成
            import time
            time.sleep(0.1)
            
            # 3. 使用智能多层次分块（每个文件都有汇总提纲）
            logger.info(f"🧠 开始调用智能多层次分块器 - 文件: {file.file_path}")
            documents = self._create_hierarchical_chunks(file, progress_callback)
            logger.info(f"✅ 智能多层次分块完成，共返回 {len(documents)} 个文档")
            
            # 验证分块结果
            if not documents:
                logger.error(f"❌ 智能分块返回空结果，文件: {file.file_path}")
                return False
            
            # 统计分块结果
            doc_types = {}
            for doc in documents:
                chunk_type = doc.metadata.get('chunk_type', 'unknown')
                doc_types[chunk_type] = doc_types.get(chunk_type, 0) + 1
            
            logger.info(f"📊 分块结果统计: {doc_types}")
            
            # 4. 批量添加到向量存储
            if documents:
                if progress_callback:
                    progress_callback("向量存储", f"正在保存 {len(documents)} 个分块到向量数据库")
                
                # 分批处理，避免一次性处理过多文档导致超时
                batch_size = 50  # 每批处理50个文档
                total_docs = len(documents)
                logger.info(f"开始分批向量化，总文档数: {total_docs}, 批大小: {batch_size}")
                
                for i in range(0, total_docs, batch_size):
                    batch_start = i
                    batch_end = min(i + batch_size, total_docs)
                    batch_docs = documents[batch_start:batch_end]
                    
                    try:
                        # 为当前批次生成ID
                        batch_ids = [f"file_{file.id}_chunk_{doc.metadata['chunk_index']}_{doc.metadata['chunk_type']}" for doc in batch_docs]
                        
                        logger.info(f"正在处理第 {i//batch_size + 1} 批，文档 {batch_start+1}-{batch_end}/{total_docs}")
                        
                        if progress_callback:
                            progress_callback("向量存储", f"正在处理第 {i//batch_size + 1} 批 ({batch_start+1}-{batch_end}/{total_docs})")
                        
                        # 保存到ChromaDB
                        self.vector_store.add_documents(batch_docs, ids=batch_ids)
                        logger.info(f"✅ 成功保存第 {i//batch_size + 1} 批到ChromaDB，包含 {len(batch_docs)} 个文档")
                        
                        # 短暂休息，避免过度占用资源
                        import time
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"❌ 保存第 {i//batch_size + 1} 批到ChromaDB失败: {e}")
                        # 如果某批失败，可以考虑继续处理其他批次，或者直接失败
                        self.db.rollback()
                        return False
                
                logger.info(f"🎉 成功添加所有 {len(documents)} 个文档到LangChain-Chroma")
            
            # 5. 提交SQLite事务
            try:
                self.db.commit()
                logger.info(f"✅ SQLite事务提交成功，文件: {file.file_path}")
            except Exception as e:
                logger.error(f"❌ SQLite事务提交失败: {e}")
                self.db.rollback()
                return False
            
            if progress_callback:
                progress_callback("完成", f"智能分块完成，共生成 {len(documents)} 个向量")
            
            logger.info(f"为文件 {file.file_path} 创建了 {len(documents)} 个智能嵌入向量")
            return True
            
        except Exception as e:
            logger.error(f"创建智能嵌入失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.db.rollback()
            return False
    

    
    def _create_hierarchical_chunks(self, file: File, progress_callback=None) -> List[Document]:
        """创建智能多层次分块（基于LLM）"""
        import time
        start_time = time.time()
        
        try:
            from .hierarchical_splitter import IntelligentHierarchicalSplitter
            
            logger.info(f"🧠 开始创建智能多层次分块 - 文件: {file.title}")
            logger.info(f"📄 文件信息: ID={file.id}, 路径={file.file_path}")
            logger.info(f"📏 内容长度: {len(file.content)} 字符")
            
            if progress_callback:
                progress_callback("分析中", f"正在分析文件结构和内容")
            
            # 验证文件内容
            if not file.content or not file.content.strip():
                logger.error(f"❌ 文件内容为空: {file.file_path}")
                return []
            
            # 创建智能分块器，传入LLM实例
            logger.info("🔧 正在初始化智能分块器...")
            splitter = IntelligentHierarchicalSplitter(llm=self.llm)
            
            logger.info("⚙️ 开始调用智能分块器进行文档分析...")
            hierarchical_docs = splitter.split_document(file.content, file.title, file.id, file.file_path, progress_callback)
            
            # 验证分块器返回结果
            if not hierarchical_docs:
                logger.error("❌ 智能分块器返回空结果")
                if progress_callback:
                    progress_callback("降级处理", f"智能分块失败，使用基本分块策略")
                return self._create_basic_fallback_chunks(file, progress_callback)
            
            logger.info(f"✅ 智能分块器完成，返回结构: {list(hierarchical_docs.keys())}")
            
            # 统计各层级文档数量
            summary_count = len(hierarchical_docs.get('summary', []))
            outline_count = len(hierarchical_docs.get('outline', []))
            content_count = len(hierarchical_docs.get('content', []))
            
            logger.info(f"📊 分块器结果统计:")
            logger.info(f"  📝 摘要层: {summary_count} 个文档")
            logger.info(f"  📋 大纲层: {outline_count} 个文档")
            logger.info(f"  📄 内容层: {content_count} 个文档")
            
            all_documents = []
            
            # 处理摘要层
            if progress_callback:
                progress_callback("摘要生成", f"正在处理文件摘要")
            
            logger.info("🏗️ 开始处理摘要层文档...")
            for i, doc in enumerate(hierarchical_docs.get('summary', [])):
                try:
                    all_documents.append(doc)
                    self._save_embedding_metadata(doc, file.id)
                    logger.debug(f"  ✅ 摘要文档 {i+1} 处理完成")
                except Exception as e:
                    logger.error(f"  ❌ 处理摘要文档 {i+1} 失败: {e}")
            
            logger.info(f"✅ 摘要层处理完成，成功处理 {len(hierarchical_docs.get('summary', []))} 个文档")
            
            # 处理大纲层
            if progress_callback:
                progress_callback("大纲提取", f"正在处理文件大纲")
            
            logger.info("🏗️ 开始处理大纲层文档...")
            for i, doc in enumerate(hierarchical_docs.get('outline', [])):
                try:
                    all_documents.append(doc)
                    self._save_embedding_metadata(doc, file.id)
                    logger.debug(f"  ✅ 大纲文档 {i+1} 处理完成")
                except Exception as e:
                    logger.error(f"  ❌ 处理大纲文档 {i+1} 失败: {e}")
            
            logger.info(f"✅ 大纲层处理完成，成功处理 {len(hierarchical_docs.get('outline', []))} 个文档")
            
            # 处理内容层
            if progress_callback:
                progress_callback("内容分块", f"正在处理内容分块")
            
            logger.info("🏗️ 开始处理内容层文档...")
            content_docs = hierarchical_docs.get('content', [])
            processed_content = 0
            
            for i, doc in enumerate(content_docs):
                try:
                    all_documents.append(doc)
                    self._save_embedding_metadata(doc, file.id)
                    processed_content += 1
                    
                    # 每50个文档输出一次进度
                    if (i + 1) % 50 == 0:
                        logger.info(f"  📈 内容层进度: {i+1}/{len(content_docs)} 个文档已处理")
                        
                except Exception as e:
                    logger.error(f"  ❌ 处理内容文档 {i+1} 失败: {e}")
            
            logger.info(f"✅ 内容层处理完成，成功处理 {processed_content}/{len(content_docs)} 个文档")
            
            # 最终统计
            processing_time = time.time() - start_time
            logger.info(f"📊 智能多层次分块最终统计:")
            logger.info(f"  ✅ 总文档数: {len(all_documents)} 个")
            logger.info(f"  📝 摘要文档: {summary_count} 个")
            logger.info(f"  📋 大纲文档: {outline_count} 个")
            logger.info(f"  📄 内容文档: {processed_content} 个")
            logger.info(f"  ⏱️ 处理时间: {processing_time:.2f} 秒")
            
            # 验证最终结果
            if not all_documents:
                logger.error("❌ 智能多层次分块最终结果为空")
                if progress_callback:
                    progress_callback("降级处理", f"智能分块失败，使用基本分块策略")
                return self._create_basic_fallback_chunks(file, progress_callback)
            
            logger.info(f"🎉 智能多层次分块完成: 总共 {len(all_documents)} 个文档")
            return all_documents
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ 创建智能多层次分块失败 (耗时: {processing_time:.2f}s): {e}")
            import traceback
            logger.error(f"📋 错误堆栈: {traceback.format_exc()}")
            
            # 创建最基本的摘要和内容块（降级策略）
            if progress_callback:
                progress_callback("降级处理", f"智能分块失败，使用基本分块策略")
            
            logger.info("🔄 降级到基本分块策略...")
            return self._create_basic_fallback_chunks(file, progress_callback)
    
    def _create_basic_fallback_chunks(self, file: File, progress_callback=None) -> List[Document]:
        """创建基本的降级分块（确保每个文件都有摘要和内容块）"""
        try:
            documents = []
            
            # 1. 创建基本摘要块
            if progress_callback:
                progress_callback("基本摘要", f"创建基本摘要块")
            
            summary_text = f"文件：{file.title}\n内容预览：{file.content[:500]}..."
            summary_doc = Document(
                page_content=summary_text,
                metadata={
                    "file_id": file.id,
                    "file_path": file.file_path,
                    "chunk_index": 0,
                    "chunk_hash": hashlib.sha256(summary_text.encode()).hexdigest(),
                    "title": file.title,
                    "vector_model": settings.embedding_model_name,
                    "chunk_type": "summary",
                    "chunk_level": 1,
                    "parent_heading": None,
                    "section_path": "基本摘要",
                    "generation_method": "basic_fallback"
                }
            )
            documents.append(summary_doc)
            self._save_embedding_metadata(summary_doc, file.id)
            
            # 2. 创建内容块
            if progress_callback:
                progress_callback("内容分块", f"正在创建内容分块")
            
            # 使用文本分割器创建内容块
            content_chunks = self.text_splitter.split_text(file.content)
            
            for i, chunk in enumerate(content_chunks):
                content_doc = Document(
                    page_content=chunk,
                    metadata={
                        "file_id": file.id,
                        "file_path": file.file_path,
                        "chunk_index": i + 1,
                        "chunk_hash": hashlib.sha256(chunk.encode()).hexdigest(),
                        "title": file.title,
                        "vector_model": settings.embedding_model_name,
                        "chunk_type": "content",
                        "chunk_level": 3,
                        "parent_heading": None,
                        "section_path": f"内容块{i+1}",
                        "generation_method": "basic_fallback"
                    }
                )
                documents.append(content_doc)
                self._save_embedding_metadata(content_doc, file.id)
            
            logger.info(f"基本分块完成: 1个摘要块 + {len(content_chunks)}个内容块")
            return documents
            
        except Exception as e:
            logger.error(f"创建基本分块失败: {e}")
            return []

    def _save_embedding_metadata(self, doc: Document, file_id: int):
        """保存嵌入元数据到SQLite"""
        try:
            # 获取vector_model，如果不存在则设置默认值
            vector_model = doc.metadata.get('vector_model', 'unknown')
            
            # 创建嵌入记录
            embedding = Embedding(
                file_id=file_id,
                chunk_index=doc.metadata['chunk_index'],
                chunk_text=doc.page_content,  # 添加缺少的chunk_text字段
                chunk_hash=doc.metadata['chunk_hash'],
                vector_model=vector_model,
                chunk_type=doc.metadata.get('chunk_type', 'content'),
                chunk_level=doc.metadata.get('chunk_level', 1),
                parent_heading=doc.metadata.get('parent_heading'),
                section_path=doc.metadata.get('section_path')
                # 移除了不存在的generation_method字段
            )
            self.db.add(embedding)
            # 不在这里提交，让上层统一提交
            
        except Exception as e:
            logger.error(f"保存嵌入元数据失败: {e}")
            raise

    def semantic_search(self, query: str, limit: int = 10, similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """语义搜索 - 支持多层次检索，带缓存优化"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行语义搜索")
            return []
        
        # 使用配置中的默认阈值
        if similarity_threshold is None:
            similarity_threshold = settings.semantic_search_threshold
        
        try:
            start_time = time.time()
            logger.info(f"开始语义搜索，查询: {query}, 阈值: {similarity_threshold}")
            
            # 检查是否启用多层次检索
            if settings.enable_hierarchical_chunking:
                results = self._hierarchical_semantic_search(query, limit, similarity_threshold)
            else:
                results = self._traditional_semantic_search(query, limit, similarity_threshold)
            
            total_time = time.time() - start_time
            logger.info(f"语义搜索完成，查询: {query}, 结果: {len(results)}, 总耗时: {total_time:.3f}秒")
            return results
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def _traditional_semantic_search(self, query: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """传统语义搜索（保持兼容性）"""
        try:
            # 使用LangChain的similarity_search_with_score方法（带缓存优化）
            search_results = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit * 2,  # 获取更多结果用于过滤
                filter=None  # 可以添加过滤条件
            )
            
            logger.info(f"传统搜索返回 {len(search_results)} 个结果")
            
            # 处理搜索结果并去重
            results = []
            seen_files = {}  # 用于文件去重：file_id -> 最佳匹配结果
            
            for doc, score in search_results:
                # LangChain-Chroma返回的score是距离，距离越小越相似
                distance = score
                
                logger.info(f"文档: {doc.metadata.get('file_path', 'unknown')}, 距离: {distance:.4f}")
                
                # 过滤距离过大的结果（距离小于阈值的保留）
                if distance > similarity_threshold:
                    logger.info(f"距离 {distance:.4f} 大于阈值 {similarity_threshold}，跳过")
                    continue
                
                # 检查文件是否仍然存在且未删除
                file_id = doc.metadata.get('file_id')
                if file_id:
                    file = self.db.query(File).filter(
                        File.id == file_id,
                        File.is_deleted == False
                    ).first()
                    
                    if file:
                        result_item = {
                            'file_id': file_id,
                            'file_path': doc.metadata.get('file_path', ''),
                            'title': doc.metadata.get('title', ''),
                            'chunk_text': doc.page_content,
                            'chunk_index': doc.metadata.get('chunk_index', 0),
                            'similarity': float(1 - distance),  # 为兼容性转换为相似度（1-距离）
                            'distance': float(distance),  # 保存原始距离用于比较
                            'created_at': file.created_at.isoformat() if file.created_at else None,
                            'updated_at': file.updated_at.isoformat() if file.updated_at else None,
                        }
                        
                        # 文件去重：保留每个文件的最佳匹配（距离最小）
                        if file_id not in seen_files or distance < seen_files[file_id]['distance']:
                            seen_files[file_id] = result_item
                            logger.info(f"添加/更新最佳匹配: {doc.metadata.get('file_path')}, 距离: {distance:.4f}")
                        else:
                            logger.info(f"跳过重复文件（距离更大）: {doc.metadata.get('file_path')}, 距离: {distance:.4f}")
                    else:
                        logger.info(f"文件不存在或已删除: file_id={file_id}")
            
            # 将去重后的结果转换为列表，按距离排序
            results = list(seen_files.values())
            results.sort(key=lambda x: x['distance'])  # 按距离升序排序（最相似的在前）
            
            # 移除临时的distance字段，限制结果数量
            for result in results[:limit]:
                result.pop('distance', None)
            
            return results
            
        except Exception as e:
            logger.error(f"传统语义搜索失败: {e}")
            return []
    
    def _hierarchical_semantic_search(self, query: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """多层次语义搜索"""
        try:
            logger.info(f"开始多层次语义搜索: {query}")
            
            # 多路召回：同时搜索三个层次
            summary_results = self._search_by_chunk_type(query, "summary", limit//3, similarity_threshold)
            outline_results = self._search_by_chunk_type(query, "outline", limit//3, similarity_threshold)
            content_results = self._search_by_chunk_type(query, "content", limit, similarity_threshold)
            
            # 记录每层级的详细匹配内容
            logger.info(f"📝 摘要层匹配结果 ({len(summary_results)} 个):")
            for i, result in enumerate(summary_results, 1):
                logger.info(f"   {i}. 文件: {result.get('title', 'Unknown')} (相似度: {result.get('similarity', 0):.3f})")
                logger.info(f"      摘要内容: {result.get('chunk_text', '')[:200]}...")
            
            logger.info(f"📋 大纲层匹配结果 ({len(outline_results)} 个):")
            for i, result in enumerate(outline_results, 1):
                logger.info(f"   {i}. 文件: {result.get('title', 'Unknown')} (相似度: {result.get('similarity', 0):.3f})")
                logger.info(f"      大纲内容: {result.get('chunk_text', '')[:200]}...")
            
            logger.info(f"📄 内容层匹配结果 ({len(content_results)} 个):")
            for i, result in enumerate(content_results, 1):
                logger.info(f"   {i}. 文件: {result.get('title', 'Unknown')} (相似度: {result.get('similarity', 0):.3f})")
                logger.info(f"      内容片段: {result.get('chunk_text', '')[:200]}...")
            
            # 智能上下文扩展
            expanded_results = []
            
            # 处理摘要匹配结果
            for result in summary_results:
                expanded_results.append(result)
                # 获取该文件的大纲和内容
                file_outline = self._get_file_outline(result['file_id'])
                expanded_results.extend(file_outline[:2])  # 添加前2个大纲项
            
            # 处理大纲匹配结果
            for result in outline_results:
                expanded_results.append(result)
                # 获取该章节下的内容块
                section_content = self._get_section_content(result['file_id'], result.get('section_path'))
                expanded_results.extend(section_content[:2])  # 添加前2个内容块
            
            # 处理内容匹配结果
            expanded_results.extend(content_results)
            
            # 去重并限制结果数量
            final_results = self._deduplicate_and_rank(expanded_results, limit)
            
            # 记录最终构建的上下文
            logger.info(f"🔧 最终构建的搜索上下文:")
            total_context_length = 0
            for i, result in enumerate(final_results, 1):
                chunk_text = result.get('chunk_text', '')
                total_context_length += len(chunk_text)
                logger.info(f"   {i}. [{result.get('chunk_type', 'content')}] {result.get('title', 'Unknown')} - {len(chunk_text)} 字符")
                logger.info(f"      预览: {chunk_text[:150]}..." if len(chunk_text) > 150 else f"      内容: {chunk_text}")
            
            logger.info(f"📊 上下文统计: 总长度={total_context_length} 字符, 片段数={len(final_results)}")
            logger.info(f"多层次搜索完成: 摘要={len(summary_results)}, 大纲={len(outline_results)}, 内容={len(content_results)}, 最终={len(final_results)}")
            return final_results
            
        except Exception as e:
            logger.error(f"多层次语义搜索失败: {e}")
            # 降级到传统搜索
            return self._traditional_semantic_search(query, limit, similarity_threshold)
    
    def _search_by_chunk_type(self, query: str, chunk_type: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """按分块类型搜索"""
        try:
            logger.info(f"🔍 开始按类型搜索: {chunk_type}, 查询: '{query}', 阈值: {similarity_threshold}")
            
            search_results = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit * 2,
                filter={"chunk_type": chunk_type}
            )
            
            logger.info(f"📊 向量数据库返回 {len(search_results)} 个 {chunk_type} 类型的原始结果")
            
            results = []
            filtered_count = 0
            
            for i, (doc, score) in enumerate(search_results, 1):
                distance = score
                similarity = 1 - distance
                
                logger.info(f"   原始结果 {i}: 距离={distance:.4f}, 相似度={similarity:.4f}, 文件={doc.metadata.get('title', 'Unknown')}")
                logger.info(f"     内容预览: {doc.page_content[:100]}...")
                
                if score <= similarity_threshold:
                    file_id = doc.metadata.get('file_id')
                    if file_id:
                        file = self.db.query(File).filter(
                            File.id == file_id,
                            File.is_deleted == False
                        ).first()
                        
                        if file:
                            result_item = {
                                'file_id': file_id,
                                'file_path': doc.metadata.get('file_path', ''),
                                'title': doc.metadata.get('title', ''),
                                'chunk_text': doc.page_content,
                                'chunk_index': doc.metadata.get('chunk_index', 0),
                                'chunk_type': chunk_type,
                                'chunk_level': doc.metadata.get('chunk_level', 3),
                                'parent_heading': doc.metadata.get('parent_heading'),
                                'section_path': doc.metadata.get('section_path'),
                                'similarity': float(similarity),
                                'created_at': file.created_at.isoformat() if file.created_at else None,
                                'updated_at': file.updated_at.isoformat() if file.updated_at else None,
                            }
                            results.append(result_item)
                            logger.info(f"     ✅ 通过阈值筛选，加入结果列表")
                        else:
                            logger.info(f"     ❌ 文件不存在或已删除: file_id={file_id}")
                else:
                    filtered_count += 1
                    logger.info(f"     ❌ 未通过阈值筛选 (距离 {distance:.4f} > {similarity_threshold})")
            
            final_results = results[:limit]
            logger.info(f"🎯 {chunk_type} 搜索完成: 原始={len(search_results)}, 过滤={filtered_count}, 通过={len(results)}, 最终={len(final_results)}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"按类型搜索失败 ({chunk_type}): {e}")
            return []
    
    def _get_file_outline(self, file_id: int) -> List[Dict[str, Any]]:
        """获取文件的大纲"""
        try:
            # 从向量存储中获取该文件的outline类型文档 - 使用正确的ChromaDB查询语法
            docs = self.vector_store.get(
                where={
                    "$and": [
                        {"file_id": {"$eq": file_id}},
                        {"chunk_type": {"$eq": "outline"}}
                    ]
                },
                limit=10
            )
            
            results = []
            if docs and docs.get('documents'):
                for i, doc_content in enumerate(docs['documents']):
                    metadata = docs['metadatas'][i]
                    result_item = {
                        'file_id': file_id,
                        'file_path': metadata.get('file_path', ''),
                        'title': metadata.get('title', ''),
                        'chunk_text': doc_content,
                        'chunk_index': metadata.get('chunk_index', 0),
                        'chunk_type': 'outline',
                        'chunk_level': 2,
                        'parent_heading': metadata.get('parent_heading'),
                        'section_path': metadata.get('section_path'),
                        'similarity': 0.8,  # 上下文相关性
                    }
                    results.append(result_item)
            
            return results
            
        except Exception as e:
            logger.error(f"获取文件大纲失败: {e}")
            return []
    
    def _get_section_content(self, file_id: int, section_path: str) -> List[Dict[str, Any]]:
        """获取章节内容"""
        try:
            # 从向量存储中获取该章节的内容 - 使用正确的ChromaDB查询语法
            docs = self.vector_store.get(
                where={
                    "$and": [
                        {"file_id": {"$eq": file_id}},
                        {"chunk_type": {"$eq": "content"}},
                        {"parent_heading": {"$eq": section_path}}
                    ]
                },
                limit=5
            )
            
            results = []
            if docs and docs.get('documents'):
                for i, doc_content in enumerate(docs['documents']):
                    metadata = docs['metadatas'][i]
                    result_item = {
                        'file_id': file_id,
                        'file_path': metadata.get('file_path', ''),
                        'title': metadata.get('title', ''),
                        'chunk_text': doc_content,
                        'chunk_index': metadata.get('chunk_index', 0),
                        'chunk_type': 'content',
                        'chunk_level': 3,
                        'parent_heading': metadata.get('parent_heading'),
                        'section_path': metadata.get('section_path'),
                        'similarity': 0.7,  # 上下文相关性
                    }
                    results.append(result_item)
            
            return results
            
        except Exception as e:
            logger.error(f"获取章节内容失败: {e}")
            return []
    
    def _deduplicate_and_rank(self, results: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """去重并排序"""
        seen_chunks = set()
        unique_results = []
        
        for result in results:
            chunk_key = (result['file_id'], result['chunk_index'], result.get('chunk_type', 'content'))
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                unique_results.append(result)
        
        # 按相似度排序
        unique_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        return unique_results[:limit]

    def clear_vector_database(self) -> bool:
        """清空向量数据库"""
        try:
            # 1. 清空SQLite中的嵌入向量
            self.db.query(Embedding).delete()
            self.db.commit()
            
            # 2. 清空LangChain向量存储
            if self.vector_store:
                try:
                    # 获取所有文档ID并删除
                    all_docs = self.vector_store.get()
                    if all_docs and all_docs.get('ids'):
                        self.vector_store.delete(ids=all_docs['ids'])
                        logger.info(f"清空LangChain向量存储，删除了 {len(all_docs['ids'])} 个文档")
                except Exception as e:
                    logger.warning(f"清空LangChain向量存储时出错: {e}")
            
            logger.info("向量数据库已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空向量数据库失败: {e}")
            self.db.rollback()
            return False

    def delete_document_by_file_path(self, file_path: str) -> bool:
        """根据文件路径删除文档的向量索引"""
        try:
            # 根据文件路径查找文件
            file = self.db.query(File).filter(File.file_path == file_path).first()
            if not file:
                logger.warning(f"文件不存在，无法删除向量索引: {file_path}")
                return False
            
            return self.delete_document_by_file_id(file.id)
            
        except Exception as e:
            logger.error(f"删除文件向量索引失败: {file_path}, 错误: {e}")
            return False

    def delete_document_by_file_id(self, file_id: int) -> bool:
        """根据文件ID删除文档的向量索引"""
        try:
            # 1. 删除SQLite中的嵌入记录
            deleted_count = self.db.query(Embedding).filter(Embedding.file_id == file_id).delete()
            
            # 2. 删除LangChain向量存储中的文档
            if self.vector_store:
                try:
                    existing_docs = self.vector_store.get(
                        where={"file_id": file_id}
                    )
                    if existing_docs and existing_docs.get('ids'):
                        self.vector_store.delete(ids=existing_docs['ids'])
                        logger.info(f"从LangChain向量存储删除文件 {file_id} 的文档: {len(existing_docs['ids'])} 个")
                except Exception as e:
                    logger.warning(f"从LangChain向量存储删除文档时出错: {e}")
            
            self.db.commit()
            logger.info(f"成功删除文件的向量索引: file_id={file_id}, SQLite删除了 {deleted_count} 个记录")
            return True
            
        except Exception as e:
            logger.error(f"删除文件向量索引失败: file_id={file_id}, 错误: {e}")
            self.db.rollback()
            return False

    def get_vector_count(self) -> int:
        """获取向量数据库中的向量数量 - 优化版本，避免获取所有数据"""
        try:
            if self.vector_store:
                # 使用ChromaDB的count方法，避免获取所有数据
                try:
                    # 尝试使用ChromaDB的内部方法获取数量
                    collection = self.vector_store._collection
                    if hasattr(collection, 'count'):
                        return collection.count()
                    elif hasattr(collection, '_count'):
                        return collection._count()
                    else:
                        # 如果没有直接的count方法，使用limit=1的查询来检查是否有数据
                        # 这样避免获取所有数据
                        sample = self.vector_store.get(limit=1)
                        if sample and sample.get('ids'):
                            # 有数据但无法获取精确数量，返回估算值
                            return -1  # 使用-1表示"有数据但数量未知"
                        else:
                            return 0
                except Exception as e:
                    logger.warning(f"无法获取精确向量数量: {e}")
                    # 降级方案：尝试简单查询检查是否有数据
                    try:
                        sample = self.vector_store.get(limit=1)
                        return -1 if sample and sample.get('ids') else 0
                    except:
                        return 0
            return 0
        except Exception as e:
            logger.error(f"获取向量数量失败: {e}")
            return 0

    def add_document_to_vector_db(self, file_id: int, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """向向量数据库添加文档"""
        try:
            # 获取文件对象
            file = self.db.query(File).filter(File.id == file_id).first()
            if not file:
                logger.error(f"文件不存在: {file_id}")
                return False
            
            # 创建嵌入向量
            success = self.create_embeddings(file)
            if success:
                logger.info(f"文档已添加到向量数据库: {title}")
            return success
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            return False

    def update_file_path_in_vectors(self, file_id: int, old_path: str, new_path: str, new_title: str) -> bool:
        """更新向量数据库中文件的路径信息"""
        try:
            if not self.vector_store:
                logger.warning("向量存储不可用，无法更新文件路径")
                return False
            
            logger.info(f"开始更新向量数据库中的文件路径: {old_path} -> {new_path}")
            
            # 1. 获取该文件的所有向量文档
            existing_docs = self.vector_store.get(
                where={"file_id": file_id}
            )
            
            if not existing_docs or not existing_docs.get('ids'):
                logger.warning(f"未找到文件 {file_id} 的向量数据")
                return True  # 没有向量数据也算成功
            
            # 2. 收集需要更新的文档信息
            doc_ids = existing_docs['ids']
            metadatas = existing_docs['metadatas']
            embeddings = existing_docs['embeddings']
            documents = existing_docs['documents']
            
            logger.info(f"找到 {len(doc_ids)} 个向量文档需要更新")
            
            # 3. 删除旧的文档
            self.vector_store.delete(ids=doc_ids)
            logger.info(f"删除了旧的向量文档: {len(doc_ids)} 个")
            
            # 4. 更新元数据并重新添加
            updated_documents = []
            updated_ids = []
            
            for i, (doc_id, metadata, embedding, document_content) in enumerate(zip(doc_ids, metadatas, embeddings, documents)):
                # 更新元数据中的文件路径和标题
                metadata['file_path'] = new_path
                metadata['title'] = new_title
                
                # 创建新的文档对象
                doc = Document(
                    page_content=document_content,
                    metadata=metadata
                )
                updated_documents.append(doc)
                updated_ids.append(doc_id)
            
            # 5. 重新添加文档（使用预计算的嵌入向量）
            self.vector_store.add_documents(
                documents=updated_documents,
                ids=updated_ids
            )
            
            logger.info(f"成功更新 {len(updated_documents)} 个向量文档的路径信息")
            return True
            
        except Exception as e:
            logger.error(f"更新向量数据库文件路径失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def generate_summary(self, content: str, max_length: int = 200) -> Optional[str]:
        """生成文档摘要"""
        if not self.llm:
            logger.warning("LLM不可用，无法生成摘要")
            return None
        
        try:
            prompt = f"""请为以下内容生成一个简洁的摘要，不超过{max_length}字：

内容：
{content[:2000]}  # 限制输入长度

摘要："""
            
            response = self.llm.invoke(prompt)
            summary = response.content.strip()
            
            logger.info(f"摘要生成成功，长度: {len(summary)}")
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return None

    def generate_outline(self, content: str, max_items: int = 10) -> Optional[str]:
        """生成文档提纲"""
        if not self.llm:
            logger.warning("LLM不可用，无法生成提纲")
            return None
        
        try:
            prompt = f"""请为以下内容生成一个清晰的提纲，包含主要章节和要点，不超过{max_items}个要点：

内容：
{content[:3000]}  # 限制输入长度

要求：
1. 提取主要章节和关键要点
2. 使用层级结构（如：一、二、三... 或 1. 2. 3...）
3. 保持逻辑清晰，结构合理
4. 每个要点简洁明了

提纲："""
            
            response = self.llm.invoke(prompt)
            outline = response.content.strip()
            
            newline_count = outline.count('\n')
            logger.info(f"提纲生成成功，包含 {newline_count} 行")
            return outline
            
        except Exception as e:
            logger.error(f"生成提纲失败: {e}")
            return None

    def suggest_tags(self, title: str, content: str, max_tags: int = 5) -> List[str]:
        """智能标签建议 - 支持多层次分析，从预设和数据库现有标签中选择"""
        if not self.llm:
            logger.warning("LLM不可用，无法生成标签建议")
            return []
        
        try:
            # 1. 定义预设的常规标签
            predefined_tags = [
                "重点", "前端", "后端", "AI大模型", "技巧", 
                "笔记", "总结", "教程", "文档", "配置",
                "问题", "解决方案", "代码", "工具", "框架",
                "数据库", "网络", "安全", "性能", "测试",
                "部署", "运维", "算法", "架构", "设计",
                "学习", "资源", "参考", "示例", "模板"
            ]
            
            # 2. 从数据库获取现有的不重复标签
            existing_tags = []
            try:
                # 使用 distinct 或 group by 获取不重复的标签名称，按使用次数降序排列
                db_tags = self.db.query(Tag.name).filter(Tag.name.isnot(None)).distinct().order_by(Tag.usage_count.desc()).limit(50).all()
                existing_tags = [tag.name for tag in db_tags if tag.name]
                logger.info(f"从数据库获取到 {len(existing_tags)} 个现有标签")
            except Exception as e:
                logger.warning(f"获取数据库标签失败: {e}")
            
            # 3. 合并候选标签，去重并保持顺序
            candidate_tags = []
            seen = set()
            
            # 先添加预设标签
            for tag in predefined_tags:
                if tag not in seen:
                    candidate_tags.append(tag)
                    seen.add(tag)
            
            # 再添加数据库中的现有标签
            for tag in existing_tags:
                if tag not in seen:
                    candidate_tags.append(tag)
                    seen.add(tag)
            
            logger.info(f"总共有 {len(candidate_tags)} 个候选标签")
            
            # 4. 准备分析内容（支持多层次分析）
            analysis_content = self._prepare_content_for_tagging(title, content)
            
            # 5. 构建提示词，要求从候选标签中选择
            candidate_tags_text = "、".join(candidate_tags)
            
            prompt = f"""请从以下候选标签中选择最多{max_tags}个最适合的标签来标记下面的文档。

**候选标签列表：**
{candidate_tags_text}

**文档信息：**
{analysis_content}

**要求：**
1. 只能从上述候选标签列表中选择，不要创造新标签
2. 选择最相关的{max_tags}个标签
3. 标签要准确反映文档的主要内容和特征
4. 每行返回一个标签名称

**返回格式：**
请只返回选中的标签，每行一个："""
            
            response = self.llm.invoke(prompt)
            tags_text = response.content.strip()
            
            # 解析标签并验证
            suggested_tags = [tag.strip() for tag in tags_text.split('\n') if tag.strip()]
            
            # 过滤：只保留在候选标签中的标签
            valid_tags = []
            for tag in suggested_tags[:max_tags]:
                if tag in candidate_tags:
                    valid_tags.append(tag)
                else:
                    logger.warning(f"LLM返回了不在候选列表中的标签: {tag}")
            
            # 如果有效标签太少，从候选标签中补充一些通用标签
            if len(valid_tags) < max_tags and len(valid_tags) < 3:
                # 添加一些通用的后备标签
                fallback_tags = ["笔记", "文档", "重点"]
                for fallback in fallback_tags:
                    if fallback in candidate_tags and fallback not in valid_tags and len(valid_tags) < max_tags:
                        valid_tags.append(fallback)
            
            logger.info(f"标签建议生成成功: {valid_tags} (从 {len(candidate_tags)} 个候选标签中选择)")
            return valid_tags
            
        except Exception as e:
            logger.error(f"生成标签建议失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def _prepare_content_for_tagging(self, title: str, content: str) -> str:
        """为标签生成准备分析内容"""
        if settings.enable_hierarchical_chunking:
            # 多层次模式：提取关键信息
            summary = self._generate_file_summary_for_linking(content, title)
            
            # 提取可能的章节标题
            from .hierarchical_splitter import HierarchicalTextSplitter
            splitter = HierarchicalTextSplitter()
            structure = splitter._extract_document_structure(content)
            
            sections = []
            for item in structure[:5]:  # 最多5个章节
                sections.append(item.get('heading', ''))
            
            analysis_parts = [
                f"标题：{title}",
                f"文档摘要：{summary[:500]}",
            ]
            
            if sections:
                analysis_parts.append(f"主要章节：{', '.join(sections)}")
            
            analysis_parts.append(f"内容片段：{content[:800]}")
            
            return "\n\n".join(analysis_parts)
        else:
            # 传统模式
            return f"标题：{title}\n内容：{content[:1000]}"

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """内容分析"""
        if not self.llm:
            logger.warning("LLM不可用，无法分析内容")
            return {}
        
        try:
            prompt = f"""请分析以下内容，提供以下信息：
1. 主要话题
2. 内容类型（技术文档、笔记、总结等）
3. 重要性评分（1-10）
4. 建议的处理方式

内容：
{content[:1500]}

请以JSON格式返回分析结果。"""
            
            response = self.llm.invoke(prompt)
            # 这里应该解析JSON响应，为简化直接返回文本
            
            analysis = {
                "raw_response": response.content,
                "analyzed": True
            }
            
            logger.info("内容分析完成")
            return analysis
            
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            return {}

    def generate_related_questions(self, content: str, num_questions: int = 3) -> List[str]:
        """生成相关问题"""
        if not self.llm:
            logger.warning("LLM不可用，无法生成相关问题")
            return []
        
        try:
            prompt = f"""基于以下内容，生成{num_questions}个相关的问题，这些问题应该能够帮助用户更深入地理解内容：

内容：
{content[:1500]}

请只返回问题列表，每行一个问题："""
            
            response = self.llm.invoke(prompt)
            questions_text = response.content.strip()
            
            # 解析问题
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            questions = questions[:num_questions]  # 限制数量
            
            logger.info(f"相关问题生成成功: {questions}")
            return questions
            
        except Exception as e:
            logger.error(f"生成相关问题失败: {e}")
            return []

    def discover_smart_links(self, file_id: int, content: str, title: str) -> List[Dict[str, Any]]:
        """智能链接发现 - 支持多层次链接发现"""
        if not self.llm:
            logger.warning("LLM不可用，无法发现智能链接")
            return []
        
        try:
            logger.info(f"开始智能链接发现: {title}")
            
            # 检查是否启用多层次模式
            if settings.enable_hierarchical_chunking:
                return self._hierarchical_smart_links(file_id, content, title)
            else:
                return self._traditional_smart_links(file_id, content, title)
            
        except Exception as e:
            logger.error(f"智能链接发现失败: {e}")
            return []
    
    def _traditional_smart_links(self, file_id: int, content: str, title: str) -> List[Dict[str, Any]]:
        """传统智能链接发现（保持兼容性）"""
        try:
            # 先通过语义搜索找到相关文档 - 智能链接使用更高的阈值确保链接质量
            link_threshold = max(settings.semantic_search_threshold + 0.2, 0.6)  # 至少0.6，确保链接质量
            related_results = self.semantic_search(content[:500], limit=5, similarity_threshold=link_threshold)
            
            if not related_results:
                logger.info("未找到相关文档，无法生成智能链接")
                return []
            
            # 构建相关文档信息
            files_text = ""
            for result in related_results:
                if result['file_id'] != file_id:  # 排除自己
                    files_text += f"文件ID: {result['file_id']}, 标题: {result['title']}, 路径: {result['file_path']}\n"
            
            if not files_text:
                logger.info("没有其他相关文档，无法生成智能链接")
                return []
            
            return self._generate_links_with_llm(file_id, content, title, files_text, related_results)
            
        except Exception as e:
            logger.error(f"传统智能链接发现失败: {e}")
            return []
    
    def _hierarchical_smart_links(self, file_id: int, content: str, title: str) -> List[Dict[str, Any]]:
        """多层次智能链接发现"""
        try:
            logger.info(f"开始多层次链接发现: {title}")
            
            # Step 1: 生成当前文件的摘要用于比较
            current_summary = self._generate_file_summary_for_linking(content, title)
            
            # Step 2: 从摘要层搜索相关文件（文件级别的关联）
            summary_results = self._search_by_chunk_type(current_summary, "summary", 10, 0.8)
            
            # Step 3: 从大纲层搜索相关章节（章节级别的关联）
            outline_results = self._search_by_chunk_type(content[:800], "outline", 8, 0.7)
            
            # Step 4: 智能链接分析
            candidate_files = {}
            
            # 处理文件级别的关联（摘要层匹配）
            for result in summary_results:
                if result['file_id'] != file_id:
                    candidate_files[result['file_id']] = {
                        'file_id': result['file_id'],
                        'title': result['title'],
                        'file_path': result['file_path'],
                        'link_level': 'file',  # 文件级别关联
                        'similarity': result['similarity'],
                        'match_type': 'summary',
                        'match_content': result['chunk_text']
                    }
            
            # 处理章节级别的关联（大纲层匹配）
            for result in outline_results:
                if result['file_id'] != file_id:
                    file_id_key = result['file_id']
                    if file_id_key in candidate_files:
                        # 如果已经有文件级别的关联，升级为章节级别
                        candidate_files[file_id_key]['link_level'] = 'section'
                        candidate_files[file_id_key]['section_info'] = {
                            'section_path': result.get('section_path'),
                            'parent_heading': result.get('parent_heading'),
                            'section_similarity': result['similarity']
                        }
                    else:
                        # 新的章节级别关联
                        candidate_files[file_id_key] = {
                            'file_id': result['file_id'],
                            'title': result['title'],
                            'file_path': result['file_path'],
                            'link_level': 'section',
                            'similarity': result['similarity'],
                            'match_type': 'outline',
                            'match_content': result['chunk_text'],
                            'section_info': {
                                'section_path': result.get('section_path'),
                                'parent_heading': result.get('parent_heading'),
                                'section_similarity': result['similarity']
                            }
                        }
            
            if not candidate_files:
                logger.info("未找到候选关联文件")
                return []
            
            # Step 5: 构建文件信息用于LLM分析
            files_info = []
            for file_info in candidate_files.values():
                if file_info['link_level'] == 'file':
                    files_info.append(f"文件ID: {file_info['file_id']}, 标题: {file_info['title']}, 路径: {file_info['file_path']}, 关联级别: 文件级(整体相关), 相似度: {file_info['similarity']:.2f}")
                elif file_info['link_level'] == 'section':
                    section_path = file_info.get('section_info', {}).get('section_path', '未知章节')
                    files_info.append(f"文件ID: {file_info['file_id']}, 标题: {file_info['title']}, 路径: {file_info['file_path']}, 关联级别: 章节级({section_path}), 相似度: {file_info['similarity']:.2f}")
            
            files_text = "\n".join(files_info)
            
            # Step 6: 使用LLM生成智能链接
            smart_links = self._generate_enhanced_links_with_llm(file_id, content, title, files_text, list(candidate_files.values()))
            
            logger.info(f"多层次链接发现完成: 找到 {len(smart_links)} 个智能链接")
            return smart_links
            
        except Exception as e:
            logger.error(f"多层次智能链接发现失败: {e}")
            # 降级到传统方法
            return self._traditional_smart_links(file_id, content, title)
    
    def _generate_file_summary_for_linking(self, content: str, title: str) -> str:
        """为链接发现生成文件摘要"""
        # 生成简洁的文件摘要用于文件级别的关联判断
        summary_parts = [f"标题: {title}"]
        
        # 提取前几段重要内容
        lines = content.split('\n')
        important_lines = []
        char_count = 0
        max_chars = 800
        
        for line in lines:
            line = line.strip()
            if line and char_count < max_chars:
                important_lines.append(line)
                char_count += len(line)
            if char_count >= max_chars:
                break
        
        summary_parts.extend(important_lines)
        return '\n'.join(summary_parts)
    
    def _generate_links_with_llm(self, file_id: int, content: str, title: str, files_text: str, related_results: List[Dict]) -> List[Dict[str, Any]]:
        """使用LLM生成传统智能链接"""
        try:
            prompt = f"""当前文档：
标题：{title}
内容：{content[:500]}

相关文档：
{files_text}

请分析当前文档与这些相关文档之间的关系类型，并为每个建议的链接提供以下信息：
1. 链接类型（reference/related/follow_up/prerequisite/example/contradiction）
2. 链接理由（简短说明为什么要建立这个链接）
3. 建议的链接文本

请以JSON格式返回，格式如下：
[
    {{
        "target_file_id": 文件ID,
        "link_type": "链接类型",
        "reason": "链接理由",
        "suggested_text": "建议的链接文本"
    }}
]

只返回JSON，不要其他文字："""
            
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # 尝试解析JSON
            import json
            try:
                smart_links = json.loads(result_text)
                logger.info(f"智能链接生成成功: {len(smart_links)} 个链接")
                return smart_links
            except json.JSONDecodeError as e:
                logger.error(f"解析智能链接JSON失败: {e}")
                return []
                
        except Exception as e:
            logger.error(f"LLM生成链接失败: {e}")
            return []
    
    def _generate_enhanced_links_with_llm(self, file_id: int, content: str, title: str, files_text: str, candidate_files: List[Dict]) -> List[Dict[str, Any]]:
        """使用LLM生成增强的多层次智能链接"""
        try:
            prompt = f"""当前文档：
标题：{title}
内容：{content[:600]}

候选关联文档（包含关联级别和相似度）：
{files_text}

请基于多层次关联分析，为每个候选文档评估是否应该建立链接，以及链接的类型和强度。

关联级别说明：
- 文件级：整个文档在主题或内容上相关
- 章节级：特定章节或主题相关

请为每个建议的链接提供：
1. 链接类型（reference/related/follow_up/prerequisite/example/contradiction/complement）
2. 链接强度（strong/medium/weak）
3. 链接理由（详细说明关联原因和关联级别）
4. 建议的链接文本
5. 是否推荐建立链接（true/false）

请以JSON格式返回，格式如下：
[
    {{
        "target_file_id": 文件ID,
        "link_type": "链接类型",
        "link_strength": "链接强度",
        "reason": "链接理由",
        "suggested_text": "建议的链接文本",
        "recommended": true或false
    }}
]

只返回JSON，不要其他文字："""
            
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # 尝试解析JSON
            import json
            try:
                smart_links = json.loads(result_text)
                # 只返回推荐的链接
                recommended_links = [link for link in smart_links if link.get('recommended', False)]
                logger.info(f"增强智能链接生成成功: {len(recommended_links)} 个推荐链接（从 {len(smart_links)} 个候选中筛选）")
                return recommended_links
            except json.JSONDecodeError as e:
                logger.error(f"解析增强智能链接JSON失败: {e}")
                return []
                
        except Exception as e:
            logger.error(f"LLM生成增强链接失败: {e}")
            return []

    def _get_cached_query_embedding(self, query: str) -> List[float]:
        """获取缓存的查询向量"""
        with self._cache_lock:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            
            if query_hash in self._query_cache:
                logger.info(f"使用缓存的查询向量: {query[:50]}...")
                return self._query_cache[query_hash]
            
            # 生成新的查询向量
            embedding = self.embeddings.embed_query(query)
            
            # 缓存管理：如果缓存过大，清理最旧的条目
            if len(self._query_cache) >= self._max_cache_size:
                # 简单的FIFO清理策略
                oldest_key = next(iter(self._query_cache))
                del self._query_cache[oldest_key]
                logger.info(f"查询向量缓存已满，清理最旧条目")
            
            self._query_cache[query_hash] = embedding
            logger.info(f"生成并缓存新的查询向量: {query[:50]}...")
            return embedding

    def _build_smart_prompt(self, question: str, context: str, messages: List[Dict] = None) -> str:
        """构建智能提示词，根据上下文内容决定策略，集成用户记忆"""
        # 获取用户记忆作为背景信息
        memory_context = ""
        try:
            memory_context = self.memory_service.format_memories_for_prompt(limit=8)
            if memory_context.strip():
                logger.info(f"🧠 记忆服务提供背景信息: {len(memory_context)} 字符")
                logger.info(f"🧠 记忆内容预览: {memory_context[:200]}...")
            else:
                logger.info("🧠 记忆服务: 未找到相关记忆")
        except Exception as e:
            logger.warning(f"获取用户记忆失败: {e}")
        
        if messages and len(messages) > 1:
            # 有对话历史的情况
            if context.strip():
                return f"""你是一个智能助手，拥有用户的历史记忆，可以基于用户笔记内容回答问题，也可以使用工具获取实时信息。请根据以下信息来回答用户的问题。

{memory_context}相关文档内容：
{context}

请根据上述信息和对话历史回答用户的问题。要求：
1. 优先结合用户记忆信息，提供个性化回答
2. 基于提供的文档内容回答问题
3. 如果文档内容不足，可以使用可用的工具获取额外信息
4. 回答要准确、有用，简洁明了
5. 如果引用文档内容，请说明来源
6. 保持对话的连贯性和个性化
7. 根据用户的偏好和习惯调整回答风格"""
            else:
                return f"""你是一个智能助手，可以回答各种问题并使用工具获取实时信息。当前没有找到相关的笔记内容，但你可以使用可用的工具来回答用户问题。

{memory_context}请根据对话历史回答用户的问题。要求：
1. 如果问题需要实时信息（如天气、地图等），请使用相应的工具
2. 回答要准确、有用，简洁明了
3. 如果使用工具获取信息，请整合工具结果提供完整回答
4. 请结合之前的对话历史，保持对话的连贯性
5. 如果无法通过工具获取所需信息，请诚实说明
6. 根据用户背景信息提供个性化回答"""
        else:
            # 没有对话历史的情况
            if context.strip():
                return f"""你是一个智能助手，可以基于用户笔记内容回答问题，也可以使用工具获取实时信息。请根据以下相关文档内容来回答用户的问题。

用户问题：{question}

{memory_context}相关文档内容：
{context}

请根据上述文档内容回答用户的问题。要求：
1. 优先基于提供的文档内容回答
2. 如果文档内容不足以完全回答问题，可以使用可用的工具获取额外信息
3. 回答要准确、有用，简洁明了
4. 如果引用文档内容，请说明来源
5. 如果使用工具获取信息，请整合工具结果提供完整回答
6. 根据用户背景信息提供个性化回答

回答："""
            else:
                return f"""你是一个智能助手，可以回答各种问题并使用工具获取实时信息。当前没有找到相关的笔记内容，但你可以使用可用的工具来回答用户问题。

用户问题：{question}

{memory_context}请回答用户的问题。要求：
1. 如果问题需要实时信息（如天气、地图等），请使用相应的工具
2. 回答要准确、有用，简洁明了
3. 如果使用工具获取信息，请整合工具结果提供完整回答
4. 如果无法通过工具获取所需信息，请诚实说明

回答："""

    def _extract_memories_from_conversation_async(self, question: str, answer: str, source: str) -> None:
        """异步从对话中提取记忆信息"""
        def _extract_memories():
            try:
                # 处理对话并更新记忆
                result = self.memory_service.process_conversation(question, answer)
                
                if result.get("status") == "success":
                    logger.info(f"从对话中自动更新记忆: {result.get('old_count')} -> {result.get('new_count')} 条记忆")
                else:
                    logger.warning(f"对话记忆处理失败: {result.get('message', '未知错误')}")
                
            except Exception as e:
                logger.error(f"提取对话记忆失败: {e}")
        
        # 异步执行记忆提取，不阻塞主线程
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(_extract_memories)
            logger.debug("记忆提取任务已提交到后台执行")
        except Exception as e:
            logger.error(f"提交记忆提取任务失败: {e}")

    def chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True, messages: List[Dict] = None) -> Dict[str, Any]:
        """基于知识库内容的智能问答"""
        if not self.is_available():
            logger.warning("AI service not available")
            return {"error": "AI service not available"}
        
        try:
            start_time = time.time()
            logger.info(f"Starting chat with context: {question}")
            
            # 获取相关文档
            context_results = self._hierarchical_context_search(question, search_limit)
            
            # 构建上下文
            context = self._build_context_from_results(context_results, max_context_length)
            
            # 构建提示词
            prompt = self._build_smart_prompt(question, context, messages)
            
            # 获取LLM回答
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # 异步提取记忆（不阻塞响应）
            self._extract_memories_from_conversation_async(question, response.content, "chat_with_context")
            
            total_time = time.time() - start_time
            logger.info(f"Chat completed in {total_time:.3f}s")
            
            return {
                "answer": response.content,
                "related_documents": context_results,
                "search_query": question,
                "context_length": len(context),
                "processing_time": round(total_time, 3),
                "tools_used": 0
            }
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {"error": str(e)}

    def direct_chat(self, question: str, messages: List[Dict] = None) -> Dict[str, Any]:
        """Non-streaming direct chat for quick responses"""
        if not self.is_available():
            logger.warning("AI service not available")
            return {"error": "AI service not available"}
        
        try:
            start_time = time.time()
            logger.info(f"Starting direct chat: {question}")
            
            # Build message history  
            if messages and len(messages) > 1:
                conversation_history = []
                for msg in messages[:-1]:
                    if msg.get('role') == 'user':
                        conversation_history.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        conversation_history.append(AIMessage(content=msg.get('content', '')))
                
                full_messages = conversation_history + [HumanMessage(content=question)]
            else:
                full_messages = [HumanMessage(content=question)]
            
            # Get response from LLM
            response = self.llm.invoke(full_messages)
            
            # 异步提取记忆（不阻塞响应）
            self._extract_memories_from_conversation_async(question, response.content, "direct_chat")
            
            total_time = time.time() - start_time
            logger.info(f"Direct chat completed in {total_time:.3f}s")
            
            return {
                "answer": response.content,
                "related_documents": [],
                "search_query": question,
                "context_length": 0,
                "processing_time": round(total_time, 3),
                "tools_used": 0
            }
            
        except Exception as e:
            logger.error(f"Direct chat failed: {e}")
            return {"error": str(e)}

    def _hierarchical_context_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """层次化上下文搜索 - 基于语义搜索的封装"""
        try:
            # 使用现有的层次化语义搜索
            similarity_threshold = settings.semantic_search_threshold
            return self._hierarchical_semantic_search(query, limit, similarity_threshold)
        except Exception as e:
            logger.error(f"层次化上下文搜索失败: {e}")
            return []

    def _build_context_from_results(self, search_results: List[Dict[str, Any]], max_length: int = 3000) -> str:
        """从搜索结果构建上下文字符串"""
        if not search_results:
            logger.info("🔧 构建上下文: 无搜索结果，返回空上下文")
            return ""
        
        logger.info(f"🔧 开始构建上下文: {len(search_results)} 个搜索结果, 最大长度: {max_length}")
        
        context_parts = []
        current_length = 0
        included_count = 0
        
        for i, result in enumerate(search_results, 1):
            content = result.get('chunk_text', result.get('content', ''))
            file_path = result.get('file_path', 'Unknown')
            chunk_type = result.get('chunk_type', 'content')
            
            # 格式化结果片段
            if chunk_type == "summary":
                formatted_content = f"[摘要 - {file_path}]\n{content}\n"
            elif chunk_type == "outline":
                formatted_content = f"[大纲 - {file_path}]\n{content}\n"
            else:
                formatted_content = f"[内容 - {file_path}]\n{content}\n"
            
            # 检查长度限制
            if current_length + len(formatted_content) > max_length:
                logger.info(f"   片段 {i}: 长度超限 ({current_length + len(formatted_content)} > {max_length}), 停止添加")
                break
                
            context_parts.append(formatted_content)
            current_length += len(formatted_content)
            included_count += 1
            
            logger.info(f"   片段 {i}: [{chunk_type}] {file_path} - {len(formatted_content)} 字符 (累计: {current_length})")
            logger.info(f"     内容: {content[:100]}..." if len(content) > 100 else f"     内容: {content}")
        
        final_context = "\n".join(context_parts)
        logger.info(f"🎯 上下文构建完成: 包含 {included_count}/{len(search_results)} 个片段, 总长度: {len(final_context)} 字符")
        logger.info(f"📄 最终上下文预览:\n{final_context[:300]}..." if len(final_context) > 300 else f"📄 最终上下文:\n{final_context}")
        
        return final_context

    def create_memory_from_chat(self, content: str, memory_type: str = "fact", 
                              category: str = "personal", importance_score: float = 0.5) -> bool:
        """手动创建聊天记忆"""
        try:
            success = self.memory_service.add_manual_memory(content, memory_type, importance_score)
            logger.info(f"手动创建聊天记忆成功")
            return success
            
        except Exception as e:
            logger.error(f"创建聊天记忆失败: {e}")
            return False

    async def direct_chat_streaming(self, question: str, messages: List[Dict] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """直接聊天 - 流式响应版本"""
        if not self.is_available():
            logger.warning("AI service not available")
            yield {"error": "AI service not available"}
            return

        try:
            # 构建提示词
            prompt = self._build_smart_prompt(question, "", messages)
            
            # 构建消息历史
            chat_history = []
            if messages:
                for msg in messages:
                    chat_history.append({"role": msg["role"], "content": msg["content"]})
            
            # 添加系统提示词
            chat_history.insert(0, {"role": "system", "content": prompt})
            
            # 添加用户问题
            chat_history.append({"role": "user", "content": question})
            
            # 调用LangChain流式聊天
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            
            langchain_messages = []
            for msg in chat_history:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 使用LangChain的streaming方式
            collected_messages = []
            for chunk in self.streaming_llm.stream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    collected_messages.append(content)
                    yield {"chunk": content}
            
            # 异步提取记忆（不阻塞响应）
            full_response = "".join(collected_messages)
            self._extract_memories_from_conversation_async(question, full_response, "direct_chat")
            
        except Exception as e:
            logger.error(f"直接聊天出错: {e}")
            yield {"error": f"对话出错: {str(e)}"}

    async def streaming_chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True, messages: List[Dict] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """基于知识库内容的智能问答 - 流式响应版本"""
        if not self.is_available():
            logger.warning("AI service not available")
            yield {"error": "AI service not available"}
            return

        try:
            start_time = time.time()
            logger.info(f"Starting streaming chat with context: {question}")
            
            # 获取相关文档
            context_results = self._hierarchical_context_search(question, search_limit)
            
            # 构建上下文
            context = self._build_context_from_results(context_results, max_context_length)
            
            # 构建提示词
            prompt = self._build_smart_prompt(question, context, messages)
            
            # 构建消息历史
            chat_history = []
            if messages:
                for msg in messages:
                    chat_history.append({"role": msg["role"], "content": msg["content"]})
            
            # 添加系统提示词
            chat_history.insert(0, {"role": "system", "content": prompt})
            
            # 添加用户问题
            chat_history.append({"role": "user", "content": question})
            
            # 调用LangChain流式聊天
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            
            langchain_messages = []
            for msg in chat_history:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 使用LangChain的streaming方式
            collected_messages = []
            for chunk in self.streaming_llm.stream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    collected_messages.append(content)
                    yield {"chunk": content}
            
            # 异步提取记忆（不阻塞响应）
            full_response = "".join(collected_messages)
            self._extract_memories_from_conversation_async(question, full_response, "chat_with_context")
            
            total_time = time.time() - start_time
            logger.info(f"Streaming chat completed in {total_time:.3f}s")
            
            # 发送最终信息
            yield {
                "related_documents": context_results,
                "search_query": question,
                "context_length": len(context),
                "processing_time": round(total_time, 3),
                "tools_used": 0,
                "finished": True
            }
            
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            yield {"error": str(e)}
    
    def get_document_summary_and_outline(self, file_id: int) -> Optional[Dict[str, Any]]:
        """获取文档的总结和提纲"""
        try:
            # 从数据库获取文件信息
            file = self.db.query(File).filter(
                File.id == file_id,
                File.is_deleted == False
            ).first()
            
            if not file:
                logger.warning(f"文件不存在或已删除: file_id={file_id}")
                return None
            
            # 检查是否启用层次化分块
            if settings.enable_hierarchical_chunking:
                # 尝试从嵌入数据中获取摘要和提纲
                embeddings = self.db.query(Embedding).filter(
                    Embedding.file_id == file_id
                ).all()
                
                summary = None
                outline = []
                
                for embedding in embeddings:
                    if embedding.chunk_type == "summary":
                        summary = embedding.chunk_text
                    elif embedding.chunk_type == "outline":
                        outline.append(embedding.chunk_text)
                
                if summary and outline:
                    return {
                        "summary": summary,
                        "outline": outline,
                        "source": "cached"
                    }
            
            # 如果没有缓存的摘要和提纲，动态生成
            if not self.is_available():
                logger.warning("AI服务不可用，无法生成文档摘要和提纲")
                return None
            
            # 生成摘要
            summary = self.generate_summary(file.content, max_length=300)
            
            # 生成提纲
            outline_items = self.generate_outline(file.content, max_items=8)
            
            if summary and outline_items:
                return {
                    "summary": summary,
                    "outline": outline_items,
                    "source": "generated"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取文档摘要和提纲失败: {e}")
            return None
