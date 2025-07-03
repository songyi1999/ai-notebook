import React, { useState, useEffect } from 'react';
import {
  Modal,
  Input,
  Select,
  List,
  Card,
  Tag,
  Spin,
  Alert,
  Tabs,
  Typography,
  Divider,
  Space,
  Empty,
  message
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  FireOutlined,
  ThunderboltOutlined,
  BranchesOutlined
} from '@ant-design/icons';
import { search, getSearchHistory, getPopularQueries } from '../services/api';
import type { SearchResponse, SearchResult, SearchHistory, PopularQuery } from '../services/api';

const { Search } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

interface SearchModalProps {
  visible: boolean;
  onClose: () => void;
  onSelectFile: (filePath: string, fileName: string) => void;
}

const SearchModal: React.FC<SearchModalProps> = ({ visible, onClose, onSelectFile }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState<'keyword' | 'semantic' | 'mixed'>('mixed');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [popularQueries, setPopularQueries] = useState<PopularQuery[]>([]);
  const [activeTab, setActiveTab] = useState('search');

  // 加载搜索历史和热门查询
  useEffect(() => {
    if (visible) {
      loadSearchHistory();
      loadPopularQueries();
    }
  }, [visible]);

  const loadSearchHistory = async () => {
    try {
      const history = await getSearchHistory(10);
      setSearchHistory(history);
    } catch (err) {
      console.error('加载搜索历史失败:', err);
    }
  };

  const loadPopularQueries = async () => {
    try {
      const popular = await getPopularQueries(10);
      setPopularQueries(popular);
    } catch (err) {
      console.error('加载热门查询失败:', err);
    }
  };

  const handleSearch = async (query: string) => {
    const trimmedQuery = query.trim();
    
    // 严格的前端验证 - 直接拦截无效输入
    if (!trimmedQuery) {
      message.warning({
        content: '请输入搜索内容',
        duration: 3,
      });
      return;
    }
    
    if (trimmedQuery.length < 2) {
      message.warning({
        content: '搜索内容至少需要2个字符，请输入更多内容',
        duration: 3,
      });
      // 清除错误状态，不发送请求
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setSearchQuery(trimmedQuery);

    try {
      // 不传递similarity_threshold参数，使用后端配置的默认值
      const response = await search(trimmedQuery, searchType, 50);
      setSearchResults(response);
      setActiveTab('search');
      loadSearchHistory();
    } catch (err: any) {
      console.error('搜索失败:', err);
      
      // 根据错误类型显示不同的提示
      if (err?.response?.status === 400) {
        const errorMsg = err.response.data?.detail || '搜索参数有误';
        message.warning(errorMsg);
        setError(errorMsg);
      } else if (err?.response?.status === 500) {
        const errorMsg = '搜索服务暂时不可用，请稍后重试';
        message.error(errorMsg);
        setError(errorMsg);
      } else {
        const errorMsg = '搜索失败，请检查网络连接';
        message.error(errorMsg);
        setError(err instanceof Error ? err.message : errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    onSelectFile(result.file_path, result.title);
    onClose();
  };

  const handleSelectHistoryOrPopular = (query: string) => {
    // 确保历史搜索和热门搜索也经过验证
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) {
      message.warning({
        content: '选择的搜索词过短，无法执行搜索',
        duration: 3,
      });
      return;
    }
    setSearchQuery(trimmedQuery);
    handleSearch(trimmedQuery);
  };

  const getSearchTypeIcon = (type: string) => {
    switch (type) {
      case 'keyword':
        return <SearchOutlined style={{ color: '#1890ff' }} />;
      case 'semantic':
        return <BranchesOutlined style={{ color: '#52c41a' }} />;
      case 'mixed':
        return <ThunderboltOutlined style={{ color: '#faad14' }} />;
      default:
        return <SearchOutlined />;
    }
  };

  const getSearchTypeColor = (type: string) => {
    switch (type) {
      case 'keyword':
        return 'blue';
      case 'semantic':
        return 'green';
      case 'mixed':
        return 'orange';
      default:
        return 'default';
    }
  };

  const formatFileSize = (size?: number) => {
    if (!size) return '';
    if (size < 1024) return `${size}B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`;
    return `${(size / (1024 * 1024)).toFixed(1)}MB`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  return (
    <Modal
      title={<Space><SearchOutlined />智能搜索</Space>}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      style={{ top: 20 }}
    >
      <div style={{ marginBottom: 16 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Select value={searchType} onChange={setSearchType} style={{ width: 120 }}>
            <Option value="mixed"><ThunderboltOutlined /> 混合</Option>
            <Option value="keyword"><SearchOutlined /> 关键词</Option>
            <Option value="semantic"><BranchesOutlined /> 语义</Option>
          </Select>
          <Search
            placeholder="请输入至少2个字符进行搜索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            loading={loading}
            style={{ flex: 1 }}
            status={searchQuery.length > 0 && searchQuery.length < 2 ? 'warning' : undefined}
          />
        </Space.Compact>
        {searchQuery.length > 0 && searchQuery.length < 2 && (
          <div style={{ marginTop: 4, padding: '4px 8px', backgroundColor: '#fff7e6', border: '1px solid #ffd591', borderRadius: '4px' }}>
            <Text type="warning" style={{ fontSize: '12px', fontWeight: 500 }}>
              ⚠️ 搜索内容至少需要2个字符，当前已输入 {searchQuery.length} 个字符
            </Text>
          </div>
        )}
      </div>

      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
          {
            key: 'search',
            label: (
              <Space>
                <SearchOutlined />
                搜索结果
                {searchResults && <Tag color="blue">{searchResults.total}</Tag>}
              </Space>
            ),
            children: (
              <div style={{ minHeight: 400, maxHeight: 500, overflow: 'auto' }}>
                {loading && (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin size="large" />
                    <Text type="secondary">搜索中...</Text>
                  </div>
                )}

                {error && (
                  <Alert message="搜索失败" description={error} type="error" style={{ marginBottom: 16 }} />
                )}

                {searchResults && !loading && (
                  <>
                    <div style={{ marginBottom: 16 }}>
                      <Space>
                        <Text type="secondary">找到 {searchResults.total} 个结果</Text>
                        <Divider type="vertical" />
                        <Text type="secondary">耗时 {searchResults.response_time_ms}ms</Text>
                        <Divider type="vertical" />
                        <Tag color={getSearchTypeColor(searchResults.search_type)}>
                          {getSearchTypeIcon(searchResults.search_type)}
                          {searchResults.search_type === 'mixed' ? '混合搜索' : 
                           searchResults.search_type === 'semantic' ? '语义搜索' : '关键词搜索'}
                        </Tag>
                      </Space>
                    </div>

                    {searchResults.results.length === 0 ? (
                      <Empty description="没有找到相关文件" />
                    ) : (
                      <List
                        dataSource={searchResults.results}
                        renderItem={(result) => (
                          <List.Item key={result.file_id} style={{ cursor: 'pointer' }} onClick={() => handleSelectResult(result)}>
                            <Card hoverable style={{ width: '100%' }} size="small">
                              <Space direction="vertical" style={{ width: '100%' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <FileTextOutlined />
                                  <Title level={5} style={{ margin: 0 }}>{result.title}</Title>
                                  <Tag color={getSearchTypeColor(result.search_type)}>
                                    {getSearchTypeIcon(result.search_type)}
                                  </Tag>
                                  {result.similarity && (
                                    <Tag color="green">{(result.similarity * 100).toFixed(1)}%</Tag>
                                  )}
                                </div>
                                <Text code style={{ fontSize: '12px' }}>{result.file_path}</Text>
                                <Text type="secondary" style={{ fontSize: '13px' }}>{result.content_preview}</Text>
                                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                  <Space>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>{formatFileSize(result.file_size)}</Text>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>{formatDate(result.updated_at)}</Text>
                                  </Space>
                                </div>
                              </Space>
                            </Card>
                          </List.Item>
                        )}
                      />
                    )}
                  </>
                )}
              </div>
            )
          },
          {
            key: 'history',
            label: <Space><ClockCircleOutlined />搜索历史</Space>,
            children: (
              <div style={{ minHeight: 400, maxHeight: 500, overflow: 'auto' }}>
                <List
                  dataSource={searchHistory}
                  renderItem={(item) => (
                    <List.Item key={item.id} style={{ cursor: 'pointer' }} onClick={() => handleSelectHistoryOrPopular(item.query)}>
                      <List.Item.Meta
                        avatar={<ClockCircleOutlined />}
                        title={item.query}
                        description={`${item.search_type} · ${item.results_count} 个结果 · ${item.response_time.toFixed(0)}ms`}
                      />
                    </List.Item>
                  )}
                />
              </div>
            )
          },
          {
            key: 'popular',
            label: <Space><FireOutlined />热门搜索</Space>,
            children: (
              <div style={{ minHeight: 400, maxHeight: 500, overflow: 'auto' }}>
                <List
                  dataSource={popularQueries}
                  renderItem={(item) => (
                    <List.Item key={item.query} style={{ cursor: 'pointer' }} onClick={() => handleSelectHistoryOrPopular(item.query)}>
                      <List.Item.Meta
                        avatar={<FireOutlined style={{ color: '#ff4d4f' }} />}
                        title={item.query}
                        description={`被搜索 ${item.search_count} 次 · 平均 ${item.avg_results} 个结果`}
                      />
                    </List.Item>
                  )}
                />
              </div>
            )
          }
        ]}
      />
    </Modal>
  );
};

export default SearchModal;
