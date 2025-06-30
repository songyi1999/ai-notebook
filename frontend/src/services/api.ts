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

    async deleteFile(fileId: number): Promise<void> {
        return this.request<void>(`/files/${fileId}`, {
            method: 'DELETE',
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

    // 搜索文件
    async searchFiles(query: string, searchType: 'keyword' | 'semantic' | 'mixed' = 'mixed'): Promise<FileData[]> {
        const params = new URLSearchParams({
            q: query,
            search_type: searchType,
        });
        return this.request<FileData[]>(`/files/search?${params}`);
    }

    // 标签相关API
    async getTags(): Promise<any[]> {
        return this.request<any[]>('/tags');
    }

    async createTag(tagData: any): Promise<any> {
        return this.request<any>('/tags', {
            method: 'POST',
            body: JSON.stringify(tagData),
        });
    }

    // 健康检查
    async healthCheck(): Promise<{ status: string; service: string }> {
        const response = await fetch('http://localhost:8000/health');
        return response.json();
    }
}

// 创建默认API客户端实例
export const apiClient = new ApiClient();

// 导出便捷方法
export const {
    getFiles,
    getFile,
    getFileByPath,
    createFile,
    updateFile,
    deleteFile,
    getFileTree,
    createDirectory,
    searchFiles,
    getTags,
    createTag,
    healthCheck,
} = apiClient; 