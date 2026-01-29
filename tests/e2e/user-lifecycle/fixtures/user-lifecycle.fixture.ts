/**
 * 用户生命周期专用 Fixture
 * 提供用户创建、状态管理、角色分配等功能
 */

import { test as base, APIRequestContext, Page } from '@playwright/test';
import { createApiClient, ApiClient } from '../../helpers/api-client';
import { test as testDataTest, TestDataFixtures } from './test-data.fixture';

// ============================================
// 类型定义
// ============================================

/**
 * 用户角色类型
 */
export type TestRole = 'admin' | 'data_engineer' | 'ai_developer' | 'data_analyst' | 'user' | 'guest';

/**
 * 用户状态类型
 */
export type UserStatus = 'pending' | 'active' | 'inactive' | 'locked' | 'deleted';

/**
 * 用户信息接口
 */
export interface TestUser {
  id: string;
  username: string;
  email: string;
  status: UserStatus;
  roles: TestRole[];
  created_at: string;
  last_login_at?: string;
  failed_login_count: number;
  login_count: number;
}

/**
 * 创建用户请求
 */
export interface CreateUserRequest {
  username: string;
  email: string;
  password?: string;
  roles?: TestRole[];
  status?: UserStatus;
}

/**
 * API 响应包装
 */
interface ApiResponse<T = any> {
  code: number;
  message?: string;
  data?: T;
  error?: string;
}

// ============================================
// 测试用户配置
// ============================================

const TEST_USERS: Record<string, CreateUserRequest> = {
  test_admin: {
    username: 'test_admin',
    email: 'test_admin@example.com',
    password: 'Admin1234!',
    roles: ['admin'],
    status: 'active',
  },
  test_de: {
    username: 'test_de',
    email: 'test_de@example.com',
    password: 'De1234!',
    roles: ['data_engineer'],
    status: 'active',
  },
  test_ai: {
    username: 'test_ai',
    email: 'test_ai@example.com',
    password: 'Ai1234!',
    roles: ['ai_developer'],
    status: 'active',
  },
  test_da: {
    username: 'test_da',
    email: 'test_da@example.com',
    password: 'Da1234!',
    roles: ['data_analyst'],
    status: 'active',
  },
  test_user: {
    username: 'test_user',
    email: 'test_user@example.com',
    password: 'User1234!',
    roles: ['user'],
    status: 'active',
  },
  test_guest: {
    username: 'test_guest',
    email: 'test_guest@example.com',
    password: 'Guest1234!',
    roles: ['guest'],
    status: 'active',
  },
  test_pending: {
    username: 'test_pending',
    email: 'test_pending@example.com',
    password: 'Pending1234!',
    roles: ['user'],
    status: 'pending',
  },
  test_inactive: {
    username: 'test_inactive',
    email: 'test_inactive@example.com',
    password: 'Inactive1234!',
    roles: ['user'],
    status: 'inactive',
  },
  test_locked: {
    username: 'test_locked',
    email: 'test_locked@example.com',
    password: 'Locked1234!',
    roles: ['user'],
    status: 'locked',
  },
  test_deleted: {
    username: 'test_deleted',
    email: 'test_deleted@example.com',
    password: 'Deleted1234!',
    roles: ['user'],
    status: 'deleted',
  },
};

// ============================================
// 用户管理类
// ============================================

export class UserManager {
  private apiClient: ApiClient;
  private createdUsers: string[] = [];

  constructor(request: APIRequestContext, baseUrl?: string) {
    this.apiClient = createApiClient(request, 'agent_api');
  }

  /**
   * 通过 API 创建测试用户
   */
  async createUser(request: CreateUserRequest): Promise<TestUser> {
    const response = await this.apiClient.post<ApiResponse<TestUser>>('/api/v1/users', {
      username: request.username,
      email: request.email,
      password: request.password || 'Test1234!',
      roles: request.roles || ['user'],
    });

    if (response.code !== 0 || !response.data) {
      throw new Error(`创建用户失败: ${response.message || response.error}`);
    }

    const user = response.data;
    this.createdUsers.push(user.id);

    // 如果需要设置特定状态
    if (request.status && request.status !== 'pending') {
      await this.setUserStatus(user.id, request.status);
    }

    return user;
  }

