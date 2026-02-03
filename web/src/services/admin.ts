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
    data_api: boolean;
    model_api: boolean;
    agent_api: boolean;
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
    data_api?: boolean;
    model_api?: boolean;
    agent_api?: boolean;
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

// ============= 门户 API 类型定义 =============

// 用户通知类型
export interface UserNotification {
  id: string;
  user_id: string;
  title: string;
  content?: string;
  summary?: string;
  notification_type: 'info' | 'success' | 'warning' | 'error' | 'alert' | 'task' | 'approval' | 'system';
  category?: 'message' | 'alert' | 'task' | 'announcement';
  severity?: 'info' | 'low' | 'medium' | 'high' | 'critical';
  action_url?: string;
  action_label?: string;
  action_type?: 'link' | 'api_call' | 'modal';
  source_type?: string;
  source_id?: string;
  source_name?: string;
  is_read: boolean;
  read_at?: string;
  is_archived: boolean;
  extra_data?: Record<string, unknown>;
  created_at: string;
  sender_id?: string;
  sender_name?: string;
}

export interface NotificationListParams {
  category?: string;
  is_read?: boolean;
  type?: string;
  page?: number;
  page_size?: number;
}

export interface NotificationListResponse {
  notifications: UserNotification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

// 用户待办类型
export interface UserTodo {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  todo_type: 'approval' | 'task' | 'reminder' | 'alert' | 'review';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  source_type?: string;
  source_id?: string;
  source_name?: string;
  source_url?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'expired';
  due_date?: string;
  reminder_at?: string;
  started_at?: string;
  completed_at?: string;
  is_overdue: boolean;
  extra_data?: Record<string, unknown>;
  action_buttons?: Array<{ label: string; action: string; url?: string; style?: string }>;
  created_at: string;
  created_by?: string;
  updated_at?: string;
}

export interface TodoListParams {
  status?: string;
  type?: string;
  priority?: string;
  include_completed?: boolean;
  page?: number;
  page_size?: number;
}

export interface TodoListResponse {
  todos: UserTodo[];
  total: number;
  pending_count: number;
  overdue_count: number;
  page: number;
  page_size: number;
}

export interface TodoSummary {
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  overdue_count: number;
  due_today: number;
}

// 系统公告类型
export interface Announcement {
  id: string;
  title: string;
  content?: string;
  summary?: string;
  announcement_type: 'info' | 'update' | 'maintenance' | 'warning' | 'urgent';
  priority: number;
  is_pinned: boolean;
  is_popup: boolean;
  target_roles: string[];
  start_time?: string;
  end_time?: string;
  status: 'draft' | 'published' | 'archived';
  publish_at?: string;
  view_count: number;
  is_active: boolean;
  created_at: string;
  created_by?: string;
  updated_at?: string;
}

export interface AnnouncementListParams {
  status?: string;
  type?: string;
  active_only?: boolean;
  page?: number;
  page_size?: number;
}

export interface AnnouncementListResponse {
  announcements: Announcement[];
  total: number;
  page: number;
  page_size: number;
}

// 门户仪表板类型
export interface PortalDashboard {
  stats: {
    unread_notifications: number;
    pending_todos: number;
    overdue_todos: number;
    today_activities: number;
  };
  recent_todos: UserTodo[];
  recent_notifications: UserNotification[];
  active_announcements: Announcement[];
}

// ============= 门户通知 API =============

/**
 * 获取用户通知列表
 */
export async function getUserNotifications(params?: NotificationListParams): Promise<ApiResponse<NotificationListResponse>> {
  return apiClient.get('/api/v1/portal/notifications', { params });
}

/**
 * 获取未读通知数量
 */
export async function getUnreadCount(): Promise<ApiResponse<{ unread_count: number; by_category: Record<string, number> }>> {
  return apiClient.get('/api/v1/portal/notifications/unread-count');
}

/**
 * 获取通知详情
 */
export async function getUserNotification(notificationId: string): Promise<ApiResponse<UserNotification>> {
  return apiClient.get(`/api/v1/portal/notifications/${notificationId}`);
}

/**
 * 标记通知为已读
 */
export async function markNotificationRead(notificationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/portal/notifications/${notificationId}/read`);
}

/**
 * 标记所有通知为已读
 */
export async function markAllNotificationsRead(category?: string): Promise<ApiResponse<{ marked_count: number }>> {
  return apiClient.post('/api/v1/portal/notifications/read-all', { category });
}

/**
 * 归档通知
 */
export async function archiveNotification(notificationId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/portal/notifications/${notificationId}/archive`);
}

