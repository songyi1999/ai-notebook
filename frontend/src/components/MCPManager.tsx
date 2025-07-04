import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Space,
  Tag,
  Tooltip,
  Tabs,
  Row,
  Col,
  Statistic,
  Badge,
  Popconfirm,
  Typography
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  DisconnectOutlined,
  ReloadOutlined,
  ToolOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { 
  mcpApi, 
  MCPServer as ServerType, 
  MCPTool as ToolType, 
  MCPStats as StatsType, 
  MCPServerCreate 
} from '../services/api';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Text } = Typography;

const MCPManager: React.FC = () => {
  const [servers, setServers] = useState<ServerType[]>([]);
  const [tools, setTools] = useState<ToolType[]>([]);
  const [stats, setStats] = useState<StatsType | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<ServerType | null>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('servers');

  // 加载数据
  useEffect(() => {
    loadServers();
    loadTools();
    loadStats();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const servers = await mcpApi.getServers();
      setServers(servers);
    } catch (error) {
      message.error('加载MCP Server列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadTools = async () => {
    try {
      const tools = await mcpApi.getTools();
      setTools(tools);
    } catch (error) {
      message.error('加载工具列表失败');
    }
  };

  const loadStats = async () => {
    try {
      const stats = await mcpApi.getStats();
      setStats(stats);
    } catch (error) {
      message.error('加载统计信息失败');
    }
  };

  // 服务器操作
  const handleCreateServer = () => {
    setEditingServer(null);
    setModalVisible(true);
    form.resetFields();
  };

  const handleEditServer = (server: ServerType) => {
    setEditingServer(server);
    setModalVisible(true);
    form.setFieldsValue({
      name: server.name,
      description: server.description,
      server_type: server.server_type,
      server_config: JSON.stringify(server.server_config, null, 2),
      auth_type: server.auth_type,
      auth_config: server.auth_config ? JSON.stringify(server.auth_config, null, 2) : '',
      is_enabled: server.is_enabled
    });
  };

  const handleDeleteServer = async (serverId: number) => {
    try {
      await mcpApi.deleteServer(serverId);
      message.success('删除成功');
      loadServers();
      loadStats();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleConnectServer = async (serverId: number) => {
    try {
      await mcpApi.connectServer(serverId);
      message.success('连接成功');
      loadServers();
      loadStats();
    } catch (error) {
      message.error('连接失败');
    }
  };

  // 添加断开连接功能
  const handleDisconnectServer = async (serverId: number) => {
    try {
      await mcpApi.disconnectServer(serverId);
      message.success('断开连接成功');
      loadServers();
      loadStats();
    } catch (error) {
      message.error('断开连接失败');
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      
      // 解析JSON配置
      let serverConfig, authConfig;
      try {
        serverConfig = JSON.parse(values.server_config);
        authConfig = values.auth_config ? JSON.parse(values.auth_config) : undefined;
      } catch (e) {
        message.error('配置格式错误，请检查JSON格式');
        return;
      }

      const serverData: MCPServerCreate = {
        name: values.name,
        description: values.description,
        server_type: values.server_type,
        server_config: serverConfig,
        auth_type: values.auth_type,
        auth_config: authConfig,
        is_enabled: values.is_enabled
      };

      if (editingServer) {
        await mcpApi.updateServer(editingServer.id, serverData);
        message.success('更新成功');
      } else {
        await mcpApi.createServer(serverData);
        message.success('创建成功');
      }

      setModalVisible(false);
      loadServers();
      loadStats();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 渲染状态标签
  const renderConnectionStatus = (server: ServerType) => {
    if (server.is_connected) {
      return <Tag color="green" icon={<CheckCircleOutlined />}>已连接</Tag>;
    } else if (server.connection_status === 'error') {
      return <Tag color="red" icon={<ExclamationCircleOutlined />}>连接错误</Tag>;
    } else {
      return <Tag color="default" icon={<ClockCircleOutlined />}>未连接</Tag>;
    }
  };

  // 服务器表格列定义
  const serverColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ServerType) => (
        <Space>
          <Text strong>{name}</Text>
          {!record.is_enabled && <Tag color="orange">已禁用</Tag>}
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'server_type',
      key: 'server_type',
      render: (type: string) => <Tag color="blue">{type.toUpperCase()}</Tag>
    },
    {
      title: '状态',
      key: 'status',
      render: (_: any, record: ServerType) => renderConnectionStatus(record)
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: ServerType) => (
        <Space>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditServer(record)}
            />
          </Tooltip>
          
          {record.is_connected ? (
            <Tooltip title="断开连接">
              <Popconfirm
                title="确定要断开连接吗？"
                onConfirm={() => handleDisconnectServer(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  size="small"
                  icon={<DisconnectOutlined />}
                  danger
                />
              </Popconfirm>
            </Tooltip>
          ) : (
            <Tooltip title="连接">
              <Button
                size="small"
                icon={<LinkOutlined />}
                type="primary"
                onClick={() => handleConnectServer(record.id)}
              />
            </Tooltip>
          )}
          
          <Popconfirm
            title="确定要删除这个MCP Server吗？"
            onConfirm={() => handleDeleteServer(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                size="small"
                icon={<DeleteOutlined />}
                danger
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  // 工具表格列定义
  const toolColumns = [
    {
      title: '工具名称',
      dataIndex: 'tool_name',
      key: 'tool_name',
      render: (name: string, record: ToolType) => (
        <Space>
          <Text strong>{name}</Text>
          {!record.is_available && <Tag color="red">不可用</Tag>}
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'tool_description',
      key: 'tool_description',
      ellipsis: true
    },
    {
      title: '所属服务器',
      key: 'server_name',
      render: (_: any, record: ToolType) => {
        const server = servers.find(s => s.id === record.server_id);
        return server ? server.name : '未知';
      }
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      render: (count: number) => <Badge count={count} color="blue" />
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计信息 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="MCP服务器"
                value={stats.servers.connected}
                suffix={`/ ${stats.servers.total}`}
                prefix={<SettingOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="可用工具"
                value={stats.tools.available}
                suffix={`/ ${stats.tools.total}`}
                prefix={<ToolOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="调用成功率"
                value={stats.calls.success_rate}
                suffix="%"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: stats.calls.success_rate > 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主要内容 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="MCP服务器" key="servers">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreateServer}
                >
                  添加MCP Server
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadServers}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            </div>
            <Table
              columns={serverColumns}
              dataSource={servers}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab="可用工具" key="tools">
            <div style={{ marginBottom: 16 }}>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadTools}
              >
                刷新工具列表
              </Button>
            </div>
            {/* 调整容器高度，确保分页组件在正常窗口下可见 */}
            <div style={{ 
              height: '400px', 
              display: 'flex',
              flexDirection: 'column',
              border: '1px solid #f0f0f0',
              borderRadius: '6px'
            }}>
              <Table
                columns={toolColumns}
                dataSource={tools}
                rowKey="id"
                pagination={{ 
                  pageSize: 10,
                  showSizeChanger: false,
                  showQuickJumper: false,
                  showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
                }}
                scroll={{ y: 280 }}
                size="small"
                style={{ flex: 1 }}
              />
            </div>
          </TabPane>
        </Tabs>
      </Card>

      {/* 添加/编辑服务器对话框 */}
      <Modal
        title={editingServer ? '编辑MCP Server' : '添加MCP Server'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="服务器名称"
            rules={[{ required: true, message: '请输入服务器名称' }]}
          >
            <Input placeholder="输入MCP Server名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="输入服务器描述（可选）" />
          </Form.Item>

          <Form.Item
            name="server_type"
            label="服务器类型"
            rules={[{ required: true, message: '请选择服务器类型' }]}
          >
            <Select placeholder="选择服务器类型">
              <Select.Option value="http">HTTP</Select.Option>
              <Select.Option value="stdio">STDIO</Select.Option>
              <Select.Option value="sse">SSE</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="server_config"
            label="服务器配置"
            rules={[{ required: true, message: '请输入服务器配置' }]}
          >
            <TextArea
              rows={4}
              placeholder='JSON格式，例如: {"url": "http://localhost:8000"}'
            />
          </Form.Item>

          <Form.Item name="auth_type" label="认证类型">
            <Select placeholder="选择认证类型（可选）" allowClear>
              <Select.Option value="none">无认证</Select.Option>
              <Select.Option value="api_key">API密钥</Select.Option>
              <Select.Option value="bearer">Bearer Token</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="auth_config" label="认证配置">
            <TextArea
              rows={3}
              placeholder='JSON格式，例如: {"api_key": "your-key"}'
            />
          </Form.Item>

          <Form.Item name="is_enabled" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" defaultChecked />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MCPManager; 