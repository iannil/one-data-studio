import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

export interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
  permission: unknown[];
  root: string;
  parent: string | null;
}

export interface ModelsListResponse {
  object: string;
  data: Model[];
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  stream?: boolean;
  extra_params?: {
    stop?: string[];
  };
}

export interface ChatCompletionChoice {
  index: number;
  message: {
    role: string;
    content: string;
  };
  finish_reason: string;
}

export interface ChatCompletionUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
  usage: ChatCompletionUsage;
}

export interface TextCompletionRequest {
  model: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
}

export interface EmbeddingRequest {
  model: string;
  input: string[];
}

export interface EmbeddingData {
  object: string;
  embedding: number[];
  index: number;
}

export interface EmbeddingResponse {
  object: string;
  data: EmbeddingData[];
  model: string;
  usage: {
    prompt_tokens: number;
    total_tokens: number;
  };
}

export interface DeployModelRequest {
  model_name: string;
  model_path: string;
  replicas: number;
  resources: {
    gpu: {
      type: string;
      count: number;
    };
    cpu: string;
    memory: string;
  };
  params: {
    tensor_parallel_size?: number;
    max_model_len?: number;
  };
}

export interface ModelStatusResponse {
  model_id: string;
  model_name: string;
  status: string;
  endpoint: string;
  replicas: {
    ready: number;
    total: number;
  };
  created_at: string;
}

// ============= Notebook 类型 =============

export interface Notebook {
  notebook_id: string;
  name: string;
  description?: string;
  image: string;
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  workspace: string;
  url?: string;
  resources: {
    cpu: string;
    memory: string;
    gpu?: string;
  };
  created_at: string;
  updated_at?: string;
  last_active?: string;
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
  env?: Record<string, string>;
}

export interface NotebookImage {
  name: string;
  display_name: string;
  description?: string;
  python_version?: string;
  frameworks?: string[];
}

// ============= 实验 (Experiments) 类型 =============

export interface Experiment {
  experiment_id: string;
  name: string;
  description?: string;
  project: string;
  status: 'running' | 'completed' | 'failed' | 'stopped';
  start_time: string;
  end_time?: string;
  duration?: number;
  parameters: Record<string, unknown>;
  metrics?: Record<string, number>;
  artifacts?: string[];
  tags?: string[];
  created_by: string;
  created_at: string;
}

export interface ExperimentListParams {
  project?: string;
  status?: string;
  tags?: string;
  page?: number;
  page_size?: number;
}

