import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

export interface PromptTemplate {
  template_id: string;
  name: string;
  description?: string;
  content: string;
  variables: string[];
  created_at: string;
  updated_at?: string;
}

export interface ChatRequest {
  message: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  template_id?: string;
  template_variables?: Record<string, string>;
  stream?: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface Conversation {
  conversation_id: string;
  title: string;
  model: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Workflow {
  workflow_id: string;
  name: string;
  description?: string;
  type: 'rag' | 'text2sql' | 'custom';
  status: 'running' | 'stopped' | 'error' | 'pending';
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  type: 'rag' | 'text2sql' | 'custom';
  config?: Record<string, unknown>;
}

// 工作流执行相关类型 (Phase 6)
export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  inputs?: Record<string, unknown>;
  outputs?: unknown;
  node_results?: Record<string, unknown>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  created_at: string;
}

export interface StartWorkflowRequest {
  inputs?: Record<string, unknown>;
}

export interface StopWorkflowRequest {
  execution_id: string;
}

export interface ExecutionLog {
  id: number;
  execution_id: string;
  node_id?: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

export interface RagQueryRequest {
  query: string;
  top_k?: number;
  score_threshold?: number;
}

export interface RagQueryResponse {
  query_id: string;
  results: Array<{
    content: string;
    source: string;
    score: number;
  }>;
  answer?: string;
}

export interface Text2SqlRequest {
  natural_language: string;
  database?: string;
  selected_tables?: string[];
}

export interface Text2SqlResponse {
  sql: string;
  confidence: number;
  tables_used: string[];
}

// ============= API 方法 =============

/**
 * 获取 Prompt 模板列表
 */
export async function getPromptTemplates(): Promise<ApiResponse<{ templates: PromptTemplate[] }>> {
  return apiClient.get('/api/v1/templates');
}

/**
 * 获取单个 Prompt 模板
 */
export async function getPromptTemplate(templateId: string): Promise<ApiResponse<PromptTemplate>> {
  return apiClient.get(`/api/v1/templates/${templateId}`);
}

/**
 * 发送聊天消息
 */
export async function sendChatMessage(data: ChatRequest): Promise<ApiResponse<ChatResponse>> {
  return apiClient.post('/api/v1/chat', {
    ...data,
    stream: false,
  });
}

/**
 * 发送聊天消息（流式）
 * 返回一个 ReadableStream
 */
export async function streamChatMessage(
  data: ChatRequest,
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
    onError(new Error('Request timeout after 60 seconds'));
  }, 60000); // 60 second timeout

