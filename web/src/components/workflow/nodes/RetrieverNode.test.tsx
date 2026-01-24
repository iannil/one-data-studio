/**
 * RetrieverNode 组件单元测试
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

import RetrieverNode from './RetrieverNode';

describe('RetrieverNode Component', () => {
  const defaultProps = {
    id: 'retriever-1',
    type: 'retriever',
    data: {
      label: '文档检索',
      config: {
        collection: 'knowledge_base',
        top_k: 10,
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render retriever node', () => {
    render(<RetrieverNode {...defaultProps} />);

    expect(screen.getByText('文档检索')).toBeInTheDocument();
    expect(screen.getByText('Retriever')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<RetrieverNode {...props} />);

    expect(screen.getByText('检索')).toBeInTheDocument();
  });

  it('should render collection name', () => {
    render(<RetrieverNode {...defaultProps} />);

    expect(screen.getByText('集合: knowledge_base')).toBeInTheDocument();
  });

  it('should render top_k value', () => {
    render(<RetrieverNode {...defaultProps} />);

    expect(screen.getByText('Top-K: 10')).toBeInTheDocument();
  });

  it('should render default collection when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Retriever',
        config: {},
      },
    };

    render(<RetrieverNode {...props} />);

    expect(screen.getByText('集合: default')).toBeInTheDocument();
  });

  it('should render default top_k when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Retriever',
        config: {},
      },
    };

    render(<RetrieverNode {...props} />);

    expect(screen.getByText('Top-K: 5')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<RetrieverNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<RetrieverNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<RetrieverNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-teal-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<RetrieverNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-teal-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with teal background', () => {
    const { container } = render(<RetrieverNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-teal-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Retriever',
      },
    };

    render(<RetrieverNode {...props} />);

    expect(screen.queryByText(/集合:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Top-K:/)).not.toBeInTheDocument();
  });
});