export interface ExperimentListResponse {
  experiments: Experiment[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateExperimentRequest {
  name: string;
  description?: string;
  project: string;
  parameters?: Record<string, unknown>;
  tags?: string[];
}

export interface ExperimentMetric {
  name: string;
  value: number;
  step?: number;
  timestamp: string;
}

export interface ExperimentArtifact {
  name: string;
  type: 'model' | 'dataset' | 'log' | 'plot' | 'other';
  path: string;
  size?: number;
  created_at: string;
}

export interface ExperimentDetail extends Omit<Experiment, 'metrics' | 'artifacts'> {
  metrics: ExperimentMetric[] | Record<string, number>;
  artifacts: ExperimentArtifact[] | string[];
  logs?: string;
}

// ============= 模型管理 类型 =============

export interface RegisteredModel {
  model_id: string;
  name: string;
  version: string;
  description?: string;
  framework: 'tensorflow' | 'pytorch' | 'sklearn' | 'xgboost' | 'onnx' | 'other';
  status: 'staging' | 'production' | 'archived';
  metrics?: Record<string, number>;
  parameters?: Record<string, unknown>;
  tags?: string[];
  uri: string;
  experiment_id?: string;
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
  metrics?: Record<string, number>;
  parameters?: Record<string, unknown>;
  tags?: string[];
  experiment_id?: string;
}

export interface ModelVersion {
  version: string;
  model_id: string;
  status: string;
  created_at: string;
  metrics?: Record<string, number>;
}

// ============= 训练 (Training) 类型 =============

export interface TrainingJob {
  job_id: string;
  name: string;
  description?: string;
  project: string;
  model_name: string;
  framework: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  dataset_id?: string;
  hyperparameters: Record<string, unknown>;
  resources: {
    cpu: number;
    memory: string;
    gpu?: number;
    gpu_type?: string;
  };
  distributed?: boolean;
  worker_count?: number;
  current_epoch?: number;
  total_epochs?: number;
  metrics?: {
    loss?: number;
    accuracy?: number;
    [key: string]: number | undefined;
  };
  logs?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  created_by: string;
}

export interface CreateTrainingJobRequest {
  name: string;
  description?: string;
  project: string;
  model_name: string;
  framework: string;
  dataset_id?: string;
  hyperparameters: Record<string, unknown>;
  resources: {
    cpu: number;
    memory: string;
    gpu?: number;
    gpu_type?: string;
  };
  distributed?: boolean;
  worker_count?: number;
  output_uri?: string;
}

export interface TrainingJobListParams {
  project?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface TrainingJobListResponse {
  jobs: TrainingJob[];
  total: number;
  page: number;
  page_size: number;
}

// ============= 模型服务 (Serving) 类型 =============

export interface ServingService {
  service_id: string;
  name: string;
  model_id: string;
  model_name: string;
  model_version: string;
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  endpoint: string;
  replicas: {
    available: number;
    total: number;
  };
  resources: {
    cpu: string;
    memory: string;
    gpu?: string;
  };
  autoscaling?: {
    min_replicas: number;
    max_replicas: number;
    target_qps?: number;
  };
  metrics?: {
    qps: number;
    avg_latency_ms: number;
    error_rate: number;
  };
  created_at: string;
  updated_at?: string;
}

export interface CreateServingServiceRequest {
  name: string;
  model_id: string;
  model_version: string;
  replicas: number;
  resources: {
    cpu: string;
    memory: string;
    gpu?: string;
  };
  autoscaling?: {
    min_replicas: number;
    max_replicas: number;
    target_qps?: number;
  };
}

export interface ScaleServiceRequest {
  replicas: number;
}

export interface ServiceMetrics {
  qps: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate: number;
  timestamp: string;
}

// ============= 资源管理 类型 =============

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
    gpu_memory: number;
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
  queued_jobs: number;
  running_jobs: number;
}

export interface ResourceQuota {
  user_id: string;
  quota: {
    max_cpu: number;
    max_memory: string;
    max_gpu?: number;
    max_running_jobs: number;
  };
  used: {
    cpu: number;
    memory: string;
    gpu?: number;
    running_jobs: number;
  };
}

export interface CostAnalysis {
  period_start: string;
  period_end: string;
  total_cost: number;
  breakdown: {
    compute: number;
    storage: number;
    network: number;
  };
  by_project: Array<{
    project: string;
    cost: number;
  }>;
}

// ============= API 方法 =============

/**
 * 获取可用模型列表
 */
export async function getModels(): Promise<ModelsListResponse> {
  return apiClient.get('/v1/models');
}

/**
 * 聊天补全（非流式）
 */
export async function createChatCompletion(
  data: ChatCompletionRequest
): Promise<ChatCompletionResponse> {
  return apiClient.post('/v1/chat/completions', {
    ...data,
    stream: false,
  });
}

/**
 * 聊天补全（流式）
 */
export async function streamChatCompletion(
  data: ChatCompletionRequest,
  onChunk: (chunk: string) => void,
  onComplete: (usage?: ChatCompletionUsage) => void,
  onError: (error: Error) => void
): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
    onError(new Error('Request timeout after 60 seconds'));
  }, 60000);

  try {
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
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
    let usage: ChatCompletionUsage | undefined;

    try {
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed === 'data: [DONE]') continue;
          if (trimmed.startsWith('data: ')) {
            try {
              const json = JSON.parse(trimmed.slice(6));
              const content = json.choices?.[0]?.delta?.content;
              if (content) {
                onChunk(content);
              }
              if (json.usage) {
                usage = {
                  prompt_tokens: json.usage.prompt_tokens || 0,
                  completion_tokens: json.usage.completion_tokens || 0,
                  total_tokens: json.usage.total_tokens || 0,
                };
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
    onComplete(usage);
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof Error && error.name === 'AbortError') {
      onError(new Error('Request was cancelled'));
    } else {
      onError(error as Error);
    }
  }
}

export interface TextCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    text: string;
    index: number;
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

/**
 * 文本补全
 */
export async function createCompletion(data: TextCompletionRequest): Promise<TextCompletionResponse> {
  return apiClient.post('/v1/completions', data);
}

/**
 * 获取文本嵌入向量
 */
export async function createEmbeddings(data: EmbeddingRequest): Promise<EmbeddingResponse> {
  return apiClient.post('/v1/embeddings', data);
}

/**
 * 部署模型
 */
export async function deployModel(data: DeployModelRequest): Promise<ApiResponse<{ model_id: string }>> {
  return apiClient.post('/api/v1/models/deploy', data);
}

/**
 * 获取模型状态
 */
export async function getModelStatus(modelId: string): Promise<ApiResponse<ModelStatusResponse>> {
  return apiClient.get(`/api/v1/models/${modelId}/status`);
}

// ============= Notebook API =============

/**
 * 获取 Notebook 列表
 */
export async function getNotebooks(params?: { status?: string; page?: number; page_size?: number }): Promise<ApiResponse<{ notebooks: Notebook[]; total: number }>> {
  return apiClient.get('/api/v1/notebooks', { params });
}

/**
 * 获取 Notebook 详情
 */
export async function getNotebook(notebookId: string): Promise<ApiResponse<Notebook>> {
  return apiClient.get(`/api/v1/notebooks/${notebookId}`);
}

/**
 * 创建 Notebook
 */
export async function createNotebook(data: CreateNotebookRequest): Promise<ApiResponse<{ notebook_id: string; url: string }>> {
  return apiClient.post('/api/v1/notebooks', data);
}

/**
 * 启动 Notebook
 */
export async function startNotebook(notebookId: string): Promise<ApiResponse<{ url: string }>> {
  return apiClient.post(`/api/v1/notebooks/${notebookId}/start`);
}

/**
 * 停止 Notebook
 */
export async function stopNotebook(notebookId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/notebooks/${notebookId}/stop`);
}

/**
 * 删除 Notebook
 */
export async function deleteNotebook(notebookId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/notebooks/${notebookId}`);
}

/**
 * 获取 Notebook 镜像列表
 */
export async function getNotebookImages(): Promise<ApiResponse<{ images: NotebookImage[] }>> {
  return apiClient.get('/api/v1/notebooks/images');
}

// ============= Experiments API =============

/**
 * 获取实验列表
 */
export async function getExperiments(params?: ExperimentListParams): Promise<ApiResponse<ExperimentListResponse>> {
  return apiClient.get('/api/v1/experiments', { params });
}

/**
 * 获取实验详情
 */
export async function getExperiment(experimentId: string): Promise<ApiResponse<ExperimentDetail>> {
  return apiClient.get(`/api/v1/experiments/${experimentId}`);
}

/**
 * 创建实验
 */
export async function createExperiment(data: CreateExperimentRequest): Promise<ApiResponse<{ experiment_id: string }>> {
  return apiClient.post('/api/v1/experiments', data);
}

/**
 * 停止实验
 */
