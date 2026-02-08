/**
 * ShardingSphere 集成服务
 * TODO: 实现 ShardingSphere API 集成
 */

import { apiClient } from './api';

export interface ShardingRule {
  tableName: string;
  logicTable: string;
  dataNodes: string[];
  databaseStrategy: {
    type: 'standard' | 'inline' | 'complex';
    shardingColumn?: string;
    algorithm?: string;
  };
  tableStrategy?: {
    type: 'standard' | 'inline' | 'complex';
    shardingColumn?: string;
    algorithm?: string;
  };
}

export interface ShardingDataSource {
  name: string;
  type: 'MySQL' | 'PostgreSQL' | 'Oracle';
  hosts: string[];
  username: string;
  database?: string;
  props?: Record<string, string>;
}

/**
 * 获取分片规则列表
 */
export async function listRules(dataSourceName: string) {
  return apiClient.get('/api/v1/shardingsphere/rules', { params: { dataSourceName } });
}

/**
 * 创建分片规则
 */
export async function createRule(rule: Partial<ShardingRule>) {
  return apiClient.post('/api/v1/shardingsphere/rules', rule);
}

/**
 * 更新分片规则
 */
export async function updateRule(tableName: string, rule: Partial<ShardingRule>) {
  return apiClient.put(`/api/v1/shardingsphere/rules/${tableName}`, rule);
}

/**
 * 删除分片规则
 */
export async function deleteRule(tableName: string) {
  return apiClient.delete(`/api/v1/shardingsphere/rules/${tableName}`);
}

/**
 * 获取数据源列表
 */
export async function listDataSources() {
  return apiClient.get<undefined, ShardingDataSource[]>('/api/v1/shardingsphere/datasources');
}

/**
 * 添加数据源
 */
export async function addDataSource(dataSource: Partial<ShardingDataSource>) {
  return apiClient.post('/api/v1/shardingsphere/datasources', dataSource);
}

/**
 * 移除数据源
 */
export async function removeDataSource(name: string) {
  return apiClient.delete(`/api/v1/shardingsphere/datasources/${name}`);
}

/**
 * 验证分片配置
 */
export async function validateConfig(config: Record<string, unknown>) {
  return apiClient.post('/api/v1/shardingsphere/validate', config);
}

/**
 * 预览路由结果
 */
export async function previewRouting(sql: string, dataSource: string) {
  return apiClient.post('/api/v1/shardingsphere/routing/preview', { sql, dataSource });
}
