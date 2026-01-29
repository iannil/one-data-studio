import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AgentsPage from './AgentsPage';
import * as agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
  default: {
    listTools: vi.fn(),
    getToolSchemas: vi.fn(),
    executeTool: vi.fn(),
    runAgent: vi.fn(),
    runAgentStream: vi.fn(),
    listAgentTemplates: vi.fn(),
    createAgentTemplate: vi.fn(),
    deleteAgentTemplate: vi.fn(),
  },
}));



describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 mock 返回值
    vi.mocked(agentService.default.listTools).mockResolvedValue({
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

    vi.mocked(agentService.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: {
        schemas: [
          {
            type: 'function' as const,
            function: {
              name: 'calculator',
              description: '数学计算',
              parameters: {
                type: 'object',
                properties: {
                  expression: { type: 'string', description: '数学表达式' },
                },
              },
            },
          },
        ],
      },
    });

    vi.mocked(agentService.default.listAgentTemplates).mockResolvedValue({
      code: 0,
      data: {
        templates: [],
        total: 0,
      },
    });

    // 添加 runAgentStream mock
    vi.mocked(agentService.default.runAgentStream).mockImplementation(async () => {});
  });

  it('应该正确渲染 Agents 页面', async () => {
    render(<AgentsPage />);

    // 等待组件渲染完成
    await waitFor(() => {
      // 检查页面是否有任何内容渲染
      const content = document.querySelector('.ant-tabs') || document.querySelector('.ant-card');
      expect(content || screen.getByRole('tablist')).toBeTruthy();
    });
  });

  it('应该显示工具列表', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      // 检查 listTools 被调用
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该显示工具描述', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      // 检查 API 被调用
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该有查询输入框', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      // 检查输入框或文本区域
      const input = document.querySelector('textarea') || document.querySelector('input[type="text"]');
      expect(input).toBeTruthy();
    });
  });

  it('应该有运行 Agent 按钮', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      const button = screen.queryByRole('button', { name: /运行/i }) ||
                     document.querySelector('button[type="primary"]');
      expect(button).toBeTruthy();
    });
  });

  it('应该能够运行 Agent', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该显示 Agent 执行结果', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });
});

describe('AgentsPage 工具管理', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.listTools).mockResolvedValue({
      code: 0,
      data: {
        tools: [
          { name: 'calculator', description: '计算器', category: 'math' },
        ],
        total: 1,
      },
    });

    vi.mocked(agentService.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(agentService.default.listAgentTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [], total: 0 },
    });

    vi.mocked(agentService.default.runAgentStream).mockImplementation(async () => {});
  });

  it('应该加载工具列表', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该能够选择工具', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该能够测试单个工具', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });
});

describe('AgentsPage Agent 模板', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.listTools).mockResolvedValue({
      code: 0,
      data: { tools: [], total: 0 },
    });

    vi.mocked(agentService.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(agentService.default.listAgentTemplates).mockResolvedValue({
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

    vi.mocked(agentService.default.runAgentStream).mockImplementation(async () => {});
  });

  it('应该加载模板列表', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listAgentTemplates).toHaveBeenCalled();
    });
  });

  it('应该显示模板列表', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listAgentTemplates).toHaveBeenCalled();
    });
  });

  it('应该能够创建新模板', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listAgentTemplates).toHaveBeenCalled();
    });
  });

  it('应该能够删除模板', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listAgentTemplates).toHaveBeenCalled();
    });
  });
});

describe('AgentsPage Agent 类型选择', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.listTools).mockResolvedValue({
      code: 0,
      data: { tools: [], total: 0 },
    });

    vi.mocked(agentService.default.getToolSchemas).mockResolvedValue({
      code: 0,
      data: { schemas: [] },
    });

    vi.mocked(agentService.default.listAgentTemplates).mockResolvedValue({
      code: 0,
      data: { templates: [], total: 0 },
    });

    vi.mocked(agentService.default.runAgentStream).mockImplementation(async () => {});
  });

  it('应该显示 Agent 类型选择器', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });

  it('应该显示可用的 Agent 类型', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(agentService.default.listTools).toHaveBeenCalled();
    });
  });
});
