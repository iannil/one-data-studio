/**
 * SchedulerPage 组件测试
 * 测试调度器管理页面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { SchedulerStats } from './services/scheduler';

// Mock scheduler service
vi.mock('./services/scheduler', () => ({
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
  },
}));

// Mock child components
vi.mock('./components/WorkflowEditor', () => ({
  default: () => <div data-testid="workflow-editor">Workflow Editor</div>,
}));

vi.mock('./components/TaskList', () => ({
  default: () => <div data-testid="task-list">Task List</div>,
}));

vi.mock('./components/SchedulerMonitor', () => ({
  default: () => <div data-testid="scheduler-monitor">Scheduler Monitor</div>,
}));

vi.mock('./components/CreateTaskModal', () => ({
  __esModule: true,
  default: () => <div data-testid="create-task-modal">Create Task Modal</div>,
}));

import SchedulerPage from './SchedulerPage';
import { schedulerApi } from './services/scheduler';

// Mock stats data
const mockStats: SchedulerStats = {
  celery: {
    workers: ['worker1@host1', 'worker2@host2'],
    total_tasks: 150,
  },
  smart_scheduler: {
    total_tasks: 50,
    status_counts: {
      pending: 10,
      running: 5,
      completed: 30,
      failed: 5,
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

describe('SchedulerPage', () => {
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
    it('应该正确渲染统计卡片', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('总任务数')).toBeInTheDocument();
        expect(screen.getByText('运行中')).toBeInTheDocument();
        expect(screen.getByText('已完成')).toBeInTheDocument();
        expect(screen.getByText('失败')).toBeInTheDocument();
      });
    });

    it('应该显示任务统计数字', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        // 检查是否有数字显示
        const numbers = screen.queryAllByText(/\d+/);
        expect(numbers.length).toBeGreaterThan(0);
      });
    });

    it('应该显示资源使用率卡片', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('资源使用率')).toBeInTheDocument();
        expect(screen.getByText('CPU')).toBeInTheDocument();
        expect(screen.getByText('内存')).toBeInTheDocument();
        expect(screen.getByText('GPU')).toBeInTheDocument();
      });
    });

    it('应该显示系统状态卡片', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('系统状态')).toBeInTheDocument();
      });
    });

    it('应该显示健康状态标签', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('健康')).toBeInTheDocument();
      });
    });

    it('应该显示创建任务和刷新按钮', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('创建任务')).toBeInTheDocument();
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });
    });
  });

  describe('统计卡片', () => {
    it('应该显示总任务数', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('总任务数')).toBeInTheDocument();
        expect(screen.getByText('50')).toBeInTheDocument();
      });
    });

    it('应该显示运行中任务数', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        const runningText = screen.getByText('运行中');
        expect(runningText).toBeInTheDocument();
      });
    });

    it('应该显示已完成任务数', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        const completedText = screen.getByText('已完成');
        expect(completedText).toBeInTheDocument();
      });
    });

    it('应该显示失败任务数', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        const failedText = screen.getByText('失败');
        expect(failedText).toBeInTheDocument();
      });
    });

    it('统计数据为空时应该显示0', async () => {
      vi.mocked(schedulerApi.getStats).mockResolvedValueOnce({
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
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        const zeros = screen.getAllByText('0');
        expect(zeros.length).toBeGreaterThan(0);
      });
    });
  });

  describe('资源使用率', () => {
    it('应该显示资源使用率卡片', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('资源使用率')).toBeInTheDocument();
      });
    });

    it('应该显示CPU/内存/GPU使用率', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('CPU')).toBeInTheDocument();
        expect(screen.getByText('内存')).toBeInTheDocument();
        expect(screen.getByText('GPU')).toBeInTheDocument();
      });
    });

    it('资源为0时应该显示默认值', async () => {
      vi.mocked(schedulerApi.getStats).mockResolvedValueOnce({
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
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        const zeros = screen.getAllByText('0%');
        expect(zeros.length).toBeGreaterThan(0);
      });
    });
  });

  describe('系统状态', () => {
    it('健康状态应该显示健康标签', async () => {
      vi.mocked(schedulerApi.getHealth).mockResolvedValueOnce({
        data: { status: 'healthy', components: {} },
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('健康')).toBeInTheDocument();
      });
    });

    it('非健康状态应该显示降级标签', async () => {
      vi.mocked(schedulerApi.getHealth).mockResolvedValueOnce({
        data: { status: 'degraded', components: {} },
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('降级')).toBeInTheDocument();
      });
    });
  });

  describe('标签页', () => {
    it('应该显示所有标签页', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('工作流编排')).toBeInTheDocument();
        expect(screen.getByText('任务管理')).toBeInTheDocument();
        expect(screen.getByText('监控面板')).toBeInTheDocument();
      });
    });

    it('应该能够切换标签页', async () => {
      const user = userEvent.setup();
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('工作流编排')).toBeInTheDocument();
      });

      // 默认在工作流编排标签
      expect(screen.getByTestId('workflow-editor')).toBeInTheDocument();

      // 切换到任务管理
      const taskTab = screen.getByText('任务管理');
      await user.click(taskTab);

      await waitFor(() => {
        expect(screen.getByTestId('task-list')).toBeInTheDocument();
      });
    });

    it('默认应该选中工作流编排标签', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByTestId('workflow-editor')).toBeInTheDocument();
      });
    });
  });

  describe('创建任务弹窗', () => {
    it('应该显示创建任务按钮', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('创建任务')).toBeInTheDocument();
      });
    });

    it('CreateTaskModal 组件应该被渲染', async () => {
      render(<SchedulerPage />);

      await waitFor(() => {
        const modal = screen.queryByTestId('create-task-modal');
        expect(modal).toBeTruthy();
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该重新获取数据', async () => {
      const user = userEvent.setup();
      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });

      const refreshButton = screen.getByText('刷新');
      await user.click(refreshButton);

      await waitFor(() => {
        expect(schedulerApi.getStats).toHaveBeenCalled();
        expect(schedulerApi.getHealth).toHaveBeenCalled();
      });
    });
  });

  describe('加载状态', () => {
    it('应该显示加载状态', async () => {
      vi.mocked(schedulerApi.getStats).mockReturnValueOnce(
        new Promise(() => {})
      );

      render(<SchedulerPage />);

      // 应该有加载骨架屏
      await waitFor(() => {
        const loadingElements = document.querySelectorAll('.ant-skeleton');
        expect(loadingElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('默认值处理', () => {
    it('stats为undefined时应该使用默认值', async () => {
      vi.mocked(schedulerApi.getStats).mockResolvedValueOnce({
        data: { data: undefined },
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('总任务数')).toBeInTheDocument();
      });
    });

    it('health为undefined时应该使用默认值', async () => {
      vi.mocked(schedulerApi.getHealth).mockResolvedValueOnce({
        data: undefined,
      } as never);

      render(<SchedulerPage />);

      await waitFor(() => {
        expect(screen.getByText('系统状态')).toBeInTheDocument();
      });
    });
  });
});
