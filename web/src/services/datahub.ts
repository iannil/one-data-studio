/**
 * DataHub 集成服务
 * TODO: 实现 DataHub API 集成
 */

import { apiClient } from './api';

export interface DataHubEntity {
  urn: string;
  type: string;
  name: string;
  description?: string;
}

export interface DataHubDataset extends DataHubEntity {
  type: 'dataset';
  platform: string;
  origin: string;
  tags?: string[];
}

export interface DataHubGMSMSearchResponse {
  searchResults: Array<{
    entity: DataHubEntity;
    matchedFields: string[];
  }>;
}

/**
 * 搜索 DataHub 实体
 */
export async function searchEntities(query: string, count: number = 10) {
  return apiClient.post<undefined, DataHubGMSMSearchResponse>('/api/v1/datahub/search', {
    query,
    count,
  });
}

/**
 * 获取数据集详情
 */
export async function getDataset(urn: string) {
  return apiClient.get<undefined, DataHubDataset>(`/api/v1/datahub/datasets/${urn}`);
}

/**
 * 同步数据集到 One Data Studio
 */
export async function syncDataset(urn: string) {
  return apiClient.post('/api/v1/datahub/sync', { urn });
}
