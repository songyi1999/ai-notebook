import React, { useState, useRef, useEffect, useCallback } from 'react';
import { flushSync } from 'react-dom';
import StreamingTypewriter from './StreamingTypewriter';
import { 
  Modal, 
  Input, 
  Button, 
  List, 
  Card, 
  Typography, 
  Space, 
  Tag, 
  Divider,
  Alert,
  Tooltip
} from 'antd';
import { 
  SendOutlined, 
  RobotOutlined, 
  UserOutlined, 
  FileTextOutlined,
  ClockCircleOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { ChatResponse } from '../services/api';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

interface ChatModalProps {
  visible: boolean;
  onClose: () => void;
  onSelectFile: (filePath: string, fileName: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  relatedDocuments?: ChatResponse['related_documents'];
  processingTime?: number;
  contextLength?: number;
  error?: string;
  isLoading?: boolean;
  isStreaming?: boolean; // 新增：是否正在流式接收
}

const ChatModal: React.FC<ChatModalProps> = ({ visible, onClose, onSelectFile }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 自动滚动到底部（带防抖）
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 防抖滚动，减少频繁滚动
  const debouncedScrollToBottom = useCallback(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    scrollTimeoutRef.current = setTimeout(() => {
      scrollToBottom();
    }, 50); // 50ms防抖
  }, [scrollToBottom]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  // 发送消息（使用OpenAI兼容格式和流式响应）
  const handleSendMessage = async () => {
    if (!inputValue.trim() || loading) return;

    const question = inputValue.trim();
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
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // 准备OpenAI兼容的请求数据
      const requestData = {
        model: 'qwen2.5',
        messages: [
          ...messages.filter(msg => !msg.isLoading).map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          { role: 'user', content: question }
        ],
        stream: true,
        max_context_length: 3000,
        search_limit: 5
      };

      // 发送流式请求
      console.log('发送请求:', requestData);
      const response = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      console.log('响应状态:', response.status, response.statusText);
      console.log('响应头:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorData = await response.json();
        console.error('请求失败:', errorData);
        throw new Error(errorData.detail || '请求失败');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let responseContent = '';
      let metadata: any = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          const chunk = decoder.decode(value);
          console.log('收到chunk:', chunk);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              console.log('处理SSE数据:', data);

              if (data === '[DONE]') {
                console.log('流式传输完成，元数据:', metadata);
                // 使用flushSync确保最终状态立即更新
                flushSync(() => {
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id 
                      ? { 
                          ...msg, 
                          isLoading: false,
                          isStreaming: false, // 流式传输完成
                          relatedDocuments: metadata?.related_documents,
                          processingTime: metadata?.processing_time
                        }
                      : msg
                  ));
                });
                return;
              }

              try {
                const parsed = JSON.parse(data);

                if (parsed.error) {
                  throw new Error(parsed.error.message);
                }

                if (parsed.choices?.[0]?.delta?.content) {
                  const deltaContent = parsed.choices[0].delta.content;
                  responseContent += deltaContent;
                  console.log('更新内容:', deltaContent, '总内容长度:', responseContent.length);
                  
                  // 使用flushSync强制同步更新 - 实现真正的打字机效果
                  flushSync(() => {
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { 
                            ...msg, 
                            content: responseContent,
                            isLoading: false,
                            isStreaming: true // 标记为正在流式接收
                          }
                        : msg
                    ));
                  });
                  
                  // 使用防抖滚动，减少频繁滚动操作
                  debouncedScrollToBottom();
                }

                // 检查是否有元数据
                if (parsed.metadata) {
                  console.log('收到元数据:', parsed.metadata);
                  metadata = parsed.metadata;
                }
              } catch (parseError) {
                console.warn('解析SSE数据失败:', parseError, '原始数据:', data);
              }
            }
          }
        }
      }

      // 标记加载完成
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessage.id 
          ? { ...msg, isLoading: false }
          : msg
      ));

    } catch (error) {
      console.error('聊天请求失败:', error);
      
      // 移除加载中的消息
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessage.id));
      
      // 添加错误消息
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

  // 点击相关文档
  const handleDocumentClick = (doc: ChatResponse['related_documents'][0]) => {
    onSelectFile(doc.file_path, doc.title);
    onClose();
  };

  // 清空对话
  const handleClearChat = () => {
    setMessages([]);
  };

  // 格式化时间
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // 格式化相似度
  const formatSimilarity = (similarity: number) => {
    return (similarity * 100).toFixed(1) + '%';
  };

  return (
    <Modal
      title={
        <Space>
          <RobotOutlined />
          <span>AI助手</span>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            基于您的笔记内容智能问答
          </Text>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      styles={{
        body: { height: '600px', padding: 0 },
      }}
    >
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '600px' 
      }}>
        {/* 消息列表 */}
        <div style={{ 
          flex: 1, 
          padding: '16px', 
          overflowY: 'auto',
          backgroundColor: '#fafafa'
        }}>
          {messages.length === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              color: '#999', 
              marginTop: '100px' 
            }}>
              <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <div>向AI助手提问，我会基于您的笔记内容来回答</div>
              <div style={{ fontSize: '12px', marginTop: '8px' }}>
                例如：请总结我关于React的学习笔记
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} style={{ marginBottom: '16px' }}>
                <Card
                  size="small"
                  style={{
                    marginLeft: message.role === 'user' ? '20%' : '0',
                    marginRight: message.role === 'user' ? '0' : '20%',
                    backgroundColor: message.role === 'user' ? '#e6f7ff' : '#fff',
                  }}
                  bodyStyle={{ padding: '12px' }}
                >
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'flex-start', 
                    gap: '8px' 
                  }}>
                    <div style={{ 
                      fontSize: '16px', 
                      color: message.role === 'user' ? '#1890ff' : '#52c41a',
                      marginTop: '2px'
                    }}>
                      {message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ 
                        fontSize: '12px', 
                        color: '#999', 
                        marginBottom: '4px' 
                      }}>
                        {message.role === 'user' ? '我' : 'AI助手'} · {formatTime(message.timestamp)}
                        {message.processingTime && (
                          <Tag 
                            icon={<ClockCircleOutlined />} 
                            color="blue" 
                            style={{ marginLeft: '8px' }}
                          >
                            {message.processingTime}s
                          </Tag>
                        )}
                      </div>
                      <Paragraph 
                        style={{ 
                          margin: 0, 
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word'
                        }}
                      >
                        {message.isLoading ? (
                          <span style={{ color: '#999' }}>AI正在思考中...</span>
                        ) : message.role === 'assistant' ? (
                          <StreamingTypewriter
                            content={message.content}
                            isStreaming={message.isStreaming || false}
                            speed={30}
                            className="ai-message-content"
                          />
                        ) : (
                          message.content
                        )}
                      </Paragraph>
                      
                      {/* 错误信息 */}
                      {message.error && (
                        <Alert 
                          message={message.error} 
                          type="error" 
                          style={{ marginTop: '8px' }}
                        />
                      )}
                      
                      {/* 相关文档 */}
                      {message.relatedDocuments && message.relatedDocuments.length > 0 && (
                        <div style={{ marginTop: '12px' }}>
                          <Divider style={{ margin: '8px 0' }} />
                          <div style={{ 
                            fontSize: '12px', 
                            color: '#666', 
                            marginBottom: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}>
                            <SearchOutlined />
                            相关笔记 ({message.relatedDocuments.length})
                          </div>
                          <List
                            size="small"
                            dataSource={message.relatedDocuments}
                            renderItem={(doc) => (
                              <List.Item style={{ padding: '4px 0' }}>
                                <Card
                                  size="small"
                                  hoverable
                                  onClick={() => handleDocumentClick(doc)}
                                  style={{ 
                                    width: '100%',
                                    cursor: 'pointer'
                                  }}
                                  bodyStyle={{ padding: '8px' }}
                                >
                                  <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'space-between',
                                    alignItems: 'flex-start',
                                    gap: '8px'
                                  }}>
                                    <div style={{ flex: 1 }}>
                                      <div style={{ 
                                        display: 'flex', 
                                        alignItems: 'center', 
                                        gap: '4px',
                                        marginBottom: '4px'
                                      }}>
                                        <FileTextOutlined style={{ fontSize: '12px' }} />
                                        <Text 
                                          strong 
                                          style={{ fontSize: '12px' }}
                                          ellipsis={{ tooltip: doc.title }}
                                        >
                                          {doc.title}
                                        </Text>
                                      </div>
                                      <Text 
                                        type="secondary" 
                                        style={{ 
                                          fontSize: '11px',
                                          display: 'block',
                                          marginBottom: '4px'
                                        }}
                                        ellipsis={{ tooltip: doc.file_path }}
                                      >
                                        {doc.file_path}
                                      </Text>
                                      <Text 
                                        style={{ 
                                          fontSize: '11px',
                                          color: '#666'
                                        }}
                                        ellipsis={{ tooltip: doc.chunk_text }}
                                      >
                                        {doc.chunk_text}
                                      </Text>
                                    </div>
                                    <Tooltip title={`相似度: ${formatSimilarity(doc.similarity)}`}>
                                      <Tag 
                                        color={doc.similarity > 0.8 ? 'green' : doc.similarity > 0.6 ? 'orange' : 'default'}
                                      >
                                        {formatSimilarity(doc.similarity)}
                                      </Tag>
                                    </Tooltip>
                                  </div>
                                </Card>
                              </List.Item>
                            )}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div style={{ 
          padding: '16px', 
          borderTop: '1px solid #f0f0f0',
          backgroundColor: '#fff'
        }}>
          <div style={{ 
            display: 'flex', 
            gap: '8px', 
            alignItems: 'flex-end' 
          }}>
            <TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题... (Shift+Enter换行，Enter发送)"
              autoSize={{ minRows: 1, maxRows: 4 }}
              style={{ flex: 1 }}
              disabled={loading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={loading}
              disabled={!inputValue.trim()}
            >
              发送
            </Button>
          </div>
          
          {messages.length > 0 && (
            <div style={{ 
              marginTop: '8px', 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                已有 {messages.length} 条对话
              </Text>
              <Button 
                type="link" 
                size="small" 
                onClick={handleClearChat}
                style={{ padding: 0 }}
              >
                清空对话
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default ChatModal; 