/**
 * Model Layer (MLOps) Service - Cube
 *
 * Comprehensive TypeScript service for the Model layer of ONE-DATA-STUDIO platform.
 * Provides APIs for: AI Hub, Experiments, Training Jobs, Model Serving, Pipelines,
 * Notebooks, LLM Fine-tuning, Monitoring, SQL Lab, and Resource Management.
 */

import apiClient, { ApiResponse } from './api';

// ============================================================================
// Common Types
// ============================================================================

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface ResourceConfig {
  cpu: number | string;
  memory: string;
  gpu?: number | string;
  gpu_type?: string;
}

// ============================================================================
// Chat Completions Types
// ============================================================================

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatCompletionUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: ChatMessage;
    finish_reason: string;
  }>;
  usage: ChatCompletionUsage;
}

// ============================================================================
// AI Hub Types
// ============================================================================

export interface HubModel {
  model_id: string;
  display_name: string;
  description: string;
  task_type: string;
  framework: string;
  parameters: string;
  accuracy?: number;
  downloads: number;
  license: string;
  author?: string;
  architecture?: string;
  size_bytes?: number;
  paper_url?: string;
  repo_url?: string;
}

export interface HubCategory {
  value: string;
  label: string;
  count: number;
}

export interface ModelDeploymentConfig {
  model_id: string;
  resources: {
    gpu_type?: string;
    gpu_count?: number;
    cpu?: string;
    memory?: string;
  };
  parameters?: {
    max_model_len?: number;
  };
  replicas?: number;
}

export interface HubModelsListParams extends PaginationParams {
  search?: string;
  task_type?: string;
  framework?: string;
  parameters?: string;
}

// ============================================================================
// Experiment Types
// ============================================================================

export interface Experiment {
  experiment_id: string;
  name: string;
  description?: string;
  project: string;
  status: 'running' | 'completed' | 'failed' | 'stopped';
  metrics?: Record<string, number>;
  parameters?: Record<string, unknown>;
  tags?: string[];
  created_by: string;
  start_time: string;
  end_time?: string;
  duration?: number;
}

export interface CreateExperimentRequest {
  name: string;
  description?: string;
  project: string;
  tags?: string[];
}

export interface ExperimentsListParams extends PaginationParams {
  status?: string;
  project?: string;
}

// ============================================================================
// Training Job Types
// ============================================================================