/**
 * 删除通知
 */
export async function deleteNotification(notificationId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/portal/notifications/${notificationId}`);
}

// ============= 门户待办 API =============

/**
 * 获取用户待办列表
 */
export async function getUserTodos(params?: TodoListParams): Promise<ApiResponse<TodoListResponse>> {
  return apiClient.get('/api/v1/portal/todos', { params });
}

/**
 * 获取待办统计摘要
 */
export async function getTodosSummary(): Promise<ApiResponse<TodoSummary>> {
  return apiClient.get('/api/v1/portal/todos/summary');
}

/**
 * 获取待办详情
 */
export async function getUserTodo(todoId: string): Promise<ApiResponse<UserTodo>> {
  return apiClient.get(`/api/v1/portal/todos/${todoId}`);
}

/**
 * 开始处理待办
 */
export async function startTodo(todoId: string): Promise<ApiResponse<UserTodo>> {
  return apiClient.post(`/api/v1/portal/todos/${todoId}/start`);
}

/**
 * 完成待办
 */
export async function completeTodo(todoId: string): Promise<ApiResponse<UserTodo>> {
  return apiClient.post(`/api/v1/portal/todos/${todoId}/complete`);
}

/**
 * 取消待办
 */
export async function cancelTodo(todoId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/portal/todos/${todoId}/cancel`);
}

// ============= 门户公告 API =============

/**
 * 获取公告列表
 */
export async function getAnnouncements(params?: AnnouncementListParams): Promise<ApiResponse<AnnouncementListResponse>> {
  return apiClient.get('/api/v1/portal/announcements', { params });
}

/**
 * 获取弹窗公告
 */
export async function getPopupAnnouncements(): Promise<ApiResponse<{ announcements: Announcement[] }>> {
  return apiClient.get('/api/v1/portal/announcements/popup');
}

/**
 * 获取公告详情
 */
export async function getAnnouncement(announcementId: string): Promise<ApiResponse<Announcement>> {
  return apiClient.get(`/api/v1/portal/announcements/${announcementId}`);
}

// ============= 门户仪表板 API =============

/**
 * 获取门户仪表板数据
 */
export async function getPortalDashboard(): Promise<ApiResponse<PortalDashboard>> {
  return apiClient.get('/api/v1/portal/dashboard');
}

/**
 * 记录用户活动
 */
export async function logUserActivity(data: {
  action: string;
  action_label?: string;
  resource_type?: string;
  resource_id?: string;
  resource_name?: string;
  resource_url?: string;
  duration_ms?: number;
}): Promise<ApiResponse<{ log_id: string }>> {
  return apiClient.post('/api/v1/portal/activities', data);
}

// ============= 内容管理 API 类型定义 =============

export interface ContentCategory {
  category_id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  parent_id?: string;
  level: number;
  path?: string;
  sort_order: number;
  is_visible: boolean;
  content_count: number;
  created_at: string;
  updated_at: string;
  children?: ContentCategory[];
}

export interface ContentTag {
  tag_id: string;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  usage_count: number;
  created_at: string;
}

