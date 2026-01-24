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
 * 返回一个 ReadableStream，同时提取 token 使用数据
 */
export async function streamChatCompletion(
  data: ChatCompletionRequest,
  onChunk: (chunk: string) => void,
  onComplete: (usage?: ChatCompletionUsage) => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch('/v1/chat/completions', {
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
    let usage: ChatCompletionUsage | undefined;

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
            // Extract usage data from the final chunk (OpenAI format)
            if (json.usage) {
              usage = {
                prompt_tokens: json.usage.prompt_tokens || 0,
                completion_tokens: json.usage.completion_tokens || 0,
                total_tokens: json.usage.total_tokens || 0,
              };
            }
            // Some providers include usage in x_groq or similar
            if (json.x_groq?.usage) {
              usage = {
                prompt_tokens: json.x_groq.usage.prompt_tokens || 0,
                completion_tokens: json.x_groq.usage.completion_tokens || 0,
                total_tokens: json.x_groq.usage.total_tokens || 0,
              };
            }
          } catch {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }
    onComplete(usage);
  } catch (error) {
    onError(error as Error);
  }
}

/**
 * 文本补全
 */
export async function createCompletion(data: TextCompletionRequest): Promise<any> {
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

export default {
  getModels,
  createChatCompletion,
  streamChatCompletion,
  createCompletion,
  createEmbeddings,
  deployModel,
  getModelStatus,
};
