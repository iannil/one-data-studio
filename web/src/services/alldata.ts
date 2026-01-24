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

// ============= 数据源类型 =============

export type DataSourceType = 'mysql' | 'postgresql' | 'oracle' | 'sqlserver' | 'hive' | 'mongodb' | 'redis' | 'elasticsearch';

export interface DataSourceConnection {
  host: string;
  port: number;
  username: string;
  password?: string;
  database?: string;
  schema?: string;
  // 额外连接参数
  params?: Record<string, string>;
}

export interface DataSource {
  source_id: string;
  name: string;
  description?: string;
  type: DataSourceType;
  connection: Omit<DataSourceConnection, 'password'>;
  status: 'connected' | 'disconnected' | 'error';
  last_connected?: string;
  last_error?: string;
  metadata?: {
    version?: string;
    tables_count?: number;
  };
  tags?: string[];
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateDataSourceRequest {
  name: string;
  description?: string;
  type: DataSourceType;
  connection: DataSourceConnection;
  tags?: string[];
}

export interface UpdateDataSourceRequest {
  name?: string;
  description?: string;
  connection?: Partial<DataSourceConnection>;
  tags?: string[];
}

export interface TestConnectionRequest {
  type: DataSourceType;
  connection: DataSourceConnection;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
  metadata?: {
    version?: string;
    tables_count?: number;
  };
}

// ============= ETL 类型 =============

export type ETLTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
export type ETLTaskType = 'batch' | 'streaming' | 'scheduled';

export interface ETLSource {
  type: 'database' | 'file' | 'api' | 'dataset';
  source_id?: string; // 数据源 ID 或数据集 ID
  table_name?: string;
  query?: string;
  file_path?: string;
  format?: string;
}

export interface ETLTarget {
  type: 'database' | 'file' | 'dataset';
  target_id?: string;
  table_name?: string;
  file_path?: string;
  format?: string;
  mode?: 'overwrite' | 'append' | 'merge';
}

export interface ETLTransform {
  type: 'sql' | 'python' | 'javascript';
  script?: string;
  operations?: Array<{
    type: 'filter' | 'map' | 'aggregate' | 'join' | 'window';
    config?: Record<string, unknown>;
  }>;
}

export interface ETLSchedule {
  type: 'cron' | 'interval' | 'once';
  expression?: string; // cron 表达式或间隔
  start_time?: string;
  end_time?: string;
  timezone?: string;
}

export interface ETLTask {
  task_id: string;
  name: string;
  description?: string;
  type: ETLTaskType;
  status: ETLTaskStatus;
  source: ETLSource;
  target: ETLTarget;
  transform?: ETLTransform;
  schedule?: ETLSchedule;
  last_run?: string;
  next_run?: string;
  last_run_status?: ETLTaskStatus;
  statistics?: {
    total_runs: number;
    success_runs: number;
    failed_runs: number;
    last_duration_ms?: number;
    avg_duration_ms?: number;
    rows_processed?: number;
    bytes_processed?: number;
  };
  tags?: string[];
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateETLTaskRequest {
  name: string;
  description?: string;
  type: ETLTaskType;
  source: ETLSource;
  target: ETLTarget;
  transform?: ETLTransform;
  schedule?: ETLSchedule;
  tags?: string[];
}

export interface UpdateETLTaskRequest {
  name?: string;
  description?: string;
  source?: ETLSource;
  target?: ETLTarget;
  transform?: ETLTransform;
  schedule?: ETLSchedule;
  tags?: string[];
  enabled?: boolean;
}

export interface ETLTaskListParams {
  status?: ETLTaskStatus;
  type?: ETLTaskType;
  page?: number;
  page_size?: number;
}

export interface ETLTaskListResponse {
  tasks: ETLTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface ETLExecutionLog {
  execution_id: string;
  task_id: string;
  task_name: string;
  status: ETLTaskStatus;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  rows_processed?: number;
  bytes_processed?: number;
  error?: string;
  logs?: string;
}

// ============= 数据源 API =============

/**
 * 获取数据源列表
 */
export async function getDataSources(params?: { type?: DataSourceType; status?: string; page?: number; page_size?: number }): Promise<ApiResponse<{ sources: DataSource[]; total: number }>> {
  return apiClient.get('/api/v1/datasources', { params });
}

/**
 * 获取数据源详情
 */
export async function getDataSource(sourceId: string): Promise<ApiResponse<DataSource>> {
  return apiClient.get(`/api/v1/datasources/${sourceId}`);
}

/**
 * 创建数据源
 */
export async function createDataSource(data: CreateDataSourceRequest): Promise<ApiResponse<{ source_id: string }>> {
  return apiClient.post('/api/v1/datasources', data);
}

/**
 * 更新数据源
 */
export async function updateDataSource(sourceId: string, data: UpdateDataSourceRequest): Promise<ApiResponse<DataSource>> {
  return apiClient.put(`/api/v1/datasources/${sourceId}`, data);
}

/**
 * 删除数据源
 */
export async function deleteDataSource(sourceId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/datasources/${sourceId}`);
}

/**
 * 测试数据源连接
 */
export async function testDataSource(data: TestConnectionRequest): Promise<ApiResponse<TestConnectionResponse>> {
  return apiClient.post('/api/v1/datasources/test', data);
}

// ============= ETL API =============

/**
 * 获取 ETL 任务列表
 */
export async function getETLTasks(params?: ETLTaskListParams): Promise<ApiResponse<ETLTaskListResponse>> {
  return apiClient.get('/api/v1/etl/tasks', { params });
}

/**
 * 获取 ETL 任务详情
 */
export async function getETLTask(taskId: string): Promise<ApiResponse<ETLTask>> {
  return apiClient.get(`/api/v1/etl/tasks/${taskId}`);
}

/**
 * 创建 ETL 任务
 */
export async function createETLTask(data: CreateETLTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/etl/tasks', data);
}

/**
 * 更新 ETL 任务
 */
export async function updateETLTask(taskId: string, data: UpdateETLTaskRequest): Promise<ApiResponse<ETLTask>> {
  return apiClient.put(`/api/v1/etl/tasks/${taskId}`, data);
}

/**
 * 删除 ETL 任务
 */
export async function deleteETLTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/etl/tasks/${taskId}`);
}

/**
 * 启动 ETL 任务
 */
export async function startETLTask(taskId: string): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/etl/tasks/${taskId}/start`);
}

/**
 * 停止 ETL 任务
 */
export async function stopETLTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/etl/tasks/${taskId}/stop`);
}

/**
 * 获取 ETL 任务日志
 */
export async function getETLTaskLogs(taskId: string, executionId?: string, limit = 100): Promise<ApiResponse<{ logs: ETLExecutionLog[] }>> {
  return apiClient.get(`/api/v1/etl/tasks/${taskId}/logs`, { params: { execution_id, limit } });
}

// ============= 数据质量类型 =============

export type QualityDimension = 'completeness' | 'accuracy' | 'consistency' | 'timeliness' | 'validity' | 'uniqueness';
export type QualityRuleType = 'null_check' | 'range_check' | 'regex_check' | 'enum_check' | 'foreign_key_check' | 'custom_sql' | 'duplicate_check';
export type QualityTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'disabled';
export type AlertChannel = 'email' | 'webhook' | 'dingtalk' | 'feishu' | 'wechat';

