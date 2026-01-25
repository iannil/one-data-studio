import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

// 人机循环 (Human-in-the-Loop) 类型
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
    form_schema?: Array<{
      name: string;
      type: 'text' | 'textarea' | 'number' | 'select' | 'multiselect' | 'boolean' | 'date';
      label: string;
      required?: boolean;
      options?: Array<{ label: string; value: string }>;
      default?: unknown;
    }>;
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

export interface CreateHumanTaskRequest {
  task_type: 'approval' | 'review' | 'input' | 'confirmation';
  title: string;
  description?: string;
  assignee?: string;
  assignees?: string[];
  data?: {
    input_data?: Record<string, unknown>;
    form_schema?: NonNullable<HumanTask['data']>['form_schema'];
    context?: Record<string, unknown>;
    timeout_minutes?: number;
  };
}

export interface SubmitHumanTaskRequest {
  approved: boolean;
  action?: 'approve' | 'reject';
  comment?: string;
  input_data?: Record<string, unknown>;
}

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

export interface TestPromptTemplateRequest {
  content: string;
  variables: Record<string, string>;
  model?: string;
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
  message_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
  timestamp?: string;
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
  definition?: {
    nodes: unknown[];
    edges: unknown[];
  };
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  type: 'rag' | 'text2sql' | 'custom';
  config?: Record<string, unknown>;
  definition?: {
    nodes: unknown[];
    edges: unknown[];
  };
}