export interface Article {
  article_id: string;
  title: string;
  slug: string;
  summary?: string;
  content?: string;
  content_type?: 'markdown' | 'html';
  cover_image?: string;
  category_id?: string;
  category_name?: string;
  tags: string[];
  author_id: string;
  author_name: string;
  status: 'draft' | 'pending' | 'published' | 'rejected' | 'archived';
  submitted_at?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  published_at?: string;
  published_by?: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
  allow_comment: boolean;
  is_featured: boolean;
  is_top: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArticleVersion {
  version_id: string;
  article_id: string;
  version_number: number;
  title: string;
  summary?: string;
  change_description?: string;
  change_type: 'create' | 'update' | 'minor';
  created_by?: string;
  created_by_name?: string;
  created_at: string;
}

export interface ContentApproval {
  approval_id: string;
  content_type: string;
  content_id: string;
  content_title: string;
  submitted_by: string;
  submitted_by_name: string;
  submitted_at: string;
  workflow_type?: string;
  current_step: number;
  status: 'pending' | 'approved' | 'rejected';
  reviewer_id?: string;
  reviewer_name?: string;
  reviewed_at?: string;
  comment?: string;
  rejection_reason?: string;
  completed_at?: string;
}

export interface CreateArticleRequest {
  title: string;
  slug?: string;
  summary?: string;
  content: string;
  content_type?: 'markdown' | 'html';
  cover_image?: string;
  category_id?: string;
  tags?: string[];
  status?: 'draft' | 'pending';
  allow_comment?: boolean;
  is_featured?: boolean;
  is_top?: boolean;
  meta_title?: string;
  meta_keywords?: string;
  meta_description?: string;
}

export interface UpdateArticleRequest {
  title?: string;
  summary?: string;
  content?: string;
  cover_image?: string;
  category_id?: string;
  tags?: string[];
  allow_comment?: boolean;
  is_featured?: boolean;
  is_top?: boolean;
  change_description?: string;
  change_type?: 'create' | 'update' | 'minor';
}

// ============= API管理 API 类型定义 =============

export interface ApiEndpoint {
  endpoint_id: string;
  path: string;
  method: string;
  service: string;
  blueprint?: string;
  endpoint_name?: string;
  description?: string;
  summary?: string;
  request_schema?: Record<string, unknown>;
  response_schema?: Record<string, unknown>;
  parameters?: Array<{ name: string; type: string; in: string; description: string }>;
  query_params?: Array<{ name: string; type: string; description: string }>;
  body_params?: Array<{ name: string; type: string; description: string }>;
  tags?: string[];
  requires_auth: boolean;
  required_permissions?: string[];
  call_count: number;
  error_count: number;
  avg_duration_ms?: number;
  first_call?: string;
  last_call?: string;
}

export interface ApiTestResult {
  status_code: number;
  status_text: string;
  headers: Record<string, string>;
  body: unknown;
  duration_ms: number;
  error?: string;
}

export interface ApiCallLog {
  call_id: string;
  path: string;
  method: string;
  user_id?: string;
  username?: string;
  status_code: number;
  duration_ms?: number;
  error_message?: string;
  client_ip?: string;
  created_at: string;
}

export interface ApiStats {
  total_calls: number;
  error_rate: number;
  avg_duration: number;
  status_distribution: Record<number, number>;
  method_distribution: Record<string, number>;
  slowest_apis: Array<{ path: string; method: string; avg_duration: number }>;
  period_days: number;
}

// ============= 用户画像 API 类型定义 =============

export interface UserProfile {
  profile_id: string;
  user_id: string;
  username?: string;
  display_name?: string;
  activity_score: number;
  behavior_tags: string[];
  segment_id?: string;
  segment_name?: string;
  preference_features?: Record<string, unknown>;
  last_activity?: string;
  profile_updated_at: string;
  created_at: string;
  // Extended properties from behavior analysis
  login_count?: number;
  login_days?: number;
  query_count?: number;
  export_count?: number;
  create_count?: number;
  is_risk_user?: boolean;
  last_login_at?: string;
}

export interface UserSegment {
  segment_id: string;
  segment_name: string;
  segment_type: 'active' | 'exploratory' | 'conservative' | 'power' | 'new' | 'churned' | 'custom';
  description?: string;
  criteria?: Record<string, unknown>;
  user_count: number;
  characteristics?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // Extended properties from behavior analysis
  strategy?: string;
  is_system?: boolean;
  last_rebuilt_at?: string;
}

export interface UserTag {
  tag_id: string;
  tag_name: string;
  tag_type: 'behavior' | 'preference' | 'demographic' | 'custom';
  description?: string;
  color?: string;
  user_count: number;
  auto_assign: boolean;
  assign_rule?: Record<string, unknown>;
  created_at: string;
}

export interface BehaviorAnomaly {
  anomaly_id: string;
  user_id: string;
  anomaly_type: 'login_anomaly' | 'usage_spike' | 'usage_drop' | 'unusual_access' | 'data_access';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  detected_at: string;
  resolved: boolean;
  resolved_at?: string;
  resolved_by?: string;
  context_data?: Record<string, unknown>;
}

export interface BehaviorInsights {
  total_users: number;
  active_users: number;
  segment_distribution: Record<string, number>;
  activity_heatmap: Record<string, number>;
  top_features: Array<{ feature: string; usage_count: number }>;
  churn_risk_users: number;
  trending_behaviors: Array<{ behavior: string; count: number; trend: 'up' | 'down' }>;
}

// ============= 内容管理 API =============

/**
 * 获取内容分类列表
 */
export async function getContentCategories(params?: {
  parent_id?: string;
  is_visible?: boolean;
}): Promise<ApiResponse<{ categories: ContentCategory[] }>> {
  return apiClient.get('/api/v1/content/categories', { params });
}

/**
 * 创建内容分类
 */
export async function createContentCategory(data: {
  name: string;
  slug?: string;
  description?: string;
  icon?: string;
  parent_id?: string;
  level?: number;
  path?: string;
  sort_order?: number;
  is_visible?: boolean;
}): Promise<ApiResponse<{ category: ContentCategory }>> {
  return apiClient.post('/api/v1/content/categories', data);
}

/**
 * 获取内容标签列表
 */
export async function getContentTags(params?: {
  search?: string;
}): Promise<ApiResponse<{ tags: ContentTag[] }>> {
  return apiClient.get('/api/v1/content/tags', { params });
}

/**
 * 获取文章列表
 */
export async function getArticles(params?: {
  category_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
  keyword?: string;
}): Promise<ApiResponse<{ articles: Article[]; total: number; page: number; page_size: number }>> {
  return apiClient.get('/api/v1/content/articles', { params });
}

/**
 * 创建文章
 */
export async function createArticle(data: CreateArticleRequest): Promise<ApiResponse<{ article: Article }>> {
  return apiClient.post('/api/v1/content/articles', data);
}

/**
 * 获取文章详情
 */
export async function getArticle(articleId: string): Promise<ApiResponse<{ article: Article }>> {
  return apiClient.get(`/api/v1/content/articles/${articleId}`);
}

/**
 * 更新文章
 */
export async function updateArticle(articleId: string, data: UpdateArticleRequest): Promise<ApiResponse<{ article: Article }>> {
  return apiClient.put(`/api/v1/content/articles/${articleId}`, data);
}

/**
 * 提交发布文章
 */
export async function publishArticle(articleId: string, data?: {
  workflow_type?: string;
}): Promise<ApiResponse<{ approval_id: string }>> {
  return apiClient.post(`/api/v1/content/articles/${articleId}/publish`, data);
}

/**
 * 获取文章版本历史
 */
export async function getArticleVersions(articleId: string): Promise<ApiResponse<{ versions: ArticleVersion[] }>> {
  return apiClient.get(`/api/v1/content/articles/${articleId}/versions`);
}

/**
 * 删除文章
 */
export async function deleteArticle(articleId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/content/articles/${articleId}`);
}

/**
 * 提交文章审核
 */
export async function submitArticleForApproval(articleId: string): Promise<ApiResponse<{ approval: ContentApproval }>> {
  return apiClient.post(`/api/v1/content/articles/${articleId}/submit`);
}

/**
 * 更新内容分类
 */
export async function updateContentCategory(categoryId: string, data: {
  name?: string;
  slug?: string;
  description?: string;
  icon?: string;
  parent_id?: string;
  sort_order?: number;
  is_visible?: boolean;
}): Promise<ApiResponse<{ category: ContentCategory }>> {
  return apiClient.put(`/api/v1/content/categories/${categoryId}`, data);
}

/**
 * 删除内容分类
 */
export async function deleteContentCategory(categoryId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/content/categories/${categoryId}`);
}

