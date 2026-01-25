/**
 * API Mock 工具
 * 提供常用的 API Mock 功能
 */

import { Page, APIResponse } from '@playwright/test';

// ============================================
// 类型定义
// ============================================

interface MockUser {
  id: string;
  username: string;
  email: string;
  roles: string[];
  status: string;
  created_at: string;
  last_login_at?: string;
  failed_login_count: number;
  login_count: number;
}

interface MockApiResponse<T = any> {
  code: number;
  message?: string;
  data?: T;
}

// ============================================
// 用户相关 Mock
// ============================================

/**
 * Mock 用户列表 API
 */
export function mockUserList(page: Page, users: MockUser[]) {
  page.route('**/api/v1/users**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: {
          users,
          total: users.length,
          page: 1,
          page_size: 10,
        },
      }),
    });
  });
}

/**
 * Mock 用户详情 API
 */
export function mockUserDetail(page: Page, user: MockUser) {
  page.route(`**/api/v1/users/${user.id}**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: user,
      }),
    });
  });
}

/**
 * Mock 创建用户 API
 */
export function mockCreateUser(page: Page, onSuccess: boolean = true) {
  page.route('**/api/v1/users', async (route) => {
    if (route.request().method() === 'POST') {
      if (onSuccess) {
        const body = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: `user_${Date.now()}`,
              username: body.username,
              email: body.email,
              roles: body.roles || ['user'],
              status: body.status || 'pending',
              created_at: new Date().toISOString(),
              failed_login_count: 0,
              login_count: 0,
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 1,
            message: '创建用户失败',
          }),
        });
      }
    }
  });
}

/**
 * Mock 删除用户 API
 */
export function mockDeleteUser(page: Page, onSuccess: boolean = true) {
  page.route('**/api/v1/users/**', async (route) => {
    if (route.request().method() === 'DELETE') {
      if (onSuccess) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: '删除成功',
          }),
        });
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 1,
            message: '删除失败',
          }),
        });
      }
    }
  });
}

/**
 * Mock 角色分配 API
 */
export function mockAssignRole(page: Page, onSuccess: boolean = true) {
  page.route('**/api/v1/users/**/roles**', async (route) => {
    if (route.request().method() === 'POST') {
      if (onSuccess) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: '角色分配成功',
          }),
        });
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 1,
            message: '角色分配失败',
          }),
        });
      }
    }
  });
}

// ============================================
// 认证相关 Mock
// ============================================

/**
 * Mock 登录 API
 */
export function mockLogin(page: Page, onSuccess: boolean = true, user?: MockUser) {
  page.route('**/api/v1/auth/login', async (route) => {
    if (onSuccess) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            access_token: 'mock_access_token',
            refresh_token: 'mock_refresh_token',
            expires_in: 3600,
            user: user || {
              id: 'mock_user_id',
              username: 'mock_user',
              email: 'mock@example.com',
              roles: ['user'],
            },
          },
        }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 1,
          message: '用户名或密码错误',
        }),
      });
    }
  });
}

/**
 * Mock 登出 API
 */
export function mockLogout(page: Page) {
  page.route('**/api/v1/auth/logout', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: '登出成功',
      }),
    });
  });
}

// ============================================
// 角色权限相关 Mock
// ============================================

/**
 * Mock 角色列表 API
 */
export function mockRoleList(page: Page) {
  page.route('**/api/v1/roles**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: {
          roles: [
            { id: '1', name: 'admin', description: '管理员', permissions: ['*'] },
            { id: '2', name: 'data_engineer', description: '数据工程师', permissions: ['data.*'] },
            { id: '3', name: 'ai_developer', description: 'AI 开发者', permissions: ['ai.*'] },
            { id: '4', name: 'data_analyst', description: '数据分析师', permissions: ['data.read'] },
            { id: '5', name: 'user', description: '普通用户', permissions: ['basic'] },
            { id: '6', name: 'guest', description: '访客', permissions: [] },
          ],
        },
      }),
    });
  });
}

/**
 * Mock 权限验证 API
 */
export function mockPermissionCheck(page: Page, permissions: string[]) {
  page.route('**/api/v1/permissions/check**', async (route) => {
    const body = route.request().postDataJSON();
    const hasPermission = permissions.includes(body.permission);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: { allowed: hasPermission },
      }),
    });
  });
}

// ============================================
// 数据资源相关 Mock
// ============================================

/**
 * Mock 数据集列表 API
 */
export function mockDatasetList(page: Page, datasets: any[] = []) {
  page.route('**/api/v1/datasets**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: {
          datasets,
          total: datasets.length,
        },
      }),
    });
  });
}

/**
 * Mock 工作流列表 API
 */
export function mockWorkflowList(page: Page, workflows: any[] = []) {
  page.route('**/api/v1/workflows**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: {
          workflows,
          total: workflows.length,
        },
      }),
    });
  });
}

// ============================================
// 通用 Mock 工具
// ============================================

/**
 * Mock API 延迟
 */
export function mockApiDelay(page: Page, pattern: string, delayMs: number = 1000) {
  page.route(pattern, async (route) => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}

/**
 * Mock API 错误
 */
export function mockApiError(page: Page, pattern: string, statusCode: number = 500) {
  page.route(pattern, async (route) => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({
        code: statusCode,
        message: 'API 错误',
      }),
    });
  });
}

/**
 * Mock API 超时
 */
export function mockApiTimeout(page: Page, pattern: string) {
  page.route(pattern, async () => {
    // 不响应，导致超时
  });
}

/**
 * Mock 通用成功响应
 */
export function mockApiSuccess(page: Page, pattern: string, data?: any) {
  page.route(pattern, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data,
      }),
    });
  });
}

/**
 * Mock 通用失败响应
 */
export function mockApiFailure(page: Page, pattern: string, message: string = '操作失败') {
  page.route(pattern, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 1,
        message,
      }),
    });
  });
}

// ============================================
// 场景 Mock 组合
// ============================================

/**
 * Mock 完整的用户管理场景
 */
export function mockUserManagementScenario(page: Page) {
  const mockUsers: MockUser[] = [
    {
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      roles: ['admin'],
      status: 'active',
      created_at: '2024-01-01T00:00:00Z',
      failed_login_count: 0,
      login_count: 10,
    },
    {
      id: '2',
      username: 'test_user',
      email: 'test@example.com',
      roles: ['user'],
      status: 'active',
      created_at: '2024-01-02T00:00:00Z',
      last_login_at: '2024-01-25T10:00:00Z',
      failed_login_count: 0,
      login_count: 5,
    },
  ];

  mockUserList(page, mockUsers);
  mockRoleList(page);
  mockCreateUser(page);
  mockDeleteUser(page);
  mockAssignRole(page);
}

/**
 * Mock 用户登录场景
 */
export function mockLoginScenario(page: Page, user?: MockUser) {
  mockLogin(page, true, user);

  // Mock 获取当前用户信息
  page.route('**/api/v1/user/info**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: user || {
          id: 'mock_user_id',
          username: 'mock_user',
          email: 'mock@example.com',
          roles: ['user'],
        },
      }),
    });
  });
}

/**
 * 清除所有 Mock
 */
export function clearMocks(page: Page) {
  page.unrouteAll();
}

// ============================================
// 导出
// ============================================

export const ApiMocks = {
  // 用户相关
  mockUserList,
  mockUserDetail,
  mockCreateUser,
  mockDeleteUser,
  mockAssignRole,

  // 认证相关
  mockLogin,
  mockLogout,

  // 角色权限
  mockRoleList,
  mockPermissionCheck,

  // 数据资源
  mockDatasetList,
  mockWorkflowList,

  // 通用工具
  mockApiDelay,
  mockApiError,
  mockApiTimeout,
  mockApiSuccess,
  mockApiFailure,

  // 场景组合
  mockUserManagementScenario,
  mockLoginScenario,
  clearMocks,
};
