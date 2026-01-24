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
  Dropdown,
  Modal,
  Popconfirm,
} from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  RobotOutlined,
  UserOutlined,
  EditOutlined,
  MoreOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useQuery } from '@tanstack/react-query';
import cube, { type ChatCompletionUsage } from '@/services/cube';
import bisheng, { type Conversation, type ConversationMessage, saveMessage, getConversationUsage } from '@/services/bisheng';
import type { ChatMessage } from '@/services/cube';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

const { TextArea } = Input;
const { Option } = Select;

interface Message extends ChatMessage {
  id: string;
}

interface SessionItem extends Conversation {
  message_count?: number;
}

function ChatPage() {
  // 会话状态
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // 聊天状态
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [model, setModel] = useState<string>('qwen-14b-chat');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxTokens, setMaxTokens] = useState<number>(2048);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');

  // Token 使用统计
  const [tokenUsage, setTokenUsage] = useState<{
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
  }>({ total_prompt_tokens: 0, total_completion_tokens: 0, total_tokens: 0 });

  // 重命名相关状态
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [newSessionTitle, setNewSessionTitle] = useState('');

  // 系统提示词状态（用于 Prompt 模板）
  const [systemPrompt, setSystemPrompt] = useState('你是一个智能助手，请用中文回答问题。');
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

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

  // 加载会话列表
  useEffect(() => {
    loadSessions();
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // 加载会话列表
  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true);
      const response = await bisheng.getConversations();
      if (response.code === 0 && response.data?.conversations) {
        const sessionList = response.data.conversations.map((conv) => ({
          ...conv,
          message_count: conv.message_count || 0,
        }));
        setSessions(sessionList);

        // 如果没有选中的会话且有会话列表，自动选择第一个
        if (!currentConversationId && sessionList.length > 0) {
          await selectSession(sessionList[0].conversation_id);
        }
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // 选择会话
  const selectSession = async (conversationId: string) => {
    try {
      setCurrentConversationId(conversationId);
      const response = await bisheng.getConversation(conversationId);
      if (response.code === 0 && response.data) {
        const sessionData = response.data;
        // 转换消息格式
        const messageList: Message[] = (sessionData.messages || []).map((msg: ConversationMessage) => ({
          id: msg.message_id || `msg-${Date.now()}`,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          created_at: msg.created_at,
        }));
        setMessages(messageList);

        // 加载 Token 使用统计
        loadTokenUsage(conversationId);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
      message.error('加载会话失败');
    }
  };

  // 加载 Token 使用统计
  const loadTokenUsage = async (conversationId: string) => {
    try {
      const response = await getConversationUsage(conversationId);
      if (response.code === 0 && response.data) {
        setTokenUsage({
          total_prompt_tokens: response.data.total_prompt_tokens || 0,
          total_completion_tokens: response.data.total_completion_tokens || 0,
          total_tokens: response.data.total_tokens || 0,
        });
      }
    } catch (error) {
      console.error('Failed to load token usage:', error);
    }
  };

  // 新建会话
  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setStreamingContent('');
    setTokenUsage({ total_prompt_tokens: 0, total_completion_tokens: 0, total_tokens: 0 });
  };

  // 创建新会话（第一次发送消息时）
  const createNewConversation = async (firstMessage: string) => {
    try {
      const title = firstMessage.slice(0, 50) + (firstMessage.length > 50 ? '...' : '');
      const response = await bisheng.createConversation(title);
      if (response.code === 0 && response.data?.conversation_id) {
        const newId = response.data.conversation_id;
        setCurrentConversationId(newId);
        await loadSessions(); // 刷新会话列表
        return newId;
      }
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
    return null;
  };

  // 删除会话
  const handleDeleteSession = async (conversationId: string) => {
    try {
      await bisheng.deleteConversation(conversationId);
      message.success('会话已删除');

      // 如果删除的是当前会话，清空消息
      if (currentConversationId === conversationId) {
        handleNewConversation();
      }

      await loadSessions();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      message.error('删除会话失败');
    }
  };

  // 打开重命名对话框
  const openRenameModal = (conversationId: string, currentTitle: string) => {
    setRenamingSessionId(conversationId);
    setNewSessionTitle(currentTitle);
    setRenameModalVisible(true);
  };

  // 确认重命名
  const handleRenameSession = async () => {
    if (!renamingSessionId || !newSessionTitle.trim()) {
      message.warning('请输入会话标题');
      return;
    }

    try {
      await bisheng.renameConversation(renamingSessionId, newSessionTitle.trim());
      message.success('重命名成功');
      setRenameModalVisible(false);
      await loadSessions();
    } catch (error) {
      console.error('Failed to rename conversation:', error);
      message.error('重命名失败');
    }
  };

  // 会话操作菜单
  const getSessionMenuItems = (session: SessionItem): MenuProps['items'] => [
    {
      key: 'rename',
      label: '重命名',
      icon: <EditOutlined />,
      onClick: () => openRenameModal(session.conversation_id, session.title),
    },
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => handleDeleteSession(session.conversation_id),
    },
  ];

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return '今天';
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  // 应用 Prompt 模板
  const handleTemplateSelect = (templateId: string | null) => {
    setSelectedTemplateId(templateId);
    if (!templateId) {
      setSystemPrompt('你是一个智能助手，请用中文回答问题。');
      return;
    }
    const templates = templatesData?.data?.templates || [];
    const template = templates.find((t) => t.template_id === templateId);
    if (template) {
      setSystemPrompt(template.content || template.template || '你是一个智能助手，请用中文回答问题。');
      message.success(`已应用模板: ${template.name}`);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) {
      message.warning('请输入消息内容');
      return;
    }

    // 如果没有当前会话，创建新会话
    let conversationId = currentConversationId;
    if (!conversationId) {
      conversationId = await createNewConversation(input);
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);
    setStreamingContent('');

    // 保存用户消息到后端
    if (conversationId) {
      saveMessage(conversationId, {
        role: 'user',
        content: currentInput,
        model,
      }).catch((err) => {
        // Log error but don't block the chat - message is already displayed locally
        console.error('Failed to save user message:', err instanceof Error ? err.message : 'Unknown error');
      });
    }

    try {
      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      // 添加占位消息
      setMessages((prev) => [...prev, assistantMessage]);

      // 用于收集完整的助手回复
      let fullContent = '';

      // 使用流式 API
      await cube.streamChatCompletion(
        {
          model,
          messages: [
            { role: 'system', content: systemPrompt },
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: 'user', content: currentInput },
          ],
          temperature,
          max_tokens: maxTokens,
        },
        // onChunk
        (chunk: string) => {
          fullContent += chunk;
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
        // onComplete - receive usage data from stream
        (usage?: ChatCompletionUsage) => {
          setIsLoading(false);
          setStreamingContent('');

          // Calculate usage from stream data or estimate
          const finalUsage = usage || {
            prompt_tokens: 0,
            completion_tokens: 0,
            total_tokens: 0,
          };

          // 保存助手消息到后端
          if (conversationId && fullContent) {
            saveMessage(conversationId, {
              role: 'assistant',
              content: fullContent,
              model,
              usage: finalUsage,
            })
              .then(() => {
                // 刷新 token 使用统计
                loadTokenUsage(conversationId!);
              })
              .catch((err) => {
                // Log error but don't disrupt the user experience
                console.error('Failed to save assistant message:', err instanceof Error ? err.message : 'Unknown error');
              });
          }
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

  return (
    <>
      <div style={{ padding: '24px', height: 'calc(100vh - 64px)', display: 'flex' }}>
        {/* 左侧会话列表 */}
        <Card
          title="会话列表"
          style={{ width: 280, marginRight: 16, display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'auto', padding: 0 }}
          extra={
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={handleNewConversation}
              title="新建会话"
            />
          }
        >
          {isLoadingSessions ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#999' }}>
              加载中...
            </div>
          ) : sessions.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#999' }}>
              <HistoryOutlined style={{ fontSize: 24, marginBottom: 8 }} />
              <p>暂无历史会话</p>
            </div>
          ) : (
            <List
              dataSource={sessions}
              renderItem={(session) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    padding: '12px 16px',
                    backgroundColor:
                      currentConversationId === session.conversation_id ? '#e6f4ff' : 'transparent',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                  onClick={() => selectSession(session.conversation_id)}
                >
                  <List.Item.Meta
                    avatar={<Avatar icon={<RobotOutlined />} size="small" />}
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span
                          style={{
                            flex: 1,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {session.title || '未命名会话'}
                        </span>
                      </div>
                    }
                    description={
                      <span style={{ fontSize: 12 }}>
                        {formatTime(session.updated_at)} · {session.message_count || 0} 条消息
                      </span>
                    }
                  />
                  <Dropdown
                    menu={{ items: getSessionMenuItems(session) }}
                    trigger={['click']}
                    placement="bottomRight"
                  >
                    <Button
                      type="text"
                      icon={<MoreOutlined />}
                      size="small"
                      onClick={(e) => e.stopPropagation()}
                      style={{ marginLeft: 8 }}
                    />
                  </Dropdown>
                </List.Item>
              )}
            />
          )}
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
                <Select
                  placeholder="选择模板"
                  style={{ width: '100%' }}
                  allowClear
                  value={selectedTemplateId}
                  onChange={handleTemplateSelect}
                >
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
                <span>{tokenUsage.total_tokens > 0 ? tokenUsage.total_tokens.toLocaleString() : '-'}</span>
              </div>
              {tokenUsage.total_tokens > 0 && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span style={{ color: '#999' }}>输入 Token</span>
                    <span style={{ color: '#999' }}>{tokenUsage.total_prompt_tokens.toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span style={{ color: '#999' }}>输出 Token</span>
                    <span style={{ color: '#999' }}>{tokenUsage.total_completion_tokens.toLocaleString()}</span>
                  </div>
                </>
              )}
            </Space>
          </div>
        </Space>
      </Card>
    </div>

      {/* 重命名会话对话框 */}
      <Modal
        title="重命名会话"
        open={renameModalVisible}
        onOk={handleRenameSession}
        onCancel={() => setRenameModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        <Input
          value={newSessionTitle}
          onChange={(e) => setNewSessionTitle(e.target.value)}
          placeholder="请输入会话标题"
          maxLength={100}
          onPressEnter={handleRenameSession}
          autoFocus
        />
      </Modal>
    </>
  );
}

// 使用 ErrorBoundary 包裹导出组件
function ChatPageWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <ChatPage />
    </ErrorBoundary>
  );
}

export default ChatPageWithErrorBoundary;
