/**
 * 审计日志服务
 * TODO: 实现审计日志 API
 */

import { apiClient } from './api';

export type AuditAction =
  | 'create'
  | 'read'
  | 'update'
  | 'delete'
  | 'login'
  | 'logout'
  | 'export'
  | 'import'
  | 'execute'
  | 'approve'
  | 'reject';

export type AuditResource =
  | 'user'
  | 'role'
  | 'datasource'
  | 'dataset'
  | 'workflow'
  | 'model'
  | 'report'
  | 'setting';

export interface AuditLog {
  id: string;
  userId: string;
  username: string;
  action: AuditAction;
  resource: AuditResource;
  resourceId?: string;
  resourceName?: string;
  details?: Record<string, unknown>;
  ip: string;
  userAgent?: string;
  status: 'success' | 'failure';
  errorMessage?: string;
  timestamp: string;
}

export interface AuditStatistics {
  totalActions: number;
  actionsByType: Record<AuditAction, number>;
  actionsByResource: Record<AuditResource, number>;
  topUsers: Array<{ username: string; count: number }>;
  failureRate: number;
}

/**
 * 获取审计日志列表
 */
export async function listAuditLogs(params: {
  page?: number;
  pageSize?: number;
  userId?: string;
  action?: AuditAction;
  resource?: AuditResource;
  startDate?: string;
  endDate?: string;
  status?: 'success' | 'failure';
}) {
  return apiClient.get('/api/v1/audit/logs', { params });
}

/**
 * 获取审计日志详情
 */
export async function getAuditLog(logId: string) {
  return apiClient.get<undefined, AuditLog>(`/api/v1/audit/logs/${logId}`);
}

/**
 * 获取审计统计
 */
export async function getStatistics(params?: {
  startDate?: string;
  endDate?: string;
}) {
  return apiClient.get<undefined, AuditStatistics>('/api/v1/audit/statistics', { params });
}

/**
 * 导出审计日志
 */
export async function exportAuditLogs(params: {
  format: 'csv' | 'json' | 'excel';
  startDate?: string;
  endDate?: string;
  actions?: AuditAction[];
  resources?: AuditResource[];
}) {
  return apiClient.post('/api/v1/audit/export', params);
}

/**
 * 获取用户操作历史
 */
export async function getUserHistory(userId: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get(`/api/v1/audit/users/${userId}/history`, { params: { page, pageSize } });
}

/**
 * 获取资源访问历史
 */
export async function getResourceHistory(resource: AuditResource, resourceId: string) {
  return apiClient.get(`/api/v1/audit/resources/${resource}/${resourceId}/history`);
}

/**
 * 搜索审计日志
 */
export async function searchLogs(query: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/audit/search', { params: { query, page, pageSize } });
}
