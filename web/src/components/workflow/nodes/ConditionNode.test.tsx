/**
 * ConditionNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock reactflow
vi.mock('reactflow', () => ({
  Handle: ({ type, position, className, id, style }: any) => (
    <div
      data-testid={`handle-${type}${id ? `-${id}` : ''}`}
      data-position={position}
      className={className}
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

import ConditionNode from './ConditionNode';

describe('ConditionNode Component', () => {
  const defaultProps = {
    id: 'condition-1',
    type: 'condition',
    data: {
      label: '判断条件',
      config: {
        condition: 'score > 80',
      },
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render condition node', () => {
    render(<ConditionNode {...defaultProps} />);

    expect(screen.getByText('判断条件')).toBeInTheDocument();
    expect(screen.getByText('Condition')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: { config: {} },
    };

    render(<ConditionNode {...props} />);

    expect(screen.getByText('条件')).toBeInTheDocument();
  });

  it('should render condition expression', () => {
    render(<ConditionNode {...defaultProps} />);

    expect(screen.getByText('score > 80')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<ConditionNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
    expect(handle).toHaveAttribute('data-position', 'top');
  });

  it('should render true branch source handle', () => {
    render(<ConditionNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source-true');
    expect(handle).toBeInTheDocument();
  });

  it('should render false branch source handle', () => {
    render(<ConditionNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source-false');
    expect(handle).toBeInTheDocument();
  });

  it('should render True and False labels', () => {
    render(<ConditionNode {...defaultProps} />);

    expect(screen.getByText('True')).toBeInTheDocument();
    expect(screen.getByText('False')).toBeInTheDocument();
  });

  it('should apply selected styling', () => {
    const { container } = render(<ConditionNode {...defaultProps} selected={true} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-amber-500');
    expect(node).toHaveClass('shadow-lg');
  });

  it('should apply unselected styling', () => {
    const { container } = render(<ConditionNode {...defaultProps} selected={false} />);

    const node = container.firstChild;
    expect(node).toHaveClass('border-amber-300');
    expect(node).not.toHaveClass('shadow-lg');
  });

  it('should render icon container with amber background', () => {
    const { container } = render(<ConditionNode {...defaultProps} />);

    const iconContainer = container.querySelector('.bg-amber-100');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render without condition section when no condition', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Condition',
        config: {},
      },
    };

    render(<ConditionNode {...props} />);

    expect(screen.queryByText('score > 80')).not.toBeInTheDocument();
  });

  it('should truncate long condition expressions', () => {
    const props = {
      ...defaultProps,
      data: {
        label: 'Condition',
        config: {
          condition: 'this_is_a_very_long_condition_expression_that_should_be_truncated_in_the_ui',
        },
      },
    };

    const { container } = render(<ConditionNode {...props} />);

    const conditionDiv = container.querySelector('.truncate');
    expect(conditionDiv).toBeInTheDocument();
  });

  it('should have title attribute for tooltip on condition', () => {
    render(<ConditionNode {...defaultProps} />);

    const conditionElement = screen.getByText('score > 80');
    expect(conditionElement).toHaveAttribute('title', 'score > 80');
  });
});
