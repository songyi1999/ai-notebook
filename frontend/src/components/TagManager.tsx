import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  ColorPicker,
  Space,
  message,
  Popconfirm,
  Tag,
  Typography,
  Row,
  Col,
  Statistic,
  Tooltip,
  Badge,
  Empty,
  Divider
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  TagOutlined,
  SearchOutlined,
  SyncOutlined,
  RobotOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  TagData,
  getTags,
  createTag,
  updateTag,
  deleteTag,
  suggestTags,
  getFileTags,
  createFileTag,
  deleteFileTag
} from '../services/api';

const { Title, Text } = Typography;
const { Search } = Input;

interface TagManagerProps {
  currentFileId?: number;
  currentFileTitle?: string;
  currentFileContent?: string;
  onTagsChange?: (tags: TagData[]) => void;
}

interface TagWithStats extends TagData {
  usage_count?: number;
  recent_files?: string[];
}

const TagManager: React.FC<TagManagerProps> = ({
  currentFileId,
  currentFileTitle,
  currentFileContent,
  onTagsChange
}) => {
  const [tags, setTags] = useState<TagWithStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTag, setEditingTag] = useState<TagData | null>(null);
  const [searchText, setSearchText] = useState('');
  const [suggestedTags, setSuggestedTags] = useState<string[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [form] = Form.useForm();

  // 文件标签相关状态
  const [fileTags, setFileTags] = useState<TagData[]>([]);
  const [fileTagsLoading, setFileTagsLoading] = useState(false);
  const [addTagModalVisible, setAddTagModalVisible] = useState(false);

  // 默认颜色选项
  const defaultColors = [
    '#f50', '#2db7f5', '#87d068', '#108ee9', '#f56a00',
    '#722ed1', '#eb2f96', '#52c41a', '#13c2c2', '#1890ff'
  ];

  // 加载所有标签
  const loadTags = useCallback(async () => {
    try {
      setLoading(true);
      const tagsData = await getTags(0, 1000); // 加载所有标签
      
      // TODO: 这里可以添加标签使用统计的API调用
      // 目前先设置模拟数据
      const tagsWithStats: TagWithStats[] = tagsData.map(tag => ({
        ...tag,
        usage_count: Math.floor(Math.random() * 20), // 模拟使用次数
        recent_files: [] // 模拟最近使用的文件
      }));
      
      setTags(tagsWithStats);
      onTagsChange?.(tagsData);
    } catch (error) {
      console.error('加载标签失败:', error);
      message.error('加载标签失败');
    } finally {
      setLoading(false);
    }
  }, [onTagsChange]);

  // 加载当前文件的标签
  const loadFileTags = useCallback(async () => {
    if (!currentFileId) {
      setFileTags([]);
      return;
    }

    try {
      setFileTagsLoading(true);
      const fileTagsData = await getFileTags(currentFileId);
      
      // 获取标签详细信息
      const tagDetails = await Promise.all(
        fileTagsData.map(async (fileTag) => {
          const tag = tags.find(t => t.id === fileTag.tag_id);
          if (tag) {
            return tag;
          }
          // 如果本地没有，从服务器获取
          try {
            return await getTags().then(allTags => allTags.find(t => t.id === fileTag.tag_id));
          } catch {
            return null;
          }
        })
      );
      
      setFileTags(tagDetails.filter(Boolean) as TagData[]);
    } catch (error) {
      console.error('加载文件标签失败:', error);
      message.error('加载文件标签失败');
    } finally {
      setFileTagsLoading(false);
    }
  }, [currentFileId, tags]);

  // 获取AI标签建议
  const handleSuggestTags = useCallback(async () => {
    if (!currentFileTitle || !currentFileContent) {
      message.warning('需要选择文件才能获取标签建议');
      return;
    }

    try {
      setSuggestLoading(true);
      const suggestions = await suggestTags(currentFileTitle, currentFileContent, 8);
      setSuggestedTags(suggestions);
      message.success(`获取到 ${suggestions.length} 个标签建议`);
    } catch (error) {
      console.error('获取标签建议失败:', error);
      message.error('获取标签建议失败');
    } finally {
      setSuggestLoading(false);
    }
  }, [currentFileTitle, currentFileContent]);

  // 为当前文件添加标签
  const handleAddTagToFile = async (tagId: number) => {
    if (!currentFileId) {
      message.warning('请先选择文件');
      return;
    }

    try {
      await createFileTag(currentFileId, tagId);
      message.success('标签添加成功');
      loadFileTags();
      setAddTagModalVisible(false);
    } catch (error) {
      console.error('添加标签失败:', error);
      message.error('添加标签失败');
    }
  };

  // 从当前文件移除标签
  const handleRemoveTagFromFile = async (tagId: number) => {
    if (!currentFileId) {
      message.warning('请先选择文件');
      return;
    }

    try {
      await deleteFileTag(currentFileId, tagId);
      message.success('标签移除成功');
      loadFileTags();
    } catch (error) {
      console.error('移除标签失败:', error);
      message.error('移除标签失败');
    }
  };

  // 创建或更新标签
  const handleSaveTag = async (values: any) => {
    try {
      const tagData = {
        name: values.name,
        description: values.description || '',
        color: typeof values.color === 'string' ? values.color : values.color?.toHexString?.() || '#1890ff'
      };

      if (editingTag) {
        await updateTag(editingTag.id!, tagData);
        message.success('标签更新成功');
      } else {
        await createTag(tagData);
        message.success('标签创建成功');
      }

      setModalVisible(false);
      setEditingTag(null);
      form.resetFields();
      loadTags();
    } catch (error) {
      console.error('保存标签失败:', error);
      message.error('保存标签失败');
    }
  };

  // 删除标签
  const handleDeleteTag = async (tagId: number) => {
    try {
      await deleteTag(tagId);
      message.success('标签删除成功');
      loadTags();
    } catch (error) {
      console.error('删除标签失败:', error);
      message.error('删除标签失败');
    }
  };

  // 编辑标签
  const handleEditTag = (tag: TagData) => {
    setEditingTag(tag);
    form.setFieldsValue({
      name: tag.name,
      description: tag.description,
      color: tag.color || '#1890ff'
    });
    setModalVisible(true);
  };

  // 从建议创建标签
  const handleCreateFromSuggestion = async (tagName: string) => {
    try {
      await createTag({
        name: tagName,
        description: `AI建议的标签`,
        color: defaultColors[Math.floor(Math.random() * defaultColors.length)]
      });
      message.success(`标签 "${tagName}" 创建成功`);
      loadTags();
      // 从建议列表中移除
      setSuggestedTags(prev => prev.filter(name => name !== tagName));
    } catch (error) {
      console.error('创建标签失败:', error);
      message.error('创建标签失败');
    }
  };

  // 应用AI建议的标签到当前文件
  const handleApplySuggestedTagToFile = async (tagName: string) => {
    if (!currentFileId) {
      message.warning('请先选择文件');
      return;
    }

    try {
      // 检查标签是否已存在
      let existingTag = tags.find(tag => tag.name === tagName);
      
      if (!existingTag) {
        // 创建新标签
        existingTag = await createTag({
          name: tagName,
          description: `AI建议的标签`,
          color: defaultColors[Math.floor(Math.random() * defaultColors.length)]
        });
        loadTags(); // 重新加载标签列表
      }

      // 检查是否已经关联
      const isAlreadyAssigned = fileTags.some(tag => tag.id === existingTag!.id);
      if (isAlreadyAssigned) {
        message.warning(`标签 "${tagName}" 已经应用到当前文件`);
        return;
      }

      // 应用到当前文件
      await createFileTag(currentFileId, existingTag.id!);
      message.success(`标签 "${tagName}" 已应用到当前文件`);
      
      // 更新状态
      loadFileTags();
      setSuggestedTags(prev => prev.filter(name => name !== tagName));
    } catch (error) {
      console.error('应用标签失败:', error);
      message.error('应用标签失败');
    }
  };

  // 过滤标签
  const filteredTags = tags.filter(tag =>
    tag.name.toLowerCase().includes(searchText.toLowerCase()) ||
    (tag.description && tag.description.toLowerCase().includes(searchText.toLowerCase()))
  );

  // 表格列定义
  const columns: ColumnsType<TagWithStats> = [
    {
      title: '标签',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: TagWithStats) => (
        <Tag color={record.color} style={{ fontSize: '14px', padding: '4px 8px' }}>
          <TagOutlined /> {name}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (description: string) => (
        <Text type="secondary">{description || '无描述'}</Text>
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color={count > 10 ? '#52c41a' : '#d9d9d9'} />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => (
        <Text type="secondary">
          {date ? new Date(date).toLocaleDateString() : '未知'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record: TagWithStats) => (
        <Space>
          <Tooltip title="编辑标签">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditTag(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除这个标签吗？"
            description="删除后将移除所有文件的此标签关联"
            onConfirm={() => handleDeleteTag(record.id!)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除标签">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  useEffect(() => {
    loadTags();
  }, [loadTags]);

  useEffect(() => {
    loadFileTags();
  }, [loadFileTags]);

  return (
    <div style={{ 
      height: '100%',
      overflow: 'auto',
      padding: '16px'
    }}>
      {/* 当前文件标签管理 */}
      {currentFileId && (
        <Card 
          title={
            <Space>
              <FileTextOutlined style={{ color: '#1890ff' }} />
              <span>当前文件标签</span>
              <Text type="secondary">({currentFileTitle})</Text>
            </Space>
          }
          style={{ marginBottom: '16px' }}
          extra={
            <Space>
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setAddTagModalVisible(true)}
              >
                添加标签
              </Button>
              <Button
                size="small"
                icon={<RobotOutlined />}
                loading={suggestLoading}
                onClick={handleSuggestTags}
              >
                AI建议
              </Button>
            </Space>
          }
        >
          <div style={{ minHeight: '40px' }}>
            {fileTagsLoading ? (
              <Text type="secondary">加载中...</Text>
            ) : fileTags.length > 0 ? (
              <Space wrap>
                {fileTags.map((tag) => (
                  <Tag
                    key={tag.id}
                    color={tag.color}
                    closable
                    onClose={() => handleRemoveTagFromFile(tag.id!)}
                    style={{ fontSize: '14px', padding: '4px 8px' }}
                  >
                    <TagOutlined /> {tag.name}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Text type="secondary">暂无标签，点击"添加标签"或"AI建议"来为文件添加标签</Text>
            )}
          </div>
        </Card>
      )}

      {/* 头部统计信息 */}
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总标签数"
              value={tags.length}
              prefix={<TagOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃标签"
              value={tags.filter(tag => (tag.usage_count || 0) > 0).length}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未使用标签"
              value={tags.filter(tag => (tag.usage_count || 0) === 0).length}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="AI建议"
              value={suggestedTags.length}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <Card style={{ marginBottom: '16px' }}>
        <Row justify="space-between" align="middle">
          <Col span={12}>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingTag(null);
                  form.resetFields();
                  setModalVisible(true);
                }}
              >
                新建标签
              </Button>
              <Button
                icon={<RobotOutlined />}
                loading={suggestLoading}
                onClick={handleSuggestTags}
                disabled={!currentFileId}
              >
                AI标签建议
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={loadTags}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col span={8}>
            <Search
              placeholder="搜索标签名称或描述"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* AI建议标签 */}
      {suggestedTags.length > 0 && (
        <Card
          title={
            <Space>
              <RobotOutlined style={{ color: '#722ed1' }} />
              <span>AI标签建议</span>
            </Space>
          }
          style={{ marginBottom: '16px' }}
          extra={
            <Button
              type="text"
              size="small"
              onClick={() => setSuggestedTags([])}
            >
              清空建议
            </Button>
          }
        >
          <Space wrap>
            {suggestedTags.map((tagName, index) => (
              <Space key={index} style={{ marginBottom: '8px' }}>
                <Tag
                  color="purple"
                  style={{ cursor: 'pointer', padding: '4px 8px' }}
                  onClick={() => handleCreateFromSuggestion(tagName)}
                >
                  <PlusOutlined /> {tagName}
                </Tag>
                {currentFileId && (
                  <Button
                    type="link"
                    size="small"
                    onClick={() => handleApplySuggestedTagToFile(tagName)}
                    style={{ padding: '0 4px', height: 'auto' }}
                  >
                    应用到文件
                  </Button>
                )}
              </Space>
            ))}
          </Space>
          <Text type="secondary" style={{ display: 'block', marginTop: '8px' }}>
            点击标签创建到标签库，点击"应用到文件"直接添加到当前文件
          </Text>
        </Card>
      )}

      {/* 标签列表 */}
      <Card title={<Title level={4}>标签管理</Title>}>
        <Table
          columns={columns}
          dataSource={filteredTags}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个标签`,
          }}
          locale={{
            emptyText: (
              <Empty
                description="暂无标签"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" onClick={() => setModalVisible(true)}>
                  创建第一个标签
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      {/* 创建/编辑标签模态框 */}
      <Modal
        title={editingTag ? '编辑标签' : '新建标签'}
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setModalVisible(false);
          setEditingTag(null);
          form.resetFields();
        }}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveTag}
        >
          <Form.Item
            name="name"
            label="标签名称"
            rules={[
              { required: true, message: '请输入标签名称' },
              { max: 50, message: '标签名称不能超过50个字符' }
            ]}
          >
            <Input placeholder="输入标签名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="标签描述"
            rules={[
              { max: 200, message: '描述不能超过200个字符' }
            ]}
          >
            <Input.TextArea
              placeholder="输入标签描述（可选）"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="color"
            label="标签颜色"
            initialValue="#1890ff"
          >
            <ColorPicker
              presets={[
                {
                  label: '推荐颜色',
                  colors: defaultColors,
                },
              ]}
            />
          </Form.Item>
                  </Form>
        </Modal>

        {/* 添加标签到文件模态框 */}
        <Modal
          title="为文件添加标签"
          open={addTagModalVisible}
          onCancel={() => setAddTagModalVisible(false)}
          footer={null}
          width={600}
        >
          <div style={{ marginBottom: '16px' }}>
            <Text strong>文件：</Text>
            <Text type="secondary">{currentFileTitle}</Text>
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <Text strong>选择标签：</Text>
          </div>
          
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <Space wrap>
              {tags
                .filter(tag => !fileTags.some(fileTag => fileTag.id === tag.id))
                .map((tag) => (
                  <Tag
                    key={tag.id}
                    color={tag.color}
                    style={{ 
                      cursor: 'pointer', 
                      padding: '6px 12px',
                      fontSize: '14px',
                      marginBottom: '8px'
                    }}
                    onClick={() => handleAddTagToFile(tag.id!)}
                  >
                    <TagOutlined /> {tag.name}
                  </Tag>
                ))}
            </Space>
            
            {tags.filter(tag => !fileTags.some(fileTag => fileTag.id === tag.id)).length === 0 && (
              <Empty 
                description="所有标签都已添加到当前文件"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </div>
          
          <Divider />
          
          <div style={{ textAlign: 'center' }}>
            <Button 
              type="primary" 
              onClick={() => {
                setAddTagModalVisible(false);
                setModalVisible(true);
              }}
            >
              创建新标签
            </Button>
          </div>
        </Modal>
      </div>
    );
  };

  export default TagManager; 