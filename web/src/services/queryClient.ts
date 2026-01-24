/**
 * React Query 配置
 * Sprint 8: 性能优化 - 高级缓存策略配置
 *
 * 提供统一的查询缓存配置、请求去重、乐观更新和智能失效支持
 *
 * 优化特性:
 * 1. 分层缓存策略 - 根据数据变化频率设置不同的 staleTime
 * 2. 智能失效 - mutation 后自动失效相关查询
 * 3. 后台刷新 - 数据过期后在后台静默刷新
 * 4. 错误恢复 - 自动重试和错误边界
 */

import { QueryClient, MutationCache, QueryCache, Query } from '@tanstack/react-query';
import { message } from 'antd';
import { logError } from './logger';

/**
 * 查询缓存键定义
 * 集中管理所有查询键，便于缓存失效和刷新
 */
export const QueryKeys = {
  // Alldata API
  datasets: () => ['alldata', 'datasets'] as const,
  dataset: (id: string) => ['alldata', 'datasets', id] as const,
  datasetVersions: (id: string) => ['alldata', 'datasets', id, 'versions'] as const,
  metadataDatabases: () => ['alldata', 'metadata', 'databases'] as const,
  metadataTables: (db: string) => ['alldata', 'metadata', 'databases', db, 'tables'] as const,
  metadataColumns: (db: string, table: string) =>
    ['alldata', 'metadata', 'databases', db, 'tables', table, 'columns'] as const,

  // Bisheng API
  workflows: () => ['bisheng', 'workflows'] as const,
  workflow: (id: string) => ['bisheng', 'workflows', id] as const,
  workflowExecutions: (id: string) => ['bisheng', 'workflows', id, 'executions'] as const,
  executions: () => ['bisheng', 'executions'] as const,
  executionLogs: (id: string) => ['bisheng', 'executions', id, 'logs'] as const,
  conversations: () => ['bisheng', 'conversations'] as const,
  conversation: (id: string) => ['bisheng', 'conversations', id] as const,
  messages: (conversationId: string) => ['bisheng', 'conversations', conversationId, 'messages'] as const,
  documents: () => ['bisheng', 'documents'] as const,
  document: (id: string) => ['bisheng', 'documents', id] as const,
  collections: () => ['bisheng', 'collections'] as const,
  agentTemplates: () => ['bisheng', 'agent', 'templates'] as const,
  agentTemplate: (id: string) => ['bisheng', 'agent', 'templates', id] as const,
  tools: () => ['bisheng', 'tools'] as const,
  schedules: (workflowId?: string) =>
    workflowId
      ? (['bisheng', 'workflows', workflowId, 'schedules'] as const)
      : (['bisheng', 'schedules'] as const),
  scheduleStats: (scheduleId: string) => ['bisheng', 'schedules', scheduleId, 'statistics'] as const,

  // Cube API
  models: () => ['cube', 'models'] as const,

  // 用户相关
  currentUser: () => ['auth', 'user'] as const,
  permissions: () => ['auth', 'permissions'] as const,
} as const;

/**
 * 缓存时间配置（毫秒）
 * 基于数据变化频率的分层策略
 */
export const CacheTime = {
  /** 即时数据 - 执行状态等实时数据 */
  REALTIME: 10 * 1000, // 10 秒
  /** 短期缓存 - 频繁变化的数据（如聊天消息） */
  SHORT: 2 * 60 * 1000, // 2 分钟
  /** 中期缓存 - 偶尔变化的数据（如工作流列表） */
  MEDIUM: 5 * 60 * 1000, // 5 分钟
  /** 长期缓存 - 很少变化的数据（如元数据） */
  LONG: 15 * 60 * 1000, // 15 分钟
  /** 静态缓存 - 极少变化的数据（如模型列表、权限） */
  STATIC: 30 * 60 * 1000, // 30 分钟
  /** 永久缓存 - 静态数据 */
  INFINITE: 1000 * 60 * 60 * 24 * 30, // 30 天
};

/**
 * 按查询类型配置的缓存策略
 */
