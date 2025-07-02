// API客户端配置
const API_BASE_URL = 'http://localhost:8000/api/v1';

// 文件接口
export interface FileData {
    id?: number;
    file_path: string;
    title: string;
    content: string;
    content_hash?: string;
    file_size?: number;
    created_at?: string;
    updated_at?: string;
    is_deleted?: boolean;
    parent_folder?: string;
    tags?: string[];
    file_metadata?: any;
}

// 文件树节点接口
export interface FileTreeNode {
    name: string;
    path: string;
    type: 'file' | 'directory';
    children?: FileTreeNode[];
    size?: number;
    modified?: string;
}

// 搜索结果接口
export interface SearchResult {
    file_id: number;
    file_path: string;
    title: string;
    content_preview: string;
    search_type: 'keyword' | 'semantic' | 'mixed';
    similarity?: number;
    chunk_index?: number;
    file_size?: number;
    created_at?: string;
    updated_at?: string;
    tags?: string[];
}

// 搜索响应接口
export interface SearchResponse {
    query: string;
    search_type: string;
    total: number;
    results: SearchResult[];
    response_time_ms: number;
}

// 搜索历史接口
export interface SearchHistory {
    id: number;
    query: string;
    search_type: string;
    results_count: number;
    response_time: number;
    created_at: string;
}

// 热门查询接口
export interface PopularQuery {
    query: string;
    search_count: number;
    avg_results: number;
}

// 标签接口
export interface TagData {
    id?: number;
    name: string;
    description?: string;
    color?: string;
    created_at?: string;
    updated_at?: string;
}

// 文件标签关联接口
export interface FileTagData {
    id?: number;
    file_id: number;
    tag_id: number;
    created_at?: string;
}

// 链接接口
export interface LinkData {
    id?: number;
    source_file_id: number;
    target_file_id: number;
    link_type: string;
    link_text?: string;
    anchor_text?: string;
    created_at?: string;
    updated_at?: string;
}

// 智能链接建议接口
export interface SmartLinkSuggestion {
    target_file_id: number;
    link_type: string;
    reason: string;
    suggested_text?: string;
}

