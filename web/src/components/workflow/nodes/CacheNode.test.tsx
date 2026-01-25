/**
 * CacheNode 组件单元测试
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

  it('should render cache key label', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('缓存键')).toBeInTheDocument();
  });

  it('should render TTL label', () => {
    render(<CacheNode {...defaultProps} />);

    expect(screen.getByText('过期时间')).toBeInTheDocument();
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

    // Find the Redis tag (may appear in multiple places)
    const redisTags = screen.getAllByText('Redis');
    expect(redisTags.length).toBeGreaterThan(0);
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

    // Find the memory tag in the ant-tag element
    const memoryTags = screen.getAllByText('内存');
    expect(memoryTags.length).toBeGreaterThan(0);
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

  it('should render Ant Design Card', () => {
    render(<CacheNode {...defaultProps} />);

    // The card should contain the label
    expect(document.querySelector('.ant-card')).toBeInTheDocument();
  });
});