const CacheStrategies: Record<string, { staleTime: number; gcTime: number }> = {
  // 实时数据 - 需要频繁更新
  'bisheng.executions': { staleTime: CacheTime.REALTIME, gcTime: CacheTime.SHORT },

  // 聊天相关 - 较短缓存
  'bisheng.conversations': { staleTime: CacheTime.SHORT, gcTime: CacheTime.MEDIUM },

  // 工作流和文档 - 中期缓存
  'bisheng.workflows': { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG },
  'bisheng.documents': { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG },
  'alldata.datasets': { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG },

  // 元数据 - 长期缓存
  'alldata.metadata': { staleTime: CacheTime.LONG, gcTime: CacheTime.STATIC },

  // 静态数据 - 很少变化
  'cube.models': { staleTime: CacheTime.STATIC, gcTime: CacheTime.INFINITE },
  'auth.permissions': { staleTime: CacheTime.STATIC, gcTime: CacheTime.INFINITE },
  'bisheng.tools': { staleTime: CacheTime.STATIC, gcTime: CacheTime.INFINITE },
};

/**
 * 根据查询键获取缓存策略
 */
function getCacheStrategyForKey(queryKey: readonly unknown[]): { staleTime: number; gcTime: number } {
  if (!queryKey || queryKey.length === 0) {
    return { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG };
  }

  const prefix = queryKey.slice(0, 2).join('.');

  // 精确匹配策略
  if (CacheStrategies[prefix]) {
    return CacheStrategies[prefix];
  }

  // 按顶层分类匹配
  const topLevel = queryKey[0] as string;
  switch (topLevel) {
    case 'cube':
      return { staleTime: CacheTime.STATIC, gcTime: CacheTime.INFINITE };
    case 'auth':
      return { staleTime: CacheTime.STATIC, gcTime: CacheTime.INFINITE };
    case 'alldata':
      return { staleTime: CacheTime.LONG, gcTime: CacheTime.STATIC };
    case 'bisheng':
      return { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG };
    default:
      return { staleTime: CacheTime.MEDIUM, gcTime: CacheTime.LONG };
  }
}

/**
 * 创建查询缓存实例
 */
function createQueryCache() {
  return new QueryCache({
    onError: (error, query) => {
      // Global query error handling - avoid logging sensitive data
      const sanitizedKey = Array.isArray(query.queryKey)
        ? query.queryKey.slice(0, 2).join('/')
        : 'unknown';
      logError(`Query error for [${sanitizedKey}]`, 'QueryCache', error instanceof Error ? error.message : 'Unknown error');

      // 只对非静默查询显示错误消息
      if (query.meta?.errorMessage !== false) {
        const errorMessage = (error as Error)?.message || '加载数据失败';
        message.error(errorMessage);
      }
    },
    onSuccess: (_data, _query) => {
      // Success logging removed - use network tab for debugging
    },
  });
}

/**
 * Mutation 到 Query 的失效映射
 * 定义 mutation 成功后应该失效的相关查询
 */
const MutationInvalidationMap: Record<string, readonly unknown[][]> = {
  // 数据集操作 -> 失效数据集列表
  'dataset.create': [QueryKeys.datasets()],
  'dataset.update': [QueryKeys.datasets()],
  'dataset.delete': [QueryKeys.datasets()],

  // 工作流操作 -> 失效工作流列表
  'workflow.create': [QueryKeys.workflows()],
  'workflow.update': [QueryKeys.workflows()],
  'workflow.delete': [QueryKeys.workflows()],

  // 文档操作 -> 失效文档和集合列表
  'document.upload': [QueryKeys.documents(), QueryKeys.collections()],
  'document.delete': [QueryKeys.documents(), QueryKeys.collections()],

  // 会话操作 -> 失效会话列表
  'conversation.create': [QueryKeys.conversations()],
  'conversation.delete': [QueryKeys.conversations()],

  // 调度操作 -> 失效调度列表
  'schedule.create': [QueryKeys.schedules()],
  'schedule.delete': [QueryKeys.schedules()],
  'schedule.update': [QueryKeys.schedules()],

  // 模板操作 -> 失效模板列表
  'template.create': [QueryKeys.agentTemplates()],
  'template.delete': [QueryKeys.agentTemplates()],
  'template.update': [QueryKeys.agentTemplates()],
};

/**
 * 创建变更缓存实例
 */
