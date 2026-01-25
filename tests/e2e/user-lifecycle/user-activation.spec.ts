/**
 * 用户激活阶段测试
 * 测试用户从 pending 状态到 active 状态的转换
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateTestUserData } from './helpers/user-management';
import { verifyUserLoggedIn, verifyUserStatus } from './helpers/verification';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('用户激活阶段', () => {
  test('新用户首次登录后状态应该变为 active', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('pending');

    // 模拟用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 验证用户已登录
    const isLoggedIn = await verifyUserLoggedIn(page);
    expect(isLoggedIn).toBe(true);

    // 验证用户状态已更新为 active
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });

  test('pending 状态用户应该可以登录', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    await userManager.createUser(userData);

    // 尝试登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 应该成功登录（首次登录会激活用户）
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');
  });

  test('inactive 状态用户被管理员重新激活后应该可以登录', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'inactive',
    });

    const user = await userManager.createUser(userData);
    expect(user.status).toBe('inactive');

    // 管理员激活用户
    await userManager.activateUser(user.id);

    // 用户尝试登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 应该成功登录
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');

    // 验证状态变为 active
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });

  test('激活后应该记录 last_login_at 时间', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);
    const beforeLogin = Date.now();

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 验证 last_login_at 已更新
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.last_login_at).toBeTruthy();

    if (updatedUser?.last_login_at) {
      const lastLoginTime = new Date(updatedUser.last_login_at).getTime();
      expect(lastLoginTime).toBeGreaterThanOrEqual(beforeLogin);
      expect(lastLoginTime).toBeLessThanOrEqual(Date.now() + 5000);
    }
  });

  test('激活后应该重置 failed_login_count', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);

    // 模拟一些登录失败
    await userManager.simulateFailedLogin(userData.username);
    await userManager.simulateFailedLogin(userData.username);

    // 验证有失败记录
    const userBefore = await userManager.getUser(user.id);
    expect(userBefore?.failed_login_count).toBeGreaterThan(0);

    // 激活用户
    await userManager.activateUser(user.id);

    // 验证 failed_login_count 已重置
    const userAfter = await userManager.getUser(user.id);
    expect(userAfter?.failed_login_count).toBe(0);
  });

  test('激活后 login_count 应该递增', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);
    const initialCount = user.login_count || 0;

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 验证 login_count 已递增
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.login_count).toBe(initialCount + 1);
  });

  test('首次登录应该记录登录 IP', async ({ userManager, page, request }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);

    // 用户登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');

    await page.waitForLoadState('networkidle');

    // 验证用户详情中记录了 IP（通过 API 获取）
    const response = await request.get(`${BASE_URL}/api/v1/users/${user.id}`);
    const json = await response.json();

    if (json.code === 0 && json.data) {
      // IP 可能在不同的字段中
      const hasIp = json.data.last_login_ip || json.data.login_ip || json.data.ip;
      expect(hasIp).toBeTruthy();
    }
  });

  test('多次登录应该持续更新 last_login_at', async ({ userManager, page }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 第一次登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    const firstLoginUser = await userManager.getUser(user.id);
    const firstLoginTime = firstLoginUser?.last_login_at;

    // 等待一段时间
    await page.waitForTimeout(2000);

    // 登出
    await page.click('.logout-button, button:has-text("退出"), button:has-text("登出")');
    await page.waitForTimeout(500);

    // 第二次登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"], input[name="email"]', userData.username);
    await page.fill('input[name="password"]', userData.password || 'Test1234!');
    await page.click('button:has-text("登录"), button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    const secondLoginUser = await userManager.getUser(user.id);
    const secondLoginTime = secondLoginUser?.last_login_at;

    expect(secondLoginTime).not.toBe(firstLoginTime);
  });

  test('管理员通过 UI 激活用户', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);

    // 导航到用户管理页面
    await adminPage.goto(`${BASE_URL}/admin/users`);
    await adminPage.waitForLoadState('networkidle');

    // 找到用户并点击激活按钮
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

    // 验证用户状态
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });

  test('通过 API 激活用户', async ({ userManager, request }) => {
    const userData = generateTestUserData({
      status: 'inactive',
    });

    const user = await userManager.createUser(userData);

    // 通过 API 激活
    const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/activate`);

    expect(response.ok()).toBeTruthy();

    const json = await response.json();
    expect(json.code).toBe(0);

    // 验证状态已更新
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });

  test('激活不存在的用户应该返回错误', async ({ request }) => {
    const fakeUserId = 'non-existent-user-id';

    const response = await request.post(`${BASE_URL}/api/v1/users/${fakeUserId}/activate`);

    expect(response.ok()).toBeFalsy();

    const json = await response.json();
    expect(json.code).not.toBe(0);
  });

  test('已激活用户再次激活应该不报错', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    // 再次激活已激活的用户
    await userManager.activateUser(user.id);

    // 应该保持 active 状态
    const updatedUser = await userManager.getUser(user.id);
    expect(updatedUser?.status).toBe('active');
  });
});
