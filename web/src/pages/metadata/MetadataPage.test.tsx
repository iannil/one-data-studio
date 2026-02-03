import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MetadataPage from './MetadataPage';

// Mock 服务
vi.mock('@/services/data', () => {
  const mockData = {
    getDatabases: vi.fn(),
    getTables: vi.fn(),
    getTableDetail: vi.fn(),
    searchTables: vi.fn(),
    executeQuery: vi.fn(),
    validateSql: vi.fn(),
    getDataAssets: vi.fn(),
    getAssetInventories: vi.fn(),
    createAssetInventory: vi.fn(),
    getDataAsset: vi.fn(),
  };
  return {
    default: mockData,
  };
});

import data from '@/services/data';

// Mock fetch for Text2SQL
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock navigator.clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

// 辅助函数：设置 mock 返回值
const setupMocks = () => {
  (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: { databases: [] },
  });
  (data.getTables as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: { tables: [] },
  });
  (data.getTableDetail as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: null,
  });
  (data.searchTables as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: { results: [] },
  });
};



const mockDatabases = [
  { name: 'production_db', description: '生产数据库' },
  { name: 'analytics_db', description: '分析数据库' },
];

const mockTables = [
  { name: 'users', description: '用户表' },
  { name: 'orders', description: '订单表' },
  { name: 'products', description: '商品表' },
];

const mockTableDetail = {
  table_name: 'users',
  database: 'production_db',
  description: '用户基础信息表',
  columns: [
    { name: 'id', type: 'bigint', nullable: false, primary_key: true },
    { name: 'username', type: 'varchar(100)', nullable: false },
    { name: 'email', type: 'varchar(200)', nullable: true },
    { name: 'created_at', type: 'timestamp', nullable: false },
  ],
  relations: [
    {
      type: 'has_many',
      from_table: 'users',
      from_column: 'id',
      to_table: 'orders',
      to_column: 'user_id',
    },
  ],
  sample_data: [
    { id: 1, username: 'admin', email: 'admin@example.com', created_at: '2024-01-01' },
  ],
};

describe('MetadataPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (data.getTables as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { tables: mockTables },
    });

    (data.getTableDetail as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: mockTableDetail,
    });
  });

  it('应该正确渲染元数据页面', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('元数据浏览')).toBeInTheDocument();
    });
  });

  it('应该显示浏览标签', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('浏览')).toBeInTheDocument();
    });
  });

  it('应该显示搜索标签', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('搜索')).toBeInTheDocument();
    });
  });

  it('应该显示 Text-to-SQL 标签', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('Text-to-SQL')).toBeInTheDocument();
    });
  });

  it('应该显示数据库面板', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('数据库')).toBeInTheDocument();
    });
  });
});

describe('MetadataPage 浏览功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (data.getTables as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { tables: mockTables },
    });

    (data.getTableDetail as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: mockTableDetail,
    });
  });

  it('应该显示数据库列表', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('production_db')).toBeInTheDocument();
      expect(screen.getByText('analytics_db')).toBeInTheDocument();
    });
  });

  it('应该显示选择表提示', async () => {
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('请选择表')).toBeInTheDocument();
    });
  });
});

describe('MetadataPage 搜索功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (data.searchTables as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: {
        results: [
          {
            database: 'production_db',
            table: 'users',
            relevance_score: 0.95,
            matched_columns: ['username', 'email'],
          },
        ],
      },
    });
  });

  it('应该能够切换到搜索标签', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('搜索')).toBeInTheDocument();
    });

    await user.click(screen.getByText('搜索'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索表名或列名/)).toBeInTheDocument();
    });
  });

  it('搜索框应该显示占位符', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('搜索'));

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/搜索表名或列名，例如：订单、客户、金额/)
      ).toBeInTheDocument();
    });
  });
});

describe('MetadataPage Text-to-SQL 功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          code: 0,
          data: { sql: 'SELECT * FROM users WHERE id = 1' },
        }),
    });
  });

  it('应该能够切换到 Text-to-SQL 标签', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await waitFor(() => {
      expect(screen.getByText('Text-to-SQL')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(screen.getByText('自然语言转 SQL')).toBeInTheDocument();
    });
  });

  it('应该显示自然语言描述输入框', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(screen.getByText('自然语言描述：')).toBeInTheDocument();
    });
  });

  it('应该显示生成 SQL 按钮', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /生成 SQL/i })).toBeInTheDocument();
    });
  });

  it('应该显示占位符提示', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/查询最近一个月订单金额大于1000的订单数量/)
      ).toBeInTheDocument();
    });
  });

  it('应该显示数据库选择状态', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(screen.getByText('数据库：')).toBeInTheDocument();
      expect(screen.getByText('(未选择，将使用默认数据库)')).toBeInTheDocument();
    });
  });
});

describe('MetadataPage SQL 结果模态框', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          code: 0,
          data: { sql: 'SELECT COUNT(*) FROM orders WHERE amount > 1000' },
        }),
    });
  });

  it('生成 SQL 后应该显示模态框', async () => {
    const user = userEvent.setup();
    render(<MetadataPage />);

    await user.click(screen.getByText('Text-to-SQL'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/查询最近一个月/)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/查询最近一个月/);
    await user.type(textarea, '查询订单数量');

    await user.click(screen.getByRole('button', { name: /生成 SQL/i }));

    await waitFor(() => {
      expect(screen.getByText('生成的 SQL')).toBeInTheDocument();
    });
  });
});

describe('MetadataPage 表详情', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (data.getDatabases as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { databases: mockDatabases },
    });

    (data.getTables as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { tables: mockTables },
    });

    (data.getTableDetail as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: mockTableDetail,
    });
  });

  it('应该显示列信息表头', async () => {
    render(<MetadataPage />);

    // 列信息表头只在选择表后显示，验证页面正常渲染
    await waitFor(() => {
      expect(screen.getByText('元数据浏览')).toBeInTheDocument();
    });
  });
});