  try {
    const response = await fetch('/api/v1/chat', {
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
      // Handle specific HTTP status codes
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
          if (!trimmed || trimmed === 'data: [DONE]') continue;
          if (trimmed.startsWith('data: ')) {
            try {
              const json = JSON.parse(trimmed.slice(6));
              const content = json.content || json.choices?.[0]?.delta?.content;
              if (content) {
                onChunk(content);
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
    onComplete();
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof Error && error.name === 'AbortError') {
      onError(new Error('Request was cancelled'));
    } else {
      onError(error as Error);
    }
  }
}

/**
 * 获取对话列表
 */
export async function getConversations(): Promise<ApiResponse<{ conversations: Conversation[] }>> {
  return apiClient.get('/api/v1/conversations');
}

/**
 * 获取对话详情
 */
export async function getConversation(
  conversationId: string
): Promise<ApiResponse<Conversation & { messages: ConversationMessage[] }>> {
  return apiClient.get(`/api/v1/conversations/${conversationId}`);
}

/**
 * 创建新对话
 */
export async function createConversation(
  title?: string
): Promise<ApiResponse<{ conversation_id: string }>> {
  return apiClient.post('/api/v1/conversations', { title });
}

/**
 * 删除对话
 */
export async function deleteConversation(conversationId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/conversations/${conversationId}`);
}

/**
 * 重命名对话
 */
export async function renameConversation(
  conversationId: string,
  title: string
): Promise<ApiResponse<{ conversation_id: string; title: string }>> {
  return apiClient.put(`/api/v1/conversations/${conversationId}`, { title });
}

/**
 * 保存消息到对话
 */
export async function saveMessage(
  conversationId: string,
  data: {
    role: 'user' | 'assistant';
    content: string;
    model?: string;
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  }
): Promise<ApiResponse<{ message_id: string; conversation_id: string }>> {
  return apiClient.post(`/api/v1/conversations/${conversationId}/messages`, data);
}

/**
 * 获取对话的 Token 使用统计
 */
export async function getConversationUsage(
  conversationId: string
): Promise<ApiResponse<{
  conversation_id: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  message_count: number;
}>> {
  return apiClient.get(`/api/v1/conversations/${conversationId}/usage`);
}

/**
 * 获取工作流列表
 */
export async function getWorkflows(): Promise<ApiResponse<{ workflows: Workflow[] }>> {
  return apiClient.get('/api/v1/workflows');
}

/**
 * 获取工作流详情
 */
export async function getWorkflow(workflowId: string): Promise<ApiResponse<Workflow>> {
  return apiClient.get(`/api/v1/workflows/${workflowId}`);
}

/**
 * 创建工作流
 */
export async function createWorkflow(
  data: CreateWorkflowRequest
): Promise<ApiResponse<{ workflow_id: string }>> {
  return apiClient.post('/api/v1/workflows', data);
}

/**
 * 启动工作流
 */
export async function startWorkflow(
  workflowId: string,
  data?: StartWorkflowRequest
): Promise<ApiResponse<{ execution_id: string; workflow_id: string; status: string }>> {
  return apiClient.post(`/api/v1/workflows/${workflowId}/start`, data || {});
}

/**
 * 停止工作流
 */
export async function stopWorkflow(
  workflowId: string,
  data?: StopWorkflowRequest
): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/workflows/${workflowId}/stop`, data || {});
}

/**
 * 获取工作流执行状态
 */
export async function getWorkflowStatus(
  workflowId: string,
  executionId?: string
): Promise<ApiResponse<{ executions: WorkflowExecution[] } | WorkflowExecution>> {
  const params = executionId ? `?execution_id=${executionId}` : '';
  return apiClient.get(`/api/v1/workflows/${workflowId}/status${params}`);
}

/**
 * 获取工作流执行历史
 */
export async function getWorkflowExecutions(
  workflowId: string,
  limit = 20
): Promise<ApiResponse<{ executions: WorkflowExecution[] }>> {
  return apiClient.get(`/api/v1/workflows/${workflowId}/executions?limit=${limit}`);
}

/**
 * 获取执行日志
 */
export async function getExecutionLogs(
  executionId: string
): Promise<ApiResponse<{ logs: ExecutionLog[] }>> {
  return apiClient.get(`/api/v1/executions/${executionId}/logs`);
}

/**
 * 列出所有执行记录
 */
export async function listExecutions(params?: {
  workflow_id?: string;
  status?: string;
  limit?: number;
}): Promise<ApiResponse<{ executions: WorkflowExecution[] }>> {
  const queryParams = new URLSearchParams();
  if (params?.workflow_id) queryParams.append('workflow_id', params.workflow_id);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  return apiClient.get(`/api/v1/executions?${queryParams.toString()}`);
}

/**
 * 删除工作流
 */
export async function deleteWorkflow(workflowId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/workflows/${workflowId}`);
}

/**
 * 更新工作流
 */
export async function updateWorkflow(
  workflowId: string,
  data: Partial<CreateWorkflowRequest> & { definition?: string | Record<string, unknown> }
): Promise<ApiResponse<Workflow>> {
  return apiClient.put(`/api/v1/workflows/${workflowId}`, data);
}

/**
 * RAG 查询
 */
export async function ragQuery(data: RagQueryRequest): Promise<ApiResponse<RagQueryResponse>> {
  return apiClient.post('/api/v1/rag/query', data);
}

/**
 * Text-to-SQL
 */
export async function text2Sql(data: Text2SqlRequest): Promise<ApiResponse<Text2SqlResponse>> {
  return apiClient.post('/api/v1/text2sql', data);
}

// ============================================
// Agent 工具 API (Phase 7: Sprint 7.1)
// ============================================

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

export interface AgentRunRequest {
  query: string;
  agent_type?: 'react' | 'function_calling' | 'plan_execute';
  model?: string;
  max_iterations?: number;
}

export interface AgentStep {
  type: 'thought' | 'action' | 'observation' | 'final' | 'plan' | 'error';
  content: string;
  tool_output?: unknown;
  timestamp: string;
}

export interface AgentStreamEvent {
  type: 'start' | 'step' | 'end' | 'error' | 'iteration' | 'status' | 'tool_start' | 'tool_end';
  message?: string;
  agent_type?: string;
  iteration?: number;
  max_iterations?: number;
  tool?: string;
  data?: AgentStep;
  success?: boolean;
  answer?: string;
  error?: string;
  iterations?: number;
}

export interface AgentRunResponse {
  success: boolean;
  answer?: string;
  error?: string;
  iterations?: number;
  steps?: AgentStep[];
}

/**
 * 列出可用工具
 */
export async function listTools(): Promise<ApiResponse<{ tools: Tool[]; total: number }>> {
  return apiClient.get('/api/v1/tools');
}

/**
 * 获取工具 Function Calling schema
 */
export async function getToolSchemas(): Promise<ApiResponse<{ schemas: ToolSchema[]; total: number }>> {
  return apiClient.get('/api/v1/tools/schemas');
}

/**
 * 执行工具
 */
export async function executeTool(
  toolName: string,
  parameters: Record<string, unknown>
): Promise<ApiResponse<unknown>> {
  return apiClient.post(`/api/v1/tools/${toolName}/execute`, parameters);
}

/**
 * 运行 Agent
 */
export async function runAgent(data: AgentRunRequest): Promise<ApiResponse<AgentRunResponse>> {
  return apiClient.post('/api/v1/agent/run', data);
}

/**
 * 运行 Agent (流式 SSE)
 * 实时返回执行步骤
 */
export async function runAgentStream(
  data: AgentRunRequest,
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
  }, 120000); // 120 second timeout for agent operations

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
      // Handle specific HTTP status codes
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
              const event: AgentStreamEvent = JSON.parse(trimmed.slice(6));

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

// ============================================
// Agent 模板管理 API (P1 - Agent 模板管理)
// ============================================

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

/**
 * 列出 Agent 模板
 */
export async function listAgentTemplates(params?: {
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
 * 获取单个 Agent 模板
 */
export async function getAgentTemplate(templateId: string): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.get(`/api/v1/agent/templates/${templateId}`);
}

/**
 * 创建 Agent 模板
 */
export async function createAgentTemplate(
  data: CreateAgentTemplateRequest
): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.post('/api/v1/agent/templates', data);
}

/**
 * 更新 Agent 模板
 */
export async function updateAgentTemplate(
  templateId: string,
  data: Partial<CreateAgentTemplateRequest>
): Promise<ApiResponse<AgentTemplate>> {
  return apiClient.put(`/api/v1/agent/templates/${templateId}`, data);
}

/**
 * 删除 Agent 模板
 */
export async function deleteAgentTemplate(templateId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/agent/templates/${templateId}`);
}

// ============================================
// 工作流调度 API (Phase 7: Sprint 7.4)
// P4: 调度管理增强 - 暂停/恢复、重试、超时、统计
// ============================================

export interface WorkflowSchedule {
  id: number;
  schedule_id: string;
  workflow_id: string;
  schedule_type: 'cron' | 'interval' | 'event';
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  enabled: boolean;
  paused: boolean;  // P4: 暂停状态
  next_run_at?: string;
  last_run_at?: string;
  // P4: 重试配置
  max_retries: number;
  retry_count: number;
  retry_delay_seconds: number;
  retry_backoff_base: number;
  last_retry_at?: string;
  // P4: 超时配置
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
  paused?: boolean;  // P4: 支持创建时设置暂停
  max_retries?: number;  // P4: 最大重试次数
  retry_delay_seconds?: number;  // P4: 重试延迟
  retry_backoff_base?: number;  // P4: 退避基数
  timeout_seconds?: number;  // P4: 超时时间
}

// P4: 调度统计信息
export interface ScheduleStatistics {
  schedule_id: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time_ms: number;
  last_execution_status: string | null;
  last_execution_at: string | null;
  success_rate: number;
  recent_executions: ScheduleExecutionRecord[];
}

// P4: 执行记录
export interface ScheduleExecutionRecord {
  execution_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

// P4: 重试配置
export interface ScheduleRetryConfig {
  max_retries: number;
  retry_delay_seconds: number;
  retry_backoff_base: number;
  timeout_seconds: number;
}

/**
 * 列出工作流的调度配置
 */
export async function listSchedules(workflowId: string): Promise<ApiResponse<{ schedules: WorkflowSchedule[] }>> {
  return apiClient.get(`/api/v1/workflows/${workflowId}/schedules`);
}

/**
 * 创建调度配置
 */
export async function createSchedule(
  workflowId: string,
  data: CreateScheduleRequest
): Promise<ApiResponse<{ schedule_id: string }>> {
  return apiClient.post(`/api/v1/workflows/${workflowId}/schedules`, data);
}

/**
 * 删除调度配置
 */
export async function deleteSchedule(scheduleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/schedules/${scheduleId}`);
}

/**
 * 手动触发调度
 */
export async function triggerSchedule(scheduleId: string): Promise<ApiResponse<{ execution_id: string }>> {
  return apiClient.post(`/api/v1/schedules/${scheduleId}/trigger`);
}

/**
 * 列出所有调度配置
 */
export async function listAllSchedules(params?: {
  workflow_id?: string;
  enabled?: boolean;
}): Promise<ApiResponse<{ schedules: WorkflowSchedule[] }>> {
  const queryParams = new URLSearchParams();
  if (params?.workflow_id) queryParams.append('workflow_id', params.workflow_id);
  if (params?.enabled !== undefined) queryParams.append('enabled', String(params.enabled));
  return apiClient.get(`/api/v1/schedules?${queryParams.toString()}`);
}

// ============================================
// P4: 调度管理增强 API
// ============================================

/**
 * 暂停调度
 */
export async function pauseSchedule(scheduleId: string): Promise<ApiResponse<{ schedule_id: string; paused: boolean }>> {
  return apiClient.post(`/api/v1/schedules/${scheduleId}/pause`);
}

/**
 * 恢复调度
 */
export async function resumeSchedule(scheduleId: string): Promise<ApiResponse<{ schedule_id: string; paused: boolean }>> {
  return apiClient.post(`/api/v1/schedules/${scheduleId}/resume`);
}

/**
 * 获取调度统计信息
 */
export async function getScheduleStatistics(scheduleId: string): Promise<ApiResponse<ScheduleStatistics>> {
  return apiClient.get(`/api/v1/schedules/${scheduleId}/statistics`);
}

/**
 * 更新调度重试配置
 */
export async function updateScheduleRetryConfig(
  scheduleId: string,
  config: Partial<ScheduleRetryConfig>
): Promise<ApiResponse<ScheduleRetryConfig & { schedule_id: string }>> {
  return apiClient.put(`/api/v1/schedules/${scheduleId}/retry-config`, config);
}

// ============================================
// 文档管理 API
// ============================================

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
}

export interface DocumentsResponse {
  documents: IndexedDocument[];
  collections: string[];
  total_collections: number;
}

export interface UploadDocumentRequest {
  file?: File;
  content?: string;
  file_name?: string;
  title?: string;
  collection?: string;
}

/**
 * 获取文档列表
 */
export async function getDocuments(params?: {
  collection?: string;
  limit?: number;
}): Promise<ApiResponse<DocumentsResponse>> {
  const queryParams = new URLSearchParams();
  if (params?.collection) queryParams.append('collection', params.collection);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  const queryString = queryParams.toString();
  return apiClient.get(`/api/v1/documents${queryString ? `?${queryString}` : ''}`);
}

/**
 * 上传文档
 */
export async function uploadDocument(formData: FormData): Promise<ApiResponse<{
  doc_id: string;
  file_name: string;
  chunk_count: number;
  collection: string;
}>> {
  return apiClient.post('/api/v1/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

/**
 * 获取文档详情
 */
export async function getDocument(docId: string): Promise<ApiResponse<IndexedDocument & { collection_info?: unknown }>> {
  return apiClient.get(`/api/v1/documents/${docId}`);
}

/**
 * 删除文档
 */
export async function deleteDocument(docId: string): Promise<ApiResponse<{ doc_id: string; vectors_deleted: boolean }>> {
  return apiClient.delete(`/api/v1/documents/${docId}`);
}

/**
 * 批量删除文档
 */
export async function batchDeleteDocuments(docIds: string[]): Promise<ApiResponse<{
  deleted_count: number;
  failed_count: number;
  failed_ids: string[];
}>> {
  return apiClient.delete('/api/v1/documents/batch', { doc_ids: docIds });
}

export default {
  // Prompt 模板
  getPromptTemplates,
  getPromptTemplate,

  // 聊天
  sendChatMessage,
  streamChatMessage,
  getConversations,
  getConversation,
  createConversation,
  deleteConversation,
  renameConversation,

  // 工作流
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  startWorkflow,
  stopWorkflow,
  deleteWorkflow,
  getWorkflowStatus,
  getWorkflowExecutions,
  getExecutionLogs,
  listExecutions,

  // RAG & Text2SQL
  ragQuery,
  text2Sql,

  // Agent 工具 (Phase 7)
  listTools,
  getToolSchemas,
  executeTool,
  runAgent,
  runAgentStream,

  // Agent 模板管理 (P1)
  listAgentTemplates,
  getAgentTemplate,
  createAgentTemplate,
  updateAgentTemplate,
  deleteAgentTemplate,

  // 工作流调度 (Phase 7)
  listSchedules,
  createSchedule,
  deleteSchedule,
  triggerSchedule,
  listAllSchedules,

  // P4: 调度管理增强
  pauseSchedule,
  resumeSchedule,
  getScheduleStatistics,
  updateScheduleRetryConfig,

  // 文档管理
  getDocuments,
  uploadDocument,
  getDocument,
  deleteDocument,
  batchDeleteDocuments,
};
