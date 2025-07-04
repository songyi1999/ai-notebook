import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  message,
  Typography,
  Row,
  Col,
  Statistic,
  Input,
  Select,
  Switch,
  Tooltip,
  Badge,
  Tag,
  Slider
} from 'antd';
import {
  ShareAltOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  AimOutlined,
  FileTextOutlined,
  LinkOutlined
} from '@ant-design/icons';
import { Network } from 'vis-network/standalone/esm/vis-network';
import type { Data, Options, Node, Edge } from 'vis-network/standalone/esm/vis-network';
import {
  FileData,
  LinkData,
  getFiles,
  getLinks
} from '../services/api';

const { Text } = Typography;
const { Search } = Input;
const { Option } = Select;

interface GraphNode extends Node {
  id: string;
  label: string;
  title?: string;
  group?: string;
  size?: number;
  font?: {
    size: number;
    color: string;
  };
  color?: {
    background: string;
    border: string;
    highlight: {
      background: string;
      border: string;
    };
  };
  fileId?: number;
  filePath?: string;
}

interface GraphEdge extends Edge {
  id: string;
  from: string;
  to: string;
  label?: string;
  title?: string;
  color?: {
    color: string;
    highlight: string;
  };
  width?: number;
  linkType?: string;
}

interface LinkGraphProps {
  currentFileId?: number;
  onNodeClick?: (fileId: number, filePath: string) => void;
}

