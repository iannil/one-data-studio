import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

export interface ColumnSchema {
  name: string;
  type: string;
  description?: string;
  nullable?: boolean;
  primary_key?: boolean;
}

export interface DatasetStatistics {
  row_count: number;
  size_bytes: number;
}

export interface Dataset {
  dataset_id: string;
  name: string;
  description?: string;
  storage_type: string;
  storage_path: string;
  format: string;
  schema?: {
    columns: ColumnSchema[];
  };
  statistics?: DatasetStatistics;
  tags?: string[];
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  storage_type: string;
  storage_path: string;
  format: string;
  schema?: {
    columns: ColumnSchema[];
  };
  statistics?: DatasetStatistics;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface UpdateDatasetRequest {
  name?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface DatasetListParams {
  tags?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
  page: number;
  page_size: number;
}

export interface UploadUrlRequest {
  file_name: string;
  file_size: number;
  content_type?: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  file_id: string;
  expires_at: string;
}

export interface DatasetPreviewResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
}

export interface DatasetVersion {
  version_id: string;
  version_number: number;
  description?: string;
  created_at: string;
  row_count?: number;
  size_bytes?: number;
}

// ============= API 方法 =============

/**
 * 获取数据集列表
 */
export async function getDatasets(params?: DatasetListParams): Promise<ApiResponse<DatasetListResponse>> {
  return apiClient.get('/api/v1/datasets', { params });
}

/**
 * 获取数据集详情
 */
export async function getDataset(datasetId: string): Promise<ApiResponse<Dataset>> {
  return apiClient.get(`/api/v1/datasets/${datasetId}`);
}

/**
 * 创建数据集
 */
export async function createDataset(
  data: CreateDatasetRequest
): Promise<ApiResponse<{ dataset_id: string; name: string; status: string; created_at: string }>> {
  return apiClient.post('/api/v1/datasets', data);
}

/**
 * 更新数据集
 */
export async function updateDataset(
  datasetId: string,
  data: UpdateDatasetRequest
): Promise<ApiResponse<Dataset>> {
  return apiClient.put(`/api/v1/datasets/${datasetId}`, data);
}

/**
 * 删除数据集
 */
export async function deleteDataset(datasetId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/datasets/${datasetId}`);
}

/**
 * 获取上传 URL
 */
export async function getUploadUrl(
  datasetId: string,
  data: UploadUrlRequest
): Promise<ApiResponse<UploadUrlResponse>> {
  return apiClient.post(`/api/v1/datasets/${datasetId}/upload-url`, data);
}

/**
 * 获取数据集预览
 */
export async function getDatasetPreview(
  datasetId: string,
  limit?: number
): Promise<ApiResponse<DatasetPreviewResponse>> {
  return apiClient.get(`/api/v1/datasets/${datasetId}/preview`, {
    params: { limit },
  });
}

/**
 * 获取数据集版本列表
 */
export async function getDatasetVersions(datasetId: string): Promise<ApiResponse<{ versions: DatasetVersion[] }>> {
  return apiClient.get(`/api/v1/datasets/${datasetId}/versions`);
}

// ============= 元数据 API =============

export interface Database {
  name: string;
  description?: string;
  owner?: string;
}

export interface TableInfo {
  name: string;
  description?: string;
  row_count?: number;
  updated_at?: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  description?: string;
  primary_key?: boolean;
  foreign_key?: {
    table: string;
    column: string;
  };
  enum?: string[];
}

export interface TableDetail {
  table_name: string;
  description?: string;
  database: string;
  columns: ColumnInfo[];
  indexes?: Array<{ name: string; columns: string[] }>;
  relations?: Array<{
    type: string;
    from_table: string;
    from_column: string;
    to_table: string;
    to_column: string;
  }>;
  sample_data?: Record<string, unknown>[];
}

/**
 * 获取数据库列表
 */
export async function getDatabases(): Promise<ApiResponse<{ databases: Database[] }>> {
  return apiClient.get('/api/v1/metadata/databases');
}

/**
 * 获取表列表
 */
export async function getTables(database: string): Promise<ApiResponse<{ tables: TableInfo[] }>> {
  return apiClient.get(`/api/v1/metadata/databases/${database}/tables`);
}

/**
 * 获取表详情
 */
export async function getTableDetail(
  database: string,
  table: string
): Promise<ApiResponse<TableDetail>> {
  return apiClient.get(`/api/v1/metadata/databases/${database}/tables/${table}`);
}

/**
 * 智能表搜索
 */
export async function searchTables(query: string, limit = 10): Promise<
  ApiResponse<{
    results: Array<{
      table: string;
      database: string;
      relevance_score: number;
      matched_columns: string[];
    }>;
  }>
> {
  return apiClient.post('/api/v1/metadata/tables/search', { query, limit });
}

// ============= 查询 API =============

export interface QueryExecuteRequest {
  database: string;
  sql: string;
  timeout_seconds?: number;
}

export interface QueryExecuteResponse {
  query_id: string;
  status: string;
  rows: Record<string, unknown>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
}

export interface QueryValidateRequest {
  database: string;
  sql: string;
}

export interface QueryValidateResponse {
  valid: boolean;
  parameters?: Array<{ index: number; type: string }>;
  estimated_rows?: number;
}

/**
 * 执行查询
 */
export async function executeQuery(
  data: QueryExecuteRequest
): Promise<ApiResponse<QueryExecuteResponse>> {
  return apiClient.post('/api/v1/query/execute', data);
}

/**
 * 验证 SQL
 */
export async function validateSql(
  data: QueryValidateRequest
): Promise<ApiResponse<QueryValidateResponse>> {
  return apiClient.post('/api/v1/query/validate', data);
}

export default {
  // 数据集
  getDatasets,
  getDataset,
  createDataset,
  updateDataset,
  deleteDataset,
  getUploadUrl,
  getDatasetPreview,
  getDatasetVersions,

  // 元数据
  getDatabases,
  getTables,
  getTableDetail,
  searchTables,

  // 查询
  executeQuery,
  validateSql,
};
