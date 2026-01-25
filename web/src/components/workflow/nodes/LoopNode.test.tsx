/**
 * LoopNode 组件单元测试
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

import LoopNode from './LoopNode';

describe('LoopNode Component', () => {
  const defaultProps = {
    id: 'loop-1',
    type: 'loop',
    data: {
      label: '数据循环',
      config: {
        loop_over: 5,
        max_iterations: 20,
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render loop node', () => {
    render(<LoopNode {...defaultProps} />);

    expect(screen.getByText('数据循环')).toBeInTheDocument();
    expect(screen.getByText('Loop')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<LoopNode {...props} />);

    expect(screen.getByText('循环')).toBeInTheDocument();
  });

  it('should render loop count', () => {
    render(<LoopNode {...defaultProps} />);

    expect(screen.getByText('次数: 5')).toBeInTheDocument();
  });

  it('should render max iterations', () => {
    render(<LoopNode {...defaultProps} />);

    expect(screen.getByText('最大: 20')).toBeInTheDocument();
  });

  it('should render default loop count when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Loop',
        config: {},
      },
    };

    render(<LoopNode {...props} />);

    expect(screen.getByText('次数: 1')).toBeInTheDocument();
  });

  it('should render default max iterations when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Loop',
        config: {},
      },
    };

    render(<LoopNode {...props} />);

    expect(screen.getByText('最大: 10')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<LoopNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<LoopNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<LoopNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-cyan-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<LoopNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-cyan-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with cyan background', () => {
    const { container } = render(<LoopNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-cyan-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Loop',
      },
    };

    render(<LoopNode {...props} />);

    expect(screen.queryByText(/次数:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/最大:/)).not.toBeInTheDocument();
  });
});
