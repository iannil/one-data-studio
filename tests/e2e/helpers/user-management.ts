/**
 * 用户管理辅助函数
 * 基于测试计划: docs/04-testing/user-lifecycle-test-cases.md
 *
 * 提供用户管理页面的导航、用户 CRUD 操作、角色分配等辅助函数
 */

import { Page, APIRequestContext, expect } from '@playwright/test';
import { TestRole, TestUser, UserStatus } from '../fixtures/user-lifecycle.fixture';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';

// ==================== 数据生成器 ====================

/**
 * 生成随机用户数据
 */
export function generateTestUserData(overrides?: Partial<TestUser>): TestUser {
  const timestamp = Date.now();
  const randomSuffix = Math.floor(Math.random() * 1000);

  return {
    user_id: `test_user_${timestamp}_${randomSuffix}`,
    username: `test_user_${timestamp}`,
    email: `test_user_${timestamp}@test.local`,
    password: 'Test1234!',
    roles: [TestRole.BUSINESS_USER],
    status: UserStatus.ACTIVE,
    ...overrides,
  };
}

/**
 * 生成指定角色的测试用户数据
 */
export function generateTestUserByRole(role: TestRole): TestUser {
  const timestamp = Date.now();
  const roleConfigs: Record<TestRole, Partial<TestUser>> = {
    [TestRole.DATA_ADMIN]: {
      username: `test_da_${timestamp}`,
      email: `test_da_${timestamp}@test.local`,
      password: 'Da1234!',
      roles: [TestRole.DATA_ADMIN],
    },
    [TestRole.DATA_ENGINEER]: {
      username: `test_de_${timestamp}`,
      email: `test_de_${timestamp}@test.local`,
      password: 'De1234!',
      roles: [TestRole.DATA_ENGINEER],
    },
    [TestRole.ALGORITHM_ENGINEER]: {
      username: `test_ae_${timestamp}`,
      email: `test_ae_${timestamp}@test.local`,
      password: 'Ae1234!',
      roles: [TestRole.ALGORITHM_ENGINEER],
    },
    [TestRole.BUSINESS_USER]: {
      username: `test_bu_${timestamp}`,
      email: `test_bu_${timestamp}@test.local`,
      password: 'Bu1234!',
      roles: [TestRole.BUSINESS_USER],
    },
    [TestRole.SYSTEM_ADMIN]: {
      username: `test_sa_${timestamp}`,
      email: `test_sa_${timestamp}@test.local`,
      password: 'Sa1234!',
      roles: [TestRole.SYSTEM_ADMIN],
    },
  };

  return {
    user_id: `test_${role}_${timestamp}`,
    status: UserStatus.ACTIVE,
    ...roleConfigs[role],
  };
}

// ==================== 导航辅助函数 ====================

/**
 * 导航到用户管理页面
 */
export async function navigateToUserManagement(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');
}

/**
 * 导航到角色管理页面
 */
export async function navigateToRoleManagement(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/roles`);
  await page.waitForLoadState('networkidle');
}

/**
 * 导航到权限管理页面
 */
export async function navigateToPermissionManagement(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/permissions`);
  await page.waitForLoadState('networkidle');
}

/**
 * 导航到审计日志页面
 */
