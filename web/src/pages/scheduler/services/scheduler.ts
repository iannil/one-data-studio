/**
 * 调度器 API 服务
 */

import { apiClient } from '@/services/api';

export interface SchedulerStats {
  celery: {
    workers: string[];
    total_tasks: number;
  };
  smart_scheduler: {
    total_tasks: number;
    status_counts: Record<string, number>;
    queue_length: number;
    available_resources: {
      cpu_cores: number;
      memory_mb: number;
      gpu_count: number;
    };
    total_resources: {
      cpu_cores: number;
      memory_mb: number;
      gpu_count: number;
    };
  };
  dolphinscheduler: {
    enabled: boolean;
    url: string;
  };
}

export interface TaskSubmitRequest {
  name: string;
  type: 'celery_task' | 'shell' | 'sql' | 'python' | 'http' | 'workflow';
  description?: string;
  celery_task_name?: string;
  script?: string;
  script_content?: string;
  sql_query?: string;
  http_url?: string;
  http_method?: string;
  http_headers?: Record<string, string>;
  http_body?: string;
  parameters?: Record<string, any>;
  dependencies?: string[];
  priority?: 'low' | 'normal' | 'high' | 'critical';
  engine?: 'auto' | 'celery' | 'dolphinscheduler' | 'smart';
  timeout?: number;
  args?: unknown[];
  kwargs?: Record<string, any>;
}

export interface TaskSubmitResponse {
  task_id: string;
  engine: string;
  status: string;
  started_at: string;
}

export interface TaskInfo {
  engine: string;
  task_id: string;
  status: string;
  name?: string;
  started_at?: string;
  completed_at?: string;
  result?: unknown;
  error?: string;
}

export interface WorkflowTask {
  name: string;
  type: string;
  description?: string;
  script?: string;
  script_content?: string;
  sql_query?: string;
  parameters?: Record<string, any>;
  dependencies?: string[];
  priority?: string;
}

export interface SmartTask {
  task_id: string;
  name: string;
  description: string;
  task_type: string;
  priority: string;
  status: string;
  dependencies: unknown[];
  resource_requirement: {
    cpu_cores: number;
    memory_mb: number;
    gpu_count: number;
  };
  estimated_duration_ms: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  metrics: {
    execution_time_ms: number;
    wait_time_ms: number;
    retry_count: number;
    success_rate: number;
  };
}

export interface ResourcePrediction {
  window_minutes: number;
  predicted_tasks: number;
  resource_demand: {
    cpu_cores: number;
    memory_mb: number;
    gpu_count: number;
  };
  resource_utilization: {
    cpu_percent: number;
    memory_percent: number;
    gpu_percent: number;
  };
  recommendations: string[];
}

export const schedulerApi = {
  /**
   * 获取统计信息
   */
  getStats: () =>
    apiClient.get<{ data: SchedulerStats; code: number; msg: string }>('/api/v1/scheduler/stats'),

  /**
   * 健康检查
   */
  getHealth: () =>
    apiClient.get<{ status: string; components: Record<string, boolean> }>('/api/v1/scheduler/health'),

  /**
   * 提交任务
   */
  submitTask: (data: TaskSubmitRequest) =>
    apiClient.post<{ data: TaskSubmitResponse; code: number; msg: string }>('/api/v1/scheduler/tasks', data),

  /**
   * 获取任务状态
   */
  getTaskStatus: (taskId: string, engine?: string) =>
    apiClient.get<{ data: TaskInfo; code: number; msg: string }>(`/api/v1/scheduler/tasks/${taskId}`, {
      params: { engine },
    }),

  /**
   * 列出任务
   */
  listTasks: (params?: { status?: string; engine?: string; limit?: number }) =>
    apiClient.get<{ data: { tasks: TaskInfo[]; total: number }; code: number; msg: string }>('/api/v1/scheduler/tasks', {
      params,
    }),

  /**
   * 取消任务
   */
  cancelTask: (taskId: string, engine?: string) =>
    apiClient.post<{ data: { cancelled: boolean }; code: number; msg: string }>(`/api/v1/scheduler/tasks/${taskId}/cancel`, null, {
      params: { engine },
    }),

  /**
   * 重试任务
   */
  retryTask: (taskId: string, engine?: string) =>
    apiClient.post<{ data: { new_task_id: string }; code: number; msg: string }>(`/api/v1/scheduler/tasks/${taskId}/retry`, null, {
      params: { engine },
    }),

  /**
   * 创建工作流
   */
  createWorkflow: (data: {
    name: string;
    description?: string;
    tasks: WorkflowTask[];
    engine?: string;
  }) =>
    apiClient.post<{ data: { workflow_id: string }; code: number; msg: string }>('/api/v1/scheduler/workflows', data),

  /**
   * 运行工作流
   */
  runWorkflow: (workflowId: string, params?: Record<string, any>) =>
    apiClient.post<{ data: { instance_id: string }; code: number; msg: string }>(
      `/api/v1/scheduler/workflows/${workflowId}/run`,
      { params }
    ),

  /**
   * 列出智能调度器任务
   */
  listSmartTasks: (params?: {
    status?: string;
    priority?: string;
    type?: string;
    limit?: number;
  }) =>
    apiClient.get<{ data: { tasks: SmartTask[]; total: number }; code: number; msg: string }>('/api/v1/scheduler/smart/tasks', {
      params,
    }),

  /**
   * 优化调度
   */
  optimizeSchedule: () =>
    apiClient.post<{
      data: {
        optimized_order: string[];
        total_tasks: number;
        estimated_completion_time: number;
      };
      code: number;
      msg: string;
    }>('/api/v1/scheduler/smart/optimize'),

  /**
   * 预测资源需求
   */
  predictResourceDemand: (windowMinutes: number = 60) =>
    apiClient.get<{ data: ResourcePrediction; code: number; msg: string }>('/api/v1/scheduler/smart/resource-demand', {
      params: { window_minutes: windowMinutes },
    }),

  /**
   * 列出 DS 项目
   */
  listDSProjects: () =>
    apiClient.get<{ data: unknown[]; code: number; msg: string }>('/api/v1/scheduler/ds/projects'),

  /**
   * 列出 DS 流程实例
   */
  listDSProcessInstances: (params: { projectId: string; page?: number; size?: number }) =>
    apiClient.get<{ data: unknown[]; code: number; msg: string }>('/api/v1/scheduler/ds/process-instances', { params }),

  /**
   * 创建定时任务
   */
  createCronTask: (data: {
    name: string;
    cron_expression: string;
    task: TaskSubmitRequest;
    description?: string;
  }) =>
    apiClient.post<{ data: { cron_id: string }; code: number; msg: string }>('/api/v1/scheduler/cron', data),
};

export default schedulerApi;