// API客户端类
export class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    // 通用请求方法
    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const defaultOptions: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API请求失败: ${response.status} ${response.statusText} - ${errorText}`);
        }

        return response.json();
    }

    // 文件相关API
    async getFiles(skip: number = 0, limit: number = 100): Promise<FileData[]> {
        return this.request<FileData[]>(`/files?skip=${skip}&limit=${limit}`);
    }

    async getFile(fileId: number): Promise<FileData> {
        return this.request<FileData>(`/files/${fileId}`);
    }

    async getFileByPath(filePath: string): Promise<FileData> {
        const encodedPath = encodeURIComponent(filePath);
        return this.request<FileData>(`/files/by-path/${encodedPath}`);
    }

    async createFile(fileData: Omit<FileData, 'id'>): Promise<FileData> {
        return this.request<FileData>('/files', {
            method: 'POST',
            body: JSON.stringify(fileData),
        });
    }

    async updateFile(fileId: number, fileData: Partial<FileData>): Promise<FileData> {
        return this.request<FileData>(`/files/${fileId}`, {
            method: 'PUT',
            body: JSON.stringify(fileData),
        });
    }

    async updateFileByPath(filePath: string, fileData: Partial<FileData>): Promise<FileData> {
        const encodedPath = encodeURIComponent(filePath);
        return this.request<FileData>(`/files/by-path/${encodedPath}`, {
            method: 'PUT',
            body: JSON.stringify(fileData),
        });
    }

    async deleteFile(fileId: number, complete: boolean = false): Promise<{ success: boolean; message: string }> {
        const url = complete ? `/files/${fileId}?complete=true` : `/files/${fileId}`;
        return this.request<{ success: boolean; message: string }>(url, {
            method: 'DELETE',
        });
    }

    // 通过路径删除文件或文件夹
    async deleteFileByPath(filePath: string): Promise<{ success: boolean; message: string }> {
        return this.request<{ success: boolean; message: string }>('/files/delete-by-path', {
            method: 'POST',
            body: JSON.stringify({ file_path: filePath }),
        });
    }

    // 文件树API
    async getFileTree(rootPath: string = 'notes'): Promise<FileTreeNode[]> {
        const encodedPath = encodeURIComponent(rootPath);
        return this.request<FileTreeNode[]>(`/files/tree/${encodedPath}`);
    }

    // 创建目录
    async createDirectory(dirPath: string): Promise<{ success: boolean; message: string }> {
        return this.request<{ success: boolean; message: string }>('/files/create-directory', {
            method: 'POST',
            body: JSON.stringify({ path: dirPath }),
        });
    }

    // 移动文件或目录
    async moveFile(sourcePath: string, destinationPath: string): Promise<{ success: boolean; message: string }> {
        return this.request<{ success: boolean; message: string }>('/files/move', {
            method: 'POST',
            body: JSON.stringify({
                source_path: sourcePath,
                destination_path: destinationPath
            }),
        });
    }

    // 搜索相关API
    async search(
        query: string,
        searchType: 'keyword' | 'semantic' | 'mixed' = 'mixed',
        limit: number = 50,
        similarityThreshold?: number  // 可选参数，不传则使用后端配置的默认值
    ): Promise<SearchResponse> {
        const params = new URLSearchParams({
            q: query,
            search_type: searchType,
            limit: limit.toString(),
        });

        // 只有显式传递了相似度阈值才添加到参数中
        if (similarityThreshold !== undefined) {
            params.append('similarity_threshold', similarityThreshold.toString());
        }

        return this.request<SearchResponse>(`/files/search?${params}`);
    }

    // 保持旧接口兼容性
    async searchFiles(query: string, searchType: 'keyword' | 'semantic' | 'mixed' = 'mixed'): Promise<FileData[]> {
        const response = await this.search(query, searchType);
        // 将新格式转换为旧格式以保持兼容性
        return response.results.map(result => ({
            id: result.file_id,
            file_path: result.file_path,
            title: result.title,
            content: result.content_preview,
            file_size: result.file_size,
            created_at: result.created_at,
            updated_at: result.updated_at,
            tags: result.tags,
            is_deleted: false,
            parent_folder: '',
        }));
    }

    // 获取搜索历史
    async getSearchHistory(limit: number = 20): Promise<SearchHistory[]> {
        const response = await this.request<{ history: SearchHistory[] }>(`/files/search/history?limit=${limit}`);
        return response.history;
    }

    // 获取热门查询
    async getPopularQueries(limit: number = 10): Promise<PopularQuery[]> {
        const response = await this.request<{ popular_queries: PopularQuery[] }>(`/files/search/popular?limit=${limit}`);
        return response.popular_queries;
    }

    // 标签相关API
    async getTags(skip: number = 0, limit: number = 100): Promise<TagData[]> {
        return this.request<TagData[]>(`/tags?skip=${skip}&limit=${limit}`);
    }

    async getTag(tagId: number): Promise<TagData> {
        return this.request<TagData>(`/tags/${tagId}`);
    }

    async createTag(tagData: Omit<TagData, 'id'>): Promise<TagData> {
        return this.request<TagData>('/tags', {
            method: 'POST',
            body: JSON.stringify(tagData),
        });
    }

    async updateTag(tagId: number, tagData: Partial<TagData>): Promise<TagData> {
        return this.request<TagData>(`/tags/${tagId}`, {
            method: 'PUT',
            body: JSON.stringify(tagData),
        });
    }

    async deleteTag(tagId: number): Promise<void> {
        return this.request<void>(`/tags/${tagId}`, {
            method: 'DELETE',
        });
    }

    // 文件标签关联API
    async createFileTag(fileId: number, tagId: number): Promise<FileTagData> {
        return this.request<FileTagData>('/file_tags', {
            method: 'POST',
            body: JSON.stringify({ file_id: fileId, tag_id: tagId }),
        });
    }

    async getFileTags(fileId: number): Promise<FileTagData[]> {
        return this.request<FileTagData[]>(`/files/${fileId}/tags`);
    }

    async deleteFileTag(fileId: number, tagId: number): Promise<void> {
        return this.request<void>(`/files/${fileId}/tags/${tagId}`, {
            method: 'DELETE',
        });
    }

    // AI标签生成API
    async suggestTags(title: string, content: string, maxTags: number = 5): Promise<string[]> {
        const response = await this.request<{ tags: string[] }>('/ai/suggest-tags', {
            method: 'POST',
            body: JSON.stringify({ title, content, max_tags: maxTags }),
        });
        return response.tags;
    }

    // 链接相关API
    async getLinks(skip: number = 0, limit: number = 100): Promise<LinkData[]> {
        return this.request<LinkData[]>(`/links?skip=${skip}&limit=${limit}`);
    }

    async getLink(linkId: number): Promise<LinkData> {
        return this.request<LinkData>(`/links/${linkId}`);
    }

    async getFileLinks(fileId: number): Promise<LinkData[]> {
        return this.request<LinkData[]>(`/files/${fileId}/links`);
    }

    async createLink(linkData: Omit<LinkData, 'id'>): Promise<LinkData> {
        return this.request<LinkData>('/links', {
            method: 'POST',
            body: JSON.stringify(linkData),
        });
    }

    async updateLink(linkId: number, linkData: Partial<LinkData>): Promise<LinkData> {
        return this.request<LinkData>(`/links/${linkId}`, {
            method: 'PUT',
            body: JSON.stringify(linkData),
        });
    }

    async deleteLink(linkId: number): Promise<void> {
        return this.request<void>(`/links/${linkId}`, {
            method: 'DELETE',
        });
    }

    // 智能链接发现API
    async discoverSmartLinks(fileId: number): Promise<SmartLinkSuggestion[]> {
        const response = await this.request<{ suggestions: SmartLinkSuggestion[] }>(`/ai/discover-links/${fileId}`, {
            method: 'POST',
        });
        return response.suggestions;
    }

    // AI服务状态检查
    async getAIStatus(): Promise<{ available: boolean; openai_configured: boolean; base_url: string }> {
        return this.request<{ available: boolean; openai_configured: boolean; base_url: string }>('/ai/status');
    }

    // 健康检查
    async healthCheck(): Promise<{ status: string; service: string }> {
        const response = await fetch('http://localhost:8000/health');
        return response.json();
    }

    // 重新构建所有索引
    async rebuildIndex(): Promise<{ success: boolean; message: string }> {
        return this.request<{ success: boolean; message: string }>('/index/rebuild', {
            method: 'POST',
        });
    }
}

// 创建默认API客户端实例
export const apiClient = new ApiClient();

// 导出便捷方法（绑定到正确的上下文）
export const getFiles = (...args: Parameters<ApiClient['getFiles']>) => apiClient.getFiles(...args);
export const getFile = (...args: Parameters<ApiClient['getFile']>) => apiClient.getFile(...args);
export const getFileByPath = (...args: Parameters<ApiClient['getFileByPath']>) => apiClient.getFileByPath(...args);
export const createFile = (...args: Parameters<ApiClient['createFile']>) => apiClient.createFile(...args);
export const updateFile = (...args: Parameters<ApiClient['updateFile']>) => apiClient.updateFile(...args);
export const updateFileByPath = (...args: Parameters<ApiClient['updateFileByPath']>) => apiClient.updateFileByPath(...args);
export const deleteFile = (...args: Parameters<ApiClient['deleteFile']>) => apiClient.deleteFile(...args);
export const getFileTree = (...args: Parameters<ApiClient['getFileTree']>) => apiClient.getFileTree(...args);
export const createDirectory = (...args: Parameters<ApiClient['createDirectory']>) => apiClient.createDirectory(...args);
export const search = (...args: Parameters<ApiClient['search']>) => apiClient.search(...args);
export const searchFiles = (...args: Parameters<ApiClient['searchFiles']>) => apiClient.searchFiles(...args);
export const getSearchHistory = (...args: Parameters<ApiClient['getSearchHistory']>) => apiClient.getSearchHistory(...args);
export const getPopularQueries = (...args: Parameters<ApiClient['getPopularQueries']>) => apiClient.getPopularQueries(...args);
export const moveFile = (...args: Parameters<ApiClient['moveFile']>) => apiClient.moveFile(...args);
// 标签相关导出
export const getTags = (...args: Parameters<ApiClient['getTags']>) => apiClient.getTags(...args);
export const getTag = (...args: Parameters<ApiClient['getTag']>) => apiClient.getTag(...args);
export const createTag = (...args: Parameters<ApiClient['createTag']>) => apiClient.createTag(...args);
export const updateTag = (...args: Parameters<ApiClient['updateTag']>) => apiClient.updateTag(...args);
export const deleteTag = (...args: Parameters<ApiClient['deleteTag']>) => apiClient.deleteTag(...args);

// 文件标签关联导出
export const createFileTag = (...args: Parameters<ApiClient['createFileTag']>) => apiClient.createFileTag(...args);
export const getFileTags = (...args: Parameters<ApiClient['getFileTags']>) => apiClient.getFileTags(...args);
export const deleteFileTag = (...args: Parameters<ApiClient['deleteFileTag']>) => apiClient.deleteFileTag(...args);

// AI标签生成导出
export const suggestTags = (...args: Parameters<ApiClient['suggestTags']>) => apiClient.suggestTags(...args);

// 链接相关导出
export const getLinks = (...args: Parameters<ApiClient['getLinks']>) => apiClient.getLinks(...args);
export const getLink = (...args: Parameters<ApiClient['getLink']>) => apiClient.getLink(...args);
export const getFileLinks = (...args: Parameters<ApiClient['getFileLinks']>) => apiClient.getFileLinks(...args);
export const createLink = (...args: Parameters<ApiClient['createLink']>) => apiClient.createLink(...args);
export const updateLink = (...args: Parameters<ApiClient['updateLink']>) => apiClient.updateLink(...args);
export const deleteLink = (...args: Parameters<ApiClient['deleteLink']>) => apiClient.deleteLink(...args);

// 智能链接发现导出
export const discoverSmartLinks = (...args: Parameters<ApiClient['discoverSmartLinks']>) => apiClient.discoverSmartLinks(...args);

// AI服务状态导出
export const getAIStatus = (...args: Parameters<ApiClient['getAIStatus']>) => apiClient.getAIStatus(...args);
export const healthCheck = (...args: Parameters<ApiClient['healthCheck']>) => apiClient.healthCheck(...args);
export const deleteFileByPath = (...args: Parameters<ApiClient['deleteFileByPath']>) => apiClient.deleteFileByPath(...args);
export const rebuildIndex = (...args: Parameters<ApiClient['rebuildIndex']>) => apiClient.rebuildIndex(...args); 