export interface TrainingJob {
  job_id: string;
  name: string;
  description?: string;
  project: string;
  model_name: string;
  framework: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  resources: ResourceConfig;
  hyperparameters?: Record<string, unknown>;
  current_epoch?: number;
  total_epochs?: number;
  metrics?: {
    loss?: number;
    accuracy?: number;
    [key: string]: number | undefined;
  };
  dataset_id?: string;
  distributed?: boolean;
  worker_count?: number;
  output_uri?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateTrainingJobRequest {
  name: string;
  description?: string;
  project: string;
  model_name: string;
  framework: string;
  dataset_id?: string;
  hyperparameters?: Record<string, unknown>;
  resources: {
    cpu?: number;
    memory?: string;
    gpu?: number;
    gpu_type?: string;
  };
  distributed?: boolean;
  worker_count?: number;
  output_uri?: string;
}

export interface TrainingJobsListParams extends PaginationParams {
  status?: string;
  project?: string;
}

// ============================================================================
// Model Serving Types
// ============================================================================

export interface ServingService {
  service_id: string;
  name: string;
  model_id: string;
  model_name: string;
  model_version: string;
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  endpoint: string;
  replicas: {
    total: number;
    available: number;
  };
  resources: ResourceConfig;
  metrics?: {
    qps: number;
    avg_latency_ms: number;
    error_rate: number;
  };
  autoscaling?: {
    min_replicas: number;
    max_replicas: number;
    target_qps?: number;
  };
  created_at: string;
}

export interface CreateServingServiceRequest {
  name: string;
  model_id: string;
  model_version: string;
  replicas?: number;
  resources: {
    cpu?: string;
    memory?: string;
    gpu?: string;
  };
  autoscaling?: {
    min_replicas: number;
    max_replicas: number;
    target_qps?: number;
  };
}

export interface ServingServicesListParams extends PaginationParams {
  status?: string;
}

export interface ScaleServingServiceRequest {
  replicas: number;
}

// ============================================================================
// Registered Model Types
// ============================================================================

export interface RegisteredModel {
  model_id: string;
  name: string;
  version: string;
  description?: string;
  framework: string;
  status: 'production' | 'staging' | 'archived';
  uri: string;
  experiment_id?: string;
  metrics?: Record<string, number>;
  parameters?: Record<string, unknown>;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface RegisterModelRequest {
  name: string;
  version: string;
  description?: string;
  framework: string;
  uri: string;
  experiment_id?: string;
  metrics?: Record<string, number>;
  parameters?: Record<string, unknown>;
  tags?: string[];
}

export interface RegisteredModelsListParams extends PaginationParams {
  framework?: string;
  status?: string;
}

// ============================================================================
// Notebook Types
// ============================================================================

export interface Notebook {
  notebook_id: string;
  name: string;
  description?: string;
  image: string;
  workspace?: string;
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  resources: ResourceConfig;
  url?: string;
  created_at: string;
  last_active?: string;
}

export interface NotebookImage {
  name: string;
  display_name: string;
  python_version?: string;
  description?: string;
}

export interface CreateNotebookRequest {
  name: string;
  description?: string;
  image: string;
  workspace?: string;
  resources: {
    cpu: string;
    memory: string;
    gpu?: string;
  };
}

export interface NotebooksListParams extends PaginationParams {
  status?: string;
}

// ============================================================================
// LLM Fine-tuning Types
// ============================================================================

export interface LLMFineTuningJob {
  job_id: string;
  name: string;
  base_model: string;
  method: 'lora' | 'qlora' | 'full' | 'p_tuning';
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  config?: {
    learning_rate?: number;
    batch_size?: number;
    num_epochs?: number;
    lora_config?: {
      r?: number;
      lora_alpha?: number;
      target_modules?: string[];
      lora_dropout?: number;
    };
  };
  resources?: {
    gpu_type?: string;
    gpu_count?: number;
    cpu?: string;
    memory?: string;
  };
  output_path?: string;
  error?: string;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateFineTuningJobRequest {
  name: string;
  base_model: string;
  method: 'lora' | 'qlora' | 'full' | 'p_tuning';
  dataset_id: string;
  config?: {
    learning_rate?: number;
    batch_size?: number;
    num_epochs?: number;
    lora_config?: {
      r?: number;
      lora_alpha?: number;
      target_modules?: string[];
      lora_dropout?: number;
    };
  };
  resources?: {
    gpu_type?: string;
    gpu_count?: number;
    cpu?: string;
    memory?: string;
  };
}

export interface FineTuningDataset {
  dataset_id: string;
  name: string;
  description?: string;
  format: string;
  total_samples: number;
  created_at: string;
}

export interface FineTuningJobsListParams extends PaginationParams {
  status?: string;
}

// ============================================================================
// Pipeline Types
// ============================================================================

export interface PipelineNode {
  node_id: string;
  name: string;
  type: 'data' | 'process' | 'model' | 'evaluate' | 'deploy' | 'custom';
  config: {
    parameters?: Record<string, unknown>;
    [key: string]: unknown;
  };
  position: {
    x: number;
    y: number;
  };
}

export interface PipelineEdge {
  edge_id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface Pipeline {
  pipeline_id: string;
  name: string;
  description?: string;
  status: 'active' | 'paused' | 'draft' | 'archived';
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  schedule?: {
    type: 'cron' | 'interval' | 'event';
    expression: string;
  };
  variables?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface PipelineExecution {
  execution_id: string;
  pipeline_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  node_statuses?: Array<{
    node_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
    started_at?: string;
    completed_at?: string;
  }>;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  error?: string;
}

export interface PipelineTemplate {
  template_id: string;
  name: string;
  description?: string;
  category: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  schedule?: {
    type: 'cron' | 'interval' | 'event';
    expression: string;
  };
  variables?: Record<string, unknown>;
}

export interface PipelinesListParams extends PaginationParams {
  status?: string;
}

// ============================================================================
// Resource Management Types
// ============================================================================

export interface ResourceOverview {
  total_gpu: number;
  used_gpu: number;
  total_cpu: number;
  used_cpu: number;
  running_jobs: number;
  queued_jobs: number;
}

export interface GPUResource {
  gpu_id: string;
  gpu_type: string;
  status: 'available' | 'in_use' | 'maintenance';
  utilization?: number;
  memory_used?: number;
  memory_total?: number;
  temperature?: number;
  jobs?: Array<{
    job_id: string;
    job_name: string;
  }>;
}

export interface ResourcePool {
  pool_name: string;
  pool_type: 'cpu' | 'gpu' | 'mixed';
  total_resources: {
    cpu: number;
    memory: string;
    gpu?: number;
  };
  used_resources: {
    cpu: number;
    memory: string;
    gpu?: number;
  };
  available_resources: {
    cpu: number;
    memory: string;
    gpu?: number;
  };
  running_jobs: number;
  queued_jobs: number;
}

// ============================================================================
// Monitoring Types
// ============================================================================

export type MetricPeriod = '5m' | '15m' | '30m' | '1h' | '6h' | '24h' | '7d';
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface MetricDataPoint {
  timestamp: string;
  value: number;
}

export interface MonitoringAlertRule {
  rule_id: string;
  name: string;
  description?: string;
  metric_type: string;
  condition: 'greater_than' | 'less_than' | 'equal_to';
  threshold: number;
  severity: AlertSeverity;
  target_type: 'training' | 'serving' | 'resource' | 'all';
  target_id?: string;
  enabled: boolean;
  cooldown_minutes: number;
  created_at: string;
}

export interface AlertNotification {
  notification_id: string;
  rule_id: string;
  rule_name: string;
  severity: AlertSeverity;
  message: string;
  metric_value: number;
  threshold: number;
  status: 'active' | 'acknowledged' | 'resolved';
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export interface CreateAlertRuleRequest {
  name: string;
  description?: string;
  metric_type: string;
  condition: 'greater_than' | 'less_than' | 'equal_to';
  threshold: number;
  severity: AlertSeverity;
  target_type: 'training' | 'serving' | 'resource' | 'all';
  target_id?: string;
  cooldown_minutes?: number;
}

export interface Dashboard {
  dashboard_id: string;
  name: string;
  description?: string;
  panels?: Array<{
    panel_id: string;
    title: string;
    type: string;
    config: Record<string, unknown>;
  }>;
  is_public: boolean;
  refresh_interval?: number;
  created_by: string;
  created_at: string;
}

export interface CreateDashboardRequest {
  name: string;
  description?: string;
  refresh_interval?: number;
  is_public?: boolean;
}

export interface SystemMetrics {
  cpu: {
    usage_percent: number;
    cores: number;
  };
  memory: {
    usage_percent: number;
    used_gb: number;
    total_gb: number;
  };
  disk: {
    usage_percent: number;
    used_gb: number;
    total_gb: number;
  };
  network: {
    inbound_mbps: number;
    outbound_mbps: number;
  };
  gpu?: Array<{
    name: string;
    utilization_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
    temperature_c?: number;
  }>;
}

export interface MetricsOverview {
  active_jobs: number;
  active_services: number;
  avg_gpu_utilization: number;
  active_alerts: number;
  critical_alerts: number;
}

// ============================================================================
// SQL Lab Types
// ============================================================================

export interface SqlLabConnection {
  id: string;
  name: string;
  type: 'mysql' | 'postgresql' | 'clickhouse' | 'hive' | 'presto';
  host: string;
  port: number;
  database: string;
  is_default?: boolean;
}

export interface QueryResult {
  query_id: string;
  status: 'completed' | 'failed' | 'cancelled';
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  execution_time_ms: number;
  error_message?: string;
}

export interface QueryHistoryItem {
  query_id: string;
  sql: string;
  database_id: string;
  status: 'completed' | 'failed' | 'cancelled';
  row_count?: number;
  duration_ms?: number;
  executed_at: string;
  executed_by: string;
}

export interface SavedQuery {
  saved_query_id: string;
  name: string;
  description?: string;
  database_id: string;
  sql: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ExecuteSqlQueryRequest {
  database_id: string;
  sql: string;
  limit?: number;
}

export interface SaveQueryRequest {
  name: string;
  description?: string;
  database_id: string;
  sql: string;
  tags?: string[];
}

// ============================================================================
// Cube Service Object
// ============================================================================

const cube = {
  // ==========================================================================
  // Chat Completions
  // ==========================================================================

  /**
   * Create a chat completion
   */
  createChatCompletion: (request: ChatCompletionRequest): Promise<ApiResponse<ChatCompletionResponse>> =>
    apiClient.post('/api/v1/model/chat/completions', request),

  // ==========================================================================
  // AI Hub
  // ==========================================================================

  /**
   * Get hub models list
   */
  getHubModels: (params?: HubModelsListParams): Promise<ApiResponse<{ models: HubModel[]; total: number }>> =>
    apiClient.get('/api/v1/model/hub/models', { params }),

  /**
   * Get hub categories
   */
  getHubCategories: (): Promise<ApiResponse<{ categories: HubCategory[] }>> =>
    apiClient.get('/api/v1/model/hub/categories'),

  /**
   * Get hub model detail
   */
  getHubModelDetail: (modelId: string): Promise<ApiResponse<HubModel>> =>
    apiClient.get(`/api/v1/model/hub/models/${modelId}`),

  /**
   * Download a hub model
   */
  downloadHubModel: (modelId: string): Promise<ApiResponse<{ task_id: string }>> =>
    apiClient.post(`/api/v1/model/hub/models/${modelId}/download`),

  /**
   * Deploy a hub model
   */
  deployHubModel: (modelId: string, config: ModelDeploymentConfig): Promise<ApiResponse<{ service_id: string }>> =>
    apiClient.post(`/api/v1/model/hub/models/${modelId}/deploy`, config),

  // ==========================================================================
  // Experiments
  // ==========================================================================

  /**
   * Get experiments list
   */
  getExperiments: (params?: ExperimentsListParams): Promise<ApiResponse<{ experiments: Experiment[]; total: number }>> =>
    apiClient.get('/api/v1/model/experiments', { params }),

  /**
   * Get experiment detail
   */
  getExperimentDetail: (experimentId: string): Promise<ApiResponse<Experiment>> =>
    apiClient.get(`/api/v1/model/experiments/${experimentId}`),

  /**
   * Create an experiment
   */
  createExperiment: (data: CreateExperimentRequest): Promise<ApiResponse<Experiment>> =>
    apiClient.post('/api/v1/model/experiments', data),

  /**
   * Stop an experiment
   */
  stopExperiment: (experimentId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/experiments/${experimentId}/stop`),

  /**
   * Delete an experiment
   */
  deleteExperiment: (experimentId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/experiments/${experimentId}`),

  /**
   * Get experiment metrics
   */
  getExperimentMetrics: (experimentId: string, period?: MetricPeriod): Promise<ApiResponse<{ metrics: MetricDataPoint[] }>> =>
    apiClient.get(`/api/v1/model/experiments/${experimentId}/metrics`, { params: { period } }),

  // ==========================================================================
  // Training Jobs
  // ==========================================================================

  /**
   * Get training jobs list
   */
  getTrainingJobs: (params?: TrainingJobsListParams): Promise<ApiResponse<{ jobs: TrainingJob[]; total: number }>> =>
    apiClient.get('/api/v1/model/training/jobs', { params }),

  /**
   * Get training job detail
   */
  getTrainingJobDetail: (jobId: string): Promise<ApiResponse<TrainingJob>> =>
    apiClient.get(`/api/v1/model/training/jobs/${jobId}`),

  /**
   * Create a training job
   */
  createTrainingJob: (data: CreateTrainingJobRequest): Promise<ApiResponse<TrainingJob>> =>
    apiClient.post('/api/v1/model/training/jobs', data),

  /**
   * Stop a training job
   */
  stopTrainingJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/training/jobs/${jobId}/stop`),

  /**
   * Delete a training job
   */
  deleteTrainingJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/training/jobs/${jobId}`),

  /**
   * Get training job metrics
   */
  getTrainingJobMetrics: (jobId: string, period?: MetricPeriod): Promise<ApiResponse<{ metrics: MetricDataPoint[] }>> =>
    apiClient.get(`/api/v1/model/training/jobs/${jobId}/metrics`, { params: { period } }),

  /**
   * Get training job logs
   */
  getTrainingJobLogs: (jobId: string, tail?: number): Promise<ApiResponse<{ logs: string[] }>> =>
    apiClient.get(`/api/v1/model/training/jobs/${jobId}/logs`, { params: { tail } }),

  // ==========================================================================
  // Model Serving
  // ==========================================================================

  /**
   * Get serving services list
   */
  getServingServices: (params?: ServingServicesListParams): Promise<ApiResponse<{ services: ServingService[]; total: number }>> =>
    apiClient.get('/api/v1/model/serving/services', { params }),

  /**
   * Get serving service detail
   */
  getServingServiceDetail: (serviceId: string): Promise<ApiResponse<ServingService>> =>
    apiClient.get(`/api/v1/model/serving/services/${serviceId}`),

  /**
   * Create a serving service
   */
  createServingService: (data: CreateServingServiceRequest): Promise<ApiResponse<ServingService>> =>
    apiClient.post('/api/v1/model/serving/services', data),

  /**
   * Start a serving service
   */
  startServingService: (serviceId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/serving/services/${serviceId}/start`),

  /**
   * Stop a serving service
   */
  stopServingService: (serviceId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/serving/services/${serviceId}/stop`),

  /**
   * Delete a serving service
   */
  deleteServingService: (serviceId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/serving/services/${serviceId}`),

  /**
   * Scale a serving service
   */
  scaleServingService: (serviceId: string, data: ScaleServingServiceRequest): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/serving/services/${serviceId}/scale`, data),

  /**
   * Get serving service metrics
   */
  getServingServiceMetrics: (serviceId: string, period?: MetricPeriod): Promise<ApiResponse<{ metrics: MetricDataPoint[] }>> =>
    apiClient.get(`/api/v1/model/serving/services/${serviceId}/metrics`, { params: { period } }),

  /**
   * Get serving service logs
   */
  getServingServiceLogs: (serviceId: string, tail?: number): Promise<ApiResponse<{ logs: string[] }>> =>
    apiClient.get(`/api/v1/model/serving/services/${serviceId}/logs`, { params: { tail } }),

  // ==========================================================================
  // Registered Models
  // ==========================================================================

  /**
   * Get registered models list
   */
  getRegisteredModels: (params?: RegisteredModelsListParams): Promise<ApiResponse<{ models: RegisteredModel[]; total: number }>> =>
    apiClient.get('/api/v1/model/registry/models', { params }),

  /**
   * Get registered model detail
   */
  getRegisteredModelDetail: (modelId: string): Promise<ApiResponse<RegisteredModel>> =>
    apiClient.get(`/api/v1/model/registry/models/${modelId}`),

  /**
   * Register a model
   */
  registerModel: (data: RegisterModelRequest): Promise<ApiResponse<RegisteredModel>> =>
    apiClient.post('/api/v1/model/registry/models', data),

  /**
   * Delete a registered model
   */
  deleteRegisteredModel: (modelId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/registry/models/${modelId}`),

  /**
   * Set model stage
   */
  setModelStage: (modelId: string, version: string, stage: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/registry/models/${modelId}/stage`, { version, stage }),

  // ==========================================================================
  // Notebooks
  // ==========================================================================

  /**
   * Get notebooks list
   */
  getNotebooks: (params?: NotebooksListParams): Promise<ApiResponse<{ notebooks: Notebook[]; total: number }>> =>
    apiClient.get('/api/v1/model/notebooks', { params }),

  /**
   * Get notebook images
   */
  getNotebookImages: (): Promise<ApiResponse<{ images: NotebookImage[] }>> =>
    apiClient.get('/api/v1/model/notebooks/images'),

  /**
   * Get notebook detail
   */
  getNotebookDetail: (notebookId: string): Promise<ApiResponse<Notebook>> =>
    apiClient.get(`/api/v1/model/notebooks/${notebookId}`),

  /**
   * Create a notebook
   */
  createNotebook: (data: CreateNotebookRequest): Promise<ApiResponse<Notebook>> =>
    apiClient.post('/api/v1/model/notebooks', data),

  /**
   * Start a notebook
   */
  startNotebook: (notebookId: string): Promise<ApiResponse<{ url: string }>> =>
    apiClient.post(`/api/v1/model/notebooks/${notebookId}/start`),

  /**
   * Stop a notebook
   */
  stopNotebook: (notebookId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/notebooks/${notebookId}/stop`),

  /**
   * Delete a notebook
   */
  deleteNotebook: (notebookId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/notebooks/${notebookId}`),

  // ==========================================================================
  // LLM Fine-tuning
  // ==========================================================================

  /**
   * Get fine-tuning jobs list
   */
  getFineTuningJobs: (params?: FineTuningJobsListParams): Promise<ApiResponse<{ jobs: LLMFineTuningJob[]; total: number }>> =>
    apiClient.get('/api/v1/model/finetuning/jobs', { params }),

  /**
   * Get fine-tuning datasets
   */
  getFineTuningDatasets: (): Promise<ApiResponse<{ datasets: FineTuningDataset[] }>> =>
    apiClient.get('/api/v1/model/finetuning/datasets'),

  /**
   * Get fine-tuning job detail
   */
  getFineTuningJobDetail: (jobId: string): Promise<ApiResponse<LLMFineTuningJob>> =>
    apiClient.get(`/api/v1/model/finetuning/jobs/${jobId}`),

  /**
   * Create a fine-tuning job
   */
  createFineTuningJob: (data: CreateFineTuningJobRequest): Promise<ApiResponse<LLMFineTuningJob>> =>
    apiClient.post('/api/v1/model/finetuning/jobs', data),

  /**
   * Start a fine-tuning job
   */
  startFineTuningJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/finetuning/jobs/${jobId}/start`),

  /**
   * Stop a fine-tuning job
   */
  stopFineTuningJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/finetuning/jobs/${jobId}/stop`),

  /**
   * Cancel a fine-tuning job
   */
  cancelFineTuningJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/finetuning/jobs/${jobId}/cancel`),

  /**
   * Delete a fine-tuning job
   */
  deleteFineTuningJob: (jobId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/finetuning/jobs/${jobId}`),

  // ==========================================================================
  // Pipelines
  // ==========================================================================

  /**
   * Get pipelines list
   */
  getPipelines: (params?: PipelinesListParams): Promise<ApiResponse<{ pipelines: Pipeline[]; total: number }>> =>
    apiClient.get('/api/v1/model/pipelines', { params }),

  /**
   * Get pipeline templates
   */
  getPipelineTemplates: (): Promise<ApiResponse<{ templates: PipelineTemplate[] }>> =>
    apiClient.get('/api/v1/model/pipelines/templates'),

  /**
   * Get pipeline detail
   */
  getPipelineDetail: (pipelineId: string): Promise<ApiResponse<Pipeline>> =>
    apiClient.get(`/api/v1/model/pipelines/${pipelineId}`),

  /**
   * Create a pipeline
   */
  createPipeline: (data: CreatePipelineRequest): Promise<ApiResponse<Pipeline>> =>
    apiClient.post('/api/v1/model/pipelines', data),

  /**
   * Update a pipeline
   */
  updatePipeline: (pipelineId: string, data: Partial<CreatePipelineRequest>): Promise<ApiResponse<Pipeline>> =>
    apiClient.put(`/api/v1/model/pipelines/${pipelineId}`, data),

  /**
   * Delete a pipeline
   */
  deletePipeline: (pipelineId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/pipelines/${pipelineId}`),

  /**
   * Get pipeline executions
   */
  getPipelineExecutions: (pipelineId: string): Promise<ApiResponse<{ executions: PipelineExecution[] }>> =>
    apiClient.get(`/api/v1/model/pipelines/${pipelineId}/executions`),

  /**
   * Run a pipeline
   */
  runPipeline: (pipelineId: string, variables?: Record<string, unknown>): Promise<ApiResponse<PipelineExecution>> =>
    apiClient.post(`/api/v1/model/pipelines/${pipelineId}/run`, { variables }),

  /**
   * Stop a pipeline execution
   */
  stopPipelineExecution: (executionId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/pipelines/executions/${executionId}/stop`),

  // ==========================================================================
  // Resource Management
  // ==========================================================================

  /**
   * Get resource overview
   */
  getResourceOverview: (): Promise<ApiResponse<ResourceOverview>> =>
    apiClient.get('/api/v1/model/resources/overview'),

  /**
   * Get GPU resources
   */
  getGPUResources: (): Promise<ApiResponse<{ gpus: GPUResource[] }>> =>
    apiClient.get('/api/v1/model/resources/gpus'),

  /**
   * Get resource pools
   */
  getResourcePools: (): Promise<ApiResponse<{ pools: ResourcePool[] }>> =>
    apiClient.get('/api/v1/model/resources/pools'),

  // ==========================================================================
  // Monitoring
  // ==========================================================================

  /**
   * Get metrics overview
   */
  getMetricsOverview: (): Promise<ApiResponse<MetricsOverview>> =>
    apiClient.get('/api/v1/model/monitoring/overview'),

  /**
   * Get system metrics
   */
  getSystemMetrics: (): Promise<ApiResponse<SystemMetrics>> =>
    apiClient.get('/api/v1/model/monitoring/system'),

  /**
   * Get model metrics
   */
  getModelMetrics: (modelId: string, period?: MetricPeriod): Promise<ApiResponse<{ metrics: MetricDataPoint[] }>> =>
    apiClient.get(`/api/v1/model/monitoring/models/${modelId}/metrics`, { params: { period } }),

  /**
   * Get model logs
   */
  getModelLogs: (modelId: string, tail?: number): Promise<ApiResponse<{ logs: string[] }>> =>
    apiClient.get(`/api/v1/model/monitoring/models/${modelId}/logs`, { params: { tail } }),

  /**
   * Get alert rules
   */
  getAlertRules: (): Promise<ApiResponse<{ rules: MonitoringAlertRule[] }>> =>
    apiClient.get('/api/v1/model/monitoring/alerts/rules'),

  /**
   * Create an alert rule
   */
  createAlertRule: (data: CreateAlertRuleRequest): Promise<ApiResponse<MonitoringAlertRule>> =>
    apiClient.post('/api/v1/model/monitoring/alerts/rules', data),

  /**
   * Delete an alert rule
   */
  deleteAlertRule: (ruleId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/monitoring/alerts/rules/${ruleId}`),

  /**
   * Toggle alert rule
   */
  toggleAlertRule: (ruleId: string, enabled: boolean): Promise<ApiResponse<void>> =>
    apiClient.patch(`/api/v1/model/monitoring/alerts/rules/${ruleId}`, { enabled }),

  /**
   * Get alert notifications
   */
  getAlertNotifications: (): Promise<ApiResponse<{ notifications: AlertNotification[] }>> =>
    apiClient.get('/api/v1/model/monitoring/alerts/notifications'),

  /**
   * Acknowledge alert notification
   */
  acknowledgeAlertNotification: (notificationId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/monitoring/alerts/notifications/${notificationId}/acknowledge`),

  /**
   * Resolve alert notification
   */
  resolveAlertNotification: (notificationId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/monitoring/alerts/notifications/${notificationId}/resolve`),

  /**
   * Get dashboards
   */
  getDashboards: (): Promise<ApiResponse<{ dashboards: Dashboard[] }>> =>
    apiClient.get('/api/v1/model/monitoring/dashboards'),

  /**
   * Create a dashboard
   */
  createDashboard: (data: CreateDashboardRequest): Promise<ApiResponse<Dashboard>> =>
    apiClient.post('/api/v1/model/monitoring/dashboards', data),

  /**
   * Delete a dashboard
   */
  deleteDashboard: (dashboardId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/monitoring/dashboards/${dashboardId}`),

  // ==========================================================================
  // SQL Lab
  // ==========================================================================

  /**
   * Get SQL Lab connections
   */
  getSqlLabConnections: (): Promise<ApiResponse<{ connections: SqlLabConnection[] }>> =>
    apiClient.get('/api/v1/model/sqllab/connections'),

  /**
   * Get SQL Lab tables for a database
   */
  getSqlLabTables: (databaseId: string): Promise<ApiResponse<{ tables: string[] }>> =>
    apiClient.get(`/api/v1/model/sqllab/databases/${databaseId}/tables`),

  /**
   * Get SQL Lab table schema
   */
  getSqlLabTableSchema: (databaseId: string, tableName: string): Promise<ApiResponse<{ columns: Array<{ name: string; type: string }> }>> =>
    apiClient.get(`/api/v1/model/sqllab/databases/${databaseId}/tables/${tableName}/schema`),

  /**
   * Execute SQL query
   */
  executeSqlQuery: (data: ExecuteSqlQueryRequest): Promise<ApiResponse<QueryResult>> =>
    apiClient.post('/api/v1/model/sqllab/query', data),

  /**
   * Cancel a query
   */
  cancelQuery: (queryId: string): Promise<ApiResponse<void>> =>
    apiClient.post(`/api/v1/model/sqllab/query/${queryId}/cancel`),

  /**
   * Export query result
   */
  exportQueryResult: (queryId: string, format: 'csv' | 'json' | 'excel'): Promise<ApiResponse<{ download_url: string }>> =>
    apiClient.get(`/api/v1/model/sqllab/query/${queryId}/export`, { params: { format } }),

  /**
   * Get query history
   */
  getQueryHistory: (params: { database_id?: string; limit?: number }): Promise<ApiResponse<{ history: QueryHistoryItem[] }>> =>
    apiClient.get('/api/v1/model/sqllab/history', { params }),

  /**
   * Get saved queries
   */
  getSavedQueries: (params: { database_id?: string }): Promise<ApiResponse<{ queries: SavedQuery[] }>> =>
    apiClient.get('/api/v1/model/sqllab/saved', { params }),

  /**
   * Save a query
   */
  saveQuery: (data: SaveQueryRequest): Promise<ApiResponse<SavedQuery>> =>
    apiClient.post('/api/v1/model/sqllab/saved', data),

  /**
   * Delete a saved query
   */
  deleteSavedQuery: (queryId: string): Promise<ApiResponse<void>> =>
    apiClient.delete(`/api/v1/model/sqllab/saved/${queryId}`),

  /**
   * Format SQL
   */
  formatSql: (sql: string): Promise<ApiResponse<{ formatted_sql: string }>> =>
    apiClient.post('/api/v1/model/sqllab/format', { sql }),

  // ==========================================================================
  // Databases (for compatibility)
  // ==========================================================================

  /**
   * Get databases (alias for getSqlLabConnections)
   */
  getDatabases: (): Promise<ApiResponse<{ connections: SqlLabConnection[] }>> =>
    apiClient.get('/api/v1/model/sqllab/connections'),

  /**
   * Execute query (alias for executeSqlQuery)
   */
  executeQuery: (data: ExecuteSqlQueryRequest): Promise<ApiResponse<QueryResult>> =>
    apiClient.post('/api/v1/model/sqllab/query', data),
};

export default cube;

// Re-export everything from model.ts for backward compatibility
export * from './model';
