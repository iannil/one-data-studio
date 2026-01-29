/**
 * React Query 自定义 Hooks
 * Sprint 8: 性能优化 - API 调用封装
 *
 * 提供基于 React Query 的 API 调用 hooks
 */

import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import apiClient, { ApiResponse } from './api';
import { QueryKeys, CacheTime } from './queryClient';
import { message } from 'antd';

// ==================== 类型定义 ====================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ListParams {
  page?: number;
  pageSize?: number;
  status?: string;
  limit?: number;
}

// ==================== 通用 Hooks ====================

/**
 * 通用查询 Hook
 */
export function useApiQuery<T>(
  queryKey: readonly unknown[],
  url: string,
  options?: Omit<UseQueryOptions<ApiResponse<T>>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey,
    queryFn: async () => {
      // apiClient response interceptor already extracts response.data
      return await apiClient.get<ApiResponse<T>>(url) as unknown as ApiResponse<T>;
    },
    staleTime: CacheTime.MEDIUM,
    ...options,
  });
}

/**
 * 通用变更 Hook
 */
export function useApiMutation<TData, TVariables = unknown>(
  url: string,
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  options?: UseMutationOptions<ApiResponse<TData>, Error, TVariables>
) {
  return useMutation({
    mutationFn: async (variables: TVariables) => {
      return await apiClient.request<ApiResponse<TData>>({
        url,
        method,
        data: variables,
      }) as unknown as ApiResponse<TData>;
    },
    ...options,
  });
}

/**
 * 通用 POST 请求 Hook
 */
export function useApiPost<TData, TVariables = unknown>(
  url: string,
  options?: UseMutationOptions<ApiResponse<TData>, Error, TVariables> & {
    successMessage?: string;
    invalidateQueries?: readonly unknown[][];
  }
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables: TVariables) => {
      return await apiClient.post<ApiResponse<TData>>(url, variables) as unknown as ApiResponse<TData>;
    },
    onSuccess: (data, variables, context) => {
      if (options?.successMessage) {
        message.success(options.successMessage);
      }
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
      if (options?.onSuccess) {
        (options.onSuccess as (data: ApiResponse<TData>, variables: TVariables, context: unknown) => void)(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * 通用 PUT 请求 Hook
 */
export function useApiPut<TData, TVariables = unknown>(
  url: string | ((variables: TVariables) => string),
  options?: UseMutationOptions<ApiResponse<TData>, Error, TVariables> & {
    successMessage?: string;
    invalidateQueries?: readonly unknown[][];
  }
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables: TVariables) => {
      const finalUrl = typeof url === 'function' ? url(variables) : url;
      return await apiClient.put<ApiResponse<TData>>(finalUrl, variables) as unknown as ApiResponse<TData>;
    },
    onSuccess: (data, variables, context) => {
      if (options?.successMessage) {
        message.success(options.successMessage);
      }
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
      if (options?.onSuccess) {
        (options.onSuccess as (data: ApiResponse<TData>, variables: TVariables, context: unknown) => void)(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * 通用 DELETE 请求 Hook
 */
export function useApiDelete<TData = unknown, TVariables = unknown>(
  url: string | ((variables: TVariables) => string),
  options?: UseMutationOptions<ApiResponse<TData>, Error, TVariables> & {
    successMessage?: string;
    invalidateQueries?: readonly unknown[][];
  }
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables: TVariables) => {
      const finalUrl = typeof url === 'function' ? url(variables) : url;
      return await apiClient.delete<ApiResponse<TData>>(finalUrl) as unknown as ApiResponse<TData>;
    },
    onSuccess: (data, variables, context) => {
      if (options?.successMessage) {
        message.success(options.successMessage || '删除成功');
      }
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
      if (options?.onSuccess) {
        (options.onSuccess as (data: ApiResponse<TData>, variables: TVariables, context: unknown) => void)(data, variables, context);
      }
    },
    ...options,
  });
}

// ==================== 数据集 Hooks ====================

export interface Dataset {
  id: number;
  dataset_id: string;
  name: string;
  description: string;
  storage_type: string;
  storage_path: string;
  format: string;
  status: string;
  tags: string[];
  row_count: number;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

export function useDatasets(params?: ListParams) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.set('status', params.status);
  if (params?.limit) queryParams.set('limit', params.limit.toString());

  return useQuery({
    queryKey: [...QueryKeys.datasets(), params],
    queryFn: async () => {
      return await apiClient.get<ApiResponse<Dataset[]>>(
        `/api/v1/datasets${queryParams.toString() ? `?${queryParams}` : ''}`
      );
    },
    staleTime: CacheTime.MEDIUM,
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: QueryKeys.dataset(id),
    queryFn: async () => {
      return await apiClient.get<ApiResponse<Dataset>>(`/api/v1/datasets/${id}`);
    },
    enabled: !!id,
    staleTime: CacheTime.LONG,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Dataset>) => {
      return await apiClient.post<ApiResponse<{ dataset_id: string }>>('/api/v1/datasets', data);
    },
    onSuccess: () => {
      message.success('数据集创建成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.datasets() });
    },
  });
}

export function useUpdateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Dataset> }) => {
      return await apiClient.put<ApiResponse<Dataset>>(`/api/v1/datasets/${id}`, data);
    },
    onSuccess: (_, variables) => {
      message.success('数据集更新成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.dataset(variables.id) });
      queryClient.invalidateQueries({ queryKey: QueryKeys.datasets() });
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete<ApiResponse<unknown>>(`/api/v1/datasets/${id}`);
    },
    onSuccess: () => {
      message.success('数据集删除成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.datasets() });
    },
  });
}

