/**
 * AllData 服务 - 数据层 (DataOps) 统一 API
 *
 * 这是一个面向数据治理的统一服务接口，提供清晰的 API 用于：
 * - 元数据管理
 * - AI 标注
 * - 敏感数据检测
 * - 数据集管理
 * - 列模式管理
 * - 数据血缘
 * - 通知管理
 * - 任务调度
 * - 内容管理
 */

import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

// AI 标注类型
export interface AIAnnotation {
  column_name: string;
  ai_description?: string;
  sensitivity_level: 'public' | 'internal' | 'confidential' | 'restricted';
  sensitivity_type: 'pii' | 'financial' | 'health' | 'credential' | 'none';
  semantic_tags: string[];
  ai_confidence: number;
  annotated_at?: string;
}

// 敏感数据报告
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

// 列模式
export interface ColumnSchema {
  name: string;
  type: string;
  description?: string;
  nullable?: boolean;
  primary_key?: boolean;
  foreign_key?: {
    table: string;
    column: string;
  };
  ai_description?: string;
  sensitivity_level?: 'public' | 'internal' | 'confidential' | 'restricted';
  sensitivity_type?: 'pii' | 'financial' | 'health' | 'credential' | 'none';
  semantic_tags?: string[];
}

// 数据集统计
export interface DatasetStatistics {
  row_count: number;
  size_bytes: number;
}

// 数据集
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

// 创建数据集请求
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

// 更新数据集请求
export interface UpdateDatasetRequest {
  name?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

// 数据集列表参数
export interface DatasetListParams {
  tags?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

// 数据集列表响应
export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
  page: number;
  page_size: number;
}

// 数据集版本
export interface DatasetVersion {
  version_id: string;
  version_number: number;
  description?: string;
  created_at: string;
  row_count?: number;
  size_bytes?: number;
}

// 血缘节点
export interface LineageNode {
  id: string;
  type: 'table' | 'view' | 'column' | 'etl_task' | 'dataset';
  name: string;
  schema?: string;
  database?: string;
  source_type?: string;
  properties?: Record<string, unknown>;
}

// 血缘边
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

// 血缘图
export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  layout?: 'hierarchical' | 'force' | 'circular';
}

// 列血缘
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

// 影响分析
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

