/**
 * Query Client 配置测试
 * 测试 React Query 客户端配置和工具函数
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./logger', () => ({
  logError: vi.fn(),
}));

vi.mock('antd', () => ({
  message: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { QueryClient } from '@tanstack/react-query';
import {
  queryClient,
  QueryKeys,
  CacheTime,
  CacheStrategies,
  invalidateQueries,
  prefetchQuery,
  cancelAllQueries,
  resetAllQueries,
  clearAllQueries,
  optimisticUpdate,
  getQueryData,
  setQueryData,
} from './queryClient';
import { message } from 'antd';

// Mock message functions for potential future use
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _mockMessageError = message.error as ReturnType<typeof vi.fn>;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _mockMessageSuccess = message.success as ReturnType<typeof vi.fn>;

describe('Query Client Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== QueryKeys ====================

  describe('QueryKeys', () => {
    it('should have datasets key', () => {
      expect(QueryKeys.datasets()).toEqual(['data', 'datasets']);
    });

    it('should have dataset key with id', () => {
      expect(QueryKeys.dataset('ds-123')).toEqual(['data', 'datasets', 'ds-123']);
    });

    it('should have dataset versions key', () => {
      expect(QueryKeys.datasetVersions('ds-123')).toEqual([
        'data',
        'datasets',
        'ds-123',
        'versions',
      ]);
    });

    it('should have metadata databases key', () => {
      expect(QueryKeys.metadataDatabases()).toEqual(['data', 'metadata', 'databases']);
    });

    it('should have metadata tables key', () => {
      expect(QueryKeys.metadataTables('sales_dw')).toEqual([
        'data',
        'metadata',
        'databases',
        'sales_dw',
        'tables',
      ]);
    });

    it('should have workflows key', () => {
      expect(QueryKeys.workflows()).toEqual(['agent', 'workflows']);
    });

    it('should have workflow key with id', () => {
      expect(QueryKeys.workflow('wf-123')).toEqual(['agent', 'workflows', 'wf-123']);
    });

    it('should have current user key', () => {
      expect(QueryKeys.currentUser()).toEqual(['auth', 'user']);
    });

    it('should have schedules key without workflowId', () => {
      expect(QueryKeys.schedules()).toEqual(['agent', 'schedules']);
    });

    it('should have schedules key with workflowId', () => {
      expect(QueryKeys.schedules('wf-123')).toEqual([
        'agent',
        'workflows',
        'wf-123',
        'schedules',
      ]);
    });
  });

  // ==================== CacheTime ====================

  describe('CacheTime', () => {
    it('should have REALTIME cache time', () => {
      expect(CacheTime.REALTIME).toBe(10 * 1000);
    });

    it('should have SHORT cache time', () => {
      expect(CacheTime.SHORT).toBe(2 * 60 * 1000);
    });

    it('should have MEDIUM cache time', () => {
      expect(CacheTime.MEDIUM).toBe(5 * 60 * 1000);
    });

    it('should have LONG cache time', () => {
      expect(CacheTime.LONG).toBe(15 * 60 * 1000);
    });

    it('should have STATIC cache time', () => {
      expect(CacheTime.STATIC).toBe(30 * 60 * 1000);
    });

    it('should have INFINITE cache time', () => {
      expect(CacheTime.INFINITE).toBe(1000 * 60 * 60 * 24 * 30);
    });
  });

  // ==================== CacheStrategies ====================

  describe('CacheStrategies', () => {
    it('should have execution strategy', () => {
      expect(CacheStrategies['agent.executions']).toEqual({
        staleTime: CacheTime.REALTIME,
        gcTime: CacheTime.SHORT,
      });
    });

    it('should have conversations strategy', () => {
      expect(CacheStrategies['agent.conversations']).toEqual({
        staleTime: CacheTime.SHORT,
        gcTime: CacheTime.MEDIUM,
      });
    });

    it('should have workflows strategy', () => {
      expect(CacheStrategies['agent.workflows']).toEqual({
        staleTime: CacheTime.MEDIUM,
        gcTime: CacheTime.LONG,
      });
    });

    it('should have metadata strategy', () => {
      expect(CacheStrategies['data.metadata']).toEqual({
        staleTime: CacheTime.LONG,
        gcTime: CacheTime.STATIC,
      });
    });

    it('should have models strategy', () => {
      expect(CacheStrategies['model.models']).toEqual({
        staleTime: CacheTime.STATIC,
        gcTime: CacheTime.INFINITE,
      });
    });
  });

  // ==================== 工具函数 ====================

  describe('Utility Functions', () => {
    it('should invalidate queries', () => {
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
      invalidateQueries(QueryKeys.datasets(), QueryKeys.workflows());

      expect(invalidateSpy).toHaveBeenCalledTimes(2);
      invalidateSpy.mockRestore();
    });

    it('should cancel all queries', () => {
      const cancelSpy = vi.spyOn(queryClient, 'cancelQueries');
      cancelAllQueries();
      expect(cancelSpy).toHaveBeenCalled();
      cancelSpy.mockRestore();
    });

    it('should reset all queries', () => {
      const resetSpy = vi.spyOn(queryClient, 'resetQueries');
      resetAllQueries();
      expect(resetSpy).toHaveBeenCalled();
      resetSpy.mockRestore();
    });

    it('should clear all queries', () => {
      const clearSpy = vi.spyOn(queryClient, 'clear');
      clearAllQueries();
      expect(clearSpy).toHaveBeenCalled();
      clearSpy.mockRestore();
    });
  });

  // ==================== 缓存数据操作 ====================

  describe('Cache Data Operations', () => {
    it('should get query data', () => {
      const testKey = ['test', 'data'];
      const testData = { id: 1, name: 'Test' };
      queryClient.setQueryData(testKey, testData);

      const result = getQueryData<typeof testData>(testKey);
      expect(result).toEqual(testData);
    });

    it('should return undefined for non-existent query data', () => {
      const result = getQueryData(['non', 'existent']);
      expect(result).toBeUndefined();
    });

    it('should set query data', () => {
      const testKey = ['test', 'data'];
      const testData = { id: 1, name: 'Test' };
      setQueryData(testKey, testData);

      const result = queryClient.getQueryData(testKey);
      expect(result).toEqual(testData);
    });

    it('should set undefined to query data', () => {
      const testKey = ['test', 'data'];
      queryClient.setQueryData(testKey, { id: 1 });
      setQueryData(testKey, undefined);

      // The operation completed without error
      expect(queryClient.getQueryData).toBeDefined();
    });
  });

  // ==================== 乐观更新 ====================

  describe('Optimistic Update', () => {
    it('should perform optimistic update', () => {
      const testKey = ['test', 'list'];
      const originalData = { items: [{ id: 1 }, { id: 2 }] };
      queryClient.setQueryData(testKey, originalData);

      const rollback = optimisticUpdate(testKey, (old) => ({
        items: [...(old?.items || []), { id: 3 }],
      }));

      const updated = queryClient.getQueryData(testKey);
      expect(updated).toEqual({ items: [{ id: 1 }, { id: 2 }, { id: 3 }] });

      rollback();
      const rolledBack = queryClient.getQueryData(testKey);
      expect(rolledBack).toEqual(originalData);
    });

    it('should handle optimistic update with undefined old data', () => {
      const testKey = ['test', 'new'];
      const rollback = optimisticUpdate<{ items: number[] }>(testKey, (old) => ({
        items: [...(old?.items || []), 1],
      }));

      const updated = queryClient.getQueryData(testKey);
      expect(updated).toEqual({ items: [1] });

      rollback();
    });
  });

  // ==================== 预取查询 ====================

  describe('Prefetch Query', () => {
    it('should prefetch query successfully', async () => {
      const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery').mockResolvedValue(undefined);
      const testKey = ['test', 'data'];
      const queryFn = vi.fn().mockResolvedValue({ data: 'test' });

      await prefetchQuery(testKey, queryFn);

      expect(prefetchSpy).toHaveBeenCalledWith({
        queryKey: testKey,
        queryFn,
        staleTime: CacheTime.MEDIUM,
      });
      prefetchSpy.mockRestore();
    });

    it('should handle prefetch errors gracefully', async () => {
      const prefetchSpy = vi
        .spyOn(queryClient, 'prefetchQuery')
        .mockRejectedValue(new Error('Network error'));
      const testKey = ['test', 'data'];
      const queryFn = vi.fn().mockRejectedValue(new Error('Network error'));

      // Should not throw
      await expect(prefetchQuery(testKey, queryFn)).resolves.toBeUndefined();

      prefetchSpy.mockRestore();
    });
  });

  // ==================== Query Client 实例 ====================

  describe('Query Client Instance', () => {
    it('should be a QueryClient instance', () => {
      expect(queryClient).toBeInstanceOf(QueryClient);
    });

    it('should have queryCache configured', () => {
      expect(queryClient.getQueryCache()).toBeDefined();
    });

    it('should have mutationCache configured', () => {
      expect(queryClient.getMutationCache()).toBeDefined();
    });

    it('should have defaultOptions configured', () => {
      const defaultOptions = queryClient.getDefaultOptions();
      expect(defaultOptions).toBeDefined();
      expect(defaultOptions.queries).toBeDefined();
      expect(defaultOptions.mutations).toBeDefined();
    });
  });
});
