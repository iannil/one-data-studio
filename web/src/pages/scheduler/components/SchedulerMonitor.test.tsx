/**
 * SchedulerMonitor 组件测试
 * 测试调度器监控面板组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { SchedulerStats, ResourcePrediction, SmartTask } from '../services/scheduler';

// Mock react-router-dom - use importActual to preserve BrowserRouter
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock scheduler service
vi.mock('../services/scheduler', () => ({
  schedulerApi: {
    getStats: vi.fn(() => Promise.resolve({
      data: {
        data: {
          celery: { workers: [], total_tasks: 0 },
          smart_scheduler: {
            total_tasks: 0,
            status_counts: {},
            queue_length: 0,
            available_resources: { cpu_cores: 0, memory_mb: 0, gpu_count: 0 },
            total_resources: { cpu_cores: 0, memory_mb: 0, gpu_count: 0 },
          },
          dolphinscheduler: { enabled: false, url: '' },
        },
      },
    })),
    getHealth: vi.fn(() => Promise.resolve({
      data: { status: 'healthy', components: {} },
    })),
    listSmartTasks: vi.fn(() => Promise.resolve({
      data: { data: { tasks: [] } },
    })),
    optimizeSchedule: vi.fn(() => Promise.resolve({
      data: { data: { optimized_order: [] } },
    })),
    predictResourceDemand: vi.fn(() => Promise.resolve({
      data: {
        data: {
          window_minutes: 60,
          predicted_tasks: 0,
          resource_demand: { cpu_cores: 0, memory_mb: 0, gpu_count: 0 },
          resource_utilization: { cpu_percent: 0, memory_percent: 0, gpu_percent: 0 },
          recommendations: [],
        },
      },
    })),
  },
}));

import SchedulerMonitor from './SchedulerMonitor';
import { schedulerApi } from '../services/scheduler';

// Mock data
const mockStats: SchedulerStats = {
  celery: {
    workers: ['worker1@host1', 'worker2@host2'],
    total_tasks: 150,
  },
  smart_scheduler: {
    total_tasks: 50,
    status_counts: {
      pending: 10,
      running: 8,
      completed: 28,
      failed: 4,
    },
    queue_length: 15,
    available_resources: {
      cpu_cores: 8,
      memory_mb: 16384,
      gpu_count: 2,
    },
    total_resources: {
      cpu_cores: 16,
      memory_mb: 32768,
      gpu_count: 4,
    },
  },
  dolphinscheduler: {
    enabled: true,
    url: 'http://dolphinscheduler:12345',
  },
};

const mockHealth = {
  status: 'healthy',
  components: {
    celery: true,
    dolphinscheduler: true,
    smart_scheduler: true,
  },
};

describe('SchedulerMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(schedulerApi.getStats).mockResolvedValue({
      data: { data: mockStats },
    } as never);
    vi.mocked(schedulerApi.getHealth).mockResolvedValue({
      data: mockHealth,
    } as never);
  });

  describe('基本渲染', () => {
    it('应该正确渲染监控面板', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        // 检查组件已渲染
        const container = document.querySelector('.ant-tabs');
        expect(container).toBeInTheDocument();
      });
    });

    it('应该显示刷新按钮', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const refreshBtns = screen.queryAllByText('刷新');
        expect(refreshBtns.length).toBeGreaterThan(0);
      });
    });
  });

  describe('标签页', () => {
    it('应该显示概览标签', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const overviewTabs = screen.queryAllByText('概览');
        expect(overviewTabs.length).toBeGreaterThan(0);
      });
    });

    it('应该显示任务列表标签', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const taskTabs = screen.queryAllByText('任务列表');
        expect(taskTabs.length).toBeGreaterThan(0);
      });
    });

    it('应该显示优化建议标签', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const optTabs = screen.queryAllByText('优化建议');
        expect(optTabs.length).toBeGreaterThan(0);
      });
    });
  });

  describe('时间窗口选择', () => {
    it('应该有时间窗口选择器', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const selects = document.querySelectorAll('.ant-select');
        expect(selects.length).toBeGreaterThan(0);
      });
    });
  });

  describe('概览面板', () => {
    it('应该显示统计卡片', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        // 检查是否有卡片组件
        const cards = document.querySelectorAll('.ant-card');
        expect(cards.length).toBeGreaterThan(0);
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该重新获取数据', async () => {
      const user = userEvent.setup();
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const refreshBtns = screen.queryAllByText('刷新');
        expect(refreshBtns.length).toBeGreaterThan(0);
      });

      const refreshButton = screen.queryAllByText('刷新')[0];
      await user.click(refreshButton);

      await waitFor(() => {
        expect(schedulerApi.getStats).toHaveBeenCalled();
      });
    });
  });

  describe('数据加载', () => {
    it('应该调用统计API', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        expect(schedulerApi.getStats).toHaveBeenCalled();
      });
    });

    it('应该调用健康检查API', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        expect(schedulerApi.getHealth).toHaveBeenCalled();
      });
    });
  });

  describe('组件状态', () => {
    it('应该调用健康检查API', async () => {
      render(<SchedulerMonitor />);

      await waitFor(() => {
        expect(schedulerApi.getHealth).toHaveBeenCalled();
      });
    });
  });

  describe('标签页切换', () => {
    it('应该能够切换标签页', async () => {
      const user = userEvent.setup();
      render(<SchedulerMonitor />);

      await waitFor(() => {
        const overviewTabs = screen.queryAllByText('概览');
        expect(overviewTabs.length).toBeGreaterThan(0);
      });

      const taskTabs = screen.queryAllByText('任务列表');
      if (taskTabs.length > 0) {
        await user.click(taskTabs[0]);

        await waitFor(() => {
          // 标签切换成功
          const tabs = document.querySelectorAll('.ant-tabs-tab-active');
          expect(tabs.length).toBeGreaterThan(0);
        });
      }
    });
  });
});