export async function stopExperiment(experimentId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/experiments/${experimentId}/stop`);
}

/**
 * 删除实验
 */
export async function deleteExperiment(experimentId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/experiments/${experimentId}`);
}

/**
 * 获取实验指标
 */
export async function getExperimentMetrics(experimentId: string): Promise<ApiResponse<ExperimentMetric[]>> {
  return apiClient.get(`/api/v1/experiments/${experimentId}/metrics`);
}

/**
 * 获取实验日志
 */
export async function getExperimentLogs(experimentId: string): Promise<ApiResponse<{ logs: string }>> {
  return apiClient.get(`/api/v1/experiments/${experimentId}/logs`);
}

/**
 * 比较实验
 */
export async function compareExperiments(experimentIds: string[]): Promise<ApiResponse<{ experiments: ExperimentDetail[] }>> {
  return apiClient.post('/api/v1/experiments/compare', { experiment_ids: experimentIds });
}

// ============= Models API =============

/**
 * 获取注册模型列表
 */
export async function getRegisteredModels(params?: { framework?: string; status?: string; page?: number; page_size?: number }): Promise<ApiResponse<{ models: RegisteredModel[]; total: number }>> {
  return apiClient.get('/api/v1/models/registered', { params });
}

/**
 * 获取注册模型详情
 */
export async function getRegisteredModel(modelId: string): Promise<ApiResponse<RegisteredModel>> {
  return apiClient.get(`/api/v1/models/registered/${modelId}`);
}

/**
 * 注册模型
 */
export async function registerModel(data: RegisterModelRequest): Promise<ApiResponse<{ model_id: string }>> {
  return apiClient.post('/api/v1/models/registered', data);
}

/**
 * 更新模型
 */
export async function updateRegisteredModel(modelId: string, data: Partial<RegisterModelRequest>): Promise<ApiResponse<RegisteredModel>> {
  return apiClient.put(`/api/v1/models/registered/${modelId}`, data);
}

/**
 * 删除模型
 */
export async function deleteRegisteredModel(modelId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/models/registered/${modelId}`);
}

/**
 * 获取模型版本列表
 */
export async function getModelVersions(modelName: string): Promise<ApiResponse<{ versions: ModelVersion[] }>> {
  return apiClient.get(`/api/v1/models/registered/${encodeURIComponent(modelName)}/versions`);
}

/**
 * 设置模型版本状态
 */
export async function setModelStage(modelId: string, version: string, stage: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/models/registered/${modelId}/versions/${version}/stage`, { stage });
}

// ============= Training API =============

/**
 * 获取训练任务列表
 */
export async function getTrainingJobs(params?: TrainingJobListParams): Promise<ApiResponse<TrainingJobListResponse>> {
  return apiClient.get('/api/v1/training/jobs', { params });
}

/**
 * 获取训练任务详情
 */
export async function getTrainingJob(jobId: string): Promise<ApiResponse<TrainingJob>> {
  return apiClient.get(`/api/v1/training/jobs/${jobId}`);
}

/**
 * 创建训练任务
 */
export async function createTrainingJob(data: CreateTrainingJobRequest): Promise<ApiResponse<{ job_id: string }>> {
  return apiClient.post('/api/v1/training/jobs', data);
}

/**
 * 停止训练任务
 */
export async function stopTrainingJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/training/jobs/${jobId}/stop`);
}

/**
 * 删除训练任务
 */
export async function deleteTrainingJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/training/jobs/${jobId}`);
}

/**
 * 获取训练任务日志
 */
export async function getTrainingJobLogs(jobId: string): Promise<ApiResponse<{ logs: string }>> {
  return apiClient.get(`/api/v1/training/jobs/${jobId}/logs`);
}

/**
 * 获取训练任务指标
 */
export async function getTrainingJobMetrics(jobId: string): Promise<ApiResponse<{ metrics: Record<string, number>[] }>> {
  return apiClient.get(`/api/v1/training/jobs/${jobId}/metrics`);
}

// ============= Serving API =============

/**
 * 获取服务列表
 */
export async function getServingServices(params?: { status?: string; page?: number; page_size?: number }): Promise<ApiResponse<{ services: ServingService[]; total: number }>> {
  return apiClient.get('/api/v1/serving/services', { params });
}

/**
 * 获取服务详情
 */
export async function getServingService(serviceId: string): Promise<ApiResponse<ServingService>> {
  return apiClient.get(`/api/v1/serving/services/${serviceId}`);
}

/**
 * 创建服务
 */
export async function createServingService(data: CreateServingServiceRequest): Promise<ApiResponse<{ service_id: string; endpoint: string }>> {
  return apiClient.post('/api/v1/serving/services', data);
}

/**
 * 启动服务
 */
export async function startServingService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/serving/services/${serviceId}/start`);
}

/**
 * 停止服务
 */
export async function stopServingService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/serving/services/${serviceId}/stop`);
}

/**
 * 删除服务
 */
export async function deleteServingService(serviceId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/serving/services/${serviceId}`);
}

/**
 * 扩缩容服务
 */
export async function scaleServingService(serviceId: string, data: ScaleServiceRequest): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/serving/services/${serviceId}/scale`, data);
}

/**
 * 获取服务指标
 */
export async function getServingServiceMetrics(serviceId: string, period?: string): Promise<ApiResponse<ServiceMetrics[]>> {
  return apiClient.get(`/api/v1/serving/services/${serviceId}/metrics`, { params: { period } });
}

/**
 * 获取服务日志
 */
export async function getServingServiceLogs(serviceId: string): Promise<ApiResponse<{ logs: string }>> {
  return apiClient.get(`/api/v1/serving/services/${serviceId}/logs`);
}

// ============= Resources API =============

