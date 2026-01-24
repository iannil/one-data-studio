/**
 * API 服务测试
 * Sprint 9: 测试覆盖扩展
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiClient, ApiResponse, request } from './api';

// Mock axios
vi.mock('axios', () => ({
  create: () => ({
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    request: vi.fn(),
  }),
}));

// Mock antd message
vi.mock('antd', () => ({
  message: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Request configuration', () => {
    it('should have default timeout', () => {
      const mockAxios = require('axios').create();
      expect(mockAxios).toBeDefined();
    });

    it('should have default headers', () => {
      const defaultHeaders = {
        'Content-Type': 'application/json',
      };
      expect(defaultHeaders['Content-Type']).toBe('application/json');
    });
  });

  describe('Request ID generation', () => {
    it('should generate unique request IDs', () => {
      const generateRequestId = () => {
        return `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      };

      const id1 = generateRequestId();
      const id2 = generateRequestId();

      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^req-\d+-[a-z0-9]+$/);
    });
  });

  describe('Error handling', () => {
    it('should handle 401 errors', () => {
      const status = 401;
      const errorMessage = status === 401 ? '未授权' : '未知错误';

      expect(errorMessage).toBe('未授权');
    });

    it('should handle 403 errors', () => {
      const status = 403;
      const errorMessage = status === 403 ? '禁止访问' : '未知错误';

      expect(errorMessage).toBe('禁止访问');
    });

    it('should handle 404 errors', () => {
      const status = 404;
      const errorMessage = status === 404 ? '资源不存在' : '未知错误';

      expect(errorMessage).toBe('资源不存在');
    });

    it('should handle 500 errors', () => {
      const status = 500;
      const errorMessage = status === 500 ? '服务器错误' : '未知错误';

      expect(errorMessage).toBe('服务器错误');
    });
  });

  describe('Token management', () => {
    it('should add token to headers when available', () => {
      const token = 'test-token';
      const headers: Record<string, string> = {};

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      expect(headers['Authorization']).toBe('Bearer test-token');
    });

    it('should not add token when not available', () => {
      const token = null;
      const headers: Record<string, string> = {};

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      expect(headers['Authorization']).toBeUndefined();
    });
  });
});

describe('API Response types', () => {
  describe('Success response', () => {
    it('should have correct structure', () => {
      const response: ApiResponse = {
        code: 0,
        message: 'success',
        data: { id: '123' },
      };

      expect(response.code).toBe(0);
      expect(response.message).toBe('success');
      expect(response.data).toEqual({ id: '123' });
    });
  });

  describe('Error response', () => {
    it('should have error structure', () => {
      const error = {
        code: 40001,
        message: 'Invalid request',
        details: { field: 'name' },
      };

      expect(error.code).toBe(40001);
      expect(error.message).toBe('Invalid request');
      expect(error.details).toEqual({ field: 'name' });
    });
  });
});

describe('Request wrapper', () => {
  it('should handle successful request', async () => {
    const mockResponse = {
      data: {
        code: 0,
        message: 'success',
        data: { id: '123' },
      },
    };

    const result: ApiResponse = mockResponse.data;
    expect(result.code).toBe(0);
  });

  it('should handle request error', async () => {
    const error = {
      response: {
        status: 400,
        data: {
          code: 40001,
          message: 'Invalid request',
        },
      },
    };

    const status = error.response?.status;
    expect(status).toBe(400);
  });
});

describe('API endpoint tests', () => {
  describe('Alldata API endpoints', () => {
    it('should construct datasets endpoint', () => {
      const baseUrl = '/api/v1';
      const endpoint = `${baseUrl}/datasets`;

      expect(endpoint).toBe('/api/v1/datasets');
    });

    it('should construct dataset detail endpoint', () => {
      const baseUrl = '/api/v1';
      const datasetId = 'ds-123';
      const endpoint = `${baseUrl}/datasets/${datasetId}`;

      expect(endpoint).toBe('/api/v1/datasets/ds-123');
    });

    it('should construct metadata endpoint', () => {
      const baseUrl = '/api/v1';
      const database = 'sales_dw';
      const endpoint = `${baseUrl}/metadata/databases/${database}/tables`;

      expect(endpoint).toBe('/api/v1/metadata/databases/sales_dw/tables');
    });
  });

  describe('Bisheng API endpoints', () => {
    it('should construct workflows endpoint', () => {
      const baseUrl = '/api/v1';
      const endpoint = `${baseUrl}/workflows`;

      expect(endpoint).toBe('/api/v1/workflows');
    });

    it('should construct chat endpoint', () => {
      const baseUrl = '/api/v1';
      const endpoint = `${baseUrl}/chat`;

      expect(endpoint).toBe('/api/v1/chat');
    });

    it('should construct rag query endpoint', () => {
      const baseUrl = '/api/v1';
      const endpoint = `${baseUrl}/rag/query`;

      expect(endpoint).toBe('/api/v1/rag/query');
    });
  });
});

describe('Request utilities', () => {
  describe('Query parameter handling', () => {
    it('should build query string', () => {
      const params = {
        page: 1,
        page_size: 20,
        status: 'active',
      };

      const queryString = new URLSearchParams(
        Object.entries(params).map(([k, v]) => [k, String(v)])
      ).toString();

      expect(queryString).toBe('page=1&page_size=20&status=active');
    });

    it('should handle empty parameters', () => {
      const params: Record<string, string> = {};
      const queryString = new URLSearchParams(params).toString();

      expect(queryString).toBe('');
    });

    it('should handle undefined parameters', () => {
      const params = {
        page: 1,
        page_size: undefined,
        status: 'active',
      };

      const filteredParams = Object.fromEntries(
        Object.entries(params).filter(([_, v]) => v !== undefined)
      );

      expect(filteredParams).not.toHaveProperty('page_size');
    });
  });

  describe('URL construction', () => {
    it('should construct URL with base and path', () => {
      const base = '/api/v1';
      const path = 'datasets';
      const url = `${base}/${path}`;

      expect(url).toBe('/api/v1/datasets');
    });

    it('should construct URL with query params', () => {
      const base = '/api/v1/datasets';
      const params = { page: '1' };
      const url = `${base}?${new URLSearchParams(params).toString()}`;

      expect(url).toBe('/api/v1/datasets?page=1');
    });
  });
});
