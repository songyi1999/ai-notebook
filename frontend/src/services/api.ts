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

export interface TagWithStats extends TagData {
    usage_count: number;
    recent_files: string[];
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
    target_file_path: string;
    target_title: string;
    link_type: string;
    description: string;
    similarity: number;
}

export interface ChatRequest {
    question: string;
    max_context_length?: number;
    search_limit?: number;
}

export interface ChatResponse {
    answer: string;
    related_documents: Array<{
        file_id: number;
        file_path: string;
        title: string;
        similarity: number;
        chunk_text: string;
    }>;
    search_query: string;
    context_length?: number;
    processing_time?: number;
    error?: string;
}

// MCP相关接口
export interface MCPServer {
    id: number;
    name: string;
    description?: string;
    server_type: string;
    server_config: Record<string, any>;
    auth_type?: string;
    auth_config?: Record<string, any>;
    is_enabled: boolean;
    is_connected: boolean;
    connection_status?: string;
    last_connected_at?: string;
    error_message?: string;
    created_at: string;
    updated_at: string;
}

export interface MCPServerCreate {
    name: string;
    description?: string;
    server_type: string;
    server_config: Record<string, any>;
    auth_type?: string;
    auth_config?: Record<string, any>;
    is_enabled?: boolean;
}

export interface MCPTool {
    id: number;
    server_id: number;
    tool_name: string;
    tool_description?: string;
    input_schema?: Record<string, any>;
    output_schema?: Record<string, any>;
    is_available: boolean;
    usage_count: number;
    last_used_at?: string;
    created_at: string;
    updated_at: string;
}

export interface MCPToolCall {
    id: number;
    tool_id: number;
    session_id?: string;
    call_context?: string;
    input_data: Record<string, any>;
    output_data?: Record<string, any>;
    call_status: string;
    error_message?: string;
    execution_time_ms?: number;
    ai_reasoning?: string;
    user_feedback?: number;
    created_at: string;
}

export interface MCPStats {
    servers: {
        total: number;
        enabled: number;
        connected: number;
    };
    tools: {
        total: number;
        available: number;
    };
    calls: {
        total: number;
        success: number;
        success_rate: number;
    };
}

// 系统状态相关接口
export interface SystemStatus {
    total_files: number;
    total_embeddings: number;
    pending_tasks: number;
    vector_count_method?: string; // 'estimated' 表示估算值, 'exact' 表示精确值
    task_details: {
        by_status: Record<string, number>;
        by_type: Record<string, number>;
        pending_details: Record<string, number>;
    };
    last_updated: string;
}

export interface ProcessorStatus {
    running: boolean;
    pid?: number;
    status: string; // 'running' | 'idle' | 'error'
    message: string;
    pending_tasks?: number;
}

// 文件上传转换相关接口
export interface FileUploadResult {
    success: boolean;
    original_filename: string;
    converted_filename?: string;
    target_path?: string;
    content_length?: number;
    file_type?: string;
    error?: string;
}

export interface FileUploadSummary {
    total_files: number;
    processed_count: number;
    successful_count: number;
    failed_count: number;
    ignored_count: number;
    created_db_records: number;
}

export interface FileUploadResponse {
    success: boolean;
    message: string;
    summary: FileUploadSummary;
    details: {
        successful_conversions: FileUploadResult[];
        failed_conversions: FileUploadResult[];
        ignored_files: Array<{ filename: string; reason: string }>;
        created_files: Array<{
            file_id: number;
            file_path: string;
            original_filename: string;
            converted_filename: string;
        }>;
    };
    target_folder: string;
}

export interface SupportedFormatsResponse {
    supported_extensions: string[];
    max_file_size_mb: number;
    description: Record<string, string>;
}

