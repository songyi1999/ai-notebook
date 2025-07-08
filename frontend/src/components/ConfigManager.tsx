import React, { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Form,
  Input,
  Switch,
  Button,
  Card,
  Space,
  Select,
  InputNumber,
  Divider,
  Alert,
  Spin,
  Typography,
  message,
  Popconfirm,
  Row,
  Col,
  Tag
} from 'antd';
import {
  SettingOutlined,
  RobotOutlined,
  CloudOutlined,
  ReloadOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  DashboardOutlined
} from '@ant-design/icons';

import { apiClient, getProcessorStatus, startProcessor, stopProcessor, SystemStatus, ProcessorStatus } from '../services/api';

const { TabPane } = Tabs;
const { Text, Title, Paragraph } = Typography;
const { Option } = Select;

interface AISettings {
  enabled: boolean;
  fallback_mode?: string;
  language_model?: {
    provider: string;
    base_url: string;
    api_key: string;
    model_name: string;
    temperature?: number;
    max_tokens?: number;
    timeout?: number;
  };
  embedding_model?: {
    provider: string;
    base_url: string;
    api_key: string;
    model_name: string;
    dimension?: number;
  };
}

interface AppConfig {
  ai_settings: AISettings;
  presets?: Record<string, any>;
  application?: {
    theme: string;
    language: string;
    auto_save: boolean;
    backup_enabled: boolean;
  };
  advanced?: {
    search?: {
      semantic_search_threshold: number;
      search_limit: number;
      enable_hierarchical_chunking: boolean;
    };
    chunking?: {
      hierarchical_summary_max_length: number;
      hierarchical_outline_max_depth: number;
      hierarchical_content_target_size: number;
      hierarchical_content_max_size: number;
      hierarchical_content_overlap: number;
    };
    llm?: {
      context_window: number;
      chunk_for_llm_processing: number;
      max_chunks_for_refine: number;
    };
  };
}

interface ConfigTestResult {
  language_model?: {
    available: boolean;
    message: string;
    available_models?: string[];
    configured_model_found?: boolean;
  };
  embedding_model?: {
    available: boolean;
    message: string;
    dimension?: number;
    configured_dimension_match?: boolean;
  };
  overall_status: string;
  message: string;
}

interface ConfigManagerProps {
  visible: boolean;
  onClose: () => void;
}

