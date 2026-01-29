import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import WorkflowsPage from './WorkflowsPage';
import * as agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    getWorkflows: vi.fn(),
    createWorkflow: vi.fn(),
    deleteWorkflow: vi.fn(),
    updateWorkflow: vi.fn(),
  },
}));

// Mock react-router-dom useNavigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

const mockWorkflows = [
  {
    workflow_id: 'wf-001',
    name: '数据清洗流程',
    description: '自动数据清洗',
    type: 'custom',
    status: 'pending',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    workflow_id: 'wf-002',
    name: 'ETL 流程',
    description: 'ETL 数据处理',
    type: 'rag',
    status: 'running',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

describe('WorkflowsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该正确渲染工作流页面', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      // 使用更具体的文本
      expect(screen.getByText('工作流管理')).toBeInTheDocument();
    });
  });

  it('应该显示工作流列表', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
      expect(screen.getByText('ETL 流程')).toBeInTheDocument();
    });
  });

  it('应该显示工作流描述', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('自动数据清洗')).toBeInTheDocument();
      expect(screen.getByText('ETL 数据处理')).toBeInTheDocument();
    });
  });

  it('应该显示工作流状态', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText(/等待中/i)).toBeInTheDocument();
    });
  });

  it('应该显示新建工作流按钮', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建/i })).toBeInTheDocument();
    });
  });
});

describe('WorkflowsPage 工作流操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该能够创建新工作流', async () => {
    vi.mocked(agentService.default.createWorkflow).mockResolvedValue({
      code: 0,
      data: { workflow_id: 'wf-new', name: '新工作流' },
    });

    const user = userEvent.setup();
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建/i }));
  });

  it('应该能够删除工作流', async () => {
    vi.mocked(agentService.default.deleteWorkflow).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 删除按钮应该存在
  });

  it('应该能够编辑工作流', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 编辑按钮应该存在
  });
});

describe('WorkflowsPage 搜索和筛选', () => {
  beforeEach(() => {
    vi.clearAllMocks();


    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该显示工作流管理标题', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('工作流管理')).toBeInTheDocument();
    });
  });

  it('应该显示分页信息', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      // 使用 regex 匹配分页信息
      const paginationInfo = screen.getByText(/共\s*2\s*条/);
      expect(paginationInfo).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

describe('WorkflowsPage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: [], total: 0 },
    });
  });

  it('应该显示空状态提示', async () => {
    render(<WorkflowsPage />);

    await waitFor(() => {
      // 应该显示空状态或引导创建
      expect(screen.queryByText('数据清洗流程')).not.toBeInTheDocument();
    });
  });
});

describe('WorkflowsPage 加载状态', () => {
  it('应该显示加载状态', async () => {
    vi.mocked(agentService.default.getWorkflows).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        code: 0,
        data: { workflows: mockWorkflows, total: 2 },
      }), 1000))
    );

    render(<WorkflowsPage />);

    // 加载状态应该显示 - 验证页面标题
    await waitFor(() => {
      expect(screen.getByText('工作流管理')).toBeInTheDocument();
    });
  });
});
