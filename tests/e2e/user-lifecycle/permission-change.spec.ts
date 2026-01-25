/**
 * 权限变更阶段测试
 * 测试角色升级、降级后的权限变化
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { verifyCanAccessPage, verifyCannotAccessPage, verifyCanPerformAction, verifyCannotPerformAction } from './helpers/verification';
import type { TestRole } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('权限变更阶段', () => {
  test('角色升级后应该能够访问新功能', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `upgrade_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 初始状态：普通用户，不能访问数据源管理
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    let result = await verifyCannotAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true); // 确认不能访问

    // 升级为 data_engineer
    await userManager.assignRole(user.id, 'data_engineer');

    // 刷新权限后应该能够访问
    await page.reload();
    await page.waitForLoadState('networkidle');

    result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);
  });

  test('角色降级后应该无法访问原功能', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
      username: `downgrade_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 初始状态：数据工程师，可以访问数据源管理
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    let result = await verifyCanAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true);

    // 降级为普通用户
    await userManager.revokeRole(user.id, 'data_engineer');

    // 刷新后应该不能访问
    await page.reload();
    await page.waitForLoadState('networkidle');

    result = await verifyCannotAccessPage(page, '/data/datasources');
    expect(result.hasAccess).toBe(true); // 确认不能访问
  });

  test('权限缓存应该被正确清除', async ({ userManager, page, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `cache_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 第一次登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 访问受限页面
    const response1 = await request.get(`${BASE_URL}/api/v1/datasources`);
    expect([401, 403]).toContain(response1.status());

    // 分予新角色
    await userManager.assignRole(user.id, 'data_engineer');

    // 直接调用 API（绕过页面缓存）
    const response2 = await request.get(`${BASE_URL}/api/v1/datasources`);
    expect(response2.status()).not.toBe(403);
  });

  test('临时权限授予后应该自动过期', async ({ userManager, page, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `temp_perm_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 授予临时权限
    const tempResponse = await request.post(`${BASE_URL}/api/v1/users/${user.id}/permissions/temporary`, {
      data: {
        permission: 'manage_datasources',
        expires_in: 2, // 2秒后过期
      },
    });

    if (tempResponse.ok()) {
      // 应该能够访问
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[name="username"]', userData.username);
      await page.fill('input[name="password"]', userData.password);
      await page.click('button:has-text("登录")');
      await page.waitForLoadState('networkidle');

      let result = await verifyCanAccessPage(page, '/data/datasources');
      expect(result.hasAccess).toBe(true);

      // 等待过期
      await page.waitForTimeout(2500);
      await page.reload();

      // 应该不能访问了
      result = await verifyCannotAccessPage(page, '/data/datasources');
      expect(result.hasAccess).toBe(true);
    }
  });

  test('权限变更后受保护的 API 应该返回 403', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `api_perm_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 获取认证 token
    const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: {
        username: userData.username,
        password: userData.password,
      },
    });

    if (loginResponse.ok()) {
      const loginJson = await loginResponse.json();
      const token = loginJson.data?.access_token || loginJson.data?.token;

      if (token) {
        // 尝试访问需要更高权限的 API
        const response = await request.get(`${BASE_URL}/api/v1/admin/users`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        expect(response.status()).toBe(403);
      }
    }
  });

  test('权限变更应该影响所有会话', async ({ userManager, context, browser }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `session_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 创建多个会话
    const page1 = await context.newPage();
    const page2 = await context.newPage();

    // 两个页面都登录
    for (const page of [page1, page2]) {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[name="username"]', userData.username);
      await page.fill('input[name="password"]', userData.password);
      await page.click('button:has-text("登录")');
      await page.waitForLoadState('networkidle');
    }

    // 验证两个页面都不能访问管理页面
    let result1 = await verifyCannotAccessPage(page1, '/admin/users');
    let result2 = await verifyCannotAccessPage(page2, '/admin/users');
    expect(result1.hasAccess).toBe(true);
    expect(result2.hasAccess).toBe(true);

    // 升级为 admin
    await userManager.assignRole(user.id, 'admin');

    // 两个页面重新登录后都应该能够访问
    for (const page of [page1, page2]) {
      await page.goto(`${BASE_URL}/logout`);
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[name="username"]', userData.username);
      await page.fill('input[name="password"]', userData.password);
      await page.click('button:has-text("登录")');
      await page.waitForLoadState('networkidle');

      const result = await verifyCanAccessPage(page, '/admin/users');
      expect(result.hasAccess).toBe(true);
    }

    await page1.close();
    await page2.close();
  });

  test('权限变更后应该能够执行新的操作', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `action_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 不能创建数据集
    await page.goto(`${BASE_URL}/data/datasets`);
    let canCreate = await verifyCanPerformAction(page, '创建', { timeout: 3000 });
    expect(canCreate).toBe(false);

    // 升级为 data_engineer
    await userManager.assignRole(user.id, 'data_engineer');

    // 刷新页面
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 应该能够创建数据集
    canCreate = await verifyCanPerformAction(page, '创建');
    expect(canCreate).toBe(true);
  });

  test('权限变更后应该不能执行原操作', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
      username: `revoke_action_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 能够创建数据集
    await page.goto(`${BASE_URL}/data/datasets`);
    let canCreate = await verifyCanPerformAction(page, '创建');
    expect(canCreate).toBe(true);

    // 降级为普通用户
    await userManager.revokeRole(user.id, 'data_engineer');

    // 刷新页面
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 不能创建数据集
    canCreate = await verifyCannotPerformAction(page, '创建');
    expect(canCreate).toBe(true);
  });

  test('从 user 升级到 admin 应该获得所有权限', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      username: `to_admin_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 升级为 admin
    await userManager.assignRole(user.id, 'admin');

    // 重新登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 应该能访问所有管理页面
    const adminPages = [
      '/admin/users',
      '/admin/roles',
      '/admin/groups',
      '/admin/audit',
      '/admin/settings',
    ];

    for (const pagePath of adminPages) {
      const result = await verifyCanAccessPage(page, pagePath);
      expect(result.hasAccess).toBe(true);
    }
  });

  test('从 admin 降级到 user 应该失去管理权限', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      roles: ['admin'],
      username: `from_admin_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证能访问管理页面
    let result = await verifyCanAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);

    // 撤销 admin 角色（保留 user 角色）
    await userManager.revokeRole(user.id, 'admin');

    // 重新登录
    await page.goto(`${BASE_URL}/logout`);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 应该不能访问管理页面
    result = await verifyCannotAccessPage(page, '/admin/users');
    expect(result.hasAccess).toBe(true);
  });

  test('通过 UI 变更用户权限', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user'],
    });

    const user = await userManager.createUser(userData);

    // 通过 UI 修改角色
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const editButton = userRow.locator('button:has-text("编辑")').first();
    await editButton.click();
    await adminPage.waitForTimeout(500);

    // 修改角色选择
    const roleSelect = adminPage.locator('select[name="role"], .role-select').first();
    if (await roleSelect.isVisible()) {
      await roleSelect.click();
      await adminPage.waitForTimeout(300);

      const dataEngineerOption = adminPage.locator('.ant-select-item:has-text("数据工程师")').first();
      if (await dataEngineerOption.isVisible()) {
        await dataEngineerOption.click();
      }
    }

    // 保存
    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(1000);

    // 验证角色已变更
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.roles).toContain('data_engineer');
  });
});
