/**
 * 用户生命周期测试 Fixtures
 * 基于测试计划: docs/04-testing/user-lifecycle-test-cases.md
 *
 * 提供测试角色用户、用户管理、角色分配等公共 fixtures
 */

import { test as base, APIRequestContext, Page } from '@playwright/test';
import { logger } from '../helpers/logger';

// ==================== 类型定义 ====================

/**
 * 用户状态枚举
 */
export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  DELETED = 'deleted',
}

/**
 * 测试角色枚举
 */
export enum TestRole {
  DATA_ADMIN = 'data_admin',        // 数据管理员
  DATA_ENGINEER = 'data_engineer',  // 数据工程师
  ALGORITHM_ENGINEER = 'algorithm_engineer', // 算法工程师
  BUSINESS_USER = 'business_user',  // 业务用户
  SYSTEM_ADMIN = 'system_admin',    // 系统管理员
}

/**
 * 测试用户类型
 */
export interface TestUser {
  user_id: string;
  username: string;
  email: string;
  password: string;
  roles: TestRole[];
  status: UserStatus;
}

/**
 * 创建用户请求类型
 */
export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  roles?: TestRole[];
  status?: UserStatus;
}

/**
 * 用户管理操作结果
 */
export interface UserOperationResult {
  success: boolean;
  user_id?: string;
  message?: string;
  error?: string;
}

// ==================== 测试用户配置 ====================

/**
 * 测试用户默认配置
 */
const TEST_USER_CONFIGS: Record<TestRole, Partial<TestUser>> = {
  [TestRole.DATA_ADMIN]: {
    username: 'test_da',
    email: 'test_da@test.local',
    password: 'Da1234!',
    roles: [TestRole.DATA_ADMIN],
  },
  [TestRole.DATA_ENGINEER]: {
    username: 'test_de',
    email: 'test_de@test.local',
    password: 'De1234!',
    roles: [TestRole.DATA_ENGINEER],
  },
  [TestRole.ALGORITHM_ENGINEER]: {
    username: 'test_ae',
    email: 'test_ae@test.local',
    password: 'Ae1234!',
    roles: [TestRole.ALGORITHM_ENGINEER],
  },
  [TestRole.BUSINESS_USER]: {
    username: 'test_bu',
    email: 'test_bu@test.local',
    password: 'Bu1234!',
    roles: [TestRole.BUSINESS_USER],
  },
  [TestRole.SYSTEM_ADMIN]: {
    username: 'test_sa',
    email: 'test_sa@test.local',
    password: 'Sa1234!',
    roles: [TestRole.SYSTEM_ADMIN],
  },
};

// ==================== 用户管理器 ====================

/**
 * 用户管理器类
 * 提供用户 CRUD、角色分配、状态管理等操作
 */
export class UserManager {
  private request: APIRequestContext;
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(request: APIRequestContext, baseUrl?: string) {
    this.request = request;
    this.baseUrl = baseUrl || process.env.API_BASE || 'http://localhost:8080';
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  /**
   * 获取请求头
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  /**
   * 创建测试用户
   */
  async createUser(request: CreateUserRequest): Promise<TestUser> {
    const timestamp = Date.now();
    const user: TestUser = {
      user_id: `test_user_${timestamp}`,
      username: request.username || `test_user_${timestamp}`,
      email: request.email || `test_user_${timestamp}@test.local`,
      password: request.password || 'Test1234!',
      roles: request.roles || [TestRole.BUSINESS_USER],
      status: request.status || UserStatus.ACTIVE,
    };

    // 调用 API 创建用户
    const response = await this.request.post(`${this.baseUrl}/api/v1/users`, {
      headers: this.getHeaders(),
      data: {
        username: user.username,
        email: user.email,
        password: user.password,
        roles: user.roles,
      },
    });

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.user_id) {
        user.user_id = json.data.user_id;
      }
    } else {
      // API 失败时返回本地构造的用户
      logger.warn(`Failed to create user via API: ${response.status()}`);
    }

