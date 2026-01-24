import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CostReportPage from './CostReportPage';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key,
  }),
}));

// Mock MUI DatePicker
vi.mock('@mui/x-date-pickers/DatePicker', () => ({
  DatePicker: ({ label, value, onChange }: any) => (
    <input
      aria-label={label}
      type="date"
      value={value?.toISOString?.()?.split('T')[0] || ''}
      onChange={(e) => onChange?.(new Date(e.target.value))}
    />
  ),
}));

// Mock recharts
vi.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock URL.createObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:test');

const mockSummary = {
  total_cost: 1234.56,
  total_input_tokens: 5000000,
  total_output_tokens: 3000000,
  total_tokens: 8000000,
  call_count: 10000,
  avg_cost_per_call: 0.123456,
  avg_tokens_per_call: 800,
  by_model: {
    'gpt-4': { cost: 800, tokens: 4000000, calls: 5000 },
    'gpt-3.5-turbo': { cost: 434.56, tokens: 4000000, calls: 5000 },
  },
  by_user: {
    'user-001': { cost: 500, tokens: 3000000, calls: 4000 },
    'user-002': { cost: 400, tokens: 2500000, calls: 3500 },
    'user-003': { cost: 334.56, tokens: 2500000, calls: 2500 },
  },
  by_workflow: {
    'wf-001': { cost: 600, tokens: 4000000, calls: 5000 },
    'wf-002': { cost: 634.56, tokens: 4000000, calls: 5000 },
  },
  currency: 'USD',
  period_start: '2024-01-01T00:00:00Z',
  period_end: '2024-01-31T23:59:59Z',
};

const mockDailyData = [
  { date: '2024-01-01', cost: 40, tokens: 250000, calls: 300 },
  { date: '2024-01-02', cost: 45, tokens: 280000, calls: 350 },
  { date: '2024-01-03', cost: 38, tokens: 220000, calls: 280 },
];

const mockRecords = [
  {
    id: 'rec-001',
    timestamp: '2024-01-01T10:00:00Z',
    user_id: 'user-001',
    tenant_id: 'tenant-001',
    workflow_id: 'wf-001',
    model: 'gpt-4',
    input_tokens: 500,
    output_tokens: 300,
    total_tokens: 800,
    cost: 0.024,
    execution_time_ms: 1500,
  },
  {
    id: 'rec-002',
    timestamp: '2024-01-01T10:05:00Z',
    user_id: 'user-002',
    tenant_id: 'tenant-001',
    workflow_id: null,
    model: 'gpt-3.5-turbo',
    input_tokens: 1000,
    output_tokens: 500,
    total_tokens: 1500,
    cost: 0.003,
    execution_time_ms: 800,
  },
];

describe('CostReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      if (url.includes('/records')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ records: mockRecords, total: 100 }),
        });
      }
      if (url.includes('/export')) {
        return Promise.resolve({
          ok: true,
          blob: () => Promise.resolve(new Blob(['test'], { type: 'text/csv' })),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该正确渲染页面标题', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Cost Report')).toBeInTheDocument();
    });
  });

  it('加载时应该显示 CircularProgress', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // 永不解析

    render(<CostReportPage />);

    expect(document.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
  });
});