const LinkGraph: React.FC<LinkGraphProps> = ({
  currentFileId,
  onNodeClick
}) => {
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  
  const [files, setFiles] = useState<FileData[]>([]);
  const [links, setLinks] = useState<LinkData[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLinkTypes, setSelectedLinkTypes] = useState<string[]>(['all']);
  const [showOrphans, setShowOrphans] = useState(true);
  const [nodeSize, setNodeSize] = useState(20);
  const [showLabels, setShowLabels] = useState(true);
  const [layoutType, setLayoutType] = useState('hierarchical');
  
  // 统计信息
  const [stats, setStats] = useState({
    totalNodes: 0,
    totalEdges: 0,
    connectedNodes: 0,
    orphanNodes: 0
  });

  // 链接类型配置
  const linkTypeConfig = {
    reference: { color: '#1890ff', label: '引用' },
    related: { color: '#52c41a', label: '相关' },
    follow_up: { color: '#fa8c16', label: '后续' },
    prerequisite: { color: '#722ed1', label: '前置' },
    example: { color: '#13c2c2', label: '示例' },
    contradiction: { color: '#f5222d', label: '对比' }
  };

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [filesData, linksData] = await Promise.all([
        getFiles(0, 1000),
        getLinks()
      ]);
      
      setFiles(filesData.filter(file => !file.is_deleted));
      setLinks(linksData);
      
    } catch (error) {
      console.error('加载图谱数据失败:', error);
      message.error('加载图谱数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 构建图谱数据
  const buildGraphData = useCallback((): Data => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    
    // 过滤文件
    const filteredFiles = files.filter(file => {
      if (searchTerm) {
        return file.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
               file.file_path.toLowerCase().includes(searchTerm.toLowerCase());
      }
      return true;
    });

    // 过滤链接
    const filteredLinks = links.filter(link => {
      if (selectedLinkTypes.includes('all')) {
        return true;
      }
      return selectedLinkTypes.includes(link.link_type || 'reference');
    });

    // 获取连接的文件ID
    const connectedFileIds = new Set<number>();
    filteredLinks.forEach(link => {
      if (link.source_file_id) connectedFileIds.add(link.source_file_id);
      if (link.target_file_id) connectedFileIds.add(link.target_file_id);
    });

    // 创建节点
    filteredFiles.forEach(file => {
      const isConnected = connectedFileIds.has(file.id!);
      const isCurrentFile = file.id === currentFileId;
      
      // 如果不显示孤立节点且节点未连接，跳过
      if (!showOrphans && !isConnected) {
        return;
      }

      // 计算节点大小（基于连接数）
      const connectionCount = filteredLinks.filter(link => 
        link.source_file_id === file.id || link.target_file_id === file.id
      ).length;
      const calculatedSize = Math.max(nodeSize, nodeSize + connectionCount * 2);

      // 节点颜色
      let nodeColor = {
        background: isCurrentFile ? '#ff7875' : (isConnected ? '#91d5ff' : '#d9d9d9'),
        border: isCurrentFile ? '#ff4d4f' : (isConnected ? '#40a9ff' : '#8c8c8c'),
        highlight: {
          background: isCurrentFile ? '#ff4d4f' : '#69c0ff',
          border: isCurrentFile ? '#cf1322' : '#096dd9'
        }
      };

      nodes.push({
        id: file.id!.toString(),
        label: showLabels ? file.title : '',
        title: `${file.title}\n路径: ${file.file_path}\n连接数: ${connectionCount}`,
        size: calculatedSize,
        font: {
          size: 12,
          color: '#000000'
        },
        color: nodeColor,
        fileId: file.id!,
        filePath: file.file_path
      });
    });

    // 创建边
    filteredLinks.forEach(link => {
      if (!link.source_file_id || !link.target_file_id) return;
      
      // 检查源节点和目标节点是否存在
      const sourceExists = nodes.some(node => node.id === link.source_file_id!.toString());
      const targetExists = nodes.some(node => node.id === link.target_file_id!.toString());
      
      if (!sourceExists || !targetExists) return;

      const linkType = link.link_type || 'reference';
      const typeConfig = linkTypeConfig[linkType as keyof typeof linkTypeConfig];

      edges.push({
        id: link.id!.toString(),
        from: link.source_file_id!.toString(),
        to: link.target_file_id!.toString(),
        label: link.link_text || '',
        title: `类型: ${typeConfig?.label || linkType}\n文本: ${link.link_text || ''}`,
        color: {
          color: typeConfig?.color || '#999999',
          highlight: '#ff4d4f'
        },
        width: 2,
        linkType
      });
    });

    // 更新统计信息
    setStats({
      totalNodes: nodes.length,
      totalEdges: edges.length,
      connectedNodes: nodes.filter(node => 
        edges.some(edge => edge.from === node.id || edge.to === node.id)
      ).length,
      orphanNodes: nodes.filter(node => 
        !edges.some(edge => edge.from === node.id || edge.to === node.id)
      ).length
    });

    return { nodes, edges };
  }, [files, links, searchTerm, selectedLinkTypes, showOrphans, nodeSize, showLabels, currentFileId]);

  // 网络配置选项
  const getNetworkOptions = useCallback((): Options => {
    const baseOptions: Options = {
      nodes: {
        shape: 'dot',
        font: {
          size: 12,
          face: 'Arial'
        },
        borderWidth: 2,
        shadow: true
      },
      edges: {
        font: {
          size: 10,
          face: 'Arial',
          strokeWidth: 2,
          strokeColor: '#ffffff'
        },
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.5
          }
        },
        smooth: {
          enabled: true,
          type: 'dynamic',
          roundness: 0.5
        },
        shadow: true
      },
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 100
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: false,
        hideEdgesOnZoom: false
      }
    };

    // 布局配置
    if (layoutType === 'hierarchical') {
      baseOptions.layout = {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 150,
          levelSeparation: 150
        }
      };
      baseOptions.physics!.enabled = false;
    } else if (layoutType === 'force') {
      baseOptions.layout = {
        randomSeed: 2
      };
      baseOptions.physics = {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 95,
          springConstant: 0.04,
          damping: 0.09
        },
        stabilization: {
          enabled: true,
          iterations: 100
        }
      };
    }

    return baseOptions;
  }, [layoutType]);

  // 初始化网络
  const initNetwork = useCallback(() => {
    if (!networkRef.current) return;

    const data = buildGraphData();
    const options = getNetworkOptions();

    if (networkInstance.current) {
      networkInstance.current.destroy();
    }

    networkInstance.current = new Network(networkRef.current, data, options);

    // 事件监听
    networkInstance.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const nodesArray = Array.isArray(data.nodes) ? data.nodes : [];
        const node = nodesArray.find((n: any) => n.id === nodeId) as GraphNode;
        if (node && node.fileId && onNodeClick) {
          onNodeClick(node.fileId, node.filePath || '');
        }
      }
    });

    networkInstance.current.on('hoverNode', () => {
      if (networkRef.current) {
        networkRef.current.style.cursor = 'pointer';
      }
    });

    networkInstance.current.on('blurNode', () => {
      if (networkRef.current) {
        networkRef.current.style.cursor = 'default';
      }
    });

  }, [buildGraphData, getNetworkOptions, onNodeClick]);

  // 网络操作方法
  const fitNetwork = () => {
    if (networkInstance.current) {
      networkInstance.current.fit({
        animation: {
          duration: 1000,
          easingFunction: 'easeInOutQuad'
        }
      });
    }
  };

  const zoomIn = () => {
    if (networkInstance.current) {
      const scale = networkInstance.current.getScale();
      networkInstance.current.moveTo({
        scale: scale * 1.2,
        animation: { 
          duration: 300,
          easingFunction: 'easeInOutQuad'
        }
      });
    }
  };

  const zoomOut = () => {
    if (networkInstance.current) {
      const scale = networkInstance.current.getScale();
      networkInstance.current.moveTo({
        scale: scale * 0.8,
        animation: { 
          duration: 300,
          easingFunction: 'easeInOutQuad'
        }
      });
    }
  };

  const focusCurrentFile = () => {
    if (networkInstance.current && currentFileId) {
      networkInstance.current.focus(currentFileId.toString(), {
        animation: {
          duration: 1000,
          easingFunction: 'easeInOutQuad'
        },
        scale: 1.5
      });
    }
  };

  // 重新渲染网络
  useEffect(() => {
    if (files.length > 0 || links.length > 0) {
      initNetwork();
    }
  }, [files, links, searchTerm, selectedLinkTypes, showOrphans, nodeSize, showLabels, layoutType, initNetwork]);

  // 初始加载
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 清理
  useEffect(() => {
    return () => {
      if (networkInstance.current) {
        networkInstance.current.destroy();
      }
    };
  }, []);

  return (
    <div style={{ padding: '16px' }}>
      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总节点数"
              value={stats.totalNodes}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="连接数"
              value={stats.totalEdges}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已连接节点"
              value={stats.connectedNodes}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="孤立节点"
              value={stats.orphanNodes}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 控制面板 */}
      <Card 
        title={
          <Space>
            <ShareAltOutlined />
            链接图谱
            <Badge count={stats.totalNodes} showZero>
              <span>节点</span>
            </Badge>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="重新加载数据">
              <Button
                icon={<ReloadOutlined />}
                onClick={loadData}
                loading={loading}
              />
            </Tooltip>
            <Tooltip title="适应画布">
              <Button
                icon={<FullscreenOutlined />}
                onClick={fitNetwork}
              />
            </Tooltip>
            <Tooltip title="放大">
              <Button
                icon={<ZoomInOutlined />}
                onClick={zoomIn}
              />
            </Tooltip>
            <Tooltip title="缩小">
              <Button
                icon={<ZoomOutOutlined />}
                onClick={zoomOut}
              />
            </Tooltip>
            {currentFileId && (
              <Tooltip title="定位当前文件">
                <Button
                  icon={<AimOutlined />}
                  onClick={focusCurrentFile}
                  type="primary"
                  ghost
                />
              </Tooltip>
            )}
          </Space>
        }
        style={{ marginBottom: '16px' }}
      >
        <Row gutter={16} style={{ marginBottom: '16px' }}>
          <Col span={8}>
            <Search
              placeholder="搜索文件名或路径"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              mode="multiple"
              placeholder="选择链接类型"
              value={selectedLinkTypes}
              onChange={setSelectedLinkTypes}
              style={{ width: '100%' }}
            >
              <Option value="all">全部类型</Option>
              {Object.entries(linkTypeConfig).map(([type, config]) => (
                <Option key={type} value={type}>
                  <Tag color={config.color}>{config.label}</Tag>
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Select
              value={layoutType}
              onChange={setLayoutType}
              style={{ width: '100%' }}
            >
              <Option value="hierarchical">层次布局</Option>
              <Option value="force">力导向布局</Option>
            </Select>
          </Col>
          <Col span={6}>
            <Space>
              <Switch
                checked={showOrphans}
                onChange={setShowOrphans}
                size="small"
              />
              <Text>显示孤立节点</Text>
              <Switch
                checked={showLabels}
                onChange={setShowLabels}
                size="small"
              />
              <Text>显示标签</Text>
            </Space>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: '16px' }}>
          <Col span={12}>
            <Text>节点大小: </Text>
            <Slider
              min={10}
              max={50}
              value={nodeSize}
              onChange={setNodeSize}
              style={{ width: '200px', marginLeft: '8px' }}
            />
          </Col>
          <Col span={12}>
            <Space wrap>
              <Text>链接类型图例:</Text>
              {Object.entries(linkTypeConfig).map(([type, config]) => (
                <Tag key={type} color={config.color}>
                  {config.label}
                </Tag>
              ))}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 图谱容器 */}
      <Card>
        <div
          ref={networkRef}
          style={{
            width: '100%',
            height: '600px',
            border: '1px solid #d9d9d9',
            borderRadius: '6px',
            backgroundColor: '#fafafa'
          }}
        />
      </Card>
    </div>
  );
};

export default LinkGraph; 