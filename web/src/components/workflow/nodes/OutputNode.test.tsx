/**
 * OutputNode 组件单元测试
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

import OutputNode from './OutputNode';

describe('OutputNode Component', () => {
  const defaultProps = {
    id: 'output-1',
    type: 'output',
    data: {
      label: '最终结果',
      config: {
        output_key: 'response',
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render output node', () => {
    render(<OutputNode {...defaultProps} />);

    expect(screen.getByText('最终结果')).toBeInTheDocument();
    expect(screen.getByText('Output')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<OutputNode {...props} />);

    expect(screen.getByText('输出')).toBeInTheDocument();
  });

  it('should render output key name', () => {
    render(<OutputNode {...defaultProps} />);

    expect(screen.getByText('键名: response')).toBeInTheDocument();
  });

  it('should render default output key when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Output',
        config: {},
      },
    };

    render(<OutputNode {...props} />);

    expect(screen.getByText('键名: result')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<OutputNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should not render source handle', () => {
    render(<OutputNode {...defaultProps} />);

    expect(screen.queryByTestId('handle-source')).not.toBeInTheDocument();
  });

  it('should apply selected styling', () => {
    const { container } = render(<OutputNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-red-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<OutputNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-red-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with red background', () => {
    const { container } = render(<OutputNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-red-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Output',
      },
    };

    render(<OutputNode {...props} />);

    expect(screen.queryByText(/键名:/)).not.toBeInTheDocument();
  });
});