    return user;
  }

  /**
   * 删除测试用户
   */
  async deleteUser(userId: string): Promise<UserOperationResult> {
    const response = await this.request.delete(
      `${this.baseUrl}/api/v1/users/${userId}`,
      { headers: this.getHeaders() }
    );

    if (response.ok()) {
      const json = await response.json();
      return {
        success: json.code === 0,
        message: json.message,
      };
    }

    return {
      success: false,
      error: `Failed to delete user: ${response.status()}`,
    };
  }

  /**
   * 设置用户状态
   */
  async setUserStatus(userId: string, status: UserStatus): Promise<UserOperationResult> {
    const response = await this.request.patch(
      `${this.baseUrl}/api/v1/users/${userId}/status`,
      {
        headers: this.getHeaders(),
        data: { status },
      }
    );

    if (response.ok()) {
      const json = await response.json();
      return {
        success: json.code === 0,
        message: json.message,
      };
    }

    return {
      success: false,
      error: `Failed to set user status: ${response.status()}`,
    };
  }

  /**
   * 分配角色给用户
   */
  async assignRole(userId: string, role: TestRole): Promise<UserOperationResult> {
    const response = await this.request.post(
      `${this.baseUrl}/api/v1/users/${userId}/roles`,
      {
        headers: this.getHeaders(),
        data: { role },
      }
    );

    if (response.ok()) {
      const json = await response.json();
      return {
        success: json.code === 0,
        message: json.message,
      };
    }

    return {
      success: false,
      error: `Failed to assign role: ${response.status()}`,
    };
  }

  /**
   * 移除用户角色
   */
  async removeRole(userId: string, role: TestRole): Promise<UserOperationResult> {
    const response = await this.request.delete(
      `${this.baseUrl}/api/v1/users/${userId}/roles/${role}`,
      { headers: this.getHeaders() }
    );

    if (response.ok()) {
      const json = await response.json();
      return {
        success: json.code === 0,
        message: json.message,
      };
    }

    return {
      success: false,
      error: `Failed to remove role: ${response.status()}`,
    };
  }

  /**
   * 获取用户信息
   */
  async getUser(userId: string): Promise<TestUser | null> {
    const response = await this.request.get(
      `${this.baseUrl}/api/v1/users/${userId}`,
      { headers: this.getHeaders() }
    );

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data) {
        return {
          user_id: json.data.user_id,
          username: json.data.username,
          email: json.data.email,
          password: '', // 不返回密码
          roles: json.data.roles || [],
          status: json.data.status || UserStatus.ACTIVE,
        };
      }
    }

    return null;
  }

  /**
   * 按角色获取用户列表
   */
  async getUsersByRole(role: TestRole): Promise<TestUser[]> {
    const response = await this.request.get(
      `${this.baseUrl}/api/v1/users?role=${role}`,
      { headers: this.getHeaders() }
    );

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && Array.isArray(json.data)) {
        return json.data.map((u: any) => ({
          user_id: u.user_id,
          username: u.username,
          email: u.email,
          password: '',
          roles: u.roles || [],
          status: u.status || UserStatus.ACTIVE,
        }));
      }
    }

    return [];
  }

  /**
   * 创建指定角色的测试用户
   */
  async createTestUser(role: TestRole): Promise<TestUser> {
    const config = TEST_USER_CONFIGS[role];
    const timestamp = Date.now();

    return this.createUser({
      username: `${config.username}_${timestamp}`,
      email: `${config.username}_${timestamp}@test.local`,
      password: config.password || 'Test1234!',
      roles: config.roles || [role],
    });
  }

  /**
   * 清理所有测试用户
   */
  async cleanupTestUsers(): Promise<void> {
    const response = await this.request.get(
      `${this.baseUrl}/api/v1/users?username_prefix=test_`,
      { headers: this.getHeaders() }
    );

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && Array.isArray(json.data)) {
        for (const user of json.data) {
          await this.deleteUser(user.user_id);
        }
      }
    }
  }
}

