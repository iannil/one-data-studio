/**
 * 数据清洗服务
 * TODO: 实现数据清洗 API
 */

import { apiClient } from './api';

export interface CleaningRule {
  id: string;
  name: string;
  type: 'null_handling' | 'duplicate_removal' | 'outlier_detection' | 'format_correction';
  tableName: string;
  columnName: string;
  config: Record<string, unknown>;
}

export interface CleaningJob {
  id: string;
  ruleId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  result?: {
    processedRows: number;
    cleanedRows: number;
    errors: number;
  };
}

/**
 * 获取清洗规则列表
 */
export async function listRules(tableId?: string) {
  return apiClient.get('/api/v1/cleaning/rules', { params: { tableId } });
}

/**
 * 创建清洗规则
 */
export async function createRule(rule: Partial<CleaningRule>) {
  return apiClient.post('/api/v1/cleaning/rules', rule);
}

/**
 * 更新清洗规则
 */
export async function updateRule(ruleId: string, rule: Partial<CleaningRule>) {
  return apiClient.put(`/api/v1/cleaning/rules/${ruleId}`, rule);
}

/**
 * 删除清洗规则
 */
export async function deleteRule(ruleId: string) {
  return apiClient.delete(`/api/v1/cleaning/rules/${ruleId}`);
}

/**
 * 执行清洗作业
 */
export async function runCleaning(ruleId: string, tableId: string) {
  return apiClient.post('/api/v1/cleaning/jobs', { ruleId, tableId });
}

/**
 * 获取清洗作业状态
 */
export async function getJobStatus(jobId: string) {
  return apiClient.get<undefined, CleaningJob>(`/api/v1/cleaning/jobs/${jobId}`);
}

/**
 * 获取清洗历史
 */
export async function getCleaningHistory(tableId: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/cleaning/history', { params: { tableId, page, pageSize } });
}
