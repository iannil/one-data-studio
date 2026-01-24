import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

// 系统配置类型
export interface SystemSettings {
  // 通用设置
  site_name: string;
  site_description?: string;
  logo_url?: string;
  timezone: string;
  language: string;

  // 邮件设置
  email_enabled: boolean;
  email_smtp_host?: string;
  email_smtp_port?: number;
  email_smtp_user?: string;
  email_from_address?: string;
  email_from_name?: string;

  // 通知设置
  notification_channels: NotificationChannel[];
  notification_rules: NotificationRule[];

  // 存储设置
  storage_type: 'local' | 'minio' | 's3';
  storage_endpoint?: string;
  storage_bucket?: string;
  storage_access_key?: string;
  storage_region?: string;

  // 安全设置
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_number: boolean;
  password_require_special: boolean;
  session_timeout_minutes: number;
  max_login_attempts: number;
  lockout_duration_minutes: number;

  // 功能开关
  features_enabled: {
    alldata: boolean;
    cube: boolean;
    bisheng: boolean;
    workflows: boolean;
  };

  updated_at?: string;
  updated_by?: string;
}

export interface NotificationChannel {
  id: string;
  type: 'email' | 'webhook' | 'dingtalk' | 'feishu' | 'slack' | 'wechat';
  name: string;
  enabled: boolean;
  config: {
    url?: string;
    secret?: string;
    recipients?: string[];
  };
}

export interface NotificationRule {
  id: string;
  name: string;
  enabled: boolean;
  events: string[];
  channel_ids: string[];
}

export interface UpdateSettingsRequest {
  site_name?: string;
  site_description?: string;
  logo_url?: string;
  timezone?: string;
  language?: string;
  email_enabled?: boolean;
  email_smtp_host?: string;
  email_smtp_port?: number;
  email_smtp_user?: string;
  email_from_address?: string;
  email_from_name?: string;
  storage_type?: 'local' | 'minio' | 's3';
  storage_endpoint?: string;
  storage_bucket?: string;
  storage_access_key?: string;
  storage_region?: string;
  password_min_length?: number;
  password_require_uppercase?: boolean;
  password_require_lowercase?: boolean;
  password_require_number?: boolean;
  password_require_special?: boolean;
  session_timeout_minutes?: number;
  max_login_attempts?: number;
  lockout_duration_minutes?: number;
  features_enabled?: {
    alldata?: boolean;
    cube?: boolean;
    bisheng?: boolean;
    workflows?: boolean;
  };
}

// 审计日志类型
export type AuditActionType =
  | 'login'
  | 'logout'
  | 'create'
  | 'update'
  | 'delete'
  | 'execute'
  | 'export'
  | 'import'
  | 'start'
  | 'stop'
  | 'deploy'
  | 'undeploy';

export type AuditResourceType =
  | 'user'
  | 'group'
  | 'role'
  | 'datasource'
  | 'dataset'
  | 'workflow'
  | 'experiment'
  | 'model'
  | 'service'
  | 'prompt'
  | 'knowledge'
  | 'metric'
  | 'settings'
  | 'system';

export interface AuditLog {
  audit_id: string;
  action: AuditActionType;
  resource_type: AuditResourceType;
  resource_id?: string;
  resource_name?: string;
  user_id: string;
  username: string;
  user_ip?: string;
  user_agent?: string;
  success: boolean;
  error_message?: string;
  changes?: {
    before?: Record<string, unknown>;
    after?: Record<string, unknown>;
  };
  created_at: string;
}

