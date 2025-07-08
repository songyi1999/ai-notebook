import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from ..dynamic_config import settings

logger = logging.getLogger(__name__)


class SimpleMemoryService:
    """简化的记忆服务 - 使用JSON文件存储，由LLM管理记忆更新"""
    
    def __init__(self, memory_file_path: str = None):
        """初始化记忆服务
        
        Args:
            memory_file_path: 记忆文件路径，默认为 ./data/memory.json
        """
        if memory_file_path is None:
            # 默认保存到数据目录
            data_dir = Path("./data")
            data_dir.mkdir(exist_ok=True)
            memory_file_path = data_dir / "memory.json"
        
        self.memory_file_path = Path(memory_file_path)
        self.memory_data = self._load_memory()
        
        # 初始化LLM
        self.llm = None
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                openai_api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                temperature=0.1
            )
    
    def _load_memory(self) -> Dict[str, Any]:
        """从文件加载记忆数据"""
        try:
            if self.memory_file_path.exists():
                with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"加载记忆数据成功，共 {len(data.get('memories', []))} 条记忆")
                    return data
            else:
                logger.info("记忆文件不存在，创建新的记忆存储")
                return self._create_empty_memory()
        except Exception as e:
            logger.error(f"加载记忆文件失败: {e}，创建新的记忆存储")
            return self._create_empty_memory()
    
    def _create_empty_memory(self) -> Dict[str, Any]:
        """创建空的记忆结构"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "memories": [],
            "stats": {
                "total_memories": 0,
                "last_update": None,
                "access_count": 0
            }
        }
    
    def _save_memory(self) -> bool:
        """保存记忆数据到文件"""
        try:
            # 更新统计信息
            self.memory_data["updated_at"] = datetime.now().isoformat()
            self.memory_data["stats"]["total_memories"] = len(self.memory_data["memories"])
            self.memory_data["stats"]["last_update"] = datetime.now().isoformat()
            
            # 确保目录存在
            self.memory_file_path.parent.mkdir(exist_ok=True)
            
            # 保存到文件
            with open(self.memory_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"记忆数据保存成功: {self.memory_file_path}")
            return True
        except Exception as e:
            logger.error(f"保存记忆文件失败: {e}")
            return False
    
    def process_conversation(self, user_input: str, ai_response: str) -> Dict[str, Any]:
        """处理对话并更新记忆
        
        Args:
            user_input: 用户输入
            ai_response: AI回复
            
        Returns:
            处理结果，包含更新的记忆信息
        """
        if not self.llm:
            logger.warning("LLM未初始化，无法处理记忆")
            return {"status": "error", "message": "LLM未初始化"}
        
        try:
            # 构建当前对话文本
            conversation_text = f"用户: {user_input}\nAI: {ai_response}"
            
            # 获取当前记忆摘要
            current_memories_text = self._format_memories_for_llm()
            
            # 构建LLM提示词
            prompt = self._build_memory_update_prompt(conversation_text, current_memories_text)
            
            # 调用LLM分析和更新记忆
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # 解析LLM响应
            updated_memories = self._parse_llm_response(response.content)
            
            if updated_memories is not None:
                # 更新记忆数据
                old_count = len(self.memory_data["memories"])
                self.memory_data["memories"] = updated_memories
                new_count = len(updated_memories)
                
                # 保存到文件
                self._save_memory()
                
                logger.info(f"记忆更新成功: {old_count} -> {new_count} 条记忆")
                return {
                    "status": "success",
                    "old_count": old_count,
                    "new_count": new_count,
                    "memories": updated_memories
                }
            else:
                logger.error("LLM响应解析失败")
                return {"status": "error", "message": "LLM响应解析失败"}
                
        except Exception as e:
            logger.error(f"处理对话记忆失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _build_memory_update_prompt(self, conversation: str, current_memories: str) -> str:
        """构建记忆更新的LLM提示词"""
        return f"""你是一个智能记忆管理器。你的任务是分析用户对话，并决定如何更新用户的记忆库。

当前记忆库内容：
{current_memories}

新的对话内容：
{conversation}

请分析这次对话，并决定如何更新记忆库。你需要：

1. **评估重要性**：判断对话中哪些信息值得记住
2. **决定操作**：对于每条记忆，决定是保留、更新、合并还是删除
3. **提取新记忆**：从对话中提取新的重要信息

记忆评估标准：
- **核心身份信息**（姓名、年龄、职业）：重要性 1.0
- **重要偏好和习惯**：重要性 0.8-0.9
- **技能和目标**：重要性 0.7-0.8  
- **一般事实和偏好**：重要性 0.5-0.7
- **临时信息**：重要性 0.3-0.5
- **无关紧要的信息**：不保存

记忆类型：
- fact: 明确的事实信息
- preference: 用户偏好
- habit: 行为习惯
- skill: 技能能力
- goal: 目标计划
- event: 重要事件

请返回更新后的完整记忆数组，严格按照以下JSON格式：

```json
[
  {{
    "id": "unique_id",
    "content": "具体的记忆内容",
    "type": "记忆类型",
    "importance": 0.8,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "tags": ["标签1", "标签2"],
    "source": "conversation/manual/system"
  }}
]
```

重要规则：
1. 只返回JSON数组，不要任何其他文字
2. 保留重要的现有记忆，删除过时或不重要的
3. 合并相似的记忆信息
4. 为新记忆分配唯一ID
5. **根据重要性决定是否保存新信息**
6. **如果没有值得记忆的新信息，保持原有记忆不变**

