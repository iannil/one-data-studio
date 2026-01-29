/**
 * 真实 API 客户端
 * 不使用 Mock，直接调用真实后端 API
 * 支持完整的请求/响应日志和错误处理
 */

import { APIRequestContext, APIResponse } from '@playwright/test';

// API 基础 URL
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const AGENT_API_URL = process.env.AGENT_API_URL || 'http://localhost:8000';
const DATA_API_URL = process.env.DATA_API_URL || 'http://localhost:8001';
const MODEL_API_URL = process.env.MODEL_API_URL || 'http://localhost:8002';
const OPENAI_API_URL = process.env.OPENAI_API_URL || 'http://localhost:8003';

// 兼容旧的环境变量名
const BISHENG_API_URL = process.env.BISHENG_API_URL || AGENT_API_URL;
const ALLDATA_API_URL = process.env.ALLDATA_API_URL || DATA_API_URL;
const CUBE_API_URL = process.env.CUBE_API_URL || MODEL_API_URL;

// 认证信息
interface AuthInfo {
  accessToken?: string;
  tokenType?: string;
}

// API 请求配置
interface RequestConfig {
  headers?: Record<string, string>;
  params?: Record<string, string | number>;
  timeout?: number;
}

// API 响应包装
interface ApiResponse<T = any> {
  code: number;
  message?: string;
  data?: T;
  error?: string;
}

// 请求日志
interface RequestLog {
  timestamp: string;
  method: string;
  url: string;
  status: number;
  duration: number;
  requestHeaders?: Record<string, string>;
  requestBody?: any;
  responseHeaders?: Record<string, string>;
  responseBody?: any;
  error?: string;
}

// 全局请求日志存储
const requestLogs: RequestLog[] = [];

/**
 * 清空请求日志
 */
export function clearRequestLogs(): void {
  requestLogs.length = 0;
}

/**
 * 获取所有请求日志
 */
export function getRequestLogs(): RequestLog[] {
  return [...requestLogs];
}

/**
 * 获取失败的请求日志
 */
export function getFailedRequests(): RequestLog[] {
  return requestLogs.filter(log => log.status >= 400 || log.error);
}

/**
 * 格式化请求日志为可读字符串
 */
export function formatRequestLogs(logs: RequestLog[]): string {
  return logs.map(log => {
    const status = log.error ? 'ERROR' : (log.status >= 400 ? 'FAIL' : 'OK');
    return `[${log.timestamp}] ${log.method} ${log.url} - ${status} (${log.status}) ${log.duration}ms`;
  }).join('\n');
}

/**
 * 记录请求日志
 */
function logRequest(log: RequestLog): void {
  requestLogs.push(log);

  // 控制台输出（仅开发模式）
  if (process.env.DEBUG_API === 'true') {
    console.log(`[API] ${log.method} ${log.url} => ${log.status} (${log.duration}ms)`);
  }
}

/**
 * 基础 API 客户端类
 */
export class ApiClient {
  protected request: APIRequestContext;
  protected auth: AuthInfo;
  protected baseUrl: string;
  protected defaultTimeout: number;

  constructor(request: APIRequestContext, baseUrl: string, auth?: AuthInfo) {
    this.request = request;
    this.baseUrl = baseUrl;
    this.auth = auth || {};
    this.defaultTimeout = 30000;
  }

  /**
   * 设置认证信息
   */
  setAuth(auth: AuthInfo): void {
    this.auth = auth;
  }

  /**
   * 获取默认请求头
   */
  protected getHeaders(additionalHeaders?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...additionalHeaders,
    };

    if (this.auth.accessToken) {
      headers['Authorization'] = `${this.auth.tokenType || 'Bearer'} ${this.auth.accessToken}`;
    }

