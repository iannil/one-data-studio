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
  // AI 增强字段
  ai_description?: string;
  sensitivity_level?: 'public' | 'internal' | 'confidential' | 'restricted';
  sensitivity_type?: 'pii' | 'financial' | 'health' | 'credential' | 'none';
  semantic_tags?: string[];
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

// ============= Kettle ETL 引擎类型 =============

export type KettleLogLevel = 'Nothing' | 'Error' | 'Minimal' | 'Basic' | 'Detailed' | 'Debug' | 'Rowlevel';

export interface KettleStatus {
  enabled: boolean;
  kettle_installed: boolean;
  kettle_home?: string;
  java_version?: string;
  message?: string;
}

export interface KettleExecutionResult {
  success: boolean;
  exit_code: number;
  stdout?: string;
  stderr?: string;
  error_message?: string;
  duration_seconds: number;
  rows_read: number;
  rows_written: number;
  rows_error: number;
  started_at: string;
  finished_at: string;
}

export interface KettleJobRequest {
  job_path?: string;
  repository?: string;
  directory?: string;
  job_name?: string;
  params?: Record<string, string>;
  log_level?: KettleLogLevel;
}

export interface KettleTransformationRequest {
  trans_path?: string;
  repository?: string;
  directory?: string;
  trans_name?: string;
  params?: Record<string, string>;
  log_level?: KettleLogLevel;
}

export interface KettleValidateResponse {
  is_valid: boolean;
  error?: string;
  file_path: string;
}

// ============= Kettle ETL API =============

/**
 * 获取 Kettle 服务状态
 */
export async function getKettleStatus(): Promise<ApiResponse<KettleStatus>> {
  return apiClient.get('/api/v1/kettle/status');
}

/**
 * 执行 Kettle 作业 (.kjb)
 */
export async function executeKettleJob(data: KettleJobRequest): Promise<ApiResponse<KettleExecutionResult>> {
  return apiClient.post('/api/v1/kettle/jobs/execute', data);
}

/**
 * 执行 Kettle 转换 (.ktr)
 */
export async function executeKettleTransformation(data: KettleTransformationRequest): Promise<ApiResponse<KettleExecutionResult>> {
  return apiClient.post('/api/v1/kettle/transformations/execute', data);
}

/**
 * 验证 Kettle 作业文件 (.kjb)
 */
export async function validateKettleJob(jobPath: string): Promise<ApiResponse<KettleValidateResponse>> {
  return apiClient.post('/api/v1/kettle/validate/job', { job_path: jobPath });
}

/**
 * 验证 Kettle 转换文件 (.ktr)
 */
export async function validateKettleTransformation(transPath: string): Promise<ApiResponse<KettleValidateResponse>> {
  return apiClient.post('/api/v1/kettle/validate/transformation', { trans_path: transPath });
}

/**
 * 使用 Kettle 引擎执行 ETL 任务
 */