// 工作流执行相关类型 (Phase 6)
export interface WorkflowExecution {
  id: string;
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
export async function getPromptTemplates(params?: {
  category?: string;
  tags?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ templates: PromptTemplate[]; total: number }>> {
  return apiClient.get('/api/v1/templates', { params });
}

/**
 * 获取单个 Prompt 模板
 */
export async function getPromptTemplate(templateId: string): Promise<ApiResponse<PromptTemplate>> {
  return apiClient.get(`/api/v1/templates/${templateId}`);
}

/**
 * 创建 Prompt 模板
 */
export async function createPromptTemplate(
  data: CreatePromptTemplateRequest
): Promise<ApiResponse<{ template_id: string }>> {
  return apiClient.post('/api/v1/templates', data);
}

/**
 * 更新 Prompt 模板
 */
export async function updatePromptTemplate(
  templateId: string,
  data: UpdatePromptTemplateRequest
): Promise<ApiResponse<PromptTemplate>> {
  return apiClient.put(`/api/v1/templates/${templateId}`, data);
}

/**
 * 删除 Prompt 模板
 */
export async function deletePromptTemplate(templateId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/templates/${templateId}`);
}

/**
 * 测试 Prompt 模板
 */
export async function testPromptTemplate(
  data: TestPromptTemplateRequest
): Promise<ApiResponse<{ result: string; usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number } }>> {
  return apiClient.post('/api/v1/templates/test', data);
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
      // eslint-disable-next-line no-constant-condition
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
  return apiClient.delete('/api/v1/documents/batch', { data: { doc_ids: docIds } });
}

// ============================================
// 知识库管理 API (Phase 3: LLMOps 增强功能)
// ============================================

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

export interface ChunkingConfig {
  chunk_size: number;
  chunk_overlap: number;
  separator?: string;
  keep_separator?: boolean;
}

export interface RetrievalTestRequest {
  query: string;
  top_k?: number;
  score_threshold?: number;
  search_type?: 'vector' | 'hybrid' | 'keyword';
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

/**
 * 获取知识库列表
 */
export async function getKnowledgeBases(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ knowledge_bases: KnowledgeBase[]; total: number }>> {
  return apiClient.get('/api/v1/knowledge-bases', { params });
}

/**
 * 获取知识库详情
 */
export async function getKnowledgeBase(kbId: string): Promise<ApiResponse<KnowledgeBase & { documents?: KnowledgeDocument[] }>> {
  return apiClient.get(`/api/v1/knowledge-bases/${kbId}`);
}

/**
 * 创建知识库
 */
export async function createKnowledgeBase(
  data: CreateKnowledgeBaseRequest
): Promise<ApiResponse<{ kb_id: string }>> {
  return apiClient.post('/api/v1/knowledge-bases', data);
}

/**
 * 更新知识库
 */
export async function updateKnowledgeBase(
  kbId: string,
  data: UpdateKnowledgeBaseRequest
): Promise<ApiResponse<KnowledgeBase>> {
  return apiClient.put(`/api/v1/knowledge-bases/${kbId}`, data);
}

/**
 * 删除知识库
 */
export async function deleteKnowledgeBase(kbId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/knowledge-bases/${kbId}`);
}

/**
 * 获取知识库文档列表
 */
export async function getKnowledgeDocuments(kbId: string): Promise<ApiResponse<{ documents: KnowledgeDocument[] }>> {
  return apiClient.get(`/api/v1/knowledge-bases/${kbId}/documents`);
}

/**
 * 上传文档到知识库
 */
export async function uploadToKnowledgeBase(
  kbId: string,
  formData: FormData
): Promise<ApiResponse<{ doc_id: string; file_name: string; chunk_count: number }>> {
  return apiClient.post(`/api/v1/knowledge-bases/${kbId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 从知识库删除文档
 */
export async function deleteKnowledgeDocument(kbId: string, docId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/knowledge-bases/${kbId}/documents/${docId}`);
}

/**
 * 测试知识库检索
 */
export async function testRetrieval(
  kbId: string,
  data: RetrievalTestRequest
): Promise<ApiResponse<RetrievalTestResult>> {
  return apiClient.post(`/api/v1/knowledge-bases/${kbId}/test`, data);
}

/**
 * 重建知识库索引
 */
export async function rebuildKnowledgeIndex(kbId: string): Promise<ApiResponse<{ status: string }>> {
  return apiClient.post(`/api/v1/knowledge-bases/${kbId}/rebuild`);
}

// ============================================
// 应用发布管理 API (Phase 3: LLMOps 增强功能)
// ============================================

export type AppStatus = 'draft' | 'published' | 'archived';

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

export interface PublishAppRequest {
  version?: string;
  changelog?: string;
}

export interface ApiKey {
  key_id: string;
  key_display: string;
  created_at: string;
  last_used?: string;
  access_count: number;
  is_active: boolean;
}

export interface AppAccessLog {
  log_id: string;
  app_id: string;
  api_key: string;
  endpoint: string;
  status: number;
  latency_ms: number;
  timestamp: string;
}

export interface AppStatistics {
  app_id: string;
  total_access: number;
  unique_users: number;
  avg_latency_ms: number;
  error_rate: number;
  access_by_date: Array<{
    date: string;
    count: number;
  }>;
  top_endpoints: Array<{
    endpoint: string;
    count: number;
  }>;
}

/**
 * 获取已发布应用列表
 */
export async function getPublishedApps(params?: {
  type?: string;
  status?: AppStatus;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ apps: PublishedApp[]; total: number }>> {
  return apiClient.get('/api/v1/apps', { params });
}

/**
 * 获取应用详情
 */
export async function getPublishedApp(appId: string): Promise<ApiResponse<PublishedApp & { config?: Record<string, unknown> }>> {
  return apiClient.get(`/api/v1/apps/${appId}`);
}

/**
 * 创建应用
 */
export async function createApp(
  data: CreateAppRequest
): Promise<ApiResponse<{ app_id: string }>> {
  return apiClient.post('/api/v1/apps', data);
}

/**
 * 更新应用
 */
export async function updateApp(
  appId: string,
  data: UpdateAppRequest
): Promise<ApiResponse<PublishedApp>> {
  return apiClient.put(`/api/v1/apps/${appId}`, data);
}

/**
 * 发布应用
 */
export async function publishApp(
  appId: string,
  data: PublishAppRequest
): Promise<ApiResponse<{ app_id: string; version: string; endpoint: string }>> {
  return apiClient.post(`/api/v1/apps/${appId}/publish`, data);
}

/**
 * 下线应用
 */
export async function unpublishApp(appId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/apps/${appId}/unpublish`);
}

/**
 * 删除应用
 */
export async function deleteApp(appId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/apps/${appId}`);
}

/**
 * 获取应用 API 密钥列表
 */
export async function getAppApiKeys(appId: string): Promise<ApiResponse<{ api_keys: ApiKey[] }>> {
  return apiClient.get(`/api/v1/apps/${appId}/api-keys`);
}

/**
 * 创建 API 密钥
 */
export async function createApiKey(appId: string): Promise<ApiResponse<{ key_id: string; key: string }>> {
  return apiClient.post(`/api/v1/apps/${appId}/api-keys`);
}

/**
 * 删除 API 密钥
 */
export async function deleteApiKey(appId: string, keyId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/apps/${appId}/api-keys/${keyId}`);
}

/**
 * 获取应用访问统计
 */
export async function getAppStatistics(
  appId: string,
  params?: { period_start?: string; period_end?: string }
): Promise<ApiResponse<AppStatistics>> {
  return apiClient.get(`/api/v1/apps/${appId}/statistics`, { params });
}

/**
 * 获取应用访问日志
 */
export async function getAppAccessLogs(
  appId: string,
  params?: { limit?: number; offset?: number }
): Promise<ApiResponse<{ logs: AppAccessLog[]; total: number }>> {
  return apiClient.get(`/api/v1/apps/${appId}/logs`, { params });
}

// ============= 模型评估类型 =============

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

export interface EvaluationResult {
  result_id: string;
  task_id: string;
  task_name: string;
  model_name: string;
  status: 'completed' | 'failed';
  metrics: Record<string, number>;
  samples_evaluated: number;
  avg_response_time_ms?: number;
  error?: string;
  evaluated_at: string;
}

export interface EvaluationDataset {
  dataset_id: string;
  name: string;
  description?: string;
  type: 'qa' | 'rag' | 'summarization' | 'classification' | 'generation';
  sample_count: number;
  created_by: string;
  created_at: string;
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

export interface SFTModelExport {
  export_id: string;
  task_id: string;
  format: 'pytorch' | 'safetensors' | 'gguf';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  output_path?: string;
  download_url?: string;
  created_at: string;
}

// ============= 模型评估 API =============

/**
 * 获取评估任务列表
 */
export async function getEvaluationTasks(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: EvaluationTask[]; total: number }>> {
  return apiClient.get('/api/v1/evaluation/tasks', { params });
}

/**
 * 获取评估任务详情
 */
export async function getEvaluationTask(taskId: string): Promise<ApiResponse<EvaluationTask>> {
  return apiClient.get(`/api/v1/evaluation/tasks/${taskId}`);
}

/**
 * 创建评估任务
 */
export async function createEvaluationTask(data: CreateEvaluationTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/evaluation/tasks', data);
}

/**
 * 启动评估任务
 */
export async function startEvaluationTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/evaluation/tasks/${taskId}/start`);
}