    return headers;
  }

  /**
   * 构建完整 URL
   */
  protected buildUrl(path: string, params?: Record<string, string | number>): string {
    const url = new URL(path, this.baseUrl);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    return url.toString();
  }

  /**
   * 执行 HTTP 请求
   */
  protected async executeRequest(
    method: string,
    path: string,
    body?: any,
    config?: RequestConfig
  ): Promise<APIResponse> {
    const url = this.buildUrl(path, config?.params);
    const headers = this.getHeaders(config?.headers);
    const startTime = Date.now();
    const timestamp = new Date().toISOString();

    try {
      const response = await this.request.fetch(url, {
        method,
        headers,
        data: body,
        timeout: config?.timeout || this.defaultTimeout,
      });

      const duration = Date.now() - startTime;

      // 记录日志
      const log: RequestLog = {
        timestamp,
        method,
        url,
        status: response.status(),
        duration,
        requestHeaders: headers,
        requestBody: body,
        responseHeaders: response.headers(),
      };

      try {
        log.responseBody = await response.json().catch(() => response.text());
      } catch {
        // 忽略解析错误
      }

      logRequest(log);

      return response;
    } catch (error) {
      const duration = Date.now() - startTime;

      // 记录错误日志
      logRequest({
        timestamp,
        method,
        url,
        status: 0,
        duration,
        requestHeaders: headers,
        requestBody: body,
        error: error instanceof Error ? error.message : String(error),
      });

      throw error;
    }
  }

  /**
   * GET 请求
   */
  async get<T = any>(path: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.executeRequest('GET', path, undefined, config);
    return await response.json() as ApiResponse<T>;
  }

  /**
   * POST 请求
   */
  async post<T = any>(path: string, body?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.executeRequest('POST', path, body, config);
    return await response.json() as ApiResponse<T>;
  }

  /**
   * PUT 请求
   */
  async put<T = any>(path: string, body?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.executeRequest('PUT', path, body, config);
    return await response.json() as ApiResponse<T>;
  }

  /**
   * PATCH 请求
   */
  async patch<T = any>(path: string, body?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.executeRequest('PATCH', path, body, config);
    return await response.json() as ApiResponse<T>;
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(path: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const response = await this.executeRequest('DELETE', path, undefined, config);
    return await response.json() as ApiResponse<T>;
  }

  /**
   * 上传文件
   */
  async upload<T = any>(path: string, file: Buffer | string, filename: string, contentType?: string): Promise<ApiResponse<T>> {
    const url = this.buildUrl(path);
    const headers = this.getHeaders({});

    // 移除 Content-Type，让 fetch 自动设置 multipart/form-data 边界
    delete headers['Content-Type'];

    const formData = new FormData();
    const blob = typeof file === 'string' ? new Blob([file], { type: contentType }) : new Blob([file], { type: contentType });
    formData.append('file', blob, filename);

    const response = await this.request.fetch(url, {
      method: 'POST',
      headers,
      multipart: {
        file: {
          name: filename,
          buffer: typeof file === 'string' ? Buffer.from(file) : file,
          contentType: contentType || 'application/octet-stream',
        },
      },
    });

    return await response.json() as ApiResponse<T>;
  }
}

/**
 * Agent API 客户端 (原 Bisheng API)
 */
export class AgentApiClient extends ApiClient {
  constructor(request: APIRequestContext, auth?: AuthInfo) {
    super(request, AGENT_API_URL, auth);
  }

  // ============================================
  // 健康检查
  // ============================================
  async healthCheck(): Promise<ApiResponse> {
    return this.get('/api/v1/health');
  }

  // ============================================
  // 用户信息
  // ============================================
  async getUserInfo(): Promise<ApiResponse> {
    return this.get('/api/v1/user/info');
  }

  // ============================================
  // 聊天相关
  // ============================================
  async getConversations(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/conversations', { params });
  }

  async createConversation(title: string): Promise<ApiResponse> {
    return this.post('/api/v1/conversations', { title });
  }