请分析并返回更新后的记忆数组："""

    def _format_memories_for_llm(self) -> str:
        """将当前记忆格式化为LLM可读的文本"""
        if not self.memory_data["memories"]:
            return "当前记忆库为空。"
        
        memories_text = "当前记忆库：\n"
        for i, memory in enumerate(self.memory_data["memories"], 1):
            memories_text += f"{i}. [{memory.get('type', 'unknown')}] {memory.get('content', '')} "
            memories_text += f"(重要性: {memory.get('importance', 0.5)}, "
            memories_text += f"创建: {memory.get('created_at', '未知')}, "
            memories_text += f"ID: {memory.get('id', 'unknown')})\n"
        
        return memories_text
    
    def _parse_llm_response(self, response_content: str) -> Optional[List[Dict[str, Any]]]:
        """解析LLM返回的记忆更新结果"""
        try:
            # 清理响应内容
            content = response_content.strip()
            
            # 移除可能的markdown标记
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            
            if content.endswith('```'):
                content = content[:-3]
            
            content = content.strip()
            
            # 解析JSON
            memories = json.loads(content)
            
            # 验证数据格式
            if isinstance(memories, list):
                # 为每条记忆补充必要字段
                for memory in memories:
                    if 'id' not in memory or not memory['id']:
                        memory['id'] = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(memories)}"
                    if 'created_at' not in memory:
                        memory['created_at'] = datetime.now().isoformat()
                    if 'updated_at' not in memory:
                        memory['updated_at'] = datetime.now().isoformat()
                    if 'importance' not in memory:
                        memory['importance'] = 0.5
                    if 'source' not in memory:
                        memory['source'] = 'conversation'
                    if 'tags' not in memory:
                        memory['tags'] = []
                
                return memories
            else:
                logger.error("LLM返回的不是数组格式")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应内容: {response_content}")
            return None
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            return None
    
    def get_memories_for_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取记忆用于上下文，按重要性排序"""
        try:
            # 更新访问统计
            self.memory_data["stats"]["access_count"] += 1
            
            memories = self.memory_data["memories"]
            
            # 按重要性排序
            sorted_memories = sorted(
                memories, 
                key=lambda x: (x.get('importance', 0.5), x.get('updated_at', '')), 
                reverse=True
            )
            
            return sorted_memories[:limit]
        except Exception as e:
            logger.error(f"获取上下文记忆失败: {e}")
            return []
    
    def format_memories_for_prompt(self, limit: int = 10) -> str:
        """将记忆格式化为系统提示词"""
        memories = self.get_memories_for_context(limit)
        
        if not memories:
            logger.debug("🧠 format_memories_for_prompt: 没有记忆信息")
            return ""
        
        logger.info(f"🧠 格式化 {len(memories)} 条记忆用于提示词")
        for i, memory in enumerate(memories, 1):
            logger.info(f"   {i}. {memory.get('content', '')[:50]}...")
        
        memory_text = "=== 用户记忆信息 ===\n"
        
        # 按重要性分组
        high_importance = [m for m in memories if m.get('importance', 0.5) >= 0.8]
        medium_importance = [m for m in memories if 0.5 <= m.get('importance', 0.5) < 0.8]
        
        if high_importance:
            memory_text += "重要信息：\n"
            for memory in high_importance[:5]:
                memory_text += f"- {memory.get('content', '')}\n"
        
        if medium_importance and len(high_importance) < 5:
            memory_text += "其他信息：\n"
            remaining_slots = 5 - len(high_importance)
            for memory in medium_importance[:remaining_slots]:
                memory_text += f"- {memory.get('content', '')}\n"
        
        memory_text += "\n"
        return memory_text
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        memories = self.memory_data["memories"]
        
        # 按类型统计
        type_stats = {}
        importance_stats = {"high": 0, "medium": 0, "low": 0}
        
        for memory in memories:
            # 类型统计
            mem_type = memory.get('type', 'unknown')
            type_stats[mem_type] = type_stats.get(mem_type, 0) + 1
            
            # 重要性统计
            importance = memory.get('importance', 0.5)
            if importance >= 0.8:
                importance_stats["high"] += 1
            elif importance >= 0.5:
                importance_stats["medium"] += 1
            else:
                importance_stats["low"] += 1
        
        return {
            "total_memories": len(memories),
            "memory_types": type_stats,
            "importance_distribution": importance_stats,
            "file_path": str(self.memory_file_path),
            "last_updated": self.memory_data.get("updated_at"),
            "access_count": self.memory_data["stats"]["access_count"]
        }
    
    def add_manual_memory(self, content: str, memory_type: str = "fact", 
                         importance: float = 0.5, tags: List[str] = None) -> bool:
        """手动添加记忆"""
        try:
            if tags is None:
                tags = []
            
            new_memory = {
                "id": f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "content": content,
                "type": memory_type,
                "importance": importance,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": tags,
                "source": "manual"
            }
            
            self.memory_data["memories"].append(new_memory)
            return self._save_memory()
            
        except Exception as e:
            logger.error(f"手动添加记忆失败: {e}")
            return False
    
    def clear_memories(self) -> bool:
        """清空所有记忆"""
        try:
            self.memory_data["memories"] = []
            return self._save_memory()
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False
    
    def export_memories(self, export_path: str = None) -> str:
        """导出记忆到文件"""
        try:
            if export_path is None:
                export_path = f"memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"记忆导出成功: {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"导出记忆失败: {e}")
            return ""