describe('CostReportPage 统计卡片', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示总成本', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Cost')).toBeInTheDocument();
      expect(screen.getByText('$1,234.56')).toBeInTheDocument();
    });
  });

  it('应该显示调用次数', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('10000 calls')).toBeInTheDocument();
    });
  });

  it('应该显示总 Tokens', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Tokens')).toBeInTheDocument();
      expect(screen.getByText('8.00M')).toBeInTheDocument();
    });
  });

  it('应该显示输入/输出 Tokens 分布', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText(/5.00M in/)).toBeInTheDocument();
      expect(screen.getByText(/3.00M out/)).toBeInTheDocument();
    });
  });

  it('应该显示平均每次调用成本', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Avg Cost/Call')).toBeInTheDocument();
    });
  });

  it('应该显示平均每次调用 Tokens', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Avg Tokens/Call')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 标签页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      if (url.includes('/records')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ records: mockRecords, total: 100 }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示 Overview 标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument();
    });
  });

  it('应该显示 By Model 标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'By Model' })).toBeInTheDocument();
    });
  });

  it('应该显示 Records 标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Records' })).toBeInTheDocument();
    });
  });

  it('切换到 By Model 标签页应该显示模型表格', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'By Model' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'By Model' }));

    await waitFor(() => {
      expect(screen.getByText('gpt-4')).toBeInTheDocument();
      expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
    });
  });

  it('切换到 Records 标签页应该显示记录表格', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Records' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'Records' }));

    await waitFor(() => {
      expect(screen.getByText('Timestamp')).toBeInTheDocument();
      expect(screen.getByText('User')).toBeInTheDocument();
      expect(screen.getByText('Model')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage Overview 标签页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示每日成本趋势图', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Daily Cost Trend')).toBeInTheDocument();
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });
  });

  it('应该显示按模型成本饼图', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Cost by Model')).toBeInTheDocument();
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });
  });

  it('应该显示用户成本排行', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Top Users by Cost')).toBeInTheDocument();
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 筛选器', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示时间范围选择器', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Period')).toBeInTheDocument();
    });
  });

  it('应该有多个时间范围选项', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Period')).toBeInTheDocument();
    });

    // 打开选择器
    const select = screen.getByLabelText('Period');
    await user.click(select);

    await waitFor(() => {
      expect(screen.getByText('7 days')).toBeInTheDocument();
      expect(screen.getByText('14 days')).toBeInTheDocument();
      expect(screen.getByText('30 days')).toBeInTheDocument();
      expect(screen.getByText('90 days')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 导出功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      if (url.includes('/export')) {
        return Promise.resolve({
          ok: true,
          blob: () => Promise.resolve(new Blob(['test'], { type: 'text/csv' })),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示导出按钮', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(document.querySelector('[data-testid="DownloadIcon"]')).toBeInTheDocument();
    });
  });

  it('点击导出按钮应该调用导出 API', async () => {
    const user = userEvent.setup();

    // Mock document.createElement 和 click
    const mockClick = vi.fn();
    const mockCreateElement = vi.spyOn(document, 'createElement');
    mockCreateElement.mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return { href: '', download: '', click: mockClick } as any;
      }
      return document.createElement(tagName);
    });

    render(<CostReportPage />);

    await waitFor(() => {
      expect(document.querySelector('[data-testid="DownloadIcon"]')).toBeInTheDocument();
    });

    const exportButton = document.querySelector('[data-testid="DownloadIcon"]')?.closest('button');
    if (exportButton) {
      await user.click(exportButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/export'),
          undefined
        );
      });
    }

    mockCreateElement.mockRestore();
  });
});

describe('CostReportPage 刷新功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示刷新按钮', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(document.querySelector('[data-testid="RefreshIcon"]')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 错误应该显示错误消息', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
    });
  });

  it('错误消息应该可以关闭', async () => {
    const user = userEvent.setup();
    mockFetch.mockRejectedValue(new Error('Network error'));

    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
    });

    const closeButton = document.querySelector('.MuiAlert-action button');
    if (closeButton) {
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText(/Failed to load data/)).not.toBeInTheDocument();
      });
    }
  });
});

describe('CostReportPage Records 分页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      if (url.includes('/records')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ records: mockRecords, total: 100 }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('Records 标签页应该显示分页组件', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Records' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'Records' }));

    await waitFor(() => {
      expect(document.querySelector('.MuiTablePagination-root')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage By Model 表格', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/daily')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDailyData),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('By Model 表格应该显示表头', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'By Model' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'By Model' }));

    await waitFor(() => {
      expect(screen.getByText('Model')).toBeInTheDocument();
      expect(screen.getByText('Calls')).toBeInTheDocument();
      expect(screen.getByText('Tokens')).toBeInTheDocument();
      expect(screen.getByText('Cost')).toBeInTheDocument();
      expect(screen.getByText('Avg Cost')).toBeInTheDocument();
    });
  });

  it('By Model 表格应该显示模型数据', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'By Model' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'By Model' }));

    await waitFor(() => {
      expect(screen.getByText('gpt-4')).toBeInTheDocument();
      expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
    });
  });
});