  async getConversation(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/conversations/${id}`);
  }

  async getMessages(conversationId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/conversations/${conversationId}/messages`);
  }

  async sendMessage(conversationId: string, content: string, stream = false): Promise<ApiResponse> {
    return this.post(`/api/v1/conversations/${conversationId}/messages`, { content, stream });
  }

  // ============================================
  // 工作流相关
  // ============================================
  async getWorkflows(params?: { page?: number; page_size?: number; status?: string }): Promise<ApiResponse> {
    return this.get('/api/v1/workflows', { params });
  }

  async createWorkflow(data: { name: string; description?: string; type: string; config?: any }): Promise<ApiResponse> {
    return this.post('/api/v1/workflows', data);
  }

  async getWorkflow(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/workflows/${id}`);
  }

  async updateWorkflow(id: string, data: any): Promise<ApiResponse> {
    return this.put(`/api/v1/workflows/${id}`, data);
  }

  async deleteWorkflow(id: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/workflows/${id}`);
  }

  async runWorkflow(id: string, inputs?: any): Promise<ApiResponse> {
    return this.post(`/api/v1/workflows/${id}/run`, { inputs });
  }

  async getWorkflowExecutions(workflowId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/workflows/${workflowId}/executions`);
  }

  // ============================================
  // 数据集相关
  // ============================================
  async getDatasets(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/datasets', { params });
  }

  async createDataset(data: { name: string; description?: string; type: string }): Promise<ApiResponse> {
    return this.post('/api/v1/datasets', data);
  }

  // ============================================
  // Text2SQL 相关
  // ============================================
  async generateSQL(query: string, databaseId?: string): Promise<ApiResponse> {
    return this.post('/api/v1/text2sql/generate', { query, database_id: databaseId });
  }

  async executeSQL(sql: string): Promise<ApiResponse> {
    return this.post('/api/v1/text2sql/execute', { sql });
  }

  // ============================================
  // Agent 相关
  // ============================================
  async getAgents(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/agents', { params });
  }

  async createAgent(data: { name: string; type: string; config?: any }): Promise<ApiResponse> {
    return this.post('/api/v1/agents', data);
  }

  async runAgent(id: string, input: string): Promise<ApiResponse> {
    return this.post(`/api/v1/agents/${id}/run`, { input });
  }

  // ============================================
  // 统计信息
  // ============================================
  async getStats(): Promise<ApiResponse> {
    return this.get('/api/v1/stats/overview');
  }
}

/**
 * Data API 客户端 (原 Alldata API)
 */
export class DataApiClient extends ApiClient {
  constructor(request: APIRequestContext, auth?: AuthInfo) {
    super(request, DATA_API_URL, auth);
  }

  // ============================================
  // 健康检查
  // ============================================
  async healthCheck(): Promise<ApiResponse> {
    return this.get('/api/v1/health');
  }

  // ============================================
  // 数据源相关
  // ============================================
  async getDatasources(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/datasources', { params });
  }

  async createDatasource(data: {
    name: string;
    type: string;
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
  }): Promise<ApiResponse> {
    return this.post('/api/v1/datasources', data);
  }

  async getDatasource(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/datasources/${id}`);
  }

  async updateDatasource(id: string, data: any): Promise<ApiResponse> {
    return this.put(`/api/v1/datasources/${id}`, data);
  }

  async deleteDatasource(id: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/datasources/${id}`);
  }

  async testDatasource(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/datasources/${id}/test`, {});
  }

  // ============================================
  // 数据集相关
  // ============================================
  async getDatasets(params?: { page?: number; page_size?: number; datasource_id?: string }): Promise<ApiResponse> {
    return this.get('/api/v1/datasets', { params });
  }

  async createDataset(data: { name: string; datasource_id: string; query?: string }): Promise<ApiResponse> {
    return this.post('/api/v1/datasets', data);
  }

  async getDataset(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/datasets/${id}`);
  }

  async deleteDataset(id: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/datasets/${id}`);
  }

  async previewDataset(id: string, limit = 100): Promise<ApiResponse> {
    return this.get(`/api/v1/datasets/${id}/preview`, { params: { limit } });
  }

  // ============================================
  // 元数据相关
  // ============================================
  async getDatabases(): Promise<ApiResponse> {
    return this.get('/api/v1/metadata/databases');
  }

  async getTables(database: string): Promise<ApiResponse> {
    return this.get(`/api/v1/metadata/databases/${database}/tables`);
  }

  async getTableColumns(database: string, table: string): Promise<ApiResponse> {
    return this.get(`/api/v1/metadata/databases/${database}/tables/${table}/columns`);
  }

  async searchMetadata(keyword: string): Promise<ApiResponse> {
    return this.get('/api/v1/metadata/search', { params: { keyword } });
  }

  // ============================================
  // 查询相关
  // ============================================
  async executeQuery(data: { database: string; sql: string; limit?: number }): Promise<ApiResponse> {
    return this.post('/api/v1/query/execute', data);
  }

  async validateSQL(sql: string): Promise<ApiResponse> {
    return this.post('/api/v1/query/validate', { sql });
  }

  async getQueryHistory(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/query/history', { params });
  }

  // ============================================
  // ETL 相关
  // ============================================
  async getEtlTasks(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/etl/tasks', { params });
  }

  async createEtlTask(data: {
    name: string;
    source_id: string;
    target_id: string;
    config: any;
  }): Promise<ApiResponse> {
    return this.post('/api/v1/etl/tasks', data);
  }

  async runEtlTask(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/etl/tasks/${id}/run`, {});
  }

  async getEtlTaskRuns(taskId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/etl/tasks/${taskId}/runs`);
  }

  // ============================================
  // 数据质量相关
  // ============================================
  async getQualityRules(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/quality/rules', { params });
  }

  async createQualityRule(data: {
    name: string;
    dataset_id: string;
    rule_type: string;
    config: any;
  }): Promise<ApiResponse> {
    return this.post('/api/v1/quality/rules', data);
  }

  async runQualityCheck(ruleId: string): Promise<ApiResponse> {
    return this.post(`/api/v1/quality/rules/${ruleId}/run`, {});
  }

  async getQualityReports(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/quality/reports', { params });
  }

  // ============================================
  // 数据血缘相关
  // ============================================
  async getLineage(params?: { entity_type?: string; entity_id?: string }): Promise<ApiResponse> {
    return this.get('/api/v1/lineage', { params });
  }

  async getLineageUpstream(entityType: string, entityId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/lineage/upstream/${entityType}/${entityId}`);
  }

  async getLineageDownstream(entityType: string, entityId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/lineage/downstream/${entityType}/${entityId}`);
  }
}