/**
 * 获取 GPU 资源列表
 */
export async function getGPUResources(): Promise<ApiResponse<{ gpus: GPUResource[] }>> {
  return apiClient.get('/api/v1/resources/gpu');
}

/**
 * 获取资源池列表
 */
export async function getResourcePools(): Promise<ApiResponse<{ pools: ResourcePool[] }>> {
  return apiClient.get('/api/v1/resources/pools');
}

/**
 * 获取用户配额
 */
export async function getResourceQuota(userId?: string): Promise<ApiResponse<ResourceQuota>> {
  return apiClient.get('/api/v1/resources/quota', { params: { user_id: userId } });
}

/**
 * 获取成本分析
 */
export async function getCostAnalysis(params?: { period_start?: string; period_end?: string }): Promise<ApiResponse<CostAnalysis>> {
  return apiClient.get('/api/v1/resources/costs', { params });
}

/**
 * 获取资源使用概览
 */
export async function getResourceOverview(): Promise<ApiResponse<{
  total_gpu: number;
  used_gpu: number;
  available_gpu: number;
  total_cpu: number;
  used_cpu: number;
  running_jobs: number;
  queued_jobs: number;
}>> {
  return apiClient.get('/api/v1/resources/overview');
}

// ============= AIHub 模型市场类型 =============

export interface HubModel {
  model_id: string;
  name: string;
  display_name: string;
  description?: string;
  framework: 'pytorch' | 'tensorflow' | 'jax' | 'onnx' | 'other';
  task_type: 'nlp' | 'cv' | 'multimodal' | 'audio' | 'recommendation' | 'other';
  architecture?: string;
  parameters: 'small' | 'medium' | 'large' | 'xl';
  size_bytes?: number;
  accuracy?: number;
  popularity: number;
  downloads: number;
  tags: string[];
  license: string;
  author?: string;
  paper_url?: string;
  repo_url?: string;
  created_at: string;
  updated_at?: string;
}

export interface HubModelFilter {
  task_type?: string;
  framework?: string;
  parameters?: string;
  min_accuracy?: number;
  tags?: string[];
  search?: string;
}

export interface HubModelDetail extends HubModel {
  benchmarks?: Array<{
    dataset: string;
    metric: string;
    score: number;
  }>;
  requirements?: {
    gpu_memory?: string;
    storage?: string;
    python_version?: string;
    dependencies?: string[];
  };
  usage_example?: string;
  model_card?: string;
}

export interface ModelDeploymentConfig {
  model_id: string;
  resources: {
    gpu_type: string;
    gpu_count: number;
    cpu: string;
    memory: string;
  };
  parameters?: {
    tensor_parallel_size?: number;
    max_model_len?: number;
    temperature?: number;
    top_p?: number;
  };
  replicas: number;
}

// ============= Pipeline 编排类型 =============

export interface PipelineTemplate {
  template_id: string;
  name: string;
  description?: string;
  category: 'data' | 'training' | 'serving' | 'custom';
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  thumbnail?: string;
  tags: string[];
  created_by: string;
  created_at: string;
}

export interface PipelineNode {
  node_id: string;
  name: string;
  type: 'data' | 'process' | 'model' | 'evaluate' | 'deploy' | 'custom';
  config: {
    source_type?: string;
    source_path?: string;
    model_id?: string;
    script?: string;
    parameters?: Record<string, unknown>;
    dependencies?: string[];
  };
  position: { x: number; y: number };
}

export interface PipelineEdge {
  edge_id: string;
  source: string;
  target: string;
  source_handle?: string;
  target_handle?: string;
}

