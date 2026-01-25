import { apiClient, ApiResponse } from './api';

// ============= 类型定义 =============

// 用户类型
export interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  phone?: string;
  avatar_url?: string;
  status: 'active' | 'inactive' | 'locked';
  roles: Role[];
  groups: UserGroup[];
  last_login?: string;
  created_at: string;
  updated_at?: string;
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  status?: string;
  role_id?: string;
  search?: string;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  display_name: string;
  phone?: string;
  role_ids?: string[];
  group_ids?: string[];
}

export interface UpdateUserRequest {
  email?: string;
  display_name?: string;
  phone?: string;
  status?: 'active' | 'inactive';
  role_ids?: string[];
  group_ids?: string[];
}

// 角色类型
export interface Role {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  permissions: Permission[];
  user_count: number;
  is_system: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Permission {
  id: string;
  name: string;
  display_name: string;
  resource: string;
  action: string;
  description?: string;
}

export interface RoleListResponse {
  roles: Role[];
  total: number;
}

export interface CreateRoleRequest {
  name: string;
  display_name: string;
  description?: string;
  permission_ids: string[];
}

export interface UpdateRoleRequest {
  display_name?: string;
  description?: string;
  permission_ids?: string[];
}

// 用户组类型
export interface UserGroup {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  group_type: 'department' | 'team' | 'project' | 'custom';
  is_active: boolean;
  member_count: number;
  members?: GroupMember[];
  created_at: string;
  updated_at?: string;
}

export interface GroupMember {
  id: string;
  username: string;
  display_name: string;
}

export interface GroupListParams {
  page?: number;
  page_size?: number;
  type?: string;
  search?: string;
}

export interface GroupListResponse {
  groups: UserGroup[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateGroupRequest {
  name: string;
  display_name: string;
  description?: string;
  group_type?: 'department' | 'team' | 'project' | 'custom';
}

export interface UpdateGroupRequest {
  display_name?: string;
  description?: string;
  group_type?: 'department' | 'team' | 'project' | 'custom';
  is_active?: boolean;
}

// 统计概览类型
export interface StatsOverview {
  users: { total: number; active: number };
  datasets: { total: number; recent: number };
  models: { total: number; deployed: number };
  workflows: { total: number; running: number };
  experiments: { total: number; completed: number };
  api_calls: { today: number; total: number };
  storage: { used_gb: number; total_gb: number };
  compute: { gpu_hours_today: number; cpu_hours_today: number };
}

// 成本报告类型
export interface CostSummary {
  total_cost: number;
  compute_cost: number;
  storage_cost: number;
  network_cost: number;
  period: string;
  currency: string;
  trend: number;
}

export interface CostUsageItem {
  resource_type: string;
  resource_name: string;
  usage: number;
  unit: string;
  cost: number;
  percentage: number;
}

export interface CostTrendItem {
  date: string;
  compute: number;
  storage: number;
  network: number;
  total: number;
}

// 模型成本类型
export interface ModelCost {
  model: string;
  calls: number;
  tokens: number;
  cost: number;
  avg_cost: number;
}

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
export async function getAuditLogRetention(): Promise<ApiResponse<{ retention_days: number }>> {
  return apiClient.get('/api/v1/admin/audit-logs/retention');
}

// ============= 用户管理 API =============

/**
 * 获取用户列表
 */
export async function getUsers(params?: UserListParams): Promise<ApiResponse<UserListResponse>> {
  return apiClient.get('/api/v1/users', { params });
}

/**
 * 获取用户详情
 */
export async function getUser(userId: string): Promise<ApiResponse<User>> {
  return apiClient.get(`/api/v1/users/${userId}`);
}

/**
 * 创建用户
 */
export async function createUser(data: CreateUserRequest): Promise<ApiResponse<{ user_id: string }>> {
  return apiClient.post('/api/v1/users', data);
}

/**
 * 更新用户
 */
export async function updateUser(userId: string, data: UpdateUserRequest): Promise<ApiResponse<User>> {
  return apiClient.put(`/api/v1/users/${userId}`, data);
}

/**
 * 删除用户
 */
export async function deleteUser(userId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/users/${userId}`);
}

/**
 * 重置用户密码
 */
export async function resetUserPassword(userId: string, newPassword?: string): Promise<ApiResponse<{ temp_password?: string }>> {
  return apiClient.post(`/api/v1/users/${userId}/reset-password`, { new_password: newPassword });
}

/**
 * 切换用户状态（启用/禁用）
 */
export async function toggleUserStatus(userId: string): Promise<ApiResponse<{ status: string }>> {
  return apiClient.post(`/api/v1/users/${userId}/toggle-status`);
}

// ============= 角色管理 API =============

/**
 * 获取角色列表
 */
export async function getRoles(): Promise<ApiResponse<RoleListResponse>> {
  return apiClient.get('/api/v1/roles');
}

/**
 * 获取角色详情
 */
export async function getRole(roleId: string): Promise<ApiResponse<Role>> {
  return apiClient.get(`/api/v1/roles/${roleId}`);
}

/**
 * 创建角色
 */
export async function createRole(data: CreateRoleRequest): Promise<ApiResponse<{ role_id: string }>> {
  return apiClient.post('/api/v1/roles', data);
}

/**
 * 更新角色
 */
export async function updateRole(roleId: string, data: UpdateRoleRequest): Promise<ApiResponse<Role>> {
  return apiClient.put(`/api/v1/roles/${roleId}`, data);
}

/**
 * 删除角色
 */
export async function deleteRole(roleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/roles/${roleId}`);
}

/**
 * 获取权限列表
 */
export async function getPermissions(): Promise<ApiResponse<{ permissions: Permission[] }>> {
  return apiClient.get('/api/v1/permissions');
}

// ============= 用户组管理 API =============

/**
 * 获取用户组列表
 */
export async function getGroups(params?: GroupListParams): Promise<ApiResponse<GroupListResponse>> {
  return apiClient.get('/api/v1/groups', { params });
}

/**
 * 获取用户组详情
 */
export async function getGroup(groupId: string, includeMembers?: boolean): Promise<ApiResponse<UserGroup>> {
  return apiClient.get(`/api/v1/groups/${groupId}`, { params: { include_members: includeMembers } });
}

/**
 * 创建用户组
 */
export async function createGroup(data: CreateGroupRequest): Promise<ApiResponse<{ group_id: string }>> {
  return apiClient.post('/api/v1/groups', data);
}

/**
 * 更新用户组
 */
export async function updateGroup(groupId: string, data: UpdateGroupRequest): Promise<ApiResponse<UserGroup>> {
  return apiClient.put(`/api/v1/groups/${groupId}`, data);
}

/**
 * 删除用户组
 */
export async function deleteGroup(groupId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/groups/${groupId}`);
}

/**
 * 添加用户组成员
 */
export async function addGroupMembers(groupId: string, userIds: string[]): Promise<ApiResponse<{ added_count: number }>> {
  return apiClient.post(`/api/v1/groups/${groupId}/members`, { user_ids: userIds });
}

/**
 * 移除用户组成员
 */
export async function removeGroupMember(groupId: string, userId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/groups/${groupId}/members/${userId}`);
}

// ============= 统计概览 API =============

/**
 * 获取平台统计概览
 */
export async function getStatsOverview(): Promise<ApiResponse<StatsOverview>> {
  return apiClient.get('/api/v1/stats/overview');
}

// ============= 成本报告 API =============

/**
 * 获取成本概览
 */
export async function getCostSummary(params?: { period?: string }): Promise<ApiResponse<CostSummary>> {
  return apiClient.get('/api/v1/cost/summary', { params });
}

/**
 * 获取用量明细
 */
export async function getCostUsage(params?: { period?: string; resource_type?: string }): Promise<ApiResponse<{ items: CostUsageItem[] }>> {
  return apiClient.get('/api/v1/cost/usage', { params });
}

/**
 * 获取成本趋势
 */
export async function getCostTrends(params?: { days?: number }): Promise<ApiResponse<{ trends: CostTrendItem[] }>> {
  return apiClient.get('/api/v1/cost/trends', { params });
}

/**
 * 获取模型成本明细
 */
export async function getModelCosts(params?: { period?: string }): Promise<ApiResponse<{ models: ModelCost[] }>> {
  return apiClient.get('/api/v1/cost/models', { params });
}

export default {
  // 用户管理
  getUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  toggleUserStatus,

  // 角色管理
  getRoles,
  getRole,
  createRole,
  updateRole,
  deleteRole,
  getPermissions,

  // 用户组管理
  getGroups,
  getGroup,
  createGroup,
  updateGroup,
  deleteGroup,
  addGroupMembers,
  removeGroupMember,

  // 统计概览
  getStatsOverview,

  // 成本报告
  getCostSummary,
  getCostUsage,
  getCostTrends,
  getModelCosts,

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
