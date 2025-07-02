import { useState, useEffect } from 'react';
import { Layout, Button, Space, Tooltip } from 'antd';
import { SearchOutlined, MenuFoldOutlined, MenuUnfoldOutlined, RobotOutlined } from '@ant-design/icons';
import NoteEditor from './components/NoteEditor';
import FileTree from './components/FileTree';
import ResizableSider from './components/ResizableSider';
import SearchModal from './components/SearchModal';
import ChatModal from './components/ChatModal';
import './App.css';

const { Header, Content } = Layout;

const App: React.FC = () => {
  const [siderWidth, setSiderWidth] = useState(250);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const [currentFile, setCurrentFile] = useState<{
    path: string;
    name: string;
  } | null>(null);
  const [searchModalVisible, setSearchModalVisible] = useState(false);
  const [chatModalVisible, setChatModalVisible] = useState(false);

  const handleFileSelect = (filePath: string, fileName: string) => {
    setCurrentFile({ path: filePath, name: fileName });
  };

  const handleSearchModalOpen = () => {
    setSearchModalVisible(true);
  };

  const handleSearchModalClose = () => {
    setSearchModalVisible(false);
  };

  const handleChatModalOpen = () => {
    setChatModalVisible(true);
  };

  const handleChatModalClose = () => {
    setChatModalVisible(false);
  };

  const toggleSider = () => {
    setSiderCollapsed(!siderCollapsed);
  };

  // 添加全局快捷键支持
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+K 打开搜索
      if (event.ctrlKey && event.key === 'k') {
        event.preventDefault();
        handleSearchModalOpen();
      }
      // Ctrl+/ 打开AI助手
      if (event.ctrlKey && event.key === '/') {
        event.preventDefault();
        handleChatModalOpen();
      }
      // ESC 关闭搜索或聊天
      if (event.key === 'Escape') {
        if (searchModalVisible) {
          handleSearchModalClose();
        } else if (chatModalVisible) {
          handleChatModalClose();
        }
      }
      // Ctrl+B 切换侧边栏
      if (event.ctrlKey && event.key === 'b') {
        event.preventDefault();
        toggleSider();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [searchModalVisible, chatModalVisible]);

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      {/* 顶部工具栏 */}
      <Header style={{ 
        background: '#fff', 
        padding: '0 16px',
        borderBottom: '1px solid #f0f0f0',
        height: '48px',
        lineHeight: '48px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Tooltip title={`${siderCollapsed ? '展开' : '收起'}侧边栏 (Ctrl+B)`}>
            <Button 
              type="text" 
              icon={siderCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSider}
              style={{ fontSize: '16px' }}
            />
          </Tooltip>
          <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#1890ff' }}>
            AI笔记本
          </div>
        </div>
        <Space>
          <Tooltip title="AI智能问答 (Ctrl+/)">
            <Button 
              type="default" 
              icon={<RobotOutlined />} 
              onClick={handleChatModalOpen}
              style={{ borderRadius: '6px' }}
            >
              询问
            </Button>
          </Tooltip>
          <Tooltip title="智能搜索 (Ctrl+K)">
            <Button 
              type="primary" 
              icon={<SearchOutlined />} 
              onClick={handleSearchModalOpen}
              style={{ borderRadius: '6px' }}
            >
              搜索
            </Button>
          </Tooltip>
        </Space>
      </Header>

      {/* 主要内容区域 */}
      <Layout style={{ 
        height: 'calc(100vh - 48px)', 
        overflow: 'hidden',
        display: 'flex'
      }}>
        {!siderCollapsed && (
          <ResizableSider
            width={siderWidth}
            onResize={setSiderWidth}
            style={{
              background: '#fff',
              borderRight: '1px solid #f0f0f0',
              height: '100%',
              overflow: 'hidden'
            }}
          >
            <div style={{ height: '100%', overflow: 'auto' }}>
              <FileTree
                onFileSelect={handleFileSelect}
                selectedFile={currentFile?.path}
              />
            </div>
          </ResizableSider>
        )}
        <Content style={{ 
          padding: 0,
          flex: 1,
          overflow: 'hidden',
          background: '#fff',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <NoteEditor
            currentFile={currentFile}
            onFileChange={handleFileSelect}
          />
        </Content>
      </Layout>

      {/* 搜索模态窗口 */}
      <SearchModal
        visible={searchModalVisible}
        onClose={handleSearchModalClose}
        onSelectFile={handleFileSelect}
      />

      {/* AI聊天模态窗口 */}
      <ChatModal
        visible={chatModalVisible}
        onClose={handleChatModalClose}
        onSelectFile={handleFileSelect}
      />
    </Layout>
  );
};

export default App;