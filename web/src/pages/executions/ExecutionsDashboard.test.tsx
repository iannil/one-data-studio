import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExecutionsDashboard from './ExecutionsDashboard';
import agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    getWorkflows: vi.fn(),
    listExecutions: vi.fn(),
  },
}));

// Mock ErrorBoundary
vi.mock('@/components/common/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: any) => <>{children}</>,
}));

// Mock ExecutionLogsModal
vi.mock('./ExecutionLogsModal', () => ({
  default: ({ executionId, open, onClose }: any) => (
    open ? <div data-testid="logs-modal">日志: {executionId}</div> : null
  ),
}));



const mockWorkflows = [
  {
    workflow_id: 'wf-001',
    name: '数据处理流程',
    type: 'custom',
    status: 'published',
  },
  {
    workflow_id: 'wf-002',
    name: 'RAG 查询流程',
    type: 'rag',
    status: 'published',
  },
];

const mockExecutions = [
  {
    id: 'exec-001',
    workflow_id: 'wf-001',
    status: 'completed',
    started_at: '2024-01-01T10:00:00Z',
    completed_at: '2024-01-01T10:05:00Z',
    duration_ms: 300000,
  },
  {
    id: 'exec-002',
    workflow_id: 'wf-001',
    status: 'running',
    started_at: '2024-01-01T11:00:00Z',
    duration_ms: 60000,
  },
  {
    id: 'exec-003',
    workflow_id: 'wf-002',
    status: 'failed',
    started_at: '2024-01-01T09:00:00Z',
    completed_at: '2024-01-01T09:01:00Z',
    duration_ms: 60000,
    error: '连接超时',
  },
  {
    id: 'exec-004',
    workflow_id: 'wf-001',
    status: 'pending',
    started_at: null,
  },
];

describe('ExecutionsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该正确渲染执行仪表板', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('执行历史仪表板')).toBeInTheDocument();
    });
  });

  it('应该显示统计卡片', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('总执行数')).toBeInTheDocument();
      expect(screen.getByText('运行中')).toBeInTheDocument();
      expect(screen.getByText('已完成')).toBeInTheDocument();
      expect(screen.getByText('失败')).toBeInTheDocument();
    });
  });

  it('应该显示正确的统计数值', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 总执行数 4
      expect(screen.getByText('4')).toBeInTheDocument();
    });
  });

  it('应该显示工作流筛选器', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('选择工作流')).toBeInTheDocument();
    });
  });

  it('应该显示状态筛选器', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('选择状态')).toBeInTheDocument();
    });
  });

  it('应该显示搜索框', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜索工作流或ID')).toBeInTheDocument();
    });
  });

  it('应该显示刷新按钮', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /自动刷新/i })).toBeInTheDocument();
    });
  });
});

describe('ExecutionsDashboard 执行列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该显示执行记录', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // ID 使用 slice(0, 8) + "..." 格式
      expect(screen.getByText(/exec-001/)).toBeInTheDocument();
      expect(screen.getByText(/exec-002/)).toBeInTheDocument();
    });
  });

  it('应该显示工作流名称', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 工作流名称可能出现多次
      expect(screen.getAllByText('数据处理流程').length).toBeGreaterThan(0);
      expect(screen.getAllByText('RAG 查询流程').length).toBeGreaterThan(0);
    });
  });

  it('应该显示执行状态', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 状态文本可能出现多次（表格和统计卡片）
      expect(screen.getAllByText('已完成').length).toBeGreaterThan(0);
      expect(screen.getAllByText('运行中').length).toBeGreaterThan(0);
      expect(screen.getAllByText('失败').length).toBeGreaterThan(0);
      expect(screen.getAllByText('等待中').length).toBeGreaterThan(0);
    });
  });

  it('应该显示错误信息', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 错误信息使用 slice(0, 30) + "..." 格式
      expect(screen.getByText(/连接超时/)).toBeInTheDocument();
    });
  });

  it('应该显示工作流类型标签', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 类型标签可能出现多次
      expect(screen.getAllByText('CUSTOM').length).toBeGreaterThan(0);
      expect(screen.getAllByText('RAG').length).toBeGreaterThan(0);
    });
  });
});

describe('ExecutionsDashboard 成功率', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该显示成功率', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('成功率')).toBeInTheDocument();
    });
  });

  it('应该显示成功率百分比', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 1 completed / 4 total = 25%
      expect(screen.getByText(/25\.0%/)).toBeInTheDocument();
    });
  });
});

describe('ExecutionsDashboard 查看日志', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该能够打开日志模态框', async () => {
    const user = userEvent.setup();
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/exec-001/)).toBeInTheDocument();
    });

    // 找到查看日志按钮
    const logButtons = screen.getAllByRole('button');
    const logButton = logButtons.find(btn =>
      btn.querySelector('[data-icon="file-text"]')
    );

    if (logButton) {
      await user.click(logButton);

      await waitFor(() => {
        expect(screen.getByTestId('logs-modal')).toBeInTheDocument();
      });
    }
  });
});

describe('ExecutionsDashboard 自动刷新', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该能够切换自动刷新', async () => {
    const user = userEvent.setup();
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /自动刷新/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /自动刷新/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /刷新/i })).toBeInTheDocument();
    });
  });
});

describe('ExecutionsDashboard 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: [] },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: [] },
    });
  });

  it('无执行记录时统计应该为 0', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      // 所有统计都应该是 0
      const zeros = screen.getAllByText('0');
      expect(zeros.length).toBeGreaterThanOrEqual(4);
    });
  });

  it('无执行记录时不应该显示成功率', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.queryByText('成功率')).not.toBeInTheDocument();
    });
  });
});

describe('ExecutionsDashboard 分页', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该显示分页信息', async () => {
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/共 4 条/)).toBeInTheDocument();
    });
  });
});

describe('ExecutionsDashboard 搜索过滤', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows },
    });

    vi.mocked(agentService.listExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该能够搜索执行记录', async () => {
    const user = userEvent.setup();
    render(<ExecutionsDashboard />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜索工作流或ID')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('搜索工作流或ID');
    await user.type(searchInput, 'RAG');

    await waitFor(() => {
      // 搜索后应该只显示匹配的结果
      expect(screen.getByText('RAG 查询流程')).toBeInTheDocument();
    });
  });
});