export interface QualityRule {
  rule_id: string;
  name: string;
  description?: string;
  dimension: QualityDimension;
  rule_type: QualityRuleType;
  table_name: string;
  column_name?: string;
  config: {
    min_value?: number;
    max_value?: number;
    regex_pattern?: string;
    allowed_values?: string[];
    custom_sql?: string;
    threshold_percentage?: number;
    reference_table?: string;
    reference_column?: string;
  };
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateQualityRuleRequest {
  name: string;
  description?: string;
  dimension: QualityDimension;
  rule_type: QualityRuleType;
  table_name: string;
  column_name?: string;
  config: {
    min_value?: number;
    max_value?: number;
    regex_pattern?: string;
    allowed_values?: string[];
    custom_sql?: string;
    threshold_percentage?: number;
    reference_table?: string;
    reference_column?: string;
  };
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface UpdateQualityRuleRequest {
  name?: string;
  description?: string;
  config?: QualityRule['config'];
  severity?: 'low' | 'medium' | 'high' | 'critical';
  enabled?: boolean;
}

export interface QualityCheckResult {
  check_id: string;
  rule_id: string;
  rule_name: string;
  table_name: string;
  status: 'passed' | 'failed' | 'warning';
  total_rows: number;
  passed_rows: number;
  failed_rows: number;
  pass_rate: number;
  failed_samples?: Array<{ row_id: string; reason: string }>;
  checked_at: string;
  duration_ms: number;
}

export interface QualityReport {
  report_id: string;
  report_name: string;
  tables_checked: number;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  warning_rules: number;
  overall_score: number;
  dimension_scores: Record<QualityDimension, number>;
  check_results: QualityCheckResult[];
  generated_at: string;
  period_start: string;
  period_end: string;
}

export interface QualityTask {
  task_id: string;
  name: string;
  description?: string;
  schedule?: ETLSchedule;
  status: QualityTaskStatus;
  last_run?: string;
  next_run?: string;
  rules: string[]; // rule_ids
  tables: string[];
  alert_enabled: boolean;
  last_report?: QualityReport;
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateQualityTaskRequest {
  name: string;
  description?: string;
  schedule?: ETLSchedule;
  rules: string[];
  tables: string[];
  alert_enabled: boolean;
}

export interface QualityAlert {
  alert_id: string;
  task_id: string;
  task_name: string;
  rule_id: string;
  rule_name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  status: 'active' | 'acknowledged' | 'resolved';
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  acknowledged_by?: string;
}

export interface AlertConfig {
  channels: AlertChannel[];
  email_recipients?: string[];
  webhook_url?: string;
  dingtalk_webhook?: string;
  feishu_webhook?: string;
  wechat_webhook?: string;
  alert_on_severity: Array<'low' | 'medium' | 'high' | 'critical'>;
}

// ============= 数据血缘类型 =============

export interface LineageNode {
  id: string;
  type: 'table' | 'view' | 'column' | 'etl_task' | 'dataset';
  name: string;
  schema?: string;
  database?: string;
  source_type?: string;
  properties?: Record<string, unknown>;
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  type: 'upstream' | 'downstream' | 'transform' | 'output';
  properties?: {
    transform_type?: string;
    column_mapping?: Record<string, string>;
  };
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  layout?: 'hierarchical' | 'force' | 'circular';
}

export interface ColumnLineage {
  column: string;
  table: string;
  source_columns: Array<{
    table: string;
    column: string;
    transform?: string;
  }>;
  target_columns: Array<{
    table: string;
    column: string;
    transform?: string;
  }>;
}

export interface ImpactAnalysis {
  table_name: string;
  impact_level: 'high' | 'medium' | 'low';
  upstream_count: number;
  downstream_count: number;
  affected_tables: Array<{
    table: string;
    distance: number;
    impact_type: string;
  }>;
  affected_reports: string[];
  affected_etl_tasks: string[];
}

// ============= 特征存储类型 =============

export interface Feature {
  feature_id: string;
  name: string;
  description?: string;
  feature_group: string;
  data_type: 'boolean' | 'integer' | 'float' | 'string' | 'array' | 'map';
  value_type: 'continuous' | 'categorical' | 'ordinal';
  source_table: string;
  source_column: string;
  transform_sql?: string;
  tags?: string[];
  metadata?: {
    domain?: string;
    category?: string;
    unit?: string;
    allowed_range?: [number, number];
  };
  status: 'active' | 'deprecated' | 'draft';
  version: number;
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface FeatureGroup {
  group_id: string;
  name: string;
  description?: string;
  source_table: string;
  join_keys?: string[];
  entity_columns?: string[];
  features: Feature[];
  status: 'active' | 'deprecated' | 'draft';
  created_at: string;
  updated_at?: string;
}

export interface FeatureSet {
  set_id: string;
  name: string;
  description?: string;
  feature_groups: Array<{
    group_id: string;
    group_name: string;
    join_key?: string;
  }>;
  labels?: string[];
  created_at: string;
  updated_at?: string;
}

export interface FeatureVersion {
  version_id: string;
  feature_id: string;
  feature_name: string;
  version: number;
  description?: string;
  transform_sql?: string;
  status: 'active' | 'deprecated';
  created_at: string;
  created_by: string;
}

export interface CreateFeatureRequest {
  name: string;
  description?: string;
  feature_group: string;
  data_type: 'boolean' | 'integer' | 'float' | 'string' | 'array' | 'map';
  value_type: 'continuous' | 'categorical' | 'ordinal';
  source_table: string;
  source_column: string;
  transform_sql?: string;
  tags?: string[];
  metadata?: {
    domain?: string;
    category?: string;
    unit?: string;
    allowed_range?: [number, number];
  };
}

export interface UpdateFeatureRequest {
  name?: string;
  description?: string;
  transform_sql?: string;
  tags?: string[];
  metadata?: Feature['metadata'];
  status?: 'active' | 'deprecated' | 'draft';
}

export interface CreateFeatureGroupRequest {
  name: string;
  description?: string;
  source_table: string;
  join_keys?: string[];
  entity_columns?: string[];
}

export interface FeatureService {
  service_id: string;
  name: string;
  feature_set_id: string;
  endpoint: string;
  status: 'running' | 'stopped' | 'error';
  features: Array<{
    feature_id: string;
    feature_name: string;
    feature_group: string;
  }>;
  qps: number;
  avg_latency_ms: number;
  created_at: string;
  updated_at?: string;
}

// ============= 质量监控 API =============

/**
 * 获取质量规则列表
 */
export async function getQualityRules(params?: {
  table_name?: string;
  dimension?: QualityDimension;
  enabled?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ rules: QualityRule[]; total: number }>> {
  return apiClient.get('/api/v1/quality/rules', { params });
}

/**
 * 获取质量规则详情
 */
export async function getQualityRule(ruleId: string): Promise<ApiResponse<QualityRule>> {
  return apiClient.get(`/api/v1/quality/rules/${ruleId}`);
}

/**
 * 创建质量规则
 */
export async function createQualityRule(data: CreateQualityRuleRequest): Promise<ApiResponse<{ rule_id: string }>> {
  return apiClient.post('/api/v1/quality/rules', data);
}

/**
 * 更新质量规则
 */
export async function updateQualityRule(ruleId: string, data: UpdateQualityRuleRequest): Promise<ApiResponse<QualityRule>> {
  return apiClient.put(`/api/v1/quality/rules/${ruleId}`, data);
}

/**
 * 删除质量规则
 */
export async function deleteQualityRule(ruleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/quality/rules/${ruleId}`);
}

/**
 * 获取质量检查结果
 */
export async function getQualityResults(params?: {
  table_name?: string;
  rule_id?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ results: QualityCheckResult[]; total: number }>> {
  return apiClient.get('/api/v1/quality/results', { params });
}

/**
 * 手动执行质量检查
 */
export async function runQualityCheck(ruleIds: string[]): Promise<ApiResponse<{ check_id: string; status: string }>> {
  return apiClient.post('/api/v1/quality/checks/run', { rule_ids: ruleIds });
}

/**
 * 获取质量报告列表
 */
export async function getQualityReports(params?: {
  table_name?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ reports: QualityReport[]; total: number }>> {
  return apiClient.get('/api/v1/quality/reports', { params });
}

/**
 * 获取质量报告详情
 */
export async function getQualityReport(reportId: string): Promise<ApiResponse<QualityReport>> {
  return apiClient.get(`/api/v1/quality/reports/${reportId}`);
}

/**
 * 获取质量任务列表
 */
export async function getQualityTasks(params?: {
  status?: QualityTaskStatus;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: QualityTask[]; total: number }>> {
  return apiClient.get('/api/v1/quality/tasks', { params });
}

/**
 * 获取质量任务详情
 */
export async function getQualityTask(taskId: string): Promise<ApiResponse<QualityTask>> {
  return apiClient.get(`/api/v1/quality/tasks/${taskId}`);
}

/**
 * 创建质量任务
 */
export async function createQualityTask(data: CreateQualityTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/quality/tasks', data);
}

/**
 * 更新质量任务
 */
export async function updateQualityTask(taskId: string, data: Partial<CreateQualityTaskRequest>): Promise<ApiResponse<QualityTask>> {
  return apiClient.put(`/api/v1/quality/tasks/${taskId}`, data);
}

/**
 * 删除质量任务
 */
export async function deleteQualityTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/quality/tasks/${taskId}`);
}

/**
 * 启动质量任务
 */
export async function startQualityTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/quality/tasks/${taskId}/start`);
}

/**
 * 停止质量任务
 */
export async function stopQualityTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/quality/tasks/${taskId}/stop`);
}

/**
 * 获取告警列表
 */
export async function getQualityAlerts(params?: {
  status?: string;
  severity?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ alerts: QualityAlert[]; total: number }>> {
  return apiClient.get('/api/v1/quality/alerts', { params });
}

/**
 * 确认告警
 */
export async function acknowledgeAlert(alertId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/quality/alerts/${alertId}/acknowledge`);
}

/**
 * 解决告警
 */
export async function resolveAlert(alertId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/quality/alerts/${alertId}/resolve`);
}

/**
 * 获取告警配置
 */
export async function getAlertConfig(): Promise<ApiResponse<AlertConfig>> {
  return apiClient.get('/api/v1/quality/alerts/config');
}

/**
 * 更新告警配置
 */
export async function updateAlertConfig(data: AlertConfig): Promise<ApiResponse<AlertConfig>> {
  return apiClient.put('/api/v1/quality/alerts/config', data);
}

/**
 * 获取质量分数趋势
 */
export async function getQualityTrend(params?: {
  table_name?: string;
  dimension?: QualityDimension;
  period?: string; // daily, weekly, monthly
  start_time?: string;
  end_time?: string;
}): Promise<ApiResponse<{
  trend_points: Array<{
    date: string;
    score: number;
    passed_rules: number;
    total_rules: number;
  }>;
}>> {
  return apiClient.get('/api/v1/quality/trends', { params });
}

// ============= 数据血缘 API =============

/**
 * 获取表级血缘图
 */
export async function getTableLineage(tableName: string, depth = 2): Promise<ApiResponse<LineageGraph>> {
  return apiClient.get('/api/v1/lineage/table', {
    params: { table_name: tableName, depth },
  });
}

/**
 * 获取字段级血缘
 */
export async function getColumnLineage(tableName: string, columnName: string): Promise<ApiResponse<ColumnLineage>> {
  return apiClient.get('/api/v1/lineage/column', {
    params: { table_name: tableName, column_name: columnName },
  });
}

/**
 * 获取影响分析
 */
export async function getImpactAnalysis(tableName: string): Promise<ApiResponse<ImpactAnalysis>> {
  return apiClient.get('/api/v1/lineage/impact', {
    params: { table_name: tableName },
  });
}

/**
 * 搜索血缘关系
 */
export async function searchLineage(query: string, type?: 'table' | 'column'): Promise<ApiResponse<{
  results: Array<{
    table: string;
    column?: string;
    match_type: string;
    upstream_count: number;
    downstream_count: number;
  }>;
}>> {
  return apiClient.get('/api/v1/lineage/search', {
    params: { query, type },
  });
}

/**
 * 获取 ETL 任务血缘
 */
export async function getETLLineage(taskId: string): Promise<ApiResponse<LineageGraph>> {
  return apiClient.get(`/api/v1/lineage/etl/${taskId}`);
}

/**
 * 获取完整血缘路径
 */
export async function getLineagePath(sourceTable: string, targetTable: string): Promise<ApiResponse<{
  path: Array<{
    type: 'table' | 'etl_task';
    name: string;
    id: string;
  }>;
}>> {
  return apiClient.get('/api/v1/lineage/path', {
    params: { source: sourceTable, target: targetTable },
  });
}

// ============= 数据标准类型 =============

export interface StandardLibrary {
  library_id: string;
  name: string;
  description?: string;
  category?: string;
  word_count: number;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateStandardLibraryRequest {
  name: string;
  description?: string;
  category?: string;
}

export interface DataElement {
  element_id: string;
  name: string;
  code: string;
  data_type: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'datetime' | 'decimal';
  length?: number;
  precision?: number;
  scale?: number;
  description?: string;
  standard_value?: string;
  library_id?: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateDataElementRequest {
  name: string;
  code: string;
  data_type: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'datetime' | 'decimal';
  length?: number;
  precision?: number;
  scale?: number;
  description?: string;
  standard_value?: string;
  library_id?: string;
  tags?: string[];
}

export interface StandardDocument {
  doc_id: string;
  name: string;
  version: string;
  type: 'dictionary' | 'rule' | 'spec' | 'manual';
  status: 'draft' | 'published' | 'deprecated';
  file_url?: string;
  content?: string;
  description?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  published_at?: string;
}

export interface CreateStandardDocumentRequest {
  name: string;
  version: string;
  type: 'dictionary' | 'rule' | 'spec' | 'manual';
  file_url?: string;
  content?: string;
  description?: string;
}

export interface StandardMapping {
  mapping_id: string;
  name: string;
  source_table: string;
  source_column: string;
  target_element_id: string;
  target_element_name: string;
  transform_rule?: string;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at?: string;
}

// ============= 数据资产类型 =============

export interface DataAsset {
  asset_id: string;
  name: string;
  type: 'database' | 'table' | 'column' | 'view';
  parent_id?: string;
  path: string;
  description?: string;
  owner?: string;
  department?: string;
  tags?: string[];
  sensitivity_level: 'public' | 'internal' | 'confidential' | 'restricted';
  quality_score?: number;
  access_heat?: number;
  row_count?: number;
  last_updated?: string;
  last_accessed?: string;
  created_at: string;
}

export interface AssetProfile {
  asset_id: string;
  basic_info: {
    name: string;
    type: string;
    owner: string;
    department: string;
    description: string;
  };
  statistics: {
    row_count: number;
    size_bytes: number;
    column_count: number;
    access_count: number;
    access_heat: number;
  };
  quality: {
    score: number;
    completeness: number;
    accuracy: number;
    consistency: number;
    timeliness: number;
  };
  lineage: {
    upstream_count: number;
    downstream_count: number;
  };
  tags: string[];
  last_updated: string;
}

export interface AssetInventoryTask {
  task_id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  scope: string[];
  total_assets: number;
  scanned_assets: number;
  start_time?: string;
  end_time?: string;
  created_by: string;
  created_at: string;
}

// ============= 数据服务类型 =============

export interface DataService {
  service_id: string;
  name: string;
  description?: string;
  type: 'rest' | 'graphql';
  source_type: 'table' | 'query' | 'dataset';
  source_config: {
    database?: string;
    table?: string;
    query?: string;
    dataset_id?: string;
  };
  endpoint: string;
  status: 'published' | 'draft' | 'archived';
  api_key_count: number;
  statistics?: {
    total_calls: number;
    qps: number;
    avg_latency_ms: number;
    error_rate: number;
  };
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateDataServiceRequest {
  name: string;
  description?: string;
  type: 'rest' | 'graphql';
  source_type: 'table' | 'query' | 'dataset';
  source_config: {
    database?: string;
    table?: string;
    query?: string;
    dataset_id?: string;
  };
}

export interface ApiKeyInfo {
  key_id: string;
  key_display: string;
  created_at: string;
  last_used?: string;
  access_count: number;
  is_active: boolean;
}

export interface ServiceStatistics {
  service_id: string;
  period_start: string;
  period_end: string;
  total_calls: number;
  success_calls: number;
  error_calls: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  qps: number;
  peak_qps: number;
  daily_stats: Array<{
    date: string;
    calls: number;
    errors: number;
    avg_latency_ms: number;
  }>;
}

// ============= BI 报表类型 =============

export interface Report {
  report_id: string;
  name: string;
  description?: string;
  type: 'dashboard' | 'chart' | 'table';
  status: 'draft' | 'published';
  dataset_id?: string;
  config?: ReportWidgetConfig[];
  layout?: {
    columns: number;
    rows: number;
  };
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ReportWidgetConfig {
  widget_id: string;
  type: 'line' | 'bar' | 'pie' | 'table' | 'card' | 'gauge';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  data_config: {
    dataset_id?: string;
    sql?: string;
    dimensions?: string[];
    metrics?: string[];
    filters?: Array<{ field: string; operator: string; value: unknown }>;
  };
  style_config?: Record<string, unknown>;
}

export interface CreateReportRequest {
  name: string;
  description?: string;
  type: 'dashboard' | 'chart' | 'table';
  dataset_id?: string;
  config?: ReportWidgetConfig[];
  layout?: {
    columns: number;
    rows: number;
  };
  tags?: string[];
}

export interface DashboardView {
  dashboard_id: string;
  name: string;
  description?: string;
  widgets: ReportWidgetConfig[];
  refresh_interval?: number;
  created_at: string;
}

// ============= 实时计算类型 =============

export interface FlinkJob {
  job_id: string;
  name: string;
  description?: string;
  type: 'sql' | 'jar';
  status: 'running' | 'stopped' | 'failed' | 'starting';
  parallelism: number;
  checkpoint_interval: number;
  source_config: {
    type: string;
    config: Record<string, unknown>;
  };
  sink_config: {
    type: string;
    config: Record<string, unknown>;
  };
  sql?: string;
  jar_uri?: string;
  statistics?: {
    records_in: number;
    records_out: number;
    bytes_in: number;
    bytes_out: number;
    lag_ms: number;
  };
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateFlinkJobRequest {
  name: string;
  description?: string;
  type: 'sql' | 'jar';
  parallelism: number;
  checkpoint_interval: number;
  source_config: {
    type: string;
    config: Record<string, unknown>;
  };
  sink_config: {
    type: string;
    config: Record<string, unknown>;
  };
  sql?: string;
  jar_uri?: string;
}

export interface FlinkJobStatistics {
  job_id: string;
  timestamp: string;
  metrics: {
    records_in_per_second: number;
    records_out_per_second: number;
    bytes_in_per_second: number;
    bytes_out_per_second: number;
    lag_ms: number;
    checkpoint_duration_ms: number;
    checkpoint_count: number;
  };
}

// ============= 离线开发类型 =============

export interface OfflineWorkflow {
  workflow_id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'draft';
  schedule?: {
    type: 'cron' | 'interval';
    expression: string;
  };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface WorkflowNode {
  node_id: string;
  name: string;
  type: 'sql' | 'shell' | 'python' | 'spark' | 'data_quality';
  config: {
    script?: string;
    sql?: string;
    parameters?: Record<string, unknown>;
    dependencies?: string[];
    timeout?: number;
    retry_count?: number;
  };
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  edge_id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface CreateOfflineWorkflowRequest {
  name: string;
  description?: string;
  schedule?: {
    type: 'cron' | 'interval';
    expression: string;
  };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables?: Record<string, unknown>;
}

export interface WorkflowExecution {
  execution_id: string;
  workflow_id: string;
  workflow_name: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  node_statuses: Array<{
    node_id: string;
    node_name: string;
    status: string;
    start_time?: string;
    end_time?: string;
  }>;
  triggered_by: string;
}

// ============= 系统监控类型 =============

export interface MonitoringMetric {
  metric_id: string;
  name: string;
  value: number;
  unit: string;
  timestamp: string;
  labels?: Record<string, string>;
}

export interface TaskMetrics {
  task_id: string;
  task_name: string;
  task_type: 'etl' | 'quality' | 'workflow';
  status: 'running' | 'success' | 'failed';
  start_time: string;
  duration_ms?: number;
  rows_processed?: number;
  bytes_processed?: number;
  error_message?: string;
}

export interface AlertRule {
  rule_id: string;
  name: string;
  metric: string;
  condition: 'greater_than' | 'less_than' | 'equal_to';
  threshold: number;
  severity: 'info' | 'warning' | 'error' | 'critical';
  enabled: boolean;
  notification_channels: string[];
  created_at: string;
}

export interface Alert {
  alert_id: string;
  rule_id: string;
  rule_name: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  metric_value: number;
  threshold: number;
  status: 'active' | 'acknowledged' | 'resolved';
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

// ============= 数据标准 API =============

/**
 * 获取词根库列表
 */
export async function getStandardLibraries(params?: {
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ libraries: StandardLibrary[]; total: number }>> {
  return apiClient.get('/api/v1/standards/libraries', { params });
}

/**
 * 创建词根库
 */
export async function createStandardLibrary(data: CreateStandardLibraryRequest): Promise<ApiResponse<{ library_id: string }>> {
  return apiClient.post('/api/v1/standards/libraries', data);
}

/**
 * 删除词根库
 */
export async function deleteStandardLibrary(libraryId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/standards/libraries/${libraryId}`);
}

/**
 * 获取数据元列表
 */
export async function getDataElements(params?: {
  library_id?: string;
  data_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ elements: DataElement[]; total: number }>> {
  return apiClient.get('/api/v1/standards/elements', { params });
}

/**
 * 创建数据元
 */
export async function createDataElement(data: CreateDataElementRequest): Promise<ApiResponse<{ element_id: string }>> {
  return apiClient.post('/api/v1/standards/elements', data);
}

/**
 * 更新数据元
 */
export async function updateDataElement(elementId: string, data: Partial<CreateDataElementRequest>): Promise<ApiResponse<DataElement>> {
  return apiClient.put(`/api/v1/standards/elements/${elementId}`, data);
}

/**
 * 删除数据元
 */
export async function deleteDataElement(elementId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/standards/elements/${elementId}`);
}

/**
 * 获取标准文档列表
 */
export async function getStandardDocuments(params?: {
  type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ documents: StandardDocument[]; total: number }>> {
  return apiClient.get('/api/v1/standards/documents', { params });
}

/**
 * 创建标准文档
 */
export async function createStandardDocument(data: CreateStandardDocumentRequest): Promise<ApiResponse<{ doc_id: string }>> {
  return apiClient.post('/api/v1/standards/documents', data);
}

/**
 * 删除标准文档
 */
export async function deleteStandardDocument(docId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/standards/documents/${docId}`);
}

/**
 * 获取标准映射列表
 */
export async function getStandardMappings(params?: {
  source_table?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ mappings: StandardMapping[]; total: number }>> {
  return apiClient.get('/api/v1/standards/mappings', { params });
}

/**
 * 创建标准映射
 */
export async function createStandardMapping(data: {
  name: string;
  source_table: string;
  source_column: string;
  target_element_id: string;
  transform_rule?: string;
}): Promise<ApiResponse<{ mapping_id: string }>> {
  return apiClient.post('/api/v1/standards/mappings', data);
}

/**
 * 删除标准映射
 */
export async function deleteStandardMapping(mappingId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/standards/mappings/${mappingId}`);
}

// ============= 数据资产 API =============

/**
 * 获取资产列表
 */
export async function getDataAssets(params?: {
  type?: string;
  parent_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ assets: DataAsset[]; total: number }>> {
  return apiClient.get('/api/v1/assets', { params });
}

/**
 * 获取资产详情
 */
export async function getDataAsset(assetId: string): Promise<ApiResponse<AssetProfile>> {
  return apiClient.get(`/api/v1/assets/${assetId}`);
}

/**
 * 获取资产树
 */
export async function getAssetTree(): Promise<ApiResponse<{ nodes: DataAsset[] }>> {
  return apiClient.get('/api/v1/assets/tree');
}

/**
 * 创建资产盘点任务
 */
export async function createAssetInventory(data: {
  name: string;
  scope: string[];
}): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/assets/inventory', data);
}

/**
 * 获取盘点任务列表
 */
export async function getAssetInventories(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: AssetInventoryTask[]; total: number }>> {
  return apiClient.get('/api/v1/assets/inventory', { params });
}

/**
 * 更新资产标签
 */
export async function updateAssetTags(assetId: string, tags: string[]): Promise<ApiResponse<void>> {
  return apiClient.put(`/api/v1/assets/${assetId}/tags`, { tags });
}

// ============= 数据服务 API =============

/**
 * 获取服务列表
 */
export async function getDataServices(params?: {
  type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ services: DataService[]; total: number }>> {
  return apiClient.get('/api/v1/services', { params });
}

/**
 * 获取服务详情
 */
export async function getDataService(serviceId: string): Promise<ApiResponse<DataService>> {
  return apiClient.get(`/api/v1/services/${serviceId}`);
}

/**
 * 创建服务
 */
export async function createDataService(data: CreateDataServiceRequest): Promise<ApiResponse<{ service_id: string; endpoint: string }>> {
  return apiClient.post('/api/v1/services', data);
}

/**
 * 更新服务
 */
export async function updateDataService(serviceId: string, data: Partial<CreateDataServiceRequest>): Promise<ApiResponse<DataService>> {
  return apiClient.put(`/api/v1/services/${serviceId}`, data);
}

/**
 * 删除服务
 */
export async function deleteDataService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/services/${serviceId}`);
}

/**
 * 发布服务
 */
export async function publishDataService(serviceId: string): Promise<ApiResponse<{ endpoint: string }>> {
  return apiClient.post(`/api/v1/services/${serviceId}/publish`);
}

/**
 * 下线服务
 */
export async function unpublishDataService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/services/${serviceId}/unpublish`);
}

/**
 * 获取服务 API 密钥
 */
export async function getServiceApiKeys(serviceId: string): Promise<ApiResponse<{ api_keys: ApiKeyInfo[] }>> {
  return apiClient.get(`/api/v1/services/${serviceId}/api-keys`);
}

/**
 * 创建 API 密钥
 */
export async function createServiceApiKey(serviceId: string): Promise<ApiResponse<{ key_id: string; key: string }>> {
  return apiClient.post(`/api/v1/services/${serviceId}/api-keys`);
}

/**
 * 删除 API 密钥
 */
export async function deleteServiceApiKey(serviceId: string, keyId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/services/${serviceId}/api-keys/${keyId}`);
}

/**
 * 获取服务统计
 */
export async function getDataServiceStatistics(serviceId: string, params?: {
  period_start?: string;
  period_end?: string;
}): Promise<ApiResponse<ServiceStatistics>> {
  return apiClient.get(`/api/v1/services/${serviceId}/statistics`, { params });
}

// ============= BI 报表 API =============

/**
 * 获取报表列表
 */
export async function getReports(params?: {
  type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ reports: Report[]; total: number }>> {
  return apiClient.get('/api/v1/bi/reports', { params });
}

/**
 * 获取报表详情
 */
export async function getReport(reportId: string): Promise<ApiResponse<DashboardView>> {
  return apiClient.get(`/api/v1/bi/reports/${reportId}`);
}

/**
 * 创建报表
 */
export async function createReport(data: CreateReportRequest): Promise<ApiResponse<{ report_id: string }>> {
  return apiClient.post('/api/v1/bi/reports', data);
}

/**
 * 更新报表
 */
export async function updateReport(reportId: string, data: Partial<CreateReportRequest>): Promise<ApiResponse<Report>> {
  return apiClient.put(`/api/v1/bi/reports/${reportId}`, data);
}

/**
 * 删除报表
 */
export async function deleteReport(reportId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/bi/reports/${reportId}`);
}

/**
 * 获取报表数据
 */
export async function getReportData(reportId: string): Promise<ApiResponse<{ data: unknown }>> {
  return apiClient.get(`/api/v1/bi/reports/${reportId}/data`);
}

/**
 * 执行报表查询
 */
export async function executeReportQuery(config: {
  dataset_id?: string;
  sql?: string;
  dimensions?: string[];
  metrics?: string[];
  filters?: Array<{ field: string; operator: string; value: unknown }>;
}): Promise<ApiResponse<{ rows: Record<string, unknown>[]; columns: string[] }>> {
  return apiClient.post('/api/v1/bi/query', config);
}

// ============= 实时计算 API =============

/**
 * 获取 Flink 作业列表
 */
export async function getFlinkJobs(params?: {
  status?: string;
  type?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ jobs: FlinkJob[]; total: number }>> {
  return apiClient.get('/api/v1/streaming/jobs', { params });
}

/**
 * 获取 Flink 作业详情
 */
export async function getFlinkJob(jobId: string): Promise<ApiResponse<FlinkJob>> {
  return apiClient.get(`/api/v1/streaming/jobs/${jobId}`);
}

/**
 * 创建 Flink 作业
 */
export async function createFlinkJob(data: CreateFlinkJobRequest): Promise<ApiResponse<{ job_id: string }>> {
  return apiClient.post('/api/v1/streaming/jobs', data);
}

/**
 * 更新 Flink 作业
 */
export async function updateFlinkJob(jobId: string, data: Partial<CreateFlinkJobRequest>): Promise<ApiResponse<FlinkJob>> {
  return apiClient.put(`/api/v1/streaming/jobs/${jobId}`, data);
}

/**
 * 删除 Flink 作业
 */
export async function deleteFlinkJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/streaming/jobs/${jobId}`);
}

/**
 * 启动 Flink 作业
 */
export async function startFlinkJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/streaming/jobs/${jobId}/start`);
}

/**
 * 停止 Flink 作业
 */
export async function stopFlinkJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/streaming/jobs/${jobId}/stop`);
}

/**
 * 获取 Flink 作业统计
 */
export async function getFlinkJobStatistics(jobId: string): Promise<ApiResponse<FlinkJobStatistics>> {
  return apiClient.get(`/api/v1/streaming/jobs/${jobId}/statistics`);
}

/**
 * 获取 Flink 作业日志
 */
export async function getFlinkJobLogs(jobId: string, params?: {
  limit?: number;
  offset?: number;
}): Promise<ApiResponse<{ logs: string[] }>> {
  return apiClient.get(`/api/v1/streaming/jobs/${jobId}/logs`, { params });
}

/**
 * 验证 Flink SQL
 */
export async function validateFlinkSql(sql: string): Promise<ApiResponse<{ valid: boolean; errors?: string[] }>> {
  return apiClient.post('/api/v1/streaming/validate-sql', { sql });
}

// ============= 离线开发 API =============

/**
 * 获取离线工作流列表
 */
export async function getOfflineWorkflows(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ workflows: OfflineWorkflow[]; total: number }>> {
  return apiClient.get('/api/v1/offline/workflows', { params });
}

/**
 * 获取离线工作流详情
 */
export async function getOfflineWorkflow(workflowId: string): Promise<ApiResponse<OfflineWorkflow>> {
  return apiClient.get(`/api/v1/offline/workflows/${workflowId}`);
}

/**
 * 创建离线工作流
 */
export async function createOfflineWorkflow(data: CreateOfflineWorkflowRequest): Promise<ApiResponse<{ workflow_id: string }>> {
  return apiClient.post('/api/v1/offline/workflows', data);
}

/**
 * 更新离线工作流
 */
export async function updateOfflineWorkflow(workflowId: string, data: Partial<CreateOfflineWorkflowRequest>): Promise<ApiResponse<OfflineWorkflow>> {
  return apiClient.put(`/api/v1/offline/workflows/${workflowId}`, data);
}

/**
 * 删除离线工作流
 */
export async function deleteOfflineWorkflow(workflowId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/offline/workflows/${workflowId}`);
}

/**
 * 执行工作流
 */
export async function executeOfflineWorkflow(workflowId: string, variables?: Record<string, unknown>): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/offline/workflows/${workflowId}/execute`, { variables });
}

/**
 * 获取执行记录
 */
export async function getWorkflowExecutions(workflowId: string, params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ executions: WorkflowExecution[]; total: number }>> {
  return apiClient.get(`/api/v1/offline/workflows/${workflowId}/executions`, { params });
}

/**
 * 获取执行详情
 */
export async function getWorkflowExecution(executionId: string): Promise<ApiResponse<WorkflowExecution>> {
  return apiClient.get(`/api/v1/offline/executions/${executionId}`);
}

/**
 * 取消执行
 */
export async function cancelWorkflowExecution(executionId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/offline/executions/${executionId}/cancel`);
}

// ============= 系统监控 API =============

/**
 * 获取任务指标
 */
export async function getTaskMetrics(params?: {
  task_type?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
}): Promise<ApiResponse<{ metrics: TaskMetrics[] }>> {
  return apiClient.get('/api/v1/monitoring/tasks', { params });
}

/**
 * 获取系统指标概览
 */
export async function getMonitoringOverview(): Promise<ApiResponse<{
  total_tasks: number;
  running_tasks: number;
  failed_tasks: number;
  success_rate: number;
  total_data_processed: number;
  avg_latency_ms: number;
}>> {
  return apiClient.get('/api/v1/monitoring/overview');
}

/**
 * 获取告警规则列表
 */
export async function getAlertRules(params?: {
  enabled?: boolean;
  severity?: string;
}): Promise<ApiResponse<{ rules: AlertRule[] }>> {
  return apiClient.get('/api/v1/monitoring/alert-rules', { params });
}

/**
 * 创建告警规则
 */
export async function createAlertRule(data: {
  name: string;
  metric: string;
  condition: 'greater_than' | 'less_than' | 'equal_to';
  threshold: number;
  severity: 'info' | 'warning' | 'error' | 'critical';
  notification_channels: string[];
}): Promise<ApiResponse<{ rule_id: string }>> {
  return apiClient.post('/api/v1/monitoring/alert-rules', data);
}

/**
 * 更新告警规则
 */
export async function updateAlertRule(ruleId: string, data: {
  enabled?: boolean;
  threshold?: number;
}): Promise<ApiResponse<AlertRule>> {
  return apiClient.put(`/api/v1/monitoring/alert-rules/${ruleId}`, data);
}

/**
 * 删除告警规则
 */
export async function deleteAlertRule(ruleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/monitoring/alert-rules/${ruleId}`);
}

/**
 * 获取告警列表
 */
export async function getAlerts(params?: {
  severity?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ alerts: Alert[]; total: number }>> {
  return apiClient.get('/api/v1/monitoring/alerts', { params });
}

/**
 * 确认监控告警
 */
export async function acknowledgeMonitoringAlert(alertId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/monitoring/alerts/${alertId}/acknowledge`);
}

/**
 * 解决监控告警
 */
export async function resolveMonitoringAlert(alertId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/monitoring/alerts/${alertId}/resolve`);
}

// ============= 特征存储 API =============

/**
 * 获取特征列表
 */
export async function getFeatures(params?: {
  feature_group?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ features: Feature[]; total: number }>> {
  return apiClient.get('/api/v1/features', { params });
}

/**
 * 获取特征详情
 */
export async function getFeature(featureId: string): Promise<ApiResponse<Feature>> {
  return apiClient.get(`/api/v1/features/${featureId}`);
}

/**
 * 创建特征
 */
export async function createFeature(data: CreateFeatureRequest): Promise<ApiResponse<{ feature_id: string }>> {
  return apiClient.post('/api/v1/features', data);
}

/**
 * 更新特征
 */
export async function updateFeature(featureId: string, data: UpdateFeatureRequest): Promise<ApiResponse<Feature>> {
  return apiClient.put(`/api/v1/features/${featureId}`, data);
}

/**
 * 删除特征
 */
export async function deleteFeature(featureId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/features/${featureId}`);
}

/**
 * 获取特征版本列表
 */
export async function getFeatureVersions(featureId: string): Promise<ApiResponse<{ versions: FeatureVersion[] }>> {
  return apiClient.get(`/api/v1/features/${featureId}/versions`);
}

/**
 * 获取特征组列表
 */
export async function getFeatureGroups(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ groups: FeatureGroup[]; total: number }>> {
  return apiClient.get('/api/v1/feature-groups', { params });
}

/**
 * 获取特征组详情
 */
export async function getFeatureGroup(groupId: string): Promise<ApiResponse<FeatureGroup>> {
  return apiClient.get(`/api/v1/feature-groups/${groupId}`);
}

/**
 * 创建特征组
 */
export async function createFeatureGroup(data: CreateFeatureGroupRequest): Promise<ApiResponse<{ group_id: string }>> {
  return apiClient.post('/api/v1/feature-groups', data);
}

/**
 * 更新特征组
 */
export async function updateFeatureGroup(groupId: string, data: Partial<CreateFeatureGroupRequest>): Promise<ApiResponse<FeatureGroup>> {
  return apiClient.put(`/api/v1/feature-groups/${groupId}`, data);
}

/**
 * 删除特征组
 */
export async function deleteFeatureGroup(groupId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/feature-groups/${groupId}`);
}

/**
 * 获取特征集列表
 */
export async function getFeatureSets(params?: {
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ sets: FeatureSet[]; total: number }>> {
  return apiClient.get('/api/v1/feature-sets', { params });
}

/**
 * 获取特征集详情
 */
export async function getFeatureSet(setId: string): Promise<ApiResponse<FeatureSet>> {
  return apiClient.get(`/api/v1/feature-sets/${setId}`);
}

/**
 * 创建特征集
 */
export async function createFeatureSet(data: {
  name: string;
  description?: string;
  feature_groups: Array<{ group_id: string; join_key?: string }>;
  labels?: string[];
}): Promise<ApiResponse<{ set_id: string }>> {
  return apiClient.post('/api/v1/feature-sets', data);
}

/**
 * 获取特征服务列表
 */
export async function getFeatureServices(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ services: FeatureService[]; total: number }>> {
  return apiClient.get('/api/v1/feature-services', { params });
}

/**
 * 获取特征服务详情
 */
export async function getFeatureService(serviceId: string): Promise<ApiResponse<FeatureService>> {
  return apiClient.get(`/api/v1/feature-services/${serviceId}`);
}

/**
 * 创建特征服务
 */
export async function createFeatureService(data: {
  name: string;
  feature_set_id: string;
}): Promise<ApiResponse<{ service_id: string; endpoint: string }>> {
  return apiClient.post('/api/v1/feature-services', data);
}

/**
 * 删除特征服务
 */
export async function deleteFeatureService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/feature-services/${serviceId}`);
}

