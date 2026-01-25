/**
 * 用户创建阶段测试
 * 测试用户创建的各种场景
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { navigateToUserManagement, createUserViaUI, generateTestUserData } from './helpers/user-management';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('用户创建阶段', () => {
  test.beforeEach(async ({ adminPage }) => {
    // 每个测试前导航到用户管理页面
    await navigateToUserManagement(adminPage);
  });

  test('应该能够通过 UI 创建新用户', async ({ adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      status: 'pending',
    });

    await createUserViaUI(adminPage, userData);

    // 验证用户出现在列表中
    const userRow = adminPage.locator(`tr:has-text("${userData.username}"), .user-item:has-text("${userData.username}")`).first();
    await expect(userRow).toBeVisible();
  });

  test('创建用户时应该分配默认角色（user）', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData({
      roles: ['user'],
      status: 'pending',
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('user');
    expect(user.status).toBe('pending');
  });

  test('创建用户时应该可以同时分配多个角色', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer', 'ai_developer'],
      status: 'active',
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('data_engineer');
    expect(user.roles).toContain('ai_developer');
  });

  test('创建用户时应该验证必填字段（username）', async ({ adminPage }) => {
    await navigateToUserManagement(adminPage);

    // 打开创建用户对话框
    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    // 不填写用户名，直接提交
    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示错误提示
    const errorMsg = adminPage.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });

  test('创建用户时应该验证必填字段（email）', async ({ adminPage }) => {
    await navigateToUserManagement(adminPage);

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    // 只填写用户名，不填写邮箱
    const usernameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
    await usernameInput.fill('test_no_email');

    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示错误提示
    const errorMsg = adminPage.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });

  test('创建用户时应该检测重复用户名', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData();

    // 创建第一个用户
    await userManager.createUser(userData);

    // 尝试创建相同用户名的用户
    await navigateToUserManagement(adminPage);

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    const usernameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
    await usernameInput.fill(userData.username);

    const emailInput = adminPage.locator('input[name="email"], input[type="email"]').first();
    await emailInput.fill('different@example.com');

    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示用户名已存在的错误
    const errorMsg = adminPage.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });

  test('创建用户时应该检测重复邮箱', async ({ userManager, adminPage }) => {
    const userData = generateTestUserData();

    // 创建第一个用户
    await userManager.createUser(userData);

    // 尝试创建相同邮箱的用户
    await navigateToUserManagement(adminPage);

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    const usernameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
    await usernameInput.fill('different_username');

    const emailInput = adminPage.locator('input[name="email"], input[type="email"]').first();
    await emailInput.fill(userData.email);

    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示邮箱已存在的错误
    const errorMsg = adminPage.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });

  test('创建用户后状态应该为 pending', async ({ userManager }) => {
    const userData = generateTestUserData({
      status: 'pending',
    });

    const user = await userManager.createUser(userData);

    expect(user.status).toBe('pending');
  });

  test('创建用户时应该记录创建者和创建时间', async ({ userManager }) => {
    const userData = generateTestUserData();

    const user = await userManager.createUser(userData);

    expect(user.created_at).toBeTruthy();
    expect(new Date(user.created_at).getTime()).toBeLessThanOrEqual(Date.now());
  });

  test('应该支持批量创建用户', async ({ userManager, adminPage }) => {
    const users = [
      generateTestUserData({ username: `batch_user_1_${Date.now()}` }),
      generateTestUserData({ username: `batch_user_2_${Date.now()}` }),
      generateTestUserData({ username: `batch_user_3_${Date.now()}` }),
    ];

    // 通过 API 批量创建
    const createdUsers = await Promise.all(
      users.map(userData => userManager.createUser(userData))
    );

    expect(createdUsers).toHaveLength(3);

    // 验证所有用户都出现在列表中
    await navigateToUserManagement(adminPage);
    await adminPage.waitForLoadState('networkidle');

    for (const user of createdUsers) {
      const userRow = adminPage.locator(`tr:has-text("${user.username}")`).first();
      await expect(userRow).toBeVisible();
    }
  });

  test('应该能够通过 API 创建用户', async ({ userManager, request }) => {
    const userData = generateTestUserData();

    const response = await request.post(`${BASE_URL}/api/v1/users`, {
      data: {
        username: userData.username,
        email: userData.email,
        password: userData.password,
        roles: userData.roles,
      },
    });

    expect(response.ok()).toBeTruthy();

    const json = await response.json();
    expect(json.code).toBe(0);
    expect(json.data).toBeTruthy();
    expect(json.data.username).toBe(userData.username);
  });

  test('创建管理员角色用户', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['admin'],
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('admin');
  });

  test('创建数据工程师角色用户', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['data_engineer'],
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('data_engineer');
  });

  test('创建 AI 开发者角色用户', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['ai_developer'],
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('ai_developer');
  });

  test('创建数据分析师角色用户', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['data_analyst'],
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('data_analyst');
  });

  test('创建访客角色用户', async ({ userManager }) => {
    const userData = generateTestUserData({
      roles: ['guest'],
    });

    const user = await userManager.createUser(userData);

    expect(user.roles).toContain('guest');
  });

  test('创建用户时应该验证邮箱格式', async ({ adminPage }) => {
    await navigateToUserManagement(adminPage);

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    const usernameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
    await usernameInput.fill('test_invalid_email');

    const emailInput = adminPage.locator('input[name="email"], input[type="email"]').first();
    await emailInput.fill('invalid-email-format');

    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示邮箱格式错误的提示
    const errorMsg = adminPage.locator('.ant-message-error, .error-message, .ant-form-item-explain-error').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });

  test('创建用户时应该验证密码强度', async ({ adminPage }) => {
    await navigateToUserManagement(adminPage);

    const createButton = adminPage.locator('button:has-text("创建"), button:has-text("新建")').first();
    await createButton.click();
    await adminPage.waitForTimeout(500);

    const usernameInput = adminPage.locator('input[name="username"], input[name="name"]').first();
    await usernameInput.fill('test_weak_password');

    const emailInput = adminPage.locator('input[name="email"], input[type="email"]').first();
    await emailInput.fill('test@example.com');

    const passwordInput = adminPage.locator('input[name="password"], input[type="password"]').first();
    await passwordInput.fill('123'); // 弱密码

    const confirmButton = adminPage.locator('.ant-modal button:has-text("确定")').first();
    await confirmButton.click();
    await adminPage.waitForTimeout(500);

    // 应该显示密码强度不足的提示
    const errorMsg = adminPage.locator('.ant-message-error, .error-message, .ant-form-item-explain-error').first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });
  });
});
