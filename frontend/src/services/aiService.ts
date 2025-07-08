/**
 * AI服务增强层 - 支持智能降级
 * 当AI功能不可用时，自动降级到基础功能
 */

import { 
  search as baseSearch, 
  chat as baseChat, 
  suggestTags as baseSuggestTags,
  discoverSmartLinks as baseDiscoverSmartLinks,
  getAIStatus,
  type SearchResponse,
  type ChatRequest,
  type ChatResponse,
  type SmartLinkSuggestion
} from './api';

interface AIServiceStatus {
  enabled: boolean;
  available: boolean;
  lastChecked: number;
  cacheDuration: number; // 缓存持续时间（毫秒）
}

class AIService {
  private status: AIServiceStatus = {
    enabled: true,
    available: false,
    lastChecked: 0,
    cacheDuration: 30000 // 30秒缓存
  };

  /**
   * 检查AI服务状态
   */
  async checkAIStatus(forceRefresh: boolean = false): Promise<boolean> {
    const now = Date.now();
    
    // 如果缓存有效且不强制刷新，返回缓存结果
    if (!forceRefresh && (now - this.status.lastChecked) < this.status.cacheDuration) {
      return this.status.available;
    }

    try {
      // 检查配置状态
      const configResponse = await fetch('/api/v1/config/status');
      if (configResponse.ok) {
        const configData = await configResponse.json();
        this.status.enabled = configData.enabled || false;
      }

      // 如果AI在配置中被禁用，直接返回false
      if (!this.status.enabled) {
        this.status.available = false;
        this.status.lastChecked = now;
        return false;
      }

      // 检查AI服务可用性
      const aiStatus = await getAIStatus();
      this.status.available = aiStatus.available;
      this.status.lastChecked = now;
      
      return this.status.available;
    } catch (error) {
      console.warn('AI状态检查失败，假设AI不可用:', error);
      this.status.available = false;
      this.status.lastChecked = now;
      return false;
    }
  }

  /**
   * 获取当前AI状态
   */
  getStatus(): AIServiceStatus {
    return { ...this.status };
  }

  /**
   * 智能搜索 - 支持降级
   */
  async search(
    query: string,
    searchType: 'keyword' | 'semantic' | 'mixed' = 'mixed',
    limit: number = 50,
    similarityThreshold?: number
  ): Promise<SearchResponse & { degraded?: boolean; degradationReason?: string }> {
    const aiAvailable = await this.checkAIStatus();

    // AI不可用时的降级逻辑
    if (!aiAvailable && (searchType === 'semantic' || searchType === 'mixed')) {
      console.info('AI不可用，搜索降级为关键词搜索');
      
      try {
        const result = await baseSearch(query, 'keyword', limit);
        return {
          ...result,
          degraded: true,
          degradationReason: this.status.enabled ? 'AI服务暂时不可用' : 'AI功能已禁用'
        };
      } catch (error) {
        console.error('关键词搜索也失败:', error);
        throw new Error('搜索服务不可用');
      }
    }

    // AI可用或用户明确选择关键词搜索
    try {
      return await baseSearch(query, searchType, limit, similarityThreshold);
    } catch (error) {
      // 如果AI搜索失败，尝试降级到关键词搜索
      if (searchType !== 'keyword') {
        console.warn('AI搜索失败，降级到关键词搜索:', error);
        try {
          const result = await baseSearch(query, 'keyword', limit);
          return {
            ...result,
            degraded: true,
            degradationReason: 'AI搜索失败，已降级'
          };
        } catch (fallbackError) {
          console.error('关键词搜索降级也失败:', fallbackError);
          throw new Error('搜索服务不可用');
        }
      }
      throw error;
    }
  }

  /**
   * AI聊天 - 支持降级
   */
  async chat(request: ChatRequest): Promise<ChatResponse & { degraded?: boolean }> {
    const aiAvailable = await this.checkAIStatus();

    if (!aiAvailable) {
      const errorMessage = this.status.enabled 
        ? '抱歉，AI服务暂时不可用。请检查网络连接或稍后重试。'
        : '抱歉，AI功能已被禁用。系统当前运行在纯笔记模式下。';
      
      return {
        answer: errorMessage,
        related_documents: [],
        search_query: request.question,
        degraded: true
      };
    }

    try {
      return await baseChat(request);
    } catch (error) {
      console.error('AI聊天失败:', error);
      
      return {
        answer: '抱歉，AI服务暂时不可用。请稍后重试。',
        related_documents: [],
        search_query: request.question,
        degraded: true
      };
    }
  }

