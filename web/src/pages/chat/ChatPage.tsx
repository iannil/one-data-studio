import { useState, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Select,
  Space,
  Slider,
  Tag,
  message,
  Divider,
  List,
  Avatar,
} from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  RobotOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import cube from '@/services/cube';
import bisheng from '@/services/bisheng';
import type { ChatMessage } from '@/services/cube';

const { TextArea } = Input;
const { Option } = Select;

interface Message extends ChatMessage {
  id: string;
}

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [model, setModel] = useState<string>('qwen-14b-chat');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxTokens, setMaxTokens] = useState<number>(2048);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 获取可用模型列表
  const { data: modelsData, isLoading: isLoadingModels } = useQuery({
    queryKey: ['models'],
    queryFn: cube.getModels,
    refetchInterval: 60000, // 每分钟刷新一次
  });

  // 获取 Prompt 模板
  const { data: templatesData } = useQuery({
    queryKey: ['templates'],
    queryFn: bisheng.getPromptTemplates,
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim()) {
      message.warning('请输入消息内容');
      return;
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setStreamingContent('');

    try {
      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      // 添加占位消息
      setMessages((prev) => [...prev, assistantMessage]);

      // 使用流式 API
      await cube.streamChatCompletion(
        {
          model,
          messages: [
            { role: 'system', content: '你是一个智能助手，请用中文回答问题。' },
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: 'user', content: input },
          ],
          temperature,
          max_tokens: maxTokens,
        },
        // onChunk
        (chunk: string) => {
          setStreamingContent((prev) => {
            const newContent = prev + chunk;
            // 更新最后一条消息的内容
            setMessages((prevMessages) => {
              const updated = [...prevMessages];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: newContent,
              };
              return updated;
            });
            return newContent;
          });
        },
        // onComplete
        () => {
          setIsLoading(false);
          setStreamingContent('');
        },
        // onError
        (error: Error) => {
          setIsLoading(false);
          setStreamingContent('');
          message.error(`请求失败: ${error.message}`);
          // 移除失败的助手消息
          setMessages((prev) => prev.slice(0, -1));
        }
      );
    } catch (error) {
      setIsLoading(false);
      message.error('发送消息失败');
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setStreamingContent('');
  };

  const handleDeleteMessage = (messageId: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
  };

  return (
    <div style={{ padding: '24px', height: 'calc(100vh - 64px)', display: 'flex' }}>
      {/* 左侧会话列表 */}
      <Card
        title="会话列表"
        style={{ width: 280, marginRight: 16, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'auto' }}
        extra={
          <Button type="text" icon={<PlusOutlined />} onClick={handleNewConversation} />
        }
      >
        <List
          dataSource={[]} // TODO: 从 API 获取历史会话
          renderItem={() => (
            <List.Item>
              <List.Item.Meta
                avatar={<Avatar icon={<RobotOutlined />} />}
                title="新对话"
                description="暂无消息"
              />
            </List.Item>
          )}
        />
      </Card>

      {/* 中间聊天区域 */}
      <Card
        title="AI 聊天"
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
      >
        {/* 消息列表 */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            backgroundColor: '#f5f5f5',
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#999',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>开始新的对话</p>
              </div>
            </div>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      maxWidth: '70%',
                      alignItems: 'flex-start',
                    }}
                  >
                    {msg.role === 'assistant' && (
                      <Avatar
                        icon={<RobotOutlined />}
                        style={{ backgroundColor: '#1677ff', marginRight: 8 }}
                      />
                    )}
                    <div>
                      <div
                        className={
                          msg.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'
                        }
                      >
                        {msg.content || <span style={{ color: '#999' }}>正在思考...</span>}
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        {msg.role === 'user' ? '用户' : 'AI 助手'}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <Avatar
                        icon={<UserOutlined />}
                        style={{ backgroundColor: '#52c41a', marginLeft: 8 }}
                      />
                    )}
                  </div>
                </div>
              ))}
              {isLoading && streamingContent === '' && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <Avatar
                      icon={<RobotOutlined />}
                      style={{ backgroundColor: '#1677ff', marginRight: 8 }}
                    />
                    <div className="chat-message-assistant">
                      <span style={{ color: '#999' }}>正在思考...</span>
                    </div>
                  </div>
                </div>
              )}
            </Space>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div style={{ borderTop: '1px solid #e8e8e8', padding: '16px' }}>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入消息... (Shift + Enter 换行)"
              autoSize={{ minRows: 1, maxRows: 4 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isLoading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={isLoading}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Card>

      {/* 右侧设置面板 */}
      <Card
        title="设置"
        style={{ width: 320, marginLeft: 16 }}
        bodyStyle={{ paddingTop: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <div style={{ marginBottom: 8 }}>模型</div>
            <Select
              value={model}
              onChange={setModel}
              loading={isLoadingModels}
              style={{ width: '100%' }}
            >
              {modelsData?.data?.map((m) => (
                <Option key={m.id} value={m.id}>
                  {m.id}
                </Option>
              ))}
            </Select>
          </div>

          <div>
            <div style={{ marginBottom: 8 }}>
              温度: {temperature.toFixed(1)}
              <Tag style={{ marginLeft: 8 }} color="blue">
                {temperature < 0.3 ? '保守' : temperature < 0.7 ? '平衡' : '创意'}
              </Tag>
            </div>
            <Slider
              min={0}
              max={1}
              step={0.1}
              value={temperature}
              onChange={setTemperature}
            />
          </div>

          <div>
            <div style={{ marginBottom: 8 }}>最大 Tokens: {maxTokens}</div>
            <Slider
              min={256}
              max={8192}
              step={256}
              value={maxTokens}
              onChange={setMaxTokens}
            />
          </div>

          {templatesData?.data?.templates && templatesData.data.templates.length > 0 && (
            <>
              <Divider style={{ margin: '8px 0' }} />
              <div>
                <div style={{ marginBottom: 8 }}>Prompt 模板</div>
                <Select placeholder="选择模板" style={{ width: '100%' }} allowClear>
                  {templatesData.data.templates.map((t) => (
                    <Option key={t.template_id} value={t.template_id}>
                      {t.name}
                    </Option>
                  ))}
                </Select>
              </div>
            </>
          )}

          <Divider style={{ margin: '8px 0' }} />

          <div>
            <div style={{ marginBottom: 8 }}>使用统计</div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#666' }}>消息数</span>
                <span>{messages.length}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#666' }}>Token 使用</span>
                <span>-</span>
              </div>
            </Space>
          </div>
        </Space>
      </Card>
    </div>
  );
}

export default ChatPage;
