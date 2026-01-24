/**
 * SubflowNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

// Mock antd components
vi.mock('antd', () => ({
  Card: ({ children, title, style, bodyStyle }: any) => (
    <div data-testid="card" style={style}>
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-body" style={bodyStyle}>{children}</div>
    </div>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: any) => (
      <span data-testid={`text-${type || 'default'}`} style={style}>{children}</span>
    ),
  },
  Space: ({ children, direction, size, style }: any) => (
    <div data-testid="space" data-direction={direction} style={style}>{children}</div>
  ),
  Select: ({ value, placeholder, options, style }: any) => (
    <select data-testid="select" value={value || ''} style={style} readOnly>
      <option value="">{placeholder}</option>
      {options?.map((opt: any) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  ),
  Switch: ({ checked, size }: any) => (
    <input data-testid="switch" type="checkbox" checked={checked} readOnly />
  ),
  InputNumber: ({ value, min, max, addonAfter, style }: any) => (
    <input
      data-testid="input-number"
      type="number"
      value={value}
      min={min}
      max={max}
      readOnly
      style={style}
    />
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" title={title}>{children}</div>
  ),
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

  it('should render workflow selector', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByTestId('select')).toBeInTheDocument();
    expect(screen.getByText('引用工作流')).toBeInTheDocument();
  });

  it('should display workflow name when workflowId is set', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByText('数据处理流程')).toBeInTheDocument();
  });

  it('should render async mode switch', () => {
    render(<SubflowNode {...defaultProps} />);

    expect(screen.getByTestId('switch')).toBeInTheDocument();
    expect(screen.getByText('异步执行')).toBeInTheDocument();
  });

  it('should render timeout input', () => {
    render(<SubflowNode {...defaultProps} />);

    const timeoutInput = screen.getByTestId('input-number');
    expect(timeoutInput).toHaveValue(600);
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

  it('should apply selected styling', () => {
    render(<SubflowNode {...defaultProps} selected={true} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '2px solid #13c2c2' });
  });

  it('should apply unselected styling', () => {
    render(<SubflowNode {...defaultProps} selected={false} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '1px solid #d9d9d9' });
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

  it('should render async mode as unchecked', () => {
    render(<SubflowNode {...defaultProps} />);

    const switchElement = screen.getByTestId('switch');
    expect(switchElement).not.toBeChecked();
  });

  it('should render async mode as checked when enabled', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        asyncMode: true,
      },
    };

    render(<SubflowNode {...props} />);

    const switchElement = screen.getByTestId('switch');
    expect(switchElement).toBeChecked();
  });
});
