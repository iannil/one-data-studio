/**
 * RetryNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

// Mock antd components
vi.mock('antd', () => ({
  Card: ({ children, title, style, bodyStyle }: any) => (
    <div data-testid="card" style={style}>
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-body" style={bodyStyle}>{children}</div>
    </div>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: any) => (
      <span data-testid={`text-${type || 'default'}`} style={style}>{children}</span>
    ),
  },
  Space: ({ children, direction, size, style }: any) => (
    <div data-testid="space" data-direction={direction} style={style}>{children}</div>
  ),
  InputNumber: ({ value, min, max, step, addonAfter, style }: any) => (
    <input
      data-testid="input-number"
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      readOnly
      style={style}
    />
  ),
  Switch: ({ checked, size }: any) => (
    <input data-testid="switch" type="checkbox" checked={checked} readOnly />
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" title={title}>{children}</div>
  ),
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

  it('should render max retries input', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('最大重试')).toBeInTheDocument();
    const inputs = screen.getAllByTestId('input-number');
    expect(inputs[0]).toHaveValue(5);
  });

  it('should render initial delay input', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('初始延迟')).toBeInTheDocument();
    const inputs = screen.getAllByTestId('input-number');
    expect(inputs[1]).toHaveValue(2);
  });

  it('should render exponential base input', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('退避基数')).toBeInTheDocument();
    const inputs = screen.getAllByTestId('input-number');
    expect(inputs[2]).toHaveValue(2);
  });

  it('should render jitter switch', () => {
    render(<RetryNode {...defaultProps} />);

    expect(screen.getByText('随机抖动')).toBeInTheDocument();
    const switchElement = screen.getByTestId('switch');
    expect(switchElement).toBeInTheDocument();
  });

  it('should show jitter as checked when enabled', () => {
    render(<RetryNode {...defaultProps} />);

    const switchElement = screen.getByTestId('switch');
    expect(switchElement).toBeChecked();
  });

  it('should show jitter as unchecked when disabled', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        jitter: false,
      },
    };

    render(<RetryNode {...props} />);

    const switchElement = screen.getByTestId('switch');
    expect(switchElement).not.toBeChecked();
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

  it('should apply selected styling', () => {
    render(<RetryNode {...defaultProps} selected={true} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '2px solid #eb2f96' });
  });

  it('should apply unselected styling', () => {
    render(<RetryNode {...defaultProps} selected={false} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '1px solid #d9d9d9' });
  });

  it('should use default max retries when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        maxRetries: undefined as any,
      },
    };

    render(<RetryNode {...props} />);

    const inputs = screen.getAllByTestId('input-number');
    expect(inputs[0]).toHaveValue(3);
  });

  it('should use default initial delay when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        initialDelay: undefined as any,
      },
    };

    render(<RetryNode {...props} />);

    const inputs = screen.getAllByTestId('input-number');
    expect(inputs[1]).toHaveValue(1);
  });
});
