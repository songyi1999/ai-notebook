import React, { useState, useEffect } from 'react';
import { Card, Button, Input, Space, message, Tabs, Typography } from 'antd';
import { SaveOutlined, FileTextOutlined, EyeOutlined, EditOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { apiClient, FileData } from '../services/api';

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
}

interface NoteEditorProps {
  currentFile?: {
    path: string;
    name: string;
  } | null;
  onFileChange?: (filePath: string, fileName: string) => void;
}

const NoteEditor: React.FC<NoteEditorProps> = ({ currentFile }) => {
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

  const [isEditing, setIsEditing] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('edit');

  // 加载文件内容
  const loadFileContent = async (filePath: string) => {
    try {
      const fileData = await apiClient.getFileByPath(filePath);
      setCurrentNote({
        id: fileData.id,
        title: fileData.title,
        content: fileData.content,
        file_path: fileData.file_path
      });
      console.log('文件加载成功:', fileData);
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
    }
  };

  // 监听文件切换
  useEffect(() => {
    if (currentFile) {
      loadFileContent(currentFile.path);
      console.log('切换到文件:', currentFile);
    }
  }, [currentFile]);

  // 保存笔记
  const handleSave = async () => {
    if (!currentNote.title.trim()) {
      message.warning('请输入笔记标题');
      return;
    }

    setIsSaving(true);
    try {
      if (currentNote.id) {
        // 更新现有文件
        await apiClient.updateFile(currentNote.id, {
          title: currentNote.title,
          content: currentNote.content,
          file_path: currentNote.file_path
        });
      } else {
        // 创建新文件
        const newFile = await apiClient.createFile({
          title: currentNote.title,
          content: currentNote.content,
          file_path: currentNote.file_path,
          parent_folder: currentNote.file_path.split('/').slice(0, -1).join('/') || 'notes'
        });
        // 更新当前笔记的ID
        setCurrentNote(prev => ({ ...prev, id: newFile.id }));
      }
      
      message.success('笔记保存成功！');
      console.log('保存笔记成功:', {
        id: currentNote.id,
        title: currentNote.title,
        file_path: currentNote.file_path,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('保存笔记失败:', error);
      message.error(`保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setIsSaving(false);
    }
  };

  // 处理内容变化
  const handleContentChange = (value: string | undefined) => {
    setCurrentNote(prev => ({
      ...prev,
      content: value || ''
    }));
  };

  // 处理标题变化
  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const title = e.target.value;
    setCurrentNote(prev => ({
      ...prev,
      title,
      file_path: title ? `${title.replace(/[^\w\u4e00-\u9fa5]/g, '_')}.md` : 'untitled.md'
    }));
  };

  // 渲染Markdown预览
  const renderMarkdown = () => {
    return {
      __html: md.render(currentNote.content)
    };
  };

  return (
    <div style={{ height: 'calc(100vh - 200px)', padding: '0 16px' }}>
      <Card 
        title={
          <Space>
            <FileTextOutlined />
            <Text strong>笔记编辑器</Text>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={isSaving}
              onClick={handleSave}
            >
              {isSaving ? '保存中...' : '保存笔记'}
            </Button>
          </Space>
        }
        style={{ height: '100%' }}
      >
        {/* 标题输入 */}
        <div style={{ marginBottom: 16 }}>
          <Input
            placeholder="输入笔记标题..."
            value={currentNote.title}
            onChange={handleTitleChange}
            style={{ fontSize: '16px', fontWeight: 'bold' }}
            prefix={<FileTextOutlined />}
          />
        </div>

        {/* 编辑器标签页 */}
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          style={{ height: 'calc(100% - 80px)' }}
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
                <div style={{ height: '500px', border: '1px solid #d9d9d9', borderRadius: '6px' }}>
                  <Editor
                    height="100%"
                    defaultLanguage="markdown"
                    value={currentNote.content}
                    onChange={handleContentChange}
                    theme="vs"
                    options={{
                      minimap: { enabled: false },
                      wordWrap: 'on',
                      lineNumbers: 'on',
                      fontSize: 14,
                      fontFamily: '"Cascadia Code", "Fira Code", "Monaco", "Consolas", monospace',
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                      tabSize: 2,
                      insertSpaces: true,
                      renderWhitespace: 'selection',
                      bracketPairColorization: { enabled: true }
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
                  style={{ 
                    height: '500px', 
                    overflow: 'auto', 
                    padding: '16px',
                    border: '1px solid #d9d9d9',
                    borderRadius: '6px',
                    backgroundColor: '#fafafa'
                  }}
                >
                  <div 
                    className="markdown-preview"
                    dangerouslySetInnerHTML={renderMarkdown()}
                    style={{
                      lineHeight: '1.6',
                      fontSize: '14px',
                      color: '#333'
                    }}
                  />
                </div>
              )
            }
          ]}
        />

        {/* 底部信息 */}
        <div style={{ 
          marginTop: '16px', 
          padding: '8px 0',
          borderTop: '1px solid #f0f0f0',
          fontSize: '12px',
          color: '#666'
        }}>
          <Space split={<span>|</span>}>
            <span>文件路径: {currentNote.file_path}</span>
            <span>字符数: {currentNote.content.length}</span>
            <span>行数: {currentNote.content.split('\n').length}</span>
            <span>最后更新: {new Date().toLocaleString()}</span>
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default NoteEditor;
