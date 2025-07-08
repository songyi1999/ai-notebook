import React, { useState, useRef, useEffect } from 'react';
import { Modal, Input, Button, Space, Typography, Tag, Card, Collapse, Spin, Alert } from 'antd';
import { 
  RobotOutlined, 
  SendOutlined, 
  ClearOutlined, 
  BulbOutlined,
  SearchOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { flushSync } from 'react-dom';
import StreamingTypewriter from './StreamingTypewriter';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  isStreaming?: boolean;
  error?: string;
  metadata?: any;
  thinkingProcess?: ThinkingProcess;
  supplements?: MessageSupplement[];
}

interface ThinkingProcess {
  evaluation?: {
    completeness: string;
    confidence: number;
    reasoning: string;
  };
  followUpNeeded?: boolean;
  suggestedActions?: Array<{
    type: string;
    priority: string;
    description: string;
    searchQuery?: string;
    expansionAreas?: string[];
  }>;
  currentAction?: {
    type: string;
    description: string;
    searchQuery?: string;
    status: 'pending' | 'processing' | 'completed';
  };
}

interface MessageSupplement {
  id: string;
  type: 'knowledge_search' | 'content_expansion' | 'tool_usage';
  content: string;
  isStreaming?: boolean;
  metadata?: any;
}

interface EnhancedChatModalProps {
  open: boolean;
  onClose: () => void;
  onSelectFile: (filePath: string, title: string) => void;
}

