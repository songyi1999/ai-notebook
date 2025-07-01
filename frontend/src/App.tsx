import { useState } from 'react';
import { Layout } from 'antd';
import NoteEditor from './components/NoteEditor';
import FileTree from './components/FileTree';
import ResizableSider from './components/ResizableSider';
import './App.css';

const App: React.FC = () => {
  const [siderWidth, setSiderWidth] = useState(250);
  const [currentFile, setCurrentFile] = useState<{
    path: string;
    name: string;
  } | null>(null);

  const handleFileSelect = (filePath: string, fileName: string) => {
    setCurrentFile({ path: filePath, name: fileName });
  };

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <ResizableSider
        width={siderWidth}
        onResize={setSiderWidth}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          height: '100%',
          overflow: 'auto'
        }}
      >
        <FileTree
          onFileSelect={handleFileSelect}
          selectedFile={currentFile?.path}
        />
      </ResizableSider>
      <Layout.Content style={{ 
        padding: '0 4px',
        height: '100%',
        overflow: 'auto',
        background: '#fff'
      }}>
        <NoteEditor
          currentFile={currentFile}
          onFileChange={handleFileSelect}
        />
      </Layout.Content>
    </Layout>
  );
};

export default App;