function createMutationCache() {
  return new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // Global mutation error handling - avoid logging sensitive variables
      const mutationKey = mutation.options.mutationKey?.[0] || 'unknown';
      logError(`Mutation error for [${mutationKey}]`, 'MutationCache', error instanceof Error ? error.message : 'Unknown error');

      if (mutation.meta?.errorMessage !== false) {
        const errorMessage = (error as Error)?.message || '操作失败';
        message.error(errorMessage);
      }
    },
    onSuccess: (_data, _variables, _context, mutation) => {
      // 成功提示
      if (mutation.meta?.successMessage) {
        message.success(mutation.meta.successMessage as string);
      }

      // 智能缓存失效：根据 mutation key 自动失效相关查询
      const mutationKey = mutation.options.mutationKey;
      if (mutationKey && typeof mutationKey[0] === 'string') {
        const invalidationKeys = MutationInvalidationMap[mutationKey[0] as string];
        if (invalidationKeys) {
          invalidationKeys.forEach((key) => {
            queryClient.invalidateQueries({ queryKey: key });
          });
        }
      }

      // 自定义失效：支持在 mutation meta 中指定
      if (mutation.meta?.invalidates) {
        const keysToInvalidate = mutation.meta.invalidates as readonly unknown[][];
        keysToInvalidate.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
    },
  });
}

/**
 * React Query 客户端配置
 */
export const queryClient = new QueryClient({
  queryCache: createQueryCache(),
  mutationCache: createMutationCache(),
  defaultOptions: {
    queries: {
      // 数据新鲜时间 - 在此时间内不会重新获取
      staleTime: CacheTime.MEDIUM,
      // 缓存时间 - 缓存在内存中保留的时间
      gcTime: CacheTime.LONG,
      // 失败重试策略
      retry: (failureCount, error: unknown) => {
        // 4xx 错误不重试（客户端错误）
        const httpError = error as { status?: number } | null;
        if (httpError?.status && httpError.status >= 400 && httpError.status < 500) {
          return false;
        }
        // 网络错误最多重试 2 次
        return failureCount < 2;
      },
      // 指数退避重试延迟
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 窗口聚焦时不自动重新获取（避免不必要的请求）
      refetchOnWindowFocus: false,
      // 组件挂载时：如果数据过期则重新获取
      refetchOnMount: 'always',
      // 重新连接时重新获取（网络恢复后更新数据）
      refetchOnReconnect: true,
      // 禁用结构共享以提高性能（适用于大数据集）
      structuralSharing: true,
      // 使用 placeholder 数据时不显示 loading 状态
      placeholderData: (previousData: unknown) => previousData,
      // 网络模式：始终尝试（包括离线状态）
      networkMode: 'offlineFirst',
    },
    mutations: {
      // 变更失败重试一次
      retry: 1,
      // 网络模式
      networkMode: 'offlineFirst',
    },
  },
});

/**
 * 工具函数：使多个查询失效
 */
export function invalidateQueries(...keys: ReturnType<typeof QueryKeys[keyof typeof QueryKeys]>[]) {
  keys.forEach((key) => {
    queryClient.invalidateQueries({ queryKey: key });
  });
}

/**
 * 工具函数：预取数据
 */
export async function prefetchQuery<T>(
  key: readonly unknown[],
  queryFn: () => Promise<T>
): Promise<void> {
  try {
    await queryClient.prefetchQuery({
      queryKey: key,
      queryFn,
      staleTime: CacheTime.MEDIUM,
    });
  } catch {
    // Prefetch failures are non-critical - silently ignore
    // Failed prefetches will be retried when the query is actually used
  }
}

/**
 * 工具函数：取消所有正在进行的查询
 */
export function cancelAllQueries() {
  queryClient.cancelQueries();
}

/**
 * 工具函数：重置所有缓存
 */
export function resetAllQueries() {
  queryClient.resetQueries();
}

/**
 * 工具函数：清除所有缓存
 */
export function clearAllQueries() {
  queryClient.clear();
}

/**
 * 乐观更新辅助函数
 *
 * @param queryKey 查询键
 * @param updateFn 更新函数，接收旧数据并返回新数据
 */
export function optimisticUpdate<T>(
  queryKey: readonly unknown[],
  updateFn: (old: T | undefined) => T
) {
  // 取消正在进行的查询，避免被覆盖
  queryClient.cancelQueries({ queryKey });

  // 保存之前的数据
  const previousData = queryClient.getQueryData<T>(queryKey);

  // 乐观更新
  queryClient.setQueryData<T>(queryKey, updateFn(previousData));

  // 返回回滚函数
  return () => {
    queryClient.setQueryData<T>(queryKey, previousData);
  };
}

/**
 * 获取缓存数据的辅助函数
 */
export function getQueryData<T>(key: readonly unknown[]): T | undefined {
  return queryClient.getQueryData<T>(key);
}

/**
 * 设置缓存数据的辅助函数
 */
export function setQueryData<T>(key: readonly unknown[], data: T | undefined): void {
  queryClient.setQueryData<T>(key, data);
}

export default queryClient;
