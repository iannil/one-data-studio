// ============= 通用类型 =============

export type Nullable<T> = T | null;

export type Optional<T> = T | undefined;

export type WithId<T = unknown> = T & {
  id: string;
};

export type WithTimestamp<T = unknown> = T & {
  created_at: string;
  updated_at?: string;
};

// ============= API 响应类型 =============

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
  timestamp?: string;
}

export interface ApiError {
  code: number;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
  timestamp?: string;
}

// ============= 分页类型 =============

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============= 路由类型 =============

export interface RouteItem {
  key: string;
  path: string;
  label: string;
  icon?: React.ReactNode;
  children?: RouteItem[];
}

// ============= 表单类型 =============

export interface FormFieldOption {
  label: string;
  value: string | number;
  disabled?: boolean;
}

export interface FormFieldGroupOption {
  label: string;
  options: FormFieldOption[];
}

// ============= 状态类型 =============

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// ============= 用户/权限类型 =============

export interface User {
  user_id: string;
  username: string;
  email?: string;
  full_name?: string;
  avatar_url?: string;
  roles: string[];
  created_at: string;
}

export interface Permission {
  resource: string;
  action: string;
  allowed: boolean;
}

// ============= 文件上传类型 =============

export interface UploadFile {
  uid: string;
  name: string;
  status?: 'uploading' | 'done' | 'error';
  url?: string;
  response?: unknown;
  percent?: number;
}

export interface UploadProgressEvent {
  percent: number;
}

// ============= 模型类型 =============

export type ModelProvider = 'openai' | 'anthropic' | 'model_api' | 'custom';

export interface ModelInfo {
  id: string;
  name: string;
  provider: ModelProvider;
  context_length: number;
  supports_streaming: boolean;
  supports_function_calling: boolean;
}

// ============= 聊天类型 =============

export type MessageRole = 'system' | 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface Conversation {
  conversation_id: string;
  title: string;
  model: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatParams {
  model: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  stream?: boolean;
}

// ============= 工作流类型 =============

export type WorkflowType = 'rag' | 'text2sql' | 'custom';
export type WorkflowStatus = 'running' | 'stopped' | 'error' | 'pending';

export interface Workflow {
  workflow_id: string;
  name: string;
  description?: string;
  type: WorkflowType;
  status: WorkflowStatus;
  created_at: string;
  updated_at: string;
}

export interface WorkflowExecution {
  execution_id: string;
  workflow_id: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  result?: unknown;
  error?: string;
}

// ============= 元数据类型 =============

export interface Database {
  name: string;
  description?: string;
  owner?: string;
  table_count?: number;
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
}

// ============= 数据集类型 =============

export type DatasetFormat = 'csv' | 'json' | 'parquet' | 'excel' | 'txt';
export type DatasetStatus = 'active' | 'archived' | 'processing';

export interface Dataset {
  dataset_id: string;
  name: string;
  description?: string;
  storage_type: string;
  storage_path: string;
  format: DatasetFormat;
  schema?: {
    columns: Array<{
      name: string;
      type: string;
      description?: string;
    }>;
  };
  tags?: string[];
  status: DatasetStatus;
  created_at: string;
  updated_at?: string;
}

// ============= RAG 类型 =============

export interface RagDocument {
  document_id: string;
  title: string;
  content: string;
  source: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface RagQueryResult {
  content: string;
  source: string;
  score: number;
  metadata?: Record<string, unknown>;
}

// ============= Text2SQL 类型 =============

export interface Text2SqlResult {
  sql: string;
  confidence: number;
  tables_used: string[];
  explanation?: string;
}

// ============= 统计类型 =============

export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  average_response_time: number;
  error_rate: number;
}

export interface DashboardStats {
  dataset_count: number;
  model_count: number;
  workflow_count: number;
  conversation_count: number;
}
