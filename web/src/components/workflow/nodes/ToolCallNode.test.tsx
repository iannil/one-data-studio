/**
 * ToolCallNode 组件单元测试
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

import ToolCallNode from './ToolCallNode';

describe('ToolCallNode Component', () => {
  const defaultProps = {
    id: 'tool-1',
    type: 'tool_call',
    data: {
      label: 'HTTP 请求',
      config: {
        tool_name: 'http_request',
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render tool call node', () => {
    render(<ToolCallNode {...defaultProps} />);

    expect(screen.getByText('HTTP 请求')).toBeInTheDocument();
    expect(screen.getByText('Tool Call')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<ToolCallNode {...props} />);

    expect(screen.getByText('工具调用')).toBeInTheDocument();
  });

  it('should render tool name', () => {
    render(<ToolCallNode {...defaultProps} />);

    expect(screen.getByText('http_request')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<ToolCallNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render source handle at bottom', () => {
    render(<ToolCallNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'bottom');
  });

  it('should apply selected styling', () => {
    const { container } = render(<ToolCallNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-indigo-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<ToolCallNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-indigo-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with indigo background', () => {
    const { container } = render(<ToolCallNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-indigo-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without tool name section when no config', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Tool Call',
        config: {},
      },
    };

    render(<ToolCallNode {...props} />);

    // The tool name section should not be rendered when tool_name is not set
    expect(screen.queryByText('http_request')).not.toBeInTheDocument();
  });

  it('should truncate long tool names', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Tool Call',
        config: {
          tool_name: 'this_is_a_very_long_tool_name_that_should_be_truncated',
        },
      },
    };

    const { container } = render(<ToolCallNode {...props} />);

    const toolNameDiv = container.querySelector('.truncate');
    expect(toolNameDiv).toBeInTheDocument();
  });

  it('should have title attribute for tooltip on tool name', () => {
    render(<ToolCallNode {...defaultProps} />);

    const toolNameElement = screen.getByText('http_request');
    expect(toolNameElement).toHaveAttribute('title', 'http_request');
  });
});
