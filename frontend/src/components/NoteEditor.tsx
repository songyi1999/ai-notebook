import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button, Input, Space, message, Tabs, Typography, Spin, Divider, Modal } from 'antd';
import { SaveOutlined, FileTextOutlined, EyeOutlined, EditOutlined, SyncOutlined, DatabaseOutlined, ClockCircleOutlined, CloseCircleOutlined, ExclamationCircleOutlined, TagOutlined, RobotOutlined, ShareAltOutlined, ToolOutlined, LinkOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { apiClient, SystemStatus, ProcessorStatus, search, getProcessorStatus, startProcessor, stopProcessor } from '../services/api';
import TagManager from './TagManager';
import AutoProcessor from './AutoProcessor';
import LinkGraph from './LinkGraph';
import MCPManager from './MCPManager';
import LinkManager from './LinkManager';

const { Text } = Typography;

// 双向链接的markdown-it插件
function wikiLinkPlugin(md: MarkdownIt) {
  md.inline.ruler.before('link', 'wikilink', function(state, silent) {
    const start = state.pos;
    const max = state.posMax;
    
    // 检查是否以[[开头
    if (start + 4 >= max) return false;
    if (state.src.slice(start, start + 2) !== '[[') return false;
    
    // 查找结束标记]]
    let pos = start + 2;
    let found = false;
    while (pos < max - 1) {
      if (state.src.slice(pos, pos + 2) === ']]') {
        found = true;
        break;
      }
      pos++;
    }
    
    if (!found) return false;
    
    // 提取链接文本
    const linkText = state.src.slice(start + 2, pos);
    if (!linkText.trim()) return false;
    
    if (!silent) {
      const token = state.push('wikilink', '', 0);
      token.content = linkText.trim();
      token.markup = '[[]]';
    }
    
    state.pos = pos + 2;
    return true;
  });
  
  md.renderer.rules.wikilink = function(tokens, idx) {
    const token = tokens[idx];
    const linkText = token.content;
    // 确保包含正确的CSS类和data属性
    return `<a href="#" class="wiki-link" data-link-target="${linkText.replace(/"/g, '&quot;')}">${linkText}</a>`;
  };
}

// 初始化 Markdown 解析器并添加双向链接插件
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
}).use(wikiLinkPlugin);

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
  const [processorStatus, setProcessorStatus] = useState<ProcessorStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [tagRefreshTrigger, setTagRefreshTrigger] = useState(0);
  


  // 使用useRef来在回调中获取最新的状态
  const noteRef = useRef(currentNote);
  useEffect(() => {
    noteRef.current = currentNote;
  }, [currentNote]);

  const isModifiedRef = useRef(isModified);
  useEffect(() => {
    isModifiedRef.current = isModified;
  }, [isModified]);

  // 处理双向链接点击
  const handleWikiLinkClick = useCallback(async (linkTarget: string) => {
    try {
      // 首先通过搜索API查找文件
      const searchResults = await search(linkTarget, 'keyword', 10);
      
      // 查找完全匹配的文件
      let targetFile = searchResults.results.find(result => 
        result.title.toLowerCase() === linkTarget.toLowerCase() ||
        result.file_path.toLowerCase().includes(linkTarget.toLowerCase())
      );
      
      if (targetFile) {
        // 如果找到文件，跳转到该文件
        if (onFileChange) {
          onFileChange(targetFile.file_path, targetFile.title);
        }
        message.success(`已跳转到文件: ${targetFile.title}`);
      } else {
        // 如果没找到文件，询问用户是否创建
        Modal.confirm({
          title: '文件不存在',
          icon: <ExclamationCircleOutlined />,
          content: `文件 "${linkTarget}" 不存在，是否创建新文件？`,
          okText: '创建',
          cancelText: '取消',
          onOk: async () => {
            try {
              // 创建新文件
              const newFilePath = `notes/${linkTarget}.md`;
              const newFile = await apiClient.createFile({
                title: linkTarget,
                content: `# ${linkTarget}\n\n`,
                file_path: newFilePath,
                parent_folder: 'notes'
              });
              
              // 跳转到新创建的文件
              if (onFileChange) {
                onFileChange(newFile.file_path, newFile.title);
              }
              message.success(`已创建并跳转到新文件: ${linkTarget}`);
            } catch (error) {
              console.error('创建文件失败:', error);
              message.error('创建文件失败');
            }
          }
        });
      }
    } catch (error) {
      console.error('查找文件失败:', error);
      message.error('查找文件失败');
    }
  }, [onFileChange]);

  // 设置点击事件监听器
  const previewRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const previewElement = previewRef.current;
    if (!previewElement) return;
    
    const handleClick = (e: Event) => {
      const target = e.target as HTMLElement;
      console.log('Click detected on:', target, 'Classes:', target.classList.toString());
      
      if (target.classList.contains('wiki-link')) {
        e.preventDefault();
        e.stopPropagation();
        
        const linkTarget = target.getAttribute('data-link-target');
        console.log('Wiki link clicked:', linkTarget);
        
        if (linkTarget) {
          handleWikiLinkClick(linkTarget);
        }
      }
    };
    
    // 使用事件委托，监听所有点击事件
    previewElement.addEventListener('click', handleClick, true);
    
    return () => {
      previewElement.removeEventListener('click', handleClick, true);
    };
  }, [handleWikiLinkClick, activeTab]); // 添加activeTab依赖，确保在切换标签时重新设置监听器

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
  const renderMarkdown = (content: string) => {
    return md.render(content || '');
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
      
      // 并行获取系统状态和任务处理器状态
      const [systemStatusResult, processorStatusResult] = await Promise.allSettled([
        apiClient.getSystemStatus(),
        getProcessorStatus()
      ]);
      
      if (systemStatusResult.status === 'fulfilled') {
        setSystemStatus(systemStatusResult.value);
      }
      
      if (processorStatusResult.status === 'fulfilled') {
        setProcessorStatus(processorStatusResult.value);
      }
    } catch (error) {
      console.error('获取系统状态失败:', error);
      // 静默失败，不显示错误消息
    } finally {
      setStatusLoading(false);
    }
  }, []);

  // 标签变化回调
  const handleTagsChange = useCallback((tags: any[]) => {
    // 这里可以处理标签变化的逻辑
    console.log('标签已更新:', tags);
  }, []);

  // 启动任务处理器
  const handleStartProcessor = useCallback(async (force: boolean = false) => {
    try {
      setStatusLoading(true);
      const result = await startProcessor(force);
      
      if (result.success) {
        message.success(result.message);
        setProcessorStatus(result.data);
      } else {
        message.warning(result.message);
      }
    } catch (error) {
      console.error('启动任务处理器失败:', error);
      message.error(`启动任务处理器失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setStatusLoading(false);
      // 刷新状态
      loadSystemStatus();
    }
  }, [loadSystemStatus]);

  // 停止任务处理器
  const handleStopProcessor = useCallback(async () => {
    try {
      setStatusLoading(true);
      const result = await stopProcessor();
      
      if (result.success) {
        message.success(result.message);
        setProcessorStatus(result.data);
      } else {
        message.warning(result.message);
      }
    } catch (error) {
      console.error('停止任务处理器失败:', error);
      message.error(`停止任务处理器失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setStatusLoading(false);
      // 刷新状态
      loadSystemStatus();
    }
  }, [loadSystemStatus]);

  // 定期更新系统状态
  useEffect(() => {
    // 初始加载
    loadSystemStatus();
    
    // 每30分钟更新一次系统状态（30 * 60 * 1000 = 1800000毫秒）
    const statusInterval = setInterval(loadSystemStatus, 1800000);
    
    return () => {
      clearInterval(statusInterval);
    };
  }, []); // 移除loadSystemStatus依赖，避免重新创建interval

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
                  ref={previewRef}
                  className="markdown-preview" 
                  style={{ 
                    height: '100%', 
                    overflow: 'auto', 
                    padding: '16px',
                    backgroundColor: '#fff'
                  }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(currentNote.content) }}
                />
              ),
            },
            {
              key: 'tags',
              label: (
                <span>
                  <TagOutlined />
                  标签
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  overflow: 'hidden'
                }}>
                  <TagManager
                    key={tagRefreshTrigger}
                    currentFileId={currentNote.id}
                    currentFileTitle={currentNote.title}
                    currentFileContent={currentNote.content}
                    onTagsChange={handleTagsChange}
                  />
                </div>
              )
            },
            {
              key: 'auto',
              label: (
                <span>
                  <RobotOutlined />
                  AI处理
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  overflow: 'hidden'
                }}>
                  <AutoProcessor
                    currentFileId={currentNote.id}
                    onProcessingComplete={(results) => {
                      // 处理完成后的回调
                      console.log('AI处理完成:', results);
                      message.success(`AI处理完成！处理了 ${results.length} 个文件`);
                      
                      // 检查是否有标签被应用，如果有则刷新TagManager
                      const hasAppliedTags = results.some(result => result.appliedTags.length > 0);
                      if (hasAppliedTags) {
                        setTagRefreshTrigger(prev => prev + 1);
                        console.log('检测到标签应用，刷新TagManager组件');
                      }
                    }}
                  />
                </div>
              )
            },
            {
              key: 'graph',
              label: (
                <span>
                  <ShareAltOutlined />
                  图谱
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  overflow: 'auto'
                }}>
                  <LinkGraph
                    currentFileId={currentNote.id}
                    onNodeClick={(_, filePath) => {
                      // 处理节点点击事件，跳转到对应文件
                      if (onFileChange) {
                        const fileName = filePath.split('/').pop() || '';
                        onFileChange(filePath, fileName);
                      }
                      message.success(`已跳转到文件: ${filePath}`);
                    }}
                  />
                </div>
              )
            },
            {
              key: 'mcp',
              label: (
                <span>
                  <ToolOutlined />
                  MCP工具
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  overflow: 'hidden'
                }}>
                  <MCPManager />
                </div>
              )
            },
            {
              key: 'links',
              label: (
                <span>
                  <LinkOutlined />
                  链接管理
                </span>
              ),
              children: (
                <div style={{ 
                  height: '100%',
                  overflow: 'hidden'
                }}>
                  <LinkManager
                    fileId={currentNote.id}
                    filePath={currentNote.file_path}
                    onLinksChange={(links) => {
                      // 链接变化时的回调处理
                      console.log('链接已更新:', links);
                    }}
                  />
                </div>
              )
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
                {systemStatus.vector_count_method === 'estimated' && (
                  <Text type="secondary" style={{ fontSize: '10px' }}>~</Text>
                )}
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
              {/* 任务处理器状态 */}
              {processorStatus && (
                <span style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px',
                  color: processorStatus.status === 'running' ? '#52c41a' : 
                        processorStatus.status === 'idle' ? '#1890ff' : '#ff4d4f'
                }}>
                  <span style={{ fontSize: '10px' }}>
                    {processorStatus.status === 'running' ? '●' : '○'}
                  </span>
                  处理器: {
                    processorStatus.status === 'running' ? '运行中' :
                    processorStatus.status === 'idle' ? '空闲中' :
                    processorStatus.status === 'error' ? '错误' :
                    '已停止'
                  }
                  {processorStatus.pending_tasks !== undefined && processorStatus.pending_tasks > 0 && (
                    <span style={{ 
                      fontSize: '10px', 
                      color: '#fa8c16',
                      marginLeft: '4px'
                    }}>
                      ({processorStatus.pending_tasks}个任务)
                    </span>
                  )}
                </span>
              )}
              {/* 控制按钮 */}
              {processorStatus && (
                <Space size="small">
                  {processorStatus.status !== 'running' && (
                    <Button
                      size="small"
                      type="text"
                      icon={<SyncOutlined />}
                      onClick={() => handleStartProcessor(false)}
                      style={{ padding: '0 4px', fontSize: '11px', height: '20px' }}
                      title="启动任务处理器"
                    >
                      启动
                    </Button>
                  )}
                  {processorStatus.status === 'running' && (
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={handleStopProcessor}
                      style={{ padding: '0 4px', fontSize: '11px', height: '20px' }}
                      title="停止任务处理器"
                    >
                      停止
                    </Button>
                  )}
                  {systemStatus.pending_tasks > 0 && processorStatus.status !== 'running' && (
                    <Button
                      size="small"
                      type="primary"
                      icon={<DatabaseOutlined />}
                      onClick={() => handleStartProcessor(true)}
                      style={{ padding: '0 8px', fontSize: '11px', height: '20px' }}
                      title="强制启动索引处理"
                    >
                      开始索引
                    </Button>
                  )}
                </Space>
              )}
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
