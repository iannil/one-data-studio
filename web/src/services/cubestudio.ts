/**
 * CubeStudio 集成服务
 * TODO: 实现 CubeStudio API 集成
 */

import { apiClient } from './api';

export interface CubeStudioProject {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived';
  createTime: string;
  updateTime: string;
}

export interface CubeStudioJob {
  id: string;
  projectId: string;
  name: string;
  type: 'sync' | 'calculation' | 'export';
  schedule?: string;
  status: 'enabled' | 'disabled';
}

export interface CubeStudioTaskInstance {
  id: string;
  jobId: string;
  status: 'waiting' | 'running' | 'success' | 'failed';
  startTime?: string;
  endTime?: string;
  log?: string;
}

/**
 * 获取项目列表
 */
export async function listProjects(page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/cubestudio/projects', { params: { page, pageSize } });
}

/**
 * 获取项目详情
 */
export async function getProject(projectId: string) {
  return apiClient.get<undefined, CubeStudioProject>(`/api/v1/cubestudio/projects/${projectId}`);
}

/**
 * 获取作业列表
 */
export async function listJobs(projectId: string, page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/cubestudio/jobs', { params: { projectId, page, pageSize } });
}

/**
 * 创建作业
 */
export async function createJob(job: Partial<CubeStudioJob>) {
  return apiClient.post('/api/v1/cubestudio/jobs', job);
}

/**
 * 触发作业
 */
export async function triggerJob(jobId: string) {
  return apiClient.post(`/api/v1/cubestudio/jobs/${jobId}/trigger`, {});
}

/**
 * 获取任务实例
 */
export async function getTaskInstance(instanceId: string) {
  return apiClient.get<undefined, CubeStudioTaskInstance>(`/api/v1/cubestudio/instances/${instanceId}`);
}

/**
 * 获取任务日志
 */
export async function getTaskLog(instanceId: string) {
  return apiClient.get<string>(`/api/v1/cubestudio/instances/${instanceId}/log`);
}
