/**
 * CDC API 服务
 */

import { apiClient } from '@/services/api';

export interface CDCJob {
  job_id: string;
  job_name: string;
  description: string;
  source_type: string;
  sink_type: string;
  status: string;
  records_in: number;
  records_out: number;
  lag_ms: number;
  start_time: string;
  enabled: boolean;
}

export interface CDCMetrics {
  job_id: string;
  status: string;
  records_in: number;
  records_out: number;
  bytes_in: number;
  bytes_out: number;
  lag_ms: number;
  last_checkpoint: string;
  error_message: string;
  start_time: string;
}

export interface CDCSourceConfig {
  type: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database: string;
  schema?: string;
  tables?: string[];
  server_id?: number;
}

export interface CDCTargetConfig {
  type: string;
  host?: string;
  port?: number;
  database?: string;
  table?: string;
  username?: string;
  password?: string;
  endpoint?: string;
  bucket?: string;
  path?: string;
  access_key?: string;
  secret_key?: string;
  primary_key?: string;
}

export interface CreateCDCJobRequest {
  job_name: string;
  description?: string;
  source: CDCSourceConfig;
  sink: CDCTargetConfig;
  transforms?: unknown[];
  parallelism?: number;
}

export const cdcApi = {
  /**
   * 健康检查
   */
  getHealth: () =>
    apiClient.get<{ data: { status: string; service: string; url: string } }>('/api/v1/cdc/health'),

  /**
   * 创建 CDC 任务
   */
  createJob: (data: CreateCDCJobRequest) =>
    apiClient.post<{ data: { job_id: string }; code: number; msg: string }>('/api/v1/cdc/jobs', data),

  /**
   * 列出 CDC 任务
   */
  listJobs: (params?: { status?: string }) =>
    apiClient.get<{ data: { jobs: CDCJob[]; total: number }; code: number; msg: string }>('/api/v1/cdc/jobs', {
      params,
    }),

  /**
   * 获取任务详情
   */
  getJob: (jobId: string) =>
    apiClient.get<{ data: { config: Record<string, unknown>; metrics: CDCMetrics }; code: number; msg: string }>(
      `/api/v1/cdc/jobs/${jobId}`
    ),

  /**
   * 启动任务
   */
  startJob: (jobId: string) =>
    apiClient.post<{ data: { job_id: string; status: string }; code: number; msg: string }>(
      `/api/v1/cdc/jobs/${jobId}/start`
    ),

  /**
   * 停止任务
   */
  stopJob: (jobId: string) =>
    apiClient.post<{ data: { job_id: string; status: string }; code: number; msg: string }>(
      `/api/v1/cdc/jobs/${jobId}/stop`
    ),

  /**
   * 删除任务
   */
  deleteJob: (jobId: string) =>
    apiClient.delete<{ data: { job_id: string }; code: number; msg: string }>(`/api/v1/cdc/jobs/${jobId}`),

  /**
   * 获取任务指标
   */
  getJobMetrics: (jobId: string) =>
    apiClient.get<{ data: CDCMetrics; code: number; msg: string }>(`/api/v1/cdc/jobs/${jobId}/metrics`),

  /**
   * 使用 MySQL-MinIO 模板创建任务
   */
  createMySQLToMinIOJob: (data: {
    mysql_host: string;
    mysql_port: number;
    mysql_user: string;
    mysql_password: string;
    mysql_database: string;
    tables: string[];
    minio_endpoint: string;
    minio_bucket: string;
    minio_path: string;
    minio_access_key: string;
    minio_secret_key: string;
  }) =>
    apiClient.post<{ data: { job_id: string }; code: number; msg: string }>(
      '/api/v1/cdc/templates/mysql-minio',
      data
    ),

  /**
   * 使用 MySQL-ClickHouse 模板创建任务
   */
  createMySQLToClickHouseJob: (data: {
    mysql_host: string;
    mysql_port: number;
    mysql_user: string;
    mysql_password: string;
    mysql_database: string;
    tables: string[];
    ch_host: string;
    ch_port: number;
    ch_database: string;
    ch_user: string;
    ch_password: string;
  }) =>
    apiClient.post<{ data: { job_id: string }; code: number; msg: string }>(
      '/api/v1/cdc/templates/mysql-clickhouse',
      data
    ),
};

export default cdcApi;