/**
 * 停止评估任务
 */
export async function stopEvaluationTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/evaluation/tasks/${taskId}/stop`);
}

/**
 * 删除评估任务
 */
export async function deleteEvaluationTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/evaluation/tasks/${taskId}`);
}

/**
 * 获取评估结果
 */
export async function getEvaluationResults(taskId: string): Promise<ApiResponse<{ results: EvaluationResult[] }>> {
  return apiClient.get(`/api/v1/evaluation/tasks/${taskId}/results`);
}

/**
 * 获取评估数据集列表
 */
export async function getEvaluationDatasets(params?: {
  type?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ datasets: EvaluationDataset[]; total: number }>> {
  return apiClient.get('/api/v1/evaluation/datasets', { params });
}

/**
 * 上传评估数据集
 */
export async function uploadEvaluationDataset(formData: FormData): Promise<ApiResponse<{ dataset_id: string }>> {
  return apiClient.post('/api/v1/evaluation/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 获取对比报告
 */
export async function getComparisonReport(taskId: string): Promise<ApiResponse<ComparisonReport>> {
  return apiClient.get(`/api/v1/evaluation/tasks/${taskId}/comparison`);
}

// ============= SFT 微调 API =============

/**
 * 获取 SFT 任务列表
 */
export async function getSFTTasks(params?: {
  status?: string;
  base_model?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: SFTTask[]; total: number }>> {
  return apiClient.get('/api/v1/sft/tasks', { params });
}

/**
 * 获取 SFT 任务详情
 */
export async function getSFTTask(taskId: string): Promise<ApiResponse<SFTTask>> {
  return apiClient.get(`/api/v1/sft/tasks/${taskId}`);
}

/**
 * 创建 SFT 任务
 */
export async function createSFTTask(data: CreateSFTTaskRequest): Promise<ApiResponse<{ task_id: string }>> {
  return apiClient.post('/api/v1/sft/tasks', data);
}

/**
 * 启动 SFT 任务
 */
export async function startSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/sft/tasks/${taskId}/start`);
}

/**
 * 停止 SFT 任务
 */
export async function stopSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/sft/tasks/${taskId}/stop`);
}

/**
 * 删除 SFT 任务
 */
export async function deleteSFTTask(taskId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/sft/tasks/${taskId}`);
}

/**
 * 获取 SFT 指标
 */
export async function getSFTMetrics(taskId: string): Promise<ApiResponse<{ metrics: SFTTask['metrics'] }>> {
  return apiClient.get(`/api/v1/sft/tasks/${taskId}/metrics`);
}

/**
 * 获取 SFT 数据集列表
 */
export async function getSFTDatasets(params?: {
  format?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ datasets: SFTDataset[]; total: number }>> {
  return apiClient.get('/api/v1/sft/datasets', { params });
}

/**
 * 上传 SFT 数据集
 */
export async function uploadSFTDataset(formData: FormData): Promise<ApiResponse<{ dataset_id: string }>> {
  return apiClient.post('/api/v1/sft/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * 导出 SFT 模型
 */
export async function exportSFTModel(taskId: string, format: 'pytorch' | 'safetensors' | 'gguf'): Promise<ApiResponse<{ export_id: string }>> {
  return apiClient.post(`/api/v1/sft/tasks/${taskId}/export`, { format });
}

/**
 * 获取导出状态
 */
export async function getSFTExportStatus(exportId: string): Promise<ApiResponse<SFTModelExport>> {
  return apiClient.get(`/api/v1/sft/exports/${exportId}`);
}

/**
 * 获取可用的基础模型列表
 */
export async function getBaseModels(): Promise<ApiResponse<{ models: Array<{ name: string; type: string; size: string }> }>> {
  return apiClient.get('/api/v1/sft/base-models');
}

/**
 * 验证 SFT 数据集格式
 */
export async function validateSFTDataset(formData: FormData): Promise<ApiResponse<{ valid: boolean; errors?: string[]; sample_count?: number }>> {
  return apiClient.post('/api/v1/sft/datasets/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

// ============================================
// 人机循环 (Human-in-the-Loop) API
// ============================================

/**
 * 获取待处理的人工任务列表
 */
export async function getPendingHumanTasks(params?: {
  execution_id?: string;
  status?: string;
  assignee?: string;
}): Promise<ApiResponse<{ tasks: HumanTask[] }>> {
  return apiClient.get('/api/v1/human-tasks', { params });
}

/**
 * 获取人工任务详情
 */
export async function getHumanTask(taskId: string): Promise<ApiResponse<HumanTask>> {
  return apiClient.get(`/api/v1/human-tasks/${taskId}`);
}

/**
 * 提交人工任务结果
 */
export async function submitHumanTask(
  taskId: string,
  data: SubmitHumanTaskRequest
): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return apiClient.post(`/api/v1/human-tasks/${taskId}/submit`, data);
}

/**
 * 批量审批人工任务
 */
export async function bulkApproveHumanTasks(taskIds: string[], comment?: string): Promise<ApiResponse<{ approved_count: number }>> {
  return apiClient.post('/api/v1/human-tasks/bulk-approve', { task_ids: taskIds, comment });
}

/**
 * 获取当前用户的待办任务
 */
export async function getMyTasks(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ tasks: HumanTask[]; total: number }>> {
  return apiClient.get('/api/v1/human-tasks/my-tasks', { params });
}

/**
 * 获取我的任务统计
 */
export async function getMyTaskStatistics(): Promise<ApiResponse<{
  pending: number;
  pending_count?: number;
  approved: number;
  approved_count?: number;
  rejected: number;
  rejected_count?: number;
  timeout: number;
  total: number;
  avg_processing_time_minutes?: number;
}>> {
  return apiClient.get('/api/v1/human-tasks/my-tasks/statistics');
}

export default {
  // Prompt 模板
  getPromptTemplates,
  getPromptTemplate,
  createPromptTemplate,
  updatePromptTemplate,
  deletePromptTemplate,
  testPromptTemplate,

  // 聊天
  sendChatMessage,
  streamChatMessage,
  getConversations,
  getConversation,
  createConversation,
  deleteConversation,
  renameConversation,
  saveMessage,
  getConversationUsage,

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

  // Agent 工具
  listTools,
  getToolSchemas,
  executeTool,
  runAgent,
  runAgentStream,

  // Agent 模板管理
  listAgentTemplates,
  getAgentTemplate,
  createAgentTemplate,
  updateAgentTemplate,
  deleteAgentTemplate,

  // 工作流调度
  listSchedules,
  createSchedule,
  deleteSchedule,
  triggerSchedule,
  listAllSchedules,
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

  // 知识库管理
  getKnowledgeBases,
  getKnowledgeBase,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeDocuments,
  uploadToKnowledgeBase,
  deleteKnowledgeDocument,
  testRetrieval,
  rebuildKnowledgeIndex,

  // 应用发布管理
  getPublishedApps,
  getPublishedApp,
  createApp,
  updateApp,
  publishApp,
  unpublishApp,
  deleteApp,
  getAppApiKeys,
  createApiKey,
  deleteApiKey,
  getAppStatistics,
  getAppAccessLogs,

  // 模型评估
  getEvaluationTasks,
  getEvaluationTask,
  createEvaluationTask,
  startEvaluationTask,
  stopEvaluationTask,
  deleteEvaluationTask,
  getEvaluationResults,
  getEvaluationDatasets,
  uploadEvaluationDataset,
  getComparisonReport,

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
  getSFTExportStatus,
  getBaseModels,
  validateSFTDataset,

  // 人机循环
  getPendingHumanTasks,
  getHumanTask,
  submitHumanTask,
  bulkApproveHumanTasks,
  getMyTasks,
  getMyTaskStatistics,
};