// ==================== 工作流 Hooks ====================

export interface Workflow {
  id: number;
  workflow_id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  definition?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export function useWorkflows() {
  return useQuery({
    queryKey: QueryKeys.workflows(),
    queryFn: async () => {
      return await apiClient.get<ApiResponse<{ workflows: Workflow[] }>>('/api/v1/workflows');
    },
    staleTime: CacheTime.MEDIUM,
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: QueryKeys.workflow(id),
    queryFn: async () => {
      return await apiClient.get<ApiResponse<Workflow>>(`/api/v1/workflows/${id}`);
    },
    enabled: !!id,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Workflow>) => {
      return await apiClient.post<ApiResponse<{ workflow_id: string }>>('/api/v1/workflows', data);
    },
    onSuccess: () => {
      message.success('工作流创建成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.workflows() });
    },
  });
}

export function useUpdateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Workflow> }) => {
      return await apiClient.put<ApiResponse<Workflow>>(`/api/v1/workflows/${id}`, data);
    },
    onSuccess: (_, variables) => {
      message.success('工作流更新成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.workflow(variables.id) });
      queryClient.invalidateQueries({ queryKey: QueryKeys.workflows() });
    },
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete<ApiResponse<unknown>>(`/api/v1/workflows/${id}`);
    },
    onSuccess: () => {
      message.success('工作流删除成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.workflows() });
    },
  });
}

// ==================== 文档 Hooks ====================

export interface Document {
  id: number;
  doc_id: string;
  file_name: string;
  title: string;
  collection_name: string;
  chunk_count: number;
  created_at: string;
  created_by: string;
}

export function useDocuments(collection?: string) {
  return useQuery({
    queryKey: [...QueryKeys.documents(), collection],
    queryFn: async () => {
      const params = collection ? `?collection=${collection}` : '';
      return await apiClient.get<ApiResponse<{ documents: Document[] }>>(
        `/api/v1/documents${params}`
      );
    },
    staleTime: CacheTime.MEDIUM,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      content: string;
      file_name: string;
      title?: string;
      collection?: string;
    }) => {
      return await apiClient.post<ApiResponse<{ doc_id: string }>>('/api/v1/documents/upload', data);
    },
    onSuccess: () => {
      message.success('文档上传成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.documents() });
      queryClient.invalidateQueries({ queryKey: QueryKeys.collections() });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete<ApiResponse<unknown>>(`/api/v1/documents/${id}`);
    },
    onSuccess: () => {
      message.success('文档删除成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.documents() });
    },
  });
}

// ==================== Agent 模板 Hooks ====================

export interface AgentTemplate {
  template_id: string;
  name: string;
  description?: string;
  agent_type: string;
  model: string;
  max_iterations: number;
  system_prompt?: string;
  selected_tools: string[];
  created_by: string;
  created_at: string;
}

export function useAgentTemplates(agentType?: string) {
  return useQuery({
    queryKey: [...QueryKeys.agentTemplates(), agentType],
    queryFn: async () => {
      const params = agentType ? `?agent_type=${agentType}` : '';
      return await apiClient.get<ApiResponse<{ templates: AgentTemplate[] }>>(
        `/api/v1/agent/templates${params}`
      );
    },
    staleTime: CacheTime.LONG,
  });
}

export function useCreateAgentTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<AgentTemplate>) => {
      return await apiClient.post<ApiResponse<AgentTemplate>>('/api/v1/agent/templates', data);
    },
    onSuccess: () => {
      message.success('Agent 模板创建成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.agentTemplates() });
    },
  });
}

export function useUpdateAgentTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AgentTemplate> }) => {
      return await apiClient.put<ApiResponse<AgentTemplate>>(
        `/api/v1/agent/templates/${id}`,
        data
      );
    },
    onSuccess: (_) => {
      message.success('Agent 模板更新成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.agentTemplates() });
    },
  });
}

export function useDeleteAgentTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete<ApiResponse<unknown>>(`/api/v1/agent/templates/${id}`);
    },
    onSuccess: () => {
      message.success('Agent 模板删除成功');
      queryClient.invalidateQueries({ queryKey: QueryKeys.agentTemplates() });
    },
  });
}

// ==================== 模型 Hooks ====================

export interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}

export function useModels() {
  return useQuery({
    queryKey: QueryKeys.models(),
    queryFn: async () => {
      return await apiClient.get<{ data: Model[]; object: string }>('/v1/models', {
        baseURL: import.meta.env.VITE_API_MODEL_URL || import.meta.env.VITE_CUBE_API_URL || '',
      });
    },
    staleTime: CacheTime.LONG,
  });
}

export default {
  // 数据集
  useDatasets,
  useDataset,
  useCreateDataset,
  useUpdateDataset,
  useDeleteDataset,

  // 工作流
  useWorkflows,
  useWorkflow,
  useCreateWorkflow,
  useUpdateWorkflow,
  useDeleteWorkflow,

  // 文档
  useDocuments,
  useUploadDocument,
  useDeleteDocument,

  // Agent 模板
  useAgentTemplates,
  useCreateAgentTemplate,
  useUpdateAgentTemplate,
  useDeleteAgentTemplate,

  // 模型
  useModels,
};
