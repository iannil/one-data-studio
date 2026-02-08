/**
 * 元数据同步服务
 * TODO: 实现元数据同步 API
 */

import { apiClient } from './api';

export interface MetadataSyncTask {
  id: string;
  name: string;
  sourceType: 'database' | 'datalake' | 'datahub' | 'openmetadata';
  sourceConfig: Record<string, unknown>;
  schedule?: string;
  status: 'active' | 'paused' | 'disabled';
  lastSyncTime?: string;
  nextSyncTime?: string;
}

export interface MetadataSyncRecord {
  id: string;
  taskId: string;
  status: 'running' | 'success' | 'failed' | 'partial';
  startTime: string;
  endTime?: string;
  summary?: {
    total: number;
    added: number;
    updated: number;
    deleted: number;
    failed: number;
  };
  error?: string;
}

/**
 * 获取同步任务列表
 */
export async function listTasks(page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/metadata-sync/tasks', { params: { page, pageSize } });
}

/**
 * 创建同步任务
 */
export async function createTask(task: Partial<MetadataSyncTask>) {
  return apiClient.post('/api/v1/metadata-sync/tasks', task);
}

/**
 * 更新同步任务
 */
export async function updateTask(taskId: string, task: Partial<MetadataSyncTask>) {
  return apiClient.put(`/api/v1/metadata-sync/tasks/${taskId}`, task);
}

/**
 * 删除同步任务
 */
export async function deleteTask(taskId: string) {
  return apiClient.delete(`/api/v1/metadata-sync/tasks/${taskId}`);
}

/**
 * 触发同步
 */
export async function triggerSync(taskId: string) {
  return apiClient.post(`/api/v1/metadata-sync/tasks/${taskId}/trigger`, {});
}

/**
 * 获取同步记录
 */
export async function getSyncRecords(taskId: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get(`/api/v1/metadata-sync/tasks/${taskId}/records`, { params: { page, pageSize } });
}

/**
 * 获取同步状态
 */
export async function getSyncStatus(recordId: string) {
  return apiClient.get<undefined, MetadataSyncRecord>(`/api/v1/metadata-sync/records/${recordId}`);
}
