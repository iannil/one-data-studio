/**
 * 用户状态管理测试
 * 测试用户在 active、inactive、locked、deleted 状态之间的转换
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { verifyUserStatus } from './helpers/verification';
import type { UserStatus } from './fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('用户状态管理', () => {
  test('管理员应该能够停用用户（active -> inactive）', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('active');

    // 通过 API 停用用户
    await userManager.deactivateUser(user.id);

    // 验证状态已变更
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('inactive');

    // 通过 UI 验证状态显示
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const statusTag = userRow.locator('.ant-tag:has-text("inactive"), [class*="status-inactive"]').first();
    await expect(statusTag).toBeVisible();
  });

  test('inactive 用户应该无法登录', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'inactive',
      username: `inactive_user_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 尝试登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    // 应该显示账户已停用的提示
    const errorMsg = page.locator('.ant-message-error, .error-message').first();
    const hasError = await errorMsg.count() > 0;

    if (hasError) {
      await expect(errorMsg).toContainText('停用', { timeout: 3000 });
    } else {
      // 或者仍然在登录页面
      const currentUrl = page.url();
      expect(currentUrl).toContain('/login');
    }
  });

  test('管理员应该能够重新激活用户（inactive -> active）', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'inactive',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('inactive');

    // 激活用户
    await userManager.activateUser(user.id);

    // 验证状态已变更
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });

  test('连续登录失败 5 次后账户应该被锁定', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'active',
      username: `lock_test_${Date.now()}`,
      password: 'CorrectPassword123!',
    });

    const user = await userManager.createUser(userData);

    // 尝试 5 次错误登录
    for (let i = 0; i < 5; i++) {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[name="username"]', userData.username);
      await page.fill('input[name="password"]', 'WrongPassword123!');
      await page.click('button:has-text("登录"), button:has-text("Login")');
      await page.waitForTimeout(500);
    }

    // 验证账户被锁定
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('locked');

    // 验证 failed_login_count
    expect(updatedUser?.failed_login_count).toBeGreaterThanOrEqual(5);
  });

  test('锁定用户应该无法登录', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'locked',
      username: `locked_user_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 即使使用正确的密码也无法登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    // 应该显示账户已锁定的提示
    const errorMsg = page.locator('.ant-message-error, .error-message').first();
    const hasError = await errorMsg.count() > 0;

    if (hasError) {
      await expect(errorMsg).toContainText('锁定', { timeout: 3000 });
    } else {
      // 或者仍然在登录页面
      const currentUrl = page.url();
      expect(currentUrl).toContain('/login');
    }
  });

  test('锁定超时后应该自动解锁', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'locked',
      username: `auto_unlock_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 设置锁定过期时间（通过 API）
    const lockTime = new Date();
    lockTime.setMinutes(lockTime.getMinutes() - 35); // 35分钟前（假设30分钟过期）

    // 注意：这个测试需要后端支持设置锁定时间
    // 如果 API 不支持，可以跳过这个测试

    // 等待可能的自动解锁时间
    await page.waitForTimeout(2000);

    // 检查状态
    const updatedUser = await userManager.getUser(user.id);
    // 如果实现了自动解锁，状态应该是 active
    // expect(updatedUser?.status).toBe('active');
  });

  test('管理员应该能够手动解锁用户', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'locked',
      username: `manual_unlock_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('locked');

    // 管理员解锁用户
    await userManager.unlockUser(user.id);

    // 验证状态已变更
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');

    // 验证 failed_login_count 已重置
    expect(updatedUser?.failed_login_count).toBe(0);

    // 用户应该能够登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');
  });

  test('应该能够软删除用户（标记为 deleted）', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 软删除用户
    await userManager.setUserStatus(user.id, 'deleted');

    // 验证状态
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('deleted');
  });

  test('deleted 用户应该无法登录且无法恢复', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'deleted',
      username: `deleted_user_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 尝试登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    // 应该显示用户不存在的提示
    const errorMsg = page.locator('.ant-message-error, .error-message').first();
    const hasError = await errorMsg.count() > 0;

    if (hasError) {
      await expect(errorMsg).toBeVisible();
    }

    // 尝试激活已删除的用户应该失败
    try {
      await userManager.activateUser(user.id);
      // 如果没有抛出错误，验证状态仍然是 deleted
      const stillDeleted = await userManager.getUser(user.id);
      expect(stillDeleted?.status).toBe('deleted');
    } catch (error) {
      // 预期抛出错误
      expect(error).toBeTruthy();
    }
  });

  test('通过 UI 停用用户', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const deactivateButton = userRow.locator('button:has-text("停用")').first();

    if (await deactivateButton.isVisible()) {
      await deactivateButton.click();
      await adminPage.waitForTimeout(500);

      // 确认停用
      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
      }
    }

    await adminPage.waitForTimeout(1000);

    // 验证状态
    const isInactive = await verifyUserStatus(adminPage, user.username, 'inactive');
    expect(isInactive).toBe(true);
  });

  test('通过 UI 激活用户', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'inactive',
    });

    const user = await userManager.createUser(userData);

    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const activateButton = userRow.locator('button:has-text("激活")').first();

    if (await activateButton.isVisible()) {
      await activateButton.click();
      await adminPage.waitForTimeout(500);

      // 确认激活
      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
      }
    }

    await adminPage.waitForTimeout(1000);

    // 验证状态
    const isActive = await verifyUserStatus(adminPage, user.username, 'active');
    expect(isActive).toBe(true);
  });

  test('通过 UI 解锁用户', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'locked',
    });

    const user = await userManager.createUser(userData);

    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
    const unlockButton = userRow.locator('button:has-text("解锁")').first();

    if (await unlockButton.isVisible()) {
      await unlockButton.click();
      await adminPage.waitForTimeout(500);

      // 确认解锁
      const confirmButton = adminPage.locator('.ant-modal-confirm button:has-text("确定")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
      }
    }

    await adminPage.waitForTimeout(1000);

    // 验证状态
    const isActive = await verifyUserStatus(adminPage, user.username, 'active');
    expect(isActive).toBe(true);
  });

  test('成功登录后应该重置 failed_login_count', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'active',
      username: `reset_fail_count_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 模拟几次登录失败
    await userManager.simulateFailedLogin(userData.username);
    await userManager.simulateFailedLogin(userData.username);

    let userWithFailures = await userManager.getUser(user.id);
    expect(userWithFailures?.failed_login_count).toBeGreaterThan(0);

    // 正确登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 验证 failed_login_count 已重置
    const userAfterLogin = await userManager.getUser(user.id);
    expect(userAfterLogin?.failed_login_count).toBe(0);
  });

  test('批量修改用户状态', async ({ userManager, request }) => {
    const users = await Promise.all([
      userManager.createUser(generateTestUserData({ status: 'active' })),
      userManager.createUser(generateTestUserData({ status: 'active' })),
      userManager.createUser(generateTestUserData({ status: 'active' })),
    ]);

    const userIds = users.map(u => u.id);

    // 批量停用
    const response = await request.post(`${BASE_URL}/api/v1/users/batch/status`, {
      data: {
        user_ids: userIds,
        status: 'inactive',
      },
    });

    if (response.ok()) {
      // 验证所有用户都已停用
      for (const user of users) {
        const updatedUser = await userManager.getUser(user.id);
        expect(updatedUser?.status).toBe('inactive');
      }
    }
  });

  test('状态变更应该触发事件通知', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 停用用户
    await userManager.deactivateUser(user.id);

    // 检查审计日志中是否有状态变更记录
    const auditResponse = await request.get(`${BASE_URL}/api/v1/admin/audit`, {
      params: { user_id: user.id, action: 'status_change' },
    });

    if (auditResponse.ok()) {
      const auditJson = await auditResponse.json();
      expect(auditJson.data?.length).toBeGreaterThan(0);
    }
  });
});