/**
 * Model API 客户端 (原 Cube API)
 */
export class ModelApiClient extends ApiClient {
  constructor(request: APIRequestContext, auth?: AuthInfo) {
    super(request, MODEL_API_URL, auth);
  }

  // ============================================
  // 健康检查
  // ============================================
  async healthCheck(): Promise<ApiResponse> {
    return this.get('/api/v1/health');
  }

  // ============================================
  // Notebook 相关
  // ============================================
  async getNotebooks(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/notebooks', { params });
  }

  async createNotebook(data: { name: string; kernel?: string }): Promise<ApiResponse> {
    return this.post('/api/v1/notebooks', data);
  }

  async getNotebook(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/notebooks/${id}`);
  }

  async startNotebook(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/notebooks/${id}/start`, {});
  }

  async stopNotebook(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/notebooks/${id}/stop`, {});
  }

  async executeCode(notebookId: string, code: string): Promise<ApiResponse> {
    return this.post(`/api/v1/notebooks/${notebookId}/execute`, { code });
  }

  // ============================================
  // 实验相关
  // ============================================
  async getExperiments(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/experiments', { params });
  }

  async createExperiment(data: { name: string; project_id?: string }): Promise<ApiResponse> {
    return this.post('/api/v1/experiments', data);
  }

  async logMetrics(experimentId: string, metrics: Record<string, number>): Promise<ApiResponse> {
    return this.post(`/api/v1/experiments/${experimentId}/metrics`, { metrics });
  }

  async getExperimentMetrics(experimentId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/experiments/${experimentId}/metrics`);
  }

  // ============================================
  // 模型相关
  // ============================================
  async getModels(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/models', { params });
  }

  async registerModel(data: { name: string; version: string; experiment_id?: string }): Promise<ApiResponse> {
    return this.post('/api/v1/models', data);
  }

  async getModel(id: string): Promise<ApiResponse> {
    return this.get(`/api/v1/models/${id}`);
  }

  async deployModel(modelId: string, config?: any): Promise<ApiResponse> {
    return this.post(`/api/v1/models/${modelId}/deploy`, config || {});
  }

  // ============================================
  // 训练相关
  // ============================================
  async getTrainingJobs(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/training/jobs', { params });
  }

  async createTrainingJob(data: {
    name: string;
    model_type: string;
    config: any;
  }): Promise<ApiResponse> {
    return this.post('/api/v1/training/jobs', data);
  }

  async startTrainingJob(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/training/jobs/${id}/start`, {});
  }

  async stopTrainingJob(id: string): Promise<ApiResponse> {
    return this.post(`/api/v1/training/jobs/${id}/stop`, {});
  }

  async getTrainingLogs(jobId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/training/jobs/${jobId}/logs`);
  }

  // ============================================
  // 模型服务相关
  // ============================================
  async getDeployments(params?: { page?: number; page_size?: number }): Promise<ApiResponse> {
    return this.get('/api/v1/serving/deployments', { params });
  }

  async scaleDeployment(deploymentId: string, replicas: number): Promise<ApiResponse> {
    return this.put(`/api/v1/serving/deployments/${deploymentId}/scale`, { replicas });
  }

  async predict(deploymentId: string, data: any): Promise<ApiResponse> {
    return this.post(`/api/v1/serving/deployments/${deploymentId}/predict`, data);
  }

  // ============================================
  // AI Hub 相关
  // ============================================
  async searchModels(keyword: string): Promise<ApiResponse> {
    return this.get('/api/v1/aihub/search', { params: { keyword } });
  }

  async importModel(modelId: string): Promise<ApiResponse> {
    return this.post(`/api/v1/aihub/models/${modelId}/import`, {});
  }
}

