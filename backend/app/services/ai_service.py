from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os

from ..models.file import File
from ..models.embedding import Embedding
from ..config import settings

logger = logging.getLogger(__name__)

class AIService:
    """AI服务类，提供智能功能"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = settings.openai_api_key
        self.openai_base_url = settings.openai_base_url
        
        # 初始化嵌入模型
        if self.openai_api_key:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                base_url=self.openai_base_url
            )
            self.llm = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=settings.openai_model
            )
        else:
            logger.warning("未配置OpenAI API密钥，AI功能将不可用")
            self.embeddings = None
            self.llm = None
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        
        # 初始化ChromaDB（如果需要）
        self.chroma_db_path = settings.chroma_db_path

    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return self.embeddings is not None and self.llm is not None

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
        """为文件创建向量嵌入"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法创建嵌入")
            return False
        
        try:
            # 分割文本
            texts = self.text_splitter.split_text(file.content)
            
            # 为每个文本块创建嵌入
            for i, text in enumerate(texts):
                # 生成嵌入向量
                embedding_vector = self.embeddings.embed_query(text)
                
                # 保存到数据库
                embedding = Embedding(
                    file_id=file.id,
                    chunk_index=i,
                    content=text,
                    embedding_vector=embedding_vector,
                    metadata_info={
                        "file_path": file.file_path,
                        "title": file.title,
                        "chunk_size": len(text)
                    }
                )
                
                self.db.add(embedding)
            
            self.db.commit()
            logger.info(f"为文件 {file.file_path} 创建了 {len(texts)} 个嵌入向量")
            return True
            
        except Exception as e:
            logger.error(f"创建嵌入失败: {e}")
            self.db.rollback()
            return False

    def semantic_search(self, query: str, limit: int = 10, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """语义搜索"""
        if not self.is_available():
            logger.warning("AI服务不可用，无法进行语义搜索")
            return []
        
        try:
            # 生成查询的嵌入向量
            query_embedding = self.embeddings.embed_query(query)
            
            # 这里需要实现向量相似度搜索
            # 由于SQLite不直接支持向量搜索，这里返回空结果
            # 在生产环境中，可以使用Chroma或其他向量数据库
            
            logger.info(f"语义搜索完成，查询: {query}")
            return []
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []

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
            基于以下内容，生成{num_questions}个相关的思考问题，帮助深入理解这个主题：
            
            内容：
            {content[:1000]}
            
            请每行一个问题：
            """
            
            response = self.llm.invoke(prompt)
            questions_text = response.content.strip()
            
            # 解析问题
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            questions = questions[:num_questions]
            
            logger.info(f"生成了 {len(questions)} 个相关问题")
            return questions
            
        except Exception as e:
            logger.error(f"生成相关问题失败: {e}")
            return [] 