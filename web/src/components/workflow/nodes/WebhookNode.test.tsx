/**
 * WebhookNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
const mockMessage = {
  success: vi.fn(),
  error: vi.fn(),
};

vi.mock('antd', () => ({
  Card: ({ children, title, style, bodyStyle }: any) => (
    <div data-testid="card" style={style}>
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-body" style={bodyStyle}>{children}</div>
    </div>
  ),
  Typography: {
    Text: ({ children, type, code, style }: any) => (
      <span data-testid={`text-${type || 'default'}`} data-code={code} style={style}>{children}</span>
    ),
  },
  Space: ({ children, direction, size, style }: any) => (
    <div data-testid="space" data-direction={direction} style={style}>{children}</div>
  ),
  Input: {
    Group: ({ children, compact, style }: any) => (
      <div data-testid="input-group" style={style}>{children}</div>
    ),
  },
  InputNumber: ({ value, min, max, style }: any) => (
    <input data-testid="input-number" type="number" value={value} min={min} max={max} readOnly style={style} />
  ),
  Button: ({ children, onClick, icon, size }: any) => (
    <button data-testid="button" onClick={onClick}>{icon}{children}</button>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" title={title}>{children}</div>
  ),
  message: mockMessage,
}));

import WebhookNode from './WebhookNode';

describe('WebhookNode Component', () => {
  const defaultProps = {
    id: 'webhook-1',
    type: 'webhook',
    data: {
      label: '外部回调',
      webhookId: 'wh-123456',
      webhookUrl: '/api/v1/webhooks/wh-123456',
      timeout: 3600,
      expectedMethod: 'POST' as const,
      secretKey: 'secret-key',
      outputMapping: {},
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('should render webhook node', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('外部回调')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        label: undefined,
      },
    };

    render(<WebhookNode {...props} />);

    expect(screen.getByText('Webhook')).toBeInTheDocument();
  });

  it('should render webhook URL', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('Webhook URL')).toBeInTheDocument();
    expect(screen.getByText('/api/v1/webhooks/wh-123456')).toBeInTheDocument();
  });

  it('should generate URL when webhookUrl not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        webhookUrl: undefined,
      },
    };

    render(<WebhookNode {...props} />);

    expect(screen.getByText('/api/v1/webhooks/wh-123456')).toBeInTheDocument();
  });

  it('should render timeout input', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('等待超时')).toBeInTheDocument();
    const input = screen.getByTestId('input-number');
    expect(input).toHaveValue(3600);
  });

  it('should render expected method', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('预期方法')).toBeInTheDocument();
    expect(screen.getByText('POST')).toBeInTheDocument();
  });

  it('should render copy button', () => {
    render(<WebhookNode {...defaultProps} />);

    const button = screen.getByTestId('button');
    expect(button).toBeInTheDocument();
  });

  it('should copy URL when copy button is clicked', async () => {
    render(<WebhookNode {...defaultProps} />);

    const button = screen.getByTestId('button');
    fireEvent.click(button);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('/api/v1/webhooks/wh-123456');
    expect(mockMessage.success).toHaveBeenCalledWith('Webhook URL 已复制');
  });

  it('should display timeout in hours for large values', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText(/1小时/)).toBeInTheDocument();
  });

  it('should display timeout in minutes for medium values', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        timeout: 300,
      },
    };

    render(<WebhookNode {...props} />);

    expect(screen.getByText(/5分钟/)).toBeInTheDocument();
  });

  it('should display timeout in seconds for small values', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        timeout: 30,
      },
    };

    render(<WebhookNode {...props} />);

    expect(screen.getByText(/30秒/)).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<WebhookNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
  });

  it('should render source handle at bottom', () => {
    render(<WebhookNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
  });

  it('should apply selected styling', () => {
    render(<WebhookNode {...defaultProps} selected={true} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '2px solid #52c41a' });
  });

  it('should apply unselected styling', () => {
    render(<WebhookNode {...defaultProps} selected={false} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '1px solid #d9d9d9' });
  });

  it('should use default timeout when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        timeout: undefined as any,
      },
    };

    render(<WebhookNode {...props} />);

    const input = screen.getByTestId('input-number');
    expect(input).toHaveValue(3600);
  });

  it('should use default method when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        expectedMethod: undefined as any,
      },
    };

    render(<WebhookNode {...props} />);

    expect(screen.getByText('POST')).toBeInTheDocument();
  });
});