const EnhancedChatModal: React.FC<EnhancedChatModalProps> = ({
  open,
  onClose,
  onSelectFile
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 防抖滚动
  const debouncedScrollToBottom = useRef(
    setTimeout(() => scrollToBottom(), 100)
  );

  useEffect(() => {
    clearTimeout(debouncedScrollToBottom.current);
    debouncedScrollToBottom.current = setTimeout(() => scrollToBottom(), 100);
  }, [messages]);

  // 发送消息
  const handleSendMessage = async () => {
    const question = inputValue.trim();
    if (!question || loading) return;

    setInputValue('');
    setLoading(true);

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    // 添加AI消息占位符
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
      isStreaming: false,
      supplements: []
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // 准备请求数据
      const requestData = {
        model: 'enhanced-chat',
        messages: [
          ...messages.filter(msg => !msg.isLoading).map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          { role: 'user', content: question }
        ],
        stream: true,
        max_context_length: 3000,
        search_limit: 5,
        enable_tools: true,
        use_intent_analysis: true
      };

      // 发送增强流式请求
      const response = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '请求失败');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let responseContent = '';
      let metadata: any = null;
      let currentSupplement: MessageSupplement | null = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') break;

              try {
                const parsed = JSON.parse(data);

                // 处理主要响应内容
                if (parsed.choices?.[0]?.delta?.content) {
                  const deltaContent = parsed.choices[0].delta.content;
                  responseContent += deltaContent;
                  
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            content: responseContent,
                            isLoading: false,
                            isStreaming: !parsed.choices[0].finish_reason
                          }
                        : msg
                    ));
                  });
                  
                  debouncedScrollToBottom.current = setTimeout(() => scrollToBottom(), 50);
                }

                // 处理思考过程
                if (parsed.thinking_process) {
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            thinkingProcess: {
                              ...msg.thinkingProcess,
                              ...parsed.thinking_process
                            }
                          }
                        : msg
                    ));
                  });
                }

                // 处理补充内容开始
                if (parsed.supplement_start) {
                  currentSupplement = {
                    id: Date.now().toString(),
                    type: parsed.action_type,
                    content: '',
                    isStreaming: true
                  };
                  
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            supplements: [...(msg.supplements || []), currentSupplement!]
                          }
                        : msg
                    ));
                  });
                }

                // 处理补充内容
                if (parsed.supplement && currentSupplement && parsed.choices?.[0]?.delta?.content) {
                  const deltaContent = parsed.choices[0].delta.content;
                  currentSupplement.content += deltaContent;
                  
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            supplements: msg.supplements?.map(sup => 
                              sup.id === currentSupplement!.id 
                                ? { ...sup, content: currentSupplement!.content }
                                : sup
                            ) || []
                          }
                        : msg
                    ));
                  });
                }

                // 处理元数据
                if (parsed.metadata) {
                  metadata = parsed.metadata;
                }

                // 处理完成信号
                if (parsed.choices?.[0]?.finish_reason === 'stop') {
                  if (currentSupplement) {
                    currentSupplement.isStreaming = false;
                  }
                  
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            isLoading: false,
                            isStreaming: false,
                            metadata: metadata
                          }
                        : msg
                    ));
                  });
                }

              } catch (parseError) {
                console.warn('解析SSE数据失败:', parseError, '原始数据:', data);
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('增强聊天请求失败:', error);
      
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessage.id));
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: '抱歉，处理您的问题时出现了错误。请稍后再试。',
        timestamp: new Date(),
        error: error instanceof Error ? error.message : '未知错误',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 清空对话
  const handleClearChat = () => {
    setMessages([]);
  };

  // 点击相关文档
  const handleDocumentClick = (filePath: string, title: string) => {
    onSelectFile(filePath, title);
    onClose();
  };

  // 格式化时间
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // 渲染思考过程
  const renderThinkingProcess = (thinking: ThinkingProcess) => {
    if (!thinking) return null;

    return (
      <Card 
        size="small" 
        style={{ 
          margin: '8px 0', 
          backgroundColor: '#f6f8fa',
          border: '1px solid #e1e4e8'
        }}
        title={
          <Space>
            <BulbOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ fontSize: '12px' }}>AI思考过程</Text>
          </Space>
        }
      >
        {thinking.evaluation && (
          <div style={{ marginBottom: '8px' }}>
            <Text strong style={{ fontSize: '11px' }}>回答评估：</Text>
            <div style={{ marginLeft: '8px', fontSize: '11px' }}>
              <div>完整性: <Tag color={
                thinking.evaluation.completeness === 'complete' ? 'green' : 
                thinking.evaluation.completeness === 'partial' ? 'orange' : 'red'
              }>{thinking.evaluation.completeness}</Tag></div>
              <div>置信度: {(thinking.evaluation.confidence * 100).toFixed(1)}%</div>
              <div>原因: {thinking.evaluation.reasoning}</div>
            </div>
          </div>
        )}

        {thinking.followUpNeeded && thinking.suggestedActions && (
          <div style={{ marginBottom: '8px' }}>
            <Text strong style={{ fontSize: '11px' }}>建议的后续行动：</Text>
            {thinking.suggestedActions.map((action, index) => (
              <div key={index} style={{ marginLeft: '8px', marginTop: '4px' }}>
                <Space size="small">
                  {action.type === 'knowledge_search' && <SearchOutlined />}
                  {action.type === 'tool_usage' && <ToolOutlined />}
                  {action.type === 'content_expansion' && <BulbOutlined />}
                  <Text style={{ fontSize: '11px' }}>{action.description}</Text>
                  <Tag color={action.priority === 'high' ? 'red' : 'blue'}>
                    {action.priority}
                  </Tag>
                </Space>
              </div>
            ))}
          </div>
        )}

        {thinking.currentAction && (
          <div>
            <Text strong style={{ fontSize: '11px' }}>当前执行：</Text>
            <div style={{ marginLeft: '8px', marginTop: '4px' }}>
              <Space size="small">
                {thinking.currentAction.status === 'processing' && <LoadingOutlined />}
                {thinking.currentAction.status === 'completed' && <CheckCircleOutlined style={{ color: 'green' }} />}
                <Text style={{ fontSize: '11px' }}>{thinking.currentAction.description}</Text>
              </Space>
            </div>
          </div>
        )}
      </Card>
    );
  };

  // 渲染补充内容
  const renderSupplements = (supplements: MessageSupplement[]) => {
    if (!supplements || supplements.length === 0) return null;

    return (
      <div style={{ marginTop: '12px' }}>
        <Collapse size="small" ghost>
          {supplements.map((supplement) => (
            <Panel 
              key={supplement.id}
              header={
                <Space>
                  {supplement.type === 'knowledge_search' && <SearchOutlined />}
                  {supplement.type === 'content_expansion' && <BulbOutlined />}
                  {supplement.type === 'tool_usage' && <ToolOutlined />}
                  <Text style={{ fontSize: '12px' }}>
                    {supplement.type === 'knowledge_search' && '知识补充'}
                    {supplement.type === 'content_expansion' && '内容扩展'}
                    {supplement.type === 'tool_usage' && '工具调用'}
                  </Text>
                  {supplement.isStreaming && <LoadingOutlined />}
                </Space>
              }
            >
              <div style={{ 
                backgroundColor: '#fafafa', 
                padding: '8px', 
                borderRadius: '4px',
                fontSize: '13px'
              }}>
                <StreamingTypewriter
                  content={supplement.content}
                  isStreaming={supplement.isStreaming || false}
                  speed={20}
                />
              </div>
            </Panel>
          ))}
        </Collapse>
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <RobotOutlined />
          <span>增强AI助手</span>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            支持自我评估和多轮处理
          </Text>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
      styles={{
        body: {
          height: '600px',
          padding: 0,
          display: 'flex',
          flexDirection: 'column'
        }
      }}
    >
      {/* 聊天消息区域 */}
      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '16px',
          backgroundColor: '#fafafa'
        }}
      >
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
            <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
            <div>你好！我是增强AI助手，可以进行智能分析和多轮思考。</div>
            <div style={{ fontSize: '12px', marginTop: '8px' }}>
              我会显示思考过程，并在需要时自动补充更多信息。
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} style={{ marginBottom: '16px' }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              {message.role === 'assistant' && (
                <RobotOutlined style={{ fontSize: '16px', color: '#1890ff', marginTop: '4px' }} />
              )}
              
              <div style={{ 
                maxWidth: '80%',
                backgroundColor: message.role === 'user' ? '#1890ff' : '#fff',
                color: message.role === 'user' ? '#fff' : '#000',
                padding: '12px',
                borderRadius: '8px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
              }}>
                <div>
                  {message.isLoading ? (
                    <Spin size="small" />
                  ) : message.isStreaming ? (
                    <StreamingTypewriter
                      content={message.content}
                      isStreaming={true}
                      speed={30}
                    />
                  ) : (
                    <Paragraph style={{ margin: 0, color: 'inherit' }}>
                      {message.content}
                    </Paragraph>
                  )}
                </div>
                
                <div style={{ 
                  fontSize: '11px', 
                  opacity: 0.7, 
                  marginTop: '4px',
                  color: 'inherit'
                }}>
                  {formatTime(message.timestamp)}
                </div>

                {message.error && (
                  <Alert 
                    message={message.error} 
                    type="error" 
                    style={{ marginTop: '8px' }} 
                  />
                )}
              </div>
            </div>

            {/* 显示思考过程 */}
            {message.thinkingProcess && renderThinkingProcess(message.thinkingProcess)}

            {/* 显示补充内容 */}
            {message.supplements && renderSupplements(message.supplements)}

            {/* 显示相关文档 */}
            {message.metadata?.related_documents && message.metadata.related_documents.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <Collapse size="small" ghost>
                  <Panel 
                    header={
                      <Space>
                        <SearchOutlined />
                        <Text style={{ fontSize: '12px' }}>相关文档 ({message.metadata.related_documents.length})</Text>
                      </Space>
                    }
                    key="related-docs"
                  >
                    <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      {message.metadata.related_documents.map((doc: any, index: number) => (
                        <div 
                          key={index}
                          style={{ 
                            padding: '8px',
                            marginBottom: '4px',
                            backgroundColor: '#fafafa',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            transition: 'background-color 0.2s'
                          }}
                          onClick={() => handleDocumentClick(doc.file_path, doc.title)}
                          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
                          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}
                        >
                          <div style={{ fontWeight: 'bold', fontSize: '12px', marginBottom: '2px' }}>
                            {doc.title}
                          </div>
                          <div style={{ fontSize: '11px', color: '#666', marginBottom: '2px' }}>
                            {doc.file_path}
                          </div>
                          {doc.similarity && (
                            <Tag color="blue">
                              相似度: {(doc.similarity * 100).toFixed(1)}%
                            </Tag>
                          )}
                        </div>
                      ))}
                    </div>
                  </Panel>
                </Collapse>
              </div>
            )}
          </div>
        ))}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div style={{ 
        padding: '16px', 
        borderTop: '1px solid #f0f0f0',
        backgroundColor: '#fff'
      }}>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入你的问题..."
            disabled={loading}
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ resize: 'none' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSendMessage}
            loading={loading}
            disabled={!inputValue.trim()}
          />
          <Button
            icon={<ClearOutlined />}
            onClick={handleClearChat}
            disabled={messages.length === 0}
            title="清空对话"
          />
        </Space.Compact>
      </div>
    </Modal>
  );
};

export default EnhancedChatModal;