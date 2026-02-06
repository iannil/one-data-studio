/**
 * Admin service API 测试
 * 测试管理后台 API 客户端
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  ApiResponse: {},
}));

import {
  getSystemSettings,
  updateSystemSettings,
  getUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  toggleUserStatus,
  getRoles,
  getRole,
  createRole,
  updateRole,
  deleteRole,
  getPermissions,
  getGroups,
  getGroup,
  createGroup,
  updateGroup,
  deleteGroup,
  addGroupMembers,
  removeGroupMember,
  getStatsOverview,
  getCostSummary,
  getCostUsage,
  getUserNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  getUserTodos,
  getTodosSummary,
  startTodo,
  completeTodo,
  cancelTodo,
  getAnnouncements,
  getPopupAnnouncements,
  getPortalDashboard,
} from './admin';
import { apiClient } from './api';

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;
const mockPut = apiClient.put as ReturnType<typeof vi.fn>;
const mockDelete = apiClient.delete as ReturnType<typeof vi.fn>;

describe('Admin Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 系统配置 API ====================

  describe('System Settings', () => {
    it('should get system settings', async () => {
      mockGet.mockResolvedValue({ code: 0, data: { site_name: 'Test Site' } });
      await getSystemSettings();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/admin/settings');
    });

    it('should update system settings', async () => {
      const updateData = { site_name: 'Updated Site' };
      mockPut.mockResolvedValue({ code: 0, data: { site_name: 'Updated Site' } });
      await updateSystemSettings(updateData);
      expect(mockPut).toHaveBeenCalledWith('/api/v1/admin/settings', updateData);
    });
  });

  // ==================== 用户管理 API ====================

  describe('User Management', () => {
    it('should get users list', async () => {
      const params = { page: 1, page_size: 20 };
      mockGet.mockResolvedValue({ code: 0, data: { users: [], total: 0 } });
      await getUsers(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/users', { params });
    });

    it('should get user by id', async () => {
      const userId = 'user-123';
      mockGet.mockResolvedValue({ code: 0, data: { id: userId } });
      await getUser(userId);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/users/${userId}`);
    });

    it('should create user', async () => {
      const userData = {
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
        display_name: 'Test User',
      };
      mockPost.mockResolvedValue({ code: 0, data: { user_id: 'new-user-123' } });
      await createUser(userData);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/users', userData);
    });

    it('should update user', async () => {
      const userId = 'user-123';
      const updateData = { display_name: 'Updated Name' };
      mockPut.mockResolvedValue({ code: 0, data: { id: userId } });
      await updateUser(userId, updateData);
      expect(mockPut).toHaveBeenCalledWith(`/api/v1/users/${userId}`, updateData);
    });

    it('should delete user', async () => {
      const userId = 'user-123';
      mockDelete.mockResolvedValue({ code: 0 });
      await deleteUser(userId);
      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/users/${userId}`);
    });

    it('should reset user password', async () => {
      const userId = 'user-123';
      mockPost.mockResolvedValue({ code: 0, data: { temp_password: 'newpass' } });
      await resetUserPassword(userId, 'newpassword');
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/users/${userId}/reset-password`, {
        new_password: 'newpassword',
      });
    });

    it('should toggle user status', async () => {
      const userId = 'user-123';
      mockPost.mockResolvedValue({ code: 0, data: { status: 'inactive' } });
      await toggleUserStatus(userId);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/users/${userId}/toggle-status`);
    });
  });

  // ==================== 角色管理 API ====================

  describe('Role Management', () => {
    it('should get roles list', async () => {
      mockGet.mockResolvedValue({ code: 0, data: { roles: [], total: 0 } });
      await getRoles();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/roles');
    });

    it('should get role by id', async () => {
      const roleId = 'role-123';
      mockGet.mockResolvedValue({ code: 0, data: { id: roleId } });
      await getRole(roleId);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/roles/${roleId}`);
    });

    it('should create role', async () => {
      const roleData = {
        name: 'editor',
        display_name: 'Editor',
        permission_ids: ['perm-1', 'perm-2'],
      };
      mockPost.mockResolvedValue({ code: 0, data: { role_id: 'new-role-123' } });
      await createRole(roleData);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/roles', roleData);
    });

    it('should update role', async () => {
      const roleId = 'role-123';
      const updateData = { display_name: 'Senior Editor' };
      mockPut.mockResolvedValue({ code: 0, data: { id: roleId } });
      await updateRole(roleId, updateData);
      expect(mockPut).toHaveBeenCalledWith(`/api/v1/roles/${roleId}`, updateData);
    });

    it('should delete role', async () => {
      const roleId = 'role-123';
      mockDelete.mockResolvedValue({ code: 0 });
      await deleteRole(roleId);
      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/roles/${roleId}`);
    });

    it('should get permissions list', async () => {
      mockGet.mockResolvedValue({ code: 0, data: { permissions: [] } });
      await getPermissions();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/permissions');
    });
  });

  // ==================== 用户组管理 API ====================

  describe('Group Management', () => {
    it('should get groups list', async () => {
      const params = { page: 1 };
      mockGet.mockResolvedValue({ code: 0, data: { groups: [], total: 0 } });
      await getGroups(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/groups', { params });
    });

    it('should get group by id', async () => {
      const groupId = 'group-123';
      mockGet.mockResolvedValue({ code: 0, data: { id: groupId } });
      await getGroup(groupId, true);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/groups/${groupId}`, {
        params: { include_members: true },
      });
    });

    it('should create group', async () => {
      const groupData = {
        name: 'engineering',
        display_name: 'Engineering Team',
        group_type: 'department' as const,
      };
      mockPost.mockResolvedValue({ code: 0, data: { group_id: 'new-group-123' } });
      await createGroup(groupData);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/groups', groupData);
    });

    it('should update group', async () => {
      const groupId = 'group-123';
      const updateData = { display_name: 'Engineering Team (Updated)' };
      mockPut.mockResolvedValue({ code: 0, data: { id: groupId } });
      await updateGroup(groupId, updateData);
      expect(mockPut).toHaveBeenCalledWith(`/api/v1/groups/${groupId}`, updateData);
    });

    it('should delete group', async () => {
      const groupId = 'group-123';
      mockDelete.mockResolvedValue({ code: 0 });
      await deleteGroup(groupId);
      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/groups/${groupId}`);
    });

    it('should add group members', async () => {
      const groupId = 'group-123';
      const userIds = ['user-1', 'user-2'];
      mockPost.mockResolvedValue({ code: 0, data: { added_count: 2 } });
      await addGroupMembers(groupId, userIds);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/groups/${groupId}/members`, {
        user_ids: userIds,
      });
    });

    it('should remove group member', async () => {
      const groupId = 'group-123';
      const userId = 'user-1';
      mockDelete.mockResolvedValue({ code: 0 });
      await removeGroupMember(groupId, userId);
      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/groups/${groupId}/members/${userId}`);
    });
  });

  // ==================== 统计概览 API ====================

  describe('Statistics', () => {
    it('should get stats overview', async () => {
      mockGet.mockResolvedValue({
        code: 0,
        data: {
          users: { total: 100, active: 85 },
          datasets: { total: 50, recent: 5 },
        },
      });
      await getStatsOverview();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/stats/overview');
    });

    it('should get cost summary', async () => {
      const params = { period: '2024-01' };
      mockGet.mockResolvedValue({
        code: 0,
        data: { total_cost: 1000, compute_cost: 800 },
      });
      await getCostSummary(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/cost/summary', { params });
    });

    it('should get cost usage', async () => {
      const params = { period: '2024-01', resource_type: 'compute' };
      mockGet.mockResolvedValue({ code: 0, data: { items: [] } });
      await getCostUsage(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/cost/usage', { params });
    });
  });

  // ==================== 门户通知 API ====================

  describe('Portal Notifications', () => {
    it('should get user notifications', async () => {
      const params = { page: 1, is_read: false };
      mockGet.mockResolvedValue({
        code: 0,
        data: { notifications: [], total: 0, unread_count: 5 },
      });
      await getUserNotifications(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/notifications', { params });
    });

    it('should get unread count', async () => {
      mockGet.mockResolvedValue({
        code: 0,
        data: { unread_count: 5, by_category: { message: 2, alert: 3 } },
      });
      await getUnreadCount();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/notifications/unread-count');
    });

    it('should mark notification as read', async () => {
      const notificationId = 'notif-123';
      mockPost.mockResolvedValue({ code: 0 });
      await markNotificationRead(notificationId);
      expect(mockPost).toHaveBeenCalledWith(
        `/api/v1/portal/notifications/${notificationId}/read`
      );
    });

    it('should mark all notifications as read', async () => {
      mockPost.mockResolvedValue({ code: 0, data: { marked_count: 10 } });
      await markAllNotificationsRead('message');
      expect(mockPost).toHaveBeenCalledWith('/api/v1/portal/notifications/read-all', {
        category: 'message',
      });
    });
  });

  // ==================== 门户待办 API ====================

  describe('Portal Todos', () => {
    it('should get user todos', async () => {
      const params = { status: 'pending' };
      mockGet.mockResolvedValue({
        code: 0,
        data: { todos: [], total: 0, pending_count: 5 },
      });
      await getUserTodos(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/todos', { params });
    });

    it('should get todos summary', async () => {
      mockGet.mockResolvedValue({
        code: 0,
        data: {
          by_status: { pending: 5, completed: 10 },
          overdue_count: 2,
        },
      });
      await getTodosSummary();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/todos/summary');
    });

    it('should start todo', async () => {
      const todoId = 'todo-123';
      mockPost.mockResolvedValue({ code: 0, data: { id: todoId, status: 'in_progress' } });
      await startTodo(todoId);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/portal/todos/${todoId}/start`);
    });

    it('should complete todo', async () => {
      const todoId = 'todo-123';
      mockPost.mockResolvedValue({ code: 0, data: { id: todoId, status: 'completed' } });
      await completeTodo(todoId);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/portal/todos/${todoId}/complete`);
    });

    it('should cancel todo', async () => {
      const todoId = 'todo-123';
      mockPost.mockResolvedValue({ code: 0 });
      await cancelTodo(todoId);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/portal/todos/${todoId}/cancel`);
    });
  });

  // ==================== 门户公告 API ====================

  describe('Portal Announcements', () => {
    it('should get announcements', async () => {
      const params = { status: 'published', active_only: true };
      mockGet.mockResolvedValue({
        code: 0,
        data: { announcements: [], total: 0 },
      });
      await getAnnouncements(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/announcements', { params });
    });

    it('should get popup announcements', async () => {
      mockGet.mockResolvedValue({ code: 0, data: { announcements: [] } });
      await getPopupAnnouncements();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/announcements/popup');
    });
  });

  // ==================== 门户仪表板 API ====================

  describe('Portal Dashboard', () => {
    it('should get portal dashboard', async () => {
      mockGet.mockResolvedValue({
        code: 0,
        data: {
          stats: { unread_notifications: 5, pending_todos: 3 },
          recent_todos: [],
          recent_notifications: [],
        },
      });
      await getPortalDashboard();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/portal/dashboard');
    });
  });
});
