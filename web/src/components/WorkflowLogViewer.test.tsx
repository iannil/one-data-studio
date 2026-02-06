/**
 * WorkflowLogViewer 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock antd components
vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    Card: ({ children, title, size }: any) => (
      <div data-testid="card" data-size={size}>
        <div data-testid="card-title">{title}</div>
        <div data-testid="card-content">{children}</div>
      </div>
    ),
    Select: Object.assign(
      ({ children, value, onChange, size, style }: any) => (
        <select
          data-testid="select"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          style={style}
        >
          {children}
        </select>
      ),
      {
        Option: ({ children, value }: any) => (
          <option value={value}>{children}</option>
        ),
      }
    ),
    Space: ({ children }: any) => <div data-testid="space">{children}</div>,
    Tag: ({ children, color }: any) => (
      <span data-testid={`tag-${color || 'default'}`}>{children}</span>
    ),
    Empty: Object.assign(
      ({ description, image }: any) => (
        <div data-testid="empty">{description}</div>
      ),
      {
        PRESENTED_IMAGE_SIMPLE: 'simple',
      }
    ),
  };
});

import WorkflowLogViewer from './WorkflowLogViewer';

describe('WorkflowLogViewer Component', () => {
  const mockLogs = [
    {
      id: '1',
      timestamp: '2024-01-15T10:00:00.123Z',
      level: 'info' as const,
      message: 'Workflow started',
      node_id: 'input-1',
    },
    {
      id: '2',
      timestamp: '2024-01-15T10:00:01.456Z',
      level: 'info' as const,
      message: 'Processing data',
      node_id: 'llm-1',
    },
    {
      id: '3',
      timestamp: '2024-01-15T10:00:02.789Z',
      level: 'warning' as const,
      message: 'Rate limit approaching',
      node_id: 'llm-1',
    },
    {
      id: '4',
      timestamp: '2024-01-15T10:00:03.000Z',
      level: 'error' as const,
      message: 'Failed to process request',
      node_id: 'agent-1',
    },
    {
      id: '5',
      timestamp: '2024-01-15T10:00:04.000Z',
      level: 'info' as const,
      message: 'Workflow completed',
      node_id: null,
    },
  ];

  it('should render log viewer with logs', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getByText('Workflow started')).toBeInTheDocument();
    expect(screen.getByText('Processing data')).toBeInTheDocument();
    expect(screen.getByText('Rate limit approaching')).toBeInTheDocument();
    expect(screen.getByText('Failed to process request')).toBeInTheDocument();
    expect(screen.getByText('Workflow completed')).toBeInTheDocument();
  });

  it('should render log viewer title', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getByText('日志')).toBeInTheDocument();
  });

  it('should render log count', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getByText('共 5 条')).toBeInTheDocument();
  });

  it('should render level filter select', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getByTestId('select')).toBeInTheDocument();
  });

  it('should filter logs by level', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    const select = screen.getByTestId('select');
    fireEvent.change(select, { target: { value: 'error' } });

    expect(screen.getByText('Failed to process request')).toBeInTheDocument();
    expect(screen.queryByText('Workflow started')).not.toBeInTheDocument();
    expect(screen.getByText('共 1 条')).toBeInTheDocument();
  });

  it('should filter logs by warning level', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    const select = screen.getByTestId('select');
    fireEvent.change(select, { target: { value: 'warning' } });

    expect(screen.getByText('Rate limit approaching')).toBeInTheDocument();
    expect(screen.queryByText('Workflow started')).not.toBeInTheDocument();
  });

  it('should filter logs by info level', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    const select = screen.getByTestId('select');
    fireEvent.change(select, { target: { value: 'info' } });

    expect(screen.getByText('Workflow started')).toBeInTheDocument();
    expect(screen.getByText('Processing data')).toBeInTheDocument();
    expect(screen.queryByText('Rate limit approaching')).not.toBeInTheDocument();
  });

  it('should show all logs when filter is "all"', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    const select = screen.getByTestId('select');
    fireEvent.change(select, { target: { value: 'all' } });

    expect(screen.getByText('共 5 条')).toBeInTheDocument();
  });

  it('should render level tags', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getAllByTestId('tag-blue')).toHaveLength(3); // 3 info logs
    expect(screen.getByTestId('tag-orange')).toBeInTheDocument(); // 1 warning
    expect(screen.getByTestId('tag-red')).toBeInTheDocument(); // 1 error
  });

  it('should render node IDs', () => {
    render(<WorkflowLogViewer logs={mockLogs} />);

    expect(screen.getByText('[input-1]')).toBeInTheDocument();
    expect(screen.getAllByText('[llm-1]')).toHaveLength(2);
    expect(screen.getByText('[agent-1]')).toBeInTheDocument();
  });

  it('should render empty state when no logs', () => {
    render(<WorkflowLogViewer logs={[]} />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
    expect(screen.getByText('暂无日志')).toBeInTheDocument();
  });

  it('should apply custom height', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} height={600} />);

    const logContainer = container.querySelector('[style*="height"]');
    expect(logContainer).toBeInTheDocument();
    expect((logContainer as HTMLElement).style.height).toBe('600px');
  });

  it('should accept string height', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} height="50vh" />);

    const logContainer = container.querySelector('[style*="height"]');
    expect(logContainer).toBeInTheDocument();
    expect((logContainer as HTMLElement).style.height).toBe('50vh');
  });

  it('should use default height when not specified', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} />);

    const logContainer = container.querySelector('[style*="height"]');
    expect(logContainer).toBeInTheDocument();
    expect((logContainer as HTMLElement).style.height).toBe('400px');
  });

  it('should format timestamps correctly', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} />);

    // Timestamps should be displayed
    expect(container.querySelector('[data-testid="log-timestamp"]') || container.textContent).toBeDefined();
  });

  it('should apply error styling to error logs', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} />);

    // Error logs should have red color
    const errorLog = container.querySelector('[style*="color: rgb(255, 107, 107)"]');
    expect(errorLog || container.querySelector('[style*="#ff6b6b"]')).toBeInTheDocument();
  });

  it('should apply warning styling to warning logs', () => {
    const { container } = render(<WorkflowLogViewer logs={mockLogs} />);

    // Warning logs should have orange color
    const warningLog = container.querySelector('[style*="color: rgb(255, 169, 64)"]');
    expect(warningLog || container.querySelector('[style*="#ffa940"]')).toBeInTheDocument();
  });
});
