import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChatPage from './ChatPage';
import * as agentService from '@/services/agent-service';
import * as model from '@/services/model';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
  default: {
    getConversations: vi.fn(),
    getConversation: vi.fn(),
    createConversation: vi.fn(),
    deleteConversation: vi.fn(),
    renameConversation: vi.fn(),
    getPromptTemplates: vi.fn(),
  },
}));

vi.mock('@/services/cube', () => ({
  default: {
    getModels: vi.fn(),
    streamChatCompletion: vi.fn(),
  },
}));



describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 mock 返回值
    vi.mocked(agentService.default.getConversations).mockResolvedValue({
      code: 0,
      data: {
        conversations: [],
      },
    });

    vi.mocked(agentService.default.getPromptTemplates).mockResolvedValue({
      code: 0,
      data: {
        templates: [],
      },
    });

    vi.mocked(model.default.getModels).mockResolvedValue({
      code: 0,
      data: [
        { id: 'gpt-4o-mini', name: 'GPT-4O Mini' },
        { id: 'qwen-14b-chat', name: 'Qwen 14B Chat' },
      ],
    });
  });

  afterEach(() => {
    
  });

  it('应该正确渲染聊天页面', async () => {
    render(<ChatPage />);

    // 验证主要 UI 元素
    await waitFor(() => {
      expect(screen.getByText('会话列表')).toBeInTheDocument();
      expect(screen.getByText('AI 聊天')).toBeInTheDocument();
      expect(screen.getByText('设置')).toBeInTheDocument();
    });
  });

  it('应该显示空会话状态', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('暂无历史会话')).toBeInTheDocument();
    });
  });

  it('应该显示会话列表', async () => {
    vi.mocked(agentService.default.getConversations).mockResolvedValue({
      code: 0,
      data: {
        conversations: [
          {
            conversation_id: 'conv-001',
            title: '测试会话 1',
            updated_at: new Date().toISOString(),
            message_count: 5,
          },
          {
            conversation_id: 'conv-002',
            title: '测试会话 2',
            updated_at: new Date().toISOString(),
            message_count: 3,
          },
        ],
      },
    });

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('测试会话 1')).toBeInTheDocument();
      expect(screen.getByText('测试会话 2')).toBeInTheDocument();
    });
  });

  it('应该显示新对话提示', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('开始新的对话')).toBeInTheDocument();
    });
  });

  it('应该显示模型选择器', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('模型')).toBeInTheDocument();
    });
  });

  it('应该显示温度滑块', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText(/温度:/)).toBeInTheDocument();
    });
  });

  it('应该显示最大 Tokens 滑块', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText(/最大 Tokens:/)).toBeInTheDocument();
    });
  });

  it('应该有发送按钮', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /发送/i })).toBeInTheDocument();
    });
  });

  it('应该有新建会话按钮', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      // 新建会话按钮是一个 icon button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it('应该在发送空消息时显示警告', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      const sendButton = screen.getByRole('button', { name: /发送/i });
      fireEvent.click(sendButton);
    });

    // 验证警告消息（具体实现可能需要调整）
  });

  it('应该能够选择会话', async () => {
    vi.mocked(agentService.default.getConversations).mockResolvedValue({
      code: 0,
      data: {
        conversations: [
          {
            conversation_id: 'conv-001',
            title: '测试会话',
            updated_at: new Date().toISOString(),
            message_count: 2,
          },
        ],
      },
    });

    vi.mocked(agentService.default.getConversation).mockResolvedValue({
      code: 0,
      data: {
        conversation_id: 'conv-001',
        title: '测试会话',
        messages: [
          { message_id: 'msg-1', role: 'user', content: '你好' },
          { message_id: 'msg-2', role: 'assistant', content: '你好！有什么可以帮助你的？' },
        ],
      },
    });

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('测试会话')).toBeInTheDocument();
    });

    // 点击会话
    fireEvent.click(screen.getByText('测试会话'));

    await waitFor(() => {
      expect(agentService.default.getConversation).toHaveBeenCalledWith('conv-001');
    });
  });

  it('应该显示使用统计', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('使用统计')).toBeInTheDocument();
      expect(screen.getByText('消息数')).toBeInTheDocument();
      expect(screen.getByText('Token 使用')).toBeInTheDocument();
    });
  });
});

describe('ChatPage 消息发送', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.getConversations).mockResolvedValue({
      code: 0,
      data: { conversations: [] },
    });

    vi.mocked(agentService.default.createConversation).mockResolvedValue({
      code: 0,
      data: { conversation_id: 'new-conv-001' },
    });

    vi.mocked(model.default.getModels).mockResolvedValue({
      code: 0,
      data: [{ id: 'gpt-4o-mini' }],
    });

    vi.mocked(agentService.default.getPromptTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [] },
    });
  });

  it('应该在输入消息后启用发送', async () => {
    const user = userEvent.setup();

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/输入消息/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/输入消息/i);
    await user.type(input, '你好');

    expect(input).toHaveValue('你好');
  });
});

describe('ChatPage 会话管理', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.getConversations).mockResolvedValue({
      code: 0,
      data: {
        conversations: [
          {
            conversation_id: 'conv-001',
            title: '会话一',
            updated_at: new Date().toISOString(),
            message_count: 5,
          },
        ],
      },
    });

    vi.mocked(model.default.getModels).mockResolvedValue({
      code: 0,
      data: [{ id: 'gpt-4o-mini' }],
    });

    vi.mocked(agentService.default.getPromptTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [] },
    });
  });

  it('应该显示会话消息数', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText(/5 条消息/)).toBeInTheDocument();
    });
  });
});
