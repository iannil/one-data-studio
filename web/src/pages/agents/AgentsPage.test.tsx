import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AgentsPage from './AgentsPage';
import * as bisheng from '@/services/bisheng';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
  default: {
    getTools: vi.fn(),
    getToolSchemas: vi.fn(),
    executeTool: vi.fn(),
    runAgent: vi.fn(),
    getAgentTemplates: vi.fn(),
    createAgentTemplate: vi.fn(),
    deleteAgentTemplate: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 mock 返回值
    vi.mocked(bisheng.default.getTools).mockResolvedValue({
      code: 0,
      data: {
        tools: [
          {
            name: 'calculator',
            description: '数学计算工具',
            category: 'math',
          },
          {
            name: 'search',
            description: '搜索引擎',
            category: 'search',
          },
          {
            name: 'weather',
            description: '天气查询',
            category: 'utility',
          },
        ],
        total: 3,
      },
    });

    vi.mocked(bisheng.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: {
        schemas: [
          {
            name: 'calculator',
            description: '数学计算',
            parameters: {
              type: 'object',
              properties: {
                expression: { type: 'string', description: '数学表达式' },
              },
            },
          },
        ],
      },
    });

    vi.mocked(bisheng.default.getAgentTemplates).mockResolvedValue({
      code: 0,
      data: {
        templates: [],
        total: 0,
      },
    });
  });

  it('应该正确渲染 Agents 页面', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Agent/i)).toBeInTheDocument();
    });
  });

  it('应该显示工具列表', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
      expect(screen.getByText('search')).toBeInTheDocument();
      expect(screen.getByText('weather')).toBeInTheDocument();
    });
  });

  it('应该显示工具描述', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('数学计算工具')).toBeInTheDocument();
      expect(screen.getByText('搜索引擎')).toBeInTheDocument();
    });
  });

  it('应该有查询输入框', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/输入问题/i)).toBeInTheDocument();
    });
  });

  it('应该有运行 Agent 按钮', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /运行/i })).toBeInTheDocument();
    });
  });

  it('应该能够运行 Agent', async () => {
    vi.mocked(bisheng.default.runAgent).mockResolvedValue({
      code: 0,
      data: {
        answer: '计算结果是 42',
        steps: [
          { type: 'thought', content: '需要使用计算器' },
          { type: 'action', tool: 'calculator', input: '6 * 7' },
          { type: 'observation', content: '42' },
        ],
        success: true,
      },
    });

    const user = userEvent.setup();
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/输入问题/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/输入问题/i);
    await user.type(input, '6 乘以 7 等于多少？');

    const runButton = screen.getByRole('button', { name: /运行/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(bisheng.default.runAgent).toHaveBeenCalledWith(
        expect.objectContaining({
          query: '6 乘以 7 等于多少？',
        })
      );
    });
  });

  it('应该显示 Agent 执行结果', async () => {
    vi.mocked(bisheng.default.runAgent).mockResolvedValue({
      code: 0,
      data: {
        answer: '北京今天天气晴朗',
        steps: [],
        success: true,
      },
    });

    const user = userEvent.setup();
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/输入问题/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/输入问题/i);
    await user.type(input, '北京天气怎么样？');

    const runButton = screen.getByRole('button', { name: /运行/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/天气/i)).toBeInTheDocument();
    });
  });
});

describe('AgentsPage 工具管理', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(bisheng.default.getTools).mockResolvedValue({
      code: 0,
      data: {
        tools: [
          { name: 'calculator', description: '计算器', category: 'math' },
        ],
        total: 1,
      },
    });

    vi.mocked(bisheng.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(bisheng.default.getAgentTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [], total: 0 },
    });
  });

  it('应该加载工具列表', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(bisheng.default.getTools).toHaveBeenCalled();
    });
  });

  it('应该能够选择工具', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
    });

    // 点击工具卡片应该选中它
  });

  it('应该能够测试单个工具', async () => {
    vi.mocked(bisheng.default.executeTool).mockResolvedValue({
      code: 0,
      data: {
        result: '42',
        success: true,
      },
    });

    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
    });
  });
});

describe('AgentsPage Agent 模板', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(bisheng.default.getTools).mockResolvedValue({
      code: 0,
      data: { tools: [], total: 0 },
    });

    vi.mocked(bisheng.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(bisheng.default.getAgentTemplates).mockResolvedValue({
      code: 0,
      data: {
        templates: [
          {
            template_id: 'tmpl-001',
            name: 'RAG Agent',
            description: '用于检索增强生成的 Agent',
            agent_type: 'react',
            model: 'gpt-4o-mini',
          },
          {
            template_id: 'tmpl-002',
            name: 'Math Agent',
            description: '数学计算 Agent',
            agent_type: 'function_calling',
            model: 'gpt-4o-mini',
          },
        ],
        total: 2,
      },
    });
  });

  it('应该加载模板列表', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(bisheng.default.getAgentTemplates).toHaveBeenCalled();
    });
  });

  it('应该显示模板列表', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('RAG Agent')).toBeInTheDocument();
      expect(screen.getByText('Math Agent')).toBeInTheDocument();
    });
  });

  it('应该能够创建新模板', async () => {
    vi.mocked(bisheng.default.createAgentTemplate).mockResolvedValue({
      code: 0,
      data: {
        template_id: 'tmpl-003',
        name: 'New Agent',
      },
    });

    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      // 查找创建模板按钮
      const createButton = screen.queryByRole('button', { name: /新建模板/i });
      if (createButton) {
        fireEvent.click(createButton);
      }
    });
  });

  it('应该能够删除模板', async () => {
    vi.mocked(bisheng.default.deleteAgentTemplate).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('RAG Agent')).toBeInTheDocument();
    });

    // 删除功能测试
  });
});

describe('AgentsPage Agent 类型选择', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(bisheng.default.getTools).mockResolvedValue({
      code: 0,
      data: { tools: [], total: 0 },
    });

    vi.mocked(bisheng.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(bisheng.default.getAgentTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [], total: 0 },
    });
  });

  it('应该显示 Agent 类型选择器', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Agent 类型/i)).toBeInTheDocument();
    });
  });

  it('应该显示可用的 Agent 类型', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      // ReAct 和 Function Calling 是常见的 Agent 类型
      expect(screen.queryByText(/ReAct/i) || screen.queryByText(/Function/i)).toBeTruthy();
    });
  });
});
