/**
 * AgentNode 组件单元测试
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

import AgentNode from './AgentNode';

describe('AgentNode Component', () => {
  const defaultProps = {
    id: 'agent-1',
    type: 'agent',
    data: {
      label: '智能助手',
      config: {
        agent_type: 'react',
        model: 'gpt-4o',
        max_iterations: 15,
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render agent node', () => {
    render(<AgentNode {...defaultProps} />);

    expect(screen.getByText('智能助手')).toBeInTheDocument();
    expect(screen.getByText('ReAct Agent')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<AgentNode {...props} />);

    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('should render agent type', () => {
    render(<AgentNode {...defaultProps} />);

    expect(screen.getByText('类型: react')).toBeInTheDocument();
  });

  it('should render model name', () => {
    render(<AgentNode {...defaultProps} />);

    expect(screen.getByText('模型: gpt-4o')).toBeInTheDocument();
  });

  it('should render max iterations', () => {
    render(<AgentNode {...defaultProps} />);

    expect(screen.getByText('迭代: 15次')).toBeInTheDocument();
  });

  it('should render default agent type when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Agent',
        config: {},
      },
    };

    render(<AgentNode {...props} />);

    expect(screen.getByText('类型: react')).toBeInTheDocument();
  });

  it('should render default model when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Agent',
        config: {},
      },
    };

    render(<AgentNode {...props} />);

    expect(screen.getByText('模型: gpt-4o-mini')).toBeInTheDocument();
  });

  it('should render default max iterations when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Agent',
        config: {},
      },
    };

    render(<AgentNode {...props} />);

    expect(screen.getByText('迭代: 10次')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<AgentNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<AgentNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<AgentNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-purple-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<AgentNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-purple-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with purple background', () => {
    const { container } = render(<AgentNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-purple-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Agent',
      },
    };

    render(<AgentNode {...props} />);

    expect(screen.queryByText(/类型:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/模型:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/迭代:/)).not.toBeInTheDocument();
  });
});