// API客户端类
export class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    // 通用请求方法
    public async request<T>(
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

        // 处理204 No Content响应（无响应体）
        if (response.status === 204) {
            return undefined as T;
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
        return this.request<FileTreeNode[]>(`/files/tree/${encodeURIComponent(rootPath)}`);
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

    async getTagsWithStats(skip: number = 0, limit: number = 100): Promise<TagWithStats[]> {
        return this.request<TagWithStats[]>(`/tags-with-stats?skip=${skip}&limit=${limit}`);
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
            body: JSON.stringify({
                file_id: fileId,
                tag_id: tagId,
                relevance_score: 1.0,
                is_manual: true
            }),
        });
    }

    async getFileTags(fileId: number): Promise<FileTagData[]> {
        return this.request<FileTagData[]>(`/files/${fileId}/tags`);
    }

    async getFileTagsWithDetails(fileId: number): Promise<TagData[]> {
        const fileTagsWithDetails = await this.request<any[]>(`/files/${fileId}/tags/with-details`);
        // 从文件标签关联数据中提取标签信息
        return fileTagsWithDetails.map(fileTag => fileTag.tag);
    }

    async deleteFileTag(fileId: number, tagId: number): Promise<void> {
        return this.request<void>(`/files/${fileId}/tags/${tagId}`, {
            method: 'DELETE',
        });
    }

    // AI内容生成API
    async generateSummary(content: string, maxLength: number = 200): Promise<string> {
        const response = await this.request<{ summary: string }>('/ai/summary', {
            method: 'POST',
            body: JSON.stringify({ content, max_length: maxLength }),
        });
        return response.summary;
    }

    async generateOutline(content: string, maxItems: number = 10): Promise<string> {
        const response = await this.request<{ outline: string }>('/ai/outline', {
            method: 'POST',
            body: JSON.stringify({ content, max_items: maxItems }),
        });
        return response.outline;
    }

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

    // AI服务相关接口
    async chat(request: ChatRequest): Promise<ChatResponse> {
        const response = await fetch(`${this.baseUrl}/ai/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || '智能问答请求失败');
        }

        return response.json();
    }

    // 获取系统状态
    async getSystemStatus(): Promise<SystemStatus> {
        const response = await this.request<{ success: boolean; data: SystemStatus }>('/index/system-status');
        return response.data;
    }

    // 获取任务处理器状态
    async getProcessorStatus(): Promise<ProcessorStatus> {
        const response = await this.request<{ success: boolean; data: ProcessorStatus }>('/index/processor/status');
        return response.data;
    }

    // 启动任务处理器
    async startProcessor(force: boolean = false): Promise<{ success: boolean; message: string; data: ProcessorStatus }> {
        return this.request<{ success: boolean; message: string; data: ProcessorStatus }>('/index/processor/start', {
            method: 'POST',
            body: JSON.stringify({ force })
        });
    }

    // 停止任务处理器
    async stopProcessor(): Promise<{ success: boolean; message: string; data: ProcessorStatus }> {
        return this.request<{ success: boolean; message: string; data: ProcessorStatus }>('/index/processor/stop', {
            method: 'POST'
        });
    }

    // 文件上传转换API
    async uploadAndConvertFiles(files: File[], targetFolder?: string): Promise<FileUploadResponse> {
        const formData = new FormData();

        // 添加文件
        files.forEach((file) => {
            formData.append('files', file);
        });

        // 添加目标文件夹
        if (targetFolder) {
            formData.append('target_folder', targetFolder);
        }

        const response = await fetch(`${this.baseUrl}/file-upload/upload-and-convert`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || '文件上传转换失败');
        }

        return response.json();
    }

    // 获取支持的文件格式
    async getSupportedFormats(): Promise<SupportedFormatsResponse> {
        return this.request<SupportedFormatsResponse>('/file-upload/supported-formats');
    }

    /**
     * 获取文件的摘要内容（若无返回 null）
     */
    async getFileSummary(fileId: number): Promise<{ summary: string | null }> {
        return this.request<{ summary: string | null }>(`/files/${fileId}/summary`);
    }

    /**
     * 获取文件的提纲列表
     */
    async getFileOutline(fileId: number): Promise<{ outline: string[] }> {
        return this.request<{ outline: string[] }>(`/files/${fileId}/outline`);
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

export const getSearchHistory = (...args: Parameters<ApiClient['getSearchHistory']>) => apiClient.getSearchHistory(...args);
export const getPopularQueries = (...args: Parameters<ApiClient['getPopularQueries']>) => apiClient.getPopularQueries(...args);
export const moveFile = (...args: Parameters<ApiClient['moveFile']>) => apiClient.moveFile(...args);
// 标签相关导出
export const getTags = (...args: Parameters<ApiClient['getTags']>) => apiClient.getTags(...args);
export const getTagsWithStats = (...args: Parameters<ApiClient['getTagsWithStats']>) => apiClient.getTagsWithStats(...args);
export const getTag = (...args: Parameters<ApiClient['getTag']>) => apiClient.getTag(...args);
export const createTag = (...args: Parameters<ApiClient['createTag']>) => apiClient.createTag(...args);
export const updateTag = (...args: Parameters<ApiClient['updateTag']>) => apiClient.updateTag(...args);
export const deleteTag = (...args: Parameters<ApiClient['deleteTag']>) => apiClient.deleteTag(...args);

// 文件标签关联导出
export const createFileTag = (...args: Parameters<ApiClient['createFileTag']>) => apiClient.createFileTag(...args);
export const getFileTags = (...args: Parameters<ApiClient['getFileTags']>) => apiClient.getFileTags(...args);
export const getFileTagsWithDetails = (...args: Parameters<ApiClient['getFileTagsWithDetails']>) => apiClient.getFileTagsWithDetails(...args);
export const deleteFileTag = (...args: Parameters<ApiClient['deleteFileTag']>) => apiClient.deleteFileTag(...args);

// AI内容生成导出
export const generateSummary = (...args: Parameters<ApiClient['generateSummary']>) => apiClient.generateSummary(...args);
export const generateOutline = (...args: Parameters<ApiClient['generateOutline']>) => apiClient.generateOutline(...args);
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
export const chat = (...args: Parameters<ApiClient['chat']>) => apiClient.chat(...args);
export const getSystemStatus = (...args: Parameters<ApiClient['getSystemStatus']>) => apiClient.getSystemStatus(...args);

// 文件上传转换导出
export const uploadAndConvertFiles = (...args: Parameters<ApiClient['uploadAndConvertFiles']>) => apiClient.uploadAndConvertFiles(...args);
export const getSupportedFormats = (...args: Parameters<ApiClient['getSupportedFormats']>) => apiClient.getSupportedFormats(...args);

// MCP相关API方法
export const mcpApi = {
    // MCP服务器管理
    async getServers(): Promise<MCPServer[]> {
        return apiClient.request<MCPServer[]>('/mcp/servers');
    },

    async getServer(serverId: number): Promise<MCPServer> {
        return apiClient.request<MCPServer>(`/mcp/servers/${serverId}`);
    },

    async createServer(serverData: MCPServerCreate): Promise<MCPServer> {
        return apiClient.request<MCPServer>('/mcp/servers', {
            method: 'POST',
            body: JSON.stringify(serverData)
        });
    },

    async updateServer(serverId: number, serverData: Partial<MCPServerCreate>): Promise<MCPServer> {
        return apiClient.request<MCPServer>(`/mcp/servers/${serverId}`, {
            method: 'PUT',
            body: JSON.stringify(serverData)
        });
    },

    async deleteServer(serverId: number): Promise<void> {
        return apiClient.request<void>(`/mcp/servers/${serverId}`, {
            method: 'DELETE'
        });
    },

    async connectServer(serverId: number): Promise<{ message: string }> {
        return apiClient.request<{ message: string }>(`/mcp/servers/${serverId}/connect`, {
            method: 'POST'
        });
    },

    async disconnectServer(serverId: number): Promise<{ message: string }> {
        return apiClient.request<{ message: string }>(`/mcp/servers/${serverId}/disconnect`, {
            method: 'POST'
        });
    },

    // MCP工具管理
    async getTools(): Promise<MCPTool[]> {
        return apiClient.request<MCPTool[]>('/mcp/tools');
    },

    async getTool(toolId: number): Promise<MCPTool> {
        return apiClient.request<MCPTool>(`/mcp/tools/${toolId}`);
    },

    async discoverTools(serverId: number): Promise<{ message: string; tools_count: number }> {
        return apiClient.request<{ message: string; tools_count: number }>(`/mcp/servers/${serverId}/discover-tools`, {
            method: 'POST'
        });
    },

    // MCP调用历史
    async getToolCalls(params?: {
        limit?: number;
        tool_id?: number;
        session_id?: string;
    }): Promise<MCPToolCall[]> {
        const searchParams = new URLSearchParams();
        if (params?.limit) searchParams.set('limit', params.limit.toString());
        if (params?.tool_id) searchParams.set('tool_id', params.tool_id.toString());
        if (params?.session_id) searchParams.set('session_id', params.session_id);

        const queryString = searchParams.toString();
        return apiClient.request<MCPToolCall[]>(`/mcp/tool-calls${queryString ? '?' + queryString : ''}`);
    },

    async getToolCall(callId: number): Promise<MCPToolCall> {
        return apiClient.request<MCPToolCall>(`/mcp/tool-calls/${callId}`);
    },

    // MCP统计信息
    async getStats(): Promise<MCPStats> {
        return apiClient.request<MCPStats>('/mcp/stats');
    }
};

// 任务处理器相关导出
export const getProcessorStatus = (...args: Parameters<ApiClient['getProcessorStatus']>) => apiClient.getProcessorStatus(...args);
export const startProcessor = (...args: Parameters<ApiClient['startProcessor']>) => apiClient.startProcessor(...args);
export const stopProcessor = (...args: Parameters<ApiClient['stopProcessor']>) => apiClient.stopProcessor(...args);

// 摘要/提纲
export const getFileSummary = (...args: Parameters<ApiClient['getFileSummary']>) => apiClient.getFileSummary(...args);
export const getFileOutline = (...args: Parameters<ApiClient['getFileOutline']>) => apiClient.getFileOutline(...args); 