  /**
   * 通过 API 删除测试用户
   */
  async deleteUser(userId: string): Promise<void> {
    const response = await this.apiClient.delete<ApiResponse>(`/api/v1/users/${userId}`);

    if (response.code !== 0) {
      throw new Error(`删除用户失败: ${response.message || response.error}`);
    }

    this.createdUsers = this.createdUsers.filter(id => id !== userId);
  }

  /**
   * 设置用户状态
   */
  async setUserStatus(userId: string, status: UserStatus): Promise<void> {
    const response = await this.apiClient.put<ApiResponse>(`/api/v1/users/${userId}/status`, {
      status,
    });

    if (response.code !== 0) {
      throw new Error(`设置用户状态失败: ${response.message || response.error}`);
    }
  }

  /**
   * 为用户分配角色
   */
  async assignRole(userId: string, role: TestRole): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>(`/api/v1/users/${userId}/roles`, {
      role,
    });

    if (response.code !== 0) {
      throw new Error(`分配角色失败: ${response.message || response.error}`);
    }
  }

  /**
   * 撤销用户角色
   */
  async revokeRole(userId: string, role: TestRole): Promise<void> {
    const response = await this.apiClient.delete<ApiResponse>(`/api/v1/users/${userId}/roles/${role}`);

    if (response.code !== 0) {
      throw new Error(`撤销角色失败: ${response.message || response.error}`);
    }
  }

  /**
   * 获取用户信息
   */
  async getUser(userId: string): Promise<TestUser | null> {
    const response = await this.apiClient.get<ApiResponse<TestUser>>(`/api/v1/users/${userId}`);

    if (response.code === 0 && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 通过用户名获取用户
   */
  async getUserByUsername(username: string): Promise<TestUser | null> {
    const response = await this.apiClient.get<ApiResponse<TestUser>>(`/api/v1/users/by-username/${username}`);

    if (response.code === 0 && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 等待用户状态变更
   */
  async waitForUserStatusChange(
    userId: string,
    expectedStatus: UserStatus,
    timeout = 10000
  ): Promise<boolean> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const user = await this.getUser(userId);
      if (user && user.status === expectedStatus) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    return false;
  }

  /**
   * 激活用户
   */
  async activateUser(userId: string): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>(`/api/v1/users/${userId}/activate`, {});

    if (response.code !== 0) {
      throw new Error(`激活用户失败: ${response.message || response.error}`);
    }
  }

  /**
   * 停用用户
   */
  async deactivateUser(userId: string): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>(`/api/v1/users/${userId}/deactivate`, {});

    if (response.code !== 0) {
      throw new Error(`停用用户失败: ${response.message || response.error}`);
    }
  }

  /**
   * 解锁用户
   */
  async unlockUser(userId: string): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>(`/api/v1/users/${userId}/unlock`, {});

    if (response.code !== 0) {
      throw new Error(`解锁用户失败: ${response.message || response.error}`);
    }
  }

  /**
   * 重置用户密码
   */
  async resetPassword(userId: string, newPassword: string): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>(`/api/v1/users/${userId}/reset-password`, {
      password: newPassword,
    });

    if (response.code !== 0) {
      throw new Error(`重置密码失败: ${response.message || response.error}`);
    }
  }

  /**
   * 模拟登录失败（用于测试账户锁定）
   */
  async simulateFailedLogin(username: string): Promise<void> {
    const response = await this.apiClient.post<ApiResponse>('/api/v1/auth/login', {
      username,
      password: 'WrongPassword123!',
    });

    // 预期失败，所以不检查错误
  }

  /**
   * 获取所有测试用户配置
   */
  getTestUserConfigs(): Record<string, CreateUserRequest> {
    return { ...TEST_USERS };
  }

  /**
   * 获取指定测试用户配置
   */
  getTestUserConfig(key: string): CreateUserRequest | undefined {
    return TEST_USERS[key];
  }

  /**
   * 清理所有创建的测试用户
   */
  async cleanup(): Promise<void> {
    for (const userId of [...this.createdUsers]) {
      try {
        await this.deleteUser(userId);
      } catch (error) {
        console.error(`清理用户 ${userId} 失败:`, error);
      }
    }
    this.createdUsers = [];
  }

  /**
   * 获取已创建的用户 ID 列表
   */
  getCreatedUserIds(): string[] {
    return [...this.createdUsers];
  }
}

// ============================================
// Fixture 类型定义
// ============================================

