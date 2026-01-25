/**
 * WebhookNode 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test/testUtils';
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

  it('should render webhook URL label', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('Webhook URL')).toBeInTheDocument();
  });

  it('should display webhook URL in input', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByDisplayValue('/api/v1/webhooks/wh-123456')).toBeInTheDocument();
  });

  it('should render timeout label', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('等待超时')).toBeInTheDocument();
  });

  it('should render expected method label', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('预期方法')).toBeInTheDocument();
  });

  it('should display POST method', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(screen.getByText('POST')).toBeInTheDocument();
  });

  it('should display timeout info', () => {
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

  it('should render Ant Design Card', () => {
    render(<WebhookNode {...defaultProps} />);

    expect(document.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render copy button', () => {
    render(<WebhookNode {...defaultProps} />);

    // Should have a button for copying
    const buttons = document.querySelectorAll('.ant-btn');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
