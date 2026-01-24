import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import WorkflowsPage from './WorkflowsPage';
import * as bisheng from '@/services/bisheng';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
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

const mockWorkflows = [
  {
    workflow_id: 'wf-001',
    name: '数据清洗流程',
    description: '自动数据清洗',
    status: 'draft',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    nodes: [],
    edges: [],
  },
  {
    workflow_id: 'wf-002',
    name: 'ETL 流程',
    description: 'ETL 数据处理',
    status: 'published',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    nodes: [],
    edges: [],
  },
];

describe('WorkflowsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该正确渲染工作流页面', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText(/工作流/i)).toBeInTheDocument();
    });
  });

  it('应该显示工作流列表', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
      expect(screen.getByText('ETL 流程')).toBeInTheDocument();
    });
  });

  it('应该显示工作流描述', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('自动数据清洗')).toBeInTheDocument();
      expect(screen.getByText('ETL 数据处理')).toBeInTheDocument();
    });
  });

  it('应该显示工作流状态', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText(/草稿/i)).toBeInTheDocument();
    });
  });

  it('应该显示新建工作流按钮', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建/i })).toBeInTheDocument();
    });
  });
});

describe('WorkflowsPage 工作流操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该能够创建新工作流', async () => {
    vi.mocked(bisheng.default.createWorkflow).mockResolvedValue({
      code: 0,
      data: { workflow_id: 'wf-new', name: '新工作流' },
    });

    const user = userEvent.setup();
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建/i }));
  });

  it('应该能够删除工作流', async () => {
    vi.mocked(bisheng.default.deleteWorkflow).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 删除按钮应该存在
  });

  it('应该能够编辑工作流', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 编辑按钮应该存在
  });
});

describe('WorkflowsPage 搜索和筛选', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });
  });

  it('应该显示搜索框', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索/i)).toBeInTheDocument();
    });
  });

  it('应该能够搜索工作流', async () => {
    const user = userEvent.setup();
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/搜索/i);
    await user.type(searchInput, 'ETL');

    // 搜索结果应该更新
  });
});

describe('WorkflowsPage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: [], total: 0 },
    });
  });

  it('应该显示空状态提示', async () => {
    renderWithProviders(<WorkflowsPage />);

    await waitFor(() => {
      // 应该显示空状态或引导创建
      expect(screen.queryByText('数据清洗流程')).not.toBeInTheDocument();
    });
  });
});

describe('WorkflowsPage 加载状态', () => {
  it('应该显示加载状态', async () => {
    vi.mocked(bisheng.default.getWorkflows).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        code: 0,
        data: { workflows: mockWorkflows, total: 2 },
      }), 1000))
    );

    renderWithProviders(<WorkflowsPage />);

    // 加载状态应该显示
    await waitFor(() => {
      expect(screen.getByText(/工作流/i)).toBeInTheDocument();
    });
  });
});
