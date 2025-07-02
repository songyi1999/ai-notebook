import React, { useState, useEffect } from 'react';
import { 
  Tree, 
  Button, 
  Modal, 
  Input, 
  message, 
  Space,
  Typography,
  Spin,
  Tooltip,
  Dropdown
} from 'antd';
import { 
  FolderOutlined, 
  FileOutlined, 
  FolderAddOutlined,
  FileAddOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import type { DataNode, TreeProps } from 'antd/es/tree';
import type { MenuProps } from 'antd';
import { apiClient, FileTreeNode } from '../services/api';

const { Text } = Typography;

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
  
  // 新增：当前选中的文件夹路径，用于新建文件
  const [selectedFolderPath, setSelectedFolderPath] = useState<string>('notes');
  
  // 模态框状态
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [createType, setCreateType] = useState<'file' | 'folder'>('file');
  const [createName, setCreateName] = useState('');
  const [createParentPath, setCreateParentPath] = useState('');

  // 添加重命名状态
  const [isRenameModalVisible, setIsRenameModalVisible] = useState(false);
  const [renameNodeKey, setRenameNodeKey] = useState('');
  const [newName, setNewName] = useState('');

  // 当父组件传入的 selectedFile 改变时同步状态
  useEffect(() => {
    if (selectedFile) {
      setSelectedKeys([selectedFile]);
    }
  }, [selectedFile]);

  // 将FileTreeNode转换为Ant Design Tree的DataNode格式
  const convertToTreeData = (nodes: FileTreeNode[]): DataNode[] => {
    return nodes.map(node => ({
      title: node.name,
      key: node.path,
      isLeaf: node.type === 'file',
      children: node.children ? convertToTreeData(node.children) : undefined,
    }));
  };

  // 加载文件树数据
  const loadFileTree = async () => {
    setLoading(true);
    try {
      // 调用后端API获取文件树
      const fileTreeNodes = await apiClient.getFileTree('notes');
      setTreeData(convertToTreeData(fileTreeNodes));
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
  const handleSelect = (keys: React.Key[], info: any) => {
    setSelectedKeys(keys);
    
    if (info.node.isLeaf) {
      // 如果是文件，选中文件并设置其父目录为当前选中文件夹
      onFileSelect(info.node.key, info.node.title);
      const parentPath = info.node.key.toString().substring(0, info.node.key.toString().lastIndexOf('/'));
      setSelectedFolderPath(parentPath || 'notes');
    } else {
      // 如果是文件夹，设置为当前选中文件夹
      setSelectedFolderPath(info.node.key.toString());
    }
  };

  // 处理双击事件 - 双击文件夹时展开/收缩
  const handleDoubleClick = (e: React.MouseEvent, node: any) => {
    // 只对文件夹响应双击事件
    if (!node.isLeaf) {
      const nodeKey = node.key;
      
      // 切换展开状态
      if (expandedKeys.includes(nodeKey)) {
        // 如果已展开，则收缩
        setExpandedKeys(prev => prev.filter(key => key !== nodeKey));
      } else {
        // 如果未展开，则展开
        setExpandedKeys(prev => [...prev, nodeKey]);
      }
    }
    
    // 阻止事件冒泡，避免触发其他事件
    e.stopPropagation();
  };

  // 创建文件/目录
  const handleCreate = async () => {
    if (!createName.trim()) {
      message.warning('请输入名称');
      return;
    }

    // 使用指定的父路径，或者当前选中的文件夹路径
    const parent = createParentPath || selectedFolderPath;
    const finalName = createType === 'file' && !createName.endsWith('.md') ? `${createName}.md` : createName;
    const finalPath = `${parent}/${finalName}`;

    try {
      if (createType === 'folder') {
        // 创建目录
        await apiClient.createDirectory(finalPath);
        message.success('目录创建成功');
      } else {
        // 创建文件
        await apiClient.createFile({
          file_path: finalPath,
          title: createName,
          content: `# ${createName}\n\n请在这里编写你的笔记内容...`,
          parent_folder: parent
        });
        message.success('文件创建成功');
        
        // 如果创建的是文件，自动选中
        onFileSelect(finalPath, finalName);
        setSelectedKeys([finalPath]);
      }
      
      console.log('创建成功:', { type: createType, path: finalPath, parent });
      
      // 重新加载文件树
      await loadFileTree();
      
      // 展开父目录以显示新创建的项目
      if (!expandedKeys.includes(parent)) {
        setExpandedKeys(prev => [...prev, parent]);
      }
      
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

  const onDrop: TreeProps['onDrop'] = async (info) => {
    const dragKey = info.dragNode.key.toString();
    
    // Determine the target directory
    let targetDir: string;
    if (info.node.isLeaf) {
      // If dropped on a file, target its parent directory
      targetDir = info.node.key.toString().substring(0, info.node.key.toString().lastIndexOf('/'));
    } else {
      // If dropped on a directory, that's the target
      targetDir = info.node.key.toString();
    }
    
    const dragNodeName = dragKey.substring(dragKey.lastIndexOf('/') + 1);
    const newPath = `${targetDir}/${dragNodeName}`;
    
    if(newPath === dragKey) return; // No change in path

    try {
        await apiClient.moveFile(dragKey, newPath);
        message.success(`Moved to ${targetDir}`);
        await loadFileTree();
        // Expand the target directory to show the moved item
        if (!expandedKeys.includes(targetDir)) {
          setExpandedKeys(prev => [...prev, targetDir]);
        }
    } catch (error) {
        console.error("Failed to move file/directory: ", error);
        message.error(`Move failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  // 处理重命名
  const handleRename = async () => {
    if (!newName.trim()) {
      message.warning('请输入新名称');
      return;
    }

    try {
      const oldPath = renameNodeKey;
      const parentPath = oldPath.substring(0, oldPath.lastIndexOf('/'));
      const newPath = `${parentPath}/${newName}`;

      await apiClient.moveFile(oldPath, newPath);
      message.success('重命名成功');
      await loadFileTree();
      
      // 如果重命名的是当前选中的文件，更新选中状态
      if (selectedKeys.includes(oldPath)) {
        setSelectedKeys([newPath]);
        onFileSelect(newPath, newName);
      }
    } catch (error) {
      console.error('重命名失败:', error);
      message.error(`重命名失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }

    setIsRenameModalVisible(false);
    setNewName('');
    setRenameNodeKey('');
  };

  // 处理删除
  const handleDelete = async (nodePath: string) => {
    // 显示确认对话框
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除 "${nodePath}" 吗？此操作不可撤销，同时会删除数据库记录和向量索引。`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 检查是否是文件
          const isFile = nodePath.endsWith('.md');
          
          if (isFile) {
            // 如果是文件，完整删除（包括物理文件）
            try {
              const fileInfo = await apiClient.getFileByPath(nodePath);
              if (fileInfo && fileInfo.id) {
                const result = await apiClient.deleteFile(fileInfo.id, true); // 使用完整删除
                message.success(result.message || '文件删除成功');
              } else {
                message.warning('文件不在数据库中');
              }
            } catch (error) {
              console.error('删除文件失败:', error);
              message.error(`删除文件失败: ${error instanceof Error ? error.message : '未知错误'}`);
            }
          } else {
            // 如果是文件夹，提示用户手动删除
            message.warning('文件夹删除功能暂时不可用，请手动删除文件夹后点击刷新按钮');
            return;
          }
          
          await loadFileTree();
          
          // 如果删除的是当前选中的文件，清除选中状态
          if (selectedKeys.includes(nodePath)) {
            setSelectedKeys([]);
          }
        } catch (error) {
          console.error('删除失败:', error);
          message.error(`删除失败: ${error instanceof Error ? error.message : '未知错误'}`);
        }
      }
    });
  };

  // 处理刷新
  const handleRefresh = async () => {
    message.info('正在刷新文件树...');
    await loadFileTree();
    message.success('文件树刷新完成');
  };

  // 处理重新索引
  const handleRebuildIndex = async () => {
    Modal.confirm({
      title: '确认重新构建索引',
      content: '此操作将删除所有数据库记录和向量索引，然后重新扫描文件构建索引。可能需要一些时间，确定继续吗？',
      okText: '确认重建',
      okType: 'primary',
      cancelText: '取消',
      onOk: async () => {
        const hide = message.loading('正在重新构建索引，请稍候...', 0);
        try {
          await apiClient.rebuildIndex();
          hide();
          message.success('重新构建索引完成');
          // 刷新文件树
          await loadFileTree();
        } catch (error) {
          hide();
          console.error('重新构建索引失败:', error);
          message.error(`重新构建索引失败: ${error instanceof Error ? error.message : '未知错误'}`);
        }
      }
    });
  };

  // 右键菜单项
  const getContextMenuItems = (node: DataNode): MenuProps['items'] => {
    const nodePath = node.key.toString();
    
    const items: MenuProps['items'] = [
      {
        key: 'newFile',
        label: '新建文件',
        icon: <FileAddOutlined />,
        onClick: () => showCreateModal('file', nodePath)
      },
      {
        key: 'newFolder',
        label: '新建文件夹',
        icon: <FolderAddOutlined />,
        onClick: () => showCreateModal('folder', nodePath)
      }
    ];

    // 非根目录才显示重命名和删除选项
    if (nodePath !== 'notes') {
      items.push(
        {
          type: 'divider'
        },
        {
          key: 'rename',
          label: '重命名',
          icon: <EditOutlined />,
          onClick: () => {
            setRenameNodeKey(nodePath);
            setNewName(nodePath.split('/').pop() || '');
            setIsRenameModalVisible(true);
          }
        },
        {
          key: 'delete',
          label: '删除',
          icon: <DeleteOutlined />,
          danger: true,
          onClick: () => handleDelete(nodePath)
        }
      );
    }

    return items;
  };

  // 自定义标题渲染，添加选中状态样式和双击事件
  const renderTitle = (node: DataNode) => {
    const isSelected = selectedKeys.includes(node.key);
    const isSelectedFolder = !node.isLeaf && selectedFolderPath === node.key.toString();
    
    return (
      <Dropdown
        menu={{ items: getContextMenuItems(node) }}
        trigger={['contextMenu']}
      >
        <Tooltip title={node.title?.toString()}>
          <Space 
            style={{
              padding: '2px 4px',
              borderRadius: '4px',
              backgroundColor: isSelected || isSelectedFolder ? '#e6f7ff' : 'transparent',
              border: isSelected || isSelectedFolder ? '1px solid #91d5ff' : '1px solid transparent',
              cursor: !node.isLeaf ? 'pointer' : 'default' // 文件夹显示手型光标
            }}
            onDoubleClick={(e) => handleDoubleClick(e, node)}
          >
            {!node.isLeaf ? <FolderOutlined /> : <FileOutlined />}
            <Text ellipsis style={{ maxWidth: '150px' }}>
              {node.title?.toString()}
            </Text>
          </Space>
        </Tooltip>
      </Dropdown>
    );
  };

  return (
    <div className="file-tree-container">
      <Spin spinning={loading}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Tooltip title="新建文件">
              <Button
                icon={<FileAddOutlined />}
                onClick={() => showCreateModal('file')}
              />
            </Tooltip>
            <Tooltip title="新建文件夹">
              <Button
                icon={<FolderAddOutlined />}
                onClick={() => showCreateModal('folder')}
              />
            </Tooltip>
            <Tooltip title="删除选中的文件/文件夹">
              <Button
                icon={<DeleteOutlined />}
                danger
                disabled={!selectedKeys.length}
                onClick={() => {
                  if (selectedKeys.length > 0) {
                    handleDelete(selectedKeys[0].toString());
                  }
                }}
              />
            </Tooltip>
            <Tooltip title="刷新文件树">
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
              />
            </Tooltip>
            <Tooltip title="重新构建索引">
              <Button
                icon={<DatabaseOutlined />}
                onClick={handleRebuildIndex}
              />
            </Tooltip>
          </Space>
          {/* 显示当前选中的文件夹 */}
          <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
            当前目录: {selectedFolderPath}
            {selectedKeys.length > 0 && (
              <span style={{ marginLeft: 16, color: '#1890ff' }}>
                已选中: {selectedKeys[0].toString()}
              </span>
            )}
          </div>
        </div>

        <Tree
          treeData={treeData}
          onSelect={handleSelect}
          selectedKeys={selectedKeys}
          expandedKeys={expandedKeys}
          onExpand={keys => setExpandedKeys(keys)}
          titleRender={renderTitle}
          draggable
          onDrop={onDrop}
        />

        {/* 创建文件/文件夹模态框 */}
        <Modal
          title={`新建${createType === 'file' ? '文件' : '文件夹'}`}
          open={isCreateModalVisible}
          onOk={handleCreate}
          onCancel={() => setIsCreateModalVisible(false)}
        >
          <div style={{ marginBottom: 16, fontSize: '14px', color: '#666' }}>
            将在目录 <strong>{createParentPath || selectedFolderPath}</strong> 下创建
          </div>
          <Input
            placeholder={`请输入${createType === 'file' ? '文件' : '文件夹'}名称`}
            value={createName}
            onChange={e => setCreateName(e.target.value)}
            onPressEnter={handleCreate}
          />
        </Modal>

        {/* 重命名模态框 */}
        <Modal
          title="重命名"
          open={isRenameModalVisible}
          onOk={handleRename}
          onCancel={() => {
            setIsRenameModalVisible(false);
            setNewName('');
            setRenameNodeKey('');
          }}
        >
          <Input
            placeholder="请输入新名称"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onPressEnter={handleRename}
          />
        </Modal>
      </Spin>
    </div>
  );
};

export default FileTree; 