const ConfigManager: React.FC<ConfigManagerProps> = ({ visible, onClose }) => {
  const [form] = Form.useForm();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<ConfigTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [presets, setPresets] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState('ai');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [processorStatus, setProcessorStatus] = useState<ProcessorStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      loadConfig();
      loadPresets();
      if (activeTab === 'status') {
        loadSystemStatus();
      }
    }
  }, [visible, activeTab]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/config/');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        form.setFieldsValue(data);
      } else {
        message.error('加载配置失败');
      }
    } catch (error) {
      console.error('加载配置失败:', error);
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPresets = async () => {
    try {
      const response = await fetch('/api/v1/config/presets');
      if (response.ok) {
        const data = await response.json();
        setPresets(data.presets || {});
      }
    } catch (error) {
      console.error('加载预设失败:', error);
    }
  };

  const saveConfig = async () => {
    try {
      const values = form.getFieldsValue();
      setLoading(true);
      
      const response = await fetch('/api/v1/config/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success('配置保存成功');
        setConfig({ ...config, ...values });
      } else {
        const error = await response.json();
        message.error(`保存失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('保存配置失败:', error);
      message.error('保存配置失败');
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    try {
      setTesting(true);
      const response = await fetch('/api/v1/config/test');
      
      if (response.ok) {
        const result = await response.json();
        setTestResult(result);
        
        if (result.overall_status === 'fully_available') {
          message.success('AI服务连接测试成功');
        } else if (result.overall_status === 'partially_available') {
          message.warning('部分AI服务可用');
        } else {
          message.error('AI服务连接失败');
        }
      } else {
        message.error('测试连接失败');
      }
    } catch (error) {
      console.error('测试连接失败:', error);
      message.error('测试连接失败');
    } finally {
      setTesting(false);
    }
  };

  const applyPreset = async (presetName: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/config/presets/${presetName}/apply`, {
        method: 'POST',
      });

      if (response.ok) {
        message.success(`已应用预设: ${presets[presetName]?.name}`);
        await loadConfig();
      } else {
        const error = await response.json();
        message.error(`应用预设失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('应用预设失败:', error);
      message.error('应用预设失败');
    } finally {
      setLoading(false);
    }
  };

  const resetToDefault = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/config/reset', {
        method: 'POST',
      });

      if (response.ok) {
        message.success('配置已重置为默认值');
        await loadConfig();
      } else {
        const error = await response.json();
        message.error(`重置失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('重置失败:', error);
      message.error('重置失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取系统状态
  const loadSystemStatus = async () => {
    try {
      setStatusLoading(true);
      
      // 并行获取系统状态和任务处理器状态
      const [systemStatusResult, processorStatusResult] = await Promise.allSettled([
        apiClient.getSystemStatus(),
        getProcessorStatus()
      ]);
      
      if (systemStatusResult.status === 'fulfilled') {
        setSystemStatus(systemStatusResult.value);
      }
      
      if (processorStatusResult.status === 'fulfilled') {
        setProcessorStatus(processorStatusResult.value);
      }
    } catch (error) {
      console.error('获取系统状态失败:', error);
      // 静默失败，不显示错误消息
    } finally {
      setStatusLoading(false);
    }
  };

  // 启动任务处理器
  const handleStartProcessor = async (force: boolean = false) => {
    try {
      setStatusLoading(true);
      const result = await startProcessor(force);
      
      if (result.success) {
        message.success(result.message);
        setProcessorStatus(result.data);
      } else {
        message.warning(result.message);
      }
    } catch (error) {
      console.error('启动任务处理器失败:', error);
      message.error(`启动任务处理器失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setStatusLoading(false);
      // 刷新状态
      loadSystemStatus();
    }
  };

  // 停止任务处理器
  const handleStopProcessor = async () => {
    try {
      setStatusLoading(true);
      const result = await stopProcessor();
      
      if (result.success) {
        message.success(result.message);
        setProcessorStatus(result.data);
      } else {
        message.warning(result.message);
      }
    } catch (error) {
      console.error('停止任务处理器失败:', error);
      message.error(`停止任务处理器失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setStatusLoading(false);
      // 刷新状态
      loadSystemStatus();
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'fully_available':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'partially_available':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'disabled':
        return <CloseCircleOutlined style={{ color: '#8c8c8c' }} />;
      default:
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const renderAITab = () => (
    <Card>
      <Title level={4}>
        <RobotOutlined /> AI 配置
      </Title>
      
      <Form.Item name={['ai_settings', 'enabled']} valuePropName="checked">
        <Switch
          checkedChildren="启用 AI"
          unCheckedChildren="禁用 AI"
          size="default"
        />
      </Form.Item>

      <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => 
        prevValues.ai_settings?.enabled !== currentValues.ai_settings?.enabled
      }>
        {({ getFieldValue }) => {
          const aiEnabled = getFieldValue(['ai_settings', 'enabled']);
          
          if (!aiEnabled) {
            return (
              <Alert
                message="纯笔记模式"
                description="AI功能已禁用，系统将作为纯笔记管理工具运行，不支持智能搜索、AI问答等功能。"
                type="info"
                showIcon
                style={{ margin: '16px 0' }}
              />
            );
          }

          return (
            <>
              <Divider orientation="left">语言模型配置</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="服务商"
                    name={['ai_settings', 'language_model', 'provider']}
                  >
                    <Select>
                      <Option value="openai_compatible">OpenAI 兼容</Option>
                      <Option value="openai">OpenAI 官方</Option>
                      <Option value="azure_openai">Azure OpenAI</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="模型名称"
                    name={['ai_settings', 'language_model', 'model_name']}
                    rules={[{ required: true, message: '请输入模型名称' }]}
                  >
                    <Input placeholder="例如: qwen2.5:0.5b" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="API 地址"
                    name={['ai_settings', 'language_model', 'base_url']}
                    rules={[{ required: true, message: '请输入API地址' }]}
                  >
                    <Input placeholder="例如: http://localhost:11434/v1" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="API 密钥"
                    name={['ai_settings', 'language_model', 'api_key']}
                  >
                    <Input.Password placeholder="例如: ollama" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="温度"
                    name={['ai_settings', 'language_model', 'temperature']}
                  >
                    <InputNumber
                      min={0}
                      max={2}
                      step={0.1}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="最大令牌数"
                    name={['ai_settings', 'language_model', 'max_tokens']}
                  >
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="超时(秒)"
                    name={['ai_settings', 'language_model', 'timeout']}
                  >
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">嵌入模型配置</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="服务商"
                    name={['ai_settings', 'embedding_model', 'provider']}
                  >
                    <Select>
                      <Option value="openai_compatible">OpenAI 兼容</Option>
                      <Option value="openai">OpenAI 官方</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="模型名称"
                    name={['ai_settings', 'embedding_model', 'model_name']}
                    rules={[{ required: true, message: '请输入嵌入模型名称' }]}
                  >
                    <Input placeholder="例如: quentinz/bge-large-zh-v1.5:latest" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="API 地址"
                    name={['ai_settings', 'embedding_model', 'base_url']}
                    rules={[{ required: true, message: '请输入API地址' }]}
                  >
                    <Input placeholder="例如: http://localhost:11434/v1" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="API 密钥"
                    name={['ai_settings', 'embedding_model', 'api_key']}
                  >
                    <Input.Password placeholder="例如: ollama" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="嵌入维度"
                name={['ai_settings', 'embedding_model', 'dimension']}
              >
                <InputNumber min={1} style={{ width: '200px' }} />
              </Form.Item>

              <Divider />

              <Space>
                <Button 
                  type="primary" 
                  icon={<ExperimentOutlined />}
                  loading={testing}
                  onClick={testConnection}
                >
                  测试连接
                </Button>
                
                {testResult && (
                  <div>
                    {getStatusIcon(testResult.overall_status)}
                    <Text style={{ marginLeft: 8 }}>
                      {testResult.message}
                    </Text>
                  </div>
                )}
              </Space>

              {testResult && (
                <div style={{ marginTop: 16 }}>
                  <Card size="small" title="连接测试详情">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Card size="small" title="语言模型">
                          <p>
                            状态: {testResult.language_model?.available ? 
                              <Tag color="green">可用</Tag> : 
                              <Tag color="red">不可用</Tag>
                            }
                          </p>
                          <p>消息: {testResult.language_model?.message}</p>
                          {testResult.language_model?.available_models && (
                            <p>可用模型数: {testResult.language_model.available_models.length}</p>
                          )}
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card size="small" title="嵌入模型">
                          <p>
                            状态: {testResult.embedding_model?.available ? 
                              <Tag color="green">可用</Tag> : 
                              <Tag color="red">不可用</Tag>
                            }
                          </p>
                          <p>消息: {testResult.embedding_model?.message}</p>
                          {testResult.embedding_model?.dimension && (
                            <p>维度: {testResult.embedding_model.dimension}</p>
                          )}
                        </Card>
                      </Col>
                    </Row>
                  </Card>
                </div>
              )}
            </>
          );
        }}
      </Form.Item>
    </Card>
  );

  const renderPresetsTab = () => (
    <Card>
      <Title level={4}>
        <CloudOutlined /> 预设配置
      </Title>
      
      <Paragraph type="secondary">
        使用预设配置可以快速切换不同的AI服务提供商或运行模式。
      </Paragraph>

      <Row gutter={16}>
        {Object.entries(presets).map(([key, preset]) => (
          <Col span={8} key={key} style={{ marginBottom: 16 }}>
            <Card
              hoverable
              size="small"
              title={preset.name}
              extra={
                <Button
                  size="small"
                  type="primary"
                  onClick={() => applyPreset(key)}
                  loading={loading}
                >
                  应用
                </Button>
              }
            >
              <Paragraph ellipsis={{ rows: 2 }}>
                {preset.description}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      {Object.keys(presets).length === 0 && (
        <Alert
          message="暂无可用预设"
          description="系统中没有配置预设，您可以手动配置AI设置。"
          type="info"
          showIcon
        />
      )}
    </Card>
  );

  const renderAdvancedTab = () => (
    <Card>
      <Title level={4}>
        <SettingOutlined /> 高级配置
      </Title>

      <Divider orientation="left">搜索配置</Divider>
      
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="语义搜索阈值"
            name={['advanced', 'search', 'semantic_search_threshold']}
            tooltip="控制语义搜索的相似度阈值，值越小要求越严格"
          >
            <InputNumber
              min={0}
              max={2}
              step={0.1}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="搜索结果限制"
            name={['advanced', 'search', 'search_limit']}
          >
            <InputNumber min={1} max={500} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name={['advanced', 'search', 'enable_hierarchical_chunking']}
            valuePropName="checked"
          >
            <Switch checkedChildren="启用分层分块" unCheckedChildren="禁用分层分块" />
          </Form.Item>
        </Col>
      </Row>

      <Divider orientation="left">分块配置</Divider>
      
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="摘要最大长度"
            name={['advanced', 'chunking', 'hierarchical_summary_max_length']}
          >
            <InputNumber min={500} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="大纲最大深度"
            name={['advanced', 'chunking', 'hierarchical_outline_max_depth']}
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="内容块目标大小"
            name={['advanced', 'chunking', 'hierarchical_content_target_size']}
          >
            <InputNumber min={100} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="内容块最大大小"
            name={['advanced', 'chunking', 'hierarchical_content_max_size']}
          >
            <InputNumber min={100} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="内容块重叠"
            name={['advanced', 'chunking', 'hierarchical_content_overlap']}
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Divider orientation="left">LLM配置</Divider>
      
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="上下文窗口"
            name={['advanced', 'llm', 'context_window']}
          >
            <InputNumber min={1000} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="LLM处理块大小"
            name={['advanced', 'llm', 'chunk_for_llm_processing']}
          >
            <InputNumber min={1000} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="最大精炼块数"
            name={['advanced', 'llm', 'max_chunks_for_refine']}
          >
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
    </Card>
  );

  const renderSystemStatusTab = () => (
    <Card>
      <Title level={4}>
        <DashboardOutlined /> 系统状态
      </Title>
      
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 刷新按钮 */}
        <div style={{ textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            loading={statusLoading}
            onClick={loadSystemStatus}
          >
            刷新状态
          </Button>
        </div>

        {statusLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px', color: '#666' }}>
              正在获取系统状态...
            </div>
          </div>
        ) : (
          <>
            {/* 系统概览 */}
            {systemStatus && (
              <Card size="small" title="系统概览">
                <Row gutter={16}>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <FileTextOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                      <div style={{ fontSize: '20px', fontWeight: 'bold', marginTop: '8px' }}>
                        {systemStatus.total_files}
                      </div>
                      <div style={{ color: '#666' }}>总文件数</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <DatabaseOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                      <div style={{ fontSize: '20px', fontWeight: 'bold', marginTop: '8px' }}>
                        {systemStatus.total_embeddings}
                        {systemStatus.vector_count_method === 'estimated' && (
                          <Text type="secondary" style={{ fontSize: '12px', marginLeft: '4px' }}>~</Text>
                        )}
                      </div>
                      <div style={{ color: '#666' }}>向量嵌入</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <ClockCircleOutlined 
                        style={{ 
                          fontSize: '24px', 
                          color: systemStatus.pending_tasks > 0 ? '#fa8c16' : '#52c41a' 
                        }} 
                      />
                      <div style={{ 
                        fontSize: '20px', 
                        fontWeight: 'bold', 
                        marginTop: '8px',
                        color: systemStatus.pending_tasks > 0 ? '#fa8c16' : '#52c41a'
                      }}>
                        {systemStatus.pending_tasks}
                      </div>
                      <div style={{ color: '#666' }}>待索引任务</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px' }}>
                        {processorStatus?.status === 'running' ? 
                          <span style={{ color: '#52c41a' }}>●</span> : 
                          <span style={{ color: '#ff4d4f' }}>○</span>
                        }
                      </div>
                      <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '8px' }}>
                        {processorStatus?.status === 'running' ? '运行中' :
                         processorStatus?.status === 'idle' ? '空闲中' :
                         processorStatus?.status === 'error' ? '错误' : '已停止'}
                      </div>
                      <div style={{ color: '#666' }}>处理器状态</div>
                    </div>
                  </Col>
                </Row>
              </Card>
            )}

            {/* 处理器控制 */}
            {processorStatus && (
              <Card size="small" title="处理器控制">
                <div style={{ marginBottom: '16px' }}>
                  <Text strong>当前状态：</Text>
                  <Tag color={
                    processorStatus.status === 'running' ? 'green' :
                    processorStatus.status === 'idle' ? 'blue' :
                    processorStatus.status === 'error' ? 'red' : 'default'
                  }>
                    {processorStatus.status === 'running' ? '运行中' :
                     processorStatus.status === 'idle' ? '空闲中' :
                     processorStatus.status === 'error' ? '错误' : '已停止'}
                  </Tag>
                  {processorStatus.pending_tasks !== undefined && processorStatus.pending_tasks > 0 && (
                    <span style={{ marginLeft: '8px', color: '#fa8c16' }}>
                      （{processorStatus.pending_tasks} 个待处理任务）
                    </span>
                  )}
                </div>
                
                <Space>
                  {processorStatus.status !== 'running' && (
                    <Button
                      type="default"
                      icon={<SyncOutlined />}
                      onClick={() => handleStartProcessor(false)}
                      loading={statusLoading}
                    >
                      启动处理器
                    </Button>
                  )}
                  {processorStatus.status === 'running' && (
                    <Button
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={handleStopProcessor}
                      loading={statusLoading}
                    >
                      停止处理器
                    </Button>
                  )}
                  {systemStatus && systemStatus.pending_tasks > 0 && processorStatus.status !== 'running' && (
                    <Button
                      type="primary"
                      icon={<DatabaseOutlined />}
                      onClick={() => handleStartProcessor(true)}
                      loading={statusLoading}
                    >
                      强制开始索引
                    </Button>
                  )}
                </Space>
              </Card>
            )}

            {/* 详细信息 */}
            {systemStatus && (
              <Card size="small" title="详细信息">
                <Row gutter={16}>
                  <Col span={12}>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>向量计数方法：</Text>
                      <Tag color={systemStatus.vector_count_method === 'exact' ? 'green' : 'orange'}>
                        {systemStatus.vector_count_method === 'exact' ? '精确计数' : '估算'}
                      </Tag>
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>数据库状态：</Text>
                      <Tag color="green">正常</Tag>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>系统版本：</Text>
                      <span style={{ marginLeft: '8px' }}>AI笔记本 v1.0</span>
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong>最后更新：</Text>
                      <span style={{ marginLeft: '8px' }}>
                        {new Date().toLocaleString('zh-CN')}
                      </span>
                    </div>
                  </Col>
                </Row>
              </Card>
            )}
          </>
        )}
      </Space>
    </Card>
  );

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          系统配置
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={
        <Space>
          <Popconfirm
            title="确定要重置为默认配置吗？"
            description="这将清除所有自定义配置。"
            onConfirm={resetToDefault}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<ReloadOutlined />}>
              重置默认
            </Button>
          </Popconfirm>
          
          <Button onClick={onClose}>
            取消
          </Button>
          
          <Button 
            type="primary" 
            onClick={saveConfig}
            loading={loading}
          >
            保存配置
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Form
          form={form}
          layout="horizontal"
          labelCol={{ span: 8 }}
          wrapperCol={{ span: 16 }}
        >
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane 
              tab={
                <Space>
                  <RobotOutlined />
                  AI 配置
                </Space>
              } 
              key="ai"
            >
              {renderAITab()}
            </TabPane>
            
            <TabPane 
              tab={
                <Space>
                  <CloudOutlined />
                  预设配置
                </Space>
              } 
              key="presets"
            >
              {renderPresetsTab()}
            </TabPane>
            
            <TabPane 
              tab={
                <Space>
                  <SettingOutlined />
                  高级设置
                </Space>
              } 
              key="advanced"
            >
              {renderAdvancedTab()}
            </TabPane>
            
            <TabPane 
              tab={
                <Space>
                  <DashboardOutlined />
                  系统状态
                </Space>
              } 
              key="status"
            >
              {renderSystemStatusTab()}
            </TabPane>
          </Tabs>
        </Form>
      </Spin>
    </Modal>
  );
};

export default ConfigManager;