// ============= 指标体系类型 =============

export type MetricCategory = 'business' | 'technical' | 'quality';
export type MetricValueType = 'absolute' | 'percentage' | 'rate' | 'duration';
export type MetricAggregation = 'sum' | 'avg' | 'min' | 'max' | 'count' | 'distinct';
export type MetricCalculationStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Metric {
  metric_id: string;
  name: string;
  code: string;
  description?: string;
  category: MetricCategory;
  value_type: MetricValueType;
  unit?: string;
  formula?: string;
  source_table: string;
  source_column?: string;
  dimensions?: string[];
  filters?: Record<string, unknown>;
  aggregation: MetricAggregation;
  tags?: string[];
  owner?: string;
  department?: string;
  status: 'active' | 'deprecated' | 'draft';
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateMetricRequest {
  name: string;
  code: string;
  description?: string;
  category: MetricCategory;
  value_type: MetricValueType;
  unit?: string;
  formula?: string;
  source_table: string;
  source_column?: string;
  dimensions?: string[];
  filters?: Record<string, unknown>;
  aggregation: MetricAggregation;
  tags?: string[];
  owner?: string;
  department?: string;
}

export interface UpdateMetricRequest {
  name?: string;
  description?: string;
  formula?: string;
  source_table?: string;
  source_column?: string;
  dimensions?: string[];
  filters?: Record<string, unknown>;
  tags?: string[];
  owner?: string;
  department?: string;
  status?: 'active' | 'deprecated' | 'draft';
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
  dimensions?: Record<string, string>;
}

export interface MetricValue {
  metric_id: string;
  metric_name: string;
  metric_code: string;
  value: number;
  unit?: string;
  timestamp: string;
  dimensions?: Record<string, string>;
}

export interface MetricCalculationTask {
  task_id: string;
  name: string;
  metric_ids: string[];
  schedule?: ETLSchedule;
  status: MetricCalculationStatus;
  last_run?: string;
  next_run?: string;
  last_run_status?: MetricCalculationStatus;
  statistics?: {
    total_runs: number;
    success_runs: number;
    failed_runs: number;
    avg_duration_ms?: number;
  };
  created_at: string;
  updated_at?: string;
  created_by: string;
}

export interface CreateMetricCalculationTaskRequest {
  name: string;
  metric_ids: string[];
  schedule?: ETLSchedule;
}

export interface MetricTrendData {
  metric_id: string;
  metric_name: string;
  data_points: MetricDataPoint[];
  aggregation?: MetricAggregation;
  period?: string; // hourly, daily, weekly, monthly
}

// ============= 指标体系 API =============

/**
 * 获取指标列表
 */
export async function getMetrics(params?: {
  category?: MetricCategory;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ metrics: Metric[]; total: number }>> {
  return apiClient.get('/api/v1/metrics', { params });
}

/**
 * 获取指标详情
 */
export async function getMetric(metricId: string): Promise<ApiResponse<Metric>> {
  return apiClient.get(`/api/v1/metrics/${metricId}`);
}

/**
 * 创建指标
 */
export async function createMetric(data: CreateMetricRequest): Promise<ApiResponse<{ metric_id: string }>> {
  return apiClient.post('/api/v1/metrics', data);
}

/**
 * 更新指标
 */
export async function updateMetric(metricId: string, data: UpdateMetricRequest): Promise<ApiResponse<Metric>> {
  return apiClient.put(`/api/v1/metrics/${metricId}`, data);
}

/**
 * 删除指标
 */
export async function deleteMetric(metricId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/metrics/${metricId}`);
}

/**
 * 批量删除指标
 */
export async function batchDeleteMetrics(metricIds: string[]): Promise<ApiResponse<void>> {
  return apiClient.post('/api/v1/metrics/batch-delete', { metric_ids: metricIds });
}

/**
 * 获取指标当前值
 */
export async function getMetricValue(metricId: string, dimensions?: Record<string, string>): Promise<ApiResponse<MetricValue>> {
  return apiClient.get(`/api/v1/metrics/${metricId}/value`, { params: dimensions });
}

/**
 * 批量获取指标值
 */
export async function getMetricValues(metricIds: string[], dimensions?: Record<string, string>): Promise<ApiResponse<{ values: MetricValue[] }>> {
  return apiClient.post('/api/v1/metrics/values/batch', { metric_ids: metricIds, dimensions });
}

/**
 * 获取指标趋势数据
 */
export async function getMetricTrend(metricId: string, params?: {
  start_time?: string;
  end_time?: string;
  period?: string; // hourly, daily, weekly, monthly
  aggregation?: MetricAggregation;
  dimensions?: Record<string, string>;
}): Promise<ApiResponse<MetricTrendData>> {
  return apiClient.get(`/api/v1/metrics/${metricId}/trend`, { params });
}

/**
 * 获取指标计算任务列表
 */
export async function getMetricCalculationTasks(params?: {
  status?: MetricCalculationStatus;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: MetricCalculationTask[]; total: number }>> {
  return apiClient.get('/api/v1/metrics/calculation-tasks', { params });
}

/**
 * 获取指标计算任务详情
 */
export async function getMetricCalculationTask(taskId: string): Promise<ApiResponse<MetricCalculationTask>> {
  return apiClient.get(`/api/v1/metrics/calculation-tasks/${taskId}`);
}

/**
 * 创建指标计算任务
 */
export async function createMetricCalculationTask(data: CreateMetricCalculationTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/metrics/calculation-tasks', data);
}

/**
 * 更新指标计算任务
 */
export async function updateMetricCalculationTask(taskId: string, data: Partial<CreateMetricCalculationTaskRequest>): Promise<ApiResponse<MetricCalculationTask>> {
  return apiClient.put(`/api/v1/metrics/calculation-tasks/${taskId}`, data);
}

/**
 * 删除指标计算任务
 */
export async function deleteMetricCalculationTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/metrics/calculation-tasks/${taskId}`);
}

/**
 * 启动指标计算任务
 */
export async function startMetricCalculationTask(taskId: string): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/metrics/calculation-tasks/${taskId}/start`);
}

/**
 * 停止指标计算任务
 */
export async function stopMetricCalculationTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/metrics/calculation-tasks/${taskId}/stop`);
}

