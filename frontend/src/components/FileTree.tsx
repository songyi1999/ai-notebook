import React, { useState, useEffect } from 'react';
import { 
  Tree, 
  Button, 
  Modal, 
  Input, 
  message, 
  Dropdown, 
  Space,
  Typography,
  Spin
} from 'antd';
import { 
  FolderOutlined, 
  FileOutlined, 
  PlusOutlined,
  FolderAddOutlined,
  FileAddOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import { apiClient, FileTreeNode } from '../services/api';

const { Text } = Typography;

interface FileNode {
  key: string;
  title: string;
  isLeaf: boolean;
  children?: FileNode[];
  path: string;
  type: 'file' | 'folder';
}

interface FileTreeProps {
  onFileSelect: (filePath: string, fileName: string) => void;
  selectedFile?: string;
}

const FileTree: React.FC<FileTreeProps> = ({ onFileSelect, selectedFile }) => {
  // 状态管理
  const [treeData, setTreeData] = useState<DataNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>(['notes']);
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  
  // 模态框状态
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [createType, setCreateType] = useState<'file' | 'folder'>('file');
  const [createName, setCreateName] = useState('');
  const [createParentPath, setCreateParentPath] = useState('');

  // 将FileTreeNode转换为Ant Design Tree的DataNode格式
  const convertToTreeData = (nodes: FileTreeNode[]): DataNode[] => {
    return nodes.map(node => ({
      title: node.name,
      key: node.path,
      icon: node.type === 'directory' ? <FolderOutlined /> : <FileOutlined />,
      isLeaf: node.type === 'file',
      children: node.children ? convertToTreeData(node.children) : undefined
    }));
  };

  // 加载文件树数据
  const loadFileTree = async () => {
    setLoading(true);
    try {
      // 调用后端API获取文件树
      const fileTreeNodes = await apiClient.getFileTree('notes');
      const treeData = convertToTreeData(fileTreeNodes);
      
      setTreeData(treeData);
      console.log('文件树加载完成:', treeData);
    } catch (error) {
      console.error('加载文件树失败:', error);
      
      // 如果API调用失败，使用模拟数据
      const mockData: DataNode[] = [
        {
          title: 'notes',
          key: 'notes',
          icon: <FolderOutlined />,
          children: [
            {
              title: '欢迎使用.md',
              key: 'notes/欢迎使用.md',
              icon: <FileOutlined />,
              isLeaf: true,
            }
          ]
        }
      ];
      
      setTreeData(mockData);
      message.warning('无法连接到后端服务，使用模拟数据');
    } finally {
      setLoading(false);
    }
  };

  // 初始化加载
  useEffect(() => {
    loadFileTree();
  }, []);

  // 处理文件选择
  const handleSelect = (selectedKeys: React.Key[], info: any) => {
    if (selectedKeys.length > 0) {
      const key = selectedKeys[0] as string;
      const node = info.node;
      
      // 只有文件才能被选中编辑
      if (node.isLeaf && key.endsWith('.md')) {
        setSelectedKeys(selectedKeys);
        const fileName = node.title;
        onFileSelect(key, fileName);
        console.log('选中文件:', { path: key, name: fileName });
      }
    }
  };

  // 创建文件/目录
  const handleCreate = async () => {
    if (!createName.trim()) {
      message.warning('请输入名称');
      return;
    }

    const fullPath = createParentPath 
      ? `${createParentPath}/${createName}` 
      : `notes/${createName}`;
    
    // 如果是文件且没有.md后缀，自动添加
    const finalPath = createType === 'file' && !createName.endsWith('.md') 
      ? `${fullPath}.md` 
      : fullPath;

    try {
      if (createType === 'folder') {
        // 创建目录
        await apiClient.createDirectory(finalPath);
        message.success('目录创建成功');
      } else {
        // 创建文件
        const fileName = createName.endsWith('.md') ? createName : `${createName}.md`;
        await apiClient.createFile({
          file_path: finalPath,
          title: createName,
          content: `# ${createName}\n\n请在这里编写你的笔记内容...`,
          parent_folder: createParentPath || 'notes'
        });
        message.success('文件创建成功');
        
        // 如果创建的是文件，自动选中
        onFileSelect(finalPath, fileName);
      }
      
      console.log('创建成功:', { type: createType, path: finalPath });
      
      // 重新加载文件树
      await loadFileTree();
      
    } catch (error) {
      console.error('创建失败:', error);
      message.error(`创建${createType === 'file' ? '文件' : '目录'}失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
    
    // 关闭模态框
    setIsCreateModalVisible(false);
    setCreateName('');
    setCreateParentPath('');
  };

  // 显示创建模态框
  const showCreateModal = (type: 'file' | 'folder', parentPath = '') => {
    setCreateType(type);
    setCreateParentPath(parentPath);
    setCreateName('');
    setIsCreateModalVisible(true);
  };

  // 右键菜单
  const getContextMenu = (node: any) => {
    const isFolder = !node.isLeaf;
    const menuItems: any[] = [
      {
        key: 'newFile',
        label: (
          <span>
            <FileAddOutlined /> 新建文件
          </span>
        ),
        onClick: () => showCreateModal('file', node.key)
      },
      {
        key: 'newFolder',
        label: (
          <span>
            <FolderAddOutlined /> 新建目录
          </span>
        ),
        onClick: () => showCreateModal('folder', node.key)
      }
    ];

    if (!isFolder) {
      menuItems.push(
        { key: 'divider', type: 'divider' as const },
        {
          key: 'rename',
          label: (
            <span>
              <EditOutlined /> 重命名
            </span>
          ),
          onClick: () => message.info('重命名功能开发中...')
        },
        {
          key: 'delete',
          label: (
            <span style={{ color: '#ff4d4f' }}>
              <DeleteOutlined /> 删除
            </span>
          ),
          onClick: () => message.info('删除功能开发中...')
        }
      );
    }

    return menuItems;
  };

  // 自定义标题渲染
  const renderTitle = (node: any) => {
    return (
      <Dropdown
        menu={{ items: getContextMenu(node) }}
        trigger={['contextMenu']}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          width: '100%'
        }}>
          <Text ellipsis style={{ flex: 1 }}>
            {node.title}
          </Text>
        </div>
      </Dropdown>
    );
  };

  return (
    <div style={{ height: '100%', padding: '16px' }}>
      {/* 头部工具栏 */}
      <div style={{ 
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Text strong>文件管理</Text>
        <Space>
          <Button
            type="text"
            size="small"
            icon={<FileAddOutlined />}
            onClick={() => showCreateModal('file', 'notes')}
            title="新建文件"
          />
          <Button
            type="text"
            size="small"
            icon={<FolderAddOutlined />}
            onClick={() => showCreateModal('folder', 'notes')}
            title="新建目录"
          />
        </Space>
      </div>

      {/* 文件树 */}
      <Spin spinning={loading}>
        <Tree
          treeData={treeData}
          onSelect={handleSelect}
          onExpand={setExpandedKeys}
          expandedKeys={expandedKeys}
          selectedKeys={selectedKeys}
          showIcon
          titleRender={renderTitle}
          style={{ 
            backgroundColor: 'transparent',
            fontSize: '14px'
          }}
        />
      </Spin>

      {/* 创建文件/目录模态框 */}
      <Modal
        title={`新建${createType === 'file' ? '文件' : '目录'}`}
        open={isCreateModalVisible}
        onOk={handleCreate}
        onCancel={() => setIsCreateModalVisible(false)}
        okText="创建"
        cancelText="取消"
      >
        <div style={{ marginBottom: '16px' }}>
          <Text type="secondary">
            父目录: {createParentPath || 'notes'}
          </Text>
        </div>
        <Input
          placeholder={`请输入${createType === 'file' ? '文件' : '目录'}名称`}
          value={createName}
          onChange={(e) => setCreateName(e.target.value)}
          onPressEnter={handleCreate}
          suffix={createType === 'file' && !createName.endsWith('.md') ? '.md' : ''}
        />
        {createType === 'file' && (
          <div style={{ marginTop: '8px' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              文件将自动添加 .md 后缀
            </Text>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default FileTree; 