/**
 * OpenAI Proxy API 客户端
 */
export class OpenAIProxyClient extends ApiClient {
  constructor(request: APIRequestContext, auth?: AuthInfo) {
    super(request, OPENAI_API_URL, auth);
  }

  // ============================================
  // 健康检查
  // ============================================
  async healthCheck(): Promise<ApiResponse> {
    return this.get('/health');
  }

  // ============================================
  // 聊天补全 (OpenAI 兼容)
  // ============================================
  async createChatCompletion(data: {
    model: string;
    messages: Array<{ role: string; content: string }>;
    stream?: boolean;
    temperature?: number;
    max_tokens?: number;
  }): Promise<ApiResponse> {
    return this.post('/v1/chat/completions', data);
  }

  // ============================================
  // 模型列表
  // ============================================
  async listModels(): Promise<ApiResponse> {
    return this.get('/v1/models');
  }

  // ============================================
  // 嵌入
  // ============================================
  async createEmbedding(data: {
    model: string;
    input: string | string[];
  }): Promise<ApiResponse> {
    return this.post('/v1/embeddings', data);
  }
}

/**
 * 创建 API 客户端工厂函数
 */
export function createApiClient(
  request: APIRequestContext,
  type: 'agent_api' | 'data_api' | 'model_api' | 'openai' | 'bisheng' | 'alldata' | 'cube',
  auth?: AuthInfo
): ApiClient {
  switch (type) {
    case 'agent_api':
    case 'bisheng':
      return new AgentApiClient(request, auth);
    case 'data_api':
    case 'alldata':
      return new DataApiClient(request, auth);
    case 'model_api':
    case 'cube':
      return new ModelApiClient(request, auth);
    case 'openai':
      return new OpenAIProxyClient(request, auth);
    default:
      throw new Error(`Unknown API client type: ${type}`);
  }
}

// 兼容性别名 - 支持旧的类名
export const BishengApiClient = AgentApiClient;
export const AlldataApiClient = DataApiClient;
export const CubeApiClient = ModelApiClient;
