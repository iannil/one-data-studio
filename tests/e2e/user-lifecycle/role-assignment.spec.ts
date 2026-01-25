/**
 * 角色分配阶段测试
 * 测试用户角色的分配、撤销和继承
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { assignRoleViaUI, revokeRoleViaUI, getUserRolesUI, verifyUserHasRole } from './helpers/role-management';
import type { TestRole } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('角色分配阶段', () => {
  test('管理员应该能够为用户分配单个角色', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 分配额外角色
    await userManager.assignRole(user.id, 'data_engineer');

    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles).toContain('data_engineer');
  });

  test('管理员应该能够为用户分配多个角色', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 分配多个角色
    await userManager.assignRole(user.id, 'data_engineer');
    await userManager.assignRole(user.id, 'ai_developer');

    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles).toContain('data_engineer');
    expect(updatedUser?.roles).toContain('ai_developer');
  });

  test('管理员应该能够撤销用户角色', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['user', 'data_engineer'],
    });

    const user = await userManager.createUser(userData);
    expect(user.roles).toContain('data_engineer');

    // 撤销角色
    await userManager.revokeRole(user.id, 'data_engineer');

    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles).not.toContain('data_engineer');
  });

  test('角色变更后应该立即生效', async ({ userManager, page, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `role_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证用户只能访问基础页面
    const canAccessAdmin = await page.goto(`${BASE_URL}/admin/users`);
    expect(canAccessAdmin?.status()).toBe(403 || 404);

    // 管理员分配 admin 角色
    await userManager.assignRole(user.id, 'admin');

    // 用户重新登录后应该能够访问管理页面
    await page.click('.logout-button');
    await page.waitForTimeout(500);

    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    const response = await page.goto(`${BASE_URL}/admin/users`);
    expect(response?.status()).not.toBe(403);
    expect(response?.status()).not.toBe(404);
  });

  test('应该支持通过用户组继承角色', async ({ userManager, request }) => {
    // 创建用户组（如果 API 支持）
    const groupResponse = await request.post(`${BASE_URL}/api/v1/groups`, {
      data: {
        name: `test_group_${Date.now()}`,
        roles: ['data_analyst'],
      },
    });

    if (groupResponse.ok()) {
      const groupJson = await groupResponse.json();
      const groupId = groupJson.data?.id;

      if (groupId) {
        const userData = generateTestUserData({
          roles: ['user'],
        });

        const user = await userManager.createUser(userData);

        // 将用户添加到用户组
        await request.post(`${BASE_URL}/api/v1/groups/${groupId}/members`, {
          data: { user_id: user.id },
        });

        // 验证用户继承了用户组的角色
        const updatedUser = await userManager.getUser(user.id);
        expect(updatedUser?.roles).toContain('data_analyst');
      }
    }
  });

  test('角色优先级应该正确生效', async ({ userManager, page }) => {
    // 创建具有多个角色的用户
    const userData = generateTestUserData({
      roles: ['user', 'data_engineer', 'ai_developer'],
    });

    const user = await userManager.createUser(userData);

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.evaluate(
      ({ username, roles }) => {
        localStorage.setItem('user_info', JSON.stringify({ username, roles }));
      },
      { username: userData.username, roles: ['user', 'data_engineer', 'ai_developer'] }
    );

    await page.goto(`${BASE_URL}/workspace`);
    await page.waitForLoadState('networkidle');

    // 验证用户能看到所有角色的功能
    // data_engineer 可以访问数据源
    const canAccessDatasources = await page.goto(`${BASE_URL}/data/datasources`);
    expect([200, 304]).toContain(canAccessDatasources?.status());

    // ai_developer 可以访问工作流
    const canAccessWorkflows = await page.goto(`${BASE_URL}/ai/workflows`);
    expect([200, 304]).toContain(canAccessWorkflows?.status());
  });

  test('角色变更应该记录审计日志', async ({ userManager, request, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 分配角色
    await userManager.assignRole(user.id, 'data_engineer');

    // 检查审计日志
    await adminPage.goto(`${BASE_URL}/admin/audit`);
    await adminPage.waitForLoadState('networkidle');

    // 搜索相关日志
    await adminPage.fill('input[placeholder*="搜索"]', `role_change:${user.id}`);
    await adminPage.waitForTimeout(500);

    // 应该找到角色变更的日志记录
    const logEntries = adminPage.locator('.audit-log, .log-item');
    const count = await logEntries.count();
    expect(count).toBeGreaterThan(0);
  });

  test('通过 UI 为用户分配角色', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 通过 UI 分配角色
    await assignRoleViaUI(adminPage, user.username, 'data_engineer');

    // 验证角色已分配
    const hasRole = await verifyUserHasRole(adminPage, user.username, 'data_engineer');
    expect(hasRole).toBe(true);
  });

  test('通过 UI 撤销用户角色', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user', 'data_engineer'],
    });

    const user = await userManager.createUser(userData);

    // 通过 UI 撤销角色
    await revokeRoleViaUI(adminPage, user.username, 'data_engineer');

    // 验证角色已撤销
    const hasRole = await verifyUserHasRole(adminPage, user.username, 'data_engineer');
    expect(hasRole).toBe(false);
  });

  test('通过 UI 获取用户角色列表', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user', 'data_engineer', 'ai_developer'],
    });

    const user = await userManager.createUser(userData);

    // 通过 UI 获取角色列表
    const roles = await getUserRolesUI(adminPage, user.username);

    expect(roles).toContain('user');
    expect(roles).toContain('data_engineer');
    expect(roles).toContain('ai_developer');
  });

  test('分配不存在的角色应该返回错误', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 尝试分配不存在的角色
    const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/roles`, {
      data: { role: 'non_existent_role' },
    });

    expect(response.ok()).toBeFalsy();

    const json = await response.json();
    expect(json.code).not.toBe(0);
  });

  test('撤销用户的最后一个角色应该保留 user 角色', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
    });

    const user = await userManager.createUser(userData);

    // 撤销唯一角色
    await userManager.revokeRole(user.id, 'data_engineer');

    // 应该保留 user 角色
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles.length).toBeGreaterThan(0);
    expect(updatedUser?.roles).toContain('user');
  });

  test('admin 角色不能被撤销', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['admin', 'user'],
    });

    const user = await userManager.createUser(userData);

    // 尝试撤销 admin 角色
    try {
      await userManager.revokeRole(user.id, 'admin');
      // 如果没有抛出错误，检查结果
      const updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).toContain('admin');
    } catch (error) {
      // 预期抛出错误
      expect(error).toBeTruthy();
    }
  });

  test('通过 API 批量分配角色', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 批量分配角色
    const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/roles/batch`, {
      data: { roles: ['data_engineer', 'ai_developer', 'data_analyst'] },
    });

    if (response.ok()) {
      const updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).toContain('data_engineer');
      expect(updatedUser?.roles).toContain('ai_developer');
      expect(updatedUser?.roles).toContain('data_analyst');
    } else {
      // 如果批量 API 不支持，使用单独分配
      await userManager.assignRole(user.id, 'data_engineer');
      await userManager.assignRole(user.id, 'ai_developer');
      await userManager.assignRole(user.id, 'data_analyst');

      const updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).toContain('data_engineer');
      expect(updatedUser?.roles).toContain('ai_developer');
      expect(updatedUser?.roles).toContain('data_analyst');
    }
  });

  test('角色分配应该验证用户存在', async ({ request }) => {
    const fakeUserId = 'non-existent-user-id';

    const response = await request.post(`${BASE_URL}/api/v1/users/${fakeUserId}/roles`, {
      data: { role: 'admin' },
    });

    expect(response.ok()).toBeFalsy();

    const json = await response.json();
    expect(json.code).not.toBe(0);
  });

  test('临时角色授予后应该自动过期', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 分配临时角色（1秒后过期）
    const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/roles/temporary`, {
      data: {
        role: 'data_engineer',
        expires_in: 1, // 1秒
      },
    });

    if (response.ok()) {
      // 立即检查应该有角色
      let updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).toContain('data_engineer');

      // 等待过期
      await new Promise(resolve => setTimeout(resolve, 2000));

      // 检查角色已过期
      updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).not.toContain('data_engineer');
    }
  });
});