type UserLifecycleFixtures = {
  /** 用户管理器 */
  userManager: UserManager;
  /** 已认证的管理员页面 */
  adminPage: Page;
  /** 创建测试用户 */
  createTestUser: (request: CreateUserRequest) => Promise<TestUser>;
  /** 设置用户状态 */
  setUserStatus: (userId: string, status: UserStatus) => Promise<void>;
  /** 分配角色 */
  assignRole: (userId: string, role: TestRole) => Promise<void>;
  /** 撤销角色 */
  revokeRole: (userId: string, role: TestRole) => Promise<void>;
  /** 获取用户信息 */
  getUser: (userId: string) => Promise<TestUser | null>;
  /** 等待用户状态变更 */
  waitForUserStatusChange: (userId: string, status: UserStatus, timeout?: number) => Promise<boolean>;
  /** 激活用户 */
  activateUser: (userId: string) => Promise<void>;
  /** 停用用户 */
  deactivateUser: (userId: string) => Promise<void>;
  /** 解锁用户 */
  unlockUser: (userId: string) => Promise<void>;
  /** 删除用户 */
  deleteUser: (userId: string) => Promise<void>;
  /** 清理测试用户 */
  cleanupTestUsers: () => Promise<void>;
};

// 合并 test-data fixtures 和 user-lifecycle fixtures
type CombinedFixtures = UserLifecycleFixtures & TestDataFixtures;

// ============================================
// 扩展测试对象
// ============================================

export const test = testDataTest.extend<CombinedFixtures>({
  // 已认证的管理员页面
  adminPage: async ({ page }, use) => {
    // 设置管理员认证
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
    const payload = Buffer.from(JSON.stringify({
      sub: 'test-admin',
      username: 'test-admin',
      email: 'admin@example.com',
      roles: ['admin', 'user'],
      exp: Math.floor(Date.now() / 1000) + 3600 * 24,
    })).toString('base64').replace(/=+$/, '');
    const mockToken = `${header}.${payload}.signature`;

    await page.addInitScript(({ token, roles }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('user_info', JSON.stringify({
        user_id: 'test-admin',
        username: 'test-admin',
        email: 'admin@example.com',
        roles: roles,
      }));
    }, { token: mockToken, roles: ['admin', 'user'] });

    // 设置通用 API Mock
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'test-admin',
            username: 'test-admin',
            email: 'admin@example.com',
            role: 'admin',
          },
        }),
      });
    });

    await use(page);
  },

  // 用户管理器
  userManager: async ({ request }, use) => {
    const manager = new UserManager(request);
    await use(manager);
    await manager.cleanup();
  },

  // 创建测试用户
  createTestUser: async ({ userManager }, use) => {
    await use((request: CreateUserRequest) => userManager.createUser(request));
  },

  // 设置用户状态
  setUserStatus: async ({ userManager }, use) => {
    await use((userId: string, status: UserStatus) => userManager.setUserStatus(userId, status));
  },

  // 分配角色
  assignRole: async ({ userManager }, use) => {
    await use((userId: string, role: TestRole) => userManager.assignRole(userId, role));
  },

  // 撤销角色
  revokeRole: async ({ userManager }, use) => {
    await use((userId: string, role: TestRole) => userManager.revokeRole(userId, role));
  },

  // 获取用户信息
  getUser: async ({ userManager }, use) => {
    await use((userId: string) => userManager.getUser(userId));
  },

  // 等待用户状态变更
  waitForUserStatusChange: async ({ userManager }, use) => {
    await use((userId: string, status: UserStatus, timeout?: number) =>
      userManager.waitForUserStatusChange(userId, status, timeout)
    );
  },

  // 激活用户
  activateUser: async ({ userManager }, use) => {
    await use((userId: string) => userManager.activateUser(userId));
  },

  // 停用用户
  deactivateUser: async ({ userManager }, use) => {
    await use((userId: string) => userManager.deactivateUser(userId));
  },

  // 解锁用户
  unlockUser: async ({ userManager }, use) => {
    await use((userId: string) => userManager.unlockUser(userId));
  },

  // 删除用户
  deleteUser: async ({ userManager }, use) => {
    await use((userId: string) => userManager.deleteUser(userId));
  },

  // 清理测试用户
  cleanupTestUsers: async ({ userManager }, use) => {
    await use(() => userManager.cleanup());
  },
});

export { expect } from '@playwright/test';
export type { TestUser, CreateUserRequest, UserStatus, TestRole };
export { TEST_USERS };
