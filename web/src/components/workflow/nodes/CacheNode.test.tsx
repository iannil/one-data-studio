/**
 * CacheNode 组件单元测试
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
  Input: ({ value, placeholder, style }: any) => (
    <input data-testid="input" type="text" value={value || ''} placeholder={placeholder} readOnly style={style} />
  ),
  InputNumber: ({ value, min, style }: any) => (
    <input data-testid="input-number" type="number" value={value} min={min} readOnly style={style} />
  ),
  Select: ({ value, options, style }: any) => (
    <select data-testid="select" value={value || ''} style={style} readOnly>
      {options?.map((opt: any) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  ),
  Tag: ({ children, color, style }: any) => (
    <span data-testid={`tag-${color || 'default'}`} style={style}>{children}</span>
  ),
}));

import CacheNode from './CacheNode';

describe('CacheNode Component', () => {
  const defaultProps = {
    id: 'cache-1',
    type: 'cache',
    data: {
      label: '结果缓存',
      cacheKey: 'user_query_cache',
      ttl: 3600,
      cacheType: 'redis' as const,
      namespace: 'workflow',
      skipIfExists: true,
    },
    position: { x: 0, y: 0 },
    selected: false,
  };

  it('should render cache node', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('结果缓存')).toBeInTheDocument();
  });

  it('should render default label when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        label: undefined,
      },
    };

    render(<CacheNode {...props} />);

    expect(screen.getByText('缓存')).toBeInTheDocument();
  });

  it('should render cache key input', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('缓存键')).toBeInTheDocument();
    const input = screen.getByTestId('input');
    expect(input).toHaveValue('user_query_cache');
  });

  it('should render TTL input', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('过期时间')).toBeInTheDocument();
    const input = screen.getByTestId('input-number');
    expect(input).toHaveValue(3600);
  });

  it('should render cache type selector', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('类型')).toBeInTheDocument();
    const select = screen.getByTestId('select');
    expect(select).toHaveValue('redis');
  });

  it('should display TTL in hours for large values', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('TTL: 1小时')).toBeInTheDocument();
  });

  it('should display TTL in minutes for medium values', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        ttl: 300,
      },
    };

    render(<CacheNode {...props} />);

    expect(screen.getByText('TTL: 5分钟')).toBeInTheDocument();
  });

  it('should display TTL in seconds for small values', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        ttl: 30,
      },
    };

    render(<CacheNode {...props} />);

    expect(screen.getByText('TTL: 30秒')).toBeInTheDocument();
  });

  it('should display Redis tag when cache type is redis', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('Redis')).toBeInTheDocument();
  });

  it('should display memory tag when cache type is memory', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        cacheType: 'memory' as const,
      },
    };

    render(<CacheNode {...props} />);

    expect(screen.getByText('内存')).toBeInTheDocument();
  });

  it('should render target handle at top', () => {
    render(<CacheNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-target');
    expect(handle).toBeInTheDocument();
  });

  it('should render source handle at bottom', () => {
    render(<CacheNode {...defaultProps} />);

    const handle = screen.getByTestId('handle-source');
    expect(handle).toBeInTheDocument();
  });

  it('should apply selected styling', () => {
    render(<CacheNode {...defaultProps} selected={true} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '2px solid #fa8c16' });
  });

  it('should apply unselected styling', () => {
    render(<CacheNode {...defaultProps} selected={false} />);

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ border: '1px solid #d9d9d9' });
  });

  it('should use default TTL when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        ttl: undefined as any,
      },
    };

    render(<CacheNode {...props} />);

    const input = screen.getByTestId('input-number');
    expect(input).toHaveValue(300);
  });
});
