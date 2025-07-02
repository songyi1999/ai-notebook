from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import numpy as np
import pickle
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.config import Settings as ChromaSettings
import hashlib
import json

from ..models.file import File
from ..models.embedding import Embedding
from ..config import settings

logger = logging.getLogger(__name__)

class AIService:
    """AI服务类，提供智能功能 - 使用ChromaDB进行向量存储"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = settings.openai_api_key
        self.openai_base_url = settings.openai_base_url
        
        # 初始化嵌入配置 - 使用标准的 /v1/embeddings 接口
        if self.openai_api_key:
            self.embedding_base_url = self.openai_base_url
            self.embedding_model = settings.embedding_model_name
            self.llm = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=settings.openai_model
            )
        else:
            logger.warning("未配置OpenAI API密钥，AI功能将不可用")
            self.llm = None
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        
        # 初始化ChromaDB客户端
        self.chroma_db_path = settings.chroma_db_path
        self._init_chroma_client()

    def _init_chroma_client(self):
        """初始化ChromaDB客户端和集合"""
        try:
            # 创建ChromaDB客户端 - 简化配置避免验证错误
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 创建或获取集合
            self.collection_name = "document_embeddings"
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "AI笔记本文档嵌入向量"}
            )
            
            logger.info(f"ChromaDB客户端初始化成功，集合: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"ChromaDB客户端初始化失败: {e}")
            self.chroma_client = None
            self.chroma_collection = None

    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return bool(self.openai_api_key and self.chroma_client)
    
    def _get_embedding(self, text: str) -> List[float]:
        """使用标准的 /v1/embeddings 接口获取文本嵌入"""
        try:
            # 构建标准的 OpenAI 兼容接口 URL
            url = f"{self.embedding_base_url}/v1/embeddings"
            
            # 使用标准的 OpenAI embeddings API 格式
            payload = {
                "model": self.embedding_model,
                "input": text,
                "encoding_format": "float"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            logger.debug(f"发送嵌入请求到: {url}")
            logger.debug(f"请求数据: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"嵌入响应: {result}")
            
            # 标准 OpenAI 格式: {"data": [{"embedding": [...]}], ...}
            if "data" in result and result["data"] and len(result["data"]) > 0:
                return result["data"][0]["embedding"]
            else:
                logger.error(f"嵌入响应格式错误: {result}")
                return []
                
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            return []

    def _serialize_vector(self, vector: List[float]) -> bytes:
        """序列化向量数据 - 用于SQLite存储"""
        try:
            return pickle.dumps(np.array(vector))
        except Exception as e:
            logger.error(f"向量序列化失败: {e}")
            return b''

    def generate_summary(self, content: str, max_length: int = 200) -> Optional[str]:
        """生成文档摘要"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法生成摘要")
            return None
        
        try:
            prompt = f"""
            请为以下内容生成一个简洁的摘要，不超过{max_length}字：
            
            内容：
            {content[:2000]}  # 限制输入长度
            
            摘要：
            """
            
            response = self.llm.invoke(prompt)
            summary = response.content.strip()
            
            logger.info(f"摘要生成成功，长度: {len(summary)}")
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return None

    def suggest_tags(self, title: str, content: str, max_tags: int = 5) -> List[str]:
        """智能标签建议"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法生成标签建议")
            return []
        
        try:
            prompt = f"""
            基于以下文档的标题和内容，建议最多{max_tags}个相关的标签。
            标签应该简洁、准确，用中文表示。
            
            标题：{title}
            内容：{content[:1000]}
            
            请只返回标签列表，每行一个标签：
            """
            
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

    def create_embeddings(self, file: File) -> bool:
        """为文件创建向量嵌入 - 双存储：SQLite(元数据) + ChromaDB(向量)"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法创建嵌入")
            return False
        
        try:
            # 1. 删除现有的SQLite嵌入记录
            self.db.query(Embedding).filter(Embedding.file_id == file.id).delete()
            
            # 2. 删除现有的ChromaDB向量（通过file_id前缀）
            try:
                # 获取该文件的所有向量ID
                existing_results = self.chroma_collection.get(
                    where={"file_id": file.id}
                )
                if existing_results['ids']:
                    self.chroma_collection.delete(ids=existing_results['ids'])
                    logger.info(f"删除文件 {file.id} 的现有向量: {len(existing_results['ids'])} 个")
            except Exception as e:
                logger.warning(f"删除现有向量时出错: {e}")
            
            # 3. 分割文本
            texts = self.text_splitter.split_text(file.content)
            
            # 4. 批量处理文本块
            embeddings_to_add = []
            metadatas_to_add = []
            ids_to_add = []
            documents_to_add = []
            
            for i, text in enumerate(texts):
                logger.info(f"正在为文本块 {i} 创建嵌入，文本长度: {len(text)}")
                
                # 生成嵌入向量
                embedding_vector = self._get_embedding(text)
                if not embedding_vector:
                    logger.error(f"无法为文本块 {i} 生成嵌入向量，跳过")
                    continue
                
                # 计算文本块哈希
                chunk_hash = hashlib.sha256(text.encode()).hexdigest()
                
                # 准备ChromaDB数据
                chunk_id = f"file_{file.id}_chunk_{i}"
                embeddings_to_add.append(embedding_vector)
                metadatas_to_add.append({
                    "file_id": file.id,
                    "file_path": file.file_path,
                    "chunk_index": i,
                    "chunk_hash": chunk_hash,
                    "title": file.title,
                    "vector_model": self.embedding_model
                })
                ids_to_add.append(chunk_id)
                documents_to_add.append(text)
                
                # 保存到SQLite（仅元数据，不存储向量）
                embedding = Embedding(
                    file_id=file.id,
                    chunk_index=i,
                    chunk_text=text,
                    chunk_hash=chunk_hash,
                    embedding_vector=b'',  # 空向量，实际向量存储在ChromaDB
                    vector_model=self.embedding_model
                )
                self.db.add(embedding)
            
            # 5. 批量添加到ChromaDB
            if embeddings_to_add:
                self.chroma_collection.add(
                    embeddings=embeddings_to_add,
                    metadatas=metadatas_to_add,
                    documents=documents_to_add,
                    ids=ids_to_add
                )
                logger.info(f"成功添加 {len(embeddings_to_add)} 个向量到ChromaDB")
            
            # 6. 提交SQLite事务
            self.db.commit()
            logger.info(f"为文件 {file.file_path} 创建了 {len(texts)} 个嵌入向量")
            return True
            
        except Exception as e:
            logger.error(f"创建嵌入失败: {e}")
            self.db.rollback()
            return False

    def semantic_search(self, query: str, limit: int = 10, similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """语义搜索 - 使用ChromaDB进行高性能向量搜索"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行语义搜索")
            return []
        
        try:
            # 如果没有传递相似度阈值，使用配置中的默认值
            if similarity_threshold is None:
                similarity_threshold = settings.semantic_search_threshold
                
            logger.info(f"开始语义搜索，查询: {query}, 阈值: {similarity_threshold}")
            
            # 1. 生成查询的嵌入向量
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                logger.error("无法为查询生成嵌入向量")
                return []
            
            logger.info(f"查询向量生成成功，维度: {len(query_embedding)}")
            
            # 2. 检查集合中的向量数量
            collection_count = self.chroma_collection.count()
            logger.info(f"ChromaDB集合中共有 {collection_count} 个向量")
            
            # 3. 使用ChromaDB进行向量搜索
            search_results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit * 2, collection_count),  # 获取更多结果用于过滤，但不超过总数
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"ChromaDB原始搜索结果: {len(search_results.get('ids', [[]])[0]) if search_results.get('ids') else 0} 个")
            
            # 4. 处理搜索结果
            results = []
            if search_results['ids'] and search_results['ids'][0]:
                logger.info(f"开始处理搜索结果，原始结果数: {len(search_results['ids'][0])}")
                
                for i, (doc_id, distance, document, metadata) in enumerate(zip(
                    search_results['ids'][0],
                    search_results['distances'][0],
                    search_results['documents'][0],
                    search_results['metadatas'][0]
                )):
                    # 计算相似度（ChromaDB返回的是距离，需要转换为相似度）
                    similarity = 1 - distance
                    
                    logger.debug(f"结果 {i}: 距离={distance:.4f}, 相似度={similarity:.4f}, 文档={document[:50]}...")
                    
                    # 过滤低相似度结果
                    if similarity < similarity_threshold:
                        logger.debug(f"相似度 {similarity:.4f} 低于阈值 {similarity_threshold}，跳过")
                        continue
                    
                    # 检查文件是否仍然存在且未删除
                    file = self.db.query(File).filter(
                        File.id == metadata['file_id'],
                        File.is_deleted == False
                    ).first()
                    
                    if file:
                        results.append({
                            'file_id': metadata['file_id'],
                            'file_path': metadata['file_path'],
                            'title': metadata['title'],
                            'chunk_text': document,
                            'chunk_index': metadata['chunk_index'],
                            'similarity': float(similarity),
                            'created_at': file.created_at.isoformat() if file.created_at else None,
                            'updated_at': file.updated_at.isoformat() if file.updated_at else None,
                        })
                        logger.debug(f"添加有效结果: {metadata['file_path']}, 相似度: {similarity:.4f}")
                    else:
                        logger.debug(f"文件不存在或已删除: file_id={metadata['file_id']}")
                    
                    # 限制结果数量
                    if len(results) >= limit:
                        break
            else:
                logger.warning("ChromaDB搜索返回空结果")
            
            logger.info(f"ChromaDB语义搜索完成，查询: {query}, 原始结果: {len(search_results.get('ids', [[]])[0]) if search_results.get('ids') else 0}, 过滤后结果: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"ChromaDB语义搜索失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []

    def clear_vector_database(self) -> bool:
        """清空向量数据库"""
        try:
            # 1. 清空SQLite中的嵌入向量
            self.db.query(Embedding).delete()
            self.db.commit()
            
            # 2. 重置ChromaDB集合
            if self.chroma_client and self.chroma_collection:
                try:
                    # 删除现有集合
                    self.chroma_client.delete_collection(name=self.collection_name)
                    # 重新创建集合
                    self.chroma_collection = self.chroma_client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "AI笔记本文档嵌入向量"}
                    )
                    logger.info("ChromaDB集合已重置")
                except Exception as e:
                    logger.warning(f"重置ChromaDB集合时出错: {e}")
            
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
            
            # 2. 删除ChromaDB中的向量
            if self.chroma_collection:
                try:
                    # 获取该文件的所有向量ID
                    existing_results = self.chroma_collection.get(
                        where={"file_id": file_id}
                    )
                    if existing_results['ids']:
                        self.chroma_collection.delete(ids=existing_results['ids'])
                        logger.info(f"从ChromaDB删除文件 {file_id} 的向量: {len(existing_results['ids'])} 个")
                except Exception as e:
                    logger.warning(f"从ChromaDB删除向量时出错: {e}")
            
            self.db.commit()
            logger.info(f"成功删除文件的向量索引: file_id={file_id}, SQLite删除了 {deleted_count} 个记录")
            return True
            
        except Exception as e:
            logger.error(f"删除文件向量索引失败: file_id={file_id}, 错误: {e}")
            self.db.rollback()
            return False
    
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

    def get_vector_count(self) -> int:
        """获取向量数据库中的向量数量"""
        try:
            if self.chroma_collection:
                count = self.chroma_collection.count()
                return count
            return 0
        except Exception as e:
            logger.error(f"获取向量数量失败: {e}")
            return 0

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """内容分析"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法分析内容")
            return {}
        
        try:
            prompt = f"""
            请分析以下内容，提供以下信息：
            1. 主要话题
            2. 内容类型（技术文档、笔记、总结等）
            3. 重要性评分（1-10）
            4. 建议的处理方式
            
            内容：
            {content[:1500]}
            
            请以JSON格式返回分析结果。
            """
            
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
        if not self.is_available():
            logger.warning("AI服务不可用，无法生成相关问题")
            return []
        
        try:
            prompt = f"""
            基于以下内容，生成{num_questions}个相关的问题，这些问题应该能够帮助用户更深入地理解内容：
            
            内容：
            {content[:1500]}
            
            请只返回问题列表，每行一个问题：
            """
            
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
        """智能发现文章间的链接关系"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行智能链接发现")
            return []
        
        try:
            # 使用语义搜索找到相关文件 - 智能链接使用更高的阈值确保链接质量
            link_threshold = max(settings.semantic_search_threshold + 0.2, 0.6)  # 至少0.6，确保链接质量
            semantic_results = self.semantic_search(content, limit=10, similarity_threshold=link_threshold)
            
            # 过滤掉当前文件
            semantic_results = [r for r in semantic_results if r.get('file_id') != file_id]
            
            if not semantic_results:
                return []

            # 获取其他文件信息
            other_files = self.db.query(File).filter(
                File.id != file_id,
                File.is_deleted == False
            ).all()
            
            # 使用AI分析链接关系
            related_files_info = []
            for result in semantic_results[:5]:  # 只分析前5个最相关的文件
                file_info = next((f for f in other_files if f.id == result['file_id']), None)
                if file_info:
                    related_files_info.append({
                        'id': file_info.id,
                        'title': file_info.title,
                        'content_preview': file_info.content[:200],
                        'similarity': result.get('similarity', 0)
                    })
            
            if not related_files_info:
                return []
            
            # 构建AI提示词
            files_text = "\n".join([
                f"文件{i+1}: {f['title']} (相似度: {f['similarity']:.2f})\n内容预览: {f['content_preview']}"
                for i, f in enumerate(related_files_info)
            ])
            
            prompt = f"""
            当前文档：
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
            
            只返回JSON，不要其他文字：
            """
            
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # 尝试解析JSON
            import json
            try:
                suggestions = json.loads(result_text)
                if isinstance(suggestions, list):
                    # 验证和清理建议
                    valid_suggestions = []
                    for suggestion in suggestions:
                        if all(key in suggestion for key in ['target_file_id', 'link_type', 'reason']):
                            # 确保target_file_id是有效的
                            target_id = suggestion['target_file_id']
                            if any(f['id'] == target_id for f in related_files_info):
                                valid_suggestions.append(suggestion)
                    
                    logger.info(f"智能链接发现成功，找到 {len(valid_suggestions)} 个建议")
                    return valid_suggestions
                else:
                    logger.error(f"AI返回的不是列表格式: {result_text}")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"无法解析AI返回的JSON: {e}, 原文: {result_text}")
                return []
                
        except Exception as e:
            logger.error(f"智能链接发现失败: {e}")
            return [] 