/**
 * 创建内容标签
 */
export async function createContentTag(data: {
  name: string;
  slug?: string;
  description?: string;
  color?: string;
}): Promise<ApiResponse<{ tag: ContentTag }>> {
  return apiClient.post('/api/v1/content/tags', data);
}

/**
 * 更新内容标签
 */
export async function updateContentTag(tagId: string, data: {
  name?: string;
  slug?: string;
  description?: string;
  color?: string;
}): Promise<ApiResponse<{ tag: ContentTag }>> {
  return apiClient.put(`/api/v1/content/tags/${tagId}`, data);
}

/**
 * 删除内容标签
 */
export async function deleteContentTag(tagId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/content/tags/${tagId}`);
}

/**
 * 获取内容审批列表
 */
export async function getContentApprovals(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ approvals: ContentApproval[]; total: number; page: number; page_size: number }>> {
  return apiClient.get('/api/v1/content/approvals', { params });
}

/**
 * 审批通过
 */
export async function approveContent(approvalId: string, data?: {
  comment?: string;
}): Promise<ApiResponse<{ approval: ContentApproval }>> {
  return apiClient.post(`/api/v1/content/approvals/${approvalId}/approve`, data);
}

/**
 * 审批拒绝
 */
export async function rejectContent(approvalId: string, data: {
  reason: string;
  comment?: string;
}): Promise<ApiResponse<{ approval: ContentApproval }>> {
  return apiClient.post(`/api/v1/content/approvals/${approvalId}/reject`, data);
}

// ============= API可视化管理 API =============

/**
 * 获取API端点列表
 */
export async function getApiEndpoints(params?: {
  service?: string;
  method?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ endpoints: ApiEndpoint[]; total: number; page: number; page_size: number }>> {
  return apiClient.get('/api/v1/admin/api-endpoints', { params });
}

/**
 * 扫描并注册API端点
 */
export async function scanApiEndpoints(): Promise<ApiResponse<{ total: number; registered: number; endpoints: ApiEndpoint[] }>> {
  return apiClient.post('/api/v1/admin/api-endpoints/scan');
}

/**
 * 获取API调用统计
 */
export async function getApiStats(params?: {
  days?: number;
  service?: string;
}): Promise<ApiResponse<ApiStats>> {
  return apiClient.get('/api/v1/admin/api-stats', { params });
}

/**
 * 测试API端点
 */
export async function testApiEndpoint(endpointId: string, data: {
  path_params?: Record<string, string>;
  query_params?: Record<string, string>;
  request_body?: Record<string, unknown>;
  headers?: Record<string, string>;
}): Promise<ApiResponse<ApiTestResult>> {
  return apiClient.post(`/api/v1/admin/api-endpoints/${endpointId}/test`, data);
}

// 别名，用于兼容 ApiTester.tsx
export const testApi = testApiEndpoint;

/**
 * 获取API调用日志列表
 */
export async function getApiCallLogs(params?: {
  path?: string;
  method?: string;
  user_id?: string;
  status_code?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ logs: ApiCallLog[]; total: number; page: number; page_size: number }>> {
  return apiClient.get('/api/v1/admin/api-calls', { params });
}

/**
 * 获取API调用详情
 */
export async function getApiCallDetail(callId: string): Promise<ApiResponse<{ log: ApiCallLog & { query_params: Record<string, string>; request_body: unknown; response_body: string } }>> {
  return apiClient.get(`/api/v1/admin/api-calls/${callId}`);
}

// ============= 用户画像 API =============

/**
 * 获取用户画像列表
 */
export async function getUserProfiles(params?: {
  segment_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{
  profiles: UserProfile[];
  total: number;
  page: number;
  page_size: number;
  active_count?: number;
  risk_count?: number;
  avg_activity?: number;
}>> {
  return apiClient.get('/api/v1/admin/user-profiles', { params });
}

/**
 * 获取用户画像详情
 */
export async function getUserProfile(userId: string): Promise<ApiResponse<{ profile: UserProfile }>> {
  return apiClient.get(`/api/v1/admin/user-profiles/${userId}`);
}

/**
 * 刷新用户画像分析
 */
export async function refreshUserProfiles(): Promise<ApiResponse<{ count: number; message: string }>> {
  return apiClient.post('/api/v1/admin/user-profiles/refresh');
}

/**
 * 获取用户分群列表
 */
export async function getUserSegments(params?: {
  is_active?: boolean;
  include_users?: boolean;
}): Promise<ApiResponse<{
  segments: UserSegment[];
  segment_count: number;
  total_users: number;
  segmented_users?: number;
}>> {
  return apiClient.get('/api/v1/admin/user-segments', { params });
}

/**
 * 重建用户分群
 */
export async function rebuildUserSegments(): Promise<ApiResponse<{
  segment_count: number;
  total_users: number;
  segmented_users: number;
}>> {
  return apiClient.post('/api/v1/admin/user-segments/rebuild');
}

/**
 * 删除用户分群
 */
export async function deleteUserSegment(segmentId: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/api/v1/admin/user-segments/${segmentId}`);
}