export interface Pipeline {
  pipeline_id: string;
  name: string;
  description?: string;
  template_id?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  variables?: Record<string, unknown>;
  schedule?: {
    type: 'cron' | 'event' | 'manual';
    expression?: string;
  };
  status: 'draft' | 'active' | 'paused' | 'archived';
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface PipelineExecution {
  execution_id: string;
  pipeline_id: string;
  pipeline_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  variables?: Record<string, unknown>;
  node_statuses: Array<{
    node_id: string;
    node_name: string;
    status: string;
    start_time?: string;
    end_time?: string;
    output?: unknown;
    error?: string;
  }>;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  triggered_by: string;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  template_id?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  variables?: Record<string, unknown>;
  schedule?: {
    type: 'cron' | 'event' | 'manual';
    expression?: string;
  };
}

// ============= LLM 微调类型 =============

export interface LLMFineTuningJob {
  job_id: string;
  name: string;
  description?: string;
  base_model: string;
  method: 'full' | 'lora' | 'qlora' | 'adapter';
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  config: {
    learning_rate: number;
    batch_size: number;
    num_epochs: number;
    max_steps?: number;
    gradient_accumulation_steps?: number;
    warmup_steps?: number;
    weight_decay?: number;
    lora_config?: {
      r: number;
      lora_alpha: number;
      target_modules: string[];
      lora_dropout: number;
    };
  };
  resources: {
    gpu_type: string;
    gpu_count: number;
    cpu: string;
    memory: string;
  };
  output_path?: string;
  metrics?: {
    step: number;
    loss: number;
    learning_rate: number;
    epoch: number;
  }[];
  checkpoints?: string[];
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface CreateFineTuningJobRequest {
  name: string;
  description?: string;
  base_model: string;
  method: 'full' | 'lora' | 'qlora' | 'adapter';
  dataset_id: string;
  config: {
    learning_rate: number;
    batch_size: number;
    num_epochs: number;
    max_steps?: number;
    gradient_accumulation_steps?: number;
    warmup_steps?: number;
    weight_decay?: number;
    lora_config?: {
      r: number;
      lora_alpha: number;
      target_modules: string[];
      lora_dropout: number;
    };
  };
  resources: {
    gpu_type: string;
    gpu_count: number;
    cpu: string;
    memory: string;
  };
}

export interface FineTuningDataset {
  dataset_id: string;
  name: string;
  description?: string;
  format: 'jsonl' | 'parquet' | 'json';
  file_count: number;
  total_samples: number;
  size_bytes: number;
  schema?: {
    instruction?: string;
    input?: string;
    output?: string;
    system_prompt?: string;
  };
  created_by: string;
  created_at: string;
}

export interface ModelExport {
  export_id: string;
  job_id: string;
  format: 'pytorch' | 'safetensors' | 'gguf' | 'onnx';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  output_path?: string;
  download_url?: string;
  created_at: string;
}

// ============= AIHub API =============

/**
 * 获取模型市场列表
 */
export async function getHubModels(params?: {
  task_type?: string;
  framework?: string;
  parameters?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ models: HubModel[]; total: number }>> {
  return apiClient.get('/api/v1/hub/models', { params });
}

/**
 * 获取模型详情
 */
export async function getHubModelDetail(modelId: string): Promise<ApiResponse<HubModelDetail>> {
  return apiClient.get(`/api/v1/hub/models/${modelId}`);
}

/**
 * 部署市场模型
 */
export async function deployHubModel(modelId: string, config: ModelDeploymentConfig): Promise<ApiResponse<{ service_id: string }>> {
  return apiClient.post(`/api/v1/hub/models/${modelId}/deploy`, config);
}

/**
 * 下载模型
 */
export async function downloadHubModel(modelId: string): Promise<ApiResponse<{ download_url: string }>> {
  return apiClient.post(`/api/v1/hub/models/${modelId}/download`);
}

/**
 * 获取模型分类
 */
export async function getHubCategories(): Promise<ApiResponse<{ categories: Array<{ value: string; label: string; count: number }> }>> {
  return apiClient.get('/api/v1/hub/categories');
}

// ============= Pipeline API =============

/**
 * 获取 Pipeline 模板列表
 */
export async function getPipelineTemplates(params?: {
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ templates: PipelineTemplate[]; total: number }>> {
  return apiClient.get('/api/v1/pipelines/templates', { params });
}

/**
 * 获取 Pipeline 列表
 */
export async function getPipelines(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ pipelines: Pipeline[]; total: number }>> {
  return apiClient.get('/api/v1/pipelines', { params });
}

/**
 * 获取 Pipeline 详情
 */
export async function getPipeline(pipelineId: string): Promise<ApiResponse<Pipeline>> {
  return apiClient.get(`/api/v1/pipelines/${pipelineId}`);
}

/**
 * 创建 Pipeline
 */
export async function createPipeline(data: CreatePipelineRequest): Promise<ApiResponse<{ pipeline_id: string }>> {
  return apiClient.post('/api/v1/pipelines', data);
}

/**
 * 更新 Pipeline
 */
export async function updatePipeline(pipelineId: string, data: Partial<CreatePipelineRequest>): Promise<ApiResponse<Pipeline>> {
  return apiClient.put(`/api/v1/pipelines/${pipelineId}`, data);
}

/**
 * 删除 Pipeline
 */
export async function deletePipeline(pipelineId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/pipelines/${pipelineId}`);
}

/**
 * 执行 Pipeline
 */
export async function executePipeline(pipelineId: string, variables?: Record<string, unknown>): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/pipelines/${pipelineId}/execute`, { variables });
}

/**
 * 获取执行记录
 */
export async function getPipelineExecutions(pipelineId: string, params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ executions: PipelineExecution[]; total: number }>> {
  return apiClient.get(`/api/v1/pipelines/${pipelineId}/executions`, { params });
}

/**
 * 获取执行详情
 */
export async function getPipelineExecution(executionId: string): Promise<ApiResponse<PipelineExecution>> {
  return apiClient.get(`/api/v1/pipelines/executions/${executionId}`);
}

/**
 * 停止执行
 */
export async function stopPipelineExecution(executionId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/pipelines/executions/${executionId}/stop`);
}

// ============= LLM 微调 API =============

/**
 * 获取微调任务列表
 */
export async function getFineTuningJobs(params?: {
  status?: string;
  base_model?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ jobs: LLMFineTuningJob[]; total: number }>> {
  return apiClient.get('/api/v1/llm/tuning', { params });
}

/**
 * 获取微调任务详情
 */
export async function getFineTuningJob(jobId: string): Promise<ApiResponse<LLMFineTuningJob>> {
  return apiClient.get(`/api/v1/llm/tuning/${jobId}`);
}

/**
 * 创建微调任务
 */
export async function createFineTuningJob(data: CreateFineTuningJobRequest): Promise<ApiResponse<{ job_id: string }>> {
  return apiClient.post('/api/v1/llm/tuning', data);
}

/**
 * 启动微调任务
 */
export async function startFineTuningJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/llm/tuning/${jobId}/start`);
}

/**
 * 停止微调任务
 */
export async function stopFineTuningJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/llm/tuning/${jobId}/stop`);
}

/**
 * 删除微调任务
 */
export async function deleteFineTuningJob(jobId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/llm/tuning/${jobId}`);
}

/**
 * 获取微调指标
 */
export async function getFineTuningMetrics(jobId: string): Promise<ApiResponse<{ metrics: LLMFineTuningJob['metrics'] }>> {
  return apiClient.get(`/api/v1/llm/tuning/${jobId}/metrics`);
}

/**
 * 获取微调数据集列表
 */
