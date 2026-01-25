/**
 * RetryNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock reactflow
vi.mock('reactflow', () => ({
  Handle: ({ type, position, style }: any) => (
    <div data-testid={`handle-${type}`} data-position={position} style={style} />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}));

import RetryNode from './RetryNode';

describe('RetryNode Component', () => {
  const defaultProps = {
    id: 'retry-1',
    type: 'retry',
    data: {
      label: '重试策略',
      maxRetries: 5,
      initialDelay: 2,
      maxDelay: 60,
      exponentialBase: 2,
      jitter: true,
      retryOnExceptions: ['TimeoutError', 'ConnectionError'],
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render retry node', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('重试策略')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        label: undefined,
      },
    };

    render(<RetryNode {...props} />);

    expect(screen.getByText('重试')).toBeInTheDocument();
  });

  it('should render max retries label', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('最大重试')).toBeInTheDocument();
  });

  it('should render initial delay label', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('初始延迟')).toBeInTheDocument();
  });

  it('should render exponential base label', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('退避基数')).toBeInTheDocument();
  });

  it('should render jitter label', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('随机抖动')).toBeInTheDocument();
  });

  it('should render delay progression info', () => {
    render(<RetryNode {...defaultProps} />);

    // Should display the delay progression
    expect(screen.getByText(/延迟:/)).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<RetryNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
  });

  it('should render source handle at bottom', () => {
    render(<RetryNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
  });

  it('should render Ant Design Card', () => {
    render(<RetryNode {...defaultProps} />);

    expect(document.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render InputNumber components', () => {
    render(<RetryNode {...defaultProps} />);

    // InputNumber components should be present
    const inputs = document.querySelectorAll('.ant-input-number');
    expect(inputs.length).toBeGreaterThan(0);
  });
});
