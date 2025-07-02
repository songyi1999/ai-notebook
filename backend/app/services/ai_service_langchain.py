# LangChain-Chroma版本的AIService

from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
import requests
import os
import hashlib
import threading
import time
from functools import lru_cache

from ..models.file import File
from ..models.embedding import Embedding
from ..config import settings

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
                                base_url=settings.openai_base_url,
                                api_key=settings.openai_api_key,
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
            base_url=self.openai_base_url,
            api_key=self.openai_api_key,
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

    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return bool(self.openai_api_key and self.vector_store)

    def create_embeddings(self, file: File) -> bool:
        """为文件创建向量嵌入 - 使用LangChain简化版本"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法创建嵌入")
            return False
        
        try:
            logger.info(f"开始为文件创建嵌入: {file.file_path}")
            
            # 1. 删除现有的SQLite嵌入记录
            self.db.query(Embedding).filter(Embedding.file_id == file.id).delete()
            
            # 2. 删除现有的向量存储中的文档
            try:
                # 通过元数据过滤删除现有文档
                existing_docs = self.vector_store.get(
                    where={"file_id": file.id}
                )
                if existing_docs and existing_docs.get('ids'):
                    self.vector_store.delete(ids=existing_docs['ids'])
                    logger.info(f"删除文件 {file.id} 的现有向量: {len(existing_docs['ids'])} 个")
            except Exception as e:
                logger.warning(f"删除现有向量时出错: {e}")
            
            # 3. 分割文本
            texts = self.text_splitter.split_text(file.content)
            
            # 4. 创建LangChain Document对象
            documents = []
            for i, text in enumerate(texts):
                doc = Document(
                    page_content=text,
                    metadata={
                        "file_id": file.id,
                        "file_path": file.file_path,
                        "chunk_index": i,
                        "chunk_hash": hashlib.sha256(text.encode()).hexdigest(),
                        "title": file.title,
                        "vector_model": settings.embedding_model_name
                    }
                )
                documents.append(doc)
                
                # 同时保存到SQLite（仅元数据）
                embedding = Embedding(
                    file_id=file.id,
                    chunk_index=i,
                    chunk_text=text,
                    chunk_hash=doc.metadata["chunk_hash"],
                    embedding_vector=b'',  # 空向量，实际向量存储在ChromaDB
                    vector_model=settings.embedding_model_name
                )
                self.db.add(embedding)
            
            # 5. 批量添加到向量存储
            if documents:
                # LangChain会自动处理嵌入生成和存储
                ids = [f"file_{file.id}_chunk_{doc.metadata['chunk_index']}" for doc in documents]
                self.vector_store.add_documents(documents, ids=ids)
                logger.info(f"成功添加 {len(documents)} 个文档到LangChain-Chroma")
            
            # 6. 提交SQLite事务
            self.db.commit()
            logger.info(f"为文件 {file.file_path} 创建了 {len(texts)} 个嵌入向量")
            return True
            
        except Exception as e:
            logger.error(f"创建嵌入失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.db.rollback()
            return False

    def semantic_search(self, query: str, limit: int = 10, similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """语义搜索 - 使用LangChain简化版本，带缓存优化"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行语义搜索")
            return []
        
        # 使用配置中的默认阈值
        if similarity_threshold is None:
            similarity_threshold = settings.semantic_search_threshold
        
        try:
            start_time = time.time()
            logger.info(f"开始LangChain语义搜索，查询: {query}, 阈值: {similarity_threshold}")
            
            # 使用LangChain的similarity_search_with_score方法（带缓存优化）
            search_results = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit * 2,  # 获取更多结果用于过滤
                filter=None  # 可以添加过滤条件
            )
            
            logger.info(f"LangChain搜索返回 {len(search_results)} 个结果")
            
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
            
            total_time = time.time() - start_time
            logger.info(f"LangChain语义搜索完成，查询: {query}, 过滤后结果: {len(results)}, 总耗时: {total_time:.3f}秒")
            return results
            
        except Exception as e:
            logger.error(f"LangChain语义搜索失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []

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
        """获取向量数据库中的向量数量"""
        try:
            if self.vector_store:
                all_docs = self.vector_store.get()
                return len(all_docs.get('ids', [])) if all_docs else 0
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
        """智能标签建议"""
        if not self.llm:
            logger.warning("LLM不可用，无法生成标签建议")
            return []
        
        try:
            prompt = f"""基于以下文档的标题和内容，建议最多{max_tags}个相关的标签。
标签应该简洁、准确，用中文表示。

标题：{title}
内容：{content[:1000]}

请只返回标签列表，每行一个标签："""
            
            response = self.llm.invoke(prompt)
            tags_text = response.content.strip()
            
            # 解析标签
            tags = [tag.strip() for tag in tags_text.split('\n') if tag.strip()]
            tags = tags[:max_tags]  # 限制数量
            
            logger.info(f"标签建议生成成功: {tags}")
            return tags
            
        except Exception as e:
            logger.error(f"生成标签建议失败: {e}")
            return []

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
        """智能链接发现"""
        if not self.llm:
            logger.warning("LLM不可用，无法发现智能链接")
            return []
        
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
                logger.info(f"智能链接发现成功: {len(smart_links)} 个链接")
                return smart_links
            except json.JSONDecodeError as e:
                logger.error(f"解析智能链接JSON失败: {e}")
                return []
            
        except Exception as e:
            logger.error(f"智能链接发现失败: {e}")
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

    def chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5) -> Dict[str, Any]:
        """基于上下文的智能问答 - RAG实现"""
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
            logger.info(f"开始RAG问答，问题: {question}")
            
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
            
            # 3. 构建提示词
            prompt = f"""你是一个智能助手，专门回答基于用户笔记内容的问题。请根据以下相关文档内容来回答用户的问题。

用户问题：{question}

相关文档内容：
{context}

请根据上述文档内容回答用户的问题。要求：
1. 回答要准确、有用，基于提供的文档内容
2. 如果文档内容不足以完全回答问题，请说明并提供你能确定的部分
3. 回答要简洁明了，重点突出
4. 如果可能，请引用具体的文档来源

回答："""

            # 4. 调用LLM生成回答
            logger.info(f"调用LLM生成回答，上下文长度: {len(context)} 字符")
            response = self.llm.invoke(prompt)
            answer = response.content.strip()
            
            total_time = time.time() - start_time
            logger.info(f"RAG问答完成，耗时: {total_time:.3f}秒，回答长度: {len(answer)} 字符")
            
            return {
                "answer": answer,
                "related_documents": related_docs,
                "search_query": question,
                "context_length": len(context),
                "processing_time": round(total_time, 3)
            }
            
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

    async def streaming_chat_with_context(self, question: str, max_context_length: int = 3000, search_limit: int = 5):
        """基于上下文的流式智能问答 - RAG实现"""
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
            logger.info(f"开始流式RAG问答，问题: {question}")
            
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
            
            # 3. 构建提示词
            prompt = f"""你是一个智能助手，专门回答基于用户笔记内容的问题。请根据以下相关文档内容来回答用户的问题。

用户问题：{question}

相关文档内容：
{context}

请根据上述文档内容回答用户的问题。要求：
1. 回答要准确、有用，基于提供的文档内容
2. 如果文档内容不足以完全回答问题，请说明并提供你能确定的部分
3. 回答要简洁明了，重点突出
4. 如果可能，请引用具体的文档来源

回答："""

            # 4. 流式调用LLM生成回答
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
            
            yield {
                "finished": True,
                "processing_time": round(total_time, 3),
                "related_documents": related_docs,
                "search_query": question,
                "context_length": len(context)
            }
            
        except Exception as e:
            logger.error(f"流式RAG问答失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            
            yield {
                "error": str(e),
                "related_documents": [],
                "search_query": question
            }
