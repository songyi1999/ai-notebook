# LangChain-Chroma版本的AIService

from typing import List, Optional, Dict, Any
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

from ..models.file import File
from ..models.embedding import Embedding
from ..models.tag import Tag
from ..config import settings
from .mcp_service import MCPClientService
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
        return bool(self.openai_api_key and self.vector_store)

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
            documents = self._create_hierarchical_chunks(file, progress_callback)
            
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
        try:
            from .hierarchical_splitter import IntelligentHierarchicalSplitter
            
            if progress_callback:
                progress_callback("分析中", f"正在分析文件结构和内容")
            
            # 创建智能分块器，传入LLM实例
            splitter = IntelligentHierarchicalSplitter(llm=self.llm)
            hierarchical_docs = splitter.split_document(file.content, file.title, file.id, progress_callback)
            
            all_documents = []
            
            # 处理摘要层
            if progress_callback:
                progress_callback("摘要生成", f"正在处理文件摘要")
            for doc in hierarchical_docs.get('summary', []):
                all_documents.append(doc)
                self._save_embedding_metadata(doc, file.id)
            
            # 处理大纲层
            if progress_callback:
                progress_callback("大纲提取", f"正在处理文件大纲")
            for doc in hierarchical_docs.get('outline', []):
                all_documents.append(doc)
                self._save_embedding_metadata(doc, file.id)
            
            # 处理内容层
            if progress_callback:
                progress_callback("内容分块", f"正在处理内容分块")
            for doc in hierarchical_docs.get('content', []):
                all_documents.append(doc)
                self._save_embedding_metadata(doc, file.id)
            
            logger.info(f"智能多层次分块完成: 总共 {len(all_documents)} 个文档")
            return all_documents
            
        except Exception as e:
            logger.error(f"创建智能多层次分块失败: {e}")
            # 创建最基本的摘要和内容块（降级策略）
            if progress_callback:
                progress_callback("降级处理", f"智能分块失败，使用基本分块策略")
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
            # 创建嵌入记录
            embedding = Embedding(
                file_id=file_id,
                chunk_index=doc.metadata['chunk_index'],
                chunk_hash=doc.metadata['chunk_hash'],
                vector_model=doc.metadata['vector_model'],
                chunk_type=doc.metadata.get('chunk_type', 'content'),
                chunk_level=doc.metadata.get('chunk_level', 1),
                parent_heading=doc.metadata.get('parent_heading'),
                section_path=doc.metadata.get('section_path'),
                generation_method=doc.metadata.get('generation_method', 'hierarchical')
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
            
            logger.info(f"多层次搜索完成: 摘要={len(summary_results)}, 大纲={len(outline_results)}, 内容={len(content_results)}, 最终={len(final_results)}")
            return final_results
            
        except Exception as e:
            logger.error(f"多层次语义搜索失败: {e}")
            # 降级到传统搜索
            return self._traditional_semantic_search(query, limit, similarity_threshold)
    
    def _search_by_chunk_type(self, query: str, chunk_type: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """按分块类型搜索"""
        try:
            search_results = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit * 2,
                filter={"chunk_type": chunk_type}
            )
            
            results = []
            for doc, score in search_results:
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
                                'similarity': float(1 - score),
                                'created_at': file.created_at.isoformat() if file.created_at else None,
                                'updated_at': file.updated_at.isoformat() if file.updated_at else None,
                            }
                            results.append(result_item)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"按类型搜索失败 ({chunk_type}): {e}")
            return []
    
    def _get_file_outline(self, file_id: int) -> List[Dict[str, Any]]:
        """获取文件的大纲"""
        try:
            # 从向量存储中获取该文件的outline类型文档
            docs = self.vector_store.get(
                where={"file_id": file_id, "chunk_type": "outline"},
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
            # 从向量存储中获取该章节的内容
            docs = self.vector_store.get(
                where={"file_id": file_id, "chunk_type": "content", "parent_heading": section_path},
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

    def chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True) -> Dict[str, Any]:
        """基于上下文的智能问答 - RAG实现，支持MCP工具调用和多层次检索"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行智能问答")
            return {
                "answer": "抱歉，AI服务当前不可用，请检查配置。",
                "related_documents": [],
                "search_query": question,
                "error": "AI服务不可用"
            }
        
        try:
            start_time = time.time()
            logger.info(f"开始RAG问答，问题: {question}, 工具调用: {enable_tools}")
            
            # 1. 智能上下文检索（支持多层次）
            if settings.enable_hierarchical_chunking:
                search_results = self._hierarchical_context_search(question, search_limit)
            else:
                search_results = self.semantic_search(
                    query=question,
                    limit=search_limit,
                    similarity_threshold=settings.semantic_search_threshold
                )
            
            logger.info(f"搜索到 {len(search_results)} 个相关文档")
            
            # 2. 构建上下文
            context_parts = []
            related_docs = []
            current_length = 0
            
            for result in search_results:
                chunk_text = result.get('chunk_text', '')
                file_path = result.get('file_path', '')
                title = result.get('title', '')
                similarity = result.get('similarity', 0)
                chunk_type = result.get('chunk_type', 'content')
                section_path = result.get('section_path', '')
                
                # 根据分块类型调整上下文格式
                if chunk_type == 'summary':
                    context_part = f"【文档摘要】{title}\n路径：{file_path}\n摘要：{chunk_text}\n"
                elif chunk_type == 'outline':
                    context_part = f"【章节大纲】{title} - {section_path}\n路径：{file_path}\n大纲：{chunk_text}\n"
                else:
                    context_part = f"【内容片段】{title}\n路径：{file_path}\n内容：{chunk_text}\n"
                
                # 检查长度限制
                if current_length + len(context_part) > max_context_length:
                    logger.info(f"上下文长度达到限制 {max_context_length}，停止添加更多文档")
                    break
                
                context_parts.append(context_part)
                current_length += len(context_part)
                
                # 添加到相关文档列表（用于前端显示）
                related_docs.append({
                    'file_id': result.get('file_id'),
                    'file_path': file_path,
                    'title': title,
                    'similarity': similarity,
                    'chunk_text': chunk_text[:200] + '...' if len(chunk_text) > 200 else chunk_text,
                    'chunk_type': chunk_type,
                    'section_path': section_path
                })
            
            context = "\n\n".join(context_parts)
            
            # 3. 获取可用的MCP工具
            tools = []
            tool_calls_history = []
            if enable_tools:
                try:
                    tools = self.mcp_service.get_tools_for_llm()
                    logger.info(f"获取到 {len(tools)} 个可用工具")
                except Exception as e:
                    logger.warning(f"获取MCP工具失败: {e}")
            
            # 4. 构建提示词
            prompt = f"""你是一个智能助手，专门回答基于用户笔记内容的问题。请根据以下相关文档内容来回答用户的问题。

用户问题：{question}

相关文档内容：
{context}

请根据上述文档内容回答用户的问题。要求：
1. 回答要准确、有用，基于提供的文档内容
2. 如果文档内容不足以完全回答问题，请说明并提供你能确定的部分
3. 回答要简洁明了，重点突出
4. 如果可能，请引用具体的文档来源
5. 如果需要额外信息或执行特定任务，可以使用可用的工具

回答："""

            # 5. 调用LLM生成回答（支持工具调用）
            logger.info(f"调用LLM生成回答，上下文长度: {len(context)} 字符")
            
            if tools:
                # 使用工具调用
                llm_with_tools = self.llm.bind_tools(tools)
                response = llm_with_tools.invoke(prompt)
                
                # 处理工具调用
                if response.tool_calls:
                    logger.info(f"LLM决定调用 {len(response.tool_calls)} 个工具")
                    
                    # 执行工具调用
                    tool_results = []
                    for tool_call in response.tool_calls:
                        try:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]
                            
                            logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")
                            
                            # 执行工具调用
                            import asyncio
                            
                            request = MCPToolCallRequest(
                                tool_name=tool_name,
                                arguments=tool_args,
                                session_id=f"chat_{int(time.time())}"
                            )
                            result = asyncio.run(self.mcp_service.call_tool(request))
                            
                            tool_results.append({
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "result": result.result if result.success else result.error,
                                "success": result.success,
                                "execution_time": result.execution_time_ms
                            })
                            
                            tool_calls_history.append({
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "result": result.result if result.success else result.error,
                                "success": result.success,
                                "execution_time": result.execution_time_ms
                            })
                            
                        except Exception as e:
                            logger.error(f"工具调用失败: {e}")
                            tool_results.append({
                                "tool_name": tool_call.get("name", "unknown"),
                                "arguments": tool_call.get("args", {}),
                                "result": f"工具调用失败: {str(e)}",
                                "success": False,
                                "execution_time": 0
                            })
                    
                    # 将工具结果整合到最终回答中
                    if tool_results:
                        tool_summary = "\n\n工具调用结果：\n"
                        for i, result in enumerate(tool_results, 1):
                            status = "成功" if result["success"] else "失败"
                            tool_summary += f"{i}. {result['tool_name']} ({status}): {result['result']}\n"
                        
                        # 重新调用LLM，整合工具结果
                        final_prompt = f"{prompt}\n\n{tool_summary}\n\n请根据上述信息和工具调用结果，提供最终的回答："
                        final_response = self.llm.invoke(final_prompt)
                        answer = final_response.content.strip()
                    else:
                        answer = response.content.strip()
                else:
                    answer = response.content.strip()
            else:
                # 不使用工具调用
                response = self.llm.invoke(prompt)
                answer = response.content.strip()
            
            total_time = time.time() - start_time
            logger.info(f"RAG问答完成，耗时: {total_time:.3f}秒，回答长度: {len(answer)} 字符")
            
            result = {
                "answer": answer,
                "related_documents": related_docs,
                "search_query": question,
                "context_length": len(context),
                "processing_time": round(total_time, 3),
                "tools_used": len(tools) if tools else 0
            }
            
            # 如果有工具调用历史，添加到结果中
            if tool_calls_history:
                result["tool_calls"] = tool_calls_history
            
            return result
            
        except Exception as e:
            logger.error(f"RAG问答失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            
            return {
                "answer": f"抱歉，处理您的问题时出现了错误：{str(e)}",
                "related_documents": [],
                "search_query": question,
                "error": str(e)
            }

    async def streaming_chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5, enable_tools: bool = True):
        """基于上下文的流式智能问答 - RAG实现，支持MCP工具调用"""
        if not self.is_available() or not self.streaming_llm:
            logger.warning("AI服务或流式LLM不可用，无法进行流式智能问答")
            yield {
                "error": "AI服务不可用",
                "related_documents": [],
                "search_query": question
            }
            return
        
        try:
            start_time = time.time()
            logger.info(f"开始流式RAG问答，问题: {question}, 工具调用: {enable_tools}")
            
            # 1. 语义搜索相关文档
            search_results = self.semantic_search(
                query=question,
                limit=search_limit,
                similarity_threshold=settings.semantic_search_threshold
            )
            
            logger.info(f"搜索到 {len(search_results)} 个相关文档")
            
            # 2. 构建上下文
            context_parts = []
            related_docs = []
            current_length = 0
            
            for result in search_results:
                chunk_text = result.get('chunk_text', '')
                file_path = result.get('file_path', '')
                title = result.get('title', '')
                similarity = result.get('similarity', 0)
                
                # 准备上下文片段
                context_part = f"文档：{title}\n路径：{file_path}\n内容：{chunk_text}\n"
                
                # 检查长度限制
                if current_length + len(context_part) > max_context_length:
                    logger.info(f"上下文长度达到限制 {max_context_length}，停止添加更多文档")
                    break
                
                context_parts.append(context_part)
                current_length += len(context_part)
                
                # 添加到相关文档列表（用于前端显示）
                related_docs.append({
                    'file_id': result.get('file_id'),
                    'file_path': file_path,
                    'title': title,
                    'similarity': similarity,
                    'chunk_text': chunk_text[:200] + '...' if len(chunk_text) > 200 else chunk_text
                })
            
            context = "\n\n".join(context_parts)
            
            # 3. 获取可用的MCP工具
            tools = []
            tool_calls_history = []
            if enable_tools:
                try:
                    tools = self.mcp_service.get_tools_for_llm()
                    logger.info(f"获取到 {len(tools)} 个可用工具")
                except Exception as e:
                    logger.warning(f"获取MCP工具失败: {e}")
            
            # 4. 构建提示词
            prompt = f"""你是一个智能助手，专门回答基于用户笔记内容的问题。请根据以下相关文档内容来回答用户的问题。

用户问题：{question}

相关文档内容：
{context}

请根据上述文档内容回答用户的问题。要求：
1. 回答要准确、有用，基于提供的文档内容
2. 如果文档内容不足以完全回答问题，请说明并提供你能确定的部分
3. 回答要简洁明了，重点突出
4. 如果可能，请引用具体的文档来源
5. 如果需要额外信息或执行特定任务，可以使用可用的工具

回答："""

            # 5. 检查是否需要工具调用（先进行非流式检查）
            if tools:
                # 先用非流式LLM检查是否需要工具调用
                llm_with_tools = self.llm.bind_tools(tools)
                check_response = llm_with_tools.invoke(prompt)
                
                if check_response.tool_calls:
                    logger.info(f"LLM决定调用 {len(check_response.tool_calls)} 个工具")
                    
                    # 发送工具调用开始信号
                    yield {
                        "tool_calls_started": True,
                        "tool_count": len(check_response.tool_calls),
                        "related_documents": related_docs,
                        "search_query": question,
                        "context_length": len(context)
                    }
                    
                    # 执行工具调用
                    tool_results = []
                    for i, tool_call in enumerate(check_response.tool_calls):
                        try:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]
                            
                            # 发送工具调用进度
                            yield {
                                "tool_call_progress": {
                                    "index": i + 1,
                                    "total": len(check_response.tool_calls),
                                    "tool_name": tool_name,
                                    "status": "executing"
                                }
                            }
                            
                            logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")
                            
                            # 执行工具调用
                            request = MCPToolCallRequest(
                                tool_name=tool_name,
                                arguments=tool_args,
                                session_id=f"stream_chat_{int(time.time())}"
                            )
                            result = await self.mcp_service.call_tool(request)
                            
                            tool_result = {
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "result": result.result if result.success else result.error,
                                "success": result.success,
                                "execution_time": result.execution_time_ms
                            }
                            
                            tool_results.append(tool_result)
                            tool_calls_history.append(tool_result)
                            
                            # 发送工具调用完成
                            yield {
                                "tool_call_progress": {
                                    "index": i + 1,
                                    "total": len(check_response.tool_calls),
                                    "tool_name": tool_name,
                                    "status": "completed",
                                    "result": tool_result
                                }
                            }
                            
                        except Exception as e:
                            logger.error(f"工具调用失败: {e}")
                            error_result = {
                                "tool_name": tool_call.get("name", "unknown"),
                                "arguments": tool_call.get("args", {}),
                                "result": f"工具调用失败: {str(e)}",
                                "success": False,
                                "execution_time": 0
                            }
                            tool_results.append(error_result)
                            
                            # 发送工具调用错误
                            yield {
                                "tool_call_progress": {
                                    "index": i + 1,
                                    "total": len(check_response.tool_calls),
                                    "tool_name": tool_call.get("name", "unknown"),
                                    "status": "error",
                                    "error": str(e)
                                }
                            }
                    
                    # 发送工具调用完成信号
                    yield {
                        "tool_calls_completed": True,
                        "tool_results": tool_results
                    }
                    
                    # 将工具结果整合到提示词中
                    if tool_results:
                        tool_summary = "\n\n工具调用结果：\n"
                        for i, result in enumerate(tool_results, 1):
                            status = "成功" if result["success"] else "失败"
                            tool_summary += f"{i}. {result['tool_name']} ({status}): {result['result']}\n"
                        
                        # 更新提示词
                        prompt = f"{prompt}\n\n{tool_summary}\n\n请根据上述信息和工具调用结果，提供最终的回答："
            
            # 6. 流式调用LLM生成回答
            logger.info(f"开始流式调用LLM，上下文长度: {len(context)} 字符")
            
            # 使用LangChain的astream方法进行真正的流式输出
            async for chunk in self.streaming_llm.astream(prompt):
                if chunk.content:  # 只有当chunk有内容时才yield
                    yield {
                        "chunk": chunk.content,
                        "related_documents": related_docs,
                        "search_query": question,
                        "context_length": len(context)
                    }
            
            # 流式结束后发送最终统计信息
            total_time = time.time() - start_time
            logger.info(f"流式RAG问答完成，耗时: {total_time:.3f}秒")
            
            final_result = {
                "finished": True,
                "processing_time": round(total_time, 3),
                "related_documents": related_docs,
                "search_query": question,
                "context_length": len(context),
                "tools_used": len(tools) if tools else 0
            }
            
            # 如果有工具调用历史，添加到结果中
            if tool_calls_history:
                final_result["tool_calls"] = tool_calls_history
            
            yield final_result
            
        except Exception as e:
            logger.error(f"流式RAG问答失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            
            yield {
                "error": str(e),
                "related_documents": [],
                "search_query": question
            }

    def _hierarchical_context_search(self, question: str, search_limit: int) -> List[Dict[str, Any]]:
        """多层次上下文搜索 - 为RAG问答优化"""
        try:
            logger.info(f"开始多层次上下文搜索: {question}")
            
            # 分析问题类型，决定搜索策略
            question_type = self._analyze_question_type(question)
            
            context_results = []
            
            if question_type == 'overview':
                # 概览性问题：优先搜索摘要层
                summary_results = self._search_by_chunk_type(question, "summary", search_limit//2, 0.8)
                outline_results = self._search_by_chunk_type(question, "outline", search_limit//2, 0.7)
                content_results = self._search_by_chunk_type(question, "content", search_limit//3, 0.7)
                
                # 智能上下文扩展：为摘要匹配的文件获取关键章节
                for summary_result in summary_results:
                    context_results.append(summary_result)
                    # 获取该文件的重要章节
                    file_outlines = self._get_file_outline(summary_result['file_id'])
                    context_results.extend(file_outlines[:2])  # 添加前2个章节
                
                context_results.extend(outline_results)
                context_results.extend(content_results)
                
            elif question_type == 'specific':
                # 具体问题：优先搜索内容层，补充相关大纲
                content_results = self._search_by_chunk_type(question, "content", search_limit, 0.7)
                outline_results = self._search_by_chunk_type(question, "outline", search_limit//2, 0.7)
                
                # 为内容匹配结果添加上下文
                for content_result in content_results:
                    context_results.append(content_result)
                    
                    # 如果有章节信息，尝试获取相邻内容
                    if content_result.get('parent_heading'):
                        sibling_content = self._get_section_content(
                            content_result['file_id'], 
                            content_result['parent_heading']
                        )
                        context_results.extend(sibling_content[:1])  # 添加1个相邻内容块
                
                context_results.extend(outline_results)
                
            else:
                # 默认策略：平衡搜索各个层次
                summary_results = self._search_by_chunk_type(question, "summary", search_limit//4, 0.8)
                outline_results = self._search_by_chunk_type(question, "outline", search_limit//3, 0.7)
                content_results = self._search_by_chunk_type(question, "content", search_limit, 0.7)
                
                context_results.extend(summary_results)
                context_results.extend(outline_results)
                context_results.extend(content_results)
            
            # 去重并排序
            final_results = self._deduplicate_and_rank(context_results, search_limit * 2)
            
            logger.info(f"多层次上下文搜索完成: 返回 {len(final_results)} 个结果")
            return final_results[:search_limit]
            
        except Exception as e:
            logger.error(f"多层次上下文搜索失败: {e}")
            # 降级到传统搜索
            return self.semantic_search(question, search_limit, settings.semantic_search_threshold)
    
    def _analyze_question_type(self, question: str) -> str:
        """分析问题类型"""
        question_lower = question.lower()
        
        # 概览性问题关键词
        overview_keywords = ['什么是', '介绍', '概述', '总结', '整体', '全部', '所有', '概况', '总体']
        
        # 具体问题关键词
        specific_keywords = ['如何', '怎么', '为什么', '哪里', '何时', '具体', '详细', '步骤', '方法']
        
        if any(keyword in question_lower for keyword in overview_keywords):
            return 'overview'
        elif any(keyword in question_lower for keyword in specific_keywords):
            return 'specific'
        else:
            return 'balanced'