export async function executeETLTaskWithKettle(taskId: string, triggeredBy?: string): Promise<ApiResponse<{
  task_id: string;
  log_id: string;
  status: string;
  execution_result: KettleExecutionResult;
}>> {
  return apiClient.post(`/api/v1/etl/tasks/${taskId}/execute-kettle`, {
    trigger_type: 'manual',
    triggered_by: triggeredBy,
  });
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
  return apiClient.get(`/api/v1/etl/tasks/${taskId}/logs`, { params: { execution_id: executionId, limit } });
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

// ============= AI 增强类型定义 =============

export interface AIAnnotation {
  column_name: string;
  ai_description?: string;
  sensitivity_level: 'public' | 'internal' | 'confidential' | 'restricted';
  sensitivity_type: 'pii' | 'financial' | 'health' | 'credential' | 'none';
  semantic_tags: string[];
  ai_confidence: number;
  annotated_at?: string;
}

export interface SensitivityReport {
  total_columns: number;
  sensitive_columns: number;
  by_type: {
    pii: string[];
    financial: string[];
    health: string[];
    credential: string[];
  };
  by_level: {
    public: number;
    internal: number;
    confidential: number;
    restricted: number;
  };
  high_risk_columns: Array<{
    column: string;
    type: string;
    level: string;
  }>;
}

export interface SQLLineageResult {
  sql: string;
  source_tables: string[];
  target_table?: string;
  column_mappings: Array<{
    source_column: string;
    target_column: string;
    transformation?: string;
  }>;
  lineage_edges: Array<{
    source: string;
    target: string;
    relation_type: string;
    confidence: number;
  }>;
  confidence: number;
  parse_method: 'rule' | 'ai_enhanced';
  errors: string[];
}

export interface AIImpactAnalysis {
  source_node: {
    node_type?: string;
    name?: string;
    full_name?: string;
  };
  change_type: string;
  impact_summary?: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  recommendations: string[];
  affected_nodes: Array<{
    node: {
      node_id?: string;
      name?: string;
      full_name?: string;
      node_type?: string;
    };
    impact_level: number;
  }>;
}

// ============= AI 增强 API =============

/**
 * 标注单个列的元数据
 */
export async function annotateColumn(
  database: string,
  table: string,
  column: string,
  options?: { use_llm?: boolean }
): Promise<ApiResponse<AIAnnotation>> {
  return apiClient.post('/api/v1/metadata/annotate/column', {
    database,
    table,
    column,
    use_llm: options?.use_llm ?? true,
  });
}

/**
 * 批量标注表的所有列
 */
export async function annotateTable(
  database: string,
  table: string,
  options?: { use_llm?: boolean; save?: boolean }
): Promise<ApiResponse<{ annotations: AIAnnotation[] }>> {
  return apiClient.post('/api/v1/metadata/annotate/table', {
    database,
    table,
    use_llm: options?.use_llm ?? true,
    save: options?.save ?? true,
  });
}

/**
 * 获取表的敏感字段报告
 */
export async function getSensitivityReport(
  database: string,
  table: string
): Promise<ApiResponse<SensitivityReport>> {
  return apiClient.post('/api/v1/metadata/sensitivity-report', {
    database,
    table,
  });
}

/**
 * 获取 AI 标注服务状态
 */
export async function getAIAnnotationStatus(): Promise<ApiResponse<{
  enabled: boolean;
  model: string;
  api_url: string;
}>> {
  return apiClient.get('/api/v1/ai/annotation-status');
}

/**
 * 解析 SQL 提取血缘关系
 */
export async function parseSQLLineage(
  sql: string,
  options?: { source_database?: string; use_ai?: boolean }
): Promise<ApiResponse<SQLLineageResult>> {
  return apiClient.post('/api/v1/lineage/parse-sql', {
    sql,
    source_database: options?.source_database,
    use_ai: options?.use_ai ?? true,
  });
}

/**
 * 分析 ETL 任务血缘
 */
export async function analyzeETLLineage(
  etlConfig: {
    source_type?: string;
    source_config?: Record<string, unknown>;
    source_query?: string;
    target_type?: string;
    target_config?: Record<string, unknown>;
    target_table?: string;
  },
  taskType?: string
): Promise<ApiResponse<{
  source_nodes: Array<{
    node_type: string;
    full_name: string;
    database_name?: string;
    table_name?: string;
  }>;
  target_nodes: Array<{
    node_type: string;
    full_name: string;
    database_name?: string;
    table_name?: string;
  }>;
  lineage_edges: Array<{
    source: string;
    target: string;
    relation_type: string;
    confidence: number;
  }>;
  confidence: number;
}>> {
  return apiClient.post('/api/v1/lineage/analyze-etl', {
    etl_config: etlConfig,
    task_type: taskType || 'batch',
  });
}

/**
 * AI 驱动的影响分析
 */
export async function getAIImpactAnalysis(
  nodeInfo: {
    node_type?: string;
    name?: string;
    full_name?: string;
  },
  options?: {
    downstream_nodes?: Array<{
      node_id?: string;
      name?: string;
      full_name?: string;
      node_type?: string;
      impact_level?: number;
    }>;
    change_type?: 'schema_change' | 'data_change' | 'deletion' | 'rename';
  }
): Promise<ApiResponse<AIImpactAnalysis>> {
  return apiClient.post('/api/v1/lineage/ai-impact-analysis', {
    node_info: nodeInfo,
    downstream_nodes: options?.downstream_nodes || [],
    change_type: options?.change_type || 'schema_change',
  });
}

/**
 * 推断列级血缘关系
 */
export async function inferColumnLineage(
  sql: string,
  options?: {
    source_columns?: Record<string, string[]>;
    use_ai?: boolean;
  }
): Promise<ApiResponse<{
  column_mappings: Array<{
    source_table: string;
    source_column: string;
    target_column: string;
    transformation?: string;
  }>;
  total: number;
}>> {
  return apiClient.post('/api/v1/lineage/infer-columns', {
    sql,
    source_columns: options?.source_columns || {},
    use_ai: options?.use_ai ?? true,
  });
}

/**
 * 从 SQL 生成并保存血缘关系
 */
export async function generateLineageFromSQL(
  sql: string,
  options?: {
    source_database?: string;
    job_id?: string;
    job_type?: string;
    save?: boolean;
  }
): Promise<ApiResponse<{
  parse_result: SQLLineageResult;
  nodes: Array<{
    node_id: string;
    node_type: string;
    name: string;
    full_name: string;
    database_name?: string;
    table_name?: string;
  }>;
  edges: Array<{
    edge_id: string;
    source_node_id: string;
    target_node_id: string;
    relation_type: string;
    confidence: number;
  }>;
  saved?: { nodes: number; edges: number };
}>> {
  return apiClient.post('/api/v1/lineage/generate-from-sql', {
    sql,
    source_database: options?.source_database,
    job_id: options?.job_id,
    job_type: options?.job_type || 'sql',
    save: options?.save ?? false,
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

// ============= AI 资产检索类型 =============

export interface QueryIntent {
  asset_types: string[];
  keywords: string[];
  data_level: string | null;
  database: string | null;
  time_filter: string | null;
  sensitive: boolean;
  original_query: string;
}

export interface AIAssetSearchResult {
  asset: DataAsset;
  relevance_score: number;
  matched_fields: string[];
}

export interface AIAssetSearchResponse {
  query: string;
  intent: QueryIntent;
  results: AIAssetSearchResult[];
  total: number;
}

export interface AISemanticSearchResult {
  asset: DataAsset;
  similarity_score: number;
}

export interface AISemanticSearchResponse {
  query: string;
  results: AISemanticSearchResult[];
  total: number;
  search_type: 'semantic' | 'keyword';
}

export interface AIRecommendation {
  asset: DataAsset;
  reason: string;
  reason_text: string;
  score: number;
}

export interface AIRecommendResponse {
  source_asset_id: string;
  recommendations: AIRecommendation[];
  total: number;
}

export interface TrendingAssetsResponse {
  period_days: number;
  assets: DataAsset[];
  total: number;
}

export interface AutocompleteSuggestion {
  type: 'asset' | 'table' | 'column';
  text: string;
  asset_id?: string;
  asset_type?: string;
  database?: string;
  table?: string;
  full_name?: string;
}

export interface AutocompleteResponse {
  prefix: string;
  suggestions: AutocompleteSuggestion[];
  total: number;
}

// ============= AI 清洗规则类型 =============

export interface CleaningRecommendation {
  issue_type: string;
  issue_description: string;
  rule_type: string;
  rule_name: string;
  rule_config: {
    target_column?: string;
    target_table?: string;
    target_database?: string;
    threshold?: number;
    action?: string;
    severity?: string;
    pattern?: string;
    expression?: string;
    [key: string]: any;
  };
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimated_improvement: number;
}

export interface CleaningRecommendationResponse {
  recommendations: CleaningRecommendation[];
  total_count: number;
  kettle_steps?: any[];
}

export interface RuleTemplate {
  category: string;
  rule_type: string;
  name: string;
  expression: string;
  severity: string;
  config_template: any;
}

export interface RuleTemplatesResponse {
  templates: RuleTemplate[];
  total: number;
  categories: string[];
}

// ============= 字段映射类型 =============

export interface FieldMappingSuggestion {
  source_field: string;
  target_field: string;
  confidence: number;
  mapping_type: 'exact' | 'fuzzy' | 'semantic' | 'inferred' | 'derived';
  transformation: string;
  data_type_conversion: {
    source_type: string;
    target_type: string;
    conversion: string;
    cost: number;
    conversion_risk: 'low' | 'medium' | 'high' | 'critical';
  };
  quality_score: number;
}

export interface MappingSummary {
  total_suggestions: number;
  source_coverage: number;
  target_coverage: number;
  avg_confidence: number;
  avg_quality: number;
  mapping_types: Record<string, number>;
}

export interface FieldMappingResponse {
  source_table: string;
  target_table: string;
  source_columns_count: number;
  target_columns_count: number;
  suggestions: FieldMappingSuggestion[];
  summary: MappingSummary;
  unmapped_source: string[];
  unmapped_target: string[];
}

export interface MappingConflict {
  type: 'multiple_sources' | 'type_incompatible' | 'length_exceeded';
  severity: 'error' | 'warning';
  message: string;
  target_field?: string;
  source_fields?: string[];
  source_field?: string;
  source_type?: string;
  target_type?: string;
  source_length?: number;
  target_length?: number;
}

export interface MappingConflictResponse {
  conflicts: MappingConflict[];
  conflict_count: number;
}

export interface MappingTable {
  table_name: string;
  database_name: string;
  table_comment: string;
  column_count: number;
}

export interface MappingTablesResponse {
  tables: MappingTable[];
  total: number;
}

export interface SQLGenerationResponse {
  select_sql: string;
  mappings: any[];
  conversion_count: number;
  high_risk_count: number;
}

export interface DerivedFieldResponse {
  suggestions: FieldMappingSuggestion[];
  count: number;
}

// ============= 智能预警类型 =============

export interface AnomalyDetectionResult {
  anomaly_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  description: string;
  affected_table: string;
  affected_column?: string;
  metric_value?: number;
  threshold?: number;
  confidence: number;
  suggestions: string[];
  detected_at: string;
}

export interface AnomalySummary {
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  critical_tables: string[];
}

export interface AnomalyDetectionResponse {
  detected_at: string;
  total_anomalies: number;
  anomalies: AnomalyDetectionResult[];
  summary: AnomalySummary;
}

export interface AlertRule {
  rule_id: string;
  name: string;
  description?: string;
  rule_type: string;
  config: Record<string, unknown>;
  severity: string;
  enabled: boolean;
  channels: string[];
  tenant_id?: string;
  created_by?: string;
  created_at?: string;
}

export interface AlertRulesResponse {
  total: number;
  rules: AlertRule[];
}

export interface AlertChannel {
  channel_type: 'email' | 'sms' | 'webhook' | 'wechat' | 'dingtalk';
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  last_used?: string;
}

export interface AlertChannelsResponse {
  channels: AlertChannel[];
  total: number;
}

export interface AlertSendResult {
  channel: string;
  success: boolean;
  message?: string;
  error?: string;
}

export interface AlertSendResponse {
  alert_id: string;
  sent_at: string;
  channels: string[];
  results: AlertSendResult[];
  summary: {
    total: number;
    success: number;
    failed: number;
  };
}

export interface AlertHistoryItem {
  alert_id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  affected_table?: string;
  channels_sent: string[];
  status: string;
  created_at: string;
}

export interface AlertHistoryResponse {
  total: number;
  history: AlertHistoryItem[];
}

export interface AlertStatistics {
  period_days: number;
  total_alerts: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  by_channel: Record<string, number>;
  top_tables: Array<{ table: string; count: number }>;
}

export interface AlertSubscription {
  subscription_id: string;
  user_id: string;
  alert_types: string[];
  severity_filter: string[];
  channels: string[];
  filters: Record<string, unknown>;
  enabled?: boolean;
}

export interface AlertSubscriptionsResponse {
  user_id: string;
  subscriptions: AlertSubscription[];
  total: number;
}

export interface AlertType {
  type: string;
  name: string;
  description: string;
  available_filters: string[];
}

export interface AlertTypesResponse {
  types: AlertType[];
  total: number;
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
  aggregation?: string;
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

// ==================== 数据脱敏 API ====================

export interface MaskingRule {
  rule_id: string;
  name: string;
  strategy: string;
  sensitivity_type: string;
  sensitivity_level: string;
  column_pattern?: string;
  data_type?: string;
  options: Record<string, any>;
  enabled: boolean;
  priority: number;
}

export interface MaskingStrategy {
  value: string;
  label: string;
}

export interface MaskingConfig {
  rule_id: string | null;
  rule_name?: string;
  strategy: string | null;
  sensitivity_type?: string;
  sensitivity_level?: string;
  options?: Record<string, any>;
  no_masking?: boolean;
}

export interface ColumnMeta {
  name?: string;
  column_name?: string;
  sensitivity_type?: string;
  sensitivity_level?: string;
  data_type?: string;
}

/**
 * 获取数据脱敏预览
 */
export async function getMaskingPreview(
  sampleData: Record<string, any>[],
  columnMetadata?: Record<string, { sensitivity_type?: string; sensitivity_level?: string; data_type?: string }>,
  maxRows?: number
): Promise<ApiResponse<{
  original: Record<string, any>[];
  masked: Record<string, any>[];
  config: Record<string, MaskingConfig>;
}>> {
  return apiClient.post('/api/v1/masking/preview', {
    sample_data: sampleData,
    column_metadata: columnMetadata,
    max_rows: maxRows,
  });
}

/**
 * 执行数据脱敏
 */
export async function executeMasking(
  data: Record<string, any>[],
  columnMetadata?: Record<string, { sensitivity_type?: string; sensitivity_level?: string; data_type?: string }>
): Promise<ApiResponse<{
  masked_data: Record<string, any>[];
  record_count: number;
}>> {
  return apiClient.post('/api/v1/masking/execute', {
    data,
    column_metadata: columnMetadata,
  });
}

/**
 * 生成脱敏配置
 */
export async function generateMaskingConfig(
  columns: ColumnMeta[]
): Promise<ApiResponse<Record<string, MaskingConfig>>> {
  return apiClient.post('/api/v1/masking/config', { columns });
}

/**
 * 获取可用的脱敏规则列表
 */
export async function getMaskingRules(): Promise<ApiResponse<{
  rules: MaskingRule[];
  strategies: MaskingStrategy[];
}>> {
  return apiClient.get('/api/v1/masking/rules');
}

/**
 * 对单个值进行脱敏
 */
export async function maskSingleValue(params: {
  value: any;
  column_name?: string;
  sensitivity_type?: string;
  sensitivity_level?: string;
  strategy?: string;
  options?: Record<string, any>;
}): Promise<ApiResponse<{
  original: any;
  masked: any;
}>> {
  return apiClient.post('/api/v1/masking/value', params);
}

/**
 * 根据表元数据自动脱敏数据
 */
export async function maskTableData(
  tableId: string,
  data: Record<string, any>[]
): Promise<ApiResponse<{
  table_id: string;
  table_name: string;
  masked_data: Record<string, any>[];
  record_count: number;
  columns_with_masking: string[];
}>> {
  return apiClient.post(`/api/v1/masking/table/${tableId}`, { data });
}

// ==================== 非结构化文档 OCR API ====================

/**
 * OCR 识别结果项
 */
export interface OCRResultItem {
  text: string;
  confidence: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  block_type: string;
}

/**
 * 表格数据
 */
export interface ExtractedTableData {
  page: number;
  rows: number;
  cols: number;
  data: string[][];
  markdown: string;
}

/**
 * 文档提取结果
 */
export interface DocumentExtractionData {
  text: string;
  page_count: number;
  pages: Array<{
    page_number: number;
    text: string;
  }>;
  tables: ExtractedTableData[];
  image_count: number;
  images: Array<{
    page_number: number;
    image_index: number;
    format: string;
    size?: { width: number; height: number };
  }>;
  metadata: Record<string, any>;
  char_count: number;
  errors: string[];
}

/**
 * OCR 服务状态
 */
export interface OCRServiceStatus {
  enabled: boolean;
  default_engine: string;
  languages: string;
  available_engines: {
    tesseract: boolean;
    paddleocr: boolean;
    easyocr: boolean;
  };
  supported_document_types: Array<{
    type: string;
    description: string;
    extensions: string[];
  }>;
  supported_structured_types: Array<{
    type: string;
    description: string;
  }>;
}

/**
 * 结构化数据提取结果
 */
export interface StructuredExtractionResult {
  data_type: string;
  structured_data: Record<string, any>;
  raw_text: string;
  full_text_length: number;
  table_count: number;
  errors: string[];
}

/**
 * 批量 OCR 文档项
 */
export interface BatchOCRDocument {
  content: string; // base64 编码
  filename?: string;
  content_type?: string;
}

/**
 * 批量 OCR 结果项
 */
export interface BatchOCRResultItem {
  index: number;
  filename: string;
  success: boolean;
  error: string | null;
  data: DocumentExtractionData | null;
}

/**
 * 从文档提取内容
 * 支持 PDF、图片、Word、文本文件
 */
export async function extractDocument(
  options: {
    file?: File;
    content?: string; // base64 编码
    filename?: string;
    content_type?: string;
    extract_tables?: boolean;
    extract_images?: boolean;
    ocr_images?: boolean;
  }
): Promise<ApiResponse<DocumentExtractionData>> {
  if (options.file) {
    const formData = new FormData();
    formData.append('file', options.file);
    if (options.extract_tables !== undefined) {
      formData.append('extract_tables', String(options.extract_tables));
    }
    if (options.extract_images !== undefined) {
      formData.append('extract_images', String(options.extract_images));
    }
    if (options.ocr_images !== undefined) {
      formData.append('ocr_images', String(options.ocr_images));
    }
    return apiClient.post('/api/v1/ocr/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  } else {
    return apiClient.post('/api/v1/ocr/extract', {
      content: options.content,
      filename: options.filename,
      content_type: options.content_type,
      extract_tables: options.extract_tables ?? true,
      extract_images: options.extract_images ?? false,
      ocr_images: options.ocr_images ?? true,
    });
  }
}

/**
 * 图片 OCR 识别
 */
export async function ocrImage(
  options: {
    file?: File;
    image?: string; // base64 编码
    engine?: 'tesseract' | 'paddleocr' | 'easyocr' | 'auto';
  }
): Promise<ApiResponse<{
  text: string;
  results: OCRResultItem[];
  total_items: number;
  average_confidence: number;
}>> {
  if (options.file) {
    const formData = new FormData();
    formData.append('file', options.file);
    if (options.engine) {
      formData.append('engine', options.engine);
    }
    return apiClient.post('/api/v1/ocr/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  } else {
    return apiClient.post('/api/v1/ocr/image', {
      image: options.image,
      engine: options.engine,
    });
  }
}

/**
 * 提取结构化数据（发票、身份证、合同等）
 */
export async function extractStructuredData(
  options: {
    file?: File;
    content?: string; // base64 编码
    filename?: string;
    content_type?: string;
    data_type: 'invoice' | 'id_card' | 'contract';
  }
): Promise<ApiResponse<StructuredExtractionResult>> {
  if (options.file) {
    const formData = new FormData();
    formData.append('file', options.file);
    formData.append('data_type', options.data_type);
    return apiClient.post('/api/v1/ocr/structured', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  } else {
    return apiClient.post('/api/v1/ocr/structured', {
      content: options.content,
      filename: options.filename,
      content_type: options.content_type,
      data_type: options.data_type,
    });
  }
}

/**
 * 获取 OCR 服务状态
 */
export async function getOCRStatus(): Promise<ApiResponse<OCRServiceStatus>> {
  return apiClient.get('/api/v1/ocr/status');
}

/**
 * 批量文档提取
 */
export async function batchExtractDocuments(
  documents: BatchOCRDocument[],
  options?: {
    extract_tables?: boolean;
    ocr_images?: boolean;
  }
): Promise<ApiResponse<{
  total: number;
  success_count: number;
  failed_count: number;
  results: BatchOCRResultItem[];
}>> {
  return apiClient.post('/api/v1/ocr/batch', {
    documents,
    extract_tables: options?.extract_tables ?? true,
    ocr_images: options?.ocr_images ?? true,
  });
}

/**
 * 将文件转换为 base64 字符串
 */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const result = reader.result as string;
      // 移除 data:xxx;base64, 前缀
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = (error) => reject(error);
  });
}

// ==================== 元数据驱动 Kettle 配置自动生成 API ====================

/**
 * Kettle 生成的配置结果
 */
export interface KettleGenerationResult {
  name: string;
  type: 'transformation' | 'job';
  format: 'ktr' | 'kjb';
  content: string;
  source_table?: string;
  target_table?: string;
  column_count?: number;
  source_column_count?: number;
  target_column_count?: number;
  transformation_count?: number;
  sequential?: boolean;
  task_id?: string;
  task_name?: string;
}

/**
 * Kettle 数据源类型选项
 */
export interface KettleTypeOption {
  value: string;
  label: string;
}

/**
 * Kettle 支持的类型配置
 */
export interface KettleTypesConfig {
  source_types: KettleTypeOption[];
  write_modes: KettleTypeOption[];
  data_types: KettleTypeOption[];
  log_levels: KettleTypeOption[];
}

/**
 * Kettle 连接配置
 */
export interface KettleConnectionConfig {
  type: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  schema?: string;
  name?: string;
}

/**
 * Kettle 列配置
 */
export interface KettleColumnConfig {
  column_name: string;
  data_type: string;
}

/**
 * 生成 Kettle 转换配置
 */
export async function generateKettleTransformation(params: {
  source: {
    connection: KettleConnectionConfig;
    table: string;
    schema?: string;
    columns: KettleColumnConfig[];
  };
  target: {
    connection: KettleConnectionConfig;
    table: string;
    schema?: string;
    columns?: KettleColumnConfig[];
  };
  options?: {
    name?: string;
    write_mode?: 'insert' | 'update' | 'upsert' | 'truncate_insert';
    batch_size?: number;
    commit_size?: number;
    incremental_field?: string;
    filter_condition?: string;
    column_mappings?: Record<string, string>;
    primary_keys?: string[];
  };
}): Promise<ApiResponse<KettleGenerationResult>> {
  return apiClient.post('/api/v1/kettle/generate/transformation', params);
}

/**
 * 生成 Kettle 作业配置
 */
export async function generateKettleJob(params: {
  name: string;
  description?: string;
  transformations: string[];
  sequential?: boolean;
}): Promise<ApiResponse<KettleGenerationResult>> {
  return apiClient.post('/api/v1/kettle/generate/job', params);
}

/**
 * 从 ETL 任务生成 Kettle 配置
 */
export async function generateKettleFromETLTask(
  taskId: string,
  options?: {
    name?: string;
    write_mode?: string;
    batch_size?: number;
  }
): Promise<ApiResponse<KettleGenerationResult>> {
  return apiClient.post(`/api/v1/kettle/generate/from-etl-task/${taskId}`, options || {});
}

/**
 * 从元数据表生成 Kettle 配置
 */
export async function generateKettleFromMetadata(params: {
  source_table_id: string;
  target_table_id: string;
  source_connection?: KettleConnectionConfig;
  target_connection?: KettleConnectionConfig;
  options?: {
    name?: string;
    write_mode?: string;
    batch_size?: number;
    column_mappings?: Record<string, string>;
  };
}): Promise<ApiResponse<KettleGenerationResult>> {
  return apiClient.post('/api/v1/kettle/generate/from-metadata', params);
}

/**
 * 获取 Kettle 支持的类型和选项
 */
export async function getKettleTypes(): Promise<ApiResponse<KettleTypesConfig>> {
  return apiClient.get('/api/v1/kettle/types');
}

/**
 * 下载 Kettle 配置文件
 */
export function downloadKettleConfig(
  content: string,
  filename: string,
  format: 'ktr' | 'kjb' = 'ktr'
): void {
  const blob = new Blob([content], { type: 'application/xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith(`.${format}`) ? filename : `${filename}.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ==================== AI 能力增强 API ====================

/**
 * 清洗规则推荐结果
 */
export interface CleaningRecommendation {
  id: string;
  rule_type: string;
  column_name: string;
  description: string;
  priority: string;
  confidence: number;
  config: Record<string, unknown>;
  kettle_step_type?: string;
}

/**
 * 缺失值填充分析结果
 */
export interface MissingAnalysis {
  column_name: string;
  total_count: number;
  missing_count: number;
  missing_ratio: number;
  pattern: string;
  recommended_strategy: string;
}

/**
 * 缺失值填充结果
 */
export interface ImputationResult {
  column_name: string;
  strategy: string;
  imputed_count: number;
  fill_value?: unknown;
  values?: unknown[];
}

/**
 * AI 缺失值填充
 */
export async function imputeMissingValues(params: {
  column_name: string;
  column_type?: string;
  sample_values: unknown[];
  strategy?: string;
  context?: Record<string, unknown>;
}): Promise<ApiResponse<{
  analysis: MissingAnalysis;
  strategy: string;
  result: ImputationResult;
}>> {
  return apiClient.post('/api/v1/data/impute-missing', params);
}

/**
 * 缺失值填充预览
 */
export async function previewImputation(params: {
  column_name: string;
  column_type?: string;
  sample_values: unknown[];
  strategy?: string;
  preview_count?: number;
}): Promise<ApiResponse<{
  original_values: unknown[];
  imputed_values: unknown[];
  changes: Array<{ index: number; original: unknown; imputed: unknown }>;
}>> {
  return apiClient.post('/api/v1/data/impute-preview', params);
}

// ==================== 语义检索 API ====================

/**
 * 语义检索结果
 */
export interface SemanticSearchResult {
  asset: {
    id: string;
    name: string;
    asset_type: string;
    database: string;
    schema: string;
    description: string;
    tags: string[];
    owner: string;
  };
  score: number;
  relevance_reason?: string;
  highlights?: string[];
}

/**
 * 语义资产检索
 */
export async function semanticSearchAssets(params: {
  query: string;
  top_k?: number;
  filters?: {
    asset_type?: string;
    database?: string;
    schema?: string;
    owner?: string;
  };
  rerank?: boolean;
}): Promise<ApiResponse<{
  query: string;
  results: SemanticSearchResult[];
  total_count: number;
}>> {
  return apiClient.post('/api/v1/assets/semantic-search', params);
}

/**
 * 索引资产用于语义检索
 */
export async function indexAssetForSearch(params: {
  table_id?: string;
  batch?: boolean;
  table_ids?: string[];
}): Promise<ApiResponse<{
  indexed: boolean;
  indexed_count?: number;
  total_requested?: number;
  table_id?: string;
}>> {
  return apiClient.post('/api/v1/assets/semantic-search/index', params);
}

/**
 * 获取语义检索服务状态
 */
export async function getSemanticSearchStats(): Promise<ApiResponse<{
  status: string;
  collection?: string;
  num_entities?: number;
  milvus_host?: string;
  milvus_port?: number;
  embedding_model?: string;
  embedding_dim?: number;
  error?: string;
}>> {
  return apiClient.get('/api/v1/assets/semantic-search/stats');
}

/**
 * 获取相似资产
 */
export async function getSimilarAssets(
  assetId: string,
  topK?: number
): Promise<ApiResponse<{
  asset_id: string;
  similar_assets: SemanticSearchResult[];
}>> {
  return apiClient.get(`/api/v1/assets/similar/${assetId}`, {
    params: { top_k: topK },
  });
}

// ==================== Kettle AI 集成 API ====================

/**
 * 注入 AI 规则到 Kettle 转换
 */
export async function injectAIRulesToKettle(params: {
  transformation_xml: string;
  cleaning_rules?: CleaningRecommendation[];
  imputation_rules?: Array<{
    column_name: string;
    strategy: string;
    fill_value?: unknown;
  }>;
}): Promise<ApiResponse<{
  modified_xml: string;
  injected_cleaning_rules: number;
  injected_imputation_rules: number;
}>> {
  return apiClient.post('/api/v1/etl/inject-ai-rules', params);
}

/**
 * 注入脱敏规则到 Kettle 转换
 */
export async function injectMaskingRulesToKettle(params: {
  transformation_xml: string;
  table_id?: string;
  masking_rules?: Record<string, {
    strategy: string;
    sensitivity_type?: string;
    preserve_length?: boolean;
    mask_char?: string;
  }>;
}): Promise<ApiResponse<{
  modified_xml: string;
  masked_columns: string[];
}>> {
  return apiClient.post('/api/v1/etl/inject-masking', params);
}

// ==================== 元数据版本 API ====================

/**
 * 元数据版本记录
 */
export interface MetadataVersion {
  id: string;
  table_id: string;
  change_type: string;
  change_summary: string;
  change_details: Record<string, unknown>;
  schema_snapshot: Record<string, unknown>;
  previous_version_id?: string;
  changed_by: string;
  change_source: string;
  version_number: number;
  created_at: string;
  tenant_id?: string;
}

/**
 * 获取元数据版本历史
 */
export async function getMetadataVersions(
  tableId: string,
  params?: {
    page?: number;
    page_size?: number;
    change_type?: string;
  }
): Promise<ApiResponse<{
  versions: MetadataVersion[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}>> {
  return apiClient.get(`/api/v1/metadata/versions/${tableId}`, { params });
}

/**
 * 获取元数据版本详情
 */
export async function getMetadataVersionDetail(
  tableId: string,
  versionId: string
): Promise<ApiResponse<MetadataVersion>> {
  return apiClient.get(`/api/v1/metadata/versions/${tableId}/${versionId}`);
}

/**
 * 比较两个元数据版本
 */
export async function compareMetadataVersions(
  tableId: string,
  versionId1: string,
  versionId2: string
): Promise<ApiResponse<{
  added_columns: string[];
  removed_columns: string[];
  modified_columns: Array<{
    name: string;
    before: Record<string, unknown>;
    after: Record<string, unknown>;
  }>;
  other_changes: Record<string, unknown>;
}>> {
  return apiClient.post(`/api/v1/metadata/versions/${tableId}/compare`, {
    version_id_1: versionId1,
    version_id_2: versionId2,
  });
}

/**
 * 回滚到指定元数据版本
 */
export async function rollbackMetadataVersion(
  tableId: string,
  versionId: string
): Promise<ApiResponse<{
  table_id: string;
  rolled_back_to: string;
}>> {
  return apiClient.post(`/api/v1/metadata/versions/${tableId}/rollback`, {
    version_id: versionId,
  });
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

  // Kettle ETL 引擎
  getKettleStatus,
  executeKettleJob,
  executeKettleTransformation,
  validateKettleJob,
  validateKettleTransformation,
  executeETLTaskWithKettle,

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

  // AI 增强
  annotateColumn,
  annotateTable,
  getSensitivityReport,
  getAIAnnotationStatus,
  parseSQLLineage,
  analyzeETLLineage,
  getAIImpactAnalysis,
  inferColumnLineage,
  generateLineageFromSQL,

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

  // AI 资产检索
  aiSearchAssets,
  aiSemanticSearchAssets,
  aiRecommendAssets,
  getTrendingAssets,
  getAssetAutocomplete,

  // AI 清洗规则
  analyzeTableQuality,
  recommendCleaningRules,
  recommendColumnRules,
  getRuleTemplates,

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

  // 数据脱敏
  getMaskingPreview,
  executeMasking,
  generateMaskingConfig,
  getMaskingRules,
  maskSingleValue,
  maskTableData,

  // 非结构化文档 OCR
  extractDocument,
  ocrImage,
  extractStructuredData,
  getOCRStatus,
  batchExtractDocuments,
  fileToBase64,

  // 元数据驱动 Kettle 配置自动生成
  generateKettleTransformation,
  generateKettleJob,
  generateKettleFromETLTask,
  generateKettleFromMetadata,
  getKettleTypes,
  downloadKettleConfig,

  // AI 能力增强
  recommendCleaningRules,
  imputeMissingValues,
  previewImputation,

  // 语义检索
  semanticSearchAssets,
  indexAssetForSearch,
  getSemanticSearchStats,
  getSimilarAssets,

  // Kettle AI 集成
  injectAIRulesToKettle,
  injectMaskingRulesToKettle,

  // 元数据版本
  getMetadataVersions,
  getMetadataVersionDetail,
  compareMetadataVersions,
  rollbackMetadataVersion,

  // 元数据图谱
  getMetadataGraph,
  getTableLineageGraph,
  getColumnRelationGraph,
  searchMetadataNodes,
  getImpactAnalysis,
  getGraphStatistics,
  getNodeNeighbors,
};

// ============= 元数据图谱 API 类型定义 =============

export interface GraphNode {
  id: string;
  label: string;
  type: 'database' | 'table' | 'column' | 'lineage';
  database_name?: string;
  table_name?: string;
  column_name?: string;
  data_type?: string;
  description?: string;
  is_center?: boolean;
  properties?: any;
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  type: string;
  direction?: 'upstream' | 'downstream';
  relation_type?: string;
  properties?: any;
}

export interface MetadataGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics?: {
    total_nodes: number;
    total_edges: number;
    node_types?: Record<string, number>;
  };
}

export interface TableLineageGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  center_table: string;
  statistics?: {
    upstream_count: number;
    downstream_count: number;
  };
  error?: string;
}

export interface ColumnRelationGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  table_name: string;
  error?: string;
}

export interface SearchNodesResponse {
  query: string;
  total: number;
  nodes: GraphNode[];
}

export interface ImpactAnalysisResponse {
  impacted_nodes: GraphNode[];
  impacted_edges: GraphEdge[];
  impact_count: number;
  risk_levels?: Record<string, number>;
}

export interface GraphStatistics {
  databases: number;
  tables: number;
  columns: number;
  tables_per_database?: Array<{
    database: string;
    count: number;
  }>;
}

// ============= 元数据图谱 API 方法 =============

/**
 * 获取完整元数据图谱
 */
export const getMetadataGraph = (params?: {
  node_types?: string;
  include_lineage?: boolean;
}) => {
  return apiClient.get<MetadataGraphResponse>('/api/v1/metadata/graph', { params });
};

/**
 * 获取表的数据血缘图谱
 */
export const getTableLineageGraph = (tableName: string, params?: {
  depth?: number;
}) => {
  return apiClient.get<TableLineageGraph>(`/api/v1/metadata/graph/lineage/${tableName}`, { params });
};

/**
 * 获取表的列关系图
 */
export const getColumnRelationGraph = (tableName: string) => {
  return apiClient.get<ColumnRelationGraph>(`/api/v1/metadata/graph/columns/${tableName}`);
};

/**
 * 搜索元数据节点
 */
export const searchMetadataNodes = (query: string, params?: {
  node_types?: string;
}) => {
  return apiClient.get<SearchNodesResponse>('/api/v1/metadata/graph/search', {
    params: { query, ...params }
  });
};

/**
 * 获取影响分析
 */
export const getImpactAnalysis = (nodeType: string, nodeId: string) => {
  return apiClient.get<ImpactAnalysisResponse>(`/api/v1/metadata/graph/impact/${nodeType}/${nodeId}`);
};

/**
 * 获取图谱统计信息
 */
export const getGraphStatistics = () => {
  return apiClient.get<GraphStatistics>('/api/v1/metadata/graph/statistics');
};

/**
 * 获取节点的邻居
 */
export const getNodeNeighbors = (nodeType: string, nodeId: string, params?: {
  depth?: number;
}) => {
  return apiClient.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`/api/v1/metadata/graph/neighbors/${nodeType}/${nodeId}`, { params });
};

// ============= AI 资产检索增强 =============

/**
 * AI 自然语言搜索资产
 */
export const aiSearchAssets = (query: string, params?: {
  limit?: number;
  filters?: {
    asset_type?: string;
    category_id?: string;
    data_level?: string;
  };
}) => {
  return apiClient.post<ApiResponse<AIAssetSearchResponse>>('/api/v1/assets/ai/search', {
    query,
    limit: params?.limit || 20,
    filters: params?.filters,
  });
};

/**
 * AI 语义搜索资产（基于向量相似度）
 */
export const aiSemanticSearchAssets = (query: string, params?: {
  limit?: number;
  filters?: {
    asset_type?: string;
    category_id?: string;
    data_level?: string;
  };
}) => {
  return apiClient.post<ApiResponse<AISemanticSearchResponse>>('/api/v1/assets/ai/semantic-search', {
    query,
    limit: params?.limit || 20,
    filters: params?.filters,
  });
};

/**
 * AI 推荐相关资产
 */
export const aiRecommendAssets = (assetId: string, params?: {
  limit?: number;
}) => {
  return apiClient.get<ApiResponse<AIRecommendResponse>>(`/api/v1/assets/ai/recommend/${assetId}`, {
    params: { limit: params?.limit || 10 },
  });
};

/**
 * 获取热门资产
 */
export const getTrendingAssets = (params?: {
  days?: number;
  limit?: number;
}) => {
  return apiClient.get<ApiResponse<TrendingAssetsResponse>>('/api/v1/assets/ai/trending', {
    params: { days: params?.days || 7, limit: params?.limit || 10 },
  });
};

/**
 * 搜索补全建议
 */
export const getAssetAutocomplete = (prefix: string, params?: {
  limit?: number;
}) => {
  return apiClient.get<ApiResponse<AutocompleteResponse>>('/api/v1/assets/ai/autocomplete', {
    params: { prefix, limit: params?.limit || 10 },
  });
};

// ============= AI 清洗规则 API =============

/**
 * AI 分析表的数据质量问题
 */
export const analyzeTableQuality = (tableName: string, params?: {
  database_name?: string;
}) => {
  return apiClient.post<{ recommendations: CleaningRecommendation[]; total_count: number }>(
    '/api/v1/quality/analyze-table',
    {
      table_name: tableName,
      database_name: params?.database_name,
    }
  );
};

/**
 * AI 推荐清洗规则（基于告警）
 */
export const recommendCleaningRules = (params: {
  table_id?: string;
  quality_alerts?: any[];
  include_kettle_steps?: boolean;
}) => {
  return apiClient.post<CleaningRecommendationResponse>('/api/v1/quality/recommend-cleaning', params);
};

/**
 * 为单个列推荐清洗规则
 */
export const recommendColumnRules = (columnInfo: {
  name: string;
  type: string;
  nullable?: boolean;
  sample_values?: any[];
}) => {
  return apiClient.post<{ recommendations: CleaningRecommendation[]; total_count: number }>(
    '/api/v1/quality/recommend-column-rules',
    { column_info: columnInfo }
  );
};

/**
 * 获取清洗规则模板
 */
export const getRuleTemplates = () => {
  return apiClient.get<RuleTemplatesResponse>('/api/v1/quality/rule-templates');
};

// ============= AI 字段映射 API =============

/**
 * 智能推荐字段映射
 */
export const suggestFieldMappings = (params: {
  source_table: string;
  target_table: string;
  source_database?: string;
  target_database?: string;
  options?: Record<string, unknown>;
}) => {
  return apiClient.post<FieldMappingResponse>('/api/v1/mapping/suggest', params);
};

/**
 * 推荐数据类型转换策略
 */
export const suggestTypeConversions = (params: {
  mappings: FieldMappingSuggestion[];
  source_schema: Array<{ name: string; type: string; length?: number }>;
  target_schema: Array<{ name: string; type: string; length?: number }>;
}) => {
  return apiClient.post<FieldMappingSuggestion[]>('/api/v1/mapping/type-conversions', params);
};

/**
 * 生成字段转换 SQL
 */
export const generateTransformationSQL = (params: {
  mappings: FieldMappingSuggestion[];
  source_table: string;
  target_table?: string;
}) => {
  return apiClient.post<SQLGenerationResponse>('/api/v1/mapping/generate-sql', params);
};

/**
 * 检测映射冲突
 */
export const detectMappingConflicts = (params: {
  mappings: FieldMappingSuggestion[];
  target_schema: Array<{ name: string; type: string; length?: number }>;
}) => {
  return apiClient.post<MappingConflictResponse>('/api/v1/mapping/detect-conflicts', params);
};

/**
 * 推荐派生字段映射
 */
export const suggestDerivedFields = (params: {
  source_columns: Array<{ name: string; type: string }>;
  target_columns: Array<{ name: string; type: string }>;
  context?: Record<string, unknown>;
}) => {
  return apiClient.post<DerivedFieldResponse>('/api/v1/mapping/derived-fields', params);
};

/**
 * 获取指定数据库的表列表（用于映射选择）
 */
export const listTablesForMapping = (databaseName: string) => {
  return apiClient.get<MappingTablesResponse>(`/api/v1/mapping/tables/${databaseName}`);
};

// ============= 智能预警 API =============

/**
 * 执行异常检测
 */
export const detectAnomalies = (params: {
  detection_types?: string[];
  time_window_hours?: number;
}) => {
  return apiClient.post<AnomalyDetectionResponse>('/api/v1/alerts/detect-anomalies', params);
};

/**
 * 获取预警规则列表
 */
export const getAlertRules = (params?: {
  rule_type?: string;
  enabled_only?: boolean;
}) => {
  return apiClient.get<AlertRulesResponse>('/api/v1/alerts/rules', { params });
};

/**
 * 创建预警规则
 */
export const createAlertRule = (rule: {
  name: string;
  description?: string;
  rule_type: string;
  config: Record<string, unknown>;
  severity: string;
  enabled?: boolean;
  channels?: string[];
}) => {
  return apiClient.post<AlertRule>('/api/v1/alerts/rules', rule);
};

/**
 * 更新预警规则
 */
export const updateAlertRule = (ruleId: string, updates: Partial<AlertRule>) => {
  return apiClient.put<AlertRule>(`/api/v1/alerts/rules/${ruleId}`, updates);
};

/**
 * 删除预警规则
 */
export const deleteAlertRule = (ruleId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/alerts/rules/${ruleId}`);
};

/**
 * 获取预警通道列表
 */
export const getAlertChannels = (includeDisabled?: boolean) => {
  return apiClient.get<AlertChannelsResponse>('/api/v1/alerts/channels', {
    params: { include_disabled: includeDisabled },
  });
};

/**
 * 添加预警通道
 */
export const addAlertChannel = (channel: {
  channel_type: string;
  name: string;
  config: Record<string, unknown>;
}) => {
  return apiClient.post<AlertChannel>('/api/v1/alerts/channels', channel);
};

/**
 * 更新预警通道
 */
export const updateAlertChannel = (channelType: string, updates: {
  enabled?: boolean;
  config?: Record<string, unknown>;
  name?: string;
}) => {
  return apiClient.put<AlertChannel>(`/api/v1/alerts/channels/${channelType}`, updates);
};

/**
 * 删除预警通道
 */
export const removeAlertChannel = (channelType: string) => {
  return apiClient.delete<{ removed: boolean }>(`/api/v1/alerts/channels/${channelType}`);
};

/**
 * 测试预警通道
 */
export const testAlertChannel = (channelType: string, message?: string) => {
  return apiClient.post<{ success: boolean; message: string }>(
    `/api/v1/alerts/channels/${channelType}/test`,
    { message }
  );
};

/**
 * 发送预警通知
 */
export const sendAlert = (params: {
  alert: {
    title: string;
    description: string;
    severity: string;
    alert_type: string;
  };
  channels?: string[];
  recipients?: string[];
}) => {
  return apiClient.post<AlertSendResponse>('/api/v1/alerts/send', params);
};

/**
 * 获取预警历史
 */
export const getAlertHistory = (params?: {
  limit?: number;
  offset?: number;
  severity?: string;
}) => {
  return apiClient.get<AlertHistoryResponse>('/api/v1/alerts/history', { params });
};

/**
 * 获取预警统计数据
 */
export const getAlertStatistics = (days: number = 30) => {
  return apiClient.get<AlertStatistics>('/api/v1/alerts/statistics', {
    params: { days },
  });
};

/**
 * 获取用户预警订阅列表
 */
export const getAlertSubscriptions = () => {
  return apiClient.get<AlertSubscriptionsResponse>('/api/v1/alerts/subscriptions');
};

/**
 * 创建预警订阅
 */
export const createAlertSubscription = (subscription: {
  alert_types: string[];
  severity_filter: string[];
  channels: string[];
  filters?: Record<string, unknown>;
}) => {
  return apiClient.post<AlertSubscription>('/api/v1/alerts/subscriptions', subscription);
};

/**
 * 更新预警订阅
 */
export const updateAlertSubscription = (subscriptionId: string, updates: Partial<AlertSubscription>) => {
  return apiClient.put<AlertSubscription>(`/api/v1/alerts/subscriptions/${subscriptionId}`, updates);
};

/**
 * 删除预警订阅
 */
export const deleteAlertSubscription = (subscriptionId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/alerts/subscriptions/${subscriptionId}`);
};

/**
 * 获取可订阅的预警类型
 */
export const getAvailableAlertTypes = () => {
  return apiClient.get<AlertTypesResponse>('/api/v1/alerts/available-types');
};

// ============= 增强型统一 SSO API =============

export interface SSOProvider {
  provider_id: string;
  provider_type: 'oidc' | 'saml' | 'cas' | 'oauth2' | 'sms' | 'qrcode' | 'wechat' | 'dingtalk';
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  icon: string;
  color: string;
}

export interface SSOProvidersResponse {
  providers: SSOProvider[];
  total: number;
}

export interface SMSVerificationResponse {
  success: boolean;
  message: string;
  expires_in?: number;
}

export interface QRCodeSession {
  session_id: string;
  status: 'pending' | 'scanned' | 'confirmed' | 'expired' | 'cancelled';
  qr_data: string;
  created_at: string;
  expires_at: string;
}

export interface QRCodeCreateResponse {
  session_id: string;
  qr_data: string;
  expires_at: string;
}

export interface OAuthURLResponse {
  success: boolean;
  auth_url?: string;
  provider?: string;
  message?: string;
}

export interface UserSession {
  session_id: string;
  user_id: string;
  provider: string;
  login_method: string;
  created_at: string;
  expires_at: string;
  last_activity: string;
  ip_address: string;
}

export interface UserSessionsResponse {
  sessions: UserSession[];
  total: number;
}

export interface SSOLogoutResponse {
  success: boolean;
  message: string;
  global: boolean;
}

/**
 * 列出所有 SSO 提供商
 */
export const listSSOProviders = (includeDisabled?: boolean) => {
  return apiClient.get<SSOProvidersResponse>('/api/v1/sso/providers', {
    params: { include_disabled: includeDisabled },
  });
};

/**
 * 获取指定 SSO 提供商配置
 */
export const getSSOProvider = (providerId: string) => {
  return apiClient.get<SSOProvider>(`/api/v1/sso/providers/${providerId}`);
};

/**
 * 添加新的 SSO 提供商
 */
export const addSSOProvider = (provider: {
  provider_id?: string;
  provider_type: string;
  name: string;
  enabled?: boolean;
  config: Record<string, unknown>;
  icon?: string;
  color?: string;
}) => {
  return apiClient.post<SSOProvider>('/api/v1/sso/providers', provider);
};

/**
 * 更新 SSO 提供商配置
 */
export const updateSSOProvider = (providerId: string, updates: Partial<SSOProvider>) => {
  return apiClient.put<SSOProvider>(`/api/v1/sso/providers/${providerId}`, updates);
};

/**
 * 删除 SSO 提供商
 */
export const deleteSSOProvider = (providerId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/sso/providers/${providerId}`);
};

/**
 * 发送短信验证码
 */
export const sendSMSVerification = (phone: string, purpose: string = 'login') => {
  return apiClient.post<SMSVerificationResponse>('/api/v1/sso/sms/send', { phone, purpose });
};

/**
 * 验证短信验证码并登录
 */
export const verifySMSCode = (phone: string, code: string, purpose: string = 'login') => {
  return apiClient.post<UserSession>('/api/v1/sso/sms/verify', { phone, code, purpose });
};

/**
 * 创建扫码登录会话
 */
export const createQRCodeSession = () => {
  return apiClient.post<QRCodeCreateResponse>('/api/v1/sso/qrcode/create', {});
};

/**
 * 获取二维码状态
 */
export const getQRCodeStatus = (sessionId: string) => {
  return apiClient.get<QRCodeSession>(`/api/v1/sso/qrcode/status/${sessionId}`);
};

/**
 * 扫描二维码（移动端调用）
 */
export const scanQRCode = (sessionId: string) => {
  return apiClient.post<{ success: boolean; message: string; status: string }>(
    `/api/v1/sso/qrcode/scan`,
    { session_id: sessionId }
  );
};

/**
 * 确认扫码登录（移动端调用）
 */
export const confirmQRCodeLogin = (sessionId: string) => {
  return apiClient.post<{ success: boolean; message: string; session_id: string; user_id: string }>(
    `/api/v1/sso/qrcode/confirm`,
    { session_id: sessionId }
  );
};

/**
 * 取消扫码登录
 */
export const cancelQRCodeLogin = (sessionId: string) => {
  return apiClient.post<{ cancelled: boolean }>(`/api/v1/sso/qrcode/cancel/${sessionId}`, {});
};

/**
 * 获取 OAuth 授权 URL
 */
export const getOAuthURL = (providerId: string, redirectUri: string, state?: string) => {
  return apiClient.get<OAuthURLResponse>('/api/v1/sso/oauth/url', {
    params: { provider_id: providerId, redirect_uri: redirectUri, state },
  });
};

/**
 * 处理 OAuth 回调
 */
export const handleOAuthCallback = (providerId: string, code: string, state?: string) => {
  return apiClient.post<{ success: boolean; user_id: string; session_id: string; provider: string }>(
    '/api/v1/sso/oauth/callback',
    { provider_id: providerId, code, state }
  );
};

/**
 * 获取会话信息
 */
export const getSessionInfo = (sessionId: string) => {
  return apiClient.get<UserSession>(`/api/v1/sso/sessions/${sessionId}`);
};

/**
 * 列出用户的所有活跃会话
 */
export const listUserSessions = (userId: string) => {
  return apiClient.get<UserSessionsResponse>(`/api/v1/sso/sessions/user/${userId}`);
};

/**
 * SSO 登出
 */
export const ssoLogout = (sessionId: string, globalLogout: boolean = false) => {
  return apiClient.post<SSOLogoutResponse>('/api/v1/sso/logout', {
    session_id: sessionId,
    global_logout: globalLogout,
  });
};

// ============= 数据服务接口管理 API =============

export interface APIDataService {
  service_id: string;
  name: string;
  description: string;
  service_type: 'rest' | 'graphql';
  source_type: 'table' | 'query' | 'dataset';
  source_config: Record<string, unknown>;
  endpoint: string;
  method: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  status: 'draft' | 'published' | 'archived';
  version: number;
  tags: string[];
  rate_limit?: { requests_per_minute: number };
}

export interface DataServicesListResponse {
  services: APIDataService[];
  total: number;
  limit: number;
  offset: number;
}

export interface APIKeyInfo {
  key_id: string;
  name: string;
  user_id: string;
  scopes: string[];
  created_at: string;
  expires_at: string | null;
  last_used: string | null;
  is_active: boolean;
}

export interface APIKeysListResponse {
  keys: APIKeyInfo[];
  total: number;
}

export interface APICallRecord {
  call_id: string;
  service_id: string;
  api_key_id: string;
  method: string;
  path: string;
  status_code: number;
  latency_ms: number;
  request_size: number;
  response_size: number;
  error_message: string;
  timestamp: string;
  ip_address: string;
}

export interface APICallRecordsResponse {
  records: APICallRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServiceStatistics {
  service_id: string;
  time_window_hours: number;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  qps: number;
  total_bytes: number;
}

export interface OverallStatistics {
  time_window_hours: number;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  active_services: number;
  active_keys: number;
  top_services: Array<{ service_id: string; calls: number; errors: number }>;
  status_codes: Record<number, number>;
}

/**
 * 列出数据服务
 */
export const listDataServices = (params?: {
  status?: string;
  service_type?: string;
  source_type?: string;
  tags?: string[];
  created_by?: string;
  limit?: number;
  offset?: number;
}) => {
  return apiClient.get<DataServicesListResponse>('/api/v1/data-services', { params });
};

/**
 * 创建数据服务
 */
export const createDataService = (service: {
  name: string;
  description?: string;
  service_type: 'rest' | 'graphql';
  source_type: 'table' | 'query' | 'dataset';
  source_config: Record<string, unknown>;
  endpoint: string;
  method?: string;
  tags?: string[];
  rate_limit?: { requests_per_minute: number };
}) => {
  return apiClient.post<APIDataService>('/api/v1/data-services', service);
};

/**
 * 获取数据服务详情
 */
export const getDataService = (serviceId: string) => {
  return apiClient.get<APIDataService>(`/api/v1/data-services/${serviceId}`);
};

/**
 * 更新数据服务
 */
export const updateDataService = (serviceId: string, updates: Partial<APIDataService>) => {
  return apiClient.put<APIDataService>(`/api/v1/data-services/${serviceId}`, updates);
};

/**
 * 删除数据服务
 */
export const deleteDataService = (serviceId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/data-services/${serviceId}`);
};

/**
 * 发布数据服务
 */
export const publishDataService = (serviceId: string) => {
  return apiClient.post<APIDataService>(`/api/v1/data-services/${serviceId}/publish`, {});
};

/**
 * 测试数据服务
 */
export const testDataService = (serviceId: string, params?: Record<string, unknown>) => {
  return apiClient.post<{ success: boolean; message: string; test_result?: unknown }>(
    `/api/v1/data-services/${serviceId}/test`,
    params
  );
};

/**
 * 列出 API Keys
 */
export const listAPIKeys = (params?: {
  include_expired?: boolean;
  include_inactive?: boolean;
}) => {
  return apiClient.get<APIKeysListResponse>('/api/v1/data-services/api-keys', { params });
};

/**
 * 创建 API Key
 */
export const createAPIKey = (key: {
  name: string;
  scopes?: string[];
  expires_days?: number;
}) => {
  return apiClient.post<APIKeyInfo & { key_secret: string }>('/api/v1/data-services/api-keys', key);
};

/**
 * 删除 API Key
 */
export const deleteAPIKey = (keyId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/data-services/api-keys/${keyId}`);
};

/**
 * 停用 API Key
 */
export const deactivateAPIKey = (keyId: string) => {
  return apiClient.post<{ deactivated: boolean }>(`/api/v1/data-services/api-keys/${keyId}/deactivate`, {});
};

/**
 * 获取 API 调用记录
 */
export const getAPICallRecords = (params?: {
  service_id?: string;
  api_key_id?: string;
  status_code?: number;
  limit?: number;
  offset?: number;
}) => {
  return apiClient.get<APICallRecordsResponse>('/api/v1/data-services/call-records', { params });
};

/**
 * 获取服务调用统计
 */
export const getServiceStatistics = (serviceId: string, timeWindowHours: number = 24) => {
  return apiClient.get<ServiceStatistics>(`/api/v1/data-services/${serviceId}/statistics`, {
    params: { time_window_hours: timeWindowHours },
  });
};

/**
 * 获取整体统计
 */
export const getOverallStatistics = (timeWindowHours: number = 24) => {
  return apiClient.get<OverallStatistics>('/api/v1/data-services/statistics/overall', {
    params: { time_window_hours: timeWindowHours },
  });
};

// ============= 统一门户 Portal API =============

export interface DashboardWidget {
  widget_id: string;
  widget_type: 'statistic' | 'chart' | 'list' | 'alert' | 'task';
  title: string;
  icon: string;
  size: 'small' | 'medium' | 'large' | 'full';
  position: { x: number; y: number; w: number; h: number };
  config: Record<string, unknown>;
  data_source?: string;
  enabled: boolean;
}

export interface WidgetDataValue {
  value?: number | string;
  trend?: number;
  trend_direction?: 'up' | 'down' | 'stable';
  total?: number;
  critical?: number;
  warning?: number;
  labels?: string[];
  series?: Array<{ name: string; data: number[] }>;
}

export interface PortalDashboardResponse {
  user_id: string;
  tenant_id: string;
  widgets: DashboardWidget[];
  widgets_data: Record<string, WidgetDataValue | Array<Record<string, unknown>>>;
  last_updated: string;
}

export interface QuickLink {
  link_id: string;
  title: string;
  description: string;
  url: string;
  icon: string;
  category: string;
  badge_count: number;
  new_window: boolean;
}

export interface QuickLinksResponse {
  links: QuickLink[];
  categories: string[];
}

export interface PortalNotification {
  notification_id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  content: string;
  source: string;
  action_url?: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  expires_at: string | null;
  created_at: string;
  read: boolean;
}

export interface PortalNotificationsResponse {
  notifications: PortalNotification[];
  total: number;
  unread_count: number;
}

export interface TodoItem {
  todo_id: string;
  title: string;
  description: string;
  source: string;
  priority: 'urgent' | 'high' | 'normal' | 'low';
  due_date: string | null;
  action_url?: string;
  created_at: string;
  completed: boolean;
  completed_at: string | null;
}

export interface TodosResponse {
  todos: TodoItem[];
  total: number;
  pending_count: number;
}

export interface UserLayout {
  user_id: string;
  layout_version: string;
  theme: string;
  widgets: DashboardWidget[];
  custom_links: QuickLink[];
  hide_defaults: boolean;
}

export interface SearchResult {
  id: string;
  type: string;
  title: string;
  description: string;
  category: string;
  url: string;
  icon: string;
  highlight?: string;
}

export interface GlobalSearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface SystemStatus {
  id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime_percent: number;
  last_check: string;
}

export interface SystemStatusResponse {
  systems: SystemStatus[];
  overall_status: 'healthy' | 'degraded' | 'down';
}

/**
 * 获取门户仪表盘数据
 */
export const getPortalDashboard = () => {
  return apiClient.get<PortalDashboardResponse>('/api/v1/portal/dashboard');
};

/**
 * 获取快捷入口
 */
export const getQuickLinks = (categories?: string[]) => {
  return apiClient.get<QuickLinksResponse>('/api/v1/portal/quick-links', {
    params: { categories },
  });
};

/**
 * 获取通知列表
 */
export const getPortalNotifications = (params?: {
  unread_only?: boolean;
  limit?: number;
}) => {
  return apiClient.get<PortalNotificationsResponse>('/api/v1/portal/notifications', { params });
};

/**
 * 标记通知为已读
 */
export const markNotificationRead = (notificationId: string) => {
  return apiClient.post<{ read: boolean }>(`/api/v1/portal/notifications/${notificationId}/read`, {});
};

/**
 * 标记所有通知为已读
 */
export const markAllNotificationsRead = () => {
  return apiClient.post<{ count: number }>('/api/v1/portal/notifications/read-all', {});
};

/**
 * 删除通知
 */
export const deleteNotification = (notificationId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/portal/notifications/${notificationId}`);
};

/**
 * 获取待办事项
 */
export const getPortalTodos = (params?: {
  status?: 'pending' | 'completed' | 'all';
  source?: string;
  limit?: number;
}) => {
  return apiClient.get<TodosResponse>('/api/v1/portal/todos', { params });
};

/**
 * 完成待办事项
 */
export const completeTodo = (todoId: string) => {
  return apiClient.post<{ completed: boolean }>(`/api/v1/portal/todos/${todoId}/complete`, {});
};

/**
 * 获取用户门户布局
 */
export const getUserLayout = () => {
  return apiClient.get<UserLayout>('/api/v1/portal/layout');
};

/**
 * 更新用户门户布局
 */
export const updateUserLayout = (layout: Partial<UserLayout>) => {
  return apiClient.put<{ updated: boolean }>('/api/v1/portal/layout', layout);
};

/**
 * 门户全局搜索
 */
export const portalGlobalSearch = (params: {
  query: string;
  categories?: string[];
  limit?: number;
}) => {
  return apiClient.get<GlobalSearchResponse>('/api/v1/portal/search', { params });
};

/**
 * 获取系统状态
 */
export const getSystemStatus = () => {
  return apiClient.get<SystemStatusResponse>('/api/v1/portal/system-status');
};

// ============= 统一通知管理 API =============

export interface NotificationChannelInfo {
  type: string;
  name: string;
  enabled: boolean;
}

export interface NotificationChannelsResponse {
  channels: NotificationChannelInfo[];
  total: number;
}

export interface NotificationTemplate {
  template_id: string;
  name: string;
  description: string;
  subject_template: string;
  body_template: string;
  type: 'info' | 'warning' | 'error' | 'success';
  supported_channels: string[];
  variables: string[];
  enabled: boolean;
}

export interface NotificationTemplatesResponse {
  templates: NotificationTemplate[];
  total: number;
}

export interface NotificationRule {
  rule_id: string;
  name: string;
  description: string;
  event_type: string;
  conditions: Record<string, unknown>;
  template_id: string;
  channels: string[];
  recipients: string[];
  enabled: boolean;
  throttle_minutes: number;
}

export interface NotificationRulesResponse {
  rules: NotificationRule[];
  total: number;
}

export interface NotificationHistoryItem {
  history_id: string;
  message_id: string;
  recipient: string;
  channel: string;
  status: 'pending' | 'sent' | 'failed';
  error_message: string | null;
  sent_at: string | null;
  retry_count: number;
}

export interface NotificationHistoryResponse {
  history: NotificationHistoryItem[];
  total: number;
}

export interface NotificationStatistics {
  period_days: number;
  total_notifications: number;
  sent: number;
  failed: number;
  success_rate: number;
  by_channel: Record<string, { total: number; sent: number; failed: number }>;
}

export interface SendNotificationRequest {
  recipients: string[];
  subject?: string;
  body?: string;
  channels?: string[];
  title?: string;
  type?: 'info' | 'warning' | 'error' | 'success';
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  action_url?: string;
  data?: Record<string, unknown>;
}

export interface SendNotificationByTemplateRequest {
  template_id: string;
  variables: Record<string, unknown>;
  recipients: string[];
  channels?: string[];
  action_url?: string;
}

export interface SendNotificationResponse {
  message_ids: string[];
  sent_count: number;
}

/**
 * 获取通知渠道列表
 */
export const getNotificationChannels = () => {
  return apiClient.get<NotificationChannelsResponse>('/api/v1/notifications/channels');
};

/**
 * 获取通知模板列表
 */
export const getNotificationTemplates = () => {
  return apiClient.get<NotificationTemplatesResponse>('/api/v1/notifications/templates');
};

/**
 * 获取通知模板详情
 */
export const getNotificationTemplate = (templateId: string) => {
  return apiClient.get<NotificationTemplate>(`/api/v1/notifications/templates/${templateId}`);
};

/**
 * 创建通知模板
 */
export const createNotificationTemplate = (template: {
  template_id?: string;
  name: string;
  description?: string;
  subject_template: string;
  body_template: string;
  type?: 'info' | 'warning' | 'error' | 'success';
  supported_channels?: string[];
  variables?: string[];
}) => {
  return apiClient.post<{ template_id: string }>('/api/v1/notifications/templates', template);
};

/**
 * 更新通知模板
 */
export const updateNotificationTemplate = (
  templateId: string,
  updates: Partial<NotificationTemplate>
) => {
  return apiClient.put<{ template_id: string }>(
    `/api/v1/notifications/templates/${templateId}`,
    updates
  );
};

/**
 * 删除通知模板
 */
export const deleteNotificationTemplate = (templateId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/notifications/templates/${templateId}`);
};

/**
 * 获取通知规则列表
 */
export const getNotificationRules = () => {
  return apiClient.get<NotificationRulesResponse>('/api/v1/notifications/rules');
};

/**
 * 获取通知规则详情
 */
export const getNotificationRule = (ruleId: string) => {
  return apiClient.get<NotificationRule>(`/api/v1/notifications/rules/${ruleId}`);
};

/**
 * 创建通知规则
 */
export const createNotificationRule = (rule: {
  rule_id?: string;
  name: string;
  description?: string;
  event_type: string;
  conditions?: Record<string, unknown>;
  template_id: string;
  channels?: string[];
  recipients: string[];
  throttle_minutes?: number;
}) => {
  return apiClient.post<{ rule_id: string }>('/api/v1/notifications/rules', rule);
};

/**
 * 更新通知规则
 */
export const updateNotificationRule = (ruleId: string, updates: Partial<NotificationRule>) => {
  return apiClient.put<{ rule_id: string }>(`/api/v1/notifications/rules/${ruleId}`, updates);
};

/**
 * 删除通知规则
 */
export const deleteNotificationRule = (ruleId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/notifications/rules/${ruleId}`);
};

/**
 * 启用通知规则
 */
export const enableNotificationRule = (ruleId: string) => {
  return apiClient.post<{ enabled: boolean }>(`/api/v1/notifications/rules/${ruleId}/enable`, {});
};

/**
 * 禁用通知规则
 */
export const disableNotificationRule = (ruleId: string) => {
  return apiClient.post<{ enabled: boolean }>(`/api/v1/notifications/rules/${ruleId}/disable`, {});
};

/**
 * 发送通知
 */
export const sendNotification = (request: SendNotificationRequest) => {
  return apiClient.post<SendNotificationResponse>('/api/v1/notifications/send', request);
};

/**
 * 使用模板发送通知
 */
export const sendNotificationByTemplate = (request: SendNotificationByTemplateRequest) => {
  return apiClient.post<SendNotificationResponse>('/api/v1/notifications/send', request);
};

/**
 * 触发通知事件
 */
export const triggerNotificationEvent = (event_type: string, event_data: Record<string, unknown>) => {
  return apiClient.post<SendNotificationResponse>('/api/v1/notifications/trigger', {
    event_type,
    event_data,
  });
};

/**
 * 获取通知历史
 */
export const getNotificationHistory = (params?: {
  recipient?: string;
  channel?: string;
  status?: string;
  limit?: number;
}) => {
  return apiClient.get<NotificationHistoryResponse>('/api/v1/notifications/history', { params });
};

/**
 * 获取通知统计
 */
export const getNotificationStatistics = (days: number = 30) => {
  return apiClient.get<NotificationStatistics>('/api/v1/notifications/statistics', {
    params: { days },
  });
};

// ============= 统一内容管理 API =============

export type ContentStatus = 'draft' | 'reviewing' | 'published' | 'archived';
export type ContentType = 'article' | 'announcement' | 'document' | 'tutorial' | 'faq' | 'news';

export interface ContentArticle {
  content_id: string;
  title: string;
  summary: string;
  content: string;
  content_type: ContentType;
  status: ContentStatus;
  category_id: string | null;
  tags: string[];
  author_id: string;
  author_name: string;
  cover_image: string;
  featured: boolean;
  allow_comment: boolean;
  view_count: number;
  like_count: number;
  comment_count: number;
  published_at: string | null;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, unknown>;
}

export interface ContentArticlesResponse {
  articles: ContentArticle[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContentCategory {
  category_id: string;
  name: string;
  description: string;
  parent_id: string | null;
  icon: string;
  sort_order: number;
  enabled: boolean;
}

export interface ContentCategoriesResponse {
  categories: ContentCategory[];
  total: number;
}

export interface ContentTag {
  tag_id: string;
  name: string;
  color: string;
  usage_count: number;
}

export interface ContentTagsResponse {
  tags: ContentTag[];
  total: number;
}

export interface ContentComment {
  comment_id: string;
  content_id: string;
  parent_id: string | null;
  user_id: string;
  user_name: string;
  user_avatar: string;
  content: string;
  like_count: number;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface ContentCommentsResponse {
  comments: ContentComment[];
  total: number;
}

export interface ContentStatistics {
  total_articles: number;
  total_categories: number;
  total_tags: number;
  total_comments: number;
  total_views: number;
  total_likes: number;
  status_counts: Record<string, number>;
  type_counts: Record<string, number>;
  featured_count: number;
}

/**
 * 获取内容文章列表
 */
export const getContentArticles = (params?: {
  content_type?: ContentType;
  status?: ContentStatus;
  category_id?: string;
  tag_id?: string;
  author_id?: string;
  featured?: boolean;
  keyword?: string;
  limit?: number;
  offset?: number;
}) => {
  return apiClient.get<ContentArticlesResponse>('/api/v1/content/articles', { params });
};

/**
 * 获取文章详情
 */
export const getContentArticle = (contentId: string) => {
  return apiClient.get<ContentArticle>(`/api/v1/content/articles/${contentId}`);
};

/**
 * 创建文章
 */
export const createContentArticle = (article: {
  title: string;
  content: string;
  content_type?: ContentType;
  author_id?: string;
  author_name?: string;
  summary?: string;
  category_id?: string;
  tags?: string[];
  cover_image?: string;
  featured?: boolean;
  allow_comment?: boolean;
  status?: ContentStatus;
  metadata?: Record<string, unknown>;
}) => {
  return apiClient.post<{ content_id: string }>('/api/v1/content/articles', article);
};

/**
 * 更新文章
 */
export const updateContentArticle = (
  contentId: string,
  updates: Partial<ContentArticle>
) => {
  return apiClient.put<{ content_id: string }>(`/api/v1/content/articles/${contentId}`, updates);
};

/**
 * 删除文章
 */
export const deleteContentArticle = (contentId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/content/articles/${contentId}`);
};

/**
 * 发布文章
 */
export const publishContentArticle = (contentId: string) => {
  return apiClient.post<ContentArticle>(`/api/v1/content/articles/${contentId}/publish`, {});
};

/**
 * 点赞文章
 */
export const likeContentArticle = (contentId: string) => {
  return apiClient.post<{ liked: boolean }>(`/api/v1/content/articles/${contentId}/like`, {});
};

/**
 * 获取内容分类列表
 */
export const getContentCategories = (enabledOnly?: boolean) => {
  return apiClient.get<ContentCategoriesResponse>('/api/v1/content/categories', {
    params: { enabled_only: enabledOnly },
  });
};

/**
 * 创建分类
 */
export const createContentCategory = (category: {
  name: string;
  description?: string;
  parent_id?: string;
  icon?: string;
  sort_order?: number;
}) => {
  return apiClient.post<{ category_id: string }>('/api/v1/content/categories', category);
};

/**
 * 获取内容标签列表
 */
export const getContentTags = () => {
  return apiClient.get<ContentTagsResponse>('/api/v1/content/tags');
};

/**
 * 创建标签
 */
export const createContentTag = (tag: {
  name: string;
  color?: string;
}) => {
  return apiClient.post<{ tag_id: string }>('/api/v1/content/tags', tag);
};

/**
 * 获取文章评论列表
 */
export const getContentComments = (contentId: string, params?: {
  status?: string;
  limit?: number;
}) => {
  return apiClient.get<ContentCommentsResponse>(`/api/v1/content/articles/${contentId}/comments`, { params });
};

/**
 * 创建评论
 */
export const createContentComment = (comment: {
  content_id: string;
  user_id?: string;
  user_name?: string;
  content: string;
  parent_id?: string;
  user_avatar?: string;
}) => {
  return apiClient.post<{ comment_id: string }>('/api/v1/content/comments', comment);
};

/**
 * 审核通过评论
 */
export const approveContentComment = (commentId: string) => {
  return apiClient.post<{ approved: boolean }>(`/api/v1/content/comments/${commentId}/approve`, {});
};

/**
 * 删除评论
 */
export const deleteContentComment = (commentId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/content/comments/${commentId}`);
};

/**
 * 搜索内容
 */
export const searchContent = (params: {
  q: string;
  content_type?: ContentType;
  limit?: number;
}) => {
  return apiClient.get<{ results: ContentArticle[]; total: number }>('/api/v1/content/search', { params });
};

/**
 * 获取内容统计
 */
export const getContentStatistics = () => {
  return apiClient.get<ContentStatistics>('/api/v1/content/statistics');
};

// ============= 元数据版本对比 API =============

export type ChangeType = 'added' | 'removed' | 'modified' | 'unchanged';

export interface FieldChange {
  change_type: ChangeType;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
}

export interface ColumnDiff {
  column_name: string;
  changes: FieldChange[];
  has_changes: boolean;
}

export interface TableDiff {
  table_name: string;
  added_columns: string[];
  removed_columns: string[];
  modified_columns: ColumnDiff[];
  unchanged_columns: string[];
  summary: string;
  is_new_table?: boolean;
  is_removed_table?: boolean;
}

export interface MetadataColumn {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  default_value: string | null;
  comment: string;
  max_length: number | null;
  decimal_places: number | null;
  auto_increment: boolean;
}

export interface MetadataTable {
  table_name: string;
  database: string;
  columns: Record<string, MetadataColumn>;
  indexes: Record<string, unknown>[];
  relations: Record<string, unknown>[];
  row_count: number;
  comment: string;
  engine: string;
  charset: string;
  collation: string;
}

export interface MetadataSnapshot {
  snapshot_id: string;
  version: string;
  database: string;
  tables: Record<string, MetadataTable>;
  created_at: string;
  created_by: string;
  description: string;
  tags: string[];
}

export interface MetadataSnapshotsResponse {
  snapshots: MetadataSnapshot[];
  total: number;
}

export interface MetadataComparisonResult {
  from_snapshot: {
    id: string;
    version: string;
    created_at: string;
  };
  to_snapshot: {
    id: string;
    version: string;
    created_at: string;
  };
  added_tables: string[];
  removed_tables: string[];
  modified_tables: string[];
  unchanged_tables: string[];
  table_diffs: Record<string, TableDiff>;
  summary: string;
}

export interface MigrationSQLResponse {
  sql_statements: Record<string, string[]>;
  summary: string;
}

export interface VersionHistoryItem {
  snapshot_id: string;
  version: string;
  created_at: string;
  created_by: string;
  description: string;
  table_count: number;
  table_exists?: boolean;
  column_count?: number;
}

export interface VersionHistoryResponse {
  history: VersionHistoryItem[];
  total: number;
}

/**
 * 获取元数据快照列表
 */
export const getMetadataSnapshots = (params?: {
  database?: string;
  limit?: number;
}) => {
  return apiClient.get<MetadataSnapshotsResponse>('/api/v1/metadata/snapshots', { params });
};

/**
 * 获取元数据快照详情
 */
export const getMetadataSnapshot = (snapshotId: string) => {
  return apiClient.get<MetadataSnapshot>(`/api/v1/metadata/snapshots/${snapshotId}`);
};

/**
 * 创建元数据快照
 */
export const createMetadataSnapshot = (snapshot: {
  version: string;
  database?: string;
  created_by?: string;
  description?: string;
  tags?: string[];
}) => {
  return apiClient.post<{ snapshot_id: string }>('/api/v1/metadata/snapshots', snapshot);
};

/**
 * 删除元数据快照
 */
export const deleteMetadataSnapshot = (snapshotId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/metadata/snapshots/${snapshotId}`);
};

/**
 * 对比两个元数据快照
 */
export const compareMetadataSnapshots = (fromSnapshotId: string, toSnapshotId: string) => {
  return apiClient.post<MetadataComparisonResult>('/api/v1/metadata/compare', {
    from_snapshot_id: fromSnapshotId,
    to_snapshot_id: toSnapshotId,
  });
};

/**
 * 获取迁移 SQL
 */
export const getMigrationSQL = (fromId: string, toId: string) => {
  return apiClient.get<MigrationSQLResponse>(`/api/v1/metadata/compare/${fromId}/${toId}/sql`);
};

/**
 * 获取元数据版本历史
 */
export const getMetadataVersionHistory = (params?: {
  database?: string;
  table_name?: string;
  limit?: number;
}) => {
  return apiClient.get<VersionHistoryResponse>('/api/v1/metadata/history', { params });
};

// ============= 智能任务调度 API =============

export type SchedulerTaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'skipped' | 'retrying';
export type SchedulerTaskPriority = 'critical' | 'high' | 'normal' | 'low';

export interface SchedulerTaskDependency {
  task_id: string;
  type: 'success' | 'completion' | 'failure';
  condition: Record<string, unknown>;
}

export interface SchedulerResourceRequirement {
  cpu_cores: number;
  memory_mb: number;
  gpu_count: number;
  gpu_memory_mb: number;
  disk_mb: number;
}

export interface SchedulerTaskMetrics {
  execution_time_ms: number;
  wait_time_ms: number;
  retry_count: number;
  last_error: string;
  last_success_time: string | null;
  last_failure_time: string | null;
  success_rate: number;
  avg_execution_time_ms: number;
}

export interface SchedulerTask {
  task_id: string;
  name: string;
  description: string;
  task_type: string;
  priority: SchedulerTaskPriority;
  status: SchedulerTaskStatus;
  dependencies: SchedulerTaskDependency[];
  resource_requirement: SchedulerResourceRequirement;
  estimated_duration_ms: number;
  timeout_ms: number;
  max_retries: number;
  retry_delay_ms: number;
  schedule_time: string | null;
  deadline: string | null;
  created_by: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metrics: SchedulerTaskMetrics;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface SchedulerTasksResponse {
  tasks: SchedulerTask[];
  total: number;
}

export interface SchedulerOptimizeResult {
  optimized_order: string[];
  total_tasks: number;
  estimated_completion_time: number;
}

export interface ResourceDemandPrediction {
  window_minutes: number;
  predicted_tasks: number;
  resource_demand: {
    cpu_cores: number;
    memory_mb: number;
    gpu_count: number;
  };
  resource_utilization: {
    cpu_percent: number;
    memory_percent: number;
    gpu_percent: number;
  };
  recommendations: string[];
}

export interface SchedulerStatistics {
  total_tasks: number;
  status_counts: Record<string, number>;
  queue_length: number;
  total_resources: SchedulerResourceRequirement;
  used_resources: SchedulerResourceRequirement;
  available_resources: SchedulerResourceRequirement;
  scheduling_stats: {
    total_scheduled: number;
    total_completed: number;
    total_failed: number;
    total_retries: number;
  };
}

/**
 * 获取调度任务列表
 */
export const getScheduledTasks = (params?: {
  status?: SchedulerTaskStatus;
  priority?: SchedulerTaskPriority;
  task_type?: string;
  limit?: number;
}) => {
  return apiClient.get<SchedulerTasksResponse>('/api/v1/scheduler/tasks', { params });
};

/**
 * 获取调度任务详情
 */
export const getScheduledTask = (taskId: string) => {
  return apiClient.get<SchedulerTask>(`/api/v1/scheduler/tasks/${taskId}`);
};

/**
 * 创建调度任务
 */
export const createScheduledTask = (task: {
  name: string;
  task_type?: string;
  priority?: SchedulerTaskPriority;
  description?: string;
  dependencies?: SchedulerTaskDependency[];
  resource_requirement?: Partial<SchedulerResourceRequirement>;
  estimated_duration_ms?: number;
  deadline?: string;
  created_by?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}) => {
  return apiClient.post<{ task_id: string }>('/api/v1/scheduler/tasks', task);
};

/**
 * 更新调度任务
 */
export const updateScheduledTask = (
  taskId: string,
  updates: Partial<SchedulerTask>
) => {
  return apiClient.put<{ task_id: string }>(`/api/v1/scheduler/tasks/${taskId}`, updates);
};

/**
 * 删除调度任务
 */
export const deleteScheduledTask = (taskId: string) => {
  return apiClient.delete<{ deleted: boolean }>(`/api/v1/scheduler/tasks/${taskId}`);
};

/**
 * 优化调度顺序
 */
export const optimizeSchedule = () => {
  return apiClient.post<SchedulerOptimizeResult>('/api/v1/scheduler/optimize', {});
};

/**
 * 获取资源需求预测
 */
export const getResourceDemand = (windowMinutes: number = 60) => {
  return apiClient.get<ResourceDemandPrediction>('/api/v1/scheduler/resource-demand', {
    params: { window_minutes: windowMinutes },
  });
};

/**
 * 获取调度统计
 */
export const getSchedulerStatistics = () => {
  return apiClient.get<SchedulerStatistics>('/api/v1/scheduler/statistics');
};

/**
 * 获取下一个可执行任务
 */
export const getNextTask = () => {
  return apiClient.post<SchedulerTask | null>('/api/v1/scheduler/next-task', {});
};

/**
 * 完成任务
 */
export const completeScheduledTask = (
  taskId: string,
  result: { success: boolean; error_message?: string; execution_time_ms?: number }
) => {
  return apiClient.post<SchedulerTask>(`/api/v1/scheduler/tasks/${taskId}/complete`, result);
};

// ============= 资产价值评估类型 =============

export type AssetValueLevel = 'S' | 'A' | 'B' | 'C';

export interface AssetValueScoreBreakdown {
  usage_score: number;
  business_score: number;
  quality_score: number;
  governance_score: number;
  overall_score: number;
  value_level: AssetValueLevel;
  details: {
    usage?: {
      daily_query_count: number;
      active_users: number;
      dependent_count: number;
      reuse_rate: number;
    };
    business?: {
      is_core_indicator: boolean;
      sla_level: string | null;
      business_domain: string | null;
      has_owner: boolean;
    };
    quality?: {
      completeness: number;
      accuracy: number;
      consistency: number;
      timeliness: number;
      has_quality_reports: boolean;
    };
    governance?: {
      has_owner: boolean;
      has_description: boolean;
      has_lineage: boolean;
      has_quality_rules: boolean;
      security_level: string | null;
    };
    weights?: Record<string, number>;
  };
}

export interface AssetValueMetrics {
  metrics_id: string;
  asset_id: string;
  asset_type: string;
  usage_metrics: {
    usage_frequency_score: number;
    daily_query_count: number;
    weekly_active_users: number;
    monthly_access_count: number;
    reuse_rate: number;
    dependent_asset_count: number;
    referencing_job_count: number;
    referencing_report_count: number;
  };
  business_metrics: {
    business_importance_score: number;
    business_domain: string | null;
    is_core_indicator: boolean;
    business_owner: string | null;
    sla_level: string | null;
  };
  quality_metrics: {
    quality_score: number;
    completeness_score: number;
    accuracy_score: number;
    consistency_score: number;
    timeliness_score: number;
  };
  governance_metrics: {
    governance_score: number;
    has_owner: boolean;
    has_description: boolean;
    has_lineage: boolean;
    has_quality_rules: boolean;
    security_level: string | null;
  };
  overall_value_score: number;
  asset_value_level: AssetValueLevel;
  weight_config: Record<string, number> | null;
  calculation_details: Record<string, unknown> | null;
  calculated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AssetValueRanking {
  rank: number;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  overall_score: number;
  value_level: AssetValueLevel;
  usage_score: number;
  business_score: number;
  quality_score: number;
  governance_score: number;
  calculated_at: string | null;
}

export interface AssetValueDistribution {
  counts: Record<AssetValueLevel, number>;
  percentages: Record<AssetValueLevel, number>;
  total: number;
}

export interface AssetValueReport {
  distribution: AssetValueDistribution;
  statistics: {
    average_score: number;
    min_score: number;
    max_score: number;
    total_assets: number;
  };
  dimension_averages: {
    usage: number;
    business: number;
    quality: number;
    governance: number;
  };
  top_assets: AssetValueRanking[];
}

export interface AssetValueHistory {
  history_id: string;
  asset_id: string;
  overall_value_score: number;
  asset_value_level: AssetValueLevel;
  usage_frequency_score: number;
  business_importance_score: number;
  quality_score: number;
  governance_score: number;
  evaluated_at: string;
}

export interface AssetValueAnalysis {
  asset_id: string;
  asset_name: string | null;
  asset_type: string | null;
  current_metrics: AssetValueMetrics;
  trend: {
    direction: 'up' | 'down' | 'stable';
    history: AssetValueHistory[];
  };
  recommendations: string[];
}

// ============= 资产价值评估 API =============

/**
 * 评估单个资产价值
 */
export const evaluateAssetValue = (
  assetId: string,
  params?: {
    business_config?: {
      domain_weights?: Record<string, number>;
    };
    weights?: {
      usage?: number;
      business?: number;
      quality?: number;
      governance?: number;
    };
  }
) => {
  return apiClient.post<{
    asset_id: string;
    score_breakdown: AssetValueScoreBreakdown;
    recommendations: string[];
  }>(`/api/v1/assets/value/evaluate/${assetId}`, params || {});
};

/**
 * 批量评估资产价值
 */
export const batchEvaluateAssetValues = (params: {
  asset_ids: string[];
  business_config?: {
    domain_weights?: Record<string, number>;
  };
}) => {
  return apiClient.post<{
    total: number;
    success_count: number;
    results: Array<{
      asset_id: string;
      status: 'success' | 'failed';
      score_breakdown?: AssetValueScoreBreakdown;
      error?: string;
    }>;
  }>('/api/v1/assets/value/batch-evaluate', params);
};

/**
 * 获取资产价值排名
 */
export const getAssetValueRanking = (params?: {
  limit?: number;
  offset?: number;
  asset_type?: string;
  value_level?: AssetValueLevel;
}) => {
  return apiClient.get<{
    ranking: AssetValueRanking[];
    total: number;
    filters: {
      asset_type: string | null;
      value_level: AssetValueLevel | null;
    };
    pagination: {
      limit: number;
      offset: number;
    };
  }>('/api/v1/assets/ranking', { params });
};

/**
 * 获取资产价值详细分析
 */
export const getAssetValueAnalysis = (assetId: string, params?: { trend_days?: number }) => {
  return apiClient.get<AssetValueAnalysis>(`/api/v1/assets/${assetId}/value-analysis`, { params });
};

/**
 * 获取资产价值分布报告
 */
export const getAssetValueReport = () => {
  return apiClient.get<AssetValueReport>('/api/v1/assets/value-report');
};

/**
 * 记录资产使用
 */
export const recordAssetUsage = (
  assetId: string,
  params: {
    usage_type?: 'query' | 'download' | 'api_call' | 'reference';
    source_type?: 'dashboard' | 'report' | 'etl_job' | 'api' | 'adhoc';
    source_id?: string;
    source_name?: string;
  }
) => {
  return apiClient.post<{
    recorded: boolean;
    asset_id: string;
    usage_type: string;
  }>(`/api/v1/assets/${assetId}/usage`, params);
};

/**
 * 更新资产业务配置
 */
export const updateAssetBusinessConfig = (
  assetId: string,
  config: {
    is_core_indicator?: boolean;
    sla_level?: 'gold' | 'silver' | 'bronze';
    business_domain?: string;
    business_owner?: string;
  }
) => {
  return apiClient.put<{
    asset_id: string;
    updated_config: {
      is_core_indicator: boolean;
      sla_level: string | null;
      business_domain: string | null;
      business_owner: string | null;
    };
  }>(`/api/v1/assets/${assetId}/business-config`, config);
};

// ============= 敏感数据自动扫描 API =============

export interface AutoScanProgress {
  task_id: string;
  status: string;
  mode: string;
  total_databases: number;
  scanned_databases: number;
  total_tables: number;
  scanned_tables: number;
  total_columns: number;
  scanned_columns: number;
  sensitive_found: number;
  progress_percent: number;
  started_at: string | null;
  completed_at: string | null;
  errors: string[];
}

export interface AutoScanSummary {
  total_databases_scanned: number;
  total_tables_scanned: number;
  total_columns_scanned: number;
  sensitive_columns_found: number;
  by_level: Record<string, number>;
  by_type: Record<string, number>;
  masking_rules_generated: number;
  metadata_updated: number;
}

export interface QuickCheckResult {
  column_name: string;
  is_sensitive: boolean;
  sensitivity_type: string | null;
  sensitivity_level: string | null;
  confidence: number;
  matched_pattern: string | null;
}

/**
 * 启动敏感数据自动扫描
 */
export const startSensitivityAutoScan = (params: {
  name?: string;
  mode?: 'incremental' | 'full';
  databases?: string[];
  exclude_databases?: string[];
  exclude_table_patterns?: string[];
  sample_size?: number;
  confidence_threshold?: number;
  auto_update_metadata?: boolean;
  auto_generate_masking_rules?: boolean;
}) => {
  return apiClient.post<AutoScanProgress>('/api/v1/sensitivity/auto-scan/start', params);
};

/**
 * 获取自动扫描进度
 */
export const getSensitivityAutoScanProgress = () => {
  return apiClient.get<AutoScanProgress>('/api/v1/sensitivity/auto-scan/progress');
};

/**
 * 取消自动扫描
 */
export const cancelSensitivityAutoScan = () => {
  return apiClient.post<{ cancelled: boolean }>('/api/v1/sensitivity/auto-scan/cancel', {});
};

/**
 * 获取自动扫描结果摘要
 */
export const getSensitivityAutoScanSummary = () => {
  return apiClient.get<AutoScanSummary>('/api/v1/sensitivity/auto-scan/summary');
};

/**
 * 快速敏感性检查（单列）
 */
export const quickSensitivityCheck = (params: {
  column_name: string;
  sample_values?: string[];
  column_type?: string;
}) => {
  return apiClient.post<QuickCheckResult>('/api/v1/sensitivity/auto-scan/quick-check', params);
};

// ============= Kettle 编排 API =============

export type KettlePipelineType = 'full_etl' | 'extract' | 'transform' | 'load';

export interface OrchestrationResult {
  request_id: string;
  status: string;
  pipeline_type: KettlePipelineType;
  name: string;
  source_info: {
    database: string;
    table: string;
    type: string;
  };
  target_info: {
    database: string;
    table: string;
  };
  ai_rules_applied: number;
  masking_rules_applied: number;
  kettle_xml_path: string | null;
  execution_result: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface OrchestrationListItem {
  request_id: string;
  name: string;
  pipeline_type: KettlePipelineType;
  status: string;
  source_table: string;
  target_table: string;
  created_at: string;
}

/**
 * 自动编排 Kettle 转换（元数据分析 → AI规则推荐 → 生成Kettle）
 */
export const orchestrateKettle = (params: {
  name?: string;
  pipeline_type?: KettlePipelineType;
  source_database: string;
  source_table: string;
  source_type?: string;
  target_database: string;
  target_table: string;
  enable_ai_cleaning?: boolean;
  enable_ai_masking?: boolean;
  enable_ai_imputation?: boolean;
  column_filter?: string[];
  auto_execute?: boolean;
  dry_run?: boolean;
}) => {
  return apiClient.post<OrchestrationResult>('/api/v1/kettle/orchestrate', params);
};

/**
 * 获取编排任务状态
 */
export const getOrchestrationStatus = (requestId: string) => {
  return apiClient.get<OrchestrationResult>(`/api/v1/kettle/orchestrate/${requestId}`);
};

/**
 * 获取编排任务列表
 */
export const listOrchestrations = (params?: { limit?: number }) => {
  return apiClient.get<{ tasks: OrchestrationListItem[] }>('/api/v1/kettle/orchestrate/list', { params });
};

/**
 * 获取生成的 Kettle 转换 XML
 */
export const getOrchestrationXML = (requestId: string) => {
  return apiClient.get<{ xml: string }>(`/api/v1/kettle/orchestrate/${requestId}/xml`);
};

// ============= 资产自动编目 API =============

export interface AutoCatalogResult {
  success: boolean;
  asset_id: string | null;
  asset_name: string | null;
  category: string | null;
  message: string;
  details: Record<string, unknown>;
}

export interface BatchCatalogResult {
  success: boolean;
  total_discovered: number;
  total_registered: number;
  skipped: number;
  errors: number;
  details: Array<{
    table_name: string;
    status: string;
    asset_id?: string;
    error?: string;
  }>;
}

export interface CatalogHistoryItem {
  asset_id: string;
  asset_name: string;
  source_table: string;
  target_table: string;
  category: string;
  created_at: string;
  created_by: string;
}

/**
 * ETL完成后自动注册目标表为数据资产
 */
export const autoCatalogFromETL = (params: {
  source_database: string;
  source_table: string;
  target_database: string;
  target_table: string;
  etl_task_id?: string;
  created_by?: string;
}) => {
  return apiClient.post<AutoCatalogResult>('/api/v1/assets/auto-catalog', params);
};

/**
 * 批量从元数据注册资产（全量同步）
 */
export const batchAutoCatalog = (params?: {
  database_name?: string;
  created_by?: string;
}) => {
  return apiClient.post<BatchCatalogResult>('/api/v1/assets/auto-catalog/batch', params || {});
};

/**
 * 获取自动编目历史
 */
export const getAutoCatalogHistory = (params?: { limit?: number }) => {
  return apiClient.get<{ history: CatalogHistoryItem[] }>('/api/v1/assets/auto-catalog/history', { params });
};

// ============= 元数据自动扫描 API =============

export interface MetadataAutoScanResult {
  success: boolean;
  database: string;
  tables_found: number;
  columns_found: number;
  tables_synced: number;
  ai_annotations: number;
  details: Array<{
    table_name: string;
    columns: number;
    synced: boolean;
    annotated: boolean;
  }>;
}

export interface DataProfileResult {
  database: string;
  table: string;
  row_count: number;
  columns: Array<{
    name: string;
    type: string;
    null_count: number;
    null_rate: number;
    distinct_count: number;
    min_value: string | null;
    max_value: string | null;
    avg_length: number | null;
    sample_values: string[];
  }>;
}

export interface MetadataScanHistoryItem {
  scan_id: string;
  database: string;
  tables_found: number;
  columns_found: number;
  ai_annotations: number;
  scanned_at: string;
  scanned_by: string;
}

/**
 * 自动扫描数据库结构并同步到元数据
 */
export const autoScanMetadata = (params: {
  connection_info: {
    type: string;
    host: string;
    port: number;
    username: string;
    password: string;
  };
  database_name: string;
  exclude_tables?: string[];
  ai_annotate?: boolean;
}) => {
  return apiClient.post<MetadataAutoScanResult>('/api/v1/metadata/auto-scan', params);
};

/**
 * 扫描并生成数据画像（列级统计）
 */
export const autoScanDataProfile = (params: {
  connection_info: {
    type: string;
    host: string;
    port: number;
    username: string;
    password: string;
  };
  database_name: string;
  table_name: string;
  sample_size?: number;
}) => {
  return apiClient.post<DataProfileResult>('/api/v1/metadata/auto-scan/profile', params);
};

/**
 * 获取元数据扫描历史
 */
export const getMetadataScanHistory = (params?: { limit?: number }) => {
  return apiClient.get<{ history: MetadataScanHistoryItem[] }>('/api/v1/metadata/auto-scan/history', { params });
};

// ============= 统一认证 (OAuth2 / API Key) API =============

export interface OAuth2Client {
  client_id: string;
  client_name: string;
  client_secret?: string;
  grant_types: string[];
  redirect_uris: string[];
  scopes: string[];
  status: 'active' | 'suspended' | 'revoked';
  created_at: string;
  created_by: string;
}

export interface OAuth2Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  scope?: string;
}

export interface AuthAPIKey {
  key_id: string;
  name: string;
  key_prefix: string;
  key_secret?: string;
  scopes: string[];
  allowed_ips: string[];
  rate_limit: number;
  status: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

export interface AuthAuditLog {
  log_id: string;
  user_id: string;
  event_type: string;
  event_status: string;
  ip_address: string;
  user_agent: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuthStatistics {
  total_logins: number;
  successful_logins: number;
  failed_logins: number;
  active_sessions: number;
  api_key_usage: number;
  oauth2_token_issued: number;
  by_event_type: Record<string, number>;
}

export interface ActiveSession {
  session_id: string;
  user_id: string;
  login_time: string;
  last_active: string;
  ip_address: string;
  user_agent: string;
}

/**
 * 注册 OAuth2 客户端
 */
export const registerOAuth2Client = (params: {
  client_name: string;
  grant_types: string[];
  redirect_uris?: string[];
  scopes?: string[];
}) => {
  return apiClient.post<OAuth2Client>('/api/v1/auth/oauth2/clients', params);
};

/**
 * 获取 OAuth2 客户端列表
 */
export const listOAuth2Clients = (params?: {
  page?: number;
  page_size?: number;
  status?: string;
}) => {
  return apiClient.get<{ clients: OAuth2Client[]; total: number }>('/api/v1/auth/oauth2/clients', { params });
};

/**
 * 更新 OAuth2 客户端状态
 */
export const updateOAuth2ClientStatus = (clientId: string, status: 'active' | 'suspended' | 'revoked') => {
  return apiClient.put<{ client_id: string; status: string }>(`/api/v1/auth/oauth2/clients/${clientId}/status`, { status });
};

/**
 * OAuth2 Token 端点
 */
export const requestOAuth2Token = (params: {
  grant_type: string;
  client_id: string;
  client_secret: string;
  scope?: string;
  code?: string;
  redirect_uri?: string;
}) => {
  return apiClient.post<OAuth2Token>('/api/v1/auth/oauth2/token', params);
};

/**
 * 撤销 Token
 */
export const revokeOAuth2Token = (params: {
  token_jti: string;
  token_type?: 'access' | 'refresh';
}) => {
  return apiClient.post<{ revoked: boolean }>('/api/v1/auth/oauth2/revoke', params);
};

/**
 * 创建 API Key
 */
export const createAuthAPIKey = (params: {
  name: string;
  scopes?: string[];
  allowed_ips?: string[];
  expires_days?: number;
  rate_limit?: number;
}) => {
  return apiClient.post<AuthAPIKey>('/api/v1/auth/api-keys', params);
};

/**
 * 获取当前用户 API Key 列表
 */
export const listAuthAPIKeys = (params?: {
  page?: number;
  page_size?: number;
}) => {
  return apiClient.get<{ keys: AuthAPIKey[]; total: number }>('/api/v1/auth/api-keys', { params });
};

/**
 * 撤销 API Key
 */
export const revokeAuthAPIKey = (keyId: string) => {
  return apiClient.post<{ revoked: boolean }>(`/api/v1/auth/api-keys/${keyId}/revoke`, {});
};

/**
 * 查询认证审计日志
 */
export const getAuthAuditLogs = (params?: {
  page?: number;
  page_size?: number;
  user_id?: string;
  event_type?: string;
  event_status?: string;
}) => {
  return apiClient.get<{ logs: AuthAuditLog[]; total: number }>('/api/v1/auth/audit-logs', { params });
};

/**
 * 获取认证统计
 */
export const getAuthStatistics = (params?: { days?: number }) => {
  return apiClient.get<AuthStatistics>('/api/v1/auth/statistics', { params });
};

/**
 * 查询活跃会话
 */
export const getActiveSessions = (params?: { user_id?: string }) => {
  return apiClient.get<{ sessions: ActiveSession[] }>('/api/v1/auth/sessions', { params });
};

/**
 * 强制用户登出
 */
export const forceLogout = (params: {
  user_id: string;
  reason?: string;
}) => {
  return apiClient.post<{ logged_out: boolean }>('/api/v1/auth/sessions/force-logout', params);
};

// ============= 审批工作流 API =============

export type ApprovalStatus = 'pending' | 'in_review' | 'approved' | 'rejected' | 'withdrawn' | 'expired';
export type ApprovalPriority = 'low' | 'normal' | 'high' | 'urgent';
export type ApprovalAction = 'approve' | 'reject' | 'delegate';

export interface ApprovalNode {
  node_id: string;
  name: string;
  type: string;
  approver_type: string;
  approver_value: string;
  order: number;
}

export interface ApprovalTemplate {
  template_id: string;
  name: string;
  description: string;
  business_type: string;
  category: string;
  nodes: ApprovalNode[];
  auto_approve_timeout_hours: number;
  allow_withdraw: boolean;
  status: string;
  created_at: string | null;
  created_by: string;
}

export interface ApprovalRequest {
  request_id: string;
  template_id: string;
  title: string;
  description: string;
  business_type: string;
  business_data: Record<string, unknown>;
  applicant_id: string;
  applicant_name: string;
  status: ApprovalStatus;
  current_node_id: string;
  current_node_order: number;
  total_nodes: number;
  priority: ApprovalPriority;
  submitted_at: string | null;
  completed_at: string | null;
  final_comment: string | null;
}

export interface ApprovalRecord {
  record_id: string;
  request_id: string;
  node_id: string;
  node_order: number;
  approver_id: string;
  approver_name: string;
  action: string;
  comment: string;
  delegate_to: string | null;
  created_at: string | null;
}

export interface ApprovalRequestDetail extends ApprovalRequest {
  records: ApprovalRecord[];
}

export interface ApprovalStatistics {
  total_requests: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  withdrawn_count: number;
  by_business_type: Record<string, number>;
}

/**
 * 获取审批模板列表
 */
export const listApprovalTemplates = (params?: {
  business_type?: string;
  category?: string;
}) => {
  return apiClient.get<{ templates: ApprovalTemplate[] }>('/api/v1/approval/templates', { params });
};

/**
 * 创建审批模板
 */
export const createApprovalTemplate = (params: {
  name: string;
  business_type: string;
  category?: string;
  nodes: Array<{
    name: string;
    type?: string;
    approver_type: string;
    approver_value: string;
  }>;
  description?: string;
}) => {
  return apiClient.post<{ template_id: string; message: string }>('/api/v1/approval/templates', params);
};

/**
 * 提交审批工单
 */
export const submitApprovalRequest = (params: {
  template_id: string;
  title: string;
  description?: string;
  business_data?: Record<string, unknown>;
  priority?: ApprovalPriority;
}) => {
  return apiClient.post<{
    request_id: string;
    message: string;
    current_node: string;
    total_nodes: number;
  }>('/api/v1/approval/requests', params);
};

/**
 * 获取审批工单详情
 */
export const getApprovalRequestDetail = (requestId: string) => {
  return apiClient.get<ApprovalRequestDetail>(`/api/v1/approval/requests/${requestId}`);
};

/**
 * 处理审批（审批/驳回/委派）
 */
export const processApproval = (
  requestId: string,
  params: {
    action: ApprovalAction;
    comment?: string;
    delegate_to?: string;
  }
) => {
  return apiClient.post<{
    success: boolean;
    message: string;
    new_status: string;
  }>(`/api/v1/approval/requests/${requestId}/process`, params);
};

/**
 * 撤回审批工单
 */
export const withdrawApprovalRequest = (requestId: string) => {
  return apiClient.post<{ success: boolean; message: string }>(`/api/v1/approval/requests/${requestId}/withdraw`, {});
};

/**
 * 获取待审批列表
 */
export const getPendingApprovals = (params?: {
  page?: number;
  page_size?: number;
}) => {
  return apiClient.get<{ total: number; items: ApprovalRequest[] }>('/api/v1/approval/pending', { params });
};

/**
 * 获取我的申请列表
 */
export const getMyApprovalRequests = (params?: {
  page?: number;
  page_size?: number;
  status?: ApprovalStatus;
}) => {
  return apiClient.get<{ total: number; items: ApprovalRequest[] }>('/api/v1/approval/my-requests', { params });
};

/**
 * 获取审批统计
 */
export const getApprovalStatistics = () => {
  return apiClient.get<ApprovalStatistics>('/api/v1/approval/statistics');
};

// ============= 表融合 API =============

export type JoinType = 'inner' | 'left' | 'right' | 'full' | 'cross';

export interface JoinKeyPair {
  source_column: string;
  target_column: string;
  confidence: number;
  match_type: string;
}

export interface JoinQualityScore {
  overall_score: number;
  match_rate: number;
  null_rate: number;
  duplicate_rate: number;
  type_compatibility: boolean;
  sample_size: number;
}

export interface JoinStrategyRecommendation {
  recommended_join_type: JoinType;
  join_keys: JoinKeyPair[];
  quality_score: JoinQualityScore;
  warnings: string[];
  alternatives: Array<{
    join_type: JoinType;
    reason: string;
  }>;
}

export interface JoinPathResult {
  tables: string[];
  paths: Array<{
    from_table: string;
    to_table: string;
    join_keys: JoinKeyPair[];
    confidence: number;
  }>;
}

export interface TableFusionAnalysis {
  tables: string[];
  join_keys: Record<string, JoinKeyPair[]>;
  quality_scores: Record<string, JoinQualityScore>;
  recommended_order: string[];
  recommended_strategy: string;
  warnings: string[];
}

/**
 * 检测潜在 JOIN 关联键
 */
export const detectJoinKeys = (params: {
  source_table: string;
  target_tables: string[];
  source_database?: string;
  target_database?: string;
  sample_size?: number;
}) => {
  return apiClient.post<Record<string, JoinKeyPair[]>>('/api/v1/fusion/detect-join-keys', params);
};

/**
 * 校验 JOIN 数据一致性
 */
export const validateJoin = (params: {
  source_table: string;
  source_key: string;
  target_table: string;
  target_key: string;
  source_database?: string;
  target_database?: string;
  sample_size?: number;
}) => {
  return apiClient.post<JoinQualityScore>('/api/v1/fusion/validate-join', params);
};

/**
 * 推荐最优 JOIN 策略
 */
export const recommendJoinStrategy = (params: {
  source_table: string;
  target_table: string;
  join_keys?: JoinKeyPair[];
  auto_detect?: boolean;
  source_database?: string;
  target_database?: string;
}) => {
  return apiClient.post<JoinStrategyRecommendation>('/api/v1/fusion/recommend-strategy', params);
};

/**
 * 生成 Kettle JOIN 步骤配置
 */
export const generateKettleJoinConfig = (params: {
  source_table: string;
  target_table: string;
  source_step_name?: string;
  target_step_name?: string;
  join_keys?: JoinKeyPair[];
  source_database?: string;
  target_database?: string;
}) => {
  return apiClient.post<{ kettle_config: string }>('/api/v1/fusion/generate-kettle-config', params);
};

/**
 * 检测多表 JOIN 路径
 */
export const detectJoinPath = (params: {
  tables: string[];
  database?: string;
  max_depth?: number;
}) => {
  return apiClient.post<JoinPathResult>('/api/v1/fusion/detect-join-path', params);
};

/**
 * 综合分析多表融合方案
 */
export const analyzeTableFusion = (params: {
  tables: string[];
  database?: string;
  primary_table?: string;
}) => {
  return apiClient.post<TableFusionAnalysis>('/api/v1/fusion/analyze-tables', params);
};

// ============= OpenMetadata 集成 API =============

export interface OpenMetadataStatus {
  available: boolean;
  enabled: boolean;
  host: string;
  port: number;
  api_version: string;
  health: boolean;
}

export interface OpenMetadataSyncResult {
  synced: number;
  failed: number;
  skipped: number;
  duration_ms: number;
}

export interface OpenMetadataLineage {
  entity: {
    id: string;
    name: string;
    type: string;
  };
  upstreamEdges: Array<{
    fromEntity: {
      type: string;
      fqn: string;
      name: string;
      description?: string;
    };
  }>;
  downstreamEdges: Array<{
    toEntity: {
      type: string;
      fqn: string;
      name: string;
      description?: string;
    };
  }>;
}

export interface OpenMetadataSearchResult {
  hits: {
    total: number;
    hits: Array<{
      _source: {
        id: string;
        name: string;
        description?: string;
        fullyQualifiedName: string;
        tableType?: string;
        database?: { name: string };
      };
    }>;
  };
}

/**
 * 获取 OpenMetadata 集成状态
 */
export const getOpenMetadataStatus = () => {
  return apiClient.get<OpenMetadataStatus>('/api/v1/openmetadata/status');
};

/**
 * 触发元数据同步到 OpenMetadata
 */
export const syncToOpenMetadata = (params?: {
  database_name?: string;
  table_names?: string[];
}) => {
  return apiClient.post<OpenMetadataSyncResult>('/api/v1/openmetadata/sync', params || {});
};

/**
 * 从 OpenMetadata 获取血缘关系
 */
export const getOpenMetadataLineage = (params: {
  database: string;
  table: string;
  upstream_depth?: number;
  downstream_depth?: number;
}) => {
  return apiClient.get<OpenMetadataLineage>('/api/v1/openmetadata/lineage', { params });
};

/**
 * 推送血缘关系到 OpenMetadata
 */
export const pushOpenMetadataLineage = (params: {
  source_db: string;
  source_table: string;
  target_db: string;
  target_table: string;
  description?: string;
  transformation?: string;
}) => {
  return apiClient.post('/api/v1/openmetadata/lineage', params);
};

/**
 * 通过 OpenMetadata 搜索
 */
export const searchOpenMetadata = (params: {
  q: string;
  limit?: number;
  offset?: number;
}) => {
  return apiClient.get<OpenMetadataSearchResult>('/api/v1/openmetadata/search', { params });
};

// ============= AI 能力增强 API =============

// ==================== Quality AI 类型 ====================

export interface QualityIssue {
  issue_type: string;
  issue_description: string;
  rule_type: string;
  rule_name: string;
  rule_config: Record<string, unknown>;
  priority: string;
  estimated_improvement: number;
}

export interface QualityAIAnalysisResponse {
  table_name: string;
  database_name?: string;
  issues_found: number;
  recommendations: QualityIssue[];
}

export interface QualityRuleTemplate {
  rule_name: string;
  rule_type: string;
  target_column: string;
  expression: string;
  description: string;
  severity: string;
  priority: number;
}

export interface QualityRuleTemplatesResponse {
  table_name: string;
  rules: QualityRuleTemplate[];
  total: number;
  fallback?: boolean;
}

export interface AlertRule {
  rule_name: string;
  metric_name: string;
  rule_type: string;
  condition: string;
  threshold_upper?: number;
  threshold_lower?: number;
  threshold_percent?: number;
  description: string;
  severity: string;
}

export interface AlertRulesResponse {
  metric_name: string;
  alert_rules: AlertRule[];
  total: number;
  statistics?: {
    count: number;
    mean: number;
    min: number;
    max: number;
  };
}

/**
 * AI 分析表的数据质量问题
 */
export const qualityAI = {
  analyzeTable: (params: {
    table_name: string;
    database_name?: string;
  }) => {
    return apiClient.post<ApiResponse<QualityAIAnalysisResponse>>(
      '/api/v1/quality/ai/analyze-table',
      params
    );
  },

  getRuleTemplates: (params: {
    table_name: string;
    columns: Array<{ name: string; type: string; description?: string }>;
  }) => {
    return apiClient.post<ApiResponse<QualityRuleTemplatesResponse>>(
      '/api/v1/quality/ai/rule-templates',
      params
    );
  },

  generateAlertRules: (params: {
    metric_name: string;
    historical_data: Array<{ value: number; timestamp?: string }>;
  }) => {
    return apiClient.post<ApiResponse<AlertRulesResponse>>(
      '/api/v1/quality/ai/alert-rules',
      params
    );
  },
};

// ==================== ETL AI 类型 ====================

export interface ColumnPattern {
  primary_keys: string[];
  timestamp_columns: string[];
  status_columns: string[];
  sensitive_columns: string[];
}

export interface DataSourceProfile {
  source_connection_id: string;
  table_name: string;
  column_count: number;
  columns: Record<string, {
    type: string;
    nullable: boolean;
    description?: string;
    sensitivity_type?: string;
    has_ai_annotation: boolean;
  }>;
  patterns: ColumnPattern;
  data_quality_score: number;
  recommendations: string[];
}

export interface Transformation {
  source_field: string;
  target_field: string;
  source_type: string;
  target_type: string;
  needs_conversion: boolean;
  sql?: string;
  description: string;
}

export interface FieldMappingResult {
  source_field: string;
  target_field: string;
  confidence: number;
  mapping_type: string;
  transformation: string;
}

export interface ETLAIResponse {
  mappings: FieldMappingResult[];
  source_count: number;
  target_count: number;
  mapped_count: number;
  coverage: number;
}

/**
 * ETL AI 能力
 */
export const etlAI = {
  profiling: (params: {
    source_connection_id: string;
    table_name?: string;
    sample_size?: number;
  }) => {
    return apiClient.post<ApiResponse<DataSourceProfile>>(
      '/api/v1/etl/ai/profiling',
      params
    );
  },

  suggestTransformation: (params: {
    source_columns: Array<{ name: string; type: string }>;
    target_columns: Array<{ name: string; type: string }>;
  }) => {
    return apiClient.post<ApiResponse<{ transformations: Transformation[]; total_count: number }>>(
      '/api/v1/etl/ai/transformation-suggest',
      params
    );
  },

  suggestFieldMapping: (params: {
    source_fields: Array<{ name: string; type: string }>;
    target_fields: Array<{ name: string; type: string }>;
  }) => {
    return apiClient.post<ApiResponse<ETLAIResponse>>(
      '/api/v1/etl/ai/field-mapping',
      params
    );
  },
};

// ==================== Assets AI 类型 ====================

export interface AssetValueScoreBreakdown {
  usage_score: number;
  business_score: number;
  quality_score: number;
  governance_score: number;
  overall_score: number;
}

export interface AssetValueAssessmentResponse {
  asset_id: string;
  asset_name: string;
  score_breakdown: AssetValueScoreBreakdown;
  value_level: 'S' | 'A' | 'B' | 'C';
  level_name: string;
  details: {
    usage: Record<string, unknown>;
    business: Record<string, unknown>;
    quality: Record<string, unknown>;
    governance: Record<string, unknown>;
  };
  recommendations: string[];
}

export interface AutoTagResponse {
  asset_id: string;
  suggested_tags: string[];
  confidence: number[];
  reasons: string[];
  existing_tags: string[];
}

/**
 * Assets AI 能力
 */
export const assetsAI = {
  assessValue: (params: {
    asset_id: string;
    metrics?: {
      lookback_days?: number;
    };
  }) => {
    return apiClient.post<ApiResponse<AssetValueAssessmentResponse>>(
      '/api/v1/assets/ai/value-assess',
      params
    );
  },

  autoTag: (params: {
    asset_id: string;
    context?: Record<string, unknown>;
  }) => {
    return apiClient.post<ApiResponse<AutoTagResponse>>(
      '/api/v1/assets/ai/auto-tag',
      params
    );
  },

  getRecommendations: (params: {
    asset_id: string;
    limit?: number;
  }) => {
    return apiClient.get<ApiResponse<{ recommendations: DataAsset[] }>>(
      `/api/v1/assets/ai/recommend/${params.asset_id}`,
      { params: { limit: params.limit || 10 } }
    );
  },
};

// ==================== Sensitivity AI 类型 ====================

export interface SensitivityColumnResult {
  column_name: string;
  is_sensitive: boolean;
  sensitivity_type: 'pii' | 'financial' | 'health' | 'credential' | 'none';
  sensitivity_sub_type?: string;
  sensitivity_level: 'public' | 'internal' | 'confidential' | 'restricted';
  confidence: number;
  matched_by: string;
  masking_strategy?: string;
  sample_count?: number;
  ai_reason?: string;
  error?: string;
}

export interface SensitivityScanResponse {
  table_name: string;
  dataset_id?: string;
  columns_scanned: number;
  sensitive_found: number;
  breakdown: Record<string, number>;
  results: SensitivityColumnResult[];
}

export interface SensitivityBatchScanResponse {
  task_id: string;
  status: string;
  tables_count: number;
  databases_count: number;
  progress: Record<string, unknown>;
}

export interface SensitivityScanResultResponse {
  task_id: string;
  status: string;
  progress_percent?: number;
  total_databases?: number;
  total_tables?: number;
  total_columns?: number;
  scanned_columns?: number;
  sensitive_found?: number;
  breakdown?: {
    pii: number;
    financial: number;
    health: number;
    credential: number;
  };
  metadata_updated?: number;
  masking_rules_created?: number;
  duration_seconds?: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  sensitive_columns?: Array<{
    database: string;
    table: string;
    column: string;
    type: string;
    sub_type: string;
    level: string;
    confidence: number;
  }>;
}

/**
 * Sensitivity AI 能力
 */
export const sensitivityAI = {
  scan: (params: {
    table_name?: string;
    dataset_id?: string;
    columns?: Array<{ name: string; type: string }>;
    sample_size?: number;
  }) => {
    return apiClient.post<ApiResponse<SensitivityScanResponse>>(
      '/api/v1/sensitivity/ai/scan',
      params
    );
  },

  batchScan: (params: {
    tables?: string[];
    databases?: string[];
    options?: {
      sample_size?: number;
      confidence_threshold?: number;
      auto_update_metadata?: boolean;
      auto_generate_masking_rules?: boolean;
    };
  }) => {
    return apiClient.post<ApiResponse<SensitivityBatchScanResponse>>(
      '/api/v1/sensitivity/ai/scan-batch',
      params
    );
  },

  getScanResult: (taskId: string) => {
    return apiClient.get<ApiResponse<SensitivityScanResultResponse>>(
      `/api/v1/sensitivity/ai/scan-result/${taskId}`
    );
  },
};

// ============= OCR服务 =============

export interface OCRTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  template_type: string;
  category?: string;
  extraction_rules: Record<string, unknown>;
  is_active: boolean;
  is_public: boolean;
  version: number;
  usage_count: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  template_type: string;
  category?: string;
  extraction_rules: Record<string, unknown>;
  ai_prompt_template?: string;
  post_processing?: Record<string, unknown>;
}

export interface UpdateTemplateRequest {
  name?: string;
  description?: string;
  category?: string;
  extraction_rules?: Record<string, unknown>;
  ai_prompt_template?: string;
  post_processing?: Record<string, unknown>;
  is_active?: boolean;
}

export interface OCRTaskResponse {
  id: string;
  document_name: string;
  document_type: string;
  status: string;
  progress: number;
  created_at: string;
  result_summary?: Record<string, unknown>;
  error_message?: string;
}

export interface OCRTaskResult {
  task_id: string;
  document_type: string;
  status: string;
  structured_data: Record<string, unknown>;
  raw_text?: string;
  tables: unknown[];
  confidence_score: number;
  validation_issues: unknown[];
  cross_field_validation?: {
    valid: boolean;
    errors?: Array<{
      rule: string;
      description: string;
      expected?: unknown;
      actual?: unknown;
    }>;
    warnings?: Array<{
      rule: string;
      description: string;
      expected?: unknown;
      actual?: unknown;
    }>;
  };
  layout_info?: {
    has_signatures: boolean;
    has_seals: boolean;
    signature_regions?: Array<{
      label: string;
      page?: number;
      bbox?: number[];
    }>;
    seal_regions?: Array<{
      label: string;
      page?: number;
      bbox?: number[];
    }>;
  };
  completeness?: {
    valid: boolean;
    completeness_rate: number;
    missing_required?: Array<{
      name: string;
      key: string;
    }>;
  };
}

export const ocrService = {
  // 获取模板列表
  listTemplates: (params?: {
    template_type?: string;
    category?: string;
    is_active?: boolean;
    include_public?: boolean;
  }) => {
    return apiClient.get<OCRTemplate[]>('/api/v1/ocr/templates', { params });
  },

  // 获取模板详情
  getTemplate: (templateId: string) => {
    return apiClient.get<OCRTemplate>(`/api/v1/ocr/templates/${templateId}`);
  },

  // 创建模板
  createTemplate: (data: CreateTemplateRequest) => {
    return apiClient.post<OCRTemplate>('/api/v1/ocr/templates', data);
  },

  // 更新模板
  updateTemplate: (templateId: string, data: UpdateTemplateRequest) => {
    return apiClient.put<OCRTemplate>(`/api/v1/ocr/templates/${templateId}`, data);
  },

  // 删除模板
  deleteTemplate: (templateId: string) => {
    return apiClient.delete<{ message: string }>(`/api/v1/ocr/templates/${templateId}`);
  },

  // 加载默认模板
  loadDefaultTemplates: () => {
    return apiClient.post<{ message: string }>('/api/v1/ocr/templates/load-defaults');
  },

  // 获取支持的文档类型
  getDocumentTypes: () => {
    return apiClient.get<Record<string, string>>('/api/v1/ocr/templates/types');
  },

  // 创建OCR任务
  createTask: (data: {
    file: File;
    extraction_type?: string;
    template_id?: string;
    extraction_config?: Record<string, unknown>;
  }) => {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.extraction_type) {
      formData.append('extraction_type', data.extraction_type);
    }
    if (data.template_id) {
      formData.append('template_id', data.template_id);
    }
    if (data.extraction_config) {
      formData.append('extraction_config', JSON.stringify(data.extraction_config));
    }

    return apiClient.post<OCRTaskResponse>('/api/v1/ocr/tasks', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 批量创建任务
  createBatchTasks: (files: File[], extraction_type: string = 'auto') => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('extraction_type', extraction_type);

    return apiClient.post<{ task_ids: string[] }>('/api/v1/ocr/tasks/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 获取任务列表
  getTasks: (params?: {
    status?: string;
    document_type?: string;
    page?: number;
    page_size?: number;
  }) => {
    return apiClient.get<{ total: number; tasks: OCRTaskResponse[] }>('/api/v1/ocr/tasks', { params });
  },

  // 获取任务详情
  getTask: (taskId: string) => {
    return apiClient.get<OCRTaskResponse>(`/api/v1/ocr/tasks/${taskId}`);
  },

  // 获取任务结果
  getTaskResult: (taskId: string) => {
    return apiClient.get<OCRTaskResult>(`/api/v1/ocr/tasks/${taskId}/result`);
  },

  // 获取增强结果
  getEnhancedResult: (taskId: string) => {
    return apiClient.get<OCRTaskResult>(`/api/v1/ocr/tasks/${taskId}/result/enhanced`);
  },

  // 检测文档类型
  detectDocumentType: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post<{
      type: string;
      confidence: number;
      alternatives?: Array<{ type: string; confidence: number }>;
    }>('/api/v1/ocr/detect-type', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 预览模板提取
  previewWithTemplate: (file: File, templateConfig: Record<string, unknown>) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_config', JSON.stringify(templateConfig));

    return apiClient.post<OCRTaskResult>('/api/v1/ocr/templates/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};