export interface AuditLogListParams {
  user_id?: string;
  action?: AuditActionType;
  resource_type?: AuditResourceType;
  resource_id?: string;
  success?: boolean;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogStatistics {
  total_actions: number;
  success_rate: number;
  action_distribution: Record<AuditActionType, number>;
  resource_distribution: Record<AuditResourceType, number>;
  top_users: Array<{ user_id: string; username: string; action_count: number }>;
  daily_stats: Array<{
    date: string;
    total_actions: number;
    success_actions: number;
    failed_actions: number;
  }>;
}

// ============= 系统配置 API =============

/**
 * 获取系统配置
 */
export async function getSystemSettings(): Promise<ApiResponse<SystemSettings>> {
  return apiClient.get('/api/v1/admin/settings');
}

/**
 * 更新系统配置
 */
export async function updateSystemSettings(data: UpdateSettingsRequest): Promise<ApiResponse<SystemSettings>> {
  return apiClient.put('/api/v1/admin/settings', data);
}

/**
 * 重置系统配置为默认值
 */
export async function resetSystemSettings(): Promise<ApiResponse<SystemSettings>> {
  return apiClient.post('/api/v1/admin/settings/reset');
}

/**
 * 发送测试邮件
 */
export async function sendTestEmail(email: string): Promise<ApiResponse<void>> {
  return apiClient.post('/api/v1/admin/settings/test-email', { email });
}

/**
 * 测试存储连接
 */
export async function testStorageConnection(): Promise<ApiResponse<{ success: boolean; message: string }>> {
  return apiClient.post('/api/v1/admin/settings/test-storage');
}

// ============= 通知渠道 API =============

/**
 * 获取通知渠道列表
 */
export async function getNotificationChannels(): Promise<ApiResponse<{ channels: NotificationChannel[] }>> {
  return apiClient.get('/api/v1/admin/settings/notification-channels');
}

/**
 * 创建通知渠道
 */
export async function createNotificationChannel(data: Omit<NotificationChannel, 'id'>): Promise<ApiResponse<{ channel_id: string }>> {
  return apiClient.post('/api/v1/admin/settings/notification-channels', data);
}

/**
 * 更新通知渠道
 */
export async function updateNotificationChannel(channelId: string, data: Partial<NotificationChannel>): Promise<ApiResponse<NotificationChannel>> {
  return apiClient.put(`/api/v1/admin/settings/notification-channels/${channelId}`, data);
}

/**
 * 删除通知渠道
 */
export async function deleteNotificationChannel(channelId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/admin/settings/notification-channels/${channelId}`);
}

/**
 * 测试通知渠道
 */
export async function testNotificationChannel(channelId: string): Promise<ApiResponse<{ success: boolean; message: string }>> {
  return apiClient.post(`/api/v1/admin/settings/notification-channels/${channelId}/test`);
}

// ============= 通知规则 API =============

/**
 * 获取通知规则列表
 */
export async function getNotificationRules(): Promise<ApiResponse<{ rules: NotificationRule[] }>> {
  return apiClient.get('/api/v1/admin/settings/notification-rules');
}

/**
 * 创建通知规则
 */
export async function createNotificationRule(data: Omit<NotificationRule, 'id'>): Promise<ApiResponse<{ rule_id: string }>> {
  return apiClient.post('/api/v1/admin/settings/notification-rules', data);
}

/**
 * 更新通知规则
 */
export async function updateNotificationRule(ruleId: string, data: Partial<NotificationRule>): Promise<ApiResponse<NotificationRule>> {
  return apiClient.put(`/api/v1/admin/settings/notification-rules/${ruleId}`, data);
}

/**
 * 删除通知规则
 */
export async function deleteNotificationRule(ruleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/admin/settings/notification-rules/${ruleId}`);
}

// ============= 审计日志 API =============

/**
 * 获取审计日志列表
 */
export async function getAuditLogs(params?: AuditLogListParams): Promise<ApiResponse<AuditLogListResponse>> {
  return apiClient.get('/api/v1/admin/audit-logs', { params });
}

/**
 * 获取审计日志详情
 */
export async function getAuditLog(auditId: string): Promise<ApiResponse<AuditLog>> {
  return apiClient.get(`/api/v1/admin/audit-logs/${auditId}`);
}

/**
 * 导出审计日志
 */
export async function exportAuditLogs(params: {
  start_time: string;
  end_time: string;
  format: 'csv' | 'json' | 'excel';
}): Promise<ApiResponse<{ download_url: string; export_id: string }>> {
  return apiClient.post('/api/v1/admin/audit-logs/export', params);
}

/**
 * 获取审计日志统计
 */
export async function getAuditLogStatistics(params?: {
  start_time?: string;
  end_time?: string;
}): Promise<ApiResponse<AuditLogStatistics>> {
  return apiClient.get('/api/v1/admin/audit-logs/statistics', { params });
}

/**
 * 获取操作类型列表
 */
export async function getAuditActionTypes(): Promise<ApiResponse<{ types: AuditActionType[] }>> {
  return apiClient.get('/api/v1/admin/audit-logs/action-types');
}

/**
 * 获取资源类型列表
 */
export async function getAuditResourceTypes(): Promise<ApiResponse<{ types: AuditResourceType[] }>> {
  return apiClient.get('/api/v1/admin/audit-logs/resource-types');
}

/**
 * 获取活跃用户列表（用于筛选）
 */
export async function getActiveUsers(params?: {
  start_time?: string;
  end_time?: string;
}): Promise<ApiResponse<{ users: Array<{ user_id: string; username: string; action_count: number }> }>> {
  return apiClient.get('/api/v1/admin/audit-logs/active-users', { params });
}

/**
 * 设置审计日志保留策略
 */
export async function setAuditLogRetention(data: {
  retention_days: number;
}): Promise<ApiResponse<void>> {
  return apiClient.put('/api/v1/admin/audit-logs/retention', data);
}

/**
 * 获取审计日志保留策略
 */
export async function getAuditLogRetention(): Promise<ApiResponse<{ retention_days: number }> {
  return apiClient.get('/api/v1/admin/audit-logs/retention');
}

export default {
  // 系统配置
  getSystemSettings,
  updateSystemSettings,
  resetSystemSettings,
  sendTestEmail,
  testStorageConnection,

  // 通知渠道
  getNotificationChannels,
  createNotificationChannel,
  updateNotificationChannel,
  deleteNotificationChannel,
  testNotificationChannel,

  // 通知规则
  getNotificationRules,
  createNotificationRule,
  updateNotificationRule,
  deleteNotificationRule,

  // 审计日志
  getAuditLogs,
  getAuditLog,
  exportAuditLogs,
  getAuditLogStatistics,
  getAuditActionTypes,
  getAuditResourceTypes,
  getActiveUsers,
  setAuditLogRetention,
  getAuditLogRetention,
};
