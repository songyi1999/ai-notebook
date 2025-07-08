import React, { useState, useEffect, useCallback } from 'react';
import {
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tooltip,
  Spin,
  Typography,
  Alert
} from 'antd';
import {
  PlusOutlined,
  TagOutlined,
  RobotOutlined,
  BulbOutlined
} from '@ant-design/icons';
import {
  TagData,
  getFileTagsWithDetails,
  getTags,
  createTag,
  createFileTag,
  deleteFileTag,
  suggestTags
} from '../services/api';

const { Text } = Typography;
const { Option } = Select;

interface FileTagsBarProps {
  fileId?: number;
  filePath: string;
  fileName: string;
  fileContent: string;
  onTagsChange?: () => void;
}

interface AddTagModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  fileId: number;
  fileName: string;
  fileContent: string;
}

// 添加标签弹窗组件
const AddTagModal: React.FC<AddTagModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  fileId,
  fileName,
  fileContent
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [allTags, setAllTags] = useState<TagData[]>([]);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [mode, setMode] = useState<'select' | 'create' | 'ai'>('select');

  // 加载所有标签
  const loadTags = async () => {
    try {
      const tags = await getTags();
      setAllTags(tags);
    } catch (error) {
      console.error('Failed to load tags:', error);
    }
  };

  // AI生成标签建议
  const generateAISuggestions = async () => {
    if (!fileContent.trim()) {
      message.warning('文件内容为空，无法生成AI标签建议');
      return;
    }

    setAiLoading(true);
    try {
      const suggestions = await suggestTags(fileName, fileContent, 8);
      setAiSuggestions(suggestions);
      setMode('ai');
      message.success(`AI生成了 ${suggestions.length} 个标签建议`);
    } catch (error) {
      console.error('AI生成标签失败:', error);
      message.error('AI生成标签失败，请稍后重试');
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      loadTags();
      form.resetFields();
      setMode('select');
      setAiSuggestions([]);
    }
  }, [visible, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (mode === 'create') {
        // 创建新标签
        const newTag = await createTag({
          name: values.tagName,
          color: values.color || '#1890ff',
          description: values.description || ''
        });
        
        // 关联到文件
        await createFileTag(fileId, newTag.id!);
        
        message.success(`成功添加新标签: ${newTag.name}`);
      } else if (mode === 'select') {
        // 选择现有标签
        if (values.existingTags && values.existingTags.length > 0) {
          for (const tagId of values.existingTags) {
            await createFileTag(fileId, tagId);
          }
          message.success(`成功添加 ${values.existingTags.length} 个标签`);
        }
      } else if (mode === 'ai') {
        // AI建议标签
        if (values.aiSelectedTags && values.aiSelectedTags.length > 0) {
          for (const tagName of values.aiSelectedTags) {
            // 检查标签是否存在
            let tag = allTags.find(t => t.name === tagName);
            if (!tag) {
              // 创建新标签
              tag = await createTag({
                name: tagName,
                color: '#52c41a', // AI生成的标签用绿色
                description: 'AI自动生成的标签'
              });
            }
            
            // 关联到文件
            await createFileTag(fileId, tag.id!);
          }
          message.success(`成功添加 ${values.aiSelectedTags.length} 个AI建议标签`);
        }
      }

      onSuccess();
      onCancel();
    } catch (error) {
      console.error('添加标签失败:', error);
      message.error('添加标签失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="为文件添加标签"
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      width={600}
      okText="添加"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">文件: {fileName}</Text>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <Button
          type={mode === 'select' ? 'primary' : 'default'}
          onClick={() => setMode('select')}
          icon={<TagOutlined />}
        >
          选择现有标签
        </Button>
        <Button
          type={mode === 'create' ? 'primary' : 'default'}
          onClick={() => setMode('create')}
          icon={<PlusOutlined />}
        >
          创建新标签
        </Button>
        <Button
          type={mode === 'ai' ? 'primary' : 'default'}
          onClick={generateAISuggestions}
          icon={<RobotOutlined />}
          loading={aiLoading}
        >
          AI生成建议
        </Button>
      </Space>

      <Form form={form} layout="vertical">
        {mode === 'select' && (
          <Form.Item
            name="existingTags"
            label="选择标签"
            rules={[{ required: true, message: '请选择至少一个标签' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要添加的标签"
              style={{ width: '100%' }}
              filterOption={(input, option) =>
                String(option?.children).toLowerCase().includes(input.toLowerCase())
              }
            >
              {allTags.map(tag => (
                <Option key={tag.id} value={tag.id}>
                  <Space>
                    <Tag color={tag.color}>{tag.name}</Tag>
                    {tag.description && (
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {tag.description}
                      </Text>
                    )}
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>
        )}

        {mode === 'create' && (
          <>
            <Form.Item
              name="tagName"
              label="标签名称"
              rules={[{ required: true, message: '请输入标签名称' }]}
            >
              <Input placeholder="输入新标签名称" />
            </Form.Item>
            <Form.Item
              name="color"
              label="标签颜色"
              initialValue="#1890ff"
            >
              <Input type="color" style={{ width: 100 }} />
            </Form.Item>
            <Form.Item
              name="description"
              label="标签描述"
            >
              <Input.TextArea placeholder="输入标签描述（可选）" rows={2} />
            </Form.Item>
          </>
        )}

        {mode === 'ai' && (
          <div>
            {aiSuggestions.length > 0 ? (
              <Form.Item
                name="aiSelectedTags"
                label={
                  <Space>
                    <BulbOutlined style={{ color: '#52c41a' }} />
                    <Text>AI建议的标签</Text>
                  </Space>
                }
                rules={[{ required: true, message: '请选择至少一个AI建议的标签' }]}
              >
                <Select
                  mode="multiple"
                  placeholder="选择AI建议的标签"
                  style={{ width: '100%' }}
                >
                  {aiSuggestions.map(suggestion => (
                    <Option key={suggestion} value={suggestion}>
                      <Tag color="#52c41a">{suggestion}</Tag>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            ) : (
              <Alert
                message="点击「AI生成建议」按钮获取智能标签建议"
                type="info"
                showIcon
                icon={<RobotOutlined />}
              />
            )}
          </div>
        )}
      </Form>
    </Modal>
  );
};

// 主组件
const FileTagsBar: React.FC<FileTagsBarProps> = ({
  fileId,
  fileName,
  fileContent,
  onTagsChange
}) => {
  const [fileTags, setFileTags] = useState<TagData[]>([]);
  const [loading, setLoading] = useState(false);
  const [addModalVisible, setAddModalVisible] = useState(false);

  // 加载文件标签
  const loadFileTags = useCallback(async () => {
    if (!fileId) return;
    
    setLoading(true);
    try {
      const tags = await getFileTagsWithDetails(fileId);
      setFileTags(tags);
    } catch (error) {
      console.error('Failed to load file tags:', error);
      message.error('加载文件标签失败');
    } finally {
      setLoading(false);
    }
  }, [fileId]);

  useEffect(() => {
    loadFileTags();
  }, [loadFileTags]);

  // 删除标签
  const handleDeleteTag = async (tagId: number, tagName: string) => {
    if (!fileId) return;

    try {
      await deleteFileTag(fileId, tagId);
      message.success(`已移除标签: ${tagName}`);
      loadFileTags();
      onTagsChange?.();
    } catch (error) {
      console.error('删除标签失败:', error);
      message.error('删除标签失败');
    }
  };

  const handleAddSuccess = () => {
    loadFileTags();
    onTagsChange?.();
  };

  if (!fileId) {
    return (
      <div style={{ 
        padding: '8px 0',
        color: '#999',
        fontSize: '12px'
      }}>
        保存文件后可添加标签
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '8px 0',
      borderTop: '1px solid #f0f0f0',
      marginTop: '8px'
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '8px',
        flexWrap: 'wrap'
      }}>
        <Text type="secondary" style={{ fontSize: '12px', marginRight: '4px' }}>
          标签:
        </Text>
        
        {loading ? (
          <Spin size="small" />
        ) : (
          <Space wrap>
            {fileTags.map(tag => (
              <Tag
                key={tag.id}
                color={tag.color}
                closable
                onClose={() => handleDeleteTag(tag.id!, tag.name)}
                style={{ cursor: 'pointer' }}
              >
                {tag.name}
              </Tag>
            ))}
            <Tooltip title="添加标签">
              <Tag
                icon={<PlusOutlined />}
                onClick={() => setAddModalVisible(true)}
                style={{ 
                  backgroundColor: '#f0f0f0',
                  borderStyle: 'dashed',
                  cursor: 'pointer'
                }}
              >
                添加标签
              </Tag>
            </Tooltip>
          </Space>
        )}
      </div>

      <AddTagModal
        visible={addModalVisible}
        onCancel={() => setAddModalVisible(false)}
        onSuccess={handleAddSuccess}
        fileId={fileId!}
        fileName={fileName}
        fileContent={fileContent}
      />
    </div>
  );
};

export default FileTagsBar;