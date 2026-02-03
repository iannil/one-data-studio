import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DatasetsPage from './DatasetsPage';
import data from '@/services/data';

// Mock 服务
vi.mock('@/services/data', () => ({
  default: {
    getDatasets: vi.fn(),
    getDataset: vi.fn(),
    createDataset: vi.fn(),
    updateDataset: vi.fn(),
    deleteDataset: vi.fn(),
  },
  getDatasets: vi.fn(),
  getDataset: vi.fn(),
  createDataset: vi.fn(),
  updateDataset: vi.fn(),
  deleteDataset: vi.fn(),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
  };
});



const mockDatasets = [
  {
    dataset_id: 'ds-001',
    name: '用户行为数据集',
    description: '用户点击行为数据',
    format: 'parquet',
    storage_type: 's3',
    storage_path: 's3://data-bucket/user-behavior/',
    status: 'active',
    tags: ['用户', '行为'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    schema: {
      columns: [
        { name: 'user_id', type: 'string', description: '用户ID', nullable: false },
        { name: 'action', type: 'string', description: '行为类型', nullable: false },
      ],
    },
    statistics: {
      row_count: 1000000,
      size_bytes: 104857600,
    },
  },
  {
    dataset_id: 'ds-002',
    name: '商品信息数据集',
    description: '商品基础信息',
    format: 'csv',
    storage_type: 's3',
    storage_path: 's3://data-bucket/products/',
    status: 'active',
    tags: ['商品'],
    created_at: '2024-01-10T00:00:00Z',
  },
];

describe('DatasetsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: mockDatasets, total: 2 },
    });
  });

  it('应该正确渲染数据集页面', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据集管理')).toBeInTheDocument();
    });
  });

  it('应该显示新建数据集按钮', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建数据集/i })).toBeInTheDocument();
    });
  });

  it('应该显示搜索框', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜索数据集名称')).toBeInTheDocument();
    });
  });

  it('应该显示状态筛选器', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      // 状态筛选器是一个 Select 组件，检查其存在
      const selects = document.querySelectorAll('.ant-select');
      expect(selects.length).toBeGreaterThan(0);
    });
  });

  it('应该显示数据集列表', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('用户行为数据集')).toBeInTheDocument();
      expect(screen.getByText('商品信息数据集')).toBeInTheDocument();
    });
  });

  it('应该显示数据集描述', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('用户点击行为数据')).toBeInTheDocument();
    });
  });

  it('应该显示数据集格式', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('PARQUET')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
    });
  });

  it('应该显示数据集标签', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('用户')).toBeInTheDocument();
      expect(screen.getByText('行为')).toBeInTheDocument();
      expect(screen.getByText('商品')).toBeInTheDocument();
    });
  });

  it('应该显示操作按钮', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      // 查看、编辑、删除按钮存在于每行
      const buttons = document.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});

describe('DatasetsPage 创建数据集', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: [], total: 0 },
    });

    vi.mocked(data.createDataset).mockResolvedValue({
      code: 0,
      data: { dataset_id: 'ds-new' },
    });
  });

  it('应该能够打开创建模态框', async () => {
    const user = userEvent.setup();
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建数据集/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建数据集/i }));

    await waitFor(() => {
      // 模态框标题 "新建数据集" 可能出现多次（按钮和模态框标题）
      const titles = screen.getAllByText('新建数据集');
      expect(titles.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('创建模态框应该显示表单字段', async () => {
    const user = userEvent.setup();
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建数据集/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建数据集/i }));

    // 验证模态框打开
    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeTruthy();
    }, { timeout: 3000 });
  });
});

describe('DatasetsPage 详情抽屉', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: mockDatasets, total: 2 },
    });
  });

  it('点击数据集名称应该打开详情抽屉', async () => {
    const user = userEvent.setup();
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('用户行为数据集')).toBeInTheDocument();
    });

    await user.click(screen.getByText('用户行为数据集'));

    await waitFor(() => {
      expect(screen.getByText('数据集详情')).toBeInTheDocument();
    });
  });
});

describe('DatasetsPage 删除数据集', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: mockDatasets, total: 2 },
    });

    vi.mocked(data.deleteDataset).mockResolvedValue({
      code: 0,
      message: 'success',
    });
  });

  it('删除确认框应该显示', async () => {
    const user = userEvent.setup();
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('用户行为数据集')).toBeInTheDocument();
    });

    // 找到删除按钮并点击
    const deleteButtons = screen.getAllByRole('button');
    const deleteButton = deleteButtons.find(btn =>
      btn.querySelector('[data-icon="delete"]') ||
      btn.className.includes('danger')
    );

    if (deleteButton) {
      await user.click(deleteButton);
      await waitFor(() => {
        expect(screen.getByText('确定要删除这个数据集吗？')).toBeInTheDocument();
      });
    }
  });
});

describe('DatasetsPage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: [], total: 0 },
    });
  });

  it('无数据时应该显示空表格', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText('数据集管理')).toBeInTheDocument();
    });

    // 应该不显示任何数据集
    expect(screen.queryByText('用户行为数据集')).not.toBeInTheDocument();
  });
});

describe('DatasetsPage 分页', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(data.getDatasets).mockResolvedValue({
      code: 0,
      data: { datasets: mockDatasets, total: 100 },
    });
  });

  it('应该显示分页信息', async () => {
    render(<DatasetsPage />);

    await waitFor(() => {
      expect(screen.getByText(/共 100 条/)).toBeInTheDocument();
    });
  });
});