/**
 * 手动计算指标
 */
export async function calculateMetric(metricId: string, params?: {
  start_time?: string;
  end_time?: string;
  dimensions?: Record<string, string>;
}): Promise<ApiResponse<{ value: number; timestamp: string }>> {
  return apiClient.post(`/api/v1/metrics/${metricId}/calculate`, params);
}

/**
 * 获取指标分类统计
 */
export async function getMetricCategories(): Promise<ApiResponse<{
  categories: Array<{ category: MetricCategory; count: number }>;
  total: number;
}>> {
  return apiClient.get('/api/v1/metrics/categories/stats');
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

  // 数据源
  getDataSources,
  getDataSource,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  testDataSource,

  // ETL
  getETLTasks,
  getETLTask,
  createETLTask,
  updateETLTask,
  deleteETLTask,
  startETLTask,
  stopETLTask,
  getETLTaskLogs,

  // 数据质量
  getQualityRules,
  getQualityRule,
  createQualityRule,
  updateQualityRule,
  deleteQualityRule,
  getQualityResults,
  runQualityCheck,
  getQualityReports,
  getQualityReport,
  getQualityTasks,
  getQualityTask,
  createQualityTask,
  updateQualityTask,
  deleteQualityTask,
  startQualityTask,
  stopQualityTask,
  getQualityAlerts,
  acknowledgeAlert,
  resolveAlert,
  getAlertConfig,
  updateAlertConfig,
  getQualityTrend,

  // 数据血缘
  getTableLineage,
  getColumnLineage,
  getImpactAnalysis,
  searchLineage,
  getETLLineage,
  getLineagePath,

  // 特征存储
  getFeatures,
  getFeature,
  createFeature,
  updateFeature,
  deleteFeature,
  getFeatureVersions,
  getFeatureGroups,
  getFeatureGroup,
  createFeatureGroup,
  updateFeatureGroup,
  deleteFeatureGroup,
  getFeatureSets,
  getFeatureSet,
  createFeatureSet,
  getFeatureServices,
  getFeatureService,
  createFeatureService,
  deleteFeatureService,

  // 数据标准
  getStandardLibraries,
  createStandardLibrary,
  deleteStandardLibrary,
  getDataElements,
  createDataElement,
  updateDataElement,
  deleteDataElement,
  getStandardDocuments,
  createStandardDocument,
  deleteStandardDocument,
  getStandardMappings,
  createStandardMapping,
  deleteStandardMapping,

  // 数据资产
  getDataAssets,
  getDataAsset,
  getAssetTree,
  createAssetInventory,
  getAssetInventories,
  updateAssetTags,

  // 数据服务
  getDataServices,
  getDataService,
  createDataService,
  updateDataService,
  deleteDataService,
  publishDataService,
  unpublishDataService,
  getServiceApiKeys,
  createServiceApiKey,
  deleteServiceApiKey,
  getDataServiceStatistics,

  // BI 报表
  getReports,
  getReport,
  createReport,
  updateReport,
  deleteReport,
  getReportData,
  executeReportQuery,

  // 实时计算
  getFlinkJobs,
  getFlinkJob,
  createFlinkJob,
  updateFlinkJob,
  deleteFlinkJob,
  startFlinkJob,
  stopFlinkJob,
  getFlinkJobStatistics,
  getFlinkJobLogs,
  validateFlinkSql,

  // 离线开发
  getOfflineWorkflows,
  getOfflineWorkflow,
  createOfflineWorkflow,
  updateOfflineWorkflow,
  deleteOfflineWorkflow,
  executeOfflineWorkflow,
  getWorkflowExecutions,
  getWorkflowExecution,
  cancelWorkflowExecution,

  // 系统监控
  getTaskMetrics,
  getMonitoringOverview,
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  getAlerts,
  acknowledgeMonitoringAlert,
  resolveMonitoringAlert,

  // 指标体系
  getMetrics,
  getMetric,
  createMetric,
  updateMetric,
  deleteMetric,
  batchDeleteMetrics,
  getMetricValue,
  getMetricValues,
  getMetricTrend,
  getMetricCalculationTasks,
  getMetricCalculationTask,
  createMetricCalculationTask,
  updateMetricCalculationTask,
  deleteMetricCalculationTask,
  startMetricCalculationTask,
  stopMetricCalculationTask,
  calculateMetric,
  getMetricCategories,
};