export async function navigateToAuditLogs(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/audit`);
  await page.waitForLoadState('networkidle');
}

// ==================== API 辅助函数 ====================

/**
 * 设置认证令牌到请求头
 */
function getAuthHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

/**
 * 通过 API 创建用户
 */
export async function createUserViaApi(
  request: APIRequestContext,
  userData: TestUser,
  adminToken: string
): Promise<{ success: boolean; userId?: string; error?: string }> {
  const response = await request.post(`${API_BASE}/api/v1/users`, {
    headers: getAuthHeaders(adminToken),
    data: {
      username: userData.username,
      email: userData.email,
      password: userData.password,
      roles: userData.roles,
    },
  });

  const json = await response.json();

  if (response.ok() && json.code === 0) {
    return {
      success: true,
      userId: json.data?.user_id || userData.user_id,
    };
  }

  return {
    success: false,
    error: json.message || '创建用户失败',
  };
}

/**
 * 通过 API 删除用户
 */
export async function deleteUserViaApi(
  request: APIRequestContext,
  userId: string,
  adminToken: string
): Promise<boolean> {
  const response = await request.delete(`${API_BASE}/api/v1/users/${userId}`, {
    headers: getAuthHeaders(adminToken),
  });

  const json = await response.json();
  return response.ok() && json.code === 0;
}

/**
 * 通过 API 更新用户状态
 */
export async function updateUserStatusViaApi(
  request: APIRequestContext,
  userId: string,
  status: UserStatus,
  adminToken: string
): Promise<boolean> {
  const response = await request.patch(`${API_BASE}/api/v1/users/${userId}/status`, {
    headers: getAuthHeaders(adminToken),
    data: { status },
  });

  const json = await response.json();
  return response.ok() && json.code === 0;
}

/**
 * 通过 API 分配角色给用户
 */
export async function assignRoleViaApi(
  request: APIRequestContext,
  userId: string,
  role: TestRole,
  adminToken: string
): Promise<boolean> {
  const response = await request.post(`${API_BASE}/api/v1/users/${userId}/roles`, {
    headers: getAuthHeaders(adminToken),
    data: { role },
  });

  const json = await response.json();
  return response.ok() && json.code === 0;
}

/**
 * 通过 API 移除用户角色
 */
export async function removeRoleViaApi(
  request: APIRequestContext,
  userId: string,
  role: TestRole,
  adminToken: string
): Promise<boolean> {
  const response = await request.delete(
    `${API_BASE}/api/v1/users/${userId}/roles/${role}`,
    { headers: getAuthHeaders(adminToken) }
  );

  const json = await response.json();
  return response.ok() && json.code === 0;
}

/**
 * 通过 API 获取用户信息
 */
export async function getUserViaApi(
  request: APIRequestContext,
  userId: string,
  adminToken: string
): Promise<TestUser | null> {
  const response = await request.get(`${API_BASE}/api/v1/users/${userId}`, {
    headers: getAuthHeaders(adminToken),
  });

  const json = await response.json();

  if (response.ok() && json.code === 0 && json.data) {
    return {
      user_id: json.data.user_id,
      username: json.data.username,
      email: json.data.email,
      password: '',
      roles: json.data.roles || [],
      status: json.data.status || UserStatus.ACTIVE,
    };
  }

  return null;
}

/**
 * 用户登录获取令牌
 */
export async function loginUser(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<string | null> {
  const response = await request.post(`${API_BASE}/api/v1/auth/login`, {
    headers: { 'Content-Type': 'application/json' },
    data: { username, password },
  });

  const json = await response.json();

  if (response.ok() && json.code === 0) {
    return json.data?.token || null;
  }

  return null;
}

// ==================== 页面操作辅助函数 ====================

/**
 * 在用户管理页面点击新增用户按钮
 */
export async function clickAddUserButton(page: Page): Promise<void> {
  await page.click('[data-testid="add-user-button"], button:has-text("新增用户"), button:has-text("添加用户")');
}

/**
 * 填写用户表单
 */
export async function fillUserForm(
  page: Page,
  userData: Partial<TestUser>
): Promise<void> {
  if (userData.username) {
    await page.fill('[data-testid="username-input"], input[name="username"]', userData.username);
  }

  if (userData.email) {
    await page.fill('[data-testid="email-input"], input[name="email"]', userData.email);
  }

  if (userData.password) {
    await page.fill('[data-testid="password-input"], input[name="password"]', userData.password);
  }

  // 角色选择（如果提供）
  if (userData.roles && userData.roles.length > 0) {
    for (const role of userData.roles) {
      const roleCheckbox = page.locator(
        `[data-testid="role-${role}"], input[type="checkbox"][value="${role}"]`
      );
      await roleCheckbox.check();
    }
  }
}

/**
 * 提交用户表单
 */
export async function submitUserForm(page: Page): Promise<void> {
  await page.click('[data-testid="submit-button"], button:has-text("保存"), button:has-text("提交")');
}

/**
 * 搜索用户
 */
export async function searchUser(page: Page, keyword: string): Promise<void> {
  const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="搜索"]');
  await searchInput.fill(keyword);
  await searchInput.press('Enter');
}

/**
 * 点击用户行
 */
export async function clickUserRow(page: Page, username: string): Promise<void> {
  await page.click(`tr:has-text("${username}")`);
}

/**
 * 点击编辑用户按钮
 */
export async function clickEditUserButton(page: Page): Promise<void> {
  await page.click('[data-testid="edit-user-button"], button:has-text("编辑")');
}

/**
 * 点击删除用户按钮
 */
export async function clickDeleteUserButton(page: Page): Promise<void> {
  await page.click('[data-testid="delete-user-button"], button:has-text("删除")');
}

/**
 * 确认删除对话框
 */
export async function confirmDeleteDialog(page: Page): Promise<void> {
  await page.click('[data-testid="confirm-delete"], button:has-text("确认"), button:has-text("确定")');
}

/**
 * 取消删除对话框
 */
export async function cancelDeleteDialog(page: Page): Promise<void> {
  await page.click('[data-testid="cancel-delete"], button:has-text("取消")');
}

/**
 * 点击用户状态切换按钮
 */
export async function toggleUserStatus(page: Page, userId: string): Promise<void> {
  await page.click(`[data-testid="toggle-status-${userId}"], [data-user-id="${userId}"] .status-toggle`);
}

/**
 * 选择角色
 */
export async function selectRole(page: Page, role: TestRole): Promise<void> {
  const roleLabel = page.locator(`label:has-text("${role}")`);
  await roleLabel.click();
}

// ==================== 断言辅助函数 ====================

/**
 * 验证用户创建成功
 */
export async function assertUserCreated(page: Page, username: string): Promise<void> {
  await expect(page.locator(`tr:has-text("${username}")`)).toBeVisible();
  await expect(page.locator('.toast-message, .notification:has-text("创建成功")')).toBeVisible();
}

/**
 * 验证用户删除成功
 */
export async function assertUserDeleted(page: Page, username: string): Promise<void> {
  await expect(page.locator(`tr:has-text("${username}")`)).not.toBeVisible();
}

/**
 * 验证用户状态已更新
 */
export async function assertUserStatusUpdated(
  page: Page,
  userId: string,
  expectedStatus: UserStatus
): Promise<void> {
  const statusElement = page.locator(
    `[data-user-id="${userId}"] [data-testid="user-status"], [data-user-id="${userId}"] .status-badge`
  );
  await expect(statusElement).toHaveText(expectedStatus);
}

/**
 * 验证角色已分配
 */
export async function assertRoleAssigned(page: Page, userId: string, role: TestRole): Promise<void> {
  const roleBadge = page.locator(
    `[data-user-id="${userId}"] [data-testid="role-badge-${role}"], [data-user-id="${userId}"] .role:has-text("${role}")`
  );
  await expect(roleBadge).toBeVisible();
}

/**
 * 验证表单错误消息
 */
export async function assertFormFieldError(
  page: Page,
  field: string,
  expectedMessage: string
): Promise<void> {
  const errorElement = page.locator(
    `[data-testid="${field}-error"], input[name="${field}"] + .error-message`
  );
  await expect(errorElement).toHaveText(expectedMessage);
}

/**
 * 验证权限错误提示
 */
export async function assertPermissionDenied(page: Page): Promise<void> {
  await expect(page.locator('.error-message:has-text("权限不足"), .toast:has-text("无权限")')).toBeVisible();
}

// ==================== 批量操作 ====================

/**
 * 批量创建测试用户
 */
export async function createTestUsers(
  request: APIRequestContext,
  roles: TestRole[],
  adminToken: string
): Promise<TestUser[]> {
  const createdUsers: TestUser[] = [];

  for (const role of roles) {
    const userData = generateTestUserByRole(role);
    const result = await createUserViaApi(request, userData, adminToken);

    if (result.success) {
      createdUsers.push({ ...userData, user_id: result.userId || userData.user_id });
    }
  }

  return createdUsers;
}

/**
 * 批量清理测试用户
 */
export async function cleanupTestUsers(
  request: APIRequestContext,
  userIds: string[],
  adminToken: string
): Promise<void> {
  for (const userId of userIds) {
    await deleteUserViaApi(request, userId, adminToken);
  }
}

/**
 * 清理所有测试用户（用户名以 test_ 开头）
 */
export async function cleanupAllTestUsers(
  request: APIRequestContext,
  adminToken: string
): Promise<void> {
  const response = await request.get(`${API_BASE}/api/v1/users?username_prefix=test_`, {
    headers: getAuthHeaders(adminToken),
  });

  const json = await response.json();

  if (response.ok() && json.code === 0 && Array.isArray(json.data)) {
    for (const user of json.data) {
      await deleteUserViaApi(request, user.user_id, adminToken);
    }
  }
}