export async function getFineTuningDatasets(params?: {
  format?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ datasets: FineTuningDataset[]; total: number }>> {
  return apiClient.get('/api/v1/llm/datasets', { params });
}

/**
 * 上传微调数据集
 */
export async function uploadFineTuningDataset(formData: FormData): Promise<ApiResponse<{ dataset_id: string }>> {
  return apiClient.post('/api/v1/llm/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 导出模型
 */
export async function exportModel(jobId: string, format: 'pytorch' | 'safetensors' | 'gguf' | 'onnx'): Promise<ApiResponse<{ export_id: string }>> {
  return apiClient.post(`/api/v1/llm/tuning/${jobId}/export`, { format });
}

/**
 * 获取导出状态
 */
export async function getExportStatus(exportId: string): Promise<ApiResponse<ModelExport>> {
  return apiClient.get(`/api/v1/llm/exports/${exportId}`);
}

// ============= SQL Lab 类型 =============

export type SqlDatabaseType = 'mysql' | 'postgresql' | 'clickhouse' | 'hive' | 'presto' | 'oracle' | 'sqlserver';
export type QueryStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface SqlDatabaseConnection {
  id: string;
  name: string;
  type: SqlDatabaseType;
  host: string;
  port: number;
  database?: string;
  username: string;
  description?: string;
  is_default: boolean;
  created_at: string;
}

export interface SqlQuery {
  query_id: string;
  name: string;
  sql: string;
  database_id: string;
  database_name: string;
  status: QueryStatus;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  row_count?: number;
  error_message?: string;
}

export interface SavedQuery {
  saved_query_id: string;
  name: string;
  description?: string;
  sql: string;
  database_id: string;
  database_name: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface QueryResult {
  query_id: string;
  status: QueryStatus;
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
  database_name: string;
  status: QueryStatus;
  executed_at: string;
  duration_ms?: number;
  row_count?: number;
}

export interface CreateSavedQueryRequest {
  name: string;
  description?: string;
  sql: string;
  database_id: string;
  tags?: string[];
}

// ============= 监控告警类型 =============

export type MetricType = 'loss' | 'accuracy' | 'precision' | 'recall' | 'f1' | 'auc' | 'learning_rate' | 'gpu_utilization' | 'memory_usage' | 'cpu_usage';
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';
export type AlertCondition = 'greater_than' | 'less_than' | 'equal_to' | 'not_equal_to' | 'contains';
export type MetricPeriod = '1m' | '5m' | '15m' | '1h' | '6h' | '1d' | '7d';

export interface MonitoringMetric {
  metric_id: string;
  name: string;
  type: MetricType;
  value: number;
  timestamp: string;
  labels?: Record<string, string>;
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
  step?: number;
}

export interface TrainingMetrics {
  job_id: string;
  job_name: string;
  metrics: Record<string, MetricDataPoint[]>;
  start_time: string;
  end_time?: string;
}

export interface MonitoringAlertRule {
  rule_id: string;
  name: string;
  description?: string;
  metric_type: MetricType;
  condition: AlertCondition;
  threshold: number;
  severity: AlertSeverity;
  enabled: boolean;
  target_type: 'training' | 'serving' | 'resource' | 'all';
  target_id?: string;
  notification_channels: AlertChannel[];
  cooldown_minutes: number;
  created_at: string;
  updated_at?: string;
}

export interface CreateAlertRuleRequest {
  name: string;
  description?: string;
  metric_type: MetricType;
  condition: AlertCondition;
  threshold: number;
  severity: AlertSeverity;
  target_type: 'training' | 'serving' | 'resource' | 'all';
  target_id?: string;
  notification_channels: AlertChannel[];
  cooldown_minutes?: number;
}

export interface AlertNotification {
  notification_id: string;
  rule_id: string;
  rule_name: string;
  severity: AlertSeverity;
  message: string;
  metric_value: number;
  threshold: number;
  target_type: string;
  target_id: string;
  status: 'active' | 'acknowledged' | 'resolved';
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  acknowledged_by?: string;
}

export interface Dashboard {
  dashboard_id: string;
  name: string;
  description?: string;
  panels: DashboardPanel[];
  refresh_interval?: number;
  is_public: boolean;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface DashboardPanel {
  panel_id: string;
  title: string;
  type: 'line' | 'bar' | 'gauge' | 'stat' | 'table' | 'heatmap';
  query: {
    metric_type: MetricType;
    target_id?: string;
    aggregation?: 'avg' | 'sum' | 'min' | 'max' | 'count';
    period?: MetricPeriod;
  };
  position: { x: number; y: number; w: number; h: number };
  config?: Record<string, unknown>;
}

export interface SystemMetrics {
  timestamp: string;
  cpu: {
    usage_percent: number;
    cores: number;
    load_avg: number[];
  };
  memory: {
    used_gb: number;
    total_gb: number;
    usage_percent: number;
  };
  disk: {
    used_gb: number;
    total_gb: number;
    usage_percent: number;
    read_iops: number;
    write_iops: number;
  };
  network: {
    inbound_mbps: number;
    outbound_mbps: number;
  };
  gpu: Array<{
    gpu_id: string;
    name: string;
    utilization_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
    temperature_c: number;
    power_usage_w: number;
  }>;
}

export type AlertChannel = 'email' | 'webhook' | 'dingtalk' | 'feishu' | 'slack' | 'telegram';

// ============= 监控告警 API =============

/**
 * 获取训练任务实时指标
 */
export async function getTrainingMetricsRealtime(jobId: string): Promise<ApiResponse<TrainingMetrics>> {
  return apiClient.get(`/api/v1/monitoring/training/${jobId}/metrics`);
}

/**
 * 获取历史指标数据
 */
export async function getMetricHistory(params: {
  metric_type: MetricType;
  target_id?: string;
  start_time?: string;
  end_time?: string;
  period?: MetricPeriod;
  aggregation?: 'avg' | 'sum' | 'min' | 'max' | 'count';
}): Promise<ApiResponse<{
  metric_type: MetricType;
  data_points: MetricDataPoint[];
}>> {
  return apiClient.get('/api/v1/monitoring/metrics/history', { params });
}

/**
 * 获取系统指标
 */
export async function getSystemMetrics(): Promise<ApiResponse<SystemMetrics>> {
  return apiClient.get('/api/v1/monitoring/system');
}

/**
 * 获取系统指标历史
 */
export async function getSystemMetricsHistory(params: {
  start_time?: string;
  end_time?: string;
  period?: MetricPeriod;
}): Promise<ApiResponse<{
  metrics: SystemMetrics[];
}>> {
  return apiClient.get('/api/v1/monitoring/system/history', { params });
}

/**
 * 获取告警规则列表
 */
export async function getAlertRules(params?: {
  target_type?: string;
  enabled?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ rules: MonitoringAlertRule[]; total: number }>> {
  return apiClient.get('/api/v1/monitoring/alerts/rules', { params });
}

/**
 * 获取告警规则详情
 */
export async function getAlertRule(ruleId: string): Promise<ApiResponse<MonitoringAlertRule>> {
  return apiClient.get(`/api/v1/monitoring/alerts/rules/${ruleId}`);
}

/**
 * 创建告警规则
 */
export async function createAlertRule(data: CreateAlertRuleRequest): Promise<ApiResponse<{ rule_id: string }>> {
  return apiClient.post('/api/v1/monitoring/alerts/rules', data);
}

/**
 * 更新告警规则
 */
export async function updateAlertRule(ruleId: string, data: Partial<CreateAlertRuleRequest>): Promise<ApiResponse<MonitoringAlertRule>> {
  return apiClient.put(`/api/v1/monitoring/alerts/rules/${ruleId}`, data);
}

/**
 * 删除告警规则
 */
export async function deleteAlertRule(ruleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/monitoring/alerts/rules/${ruleId}`);
}

/**
 * 启用/禁用告警规则
 */
export async function toggleAlertRule(ruleId: string, enabled: boolean): Promise<ApiResponse<void>> {
  return apiClient.put(`/api/v1/monitoring/alerts/rules/${ruleId}/toggle`, { enabled });
}

/**
 * 获取告警通知列表
 */
export async function getAlertNotifications(params?: {
  rule_id?: string;
  severity?: AlertSeverity;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ notifications: AlertNotification[]; total: number }>> {
  return apiClient.get('/api/v1/monitoring/alerts/notifications', { params });
}

/**
 * 确认告警
 */
export async function acknowledgeAlertNotification(notificationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/monitoring/alerts/notifications/${notificationId}/acknowledge`);
}

/**
 * 解决告警
 */
export async function resolveAlertNotification(notificationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/monitoring/alerts/notifications/${notificationId}/resolve`);
}

/**
 * 获取仪表板列表
 */
export async function getDashboards(params?: {
  is_public?: boolean;
  created_by?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ dashboards: Dashboard[]; total: number }>> {
  return apiClient.get('/api/v1/monitoring/dashboards', { params });
}

/**
 * 获取仪表板详情
 */
export async function getDashboard(dashboardId: string): Promise<ApiResponse<Dashboard>> {
  return apiClient.get(`/api/v1/monitoring/dashboards/${dashboardId}`);
}

/**
 * 创建仪表板
 */
export async function createDashboard(data: {
  name: string;
  description?: string;
  panels: DashboardPanel[];
  refresh_interval?: number;
  is_public?: boolean;
}): Promise<ApiResponse<{ dashboard_id: string }>> {
  return apiClient.post('/api/v1/monitoring/dashboards', data);
}

/**
 * 更新仪表板
 */
export async function updateDashboard(dashboardId: string, data: {
  name?: string;
  description?: string;
  panels?: DashboardPanel[];
  refresh_interval?: number;
  is_public?: boolean;
}): Promise<ApiResponse<Dashboard>> {
  return apiClient.put(`/api/v1/monitoring/dashboards/${dashboardId}`, data);
}

/**
 * 删除仪表板
 */
export async function deleteDashboard(dashboardId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/monitoring/dashboards/${dashboardId}`);
}

/**
 * 获取指标概览
 */
export async function getMetricsOverview(): Promise<ApiResponse<{
  active_jobs: number;
  active_services: number;
  total_gpus: number;
  used_gpus: number;
  avg_gpu_utilization: number;
  total_memory_gb: number;
  used_memory_gb: number;
  active_alerts: number;
  critical_alerts: number;
}>> {
  return apiClient.get('/api/v1/monitoring/overview');
}

// ============= SQL Lab API =============

/**
 * 获取 SQL Lab 数据库连接列表
 */
export async function getSqlLabConnections(): Promise<ApiResponse<{ connections: SqlDatabaseConnection[] }>> {
  return apiClient.get('/api/v1/cube/sql-lab/connections');
}

/**
 * 执行 SQL 查询
 */
export async function executeSqlQuery(data: {
  database_id: string;
  sql: string;
  limit?: number;
}): Promise<ApiResponse<QueryResult>> {
  return apiClient.post('/api/v1/cube/sql-lab/execute', data);
}

/**
 * 获取查询结果
 */
export async function getQueryResult(queryId: string): Promise<ApiResponse<QueryResult>> {
  return apiClient.get(`/api/v1/cube/sql-lab/queries/${queryId}/result`);
}

/**
 * 取消查询
 */
export async function cancelQuery(queryId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/cube/sql-lab/queries/${queryId}/cancel`);
}

/**
 * 获取查询历史
 */
export async function getQueryHistory(params?: {
  database_id?: string;
  limit?: number;
}): Promise<ApiResponse<{ history: QueryHistoryItem[] }>> {
  return apiClient.get('/api/v1/cube/sql-lab/history', { params });
}

/**
 * 获取保存的查询列表
 */
export async function getSavedQueries(params?: {
  database_id?: string;
  tags?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ queries: SavedQuery[]; total: number }>> {
  return apiClient.get('/api/v1/cube/sql-lab/saved', { params });
}

/**
 * 获取保存的查询详情
 */
export async function getSavedQuery(savedQueryId: string): Promise<ApiResponse<SavedQuery>> {
  return apiClient.get(`/api/v1/cube/sql-lab/saved/${savedQueryId}`);
}

/**
 * 保存查询
 */
export async function saveQuery(data: CreateSavedQueryRequest): Promise<ApiResponse<{ saved_query_id: string }>> {
  return apiClient.post('/api/v1/cube/sql-lab/saved', data);
}

/**
 * 更新保存的查询
 */
export async function updateSavedQuery(savedQueryId: string, data: Partial<CreateSavedQueryRequest>): Promise<ApiResponse<SavedQuery>> {
  return apiClient.put(`/api/v1/cube/sql-lab/saved/${savedQueryId}`, data);
}

/**
 * 删除保存的查询
 */
export async function deleteSavedQuery(savedQueryId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/cube/sql-lab/saved/${savedQueryId}`);
}

/**
 * 导出查询结果
 */
export async function exportQueryResult(queryId: string, format: 'csv' | 'json' | 'excel'): Promise<ApiResponse<{ download_url: string }>> {
  return apiClient.post(`/api/v1/cube/sql-lab/queries/${queryId}/export`, { format });
}

/**
 * 获取数据库表列表
 */
export async function getSqlLabTables(databaseId: string): Promise<ApiResponse<{ tables: string[] }>> {
  return apiClient.get(`/api/v1/cube/sql-lab/connections/${databaseId}/tables`);
}

/**
 * 获取表结构
 */
export async function getSqlLabTableSchema(databaseId: string, tableName: string): Promise<ApiResponse<{
  columns: Array<{ name: string; type: string; nullable: boolean }>;
}>> {
  return apiClient.get(`/api/v1/cube/sql-lab/connections/${databaseId}/tables/${tableName}/schema`);
}

/**
 * 格式化 SQL
 */
export async function formatSql(sql: string): Promise<ApiResponse<{ formatted_sql: string }>> {
  return apiClient.post('/api/v1/cube/sql-lab/format', { sql });
}

/**
 * 验证 SQL 语法
 */
export async function validateSqlSyntax(databaseId: string, sql: string): Promise<ApiResponse<{
  valid: boolean;
  errors?: Array<{ line: number; column: number; message: string }>;
}>> {
  return apiClient.post('/api/v1/cube/sql-lab/validate', { database_id: databaseId, sql });
}

export default {
  // 原有 OpenAI 兼容 API
  getModels,
  createChatCompletion,
  streamChatCompletion,
  createCompletion,
  createEmbeddings,
  deployModel,
  getModelStatus,

  // Notebook
  getNotebooks,
  getNotebook,
  createNotebook,
  startNotebook,
  stopNotebook,
  deleteNotebook,
  getNotebookImages,

  // Experiments
  getExperiments,
  getExperiment,
  createExperiment,
  stopExperiment,
  deleteExperiment,
  getExperimentMetrics,
  getExperimentLogs,
  compareExperiments,

  // Models
  getRegisteredModels,
  getRegisteredModel,
  registerModel,
  updateRegisteredModel,
  deleteRegisteredModel,
  getModelVersions,
  setModelStage,

  // Training
  getTrainingJobs,
  getTrainingJob,
  createTrainingJob,
  stopTrainingJob,
  deleteTrainingJob,
  getTrainingJobLogs,
  getTrainingJobMetrics,

  // Serving
  getServingServices,
  getServingService,
  createServingService,
  startServingService,
  stopServingService,
  deleteServingService,
  scaleServingService,
  getServingServiceMetrics,
  getServingServiceLogs,

  // Resources
  getGPUResources,
  getResourcePools,
  getResourceQuota,
  getCostAnalysis,
  getResourceOverview,

  // 监控告警
  getTrainingMetricsRealtime,
  getMetricHistory,
  getSystemMetrics,
  getSystemMetricsHistory,
  getAlertRules,
  getAlertRule,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  toggleAlertRule,
  getAlertNotifications,
  acknowledgeAlertNotification,
  resolveAlertNotification,
  getDashboards,
  getDashboard,
  createDashboard,
  updateDashboard,
  deleteDashboard,
  getMetricsOverview,

  // AIHub
  getHubModels,
  getHubModelDetail,
  deployHubModel,
  downloadHubModel,
  getHubCategories,

  // Pipeline
  getPipelineTemplates,
  getPipelines,
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  executePipeline,
  getPipelineExecutions,
  getPipelineExecution,
  stopPipelineExecution,

  // LLM 微调
  getFineTuningJobs,
  getFineTuningJob,
  createFineTuningJob,
  startFineTuningJob,
  stopFineTuningJob,
  deleteFineTuningJob,
  getFineTuningMetrics,
  getFineTuningDatasets,
  uploadFineTuningDataset,
  exportModel,
  getExportStatus,

  // SQL Lab
  getSqlLabConnections,
  executeSqlQuery,
  getQueryResult,
  cancelQuery,
  getQueryHistory,
  getSavedQueries,
  getSavedQuery,
  saveQuery,
  updateSavedQuery,
  deleteSavedQuery,
  exportQueryResult,
  getSqlLabTables,
  getSqlLabTableSchema,
  formatSql,
  validateSqlSyntax,
};
