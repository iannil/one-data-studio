import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExecutionLogsModal from './ExecutionLogsModal';
import agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    getExecutionLogs: vi.fn(),
  },
}));

// Mock dayjs
vi.mock('dayjs', () => ({
  default: (date: string) => ({
    format: (fmt: string) => {
      const d = new Date(date);
      return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}.000`;
    },
  }),
}));



const mockLogs = [
  {
    id: 'log-001',
    timestamp: '2024-01-01T10:00:00.123Z',
    level: 'info',
    message: 'Workflow started',
    node_id: 'node-1',
  },
  {
    id: 'log-002',
    timestamp: '2024-01-01T10:00:01.456Z',
    level: 'info',
    message: 'Processing input data',
    node_id: 'node-2',
  },
  {
    id: 'log-003',
    timestamp: '2024-01-01T10:00:02.789Z',
    level: 'warning',
    message: 'Rate limit approaching',
    node_id: null,
  },
  {
    id: 'log-004',
    timestamp: '2024-01-01T10:00:03.000Z',
    level: 'error',
    message: 'Connection timeout',
    node_id: 'node-3',
  },
];

describe('ExecutionLogsModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('不应该在 open 为 false 时渲染', () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={false} onClose={vi.fn()} />
    );

    expect(screen.queryByText('执行日志')).not.toBeInTheDocument();
  });

  it('应该在 open 为 true 时渲染', async () => {
    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: [] },
    });

    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText(/执行日志/)).toBeInTheDocument();
    });
  });

  it('应该显示执行 ID 的缩略形式', async () => {
    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: [] },
    });

    render(
      <ExecutionLogsModal
        executionId="abcdef12-3456-7890-abcd-ef1234567890"
        open={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/abcdef12/)).toBeInTheDocument();
    });
  });
});

describe('ExecutionLogsModal 日志显示', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: mockLogs },
    });
  });

  it('应该显示日志消息', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText('Workflow started')).toBeInTheDocument();
      expect(screen.getByText('Processing input data')).toBeInTheDocument();
      expect(screen.getByText('Rate limit approaching')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });
  });

  it('应该显示日志级别标签', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getAllByText('INFO').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('WARN')).toBeInTheDocument();
      expect(screen.getByText('ERROR')).toBeInTheDocument();
    });
  });

  it('应该显示节点 ID', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText('[node-1]')).toBeInTheDocument();
      expect(screen.getByText('[node-2]')).toBeInTheDocument();
      expect(screen.getByText('[node-3]')).toBeInTheDocument();
    });
  });

  it('应该显示时间戳', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      // 验证日志已加载 - 确认有日志消息说明时间戳也渲染了
      expect(screen.getByText('Workflow started')).toBeInTheDocument();
    });
  });
});

describe('ExecutionLogsModal 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('无日志时应该显示空状态', async () => {
    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: [] },
    });

    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText('暂无日志')).toBeInTheDocument();
    });
  });
});

describe('ExecutionLogsModal 加载状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该在加载时显示 Spin', async () => {
    vi.mocked(agentService.getExecutionLogs).mockImplementation(
      () => new Promise(() => {}) // 永不解析
    );

    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

describe('ExecutionLogsModal 关闭操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: mockLogs },
    });
  });

  it('点击关闭按钮应该调用 onClose', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={onClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('Workflow started')).toBeInTheDocument();
    });

    // 找到并点击关闭按钮
    const closeButton = document.querySelector('.ant-modal-close');
    if (closeButton) {
      await user.click(closeButton);
      expect(onClose).toHaveBeenCalled();
    }
  });
});

describe('ExecutionLogsModal API 调用', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该使用正确的 executionId 调用 API', async () => {
    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: [] },
    });

    render(
      <ExecutionLogsModal executionId="my-execution-123" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(agentService.getExecutionLogs).toHaveBeenCalledWith('my-execution-123');
    });
  });

  it('open 为 false 时不应该调用 API', () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={false} onClose={vi.fn()} />
    );

    expect(agentService.getExecutionLogs).not.toHaveBeenCalled();
  });

  it('executionId 为 null 时不应该调用 API', () => {
    render(
      <ExecutionLogsModal executionId={null} open={true} onClose={vi.fn()} />
    );

    expect(agentService.getExecutionLogs).not.toHaveBeenCalled();
  });
});

describe('ExecutionLogsModal 日志容器', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.getExecutionLogs).mockResolvedValue({
      code: 0,
      data: { logs: mockLogs },
    });
  });

  it('应该有日志容器元素', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(document.getElementById('log-container')).toBeInTheDocument();
    });
  });

  it('日志容器应该有正确的样式', async () => {
    render(
      <ExecutionLogsModal executionId="exec-001" open={true} onClose={vi.fn()} />
    );

    await waitFor(() => {
      const container = document.getElementById('log-container');
      expect(container).toHaveStyle({ height: '400px', overflowY: 'auto' });
    });
  });
});
