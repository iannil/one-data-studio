/**
 * SeaTunnel 集成服务
 * TODO: 实现 SeaTunnel API 集成
 */

import { apiClient } from './api';

export interface SeaTunnelJob {
  id: string;
  name: string;
  status: 'RUNNING' | 'FAILED' | 'SUCCESS' | 'SUBMITTED';
  createTime: number;
  updateTime: number;
}

export interface SeaTunnelPipeline {
  name: string;
  source?: Record<string, unknown>;
  sink?: Record<string, unknown>;
  transform?: Record<string, unknown>;
}

/**
 * 提交 SeaTunnel 作业
 */
export async function submitJob(pipeline: SeaTunnelPipeline) {
  return apiClient.post('/api/v1/seatunnel/jobs', pipeline);
}

/**
 * 获取作业状态
 */
export async function getJobStatus(jobId: string) {
  return apiClient.get<undefined, SeaTunnelJob>(`/api/v1/seatunnel/jobs/${jobId}`);
}

/**
 * 停止作业
 */
export async function stopJob(jobId: string) {
  return apiClient.post(`/api/v1/seatunnel/jobs/${jobId}/stop`, {});
}

/**
 * 获取作业列表
 */
export async function listJobs(page: number = 1, pageSize: number = 10) {
  return apiClient.get('/api/v1/seatunnel/jobs', { params: { page, pageSize } });
}
