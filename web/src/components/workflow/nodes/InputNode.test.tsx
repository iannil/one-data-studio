/**
 * InputNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock reactflow
vi.mock('reactflow', () => ({
  Handle: ({ type, position, className }: any) => (
    <div data-testid={`handle-${type}`} data-position={position} className={className} />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}));

import InputNode from './InputNode';

describe('InputNode Component', () => {
  const defaultProps = {
    id: 'input-1',
    type: 'input',
    data: {
      label: '用户输入',
      config: {
        key: 'user_query',
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render input node', () => {
    render(<InputNode {...defaultProps} />);

    expect(screen.getByText('用户输入')).toBeInTheDocument();
    expect(screen.getByText('Input')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<InputNode {...props} />);

    expect(screen.getByText('输入')).toBeInTheDocument();
  });

  it('should render config key name', () => {
    render(<InputNode {...defaultProps} />);

    expect(screen.getByText('键名: user_query')).toBeInTheDocument();
  });

  it('should render default key when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Input',
        config: {},
      },
    };

    render(<InputNode {...props} />);

    expect(screen.getByText('键名: input')).toBeInTheDocument();
  });

  it('should render source handle at bottom', () => {
    render(<InputNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should not render target handle', () => {
    render(<InputNode {...defaultProps} />);

    expect(screen.queryByTestId('handle-target')).not.toBeInTheDocument();
  });

  it('should apply selected styling', () => {
    const { container } = render(<InputNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-emerald-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<InputNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-emerald-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container', () => {
    const { container } = render(<InputNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-emerald-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Input',
      },
    };

    render(<InputNode {...props} />);

    expect(screen.queryByText(/键名:/)).not.toBeInTheDocument();
  });
});
