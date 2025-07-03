import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button, Input, Space, message, Tabs, Typography, Spin, Divider } from 'antd';
import { SaveOutlined, FileTextOutlined, EyeOutlined, EditOutlined, SyncOutlined, DatabaseOutlined, ClockCircleOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { apiClient, SystemStatus } from '../services/api';

const { Text } = Typography;

// 初始化 Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value;
      } catch (__) {}
    }
    return '';
  }
});

interface NoteFile {
  id?: number;
  title: string;
  content: string;
  file_path: string;
  created_at?: string;
  updated_at?: string;
  file_size?: number;
}

interface FileResponse extends NoteFile {
  //
}

interface NoteEditorProps {
  currentFile?: {
    path: string;
    name: string;
  } | null;
  onFileChange?: (filePath: string, fileName: string) => void;
}

const NoteEditor: React.FC<NoteEditorProps> = ({ currentFile, onFileChange }) => {
  // 获取默认内容
  const getDefaultContent = () => {
    if (currentFile) {
      return {
        title: currentFile.name.replace('.md', ''),
        content: `# ${currentFile.name.replace('.md', '')}\n\n`,
        file_path: currentFile.path
      };
    }
    
    return {
      title: '欢迎使用AI笔记本',
      content: `# 欢迎使用AI笔记本

这是一个**纯本地、AI增强**的个人知识管理系统。

## 主要功能

- 📝 **Markdown编辑**：支持实时预览的Markdown编辑器
- 🔗 **双向链接**：通过 [[链接]] 语法创建笔记间的关联
- 🔍 **智能搜索**：结合关键词和语义搜索
- 🤖 **AI问答**：基于你的笔记内容进行智能问答
- 🏷️ **标签管理**：自动提取和手动添加标签
- 📊 **关系图谱**：可视化笔记间的链接关系

## 开始使用

1. 在左侧文件树中选择或新建文件
2. 使用 Markdown 语法进行格式化
3. 通过 [[笔记名称]] 创建双向链接
4. 使用 #标签 为笔记添加标签
5. 点击保存按钮保存你的笔记

## 示例链接

- [[技术笔记]]
- [[学习计划]]
- [[项目管理]]

## 示例标签

#技术 #学习 #个人知识管理

---

开始你的知识管理之旅吧！ 🚀`,
      file_path: 'welcome.md'
    };
  };

  // 状态管理
  const [currentNote, setCurrentNote] = useState<NoteFile>(getDefaultContent());
  const [isModified, setIsModified] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [activeTab, setActiveTab] = useState('edit');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  


  // 使用useRef来在回调中获取最新的状态
  const noteRef = useRef(currentNote);
  useEffect(() => {
    noteRef.current = currentNote;
  }, [currentNote]);

  const isModifiedRef = useRef(isModified);
  useEffect(() => {
    isModifiedRef.current = isModified;
  }, [isModified]);

  // 加载文件内容
  const loadFileContent = async (filePath: string) => {
    try {
      const fileData = await apiClient.getFileByPath(filePath);
      setCurrentNote({
        id: fileData.id,
        title: fileData.title,
        content: fileData.content,
        file_path: fileData.file_path,
        created_at: fileData.created_at,
        updated_at: fileData.updated_at,
        file_size: fileData.file_size
      });
      console.log('文件加载成功:', fileData);
      setIsModified(false);
      setSaveStatus('saved');
    } catch (error) {
      console.error('加载文件失败:', error);
      // 如果加载失败，使用默认内容
      const fileName = filePath.split('/').pop()?.replace('.md', '') || '新文件';
      setCurrentNote({
        title: fileName,
        content: `# ${fileName}\n\n请在这里编写你的笔记内容...`,
        file_path: filePath
      });
      message.warning('文件加载失败，使用默认内容');
      setIsModified(true);
      setSaveStatus('unsaved');
    }
  };

  // 文件切换前的保存处理函数
  const handleFileSwitch = useCallback(async () => {
    // 如果当前有未保存的修改，立即保存
    if (isModifiedRef.current) {
      console.log('检测到未保存的修改，切换文件前自动保存');
      try {
        const noteToSave = noteRef.current;
        if (!noteToSave.title.trim()) {
          console.warn('标题为空，跳过保存');
          return;
        }

        setSaveStatus('saving');
        const originalPath = currentFile?.path;
        const hasPathChanged = originalPath && originalPath !== noteToSave.file_path;
        
        if (noteToSave.id) {
          // 如果文件路径发生了变化，需要先重命名文件
          if (hasPathChanged) {
            console.log('切换前检测到文件路径变化，执行重命名:', originalPath, '->', noteToSave.file_path);
            try {
              await apiClient.moveFile(originalPath, noteToSave.file_path);
              console.log('切换前文件重命名成功');
            } catch (error) {
              console.error('切换前文件重命名失败:', error);
              setSaveStatus('unsaved');
              return;
            }
          }
          
          await apiClient.updateFile(noteToSave.id, {
            title: noteToSave.title,
            content: noteToSave.content,
            file_path: noteToSave.file_path,
          });
        } else {
          await apiClient.createFile({
            title: noteToSave.title,
            content: noteToSave.content,
            file_path: noteToSave.file_path,
            parent_folder: noteToSave.file_path.split('/').slice(0, -1).join('/') || 'notes'
          });
        }
        
        setIsModified(false);
        setSaveStatus('saved');
        console.log('文件切换前保存成功');
      } catch (error) {
        console.error('切换文件前保存失败:', error);
        setSaveStatus('unsaved');
      }
    }
  }, [currentFile]);

  // 监听文件切换
  useEffect(() => {
    const switchFile = async () => {
      // 先保存当前文件（如果有修改）
      await handleFileSwitch();
      
      // 然后加载新文件
      if (currentFile) {
        loadFileContent(currentFile.path);
        console.log('切换到文件:', currentFile);
      } else {
        // 如果没有选中文件，则显示欢迎页
        setCurrentNote(getDefaultContent());
        setIsModified(false);
        setSaveStatus('saved');
      }
    };

    switchFile();
  }, [currentFile, handleFileSwitch]);

  // 保存笔记 - 使用 useCallback 避免不必要的重渲染
  const handleSave = useCallback(async () => {
    const noteToSave = noteRef.current;
    if (!noteToSave.title.trim()) {
      message.warning('请输入笔记标题');
      return;
    }

    setSaveStatus('saving');
    try {
      let savedFile: FileResponse;
      const originalPath = currentFile?.path;
      const hasPathChanged = originalPath && originalPath !== noteToSave.file_path;
      
      if (noteToSave.id) {
        // 如果文件路径发生了变化，需要先重命名文件
        if (hasPathChanged) {
          console.log('检测到文件路径变化，执行重命名:', originalPath, '->', noteToSave.file_path);
          try {
            await apiClient.moveFile(originalPath, noteToSave.file_path);
            console.log('文件重命名成功');
          } catch (error) {
            console.error('文件重命名失败:', error);
            message.error(`重命名失败: ${error instanceof Error ? error.message : '未知错误'}`);
            setSaveStatus('unsaved');
            return;
          }
        }
        
        // 更新现有文件
        savedFile = await apiClient.updateFile(noteToSave.id, {
          title: noteToSave.title,
          content: noteToSave.content,
          file_path: noteToSave.file_path,
        });
      } else {
        // 创建新文件
        savedFile = await apiClient.createFile({
          title: noteToSave.title,
          content: noteToSave.content,
          file_path: noteToSave.file_path,
          parent_folder: noteToSave.file_path.split('/').slice(0, -1).join('/') || 'notes'
        });
        // 更新当前笔记的ID
        setCurrentNote(prev => ({ ...prev, id: savedFile.id }));
      }
      
      // 更新文件信息
      setCurrentNote(prev => ({
        ...prev,
        id: savedFile.id,
        created_at: savedFile.created_at,
        updated_at: savedFile.updated_at,
        file_size: savedFile.file_size
      }));
      
      setIsModified(false);
      setSaveStatus('saved');
      
      // 如果文件名发生变化，通知父组件
      if (onFileChange && (hasPathChanged || currentFile?.path !== noteToSave.file_path)) {
        onFileChange(noteToSave.file_path, noteToSave.title);
      }

      console.log('保存笔记成功:', {
        id: savedFile.id,
        title: savedFile.title,
        path: savedFile.file_path,
        renamed: hasPathChanged,
        timestamp: new Date().toISOString()
      });

    } catch (error) {
      console.error('保存笔记失败:', error);
      message.error(`保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setSaveStatus('unsaved');
    }
  }, [onFileChange, currentFile]);

  // 自动保存逻辑 - 修改为30秒自动保存
  useEffect(() => {
    if (!isModified) return;

    const handler = setTimeout(() => {
      handleSave();
    }, 30000); // 30秒后自动保存

    // 清理函数
    return () => {
      clearTimeout(handler);
    };
  }, [isModified, handleSave]);


  // 快捷键保存 (Ctrl+S / Cmd+S)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        if (isModifiedRef.current) {
           handleSave();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleSave]);

  // 处理内容变化
  const handleContentChange = (value: string | undefined) => {
    setCurrentNote(prev => ({
      ...prev,
      content: value || ''
    }));
    setIsModified(true);
    setSaveStatus('unsaved');
  };

  // 处理标题变化
  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTitle = e.target.value;
    const oldPath = currentNote.file_path;
    const parentPath = oldPath.substring(0, oldPath.lastIndexOf('/'));
    const newPath = newTitle 
      ? `${parentPath}/${newTitle.replace(/[^\w\u4e00-\u9fa5.-]/g, '_')}.md` 
      : `${parentPath}/untitled.md`;

    setCurrentNote(prev => ({
      ...prev,
      title: newTitle,
      file_path: newPath,
    }));
    setIsModified(true);
    setSaveStatus('unsaved');
  };

  // 渲染Markdown预览
  const renderMarkdown = () => {
    return {
      __html: md.render(currentNote.content || '')
    };
  };

  // 渲染保存状态
  const renderSaveStatus = () => {
    switch(saveStatus) {
      case 'saving':
        return <><Spin indicator={<SyncOutlined spin />} size="small" /> 正在保存...</>;
      case 'saved':
        return <Text type="secondary">所有更改已保存</Text>;
      case 'unsaved':
        return <Text type="warning">有未保存的更改</Text>;
    }
  }

  // 计算字数（中文按字符计算，英文按单词计算）
  const getWordCount = () => {
    const content = currentNote.content || '';
    // 中文字符数
    const chineseCount = (content.match(/[\u4e00-\u9fa5]/g) || []).length;
    // 英文单词数
    const englishWords = content.replace(/[\u4e00-\u9fa5]/g, '').match(/\b\w+\b/g) || [];
    const englishCount = englishWords.length;
    
    return chineseCount + englishCount;
  };

  // 格式化时间 - 修复为使用本地时区
  const formatTime = (timestamp?: string) => {
    if (!timestamp) return '未知';
    try {
      // 创建Date对象时会自动转换为本地时区
      const date = new Date(timestamp);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Shanghai' // 明确指定东8区
      });
    } catch {
      return '格式错误';
    }
  };

  // 格式化文件大小
  const formatFileSize = (size?: number) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let unitIndex = 0;
    let fileSize = size;
    
    while (fileSize >= 1024 && unitIndex < units.length - 1) {
      fileSize /= 1024;
      unitIndex++;
    }
    
    return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
  };

  // 获取系统状态
  const loadSystemStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
    } catch (error) {
      console.error('获取系统状态失败:', error);
      // 静默失败，不显示错误消息
    } finally {
      setStatusLoading(false);
    }
  }, []);

  // 定期更新系统状态
  useEffect(() => {
    // 初始加载
    loadSystemStatus();
    
    // 每30秒更新一次系统状态
    const statusInterval = setInterval(loadSystemStatus, 30000);
    
    return () => {
      clearInterval(statusInterval);
    };
  }, [loadSystemStatus]);

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      minHeight: 0
    }}>
      {/* 顶部笔记信息栏 */}
      <div style={{ 
        padding: '8px 16px', 
        borderBottom: '1px solid #f0f0f0', 
        flexShrink: 0 
      }}>
        <Space>
          <FileTextOutlined />
          <Input 
            placeholder="输入笔记标题..."
            value={currentNote?.title || ''}
            onChange={handleTitleChange}
            style={{ 
              fontSize: '16px', 
              fontWeight: '500', 
              border: 'none', 
              boxShadow: 'none',
              width: '400px',  // 增加宽度到400px（约为原来的两倍）
              maxWidth: '60%'  // 设置最大宽度，避免在小屏幕上过宽
            }}
          />
        </Space>
      </div>

      {/* 编辑器和预览区域 */}
      <div style={{ 
        flex: 1, 
        minHeight: 0,
        overflow: 'hidden',
        position: 'relative'
      }}>
        <Tabs
          className="editor-tabs"
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ 
            height: '100%',
            minHeight: 0,
            overflow: 'hidden'
          }}
          tabBarExtraContent={
            <Space>
              {renderSaveStatus()}
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saveStatus === 'saving'}
                onClick={handleSave}
                disabled={!isModified && saveStatus !== 'unsaved'}
              >
                保存
              </Button>
            </Space>
          }
          items={[
            {
              key: 'edit',
              label: (
                <span>
                  <EditOutlined />
                  编辑
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  border: '1px solid #d9d9d9', 
                  borderRadius: '6px', 
                  overflow: 'hidden'
                }}>
                  <Editor
                    height="100%"
                    language="markdown"
                    value={currentNote.content}
                    onChange={handleContentChange}
                    options={{ 
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      automaticLayout: true
                    }}
                  />
                </div>
              )
            },
            {
              key: 'preview',
              label: (
                <span>
                  <EyeOutlined />
                  预览
                </span>
              ),
              children: (
                <div 
                  className="markdown-body"
                  style={{ 
                    height: '100%',
                    overflow: 'auto', 
                    padding: '16px'
                  }} 
                  dangerouslySetInnerHTML={renderMarkdown()} 
                />
              ),
            }
          ]}
        />
      </div>

      {/* 底部文件信息栏 - 修改样式并添加系统状态 */}
      <div style={{
        padding: '8px 16px',
        borderTop: '1px solid #d9d9d9',
        background: '#f5f5f5',
        fontSize: '12px',
        color: '#333',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 -1px 2px rgba(0,0,0,0.1)',
        minHeight: '32px',
        flexShrink: 0,
        overflow: 'auto'
      }}>
        {/* 左侧：文件信息 */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Space split={<span style={{ color: '#d9d9d9' }}>|</span>} size="small">
            <span>字数: {getWordCount()}</span>
            <span>路径: {currentNote.file_path}</span>
            <span>大小: {formatFileSize(currentNote.file_size)}</span>
            {currentNote.created_at && (
              <span>创建: {formatTime(currentNote.created_at)}</span>
            )}
            {currentNote.updated_at && (
              <span>修改: {formatTime(currentNote.updated_at)}</span>
            )}
          </Space>
        </div>

        {/* 右侧：系统状态 */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {statusLoading ? (
            <Spin indicator={<SyncOutlined spin />} size="small" />
          ) : systemStatus ? (
            <Space split={<Divider type="vertical" />} size="small">
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <FileTextOutlined style={{ color: '#1890ff' }} />
                文件: {systemStatus.total_files}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <DatabaseOutlined style={{ color: '#52c41a' }} />
                嵌入: {systemStatus.total_embeddings}
              </span>
              <span style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '4px',
                color: systemStatus.pending_tasks > 0 ? '#fa8c16' : '#52c41a'
              }}>
                <ClockCircleOutlined />
                待索引: {systemStatus.pending_tasks}
              </span>
            </Space>
          ) : (
            <Text type="secondary" style={{ fontSize: '12px' }}>系统状态加载中...</Text>
          )}
        </div>
      </div>


    </div>
  );
};

export default NoteEditor;
