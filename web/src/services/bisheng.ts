import { apiClient, ApiResponse } from './api';

// ============= 应用状态类型 =============

export type AppStatus = 'draft' | 'published' | 'archived';

// ============= API 密钥类型 =============

export interface ApiKey {
  key_id: string;
  key_display: string;
  created_at: string;
  last_used?: string;
  access_count: number;
  is_active: boolean;
}

// ============= 发布应用类型 (别名) =============

export interface PublishedApp {
  app_id: string;
  name: string;
  description?: string;
  type: 'chat' | 'workflow' | 'agent';
  status: AppStatus;
  version: string;
  endpoint?: string;
  api_key_count: number;
  access_count: number;
  last_accessed?: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
  published_at?: string;
}

// ============= 文档索引类型 =============

export interface IndexedDocument {
  doc_id: string;
  file_name: string;
  title: string;
  collection_name: string;
  chunk_count: number;
  content: string;
  metadata: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentsResponse {
  documents: IndexedDocument[];
  collections: string[];
  total_collections: number;
  total: number;
}

export interface IndexDocumentRequest {
  content?: string;
  file_name?: string;
  title?: string;
  collection?: string;
  metadata?: Record<string, unknown>;
}

// ============= 执行日志类型 =============

export interface ExecutionLog {
  id: number;
  execution_id: string;
  node_id?: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// ============= 工具类型 =============

export interface Tool {
  name: string;
  description: string;
  parameters: Array<{
    name: string;
    type: string;
    description: string;
    required: boolean;
    default?: unknown;
  }>;
  category?: string;
  enabled?: boolean;
}

export interface ToolSchema {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters: {
      type: 'object';
      properties: Record<string, { type: string; description?: string; default?: unknown }>;
      required: string[];
    };
  };
}

export interface ToolExecuteRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
}

export interface ToolExecuteResponse {
  success: boolean;
  result: unknown;
  execution_time_ms?: number;
  error?: string;
}

// ============= 调度类型 =============

