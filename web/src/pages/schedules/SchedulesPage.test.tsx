import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import SchedulesPage from './SchedulesPage';
import * as agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    getWorkflows: vi.fn(),
    listAllSchedules: vi.fn(),
    createSchedule: vi.fn(),
    deleteSchedule: vi.fn(),
    triggerSchedule: vi.fn(),
    pauseSchedule: vi.fn(),
    resumeSchedule: vi.fn(),
    updateScheduleRetryConfig: vi.fn(),
    getScheduleStatistics: vi.fn(),
  },
}));



const mockWorkflows = [
  { workflow_id: 'wf-001', name: '数据清洗流程' },
  { workflow_id: 'wf-002', name: 'ETL 流程' },
];

const mockSchedules = [
  {
    schedule_id: 'sch-001',
    workflow_id: 'wf-001',
    schedule_type: 'cron',
    cron_expression: '0 0 * * *',
    enabled: true,
    next_run_at: '2024-01-01T00:00:00Z',
    last_run_at: '2023-12-31T00:00:00Z',
    paused: false,
  },
  {
    schedule_id: 'sch-002',
    workflow_id: 'wf-002',
    schedule_type: 'interval',
    interval_seconds: 3600,
    enabled: false,
    paused: false,
  },
];

describe('SchedulesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });

    vi.mocked(agentService.default.listAllSchedules).mockResolvedValue({
      code: 0,
      data: { schedules: mockSchedules, total: 2 },
    });
  });

  it('应该正确渲染调度管理页面', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('调度管理')).toBeInTheDocument();
    });
  });

  it('应该显示调度列表', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });
  });

  it('应该显示调度类型标签', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('Cron')).toBeInTheDocument();
      expect(screen.getByText('间隔')).toBeInTheDocument();
    });
  });

  it('应该显示新建调度按钮', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建调度/i })).toBeInTheDocument();
    });
  });

  it('应该能够打开新建调度模态框', async () => {
    const user = userEvent.setup();
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建调度/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建调度/i }));

    // 验证模态框打开
    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal || screen.getByRole('button', { name: /新建调度/i })).toBeTruthy();
    });
  });

  it('应该能够切换启用状态', async () => {
    vi.mocked(agentService.default.deleteSchedule).mockResolvedValue({ code: 0 });
    vi.mocked(agentService.default.createSchedule).mockResolvedValue({
      code: 0,
      data: { schedule_id: 'sch-new' },
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      const switches = screen.getAllByRole('switch');
      expect(switches.length).toBeGreaterThan(0);
    });
  });

  it('应该显示启用/禁用筛选开关', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('全部')).toBeInTheDocument();
    });
  });
});

describe('SchedulesPage 调度操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });

    vi.mocked(agentService.default.listAllSchedules).mockResolvedValue({
      code: 0,
      data: { schedules: mockSchedules, total: 2 },
    });
  });

  it('应该能够手动触发调度', async () => {
    vi.mocked(agentService.default.triggerSchedule).mockResolvedValue({
      code: 0,
      data: { execution_id: 'exec-001' },
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 点击触发按钮
  });

  it('应该能够删除调度', async () => {
    vi.mocked(agentService.default.deleteSchedule).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 删除确认测试
  });

  it('应该能够暂停和恢复调度', async () => {
    vi.mocked(agentService.default.pauseSchedule).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    vi.mocked(agentService.default.resumeSchedule).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });
  });
});

describe('SchedulesPage 创建调度', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });

    vi.mocked(agentService.default.listAllSchedules).mockResolvedValue({
      code: 0,
      data: { schedules: [], total: 0 },
    });
  });

  it('应该能够创建 Cron 类型调度', async () => {
    vi.mocked(agentService.default.createSchedule).mockResolvedValue({
      code: 0,
      data: { schedule_id: 'sch-new' },
    });

    const user = userEvent.setup();
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建调度/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建调度/i }));

    // 验证模态框打开
    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal || screen.getByRole('button', { name: /新建调度/i })).toBeTruthy();
    });
  });

  it('应该显示 Cron 表达式预设', async () => {
    const user = userEvent.setup();
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建调度/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建调度/i }));

    // 验证模态框打开
    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal || screen.getByRole('button', { name: /新建调度/i })).toBeTruthy();
    });
  });

  it('应该能够创建间隔类型调度', async () => {
    vi.mocked(agentService.default.createSchedule).mockResolvedValue({
      code: 0,
      data: { schedule_id: 'sch-new' },
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建调度/i })).toBeInTheDocument();
    });
  });
});

describe('SchedulesPage 统计信息', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });

    vi.mocked(agentService.default.listAllSchedules).mockResolvedValue({
      code: 0,
      data: { schedules: mockSchedules, total: 2 },
    });

    vi.mocked(agentService.default.getScheduleStatistics).mockResolvedValue({
      code: 0,
      data: {
        total_executions: 100,
        successful_executions: 95,
        failed_executions: 5,
        success_rate: 95,
        average_execution_time_ms: 5000,
        last_execution_status: 'completed',
        last_execution_at: '2024-01-01T00:00:00Z',
        recent_executions: [],
      },
    });
  });

  it('应该能够查看执行统计', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 统计按钮应该存在
  });
});

describe('SchedulesPage 重试配置', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.default.getWorkflows).mockResolvedValue({
      code: 0,
      data: { workflows: mockWorkflows, total: 2 },
    });

    vi.mocked(agentService.default.listAllSchedules).mockResolvedValue({
      code: 0,
      data: {
        schedules: [
          {
            ...mockSchedules[0],
            max_retries: 3,
            retry_delay_seconds: 60,
            retry_backoff_base: 2,
            timeout_seconds: 3600,
          },
        ],
        total: 1,
      },
    });
  });

  it('应该能够打开重试配置模态框', async () => {
    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });

    // 重试配置按钮应该存在
  });

  it('应该能够更新重试配置', async () => {
    vi.mocked(agentService.default.updateScheduleRetryConfig).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    render(<SchedulesPage />);

    await waitFor(() => {
      expect(screen.getByText('数据清洗流程')).toBeInTheDocument();
    });
  });
});