// 通知类型
export interface Notification {
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

// 通知列表响应
export interface NotificationsResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

// 通知渠道
export interface NotificationChannel {
  type: string;
  name: string;
  enabled: boolean;
}

// 通知模板
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

// 通知规则
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

// 调度任务状态
export type ScheduledTaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'skipped' | 'retrying';

// 调度任务优先级
export type ScheduledTaskPriority = 'critical' | 'high' | 'normal' | 'low';

// 调度任务依赖
export interface ScheduledTaskDependency {
  task_id: string;
  type: 'success' | 'completion' | 'failure';
  condition: Record<string, unknown>;
}

// 调度资源需求
export interface ScheduledResourceRequirement {
  cpu_cores: number;
  memory_mb: number;
  gpu_count: number;
  gpu_memory_mb: number;
  disk_mb: number;
}

// 调度任务指标
export interface ScheduledTaskMetrics {
  execution_time_ms: number;
  wait_time_ms: number;
  retry_count: number;
  last_error: string;
  last_success_time: string | null;
  last_failure_time: string | null;
  success_rate: number;
  avg_execution_time_ms: number;
}

// 调度任务
export interface ScheduledTask {
  task_id: string;
  name: string;
  description: string;
  task_type: string;
  priority: ScheduledTaskPriority;
  status: ScheduledTaskStatus;
  dependencies: ScheduledTaskDependency[];
  resource_requirement: ScheduledResourceRequirement;
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
  metrics: ScheduledTaskMetrics;
  tags: string[];
  metadata: Record<string, unknown>;
}

// 调度任务列表响应
export interface ScheduledTasksResponse {
  tasks: ScheduledTask[];
  total: number;
}

// 调度统计
export interface SchedulerStatistics {
  total_tasks: number;
  status_counts: Record<string, number>;
  queue_length: number;
  total_resources: ScheduledResourceRequirement;
  used_resources: ScheduledResourceRequirement;
  available_resources: ScheduledResourceRequirement;
  scheduling_stats: {
    total_scheduled: number;
    total_completed: number;
    total_failed: number;
    total_retries: number;
  };
}

// 元数据表
export interface MetadataTable {
  table_id: string;
  table_name: string;
  database: string;
  schema_name?: string;
  description?: string;
  table_type: string;
  row_count?: number;
  column_count?: number;
  created_at?: string;
  updated_at?: string;
  owner?: string;
}

// 元数据列
export interface MetadataColumn {
  column_id: string;
  column_name: string;
  table_id: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  description?: string;
  ai_description?: string;
  sensitivity_level?: string;
  sensitivity_type?: string;
  semantic_tags?: string[];
}

// 内容项
export interface ContentItem {
  content_id: string;
  title: string;
  content_type: 'document' | 'report' | 'dashboard' | 'query' | 'dataset';
  description?: string;
  content: string | Record<string, unknown>;
  tags?: string[];
  category?: string;
  author: string;
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  updated_at?: string;
  published_at?: string;
  view_count?: number;
  like_count?: number;
}

// 创建内容请求
export interface CreateContentRequest {
  title: string;
  content_type: 'document' | 'report' | 'dashboard' | 'query' | 'dataset';
  description?: string;
  content: string | Record<string, unknown>;
  tags?: string[];
  category?: string;
}

// 更新内容请求
export interface UpdateContentRequest {
  title?: string;
  description?: string;
  content?: string | Record<string, unknown>;
  tags?: string[];
  category?: string;
  status?: 'draft' | 'published' | 'archived';
}

// 内容列表响应
export interface ContentListResponse {
  items: ContentItem[];
  total: number;
  page: number;
  page_size: number;
}

// SQL 血缘解析结果
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

// AI 影响分析
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

// 敏感数据扫描结果
export interface SensitivityScanResult {
  scan_id: string;
  database: string;
  table: string;
  scanned_at: string;
  total_columns: number;
  sensitive_columns: number;
  scan_duration_ms: number;
  findings: Array<{
    column: string;
    sensitivity_level: string;
    sensitivity_type: string;
    confidence: number;
    recommendation?: string;
  }>;
}

// ============= API 实现 =============

// ---------- 元数据 API ----------

/**
 * 获取元数据表列表
 */
export async function getMetadata(params?: {
  database?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tables: MetadataTable[]; total: number }>> {
  return apiClient.get('/api/v1/data/metadata/tables', { params });
}

/**
 * 获取单个表的元数据
 */
export async function getTableMetadata(
  database: string,
  table: string
): Promise<ApiResponse<MetadataTable & { columns: MetadataColumn[] }>> {
  return apiClient.get(`/api/v1/data/metadata/databases/${database}/tables/${table}`);
}

/**
 * 更新表元数据
 */
export async function updateMetadata(
  database: string,
  table: string,
  data: {
    description?: string;
    tags?: string[];
    owner?: string;
  }
): Promise<ApiResponse<MetadataTable>> {
  return apiClient.put(`/api/v1/data/metadata/databases/${database}/tables/${table}`, data);
}

/**
 * 刷新元数据
 */
export async function refreshMetadata(
  database: string,
  table?: string
): Promise<ApiResponse<{ refreshed: boolean; tables_count: number }>> {
  return apiClient.post('/api/v1/data/metadata/refresh', { database, table });
}

/**
 * 搜索元数据
 */
export async function searchMetadata(
  query: string,
  options?: {
    limit?: number;
    type?: 'table' | 'column' | 'all';
  }
): Promise<ApiResponse<{
  results: Array<{
    type: 'table' | 'column';
    database: string;
    table: string;
    column?: string;
    description?: string;
    relevance_score: number;
  }>;
  total: number;
}>> {
  return apiClient.get('/api/v1/data/metadata/search', {
    params: { query, ...options },
  });
}

// ---------- AI 标注 API ----------

/**
 * 获取 AI 标注
 */
export async function getAIAnnotations(
  database: string,
  table: string
): Promise<ApiResponse<{ annotations: AIAnnotation[] }>> {
  return apiClient.get(`/api/v1/data/ai/annotations/${database}/${table}`);
}

/**
 * 创建 AI 标注 (对单列)
 */
export async function createAIAnnotation(
  database: string,
  table: string,
  column: string,
  options?: { use_llm?: boolean }
): Promise<ApiResponse<AIAnnotation>> {
  return apiClient.post('/api/v1/data/ai/annotate/column', {
    database,
    table,
    column,
    use_llm: options?.use_llm ?? true,
  });
}

/**
 * 批量创建 AI 标注 (对整个表)
 */
export async function createTableAIAnnotations(
  database: string,
  table: string,
  options?: { use_llm?: boolean; save?: boolean }
): Promise<ApiResponse<{ annotations: AIAnnotation[] }>> {
  return apiClient.post('/api/v1/data/ai/annotate/table', {
    database,
    table,
    use_llm: options?.use_llm ?? true,
    save: options?.save ?? true,
  });
}

/**
 * 更新 AI 标注
 */
export async function updateAIAnnotation(
  database: string,
  table: string,
  column: string,
  annotation: Partial<Omit<AIAnnotation, 'column_name'>>
): Promise<ApiResponse<AIAnnotation>> {
  return apiClient.put(`/api/v1/data/ai/annotations/${database}/${table}/${column}`, annotation);
}

/**
 * 删除 AI 标注
 */
export async function deleteAIAnnotation(
  database: string,
  table: string,
  column: string
): Promise<ApiResponse<{ deleted: boolean }>> {
  return apiClient.delete(`/api/v1/data/ai/annotations/${database}/${table}/${column}`);
}

/**
 * 获取 AI 标注服务状态
 */
export async function getAIAnnotationStatus(): Promise<ApiResponse<{
  enabled: boolean;
  model: string;
  api_url: string;
}>> {
  return apiClient.get('/api/v1/data/ai/annotation-status');
}

// ---------- 敏感数据 API ----------

/**
 * 获取敏感数据报告
 */
export async function getSensitivityReport(
  database: string,
  table: string
): Promise<ApiResponse<SensitivityReport>> {
  return apiClient.post('/api/v1/data/sensitivity/report', {
    database,
    table,
  });
}

/**
 * 扫描敏感数据
 */
export async function scanForSensitiveData(
  database: string,
  table?: string,
  options?: {
    columns?: string[];
    sensitivity_types?: string[];
    min_confidence?: number;
  }
): Promise<ApiResponse<SensitivityScanResult>> {
  return apiClient.post('/api/v1/data/sensitivity/scan', {
    database,
    table,
    ...options,
  });
}

/**
 * 获取敏感数据扫描历史
 */
export async function getSensitivityScanHistory(params?: {
  database?: string;
  table?: string;
  limit?: number;
}): Promise<ApiResponse<{ scans: SensitivityScanResult[]; total: number }>> {
  return apiClient.get('/api/v1/data/sensitivity/history', { params });
}

/**
 * 应用敏感数据策略
 */
export async function applySensitivityPolicy(
  database: string,
  table: string,
  policy: {
    columns: string[];
    masking_rule?: string;
    access_level?: string;
  }
): Promise<ApiResponse<{ applied: boolean; columns_affected: number }>> {
  return apiClient.post('/api/v1/data/sensitivity/apply-policy', {
    database,
    table,
    ...policy,
  });
}

// ---------- 数据集 API ----------

/**
 * 获取数据集列表
 */
export async function getDatasets(params?: DatasetListParams): Promise<ApiResponse<DatasetListResponse>> {
  return apiClient.get('/api/v1/data/datasets', { params });
}

/**
 * 获取数据集详情
 */
export async function getDataset(datasetId: string): Promise<ApiResponse<Dataset>> {
  return apiClient.get(`/api/v1/data/datasets/${datasetId}`);
}

/**
 * 创建数据集
 */
export async function createDataset(
  data: CreateDatasetRequest
): Promise<ApiResponse<{ dataset_id: string; name: string; status: string; created_at: string }>> {
  return apiClient.post('/api/v1/data/datasets', data);
}

/**
 * 更新数据集
 */
export async function updateDataset(
  datasetId: string,
  data: UpdateDatasetRequest
): Promise<ApiResponse<Dataset>> {
  return apiClient.put(`/api/v1/data/datasets/${datasetId}`, data);
}

/**
 * 删除数据集
 */
export async function deleteDataset(datasetId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/data/datasets/${datasetId}`);
}

/**
 * 获取数据集预览
 */
export async function getDatasetPreview(
  datasetId: string,
  limit?: number
): Promise<ApiResponse<{
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
}>> {
  return apiClient.get(`/api/v1/data/datasets/${datasetId}/preview`, {
    params: { limit },
  });
}

/**
 * 获取数据集版本列表
 */
export async function getDatasetVersions(datasetId: string): Promise<ApiResponse<{ versions: DatasetVersion[] }>> {
  return apiClient.get(`/api/v1/data/datasets/${datasetId}/versions`);
}

// ---------- 列模式 API ----------

/**
 * 获取列模式
 */
export async function getColumnSchema(
  database: string,
  table: string
): Promise<ApiResponse<{ columns: ColumnSchema[] }>> {
  return apiClient.get(`/api/v1/data/schema/${database}/${table}/columns`);
}

/**
 * 更新列模式
 */
export async function updateColumnSchema(
  database: string,
  table: string,
  column: string,
  schema: Partial<ColumnSchema>
): Promise<ApiResponse<ColumnSchema>> {
  return apiClient.put(`/api/v1/data/schema/${database}/${table}/columns/${column}`, schema);
}

/**
 * 验证列模式
 */
export async function validateColumnSchema(
  database: string,
  table: string,
  schema: { columns: Partial<ColumnSchema>[] }
): Promise<ApiResponse<{
  valid: boolean;
  errors: Array<{ column: string; error: string }>;
}>> {
  return apiClient.post(`/api/v1/data/schema/${database}/${table}/validate`, schema);
}

// ---------- 血缘 API ----------

/**
 * 获取血缘图
 */
export async function getLineageGraph(
  tableName: string,
  options?: {
    depth?: number;
    direction?: 'upstream' | 'downstream' | 'both';
  }
): Promise<ApiResponse<LineageGraph>> {
  return apiClient.get('/api/v1/data/lineage/graph', {
    params: { table_name: tableName, ...options },
  });
}

/**
 * 获取列血缘
 */
export async function getColumnLineage(
  tableName: string,
  columnName: string
): Promise<ApiResponse<ColumnLineage>> {
  return apiClient.get('/api/v1/data/lineage/column', {
    params: { table_name: tableName, column_name: columnName },
  });
}

/**
 * 获取影响分析
 */
export async function getImpactAnalysis(
  tableName: string,
  options?: {
    change_type?: 'schema_change' | 'data_change' | 'deletion' | 'rename';
    depth?: number;
  }
): Promise<ApiResponse<ImpactAnalysis>> {
  return apiClient.get('/api/v1/data/lineage/impact', {
    params: { table_name: tableName, ...options },
  });
}

/**
 * 解析 SQL 获取血缘
 */
export async function parseSQLLineage(
  sql: string,
  options?: { source_database?: string; use_ai?: boolean }
): Promise<ApiResponse<SQLLineageResult>> {
  return apiClient.post('/api/v1/data/lineage/parse-sql', {
    sql,
    source_database: options?.source_database,
    use_ai: options?.use_ai ?? true,
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
  return apiClient.post('/api/v1/data/lineage/ai-impact-analysis', {
    node_info: nodeInfo,
    downstream_nodes: options?.downstream_nodes || [],
    change_type: options?.change_type || 'schema_change',
  });
}

/**
 * 搜索血缘
 */
export async function searchLineage(
  query: string,
  type?: 'table' | 'column'
): Promise<ApiResponse<{
  results: Array<{
    table: string;
    column?: string;
    match_type: string;
    upstream_count: number;
    downstream_count: number;
  }>;
}>> {
  return apiClient.get('/api/v1/data/lineage/search', {
    params: { query, type },
  });
}

// ---------- 通知 API ----------

/**
 * 获取通知列表
 */
export async function getNotifications(params?: {
  unread_only?: boolean;
  limit?: number;
  type?: string;
}): Promise<ApiResponse<NotificationsResponse>> {
  return apiClient.get('/api/v1/data/notifications', { params });
}

/**
 * 标记通知为已读
 */
export async function markNotificationRead(notificationId: string): Promise<ApiResponse<{ read: boolean }>> {
  return apiClient.post(`/api/v1/data/notifications/${notificationId}/read`, {});
}

/**
 * 标记所有通知为已读
 */
export async function markAllNotificationsRead(): Promise<ApiResponse<{ count: number }>> {
  return apiClient.post('/api/v1/data/notifications/read-all', {});
}

/**
 * 删除通知
 */
export async function deleteNotification(notificationId: string): Promise<ApiResponse<{ deleted: boolean }>> {
  return apiClient.delete(`/api/v1/data/notifications/${notificationId}`);
}

/**
 * 获取通知渠道
 */
export async function getNotificationChannels(): Promise<ApiResponse<{ channels: NotificationChannel[]; total: number }>> {
  return apiClient.get('/api/v1/data/notifications/channels');
}

/**
 * 获取通知模板
 */
export async function getNotificationTemplates(): Promise<ApiResponse<{ templates: NotificationTemplate[]; total: number }>> {
  return apiClient.get('/api/v1/data/notifications/templates');
}

/**
 * 获取通知规则
 */
export async function getNotificationRules(): Promise<ApiResponse<{ rules: NotificationRule[]; total: number }>> {
  return apiClient.get('/api/v1/data/notifications/rules');
}

/**
 * 创建通知规则
 */
export async function createNotificationRule(rule: {
  name: string;
  description?: string;
  event_type: string;
  conditions?: Record<string, unknown>;
  template_id: string;
  channels: string[];
  recipients: string[];
  throttle_minutes?: number;
}): Promise<ApiResponse<{ rule_id: string }>> {
  return apiClient.post('/api/v1/data/notifications/rules', rule);
}

/**
 * 更新通知规则
 */
export async function updateNotificationRule(
  ruleId: string,
  updates: Partial<NotificationRule>
): Promise<ApiResponse<NotificationRule>> {
  return apiClient.put(`/api/v1/data/notifications/rules/${ruleId}`, updates);
}

/**
 * 删除通知规则
 */
export async function deleteNotificationRule(ruleId: string): Promise<ApiResponse<{ deleted: boolean }>> {
  return apiClient.delete(`/api/v1/data/notifications/rules/${ruleId}`);
}

/**
 * 发送通知
 */
export async function sendNotification(request: {
  recipients: string[];
  subject?: string;
  body: string;
  channels: string[];
  type?: 'info' | 'warning' | 'error' | 'success';
  priority?: 'low' | 'normal' | 'high' | 'urgent';
}): Promise<ApiResponse<{ message_id: string; status: string }>> {
  return apiClient.post('/api/v1/data/notifications/send', request);
}

// ---------- 调度 API ----------

/**
 * 获取调度任务列表
 */
export async function getScheduledTasks(params?: {
  status?: ScheduledTaskStatus;
  priority?: ScheduledTaskPriority;
  task_type?: string;
  limit?: number;
}): Promise<ApiResponse<ScheduledTasksResponse>> {
  return apiClient.get('/api/v1/data/scheduler/tasks', { params });
}

/**
 * 获取调度任务详情
 */
export async function getScheduledTask(taskId: string): Promise<ApiResponse<ScheduledTask>> {
  return apiClient.get(`/api/v1/data/scheduler/tasks/${taskId}`);
}

/**
 * 创建调度任务
 */
export async function createScheduledTask(task: {
  name: string;
  task_type?: string;
  priority?: ScheduledTaskPriority;
  description?: string;
  dependencies?: ScheduledTaskDependency[];
  resource_requirement?: Partial<ScheduledResourceRequirement>;
  estimated_duration_ms?: number;
  deadline?: string;
  created_by?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/data/scheduler/tasks', task);
}

/**
 * 更新调度任务
 */
export async function updateScheduledTask(
  taskId: string,
  updates: Partial<ScheduledTask>
): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.put(`/api/v1/data/scheduler/tasks/${taskId}`, updates);
}

/**
 * 删除调度任务
 */
export async function deleteScheduledTask(taskId: string): Promise<ApiResponse<{ deleted: boolean }>> {
  return apiClient.delete(`/api/v1/data/scheduler/tasks/${taskId}`);
}

/**
 * 完成调度任务
 */
export async function completeScheduledTask(
  taskId: string,
  result: { success: boolean; error_message?: string; execution_time_ms?: number }
): Promise<ApiResponse<ScheduledTask>> {
  return apiClient.post(`/api/v1/data/scheduler/tasks/${taskId}/complete`, result);
}

/**
 * 获取调度统计
 */
export async function getSchedulerStatistics(): Promise<ApiResponse<SchedulerStatistics>> {
  return apiClient.get('/api/v1/data/scheduler/statistics');
}

/**
 * 优化调度顺序
 */
export async function optimizeSchedule(): Promise<ApiResponse<{
  optimized_order: string[];
  total_tasks: number;
  estimated_completion_time: number;
}>> {
  return apiClient.post('/api/v1/data/scheduler/optimize', {});
}

// ---------- 内容管理 API ----------

/**
 * 获取内容列表
 */
export async function getContents(params?: {
  content_type?: string;
  status?: string;
  category?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<ContentListResponse>> {
  return apiClient.get('/api/v1/data/contents', { params });
}

/**
 * 获取内容详情
 */
export async function getContent(contentId: string): Promise<ApiResponse<ContentItem>> {
  return apiClient.get(`/api/v1/data/contents/${contentId}`);
}

/**
 * 创建内容
 */
export async function createContent(
  data: CreateContentRequest
): Promise<ApiResponse<{ content_id: string; created_at: string }>> {
  return apiClient.post('/api/v1/data/contents', data);
}

/**
 * 更新内容
 */
export async function updateContent(
  contentId: string,
  data: UpdateContentRequest
): Promise<ApiResponse<ContentItem>> {
  return apiClient.put(`/api/v1/data/contents/${contentId}`, data);
}

/**
 * 删除内容
 */
export async function deleteContent(contentId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/data/contents/${contentId}`);
}

/**
 * 发布内容
 */
export async function publishContent(contentId: string): Promise<ApiResponse<{ published: boolean; published_at: string }>> {
  return apiClient.post(`/api/v1/data/contents/${contentId}/publish`, {});
}

/**
 * 归档内容
 */
export async function archiveContent(contentId: string): Promise<ApiResponse<{ archived: boolean }>> {
  return apiClient.post(`/api/v1/data/contents/${contentId}/archive`, {});
}

/**
 * 搜索内容
 */
export async function searchContents(
  query: string,
  options?: {
    content_type?: string;
    category?: string;
    limit?: number;
  }
): Promise<ApiResponse<{
  results: ContentItem[];
  total: number;
}>> {
  return apiClient.get('/api/v1/data/contents/search', {
    params: { query, ...options },
  });
}

// ============= 默认导出对象 =============

const alldata = {
  // 元数据
  getMetadata,
  getTableMetadata,
  updateMetadata,
  refreshMetadata,
  searchMetadata,

  // AI 标注
  getAIAnnotations,
  createAIAnnotation,
  createTableAIAnnotations,
  updateAIAnnotation,
  deleteAIAnnotation,
  getAIAnnotationStatus,

  // 敏感数据
  getSensitivityReport,
  scanForSensitiveData,
  getSensitivityScanHistory,
  applySensitivityPolicy,

  // 数据集
  getDatasets,
  getDataset,
  createDataset,
  updateDataset,
  deleteDataset,
  getDatasetPreview,
  getDatasetVersions,

  // 列模式
  getColumnSchema,
  updateColumnSchema,
  validateColumnSchema,

  // 血缘
  getLineageGraph,
  getColumnLineage,
  getImpactAnalysis,
  parseSQLLineage,
  getAIImpactAnalysis,
  searchLineage,

  // 通知
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
  getNotificationChannels,
  getNotificationTemplates,
  getNotificationRules,
  createNotificationRule,
  updateNotificationRule,
  deleteNotificationRule,
  sendNotification,

  // 调度
  getScheduledTasks,
  getScheduledTask,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  completeScheduledTask,
  getSchedulerStatistics,
  optimizeSchedule,

  // 内容管理
  getContents,
  getContent,
  createContent,
  updateContent,
  deleteContent,
  publishContent,
  archiveContent,
  searchContents,
};

export default alldata;

// Re-export everything from data.ts for backward compatibility
export * from './data';