export interface WorkflowSchedule {
  id: number;
  schedule_id: string;
  workflow_id: string;
  schedule_type: 'cron' | 'interval' | 'event';
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  enabled: boolean;
  paused: boolean;
  next_run_at?: string;
  last_run_at?: string;
  max_retries: number;
  retry_count: number;
  retry_delay_seconds: number;
  retry_backoff_base: number;
  last_retry_at?: string;
  timeout_seconds: number;
  description?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateScheduleRequest {
  type: 'cron' | 'interval' | 'event';
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  enabled?: boolean;
  paused?: boolean;
  max_retries?: number;
  retry_delay_seconds?: number;
  retry_backoff_base?: number;
  timeout_seconds?: number;
  description?: string;
}

export interface UpdateScheduleRequest {
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  enabled?: boolean;
  paused?: boolean;
  max_retries?: number;
  retry_delay_seconds?: number;
  retry_backoff_base?: number;
  timeout_seconds?: number;
  description?: string;
}

export interface ScheduleRetryConfig {
  max_retries: number;
  retry_delay_seconds: number;
  retry_backoff_base: number;
  timeout_seconds: number;
}

export interface ScheduleStatistics {
  schedule_id: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time_ms: number;
  last_execution_status: string | null;
  last_execution_at: string | null;
  success_rate: number;
  recent_executions: Array<{
    execution_id: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    duration_ms?: number;
    error?: string;
  }>;
}

// ============= 会话类型 =============

export interface Conversation {
  conversation_id: string;
  title: string;
  model: string;
  message_count?: number;
  created_at: string;
  updated_at: string;
  last_message?: string;
  tags?: string[];
}

export interface ConversationMessage {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: {
    model?: string;
    tokens?: number;
    latency_ms?: number;
  };
}

export interface ConversationUsage {
  conversation_id: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  message_count: number;
  estimated_cost?: number;
}

export interface SaveMessageRequest {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

// ============= SFT 微调类型 =============

export interface SFTTask {
  task_id: string;
  name: string;
  description?: string;
  base_model: string;
  method: 'sft' | 'lora' | 'qlora';
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  config: {
    learning_rate: number;
    batch_size: number;
    num_epochs: number;
    max_steps?: number;
    warmup_ratio?: number;
    lora_r?: number;
    lora_alpha?: number;
    lora_dropout?: number;
  };
  resources: {
    gpu_type: string;
    gpu_count: number;
    cpu: string;
    memory: string;
  };
  output_model_path?: string;
  metrics?: Array<{
    step: number;
    loss: number;
    learning_rate: number;
    epoch: number;
  }>;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface CreateSFTTaskRequest {
  name: string;
  description?: string;
  base_model: string;
  method: 'sft' | 'lora' | 'qlora';
  dataset_id: string;
  config: {
    learning_rate: number;
    batch_size: number;
    num_epochs: number;
    max_steps?: number;
    warmup_ratio?: number;
    lora_r?: number;
    lora_alpha?: number;
    lora_dropout?: number;
  };
  resources: {
    gpu_type: string;
    gpu_count: number;
    cpu: string;
    memory: string;
  };
}

export interface SFTDataset {
  dataset_id: string;
  name: string;
  description?: string;
  format: 'jsonl' | 'parquet' | 'json';
  sample_count: number;
  file_size: number;
  schema?: {
    system?: string;
    instruction: string;
    input?: string;
    output: string;
  };
  created_by: string;
  created_at: string;
}

// ============= Agent 类型 =============

export interface AgentStep {
  type: 'thought' | 'action' | 'observation' | 'final' | 'plan' | 'error';
  content: string;
  tool_output?: unknown;
  timestamp: string;
  iteration?: number;
}

export interface AgentTemplate {
  id: number;
  template_id: string;
  name: string;
  description?: string;
  agent_type: 'react' | 'function_calling' | 'plan_execute';
  model: string;
  max_iterations?: number;
  system_prompt?: string;
  selected_tools: string[];
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentTemplateRequest {
  name: string;
  description?: string;
  agent_type?: 'react' | 'function_calling' | 'plan_execute';
  model?: string;
  max_iterations?: number;
  system_prompt?: string;
  selected_tools?: string[];
}

export interface UpdateAgentTemplateRequest {
  name?: string;
  description?: string;
  agent_type?: 'react' | 'function_calling' | 'plan_execute';
  model?: string;
  max_iterations?: number;
  system_prompt?: string;
  selected_tools?: string[];
}

export interface AgentExecuteRequest {
  query: string;
  agent_type?: 'react' | 'function_calling' | 'plan_execute';
  template_id?: string;
  model?: string;
  max_iterations?: number;
  tools?: string[];
  context?: Record<string, unknown>;
}

export interface AgentExecuteResponse {
  success: boolean;
  answer?: string;
  error?: string;
  iterations?: number;
  steps?: AgentStep[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// ============= Prompt 模板类型 =============

export interface PromptTemplate {
  template_id: string;
  name: string;
  description?: string;
  content: string;
  variables: string[];
  category?: string;
  tags?: string[];
  created_at: string;
  updated_at?: string;
  created_by?: string;
  version?: number;
}

export interface CreatePromptTemplateRequest {
  name: string;
  description?: string;
  content: string;
  category?: string;
  tags?: string[];
}

export interface UpdatePromptTemplateRequest {
  name?: string;
  description?: string;
  content?: string;
  category?: string;
  tags?: string[];
}

// ============= 工作流类型 =============

export interface WorkflowExecution {
  id: string;
  execution_id?: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped' | 'waiting_human';
  inputs?: Record<string, unknown>;
  outputs?: unknown;
  node_results?: Record<string, unknown>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  created_at: string;
}

export interface Workflow {
  workflow_id: string;
  name: string;
  description?: string;
  type: 'rag' | 'text2sql' | 'custom' | 'agent';
  status: 'running' | 'stopped' | 'error' | 'pending' | 'draft';
  definition?: {
    nodes: unknown[];
    edges: unknown[];
  };
  version?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  type: 'rag' | 'text2sql' | 'custom' | 'agent';
  config?: Record<string, unknown>;
  definition?: {
    nodes: unknown[];
    edges: unknown[];
  };
}

export interface UpdateWorkflowRequest {
  name?: string;
  description?: string;
  type?: 'rag' | 'text2sql' | 'custom' | 'agent';
  config?: Record<string, unknown>;
  definition?: {
    nodes: unknown[];
    edges: unknown[];
  } | string;
}

// ============= 人机循环类型 =============

export interface HumanTask {
  task_id: string;
  human_task_id?: string;
  execution_id: string;
  node_id: string;
  task_type: 'approval' | 'review' | 'input' | 'confirmation';
  task_name?: string;
  approval_type?: 'single' | 'multi' | 'unanimous';
  title: string;
  description?: string;
  assignee?: string;
  assignees?: string[];
  status: 'pending' | 'approved' | 'rejected' | 'timeout' | 'cancelled';
  input_data?: Record<string, unknown>;
  timeout_at?: string;
  form_schema?: Array<{
    name: string;
    type: 'text' | 'textarea' | 'number' | 'select' | 'multiselect' | 'boolean' | 'date';
    label: string;
    required?: boolean;
    options?: Array<{ label: string; value: string }>;
    default?: unknown;
  }>;
  data?: {
    input_data?: Record<string, unknown>;
    form_schema?: HumanTask['form_schema'];
    context?: Record<string, unknown>;
    timeout_minutes?: number;
  };
  created_at: string;
  completed_at?: string;
  result?: {
    approved: boolean;
    comment?: string;
    input_data?: Record<string, unknown>;
  };
}

// ============= Text2SQL 类型 =============

export interface Text2SqlRequest {
  natural_language: string;
  database?: string;
  selected_tables?: string[];
}

export interface Text2SqlResponse {
  sql: string;
  confidence: number;
  tables_used: string[];
  interpretation?: string;
  chartRecommendation?: {
    chartType?: string;
    chartName?: string;
    confidence?: number;
    reason?: string;
    type?: 'bar' | 'line' | 'pie' | 'table' | 'area' | 'scatter';
    title?: string;
    x_axis?: string;
    y_axis?: string;
    group_by?: string;
    aggregation?: 'sum' | 'avg' | 'count' | 'max' | 'min';
  };
  suggestions?: string[];
}

// ============= 评估类型 =============

export interface Evaluation {
  evaluation_id: string;
  name: string;
  description?: string;
  model_configs: Array<{
    model_name: string;
    endpoint: string;
    api_key?: string;
  }>;
  dataset_id: string;
  metrics: string[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateEvaluationRequest {
  name: string;
  description?: string;
  model_configs: Array<{
    model_name: string;
    endpoint: string;
    api_key?: string;
  }>;
  dataset_id: string;
  metrics: string[];
}

export interface EvaluationResult {
  result_id: string;
  evaluation_id: string;
  model_name: string;
  status: 'completed' | 'failed';
  metrics: Record<string, number>;
  samples_evaluated: number;
  avg_response_time_ms?: number;
  error?: string;
  evaluated_at: string;
}

// 别名类型 - 用于兼容
export interface EvaluationTask {
  task_id: string;
  name: string;
  description?: string;
  model_configs: Array<{
    model_name: string;
    endpoint: string;
    api_key?: string;
  }>;
  dataset_id: string;
  metrics: Array<'accuracy' | 'f1' | 'precision' | 'recall' | 'bleu' | 'rouge' | 'cosine_similarity' | 'response_time'>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateEvaluationTaskRequest {
  name: string;
  description?: string;
  model_configs: Array<{
    model_name: string;
    endpoint: string;
    api_key?: string;
  }>;
  dataset_id: string;
  metrics: Array<'accuracy' | 'f1' | 'precision' | 'recall' | 'bleu' | 'rouge' | 'cosine_similarity' | 'response_time'>;
}

export interface ComparisonReport {
  report_id: string;
  task_id: string;
  task_name: string;
  models: Array<{
    model_name: string;
    metrics: Record<string, number>;
  }>;
  winner: string;
  comparison: Record<string, {
    best_model: string;
    difference: number;
  }>;
  generated_at: string;
}

export interface RetrievalTestResult {
  query: string;
  results: Array<{
    chunk_id: string;
    content: string;
    score: number;
    source: {
      doc_id: string;
      file_name: string;
      title: string;
    };
  }>;
  total_results: number;
  search_type: string;
}

// ============= 知识库类型 =============

export interface KnowledgeBase {
  kb_id: string;
  name: string;
  description?: string;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  vector_count: number;
  status: 'ready' | 'indexing' | 'error';
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  tags?: string[];
}

export interface UpdateKnowledgeBaseRequest {
  name?: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  tags?: string[];
}

export interface KnowledgeDocument {
  doc_id: string;
  kb_id: string;
  file_name: string;
  title: string;
  chunk_count: number;
  status: 'pending' | 'indexed' | 'failed';
  error?: string;
  created_at: string;
}

// ============= 应用类型 =============

export interface App {
  app_id: string;
  name: string;
  description?: string;
  type: 'chat' | 'workflow' | 'agent';
  status: 'draft' | 'published' | 'archived';
  version: string;
  endpoint?: string;
  api_key_count: number;
  access_count: number;
  last_accessed?: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
  published_at?: string;
}

export interface CreateAppRequest {
  name: string;
  description?: string;
  type: 'chat' | 'workflow' | 'agent';
  config?: Record<string, unknown>;
}

export interface UpdateAppRequest {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
  tags?: string[];
}

// ============= API 方法: 文档管理 =============

/**
 * 索引文档
 */
export async function indexDocument(formData: FormData): Promise<ApiResponse<{
  doc_id: string;
  file_name: string;
  chunk_count: number;
  collection: string;
}>> {
  return apiClient.post('/api/v1/agent/documents/index', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 获取文档列表
 */
export async function getDocuments(params?: {
  collection?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResponse<DocumentsResponse>> {
  return apiClient.get('/api/v1/agent/documents', { params });
}

/**
 * 获取文档详情
 */
export async function getDocument(docId: string): Promise<ApiResponse<IndexedDocument>> {
  return apiClient.get(`/api/v1/agent/documents/${docId}`);
}

/**
 * 删除文档
 */
export async function deleteDocument(docId: string): Promise<ApiResponse<{ doc_id: string; vectors_deleted: boolean }>> {
  return apiClient.delete(`/api/v1/agent/documents/${docId}`);
}

/**
 * 批量删除文档
 */
export async function batchDeleteDocuments(docIds: string[]): Promise<ApiResponse<{
  deleted_count: number;
  failed_count: number;
  failed_ids: string[];
}>> {
  return apiClient.delete('/api/v1/agent/documents/batch', { data: { doc_ids: docIds } });
}

/**
 * 搜索文档
 */
export async function searchDocuments(query: string, params?: {
  collection?: string;
  top_k?: number;
  score_threshold?: number;
}): Promise<ApiResponse<{
  results: Array<{
    doc_id: string;
    content: string;
    score: number;
    metadata: Record<string, unknown>;
  }>;
}>> {
  return apiClient.post('/api/v1/agent/documents/search', { query, ...params });
}

// ============= API 方法: 应用管理 =============

/**
 * 获取应用列表
 */
export async function getApps(params?: {
  type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ apps: App[]; total: number }>> {
  return apiClient.get('/api/v1/agent/apps', { params });
}

/**
 * 获取应用详情
 */
export async function getApp(appId: string): Promise<ApiResponse<App & { config?: Record<string, unknown> }>> {
  return apiClient.get(`/api/v1/agent/apps/${appId}`);
}

/**
 * 创建应用
 */
export async function createApp(data: CreateAppRequest): Promise<ApiResponse<{ app_id: string }>> {
  return apiClient.post('/api/v1/agent/apps', data);
}

/**
 * 更新应用
 */
export async function updateApp(appId: string, data: UpdateAppRequest): Promise<ApiResponse<App>> {
  return apiClient.put(`/api/v1/agent/apps/${appId}`, data);
}

/**
 * 删除应用
 */
export async function deleteApp(appId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/apps/${appId}`);
}

/**
 * 发布应用
 */
export async function publishApp(appId: string, data?: {
  version?: string;
  changelog?: string;
}): Promise<ApiResponse<{ app_id: string; version: string; endpoint: string }>> {
  return apiClient.post(`/api/v1/agent/apps/${appId}/publish`, data || {});
}

/**
 * 下线应用
 */
export async function unpublishApp(appId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/apps/${appId}/unpublish`);
}

// ============= API 方法: 工具管理 =============

/**
 * 获取工具列表
 */
export async function getTools(params?: {
  category?: string;
  enabled?: boolean;
}): Promise<ApiResponse<{ tools: Tool[]; total: number }>> {
  return apiClient.get('/api/v1/agent/tools', { params });
}

/**
 * 获取工具 schemas
 */
export async function getToolSchemas(): Promise<ApiResponse<{ schemas: ToolSchema[]; total: number }>> {
  return apiClient.get('/api/v1/agent/tools/schemas');
}

/**
 * 执行工具
 */
export async function executeTool(
  toolName: string,
  parameters: Record<string, unknown>
): Promise<ApiResponse<ToolExecuteResponse>> {
  return apiClient.post(`/api/v1/agent/tools/${toolName}/execute`, parameters);
}

/**
 * 获取工具详情
 */
export async function getTool(toolName: string): Promise<ApiResponse<Tool>> {
  return apiClient.get(`/api/v1/agent/tools/${toolName}`);
}

// ============= API 方法: 调度管理 =============

/**
 * 获取调度列表
 */
export async function getSchedules(params?: {
  workflow_id?: string;
  enabled?: boolean;
}): Promise<ApiResponse<{ schedules: WorkflowSchedule[] }>> {
  return apiClient.get('/api/v1/agent/schedules', { params });
}

/**
 * 获取工作流的调度配置
 */
export async function getWorkflowSchedules(workflowId: string): Promise<ApiResponse<{ schedules: WorkflowSchedule[] }>> {
  return apiClient.get(`/api/v1/agent/workflows/${workflowId}/schedules`);
}

/**
 * 创建调度
 */
export async function createSchedule(
  workflowId: string,
  data: CreateScheduleRequest
): Promise<ApiResponse<{ schedule_id: string }>> {
  return apiClient.post(`/api/v1/agent/workflows/${workflowId}/schedules`, data);
}

/**
 * 更新调度
 */
export async function updateSchedule(
  scheduleId: string,
  data: UpdateScheduleRequest
): Promise<ApiResponse<WorkflowSchedule>> {
  return apiClient.put(`/api/v1/agent/schedules/${scheduleId}`, data);
}

/**
 * 删除调度
 */
export async function deleteSchedule(scheduleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/schedules/${scheduleId}`);
}

/**
 * 暂停调度
 */
export async function pauseSchedule(scheduleId: string): Promise<ApiResponse<{ schedule_id: string; paused: boolean }>> {
  return apiClient.post(`/api/v1/agent/schedules/${scheduleId}/pause`);
}

/**
 * 恢复调度
 */
export async function resumeSchedule(scheduleId: string): Promise<ApiResponse<{ schedule_id: string; paused: boolean }>> {
  return apiClient.post(`/api/v1/agent/schedules/${scheduleId}/resume`);
}

/**
 * 手动触发调度
 */
export async function triggerSchedule(scheduleId: string): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/agent/schedules/${scheduleId}/trigger`);
}

/**
 * 获取调度统计
 */
export async function getScheduleStatistics(scheduleId: string): Promise<ApiResponse<ScheduleStatistics>> {
  return apiClient.get(`/api/v1/agent/schedules/${scheduleId}/statistics`);
}

/**
 * 更新调度重试配置
 */
export async function updateScheduleRetryConfig(
  scheduleId: string,
  config: Partial<ScheduleRetryConfig>
): Promise<ApiResponse<ScheduleRetryConfig & { schedule_id: string }>> {
  return apiClient.put(`/api/v1/agent/schedules/${scheduleId}/retry-config`, config);
}

// ============= API 方法: 会话管理 =============

/**
 * 获取会话列表
 */
export async function getConversations(params?: {
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ conversations: Conversation[]; total: number }>> {
  return apiClient.get('/api/v1/agent/conversations', { params });
}

/**
 * 获取会话详情
 */
export async function getConversation(
  conversationId: string
): Promise<ApiResponse<Conversation & { messages: ConversationMessage[] }>> {
  return apiClient.get(`/api/v1/agent/conversations/${conversationId}`);
}

/**
 * 创建会话
 */
export async function createConversation(title?: string): Promise<ApiResponse<{ conversation_id: string }>> {
  return apiClient.post('/api/v1/agent/conversations', { title });
}

/**
 * 删除会话
 */
export async function deleteConversation(conversationId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/conversations/${conversationId}`);
}

/**
 * 保存消息到会话
 */
export async function saveMessage(
  conversationId: string,
  data: SaveMessageRequest
): Promise<ApiResponse<{ message_id: string; conversation_id: string }>> {
  return apiClient.post(`/api/v1/agent/conversations/${conversationId}/messages`, data);
}

/**
 * 获取会话使用统计
 */
export async function getConversationUsage(
  conversationId: string
): Promise<ApiResponse<ConversationUsage>> {
  return apiClient.get(`/api/v1/agent/conversations/${conversationId}/usage`);
}

// ============= API 方法: SFT 微调 =============

/**
 * 获取 SFT 任务列表
 */
export async function getSFTTasks(params?: {
  status?: string;
  base_model?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: SFTTask[]; total: number }>> {
  return apiClient.get('/api/v1/agent/sft/tasks', { params });
}

/**
 * 获取 SFT 任务详情
 */
export async function getSFTTask(taskId: string): Promise<ApiResponse<SFTTask>> {
  return apiClient.get(`/api/v1/agent/sft/tasks/${taskId}`);
}

/**
 * 创建 SFT 任务
 */
export async function createSFTTask(data: CreateSFTTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/agent/sft/tasks', data);
}

/**
 * 启动 SFT 任务
 */
export async function startSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/sft/tasks/${taskId}/start`);
}

/**
 * 停止 SFT 任务
 */
export async function stopSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/sft/tasks/${taskId}/stop`);
}

/**
 * 删除 SFT 任务
 */
export async function deleteSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/sft/tasks/${taskId}`);
}

/**
 * 获取 SFT 任务指标
 */
export async function getSFTMetrics(taskId: string): Promise<ApiResponse<{ metrics: SFTTask['metrics'] }>> {
  return apiClient.get(`/api/v1/agent/sft/tasks/${taskId}/metrics`);
}

/**
 * 获取 SFT 数据集列表
 */
export async function getSFTDatasets(params?: {
  format?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ datasets: SFTDataset[]; total: number }>> {
  return apiClient.get('/api/v1/agent/sft/datasets', { params });
}

/**
 * 上传 SFT 数据集
 */
export async function uploadSFTDataset(formData: FormData): Promise<ApiResponse<{ dataset_id: string }>> {
  return apiClient.post('/api/v1/agent/sft/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 导出 SFT 模型
 */
export async function exportSFTModel(
  taskId: string,
  format: 'pytorch' | 'safetensors' | 'gguf'
): Promise<ApiResponse<{ export_id: string }>> {
  return apiClient.post(`/api/v1/agent/sft/tasks/${taskId}/export`, { format });
}

// ============= API 方法: Agent 管理 =============

/**
 * 获取 Agent 列表
 */
export async function getAgents(params?: {
  agent_type?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ agents: AgentTemplate[]; total: number }>> {
  return apiClient.get('/api/v1/agent/agents', { params });
}

/**
 * 执行 Agent
 */
export async function executeAgent(data: AgentExecuteRequest): Promise<ApiResponse<AgentExecuteResponse>> {
  return apiClient.post('/api/v1/agent/run', data);
}

/**
 * 执行 Agent (流式)
 */
export async function executeAgentStream(
  data: AgentExecuteRequest,
  callbacks: {
    onStep?: (step: AgentStep) => void;
    onStart?: (agentType: string) => void;
    onIteration?: (iteration: number, maxIterations: number) => void;
    onToolStart?: (tool: string) => void;
    onToolEnd?: (tool: string) => void;
    onStatus?: (message: string) => void;
    onComplete?: (result: { success: boolean; answer?: string; iterations?: number }) => void;
    onError?: (error: string) => void;
  }
): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
    callbacks.onError?.('Request timeout after 120 seconds');
    callbacks.onComplete?.({ success: false, answer: undefined });
  }, 120000);

  try {
    const response = await fetch('/api/v1/agent/run-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized: Please login again');
      } else if (response.status === 429) {
        throw new Error('Rate limit exceeded. Please try again later.');
      } else if (response.status >= 500) {
        throw new Error(`Server error: ${response.status}`);
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const event = JSON.parse(trimmed.slice(6));

              switch (event.type) {
                case 'start':
                  callbacks.onStart?.(event.agent_type || 'unknown');
                  break;
                case 'step':
                  if (event.data) {
                    callbacks.onStep?.(event.data);
                  }
                  break;
                case 'iteration':
                  if (event.iteration !== undefined && event.max_iterations !== undefined) {
                    callbacks.onIteration?.(event.iteration, event.max_iterations);
                  }
                  break;
                case 'tool_start':
                  if (event.tool) {
                    callbacks.onToolStart?.(event.tool);
                  }
                  break;
                case 'tool_end':
                  if (event.tool) {
                    callbacks.onToolEnd?.(event.tool);
                  }
                  break;
                case 'status':
                  if (event.message) {
                    callbacks.onStatus?.(event.message);
                  }
                  break;
                case 'end':
                  callbacks.onComplete?.({
                    success: event.success || false,
                    answer: event.answer,
                    iterations: event.iterations,
                  });
                  break;
                case 'error':
                  callbacks.onError?.(event.message || 'Unknown error');
                  callbacks.onComplete?.({ success: false, answer: undefined });
                  break;
              }
            } catch {
              // Silently ignore parse errors for malformed SSE chunks
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof Error && error.name === 'AbortError') {
      callbacks.onError?.('Request was cancelled');
    } else {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      callbacks.onError?.(errorMsg);
    }
    callbacks.onComplete?.({ success: false, answer: undefined });
  }
}

/**
 * 获取 Agent 模板列表
 */
export async function getAgentTemplates(params?: {
  agent_type?: string;
  limit?: number;
}): Promise<ApiResponse<{ templates: AgentTemplate[]; total: number }>> {
  const queryParams = new URLSearchParams();
  if (params?.agent_type) queryParams.append('agent_type', params.agent_type);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  const queryString = queryParams.toString();
  return apiClient.get(`/api/v1/agent/templates${queryString ? `?${queryString}` : ''}`);
}

/**
 * 获取 Agent 模板详情
 */
export async function getAgentTemplate(templateId: string): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.get(`/api/v1/agent/templates/${templateId}`);
}

/**
 * 创建 Agent 模板
 */
export async function createAgentTemplate(data: CreateAgentTemplateRequest): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.post('/api/v1/agent/templates', data);
}

/**
 * 更新 Agent 模板
 */
export async function updateAgentTemplate(
  templateId: string,
  data: UpdateAgentTemplateRequest
): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.put(`/api/v1/agent/templates/${templateId}`, data);
}

/**
 * 删除 Agent 模板
 */
export async function deleteAgentTemplate(templateId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/templates/${templateId}`);
}

// ============= API 方法: 评估管理 =============

/**
 * 获取评估任务列表
 */
export async function getEvaluations(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ evaluations: Evaluation[]; total: number }>> {
  return apiClient.get('/api/v1/agent/evaluations', { params });
}

/**
 * 获取评估任务详情
 */
export async function getEvaluation(evaluationId: string): Promise<ApiResponse<Evaluation>> {
  return apiClient.get(`/api/v1/agent/evaluations/${evaluationId}`);
}

/**
 * 创建评估任务
 */
export async function createEvaluation(data: CreateEvaluationRequest): Promise<ApiResponse<{ evaluation_id: string }>> {
  return apiClient.post('/api/v1/agent/evaluations', data);
}

/**
 * 启动评估任务
 */
export async function startEvaluation(evaluationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/evaluations/${evaluationId}/start`);
}

/**
 * 停止评估任务
 */
export async function stopEvaluation(evaluationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/evaluations/${evaluationId}/stop`);
}

/**
 * 删除评估任务
 */
export async function deleteEvaluation(evaluationId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/evaluations/${evaluationId}`);
}

/**
 * 获取评估结果
 */
export async function getEvaluationResults(evaluationId: string): Promise<ApiResponse<{ results: EvaluationResult[] }>> {
  return apiClient.get(`/api/v1/agent/evaluations/${evaluationId}/results`);
}

// ============= API 方法: 知识库管理 =============

/**
 * 获取知识库列表
 */
export async function getKnowledgeBases(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ knowledge_bases: KnowledgeBase[]; total: number }>> {
  return apiClient.get('/api/v1/agent/knowledge-bases', { params });
}

/**
 * 获取知识库详情
 */
export async function getKnowledgeBase(kbId: string): Promise<ApiResponse<KnowledgeBase & { documents?: KnowledgeDocument[] }>> {
  return apiClient.get(`/api/v1/agent/knowledge-bases/${kbId}`);
}

/**
 * 创建知识库
 */
export async function createKnowledgeBase(data: CreateKnowledgeBaseRequest): Promise<ApiResponse<{ kb_id: string }>> {
  return apiClient.post('/api/v1/agent/knowledge-bases', data);
}

/**
 * 更新知识库
 */
export async function updateKnowledgeBase(
  kbId: string,
  data: UpdateKnowledgeBaseRequest
): Promise<ApiResponse<KnowledgeBase>> {
  return apiClient.put(`/api/v1/agent/knowledge-bases/${kbId}`, data);
}

/**
 * 删除知识库
 */
export async function deleteKnowledgeBase(kbId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/knowledge-bases/${kbId}`);
}

/**
 * 上传文档到知识库
 */
export async function uploadDocument(
  kbId: string,
  formData: FormData
): Promise<ApiResponse<{ doc_id: string; file_name: string; chunk_count: number }>> {
  return apiClient.post(`/api/v1/agent/knowledge-bases/${kbId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 从知识库删除文档
 */
export async function deleteKnowledgeDocument(kbId: string, docId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/knowledge-bases/${kbId}/documents/${docId}`);
}

/**
 * 测试知识库检索
 */
export async function testRetrieval(kbId: string, data: {
  query: string;
  top_k?: number;
  score_threshold?: number;
  search_type?: 'vector' | 'hybrid' | 'keyword';
}): Promise<ApiResponse<{
  query: string;
  results: Array<{
    chunk_id: string;
    content: string;
    score: number;
    source: {
      doc_id: string;
      file_name: string;
      title: string;
    };
  }>;
  total_results: number;
  search_type: string;
}>> {
  return apiClient.post(`/api/v1/agent/knowledge-bases/${kbId}/test`, data);
}

/**
 * 重建知识库索引
 */
export async function rebuildKnowledgeIndex(kbId: string): Promise<ApiResponse<{ status: string }>> {
  return apiClient.post(`/api/v1/agent/knowledge-bases/${kbId}/rebuild`);
}

// ============= API 方法: Prompt 模板 =============

/**
 * 获取 Prompt 模板列表
 */
export async function getPromptTemplates(params?: {
  category?: string;
  tags?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ templates: PromptTemplate[]; total: number }>> {
  return apiClient.get('/api/v1/agent/templates/prompts', { params });
}

/**
 * 获取 Prompt 模板详情
 */
export async function getPromptTemplate(templateId: string): Promise<ApiResponse<PromptTemplate>> {
  return apiClient.get(`/api/v1/agent/templates/prompts/${templateId}`);
}

/**
 * 创建 Prompt 模板
 */
export async function createPromptTemplate(data: CreatePromptTemplateRequest): Promise<ApiResponse<{ template_id: string }>> {
  return apiClient.post('/api/v1/agent/templates/prompts', data);
}

/**
 * 更新 Prompt 模板
 */
export async function updatePromptTemplate(
  templateId: string,
  data: UpdatePromptTemplateRequest
): Promise<ApiResponse<PromptTemplate>> {
  return apiClient.put(`/api/v1/agent/templates/prompts/${templateId}`, data);
}

/**
 * 删除 Prompt 模板
 */
export async function deletePromptTemplate(templateId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/templates/prompts/${templateId}`);
}

/**
 * 测试 Prompt 模板
 */
export async function testPromptTemplate(data: {
  content: string;
  variables: Record<string, string>;
  model?: string;
}): Promise<ApiResponse<{ result: string; usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number } }>> {
  return apiClient.post('/api/v1/agent/templates/prompts/test', data);
}

// ============= API 方法: 工作流管理 =============

/**
 * 获取工作流列表
 */
export async function getWorkflows(params?: {
  type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ workflows: Workflow[]; total: number }>> {
  return apiClient.get('/api/v1/agent/workflows', { params });
}

/**
 * 获取工作流详情
 */
export async function getWorkflow(workflowId: string): Promise<ApiResponse<Workflow>> {
  return apiClient.get(`/api/v1/agent/workflows/${workflowId}`);
}

/**
 * 创建工作流
 */
export async function createWorkflow(data: CreateWorkflowRequest): Promise<ApiResponse<{ workflow_id: string }>> {
  return apiClient.post('/api/v1/agent/workflows', data);
}

/**
 * 更新工作流
 */
export async function updateWorkflow(
  workflowId: string,
  data: UpdateWorkflowRequest
): Promise<ApiResponse<Workflow>> {
  return apiClient.put(`/api/v1/agent/workflows/${workflowId}`, data);
}

/**
 * 删除工作流
 */
export async function deleteWorkflow(workflowId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/workflows/${workflowId}`);
}

/**
 * 执行工作流
 */
export async function executeWorkflow(
  workflowId: string,
  data?: { inputs?: Record<string, unknown> }
): Promise<ApiResponse<{ execution_id: string; workflow_id: string; status: string }>> {
  return apiClient.post(`/api/v1/agent/workflows/${workflowId}/execute`, data || {});
}

/**
 * 启动工作流 (别名 for executeWorkflow)
 */
export async function startWorkflow(
  workflowId: string,
  data?: { inputs?: Record<string, unknown> }
): Promise<ApiResponse<{ execution_id: string; workflow_id: string; status: string }>> {
  return apiClient.post(`/api/v1/agent/workflows/${workflowId}/start`, data || {});
}

/**
 * 停止工作流
 */
export async function stopWorkflow(workflowId: string, executionId?: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/agent/workflows/${workflowId}/stop`, { execution_id: executionId });
}

/**
 * 获取工作流执行列表
 */
export async function getWorkflowExecutions(
  workflowId: string,
  params?: { limit?: number; status?: string }
): Promise<ApiResponse<{ executions: WorkflowExecution[] }>> {
  return apiClient.get(`/api/v1/agent/workflows/${workflowId}/executions`, { params });
}

/**
 * 获取执行详情
 */
export async function getExecution(executionId: string): Promise<ApiResponse<WorkflowExecution>> {
  return apiClient.get(`/api/v1/agent/executions/${executionId}`);
}

/**
 * 获取执行日志
 */
export async function getExecutionLogs(executionId: string): Promise<ApiResponse<{ logs: ExecutionLog[] }>> {
  return apiClient.get(`/api/v1/agent/executions/${executionId}/logs`);
}

/**
 * 获取人工任务列表
 */
export async function getHumanTasks(params?: {
  execution_id?: string;
  status?: string;
  assignee?: string;
}): Promise<ApiResponse<{ tasks: HumanTask[] }>> {
  return apiClient.get('/api/v1/agent/human-tasks', { params });
}

/**
 * 提交人工任务
 */
export async function submitHumanTask(
  taskId: string,
  data: { approved: boolean; action?: 'approve' | 'reject'; comment?: string; input_data?: Record<string, unknown> }
): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return apiClient.post(`/api/v1/agent/human-tasks/${taskId}/submit`, data);
}

// ============= API 方法: Text2SQL =============

/**
 * Text-to-SQL 转换
 */
export async function text2Sql(data: Text2SqlRequest): Promise<ApiResponse<Text2SqlResponse>> {
  return apiClient.post('/api/v1/agent/text2sql', data);
}

// ============= 默认导出 =============

const bisheng = {
  // 文档管理
  indexDocument,
  getDocuments,
  getDocument,
  deleteDocument,
  batchDeleteDocuments,
  searchDocuments,

  // 应用管理
  getApps,
  getApp,
  createApp,
  updateApp,
  deleteApp,
  publishApp,
  unpublishApp,

  // 工具管理
  getTools,
  getToolSchemas,
  executeTool,
  getTool,

  // 调度管理
  getSchedules,
  getWorkflowSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  pauseSchedule,
  resumeSchedule,
  triggerSchedule,
  getScheduleStatistics,
  updateScheduleRetryConfig,

  // 会话管理
  getConversations,
  getConversation,
  createConversation,
  deleteConversation,
  saveMessage,
  getConversationUsage,

  // SFT 微调
  getSFTTasks,
  getSFTTask,
  createSFTTask,
  startSFTTask,
  stopSFTTask,
  deleteSFTTask,
  getSFTMetrics,
  getSFTDatasets,
  uploadSFTDataset,
  exportSFTModel,

  // Agent 管理
  getAgents,
  executeAgent,
  executeAgentStream,
  getAgentTemplates,
  getAgentTemplate,
  createAgentTemplate,
  updateAgentTemplate,
  deleteAgentTemplate,

  // 评估管理
  getEvaluations,
  getEvaluation,
  createEvaluation,
  startEvaluation,
  stopEvaluation,
  deleteEvaluation,
  getEvaluationResults,

  // 知识库管理
  getKnowledgeBases,
  getKnowledgeBase,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  uploadDocument,
  deleteKnowledgeDocument,
  testRetrieval,
  rebuildKnowledgeIndex,

  // Prompt 模板
  getPromptTemplates,
  getPromptTemplate,
  createPromptTemplate,
  updatePromptTemplate,
  deletePromptTemplate,
  testPromptTemplate,

  // 工作流管理
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  executeWorkflow,
  startWorkflow,
  stopWorkflow,
  getWorkflowExecutions,
  getExecution,
  getExecutionLogs,
  getHumanTasks,
  submitHumanTask,

  // Text2SQL
  text2Sql,
};

export default bisheng;

// Re-export everything from agent-service.ts for backward compatibility
export * from './agent-service';