// ==================== 认证管理器 ====================

/**
 * 认证管理器类
 * 处理用户登录、令牌刷新等操作
 */
export class AuthManager {
  private request: APIRequestContext;
  private baseUrl: string;

  constructor(request: APIRequestContext, baseUrl?: string) {
    this.request = request;
    this.baseUrl = baseUrl || process.env.API_BASE || 'http://localhost:8080';
  }

  /**
   * 用户登录
   */
  async login(username: string, password: string): Promise<string | null> {
    const response = await this.request.post(`${this.baseUrl}/api/v1/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: { username, password },
    });

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.token) {
        return json.data.token;
      }
    }

    return null;
  }

  /**
   * 测试角色用户登录
   */
  async loginAs(role: TestRole): Promise<string | null> {
    const config = TEST_USER_CONFIGS[role];
    return this.login(config.username, config.password);
  }

  /**
   * 刷新令牌
   */
  async refreshAccessToken(refreshToken: string): Promise<string | null> {
    const response = await this.request.post(`${this.baseUrl}/api/v1/auth/refresh`, {
      headers: { 'Content-Type': 'application/json' },
      data: { refresh_token: refreshToken },
    });

    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.token) {
        return json.data.token;
      }
    }

    return null;
  }

  /**
   * 用户登出
   */
  async logout(token: string): Promise<boolean> {
    const response = await this.request.post(`${this.baseUrl}/api/v1/auth/logout`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    return response.ok();
  }
}

// ==================== 页面认证设置 ====================

/**
 * 设置页面认证状态
 */
async function setupAuthToPage(
  page: Page,
  username: string,
  roles: TestRole[],
  token?: string
): Promise<void> {
  // 构造 Mock JWT（如果未提供真实 token）
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    .toString('base64')
    .replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: username,
    username: username,
    roles: roles,
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
  })).toString('base64').replace(/=+$/, '');
  const mockToken = token || `${header}.${payload}.signature`;

  await page.addInitScript(({ accessToken, userInfo }) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', accessToken);
    localStorage.setItem('user_info', JSON.stringify(userInfo));
  }, {
    accessToken: mockToken,
    userInfo: {
      user_id: username,
      username: username,
      email: `${username}@test.local`,
      roles: roles,
    },
  });
}

// ==================== Fixtures 类型定义 ====================

type UserLifecycleFixtures = {
  // API 请求上下文
  request: APIRequestContext;

  // API 基础 URL
  apiBaseUrl: string;

  // 用户管理器
  userManager: UserManager;

  // 认证管理器
  authManager: AuthManager;

  // 测试用户
  testDataAdmin: TestUser;
  testDataEngineer: TestUser;
  testAlgorithmEngineer: TestUser;
  testBusinessUser: TestUser;
  testSystemAdmin: TestUser;

  // 已认证的页面（各角色）
  dataAdminPage: Page;
  dataEngineerPage: Page;
  algorithmEngineerPage: Page;
  businessUserPage: Page;
  systemAdminPage: Page;

  // 认证令牌
  dataAdminToken: string;
  dataEngineerToken: string;
  algorithmEngineerToken: string;
  businessUserToken: string;
  systemAdminToken: string;
};

// ==================== 扩展测试对象 ====================

export const test = base.extend<UserLifecycleFixtures>({
  // API 基础 URL
  apiBaseUrl: async ({}, use) => {
    await use(process.env.API_BASE || 'http://localhost:8080');
  },

  // 用户管理器
  userManager: async ({ request, apiBaseUrl }, use) => {
    const manager = new UserManager(request, apiBaseUrl);
    await use(manager);
  },

  // 认证管理器
  authManager: async ({ request, apiBaseUrl }, use) => {
    const manager = new AuthManager(request, apiBaseUrl);
    await use(manager);
  },

  // 测试用户 - 数据管理员
  testDataAdmin: async ({}, use) => {
    const user: TestUser = {
      user_id: 'test_da',
      username: 'test_da',
      email: 'test_da@test.local',
      password: 'Da1234!',
      roles: [TestRole.DATA_ADMIN],
      status: UserStatus.ACTIVE,
    };
    await use(user);
  },

  // 测试用户 - 数据工程师
  testDataEngineer: async ({}, use) => {
    const user: TestUser = {
      user_id: 'test_de',
      username: 'test_de',
      email: 'test_de@test.local',
      password: 'De1234!',
      roles: [TestRole.DATA_ENGINEER],
      status: UserStatus.ACTIVE,
    };
    await use(user);
  },

  // 测试用户 - 算法工程师
  testAlgorithmEngineer: async ({}, use) => {
    const user: TestUser = {
      user_id: 'test_ae',
      username: 'test_ae',
      email: 'test_ae@test.local',
      password: 'Ae1234!',
      roles: [TestRole.ALGORITHM_ENGINEER],
      status: UserStatus.ACTIVE,
    };
    await use(user);
  },

  // 测试用户 - 业务用户
  testBusinessUser: async ({}, use) => {
    const user: TestUser = {
      user_id: 'test_bu',
      username: 'test_bu',
      email: 'test_bu@test.local',
      password: 'Bu1234!',
      roles: [TestRole.BUSINESS_USER],
      status: UserStatus.ACTIVE,
    };
    await use(user);
  },

  // 测试用户 - 系统管理员
  testSystemAdmin: async ({}, use) => {
    const user: TestUser = {
      user_id: 'test_sa',
      username: 'test_sa',
      email: 'test_sa@test.local',
      password: 'Sa1234!',
      roles: [TestRole.SYSTEM_ADMIN],
      status: UserStatus.ACTIVE,
    };
    await use(user);
  },

  // 已认证页面 - 数据管理员
  dataAdminPage: async ({ page }, use) => {
    await setupAuthToPage(page, 'test_da', [TestRole.DATA_ADMIN]);
    await use(page);
  },

  // 已认证页面 - 数据工程师
  dataEngineerPage: async ({ page }, use) => {
    await setupAuthToPage(page, 'test_de', [TestRole.DATA_ENGINEER]);
    await use(page);
  },

  // 已认证页面 - 算法工程师
  algorithmEngineerPage: async ({ page }, use) => {
    await setupAuthToPage(page, 'test_ae', [TestRole.ALGORITHM_ENGINEER]);
    await use(page);
  },

  // 已认证页面 - 业务用户
  businessUserPage: async ({ page }, use) => {
    await setupAuthToPage(page, 'test_bu', [TestRole.BUSINESS_USER]);
    await use(page);
  },

  // 已认证页面 - 系统管理员
  systemAdminPage: async ({ page }, use) => {
    await setupAuthToPage(page, 'test_sa', [TestRole.SYSTEM_ADMIN]);
    await use(page);
  },

  // 认证令牌 - 数据管理员
  dataAdminToken: async ({ authManager }, use) => {
    const token = await authManager.loginAs(TestRole.DATA_ADMIN);
    await use(token || '');
  },

  // 认证令牌 - 数据工程师
  dataEngineerToken: async ({ authManager }, use) => {
    const token = await authManager.loginAs(TestRole.DATA_ENGINEER);
    await use(token || '');
  },

  // 认证令牌 - 算法工程师
  algorithmEngineerToken: async ({ authManager }, use) => {
    const token = await authManager.loginAs(TestRole.ALGORITHM_ENGINEER);
    await use(token || '');
  },

  // 认证令牌 - 业务用户
  businessUserToken: async ({ authManager }, use) => {
    const token = await authManager.loginAs(TestRole.BUSINESS_USER);
    await use(token || '');
  },

  // 认证令牌 - 系统管理员
  systemAdminToken: async ({ authManager }, use) => {
    const token = await authManager.loginAs(TestRole.SYSTEM_ADMIN);
    await use(token || '');
  },
});

// 导出 expect
export { expect } from '@playwright/test';
