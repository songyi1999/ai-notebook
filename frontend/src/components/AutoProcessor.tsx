import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Progress,
  List,
  Space,
  message,
  Typography,
  Row,
  Col,
  Statistic,
  Tag,
  Switch,
  Alert,
  Modal,
  Checkbox,
  Table,
  Tooltip
} from 'antd';
import {
  RobotOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  LinkOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  BulbOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  FileData,
  SmartLinkSuggestion,
  getFiles,
  getTags,
  createTag,
  createFileTag,
  suggestTags,
  discoverSmartLinks,
  createLink,
  getAIStatus
} from '../services/api';

const { Text } = Typography;

interface ProcessingResult {
  fileId: number;
  fileName: string;
  filePath: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  suggestedTags: string[];
  appliedTags: string[];
  suggestedLinks: SmartLinkSuggestion[];
  appliedLinks: number;
  error?: string;
  processingTime?: number;
}

interface AutoProcessorProps {
  currentFileId?: number;
  onProcessingComplete?: (results: ProcessingResult[]) => void;
}

const AutoProcessor: React.FC<AutoProcessorProps> = ({
  currentFileId,
  onProcessingComplete
}) => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<number[]>([]);
  const [processing, setProcessing] = useState(false);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<ProcessingResult[]>([]);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [currentProcessing, setCurrentProcessing] = useState<string>('');
  
  // 配置选项
  const [autoCreateTags, setAutoCreateTags] = useState(true);
  const [autoCreateLinks, setAutoCreateLinks] = useState(true);
  const maxTagsPerFile = 5;
  const linkSimilarityThreshold = 0.7;
  
  // 模态框状态
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewData, setPreviewData] = useState<ProcessingResult | null>(null);

  // 检查AI服务状态
  const checkAIStatus = useCallback(async () => {
    try {
      const status = await getAIStatus();
      setAiAvailable(status.available);
    } catch (error) {
      console.error('检查AI状态失败:', error);
      setAiAvailable(false);
    }
  }, []);

  // 加载文件列表
  const loadFiles = useCallback(async () => {
    try {
      const filesData = await getFiles(0, 1000);
      setFiles(filesData.filter(file => !file.is_deleted));
      
      // 如果有当前文件ID，默认选中
      if (currentFileId) {
        setSelectedFiles([currentFileId]);
      }
    } catch (error) {
      console.error('加载文件失败:', error);
      message.error('加载文件失败');
    }
  }, [currentFileId]);

  // 处理单个文件
  const processFile = async (file: FileData): Promise<ProcessingResult> => {
    const result: ProcessingResult = {
      fileId: file.id!,
      fileName: file.title,
      filePath: file.file_path,
      status: 'processing',
      suggestedTags: [],
      appliedTags: [],
      suggestedLinks: [],
      appliedLinks: 0
    };

    const startTime = Date.now();
    setCurrentProcessing(`正在处理: ${file.title}`);

    try {
      // 1. 获取AI标签建议
      if (autoCreateTags) {
        try {
          const suggestedTags = await suggestTags(file.title, file.content, maxTagsPerFile);
          result.suggestedTags = suggestedTags;

          // 自动创建标签
          for (const tagName of suggestedTags) {
            try {
              // 尝试创建标签（如果已存在会失败，但不影响流程）
              let tagId: number | undefined;
              
              try {
                const newTag = await createTag({
                  name: tagName,
                  description: `AI自动生成的标签`,
                  color: '#722ed1'
                });
                tagId = newTag.id;
              } catch (createError) {
                // 标签可能已存在，尝试获取现有标签
                console.log(`标签 "${tagName}" 可能已存在，尝试获取现有标签`);
                try {
                  const allTags = await getTags();
                  const existingTag = allTags.find((tag: any) => tag.name === tagName);
                  if (existingTag) {
                    tagId = existingTag.id;
                  }
                } catch (getError) {
                  console.error(`获取标签失败:`, getError);
                }
              }
              
              // 如果成功获取到标签ID，则关联到文件
              if (tagId && file.id) {
                try {
                  await createFileTag(file.id, tagId);
                  result.appliedTags.push(tagName);
                  console.log(`标签 "${tagName}" 已成功关联到文件 "${file.title}"`);
                } catch (linkError) {
                  console.error(`关联标签到文件失败:`, linkError);
                  // 即使关联失败，标签也已创建，仍算作建议成功
                }
              }
            } catch (error) {
              console.error(`处理标签 "${tagName}" 失败:`, error);
            }
          }
        } catch (error) {
          console.error(`文件 ${file.title} 标签处理失败:`, error);
        }
      }

      // 2. 发现智能链接
      if (autoCreateLinks) {
        try {
          const linkSuggestions = await discoverSmartLinks(file.id!);
          result.suggestedLinks = linkSuggestions.filter(
            suggestion => suggestion.similarity >= linkSimilarityThreshold
          );

          // 自动创建链接
          for (const suggestion of result.suggestedLinks) {
            try {
              await createLink({
                source_file_id: file.id!,
                target_file_id: suggestion.target_file_id,
                link_type: suggestion.link_type,
                link_text: suggestion.description,
                anchor_text: suggestion.description
              });
              result.appliedLinks++;
            } catch (error) {
              console.error(`创建链接失败:`, error);
            }
          }
        } catch (error) {
          console.error(`文件 ${file.title} 链接处理失败:`, error);
        }
      }

      result.status = 'completed';
      result.processingTime = Date.now() - startTime;
      
    } catch (error) {
      result.status = 'error';
      result.error = error instanceof Error ? error.message : '处理失败';
      result.processingTime = Date.now() - startTime;
    }

    return result;
  };

  // 批量处理文件
  const handleBatchProcess = async () => {
    if (!aiAvailable) {
      message.error('AI服务不可用，无法进行自动处理');
      return;
    }

    if (selectedFiles.length === 0) {
      message.warning('请选择要处理的文件');
      return;
    }

    setProcessing(true);
    setPaused(false);
    setProgress(0);
    setResults([]);
    setCurrentProcessing('');

    const selectedFileData = files.filter(file => selectedFiles.includes(file.id!));
    const totalFiles = selectedFileData.length;
    const newResults: ProcessingResult[] = [];

    for (let i = 0; i < selectedFileData.length; i++) {
      if (paused) {
        setCurrentProcessing('处理已暂停');
        break;
      }

      const file = selectedFileData[i];
      const result = await processFile(file);
      newResults.push(result);
      setResults([...newResults]);
      setProgress(((i + 1) / totalFiles) * 100);

      // 添加小延迟避免API过载
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    setProcessing(false);
    setCurrentProcessing('');
    onProcessingComplete?.(newResults);
    
    message.success(`批量处理完成！处理了 ${newResults.length} 个文件`);
  };

  // 暂停/恢复处理
  const handlePauseResume = () => {
    setPaused(!paused);
    setCurrentProcessing(paused ? '恢复处理中...' : '处理已暂停');
  };

  // 停止处理
  const handleStop = () => {
    setProcessing(false);
    setPaused(false);
    setCurrentProcessing('');
    message.info('处理已停止');
  };

  // 预览处理结果
  const handlePreview = (result: ProcessingResult) => {
    setPreviewData(result);
    setPreviewModalVisible(true);
  };

  // 文件选择表格列定义
  const fileColumns: ColumnsType<FileData> = [
    {
      title: '选择',
      key: 'select',
      width: 60,
      render: (_, record) => (
        <Checkbox
          checked={selectedFiles.includes(record.id!)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedFiles([...selectedFiles, record.id!]);
            } else {
              setSelectedFiles(selectedFiles.filter(id => id !== record.id!));
            }
          }}
        />
      ),
    },
    {
      title: '文件名',
      dataIndex: 'title',
      key: 'title',
      render: (title: string) => (
        <Space>
          <FileTextOutlined />
          <Text>{title}</Text>
        </Space>
      ),
    },
    {
      title: '路径',
      dataIndex: 'file_path',
      key: 'file_path',
      render: (path: string) => (
        <Text type="secondary" style={{ fontSize: '12px' }}>{path}</Text>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => (
        <Text type="secondary">
          {size ? `${(size / 1024).toFixed(1)}KB` : '未知'}
        </Text>
      ),
    }
  ];

  // 结果表格列定义
  const resultColumns: ColumnsType<ProcessingResult> = [
    {
      title: '文件',
      dataIndex: 'fileName',
      key: 'fileName',
      render: (name: string, record: ProcessingResult) => (
        <Space>
          <FileTextOutlined />
          <div>
            <div>{name}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.filePath}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          pending: { color: 'default', icon: <ExclamationCircleOutlined />, text: '等待中' },
          processing: { color: 'processing', icon: <RobotOutlined />, text: '处理中' },
          completed: { color: 'success', icon: <CheckCircleOutlined />, text: '完成' },
          error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '错误' }
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '标签',
      key: 'tags',
      width: 120,
      render: (_, record: ProcessingResult) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: '12px' }}>
            建议: {record.suggestedTags.length}
          </Text>
          <Text style={{ fontSize: '12px' }}>
            应用: {record.appliedTags.length}
          </Text>
        </Space>
      ),
    },
    {
      title: '链接',
      key: 'links',
      width: 120,
      render: (_, record: ProcessingResult) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: '12px' }}>
            建议: {record.suggestedLinks.length}
          </Text>
          <Text style={{ fontSize: '12px' }}>
            应用: {record.appliedLinks}
          </Text>
        </Space>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'processingTime',
      key: 'processingTime',
      width: 80,
      render: (time: number) => (
        <Text type="secondary">
          {time ? `${(time / 1000).toFixed(1)}s` : '-'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record: ProcessingResult) => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          />
        </Tooltip>
      ),
    }
  ];

  useEffect(() => {
    loadFiles();
    checkAIStatus();
  }, [loadFiles, checkAIStatus]);

  return (
    <div style={{ 
      height: '100%',
      overflow: 'auto',
      padding: '16px'
    }}>
      {/* AI状态提示 */}
      {!aiAvailable && (
        <Alert
          message="AI服务不可用"
          description="自动处理功能需要AI服务支持，请检查AI服务配置"
          type="warning"
          showIcon
          style={{ marginBottom: '16px' }}
        />
      )}

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总文件数"
              value={files.length}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已选择"
              value={selectedFiles.length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已处理"
              value={results.filter(r => r.status === 'completed').length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="处理失败"
              value={results.filter(r => r.status === 'error').length}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 处理配置 */}
      <Card title="处理配置" style={{ marginBottom: '16px' }}>
        <Row gutter={16}>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Switch
                  checked={autoCreateTags}
                  onChange={setAutoCreateTags}
                  disabled={processing}
                />
                <Text style={{ marginLeft: 8 }}>自动创建和应用标签</Text>
              </div>
              <div>
                <Switch
                  checked={autoCreateLinks}
                  onChange={setAutoCreateLinks}
                  disabled={processing}
                />
                <Text style={{ marginLeft: 8 }}>自动发现和创建链接</Text>
              </div>
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>每个文件最多标签数: {maxTagsPerFile}</Text>
              </div>
              <div>
                <Text>链接相似度阈值: {linkSimilarityThreshold}</Text>
              </div>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 文件选择 */}
      <Card
        title="选择要处理的文件"
        extra={
          <Space>
            <Button
              size="small"
              onClick={() => setSelectedFiles(files.map(f => f.id!))}
              disabled={processing}
            >
              全选
            </Button>
            <Button
              size="small"
              onClick={() => setSelectedFiles([])}
              disabled={processing}
            >
              清空
            </Button>
          </Space>
        }
        style={{ marginBottom: '16px' }}
      >
        <Table
          columns={fileColumns}
          dataSource={files}
          rowKey="id"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
        />
      </Card>

      {/* 处理控制 */}
      <Card
        title="批量处理控制"
        extra={
          <Space>
            {!processing ? (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleBatchProcess}
                disabled={!aiAvailable || selectedFiles.length === 0}
              >
                开始处理
              </Button>
            ) : (
              <>
                <Button
                  icon={paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
                  onClick={handlePauseResume}
                >
                  {paused ? '恢复' : '暂停'}
                </Button>
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleStop}
                >
                  停止
                </Button>
              </>
            )}
          </Space>
        }
        style={{ marginBottom: '16px' }}
      >
        {processing && (
          <div>
            <Progress percent={Math.round(progress)} status={paused ? 'exception' : 'active'} />
            <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
              {currentProcessing}
            </Text>
          </div>
        )}
      </Card>

      {/* 处理结果 */}
      {results.length > 0 && (
        <Card title="处理结果">
          <Table
            columns={resultColumns}
            dataSource={results}
            rowKey="fileId"
            size="small"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
            }}
          />
        </Card>
      )}

      {/* 结果预览模态框 */}
      <Modal
        title={`处理结果详情 - ${previewData?.fileName}`}
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        footer={null}
        width={800}
      >
        {previewData && (
          <div>
            <Row gutter={16} style={{ marginBottom: '16px' }}>
              <Col span={12}>
                <Card size="small" title="标签处理结果">
                  <div style={{ marginBottom: '8px' }}>
                    <Text strong>建议的标签:</Text>
                  </div>
                  <Space wrap>
                    {previewData.suggestedTags.map((tag, index) => (
                      <Tag key={index} color="purple" icon={<BulbOutlined />}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                  
                  <div style={{ marginTop: '16px', marginBottom: '8px' }}>
                    <Text strong>已应用的标签:</Text>
                  </div>
                  <Space wrap>
                    {previewData.appliedTags.map((tag, index) => (
                      <Tag key={index} color="green" icon={<CheckCircleOutlined />}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="链接处理结果">
                  <div style={{ marginBottom: '8px' }}>
                    <Text strong>发现的智能链接:</Text>
                  </div>
                  <List
                    size="small"
                    dataSource={previewData.suggestedLinks}
                    renderItem={(link, index) => (
                      <List.Item key={index}>
                        <div style={{ width: '100%' }}>
                          <div>
                            <LinkOutlined /> {link.target_title}
                          </div>
                          <div>
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              {link.description}
                            </Text>
                          </div>
                          <div>
                            <Tag color="blue">{link.link_type}</Tag>
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              相似度: {(link.similarity * 100).toFixed(1)}%
                            </Text>
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>

            {previewData.error && (
              <Alert
                message="处理错误"
                description={previewData.error}
                type="error"
                showIcon
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AutoProcessor; 