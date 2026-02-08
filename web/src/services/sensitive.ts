/**
 * 敏感数据服务
 * TODO: 实现敏感数据识别和脱敏 API
 */

import { apiClient } from './api';

export type SensitiveLevel = 'public' | 'internal' | 'confidential' | 'secret';
export type SensitiveType = 'personal' | 'financial' | 'health' | 'identity' | 'contact' | 'other';

export interface SensitiveColumn {
  id: string;
  datasourceId: string;
  database: string;
  table: string;
  column: string;
  level: SensitiveLevel;
  type: SensitiveType;
  confidence: number;
  detectedBy: 'manual' | 'ai' | 'rule';
  description?: string;
}

export interface SensitiveMaskRule {
  id: string;
  name: string;
  type: SensitiveType;
  maskType: 'partial' | 'hash' | 'replace' | 'encrypt';
  pattern?: string;
  replacement?: string;
}

export interface SensitiveScanTask {
  id: string;
  datasourceId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  scannedColumns: number;
  sensitiveColumns: number;
  startTime: string;
  endTime?: string;
}

/**
 * 获取敏感字段列表
 */
export async function listSensitiveColumns(filters?: {
  datasourceId?: string;
  level?: SensitiveLevel;
  type?: SensitiveType;
}) {
  return apiClient.get('/api/v1/sensitive/columns', { params: filters });
}

/**
 * 更新敏感级别
 */
export async function updateSensitiveLevel(columnId: string, level: SensitiveLevel) {
  return apiClient.put(`/api/v1/sensitive/columns/${columnId}`, { level });
}

/**
 * 获取脱敏规则列表
 */
export async function listMaskRules() {
  return apiClient.get('/api/v1/sensitive/mask-rules');
}

/**
 * 创建脱敏规则
 */
export async function createMaskRule(rule: Partial<SensitiveMaskRule>) {
  return apiClient.post('/api/v1/sensitive/mask-rules', rule);
}

/**
 * 更新脱敏规则
 */
export async function updateMaskRule(ruleId: string, rule: Partial<SensitiveMaskRule>) {
  return apiClient.put(`/api/v1/sensitive/mask-rules/${ruleId}`, rule);
}

/**
 * 删除脱敏规则
 */
export async function deleteMaskRule(ruleId: string) {
  return apiClient.delete(`/api/v1/sensitive/mask-rules/${ruleId}`);
}

/**
 * 创建敏感数据扫描任务
 */
export async function createScanTask(datasourceId: string, tables?: string[]) {
  return apiClient.post('/api/v1/sensitive/scan-tasks', { datasourceId, tables });
}

/**
 * 获取扫描任务状态
 */
export async function getScanTaskStatus(taskId: string) {
  return apiClient.get<undefined, SensitiveScanTask>(`/api/v1/sensitive/scan-tasks/${taskId}`);
}

/**
 * 获取敏感数据统计
 */
export async function getStatistics(datasourceId?: string) {
  return apiClient.get('/api/v1/sensitive/statistics', { params: { datasourceId } });
}

/**
 * 应用脱敏到查询结果
 */
export async function applyMasking(sql: string, datasourceId: string) {
  return apiClient.post('/api/v1/sensitive/apply-masking', { sql, datasourceId });
}