/**
 * 创建自定义分群
 */
export async function createUserSegment(data: {
  segment_name: string;
  description?: string;
  criteria: Record<string, unknown>;
}): Promise<ApiResponse<{ segment: UserSegment }>> {
  return apiClient.post('/api/v1/admin/user-segments', data);
}

/**
 * 获取用户标签列表
 */
export async function getUserTags(params?: {
  tag_type?: string;
}): Promise<ApiResponse<{ tags: UserTag[] }>> {
  return apiClient.get('/api/v1/admin/user-tags', { params });
}

/**
 * 创建用户标签
 */
export async function createUserTag(data: {
  tag_name: string;
  tag_type: string;
  description?: string;
  color?: string;
  auto_assign?: boolean;
  assign_rule?: Record<string, unknown>;
}): Promise<ApiResponse<{ tag: UserTag }>> {
  return apiClient.post('/api/v1/admin/user-tags', data);
}

/**
 * 获取行为洞察
 */
export async function getBehaviorInsights(params?: {
  days?: number;
}): Promise<ApiResponse<BehaviorInsights>> {
  return apiClient.get('/api/v1/admin/behavior-insights', { params });
}

/**
 * 获取行为异常列表
 */
export async function getBehaviorAnomalies(params?: {
  user_id?: string;
  severity?: string;
  resolved?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ApiResponse<{ anomalies: BehaviorAnomaly[]; total: number }>> {
  return apiClient.get('/api/v1/admin/behavior-anomalies', { params });
}

/**
 * 解决行为异常
 */
export async function resolveBehaviorAnomaly(anomalyId: string): Promise<ApiResponse<void>> {
  return apiClient.post(`/api/v1/admin/behavior-anomalies/${anomalyId}/resolve`);
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

  // 门户 - 通知
  getUserNotifications,
  getUnreadCount,
  getUserNotification,
  markNotificationRead,
  markAllNotificationsRead,
  archiveNotification,
  deleteNotification,

  // 门户 - 待办
  getUserTodos,
  getTodosSummary,
  getUserTodo,
  startTodo,
  completeTodo,
  cancelTodo,

  // 门户 - 公告
  getAnnouncements,
  getPopupAnnouncements,
  getAnnouncement,

  // 门户 - 仪表板
  getPortalDashboard,
  logUserActivity,

  // 内容管理
  getContentCategories,
  createContentCategory,
  getContentTags,
  getArticles,
  createArticle,
  getArticle,
  updateArticle,
  publishArticle,
  getArticleVersions,
  getContentApprovals,
  approveContent,
  rejectContent,

  // API可视化管理
  getApiEndpoints,
  scanApiEndpoints,
  getApiStats,
  testApiEndpoint,
  testApi,
  getApiCallLogs,
  getApiCallDetail,

  // 用户画像
  getUserProfiles,
  getUserProfile,
  refreshUserProfiles,
  getUserSegments,
  rebuildUserSegments,
  deleteUserSegment,
  createUserSegment,
  getUserTags,
  createUserTag,
  getBehaviorInsights,
  getBehaviorAnomalies,
  resolveBehaviorAnomaly,

  // 内容管理扩展
  updateContentCategory,
  deleteContentCategory,
  createContentTag,
  updateContentTag,
  deleteContentTag,
  deleteArticle,
  submitArticleForApproval,
};
