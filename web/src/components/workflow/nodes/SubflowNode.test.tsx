/**
 * SubflowNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock reactflow
vi.mock('reactflow', () => ({
  Handle: ({ type, position, style }: any) => (
    <div data-testid={`handle-${type}`} data-position={position} style={style} />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}));

import SubflowNode from './SubflowNode';

describe('SubflowNode Component', () => {
  const defaultProps = {
    id: 'subflow-1',
    type: 'subflow',
    data: {
      label: '子流程调用',
      workflowId: 'wf-123',
      workflowName: '数据处理流程',
      inputMapping: {},
      outputMapping: {},
      timeout: 600,
      asyncMode: false,
      inheritContext: true,
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render subflow node', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByText('子流程调用')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        label: undefined,
      },
    };

    render(<SubflowNode {...props} />);

    expect(screen.getByText('子工作流')).toBeInTheDocument();
  });

  it('should render workflow reference label', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByText('引用工作流')).toBeInTheDocument();
  });

  it('should display workflow name when workflowId is set', () => {
    render(<SubflowNode {...defaultProps} />);

    const workflowNames = screen.getAllByText('数据处理流程');
    expect(workflowNames.length).toBeGreaterThan(0);
  });

  it('should render async mode label', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByText('异步执行')).toBeInTheDocument();
  });

  it('should render timeout label', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByText('超时')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<SubflowNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
  });

  it('should render source handle at bottom', () => {
    render(<SubflowNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
  });

  it('should not display workflow link when no workflowId', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        workflowId: '',
        workflowName: '',
      },
    };

    render(<SubflowNode {...props} />);

    expect(screen.queryByText('数据处理流程')).not.toBeInTheDocument();
  });

  it('should render Ant Design Card', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(document.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render Select component', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(document.querySelector('.ant-select')).toBeInTheDocument();
  });
});
