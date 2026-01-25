/**
 * ParallelNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock reactflow
vi.mock('reactflow', () => ({
  Handle: ({ type, position, id, style }: any) => (
    <div
      data-testid={`handle-${type}${id ? `-${id}` : ''}`}
      data-position={position}
      style={style}
    />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}));

import ParallelNode from './ParallelNode';

describe('ParallelNode Component', () => {
  const defaultProps = {
    id: 'parallel-1',
    type: 'parallel',
    data: {
      label: '并行处理',
      branches: [
        { id: 'branch_0', name: '分支A' },
        { id: 'branch_1', name: '分支B' },
      ],
      strategy: 'all' as const,
      timeout: 300,
      failFast: false,
      maxConcurrent: 3,
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render parallel node', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText('并行处理')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        label: undefined,
      },
    };

    render(<ParallelNode {...props} />);

    expect(screen.getByText('并行执行')).toBeInTheDocument();
  });

  it('should render strategy label', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText('执行策略')).toBeInTheDocument();
  });

  it('should render branch tags', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText('分支A')).toBeInTheDocument();
    expect(screen.getByText('分支B')).toBeInTheDocument();
  });

  it('should render add branch button', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText(/添加分支/)).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<ParallelNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
  });

  it('should render source handles for each branch', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByTestId('handle-source-branch-0')).toBeInTheDocument();
    expect(screen.getByTestId('handle-source-branch-1')).toBeInTheDocument();
  });

  it('should render branch count', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText('分支 (2)')).toBeInTheDocument();
  });

  it('should render empty branches', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        branches: [],
      },
    };

    render(<ParallelNode {...props} />);

    expect(screen.getByText('分支 (0)')).toBeInTheDocument();
  });

  it('should render Ant Design Card', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(document.querySelector('.ant-card')).toBeInTheDocument();
  });
});
