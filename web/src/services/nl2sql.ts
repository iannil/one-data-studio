/**
 * NL2SQL (自然语言转 SQL) 服务
 * TODO: 实现 NL2SQL API
 */

import { apiClient } from './api';

export interface NL2SQLRequest {
  query: string;
  datasourceId: string;
  database?: string;
  context?: string[];
}

export interface NL2SQLResponse {
  sql: string;
  explanation: string;
  confidence: number;
  suggestedTables?: string[];
}

export interface NL2SQLHistory {
  id: string;
  naturalLanguageQuery: string;
  generatedSQL: string;
  executionResult?: {
    rows: number;
    time: number;
  };
  createdAt: string;
}

/**
 * 自然语言转 SQL
 */
export async function convertNL2SQL(params: NL2SQLRequest) {
  return apiClient.post<undefined, NL2SQLResponse>('/api/v1/nl2sql/convert', params);
}

/**
 * 验证生成的 SQL
 */
export async function validateSQL(sql: string, datasourceId: string) {
  return apiClient.post('/api/v1/nl2sql/validate', { sql, datasourceId });
}

/**
 * 执行 SQL
 */
export async function executeSQL(sql: string, datasourceId: string, database?: string) {
  return apiClient.post('/api/v1/nl2sql/execute', { sql, datasourceId, database });
}

/**
 * 获取查询历史
 */
export async function getHistory(datasourceId?: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/nl2sql/history', { params: { datasourceId, page, pageSize } });
}

/**
 * 获取推荐查询
 */
export async function getSuggestions(datasourceId: string, limit: number = 5) {
  return apiClient.get('/api/v1/nl2sql/suggestions', { params: { datasourceId, limit } });
}
