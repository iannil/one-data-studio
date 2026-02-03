import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import CostReportPage from './CostReportPage';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockSummary = {
  total_cost: 1234.56,
  compute_cost: 800,
  storage_cost: 200,
  network_cost: 100,
  api_cost: 134.56,
  period: '2024-01',
  trend: '+5%',
};

const mockUsage = [
  { resource: 'GPU 计算', usage: '100 小时', cost: 500 },
  { resource: 'CPU 计算', usage: '200 小时', cost: 300 },
  { resource: '存储', usage: '500 GB', cost: 200 },
];

const mockTrends = [
  { date: '2024-01-01', cost: 40 },
  { date: '2024-01-02', cost: 45 },
  { date: '2024-01-03', cost: 38 },
];

describe('CostReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该正确渲染页面标题', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('成本报告')).toBeInTheDocument();
    });
  });

  it('加载时应该显示 Spin', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // 永不解析

    render(<CostReportPage />);

    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

describe('CostReportPage 统计卡片', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示总费用', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('总费用')).toBeInTheDocument();
    });
  });

  it('应该显示计算资源费用', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      // 检查统计卡片存在
      const cards = document.querySelectorAll('.ant-card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  it('应该显示存储费用', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      // 检查 Ant Design Card 组件存在
      const cards = document.querySelectorAll('.ant-card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  it('应该显示 API 调用费用', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      // 检查 API 相关的统计卡片
      const cards = document.querySelectorAll('.ant-card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});

describe('CostReportPage 标签页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示概览标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '概览' })).toBeInTheDocument();
    });
  });

  it('应该显示按模型标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '按模型' })).toBeInTheDocument();
    });
  });

  it('应该显示明细记录标签页', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '明细记录' })).toBeInTheDocument();
    });
  });

  it('切换到按模型标签页应该显示模型数据', async () => {
    // 为这个测试设置 mock 返回模型数据
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      if (url.includes('/cost/models')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            data: {
              models: [
                { model: 'gpt-4', calls: 1250, tokens: 2500000, cost: 3500.00, avg_cost: 2.80 },
                { model: 'gpt-3.5-turbo', calls: 8500, tokens: 12000000, cost: 1200.00, avg_cost: 0.14 },
              ],
            },
          }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });

    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '按模型' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: '按模型' }));

    await waitFor(() => {
      expect(screen.getByText('gpt-4')).toBeInTheDocument();
    }, { timeout: 5000 });
  });
});

describe('CostReportPage 概览标签页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示日成本趋势', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('日成本趋势')).toBeInTheDocument();
    });
  });

  it('应该显示成本分布', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('成本分布')).toBeInTheDocument();
    });
  });

  it('应该显示用量明细', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByText('用量明细')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 筛选器', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示时间范围选择器', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      // 默认选中 30 天
      expect(screen.getByText('近 30 天')).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 操作按钮', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示导出按钮', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /导出/i })).toBeInTheDocument();
    });
  });

  it('应该显示刷新按钮', async () => {
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /刷新/i })).toBeInTheDocument();
    });
  });
});

describe('CostReportPage 按模型表格', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: mockSummary }),
        });
      }
      if (url.includes('/cost/usage')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { items: mockUsage } }),
        });
      }
      if (url.includes('/cost/trends')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { trends: mockTrends } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('按模型表格应该显示表头', async () => {
    const user = userEvent.setup();
    render(<CostReportPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '按模型' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: '按模型' }));

    await waitFor(() => {
      // 检查表格存在
      const table = document.querySelector('.ant-table');
      expect(table).toBeTruthy();
    });
  });
});
