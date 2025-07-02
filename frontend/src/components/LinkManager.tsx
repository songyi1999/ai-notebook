import React, { useState, useEffect } from 'react';
import {
    Card,
    List,
    Button,
    Modal,
    Form,
    Input,
    Select,
    Space,
    message,
    Tooltip,
    Popconfirm,
    Badge,
    Empty,
    Typography,
    Tag,
    Divider
} from 'antd';
import {
    LinkOutlined,
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    ReloadOutlined,
    ArrowRightOutlined,
    ArrowLeftOutlined,
    FileTextOutlined,
    RobotOutlined,
    BulbOutlined
} from '@ant-design/icons';
import {
    LinkData,
    FileData,
    SmartLinkSuggestion,
    getLinks,
    createLink,
    updateLink,
    deleteLink,
    getFileLinks,
    getFiles,
    discoverSmartLinks,
    getAIStatus
} from '../services/api';

const { Text } = Typography;
const { Option } = Select;

interface LinkManagerProps {
    fileId?: number;
    filePath?: string;
    onLinksChange?: (links: LinkData[]) => void;
}

const LinkManager: React.FC<LinkManagerProps> = ({
    fileId,
    onLinksChange
}) => {
    const [allLinks, setAllLinks] = useState<LinkData[]>([]);
    const [fileLinks, setFileLinks] = useState<LinkData[]>([]);
    const [allFiles, setAllFiles] = useState<FileData[]>([]);
    const [loading, setLoading] = useState(false);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiAvailable, setAiAvailable] = useState(false);
    const [smartSuggestions, setSmartSuggestions] = useState<SmartLinkSuggestion[]>([]);
    
    // 模态框状态
    const [linkModalVisible, setLinkModalVisible] = useState(false);
    const [editingLink, setEditingLink] = useState<LinkData | null>(null);
    
    // 表单
    const [form] = Form.useForm();

    // 链接类型选项
    const linkTypes = [
        { value: 'reference', label: '引用', color: 'blue' },
        { value: 'related', label: '相关', color: 'green' },
        { value: 'follow_up', label: '后续', color: 'orange' },
        { value: 'prerequisite', label: '前置', color: 'purple' },
        { value: 'example', label: '示例', color: 'cyan' },
        { value: 'contradiction', label: '对比', color: 'red' }
    ];

    // 加载所有链接
    const loadAllLinks = async () => {
        try {
            setLoading(true);
            const links = await getLinks();
            setAllLinks(links);
        } catch (error) {
            console.error('加载链接失败:', error);
            message.error('加载链接失败');
        } finally {
            setLoading(false);
        }
    };

    // 加载文件链接
    const loadFileLinks = async () => {
        if (!fileId) return;
        
        try {
            const links = await getFileLinks(fileId);
            // 同时获取反向链接（其他文件指向当前文件的链接）
            const reverseLinks = allLinks.filter(link => link.target_file_id === fileId);
            const allFileLinks = [...links, ...reverseLinks];
            setFileLinks(allFileLinks);
            onLinksChange?.(allFileLinks);
        } catch (error) {
            console.error('加载文件链接失败:', error);
            message.error('加载文件链接失败');
        }
    };

    // 加载所有文件
    const loadAllFiles = async () => {
        try {
            const files = await getFiles(0, 1000); // 获取足够多的文件
            setAllFiles(files);
        } catch (error) {
            console.error('加载文件列表失败:', error);
            message.error('加载文件列表失败');
        }
    };

    // 检查AI服务状态
    const checkAIStatus = async () => {
        try {
            const status = await getAIStatus();
            setAiAvailable(status.available);
        } catch (error) {
            console.error('检查AI状态失败:', error);
            setAiAvailable(false);
        }
    };

    // 智能链接发现
    const handleSmartDiscovery = async () => {
        if (!fileId || !aiAvailable) {
            message.warning('AI服务不可用或未选择文件');
            return;
        }

        try {
            setAiLoading(true);
            const suggestions = await discoverSmartLinks(fileId);
            setSmartSuggestions(suggestions);
            
            if (suggestions.length === 0) {
                message.info('AI未发现合适的链接建议');
            } else {
                message.success(`AI发现了 ${suggestions.length} 个链接建议`);
            }
        } catch (error) {
            console.error('智能链接发现失败:', error);
            message.error('智能链接发现失败');
        } finally {
            setAiLoading(false);
        }
    };

    // 应用链接建议
    const applyLinkSuggestion = async (suggestion: SmartLinkSuggestion) => {
        if (!fileId) return;

        try {
            await createLink({
                source_file_id: fileId,
                target_file_id: suggestion.target_file_id,
                link_type: suggestion.link_type,
                link_text: suggestion.suggested_text || suggestion.reason,
                anchor_text: suggestion.suggested_text
            });
            
            // 移除已应用的建议
            setSmartSuggestions(prev => prev.filter(s => s.target_file_id !== suggestion.target_file_id));
            
            // 重新加载链接
            loadAllLinks();
            message.success('链接创建成功');
        } catch (error) {
            console.error('创建链接失败:', error);
            message.error('创建链接失败');
        }
    };

    useEffect(() => {
        loadAllLinks();
        loadAllFiles();
        checkAIStatus();
    }, []);

    useEffect(() => {
        if (allLinks.length > 0) {
            loadFileLinks();
        }
    }, [allLinks, fileId]);

    // 创建链接
    const handleCreateLink = async (values: any) => {
        try {
            const newLink = await createLink({
                source_file_id: values.source_file_id,
                target_file_id: values.target_file_id,
                link_type: values.link_type,
                link_text: values.link_text,
                anchor_text: values.anchor_text
            });
            setAllLinks([...allLinks, newLink]);
            message.success('链接创建成功');
            setLinkModalVisible(false);
            form.resetFields();
        } catch (error) {
            console.error('创建链接失败:', error);
            message.error('创建链接失败');
        }
    };

    // 更新链接
    const handleUpdateLink = async (values: any) => {
        if (!editingLink?.id) return;
        
        try {
            const updatedLink = await updateLink(editingLink.id, {
                source_file_id: values.source_file_id,
                target_file_id: values.target_file_id,
                link_type: values.link_type,
                link_text: values.link_text,
                anchor_text: values.anchor_text
            });
            setAllLinks(allLinks.map(link => link.id === editingLink.id ? updatedLink : link));
            message.success('链接更新成功');
            setLinkModalVisible(false);
            setEditingLink(null);
            form.resetFields();
        } catch (error) {
            console.error('更新链接失败:', error);
            message.error('更新链接失败');
        }
    };

    // 删除链接
    const handleDeleteLink = async (linkId: number) => {
        try {
            await deleteLink(linkId);
            setAllLinks(allLinks.filter(link => link.id !== linkId));
            setFileLinks(fileLinks.filter(link => link.id !== linkId));
            message.success('链接删除成功');
        } catch (error) {
            console.error('删除链接失败:', error);
            message.error('删除链接失败');
        }
    };

    // 打开链接编辑模态框
    const openLinkModal = (link?: LinkData) => {
        setEditingLink(link || null);
        if (link) {
            form.setFieldsValue({
                source_file_id: link.source_file_id,
                target_file_id: link.target_file_id,
                link_type: link.link_type,
                link_text: link.link_text,
                anchor_text: link.anchor_text
            });
        } else {
            form.resetFields();
            // 如果有当前文件，默认设置为源文件
            if (fileId) {
                form.setFieldsValue({
                    source_file_id: fileId
                });
            }
        }
        setLinkModalVisible(true);
    };

    // 获取文件名
    const getFileName = (fileId: number) => {
        const file = allFiles.find(f => f.id === fileId);
        return file ? file.title || file.file_path.split('/').pop() : `文件ID: ${fileId}`;
    };

    // 获取链接类型信息
    const getLinkTypeInfo = (type: string) => {
        return linkTypes.find(t => t.value === type) || { label: type, color: 'default' };
    };

    // 渲染链接项
    const renderLinkItem = (link: LinkData) => {
        const isOutgoing = link.source_file_id === fileId;
        const otherFileId = isOutgoing ? link.target_file_id : link.source_file_id;
        const otherFileName = getFileName(otherFileId);
        const linkTypeInfo = getLinkTypeInfo(link.link_type);

        return (
            <List.Item
                key={link.id}
                actions={[
                    <Tooltip title="编辑链接">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => openLinkModal(link)}
                        />
                    </Tooltip>,
                    <Popconfirm
                        title="确定删除这个链接吗？"
                        onConfirm={() => handleDeleteLink(link.id!)}
                        okText="确定"
                        cancelText="取消"
                    >
                        <Tooltip title="删除链接">
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                            />
                        </Tooltip>
                    </Popconfirm>
                ]}
            >
                <List.Item.Meta
                    avatar={
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                            {isOutgoing ? (
                                <ArrowRightOutlined style={{ color: '#1890ff' }} />
                            ) : (
                                <ArrowLeftOutlined style={{ color: '#52c41a' }} />
                            )}
                        </div>
                    }
                    title={
                        <Space>
                            <FileTextOutlined />
                            <Text strong>{otherFileName}</Text>
                            <Tag color={linkTypeInfo.color}>{linkTypeInfo.label}</Tag>
                        </Space>
                    }
                    description={
                        <div>
                            {link.link_text && (
                                <div>
                                    <Text type="secondary">链接文本: </Text>
                                    <Text>{link.link_text}</Text>
                                </div>
                            )}
                            {link.anchor_text && (
                                <div>
                                    <Text type="secondary">锚点文本: </Text>
                                    <Text>{link.anchor_text}</Text>
                                </div>
                            )}
                            <div>
                                <Text type="secondary">
                                    {isOutgoing ? '出链到: ' : '入链来自: '}
                                </Text>
                                <Text>{getFileName(isOutgoing ? link.target_file_id : link.source_file_id)}</Text>
                            </div>
                        </div>
                    }
                />
            </List.Item>
        );
    };

    return (
        <div style={{ padding: '16px' }}>
            <Card
                title={
                    <Space>
                        <LinkOutlined />
                        链接管理
                        {fileId && (
                            <Badge count={fileLinks.length} showZero>
                                <span style={{ marginLeft: 8 }}>当前文件链接</span>
                            </Badge>
                        )}
                    </Space>
                }
                extra={
                    <Space>
                        {fileId && aiAvailable && (
                            <Tooltip title="AI智能发现链接">
                                <Button
                                    icon={<RobotOutlined />}
                                    loading={aiLoading}
                                    onClick={handleSmartDiscovery}
                                    type="primary"
                                    ghost
                                >
                                    智能发现
                                </Button>
                            </Tooltip>
                        )}
                        <Tooltip title="刷新链接列表">
                            <Button
                                icon={<ReloadOutlined />}
                                onClick={loadAllLinks}
                                loading={loading}
                            />
                        </Tooltip>
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={() => openLinkModal()}
                        >
                            新建链接
                        </Button>
                    </Space>
                }
                loading={loading}
            >
                {/* 当前文件链接 */}
                {fileId && (
                    <>
                        <div style={{ marginBottom: 16 }}>
                            <h4>当前文件链接:</h4>
                            {fileLinks.length > 0 ? (
                                <List
                                    dataSource={fileLinks}
                                    renderItem={renderLinkItem}
                                    size="small"
                                />
                            ) : (
                                <Empty
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                    description="暂无链接"
                                />
                            )}
                        </div>
                        
                        {/* AI链接建议 */}
                        {smartSuggestions.length > 0 && (
                            <>
                                <Divider />
                                <div style={{ marginBottom: 16 }}>
                                    <h4>
                                        <Space>
                                            <BulbOutlined style={{ color: '#faad14' }} />
                                            AI链接建议:
                                        </Space>
                                    </h4>
                                    <List
                                        dataSource={smartSuggestions}
                                        renderItem={(suggestion) => (
                                            <List.Item
                                                key={suggestion.target_file_id}
                                                actions={[
                                                    <Button
                                                        type="primary"
                                                        size="small"
                                                        onClick={() => applyLinkSuggestion(suggestion)}
                                                    >
                                                        应用
                                                    </Button>,
                                                    <Button
                                                        type="text"
                                                        size="small"
                                                        onClick={() => setSmartSuggestions(prev => 
                                                            prev.filter(s => s.target_file_id !== suggestion.target_file_id)
                                                        )}
                                                    >
                                                        忽略
                                                    </Button>
                                                ]}
                                            >
                                                <List.Item.Meta
                                                    avatar={<BulbOutlined style={{ color: '#faad14' }} />}
                                                    title={
                                                        <Space>
                                                            <Text>{getFileName(suggestion.target_file_id)}</Text>
                                                            <Tag color={getLinkTypeInfo(suggestion.link_type).color}>
                                                                {getLinkTypeInfo(suggestion.link_type).label}
                                                            </Tag>
                                                        </Space>
                                                    }
                                                    description={
                                                        <div>
                                                            <Text type="secondary">理由: </Text>
                                                            <Text>{suggestion.reason}</Text>
                                                            {suggestion.suggested_text && (
                                                                <div>
                                                                    <Text type="secondary">建议文本: </Text>
                                                                    <Text>{suggestion.suggested_text}</Text>
                                                                </div>
                                                            )}
                                                        </div>
                                                    }
                                                />
                                            </List.Item>
                                        )}
                                        size="small"
                                    />
                                </div>
                            </>
                        )}
                        
                        <Divider />
                    </>
                )}

                {/* 所有链接管理 */}
                <div>
                    <h4>所有链接:</h4>
                    {allLinks.length > 0 ? (
                        <List
                            dataSource={allLinks}
                            renderItem={(link) => (
                                <List.Item
                                    key={link.id}
                                    actions={[
                                        <Tooltip title="编辑链接">
                                            <Button
                                                type="text"
                                                icon={<EditOutlined />}
                                                onClick={() => openLinkModal(link)}
                                            />
                                        </Tooltip>,
                                        <Popconfirm
                                            title="确定删除这个链接吗？"
                                            onConfirm={() => handleDeleteLink(link.id!)}
                                            okText="确定"
                                            cancelText="取消"
                                        >
                                            <Tooltip title="删除链接">
                                                <Button
                                                    type="text"
                                                    danger
                                                    icon={<DeleteOutlined />}
                                                />
                                            </Tooltip>
                                        </Popconfirm>
                                    ]}
                                >
                                    <List.Item.Meta
                                        avatar={<LinkOutlined />}
                                        title={
                                            <Space>
                                                <Text>{getFileName(link.source_file_id)}</Text>
                                                <ArrowRightOutlined />
                                                <Text>{getFileName(link.target_file_id)}</Text>
                                                <Tag color={getLinkTypeInfo(link.link_type).color}>
                                                    {getLinkTypeInfo(link.link_type).label}
                                                </Tag>
                                            </Space>
                                        }
                                        description={link.link_text || '无描述'}
                                    />
                                </List.Item>
                            )}
                            size="small"
                        />
                    ) : (
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="暂无链接，点击新建链接开始使用"
                        />
                    )}
                </div>
            </Card>

            {/* 链接编辑模态框 */}
            <Modal
                title={editingLink ? '编辑链接' : '新建链接'}
                open={linkModalVisible}
                onCancel={() => {
                    setLinkModalVisible(false);
                    setEditingLink(null);
                    form.resetFields();
                }}
                footer={null}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={editingLink ? handleUpdateLink : handleCreateLink}
                >
                    <Form.Item
                        label="源文件"
                        name="source_file_id"
                        rules={[{ required: true, message: '请选择源文件' }]}
                    >
                        <Select
                            placeholder="请选择源文件"
                            showSearch
                            filterOption={(input, option) =>
                                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {allFiles.map(file => (
                                <Option key={file.id} value={file.id}>
                                    {file.title || file.file_path}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="目标文件"
                        name="target_file_id"
                        rules={[{ required: true, message: '请选择目标文件' }]}
                    >
                        <Select
                            placeholder="请选择目标文件"
                            showSearch
                            filterOption={(input, option) =>
                                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {allFiles.map(file => (
                                <Option key={file.id} value={file.id}>
                                    {file.title || file.file_path}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="链接类型"
                        name="link_type"
                        rules={[{ required: true, message: '请选择链接类型' }]}
                    >
                        <Select placeholder="请选择链接类型">
                            {linkTypes.map(type => (
                                <Option key={type.value} value={type.value}>
                                    <Tag color={type.color}>{type.label}</Tag>
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="链接文本"
                        name="link_text"
                    >
                        <Input placeholder="请输入链接描述文本（可选）" />
                    </Form.Item>

                    <Form.Item
                        label="锚点文本"
                        name="anchor_text"
                    >
                        <Input placeholder="请输入锚点文本（可选）" />
                    </Form.Item>

                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit">
                                {editingLink ? '更新' : '创建'}
                            </Button>
                            <Button onClick={() => {
                                setLinkModalVisible(false);
                                setEditingLink(null);
                                form.resetFields();
                            }}>
                                取消
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default LinkManager; 