  /**
   * 智能标签建议 - 支持降级
   */
  async suggestTags(
    title: string, 
    content: string, 
    maxTags: number = 5
  ): Promise<{ tags: string[]; degraded?: boolean; degradationReason?: string }> {
    const aiAvailable = await this.checkAIStatus();

    if (!aiAvailable) {
      // 降级为基于关键词的简单标签生成
      const simpleTags = this.generateSimpleTags(title, content, maxTags);
      return {
        tags: simpleTags,
        degraded: true,
        degradationReason: this.status.enabled ? 'AI服务暂时不可用' : 'AI功能已禁用'
      };
    }

    try {
      const tags = await baseSuggestTags(title, content, maxTags);
      return { tags };
    } catch (error) {
      console.warn('AI标签建议失败，使用简单标签生成:', error);
      const simpleTags = this.generateSimpleTags(title, content, maxTags);
      return {
        tags: simpleTags,
        degraded: true,
        degradationReason: 'AI标签生成失败'
      };
    }
  }

  /**
   * 智能链接发现 - 支持降级
   */
  async discoverSmartLinks(fileId: number): Promise<{ 
    suggestions: SmartLinkSuggestion[]; 
    degraded?: boolean; 
    degradationReason?: string 
  }> {
    const aiAvailable = await this.checkAIStatus();

    if (!aiAvailable) {
      return {
        suggestions: [],
        degraded: true,
        degradationReason: this.status.enabled ? 'AI服务暂时不可用' : 'AI功能已禁用'
      };
    }

    try {
      const suggestions = await baseDiscoverSmartLinks(fileId);
      return { suggestions };
    } catch (error) {
      console.warn('智能链接发现失败:', error);
      return {
        suggestions: [],
        degraded: true,
        degradationReason: '智能链接发现失败'
      };
    }
  }

  /**
   * 生成简单标签（基于关键词的降级实现）
   */
  private generateSimpleTags(title: string, content: string, maxTags: number): string[] {
    const text = `${title} ${content}`.toLowerCase();
    const tags = new Set<string>();

    // 预定义的常用标签
    const commonTags = [
      '笔记', '文档', '重要', '学习', '工作', '总结', '参考',
      '代码', '技术', '前端', '后端', '数据库', '算法',
      '会议', '计划', '想法', '项目', '任务'
    ];

    // 检查预定义标签
    for (const tag of commonTags) {
      if (text.includes(tag) && tags.size < maxTags) {
        tags.add(tag);
      }
    }

    // 基于文件名推断
    if (title.includes('.md')) tags.add('Markdown');
    if (title.includes('.js') || title.includes('.ts')) tags.add('代码');
    if (title.includes('会议') || title.includes('meeting')) tags.add('会议');
    if (title.includes('TODO') || title.includes('任务')) tags.add('任务');

    // 如果没有找到合适的标签，添加通用标签
    if (tags.size === 0) {
      tags.add('笔记');
    }

    return Array.from(tags).slice(0, maxTags);
  }

  /**
   * 手动刷新AI状态
   */
  async refreshStatus(): Promise<boolean> {
    return this.checkAIStatus(true);
  }

  /**
   * 获取降级模式信息
   */
  getDegradationInfo(): { mode: string; description: string } {
    if (!this.status.enabled) {
      return {
        mode: 'notes_only',
        description: '纯笔记模式：AI功能已禁用，系统仅提供基础笔记管理功能。'
      };
    }
    
    if (!this.status.available) {
      return {
        mode: 'limited',
        description: '有限模式：AI服务暂时不可用，部分功能已降级为基础实现。'
      };
    }

    return {
      mode: 'full',
      description: '完整模式：所有AI功能正常可用。'
    };
  }
}

// 创建全局AI服务实例
export const aiService = new AIService();

// 导出增强的API方法
export const enhancedSearch = (
  query: string,
  searchType: 'keyword' | 'semantic' | 'mixed' = 'mixed',
  limit: number = 50,
  similarityThreshold?: number
) => aiService.search(query, searchType, limit, similarityThreshold);

export const enhancedChat = (request: ChatRequest) => aiService.chat(request);

export const enhancedSuggestTags = (
  title: string, 
  content: string, 
  maxTags: number = 5
) => aiService.suggestTags(title, content, maxTags);

export const enhancedDiscoverSmartLinks = (fileId: number) => 
  aiService.discoverSmartLinks(fileId);

// 导出AI状态相关方法
export const checkAIAvailability = () => aiService.checkAIStatus();
export const getAIServiceStatus = () => aiService.getStatus();
export const refreshAIStatus = () => aiService.refreshStatus();
export const getAIDegradationInfo = () => aiService.getDegradationInfo();