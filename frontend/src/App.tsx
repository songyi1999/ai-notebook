import React, { useState } from 'react';
import { Layout } from 'antd';
import NoteEditor from './components/NoteEditor';
import FileTree from './components/FileTree';

const { Header, Content, Sider } = Layout;

function App() {
  // 当前选中的文件
  const [currentFile, setCurrentFile] = useState<{
    path: string;
    name: string;
  } | null>(null);

  // 处理文件选择
  const handleFileSelect = (filePath: string, fileName: string) => {
    setCurrentFile({ path: filePath, name: fileName });
    console.log('App: 选中文件', { path: filePath, name: fileName });
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 头部 */}
      <Header style={{ 
        background: '#fff', 
        padding: '0 24px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center'
      }}>
        <h1 style={{ 
          margin: 0, 
          fontSize: '24px',
          fontWeight: 'bold',
          color: '#1890ff'
        }}>
          AI笔记本
        </h1>
        <p style={{ 
          margin: '0 0 0 16px', 
          color: '#666',
          fontSize: '14px'
        }}>
          纯本地、AI增强的个人知识管理系统
        </p>
      </Header>

      <Layout>
        {/* 左侧文件树 */}
        <Sider 
          width={300} 
          style={{ 
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            overflow: 'auto',
            height: 'calc(100vh - 64px)'
          }}
        >
          <FileTree 
            onFileSelect={handleFileSelect}
            selectedFile={currentFile?.path}
          />
        </Sider>

        {/* 右侧编辑器 */}
        <Layout style={{ padding: '0' }}>
          <Content style={{ 
            margin: 0,
            background: '#fff',
            minHeight: 'calc(100vh - 64px)'
          }}>
            <NoteEditor 
              currentFile={currentFile}
              onFileChange={handleFileSelect}
            />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;