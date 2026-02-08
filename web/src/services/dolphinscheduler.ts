/**
 * DolphinScheduler 集成服务
 * TODO: 实现 DolphinScheduler API 集成
 */

import { apiClient } from './api';

export interface DolphinTask {
  id: number;
  name: string;
  description?: string;
  taskType: string;
  taskParams?: Record<string, unknown>;
}

export interface DolphinProcess {
  id: number;
  name: string;
  description?: string;
  processDefinition: DolphinTask[];
  releaseState: 'ONLINE' | 'OFFLINE';
}

export interface DolphinInstance {
  id: number;
  processInstanceId: number;
  state: 'SUCCESS' | 'RUNNING_EXECUTION' | 'FAILURE' | 'STOP';
  startTime: string;
  endTime?: string;
}

/**
 * 获取工作流列表
 */
export async function listWorkflows(page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/dolphinscheduler/workflows', { params: { page, pageSize } });
}

/**
 * 获取工作流详情
 */
export async function getWorkflow(id: number) {
  return apiClient.get<undefined, DolphinProcess>(`/api/v1/dolphinscheduler/workflows/${id}`);
}

/**
 * 创建工作流
 */
export async function createWorkflow(workflow: Partial<DolphinProcess>) {
  return apiClient.post('/api/v1/dolphinscheduler/workflows', workflow);
}

/**
 * 运行工作流
 */
export async function runWorkflow(id: number) {
  return apiClient.post(`/api/v1/dolphinscheduler/workflows/${id}/run`, {});
}

/**
 * 获取实例列表
 */
export async function listInstances(workflowId?: number, page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/dolphinscheduler/instances', { params: { workflowId, page, pageSize } });
}

/**
 * 获取实例状态
 */
export async function getInstanceStatus(instanceId: number) {
  return apiClient.get<undefined, DolphinInstance>(`/api/v1/dolphinscheduler/instances/${instanceId}`);
}
