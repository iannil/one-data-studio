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
  try {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

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
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
    onComplete();
  } catch (error) {
    onError(error as Error);
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
    default?: any;
  }>;
}

export interface ToolSchema {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters: {
      type: 'object';
      properties: Record<string, any>;
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
  type: 'thought' | 'action' | 'observation' | 'final';
  content: string;
  tool_output?: any;
  timestamp: string;
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
  parameters: Record<string, any>
): Promise<ApiResponse<any>> {
  return apiClient.post(`/api/v1/tools/${toolName}/execute`, parameters);
}

/**
 * 运行 Agent
 */
export async function runAgent(data: AgentRunRequest): Promise<ApiResponse<AgentRunResponse>> {
  return apiClient.post('/api/v1/agent/run', data);
}

// ============================================
// 工作流调度 API (Phase 7: Sprint 7.4)
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
  next_run_at?: string;
  last_run_at?: string;
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

  // 工作流
  getWorkflows,
  getWorkflow,
  createWorkflow,
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

  // 工作流调度 (Phase 7)
  listSchedules,
  createSchedule,
  deleteSchedule,
  triggerSchedule,
  listAllSchedules,
};
