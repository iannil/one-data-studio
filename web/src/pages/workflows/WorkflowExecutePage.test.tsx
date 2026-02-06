import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import WorkflowExecutePage from './WorkflowExecutePage';
import agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    getWorkflow: vi.fn(),
    getWorkflowExecutions: vi.fn(),
    getExecutionLogs: vi.fn(),
    startWorkflow: vi.fn(),
    stopWorkflow: vi.fn(),
  },
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({ workflowId: 'wf-001' }),
  };
});

// Mock WorkflowLogViewer
vi.mock('@/components/WorkflowLogViewer', () => ({
  default: ({ logs }: { logs?: unknown[] }) => (
    <div data-testid="log-viewer">日志数: {logs?.length || 0}</div>
  ),
}));



const mockWorkflow = {
  workflow_id: 'wf-001',
  name: '测试工作流',
  description: '用于测试的工作流',
  type: 'custom',
  status: 'published',
  created_at: '2024-01-01T00:00:00Z',
  created_by: 'admin',
};

const mockExecutions = [
  {
    id: 'exec-001',
    workflow_id: 'wf-001',
    status: 'completed',
    started_at: '2024-01-01T10:00:00Z',
    completed_at: '2024-01-01T10:01:00Z',
    duration_ms: 60000,
  },
  {
    id: 'exec-002',
    workflow_id: 'wf-001',
    status: 'running',
    started_at: '2024-01-01T11:00:00Z',
    duration_ms: 30000,
  },
  {
    id: 'exec-003',
    workflow_id: 'wf-001',
    status: 'failed',
    started_at: '2024-01-01T09:00:00Z',
    completed_at: '2024-01-01T09:00:30Z',
    duration_ms: 30000,
    error: '执行失败：连接超时',
  },
];

describe('WorkflowExecutePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflow).mockResolvedValue({
      code: 0,
      data: mockWorkflow,
    });

    vi.mocked(agentService.getWorkflowExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });

    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: [] },
    });
  });

  it('应该正确渲染执行页面', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('测试工作流')).toBeInTheDocument();
    });
  });

  it('应该显示工作流详情', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('用于测试的工作流')).toBeInTheDocument();
    });
  });

  it('应该显示返回按钮', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /返回/i })).toBeInTheDocument();
    });
  });

  it('应该显示执行历史标签', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText(/执行历史/)).toBeInTheDocument();
    });
  });

  it('应该显示执行日志标签', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('执行日志')).toBeInTheDocument();
    });
  });

  it('应该显示输入配置标签', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('输入配置')).toBeInTheDocument();
    });
  });
});

describe('WorkflowExecutePage 执行历史', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflow).mockResolvedValue({
      code: 0,
      data: mockWorkflow,
    });

    vi.mocked(agentService.getWorkflowExecutions).mockResolvedValue({
      code: 0,
      data: { executions: mockExecutions },
    });
  });

  it('应该显示执行记录', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('exec-001')).toBeInTheDocument();
      expect(screen.getByText('exec-002')).toBeInTheDocument();
    });
  });

  it('应该显示执行状态', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('已完成')).toBeInTheDocument();
      expect(screen.getByText('运行中')).toBeInTheDocument();
      expect(screen.getByText('失败')).toBeInTheDocument();
    });
  });

  it('应该显示停止按钮（运行中的执行）', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      const stopButtons = screen.getAllByRole('button', { name: /停止/i });
      expect(stopButtons.length).toBeGreaterThan(0);
    });
  });

  it('应该显示查看日志按钮', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      const logButtons = screen.getAllByRole('button', { name: /查看日志/i });
      expect(logButtons.length).toBeGreaterThan(0);
    });
  });
});

describe('WorkflowExecutePage 启动工作流', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflow).mockResolvedValue({
      code: 0,
      data: mockWorkflow,
    });

    vi.mocked(agentService.getWorkflowExecutions).mockResolvedValue({
      code: 0,
      data: { executions: [] },
    });

    vi.mocked(agentService.startWorkflow).mockResolvedValue({
      code: 0,
      data: { execution_id: 'exec-new' },
    });
  });

  it('应该能够切换到输入配置标签', async () => {
    const user = userEvent.setup();
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('输入配置')).toBeInTheDocument();
    });

    await user.click(screen.getByText('输入配置'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /启动工作流/i })).toBeInTheDocument();
    });
  });

  it('应该显示输入文本框', async () => {
    const user = userEvent.setup();
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('输入配置')).toBeInTheDocument();
    });

    await user.click(screen.getByText('输入配置'));

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });
  });
});

describe('WorkflowExecutePage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflow).mockResolvedValue({
      code: 0,
      data: mockWorkflow,
    });

    vi.mocked(agentService.getWorkflowExecutions).mockResolvedValue({
      code: 0,
      data: { executions: [] },
    });
  });

  it('应该显示无执行记录提示', async () => {
    render(<WorkflowExecutePage />);

    await waitFor(() => {
      expect(screen.getByText('暂无执行记录')).toBeInTheDocument();
    });
  });
});

describe('WorkflowExecutePage 状态提示', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getWorkflow).mockResolvedValue({
      code: 0,
      data: mockWorkflow,
    });
  });

  it('应该显示运行中提示', async () => {
    vi.mocked(agentService.getWorkflowExecutions).mockResolvedValue({
      code: 0,
      data: {
        executions: [
          {
            id: 'exec-running',
            workflow_id: 'wf-001',
            status: 'running',
            started_at: '2024-01-01T10:00:00Z',
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<WorkflowExecutePage />);

    // 点击执行记录查看详情
    await waitFor(() => {
      expect(screen.getByText('exec-running')).toBeInTheDocument();
    });

    await user.click(screen.getByText('exec-running'));

    await waitFor(() => {
      expect(screen.getByText(/工作流正在运行中/)).toBeInTheDocument();
    });
  });
});
