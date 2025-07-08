from typing import List, Dict, Any, Optional, Union
import logging
from sqlalchemy.orm import Session
from datetime import datetime
import time

from ..models.file import File
from ..models.search_history import SearchHistory
from ..services.file_service import FileService
from ..services.ai_service_langchain import AIService
from ..dynamic_config import settings

logger = logging.getLogger(__name__)

class SearchService:
    """搜索服务类，统一管理所有搜索功能"""
    
    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService(db)
        self.ai_service = AIService(db)
    
    def search(
        self,
        query: str,
        search_type: str = "mixed",
        limit: int = 50,
        similarity_threshold: float = None
    ) -> Dict[str, Any]:
        """
        统一搜索入口
        
        Args:
            query: 搜索查询
            search_type: 搜索类型 ("keyword", "semantic", "mixed")
            limit: 结果限制
            similarity_threshold: 语义搜索相似度阈值
            
        Returns:
            搜索结果字典，包含结果和元数据
        """
        start_time = time.time()
        
        # 如果没有传递相似度阈值，使用配置中的默认值
        if similarity_threshold is None:
            similarity_threshold = settings.semantic_search_threshold
        
        try:
            degraded = False
            degradation_reason = None
            
            # 检查AI可用性并处理降级
            ai_available = self.ai_service.is_available()
            
            if search_type == "keyword":
                results = self._keyword_search(query, limit)
                result_type = "keyword"
            elif search_type == "semantic":
                if not ai_available:
                    # 语义搜索降级为关键词搜索
                    logger.warning("AI服务不可用，语义搜索降级为关键词搜索")
                    results = self._keyword_search(query, limit)
                    result_type = "keyword"
                    degraded = True
                    degradation_reason = "AI功能已禁用" if not settings.is_ai_enabled() else "AI服务暂时不可用"
                else:
                    results = self._semantic_search(query, limit, similarity_threshold)
                    result_type = "semantic"
            elif search_type == "mixed":
                if not ai_available:
                    # 混合搜索降级为关键词搜索
                    logger.warning("AI服务不可用，混合搜索降级为关键词搜索")
                    results = self._keyword_search(query, limit)
                    result_type = "keyword"
                    degraded = True
                    degradation_reason = "AI功能已禁用" if not settings.is_ai_enabled() else "AI服务暂时不可用"
                else:
                    results = self._mixed_search(query, limit, similarity_threshold)
                    result_type = "mixed"
            else:
                raise ValueError(f"不支持的搜索类型: {search_type}")
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 记录搜索历史
            self._record_search_history(query, result_type, len(results), response_time)
            
            response_data = {
                "query": query,
                "search_type": result_type,
                "total": len(results),
                "results": results,
                "response_time_ms": round(response_time, 2)
            }
            
            # 添加降级信息
            if degraded:
                response_data["degraded"] = True
                response_data["degradation_reason"] = degradation_reason
                
            return response_data
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            response_time = (time.time() - start_time) * 1000
            self._record_search_history(query, search_type, 0, response_time)
            raise
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """关键词搜索 - 返回所有匹配的文件"""
        try:
            files = self.file_service.search_files(query, limit=limit)
            return [self._file_to_dict(file, "keyword") for file in files]
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []
    
    def _semantic_search(self, query: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """语义搜索 - 返回前N个最相关的文件，并自动获取完整上下文"""
        try:
            if not self.ai_service.is_available():
                logger.warning("AI服务不可用，无法进行语义搜索")
                return []
            
            semantic_results = self.ai_service.semantic_search(
                query, limit, similarity_threshold
            )
            
            # 转换为统一格式并增强上下文
            results = []
            for result in semantic_results:
                enhanced_result = {
                    "file_id": result["file_id"],
                    "file_path": result["file_path"],
                    "title": result["title"],
                    "content_preview": result["chunk_text"][:200] + "..." if len(result["chunk_text"]) > 200 else result["chunk_text"],
                    "search_type": "semantic",
                    "similarity": result["similarity"],
                    "chunk_index": result["chunk_index"],
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                }
                
                # 增强知识检索：获取完整文档的总结和提纲
                logger.info(f"🔍 正在获取文件 {result['file_id']} 的增强上下文...")
                enhanced_context = self._get_enhanced_context(result["file_id"], result.get("chunk_text", ""))
                if enhanced_context:
                    enhanced_result["enhanced_context"] = enhanced_context
                    logger.info(f"✅ 获取到增强上下文 - 类型: {enhanced_context.get('chunk_type')}, 策略: {enhanced_context.get('enhancement_strategy')}")
                else:
                    logger.warning(f"⚠️ 文件 {result['file_id']} 未能获取增强上下文")
                
                results.append(enhanced_result)
            
            return results
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
    
    def _mixed_search(self, query: str, limit: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """混合搜索 - 结合关键词和语义搜索结果，包含增强上下文"""
        try:
            # 关键词搜索 - 获取所有匹配
            keyword_results = self._keyword_search(query, limit)
            
            # 语义搜索 - 获取前10个最相关
            semantic_limit = min(10, limit)
            semantic_results = self._semantic_search(query, semantic_limit, similarity_threshold)
            
            # 合并结果并去重
            combined_results = self._merge_search_results(keyword_results, semantic_results)
            
            # 限制最终结果数量
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            # 如果混合搜索失败，回退到关键词搜索
            return self._keyword_search(query, limit)
    
    def _merge_search_results(
        self, 
        keyword_results: List[Dict[str, Any]], 
        semantic_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并搜索结果并去重"""
        merged = []
        seen_file_ids = set()
        
        # 优先添加语义搜索结果（按相似度排序）
        for result in semantic_results:
            if result["file_id"] not in seen_file_ids:
                merged.append(result)
                seen_file_ids.add(result["file_id"])
        
        # 添加关键词搜索结果（去除重复）
        for result in keyword_results:
            if result["file_id"] not in seen_file_ids:
                merged.append(result)
                seen_file_ids.add(result["file_id"])
        
        return merged
    
    def _file_to_dict(self, file: File, search_type: str) -> Dict[str, Any]:
        """将File对象转换为字典格式"""
        content_preview = file.content[:200] + "..." if len(file.content) > 200 else file.content
        
        # 安全地处理datetime字段
        def safe_datetime_to_iso(dt_field):
            if dt_field is None:
                return None
            if hasattr(dt_field, 'isoformat'):
                return dt_field.isoformat()
            return str(dt_field)  # 如果已经是字符串，直接返回
        
        return {
            "file_id": file.id,
            "file_path": file.file_path,
            "title": file.title,
            "content_preview": content_preview,
            "search_type": search_type,
            "file_size": file.file_size,
            "created_at": safe_datetime_to_iso(file.created_at),
            "updated_at": safe_datetime_to_iso(file.updated_at),
            "tags": []  # 标签信息现在通过file_tags关联表获取
        }
    
    def _get_enhanced_context(self, file_id: int, chunk_text: str) -> Optional[Dict[str, Any]]:
        """获取增强的上下文信息 - 包括文档总结和提纲"""
        try:
            if not self.ai_service.is_available():
                return None
            
            # 获取文档的总结和提纲
            summary_and_outline = self.ai_service.get_document_summary_and_outline(file_id)
            
            if not summary_and_outline:
                return None
            
            # 根据检索到的内容类型决定返回策略
            chunk_type = self._detect_chunk_type(chunk_text)
            
            enhanced_context = {
                "chunk_type": chunk_type,
                "document_summary": summary_and_outline.get("summary", ""),
                "document_outline": summary_and_outline.get("outline", []),
                "enhancement_strategy": self._get_enhancement_strategy(chunk_type)
            }
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"获取增强上下文失败: {e}")
            return None
    
    def _detect_chunk_type(self, chunk_text: str) -> str:
        """检测文本块类型"""
        # 简单的启发式检测
        if len(chunk_text) < 100:
            return "outline"
        elif "总结" in chunk_text or "摘要" in chunk_text:
            return "summary"
        else:
            return "content"
    
    def _get_enhancement_strategy(self, chunk_type: str) -> str:
        """根据块类型返回增强策略"""
        if chunk_type == "content":
            return "提供完整文档的总结和提纲以丰富上下文"
        elif chunk_type == "summary":
            return "提供完整文档的提纲以补充结构信息"
        elif chunk_type == "outline":
            return "提供完整文档的总结以补充内容概述"
        else:
            return "提供完整文档的总结和提纲"
    
    def _record_search_history(
        self, 
        query: str, 
        search_type: str, 
        results_count: int, 
        response_time: float
    ) -> None:
        """记录搜索历史"""
        try:
            search_history = SearchHistory(
                query=query,
                search_type=search_type,
                results_count=results_count,
                response_time=response_time
            )
            
            self.db.add(search_history)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"记录搜索历史失败: {e}")
            # 不影响搜索功能，只记录错误
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        try:
            histories = (
                self.db.query(SearchHistory)
                .order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": h.id,
                    "query": h.query,
                    "search_type": h.search_type,
                    "results_count": h.results_count,
                    "response_time": h.response_time,
                    "created_at": h.created_at.isoformat() if h.created_at else None
                }
                for h in histories
            ]
            
        except Exception as e:
            logger.error(f"获取搜索历史失败: {e}")
            return []
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门搜索查询"""
        try:
            # 简单统计：按查询分组，计算出现次数
            from sqlalchemy import func
            
            popular = (
                self.db.query(
                    SearchHistory.query,
                    func.count(SearchHistory.id).label('count'),
                    func.avg(SearchHistory.results_count).label('avg_results')
                )
                .group_by(SearchHistory.query)
                .order_by(func.count(SearchHistory.id).desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "query": p.query,
                    "search_count": p.count,
                    "avg_results": round(p.avg_results, 1)
                }
                for p in popular
            ]
            
        except Exception as e:
            logger.error(f"获取热门查询失败: {e}")
            return [] 