import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import StepsViewer from './StepsViewer';

const mockSteps = [
  {
    type: 'thought' as const,
    content: '我需要计算这个数学表达式',
    timestamp: '2024-01-01T10:00:00Z',
  },
  {
    type: 'action' as const,
    content: '使用计算器工具',
    timestamp: '2024-01-01T10:00:01Z',
    tool_output: '42',
  },
  {
    type: 'observation' as const,
    content: '计算结果是 42',
    timestamp: '2024-01-01T10:00:02Z',
  },
  {
    type: 'final' as const,
    content: '答案是 42',
    timestamp: '2024-01-01T10:00:03Z',
  },
];

describe('StepsViewer', () => {
  it('应该正确渲染执行步骤', () => {
    render(<StepsViewer steps={mockSteps} />);

    expect(screen.getByText('我需要计算这个数学表达式')).toBeInTheDocument();
    expect(screen.getByText('使用计算器工具')).toBeInTheDocument();
    expect(screen.getByText('计算结果是 42')).toBeInTheDocument();
    expect(screen.getByText('答案是 42')).toBeInTheDocument();
  });

  it('应该显示步骤类型标签', () => {
    render(<StepsViewer steps={mockSteps} />);

    expect(screen.getByText('思考')).toBeInTheDocument();
    expect(screen.getByText('行动')).toBeInTheDocument();
    expect(screen.getByText('观察')).toBeInTheDocument();
    expect(screen.getByText('最终')).toBeInTheDocument();
  });

  it('应该显示工具输出', () => {
    render(<StepsViewer steps={mockSteps} />);

    expect(screen.getByText('工具输出:')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('应该显示时间戳', () => {
    render(<StepsViewer steps={mockSteps} />);

    // 时间会被格式化为本地时间
    const timeElements = screen.getAllByText(/\d+:\d+:\d+/);
    expect(timeElements.length).toBeGreaterThan(0);
  });
});

describe('StepsViewer 加载状态', () => {
  it('应该显示加载中提示', () => {
    render(<StepsViewer steps={[]} loading={true} />);

    expect(screen.getByText('Agent 运行中...')).toBeInTheDocument();
  });
});

describe('StepsViewer 空状态', () => {
  it('应该显示无步骤提示', () => {
    render(<StepsViewer steps={[]} loading={false} />);

    expect(screen.getByText('暂无执行步骤')).toBeInTheDocument();
  });
});

describe('StepsViewer 错误步骤', () => {
  it('应该正确显示错误步骤', () => {
    const errorSteps = [
      {
        type: 'error' as const,
        content: '执行失败：API 调用超时',
        timestamp: '2024-01-01T10:00:00Z',
      },
    ];

    render(<StepsViewer steps={errorSteps} />);

    expect(screen.getByText('错误')).toBeInTheDocument();
    expect(screen.getByText('执行失败：API 调用超时')).toBeInTheDocument();
  });
});

describe('StepsViewer 计划步骤', () => {
  it('应该正确显示计划步骤', () => {
    const planSteps = [
      {
        type: 'plan' as const,
        content: '1. 首先获取数据\n2. 然后进行处理\n3. 最后返回结果',
        timestamp: '2024-01-01T10:00:00Z',
      },
    ];

    render(<StepsViewer steps={planSteps} />);

    expect(screen.getByText('计划')).toBeInTheDocument();
    expect(screen.getByText(/首先获取数据/)).toBeInTheDocument();
  });
});

describe('StepsViewer 工具输出格式', () => {
  it('应该正确显示字符串工具输出', () => {
    const steps = [
      {
        type: 'action' as const,
        content: '调用搜索工具',
        timestamp: '2024-01-01T10:00:00Z',
        tool_output: '搜索结果：找到 10 条记录',
      },
    ];

    render(<StepsViewer steps={steps} />);

    expect(screen.getByText('搜索结果：找到 10 条记录')).toBeInTheDocument();
  });

  it('应该正确显示对象工具输出', () => {
    const steps = [
      {
        type: 'action' as const,
        content: '调用 API',
        timestamp: '2024-01-01T10:00:00Z',
        tool_output: { status: 'success', data: { count: 10 } },
      },
    ];

    render(<StepsViewer steps={steps} />);

    // JSON 字符串化后的输出
    expect(screen.getByText(/"status": "success"/)).toBeInTheDocument();
  });
});
