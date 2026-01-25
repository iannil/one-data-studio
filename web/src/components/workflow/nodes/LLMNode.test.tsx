/**
 * LLMNode 组件单元测试
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

import LLMNode from './LLMNode';

describe('LLMNode Component', () => {
  const defaultProps = {
    id: 'llm-1',
    type: 'llm',
    data: {
      label: '文本生成',
      config: {
        model: 'gpt-4o',
        temperature: 0.8,
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render LLM node', () => {
    render(<LLMNode {...defaultProps} />);

    expect(screen.getByText('文本生成')).toBeInTheDocument();
    expect(screen.getByText('LLM')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<LLMNode {...props} />);

    expect(screen.getByText('大模型')).toBeInTheDocument();
  });

  it('should render model name', () => {
    render(<LLMNode {...defaultProps} />);

    expect(screen.getByText('模型: gpt-4o')).toBeInTheDocument();
  });

  it('should render temperature', () => {
    render(<LLMNode {...defaultProps} />);

    expect(screen.getByText('温度: 0.8')).toBeInTheDocument();
  });

  it('should render default model when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'LLM',
        config: {},
      },
    };

    render(<LLMNode {...props} />);

    expect(screen.getByText('模型: gpt-4o-mini')).toBeInTheDocument();
  });

  it('should render default temperature when not configured', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'LLM',
        config: {},
      },
    };

    render(<LLMNode {...props} />);

    expect(screen.getByText('温度: 0.7')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<LLMNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<LLMNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<LLMNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-blue-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<LLMNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-blue-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with blue background', () => {
    const { container } = render(<LLMNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-blue-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without config section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'LLM',
      },
    };

    render(<LLMNode {...props} />);

    expect(screen.queryByText(/模型:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/温度:/)).not.toBeInTheDocument();
  });
});
