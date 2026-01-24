/**
 * ThinkNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

import ThinkNode from './ThinkNode';

describe('ThinkNode Component', () => {
  const defaultProps = {
    id: 'think-1',
    type: 'think',
    data: {
      label: '深度推理',
      config: {
        model: 'gpt-4o',
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render think node', () => {
    render(<ThinkNode {...defaultProps} />);

    expect(screen.getByText('深度推理')).toBeInTheDocument();
    expect(screen.getByText('Think')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<ThinkNode {...props} />);

    expect(screen.getByText('思考')).toBeInTheDocument();
  });

  it('should render model name', () => {
    render(<ThinkNode {...defaultProps} />);

    expect(screen.getByText('模型: gpt-4o')).toBeInTheDocument();
  });

  it('should render default model when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Think',
        config: {},
      },
    };

    render(<ThinkNode {...props} />);

    expect(screen.getByText('模型: gpt-4o-mini')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<ThinkNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<ThinkNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<ThinkNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-yellow-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<ThinkNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-yellow-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with yellow background', () => {
    const { container } = render(<ThinkNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-yellow-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Think',
      },
    };

    render(<ThinkNode {...props} />);

    expect(screen.queryByText(/模型:/)).not.toBeInTheDocument();
  });
});
