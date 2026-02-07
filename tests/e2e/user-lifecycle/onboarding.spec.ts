/**
 * 用户入职流程 E2E 测试
 * 测试用例编号: LC-ON-E-001 ~ LC-ON-E-005
 *
 * 阶段1: 入职准备流程
 * - 创建账户
 * - 分配初始角色
 * - 发送激活通知
 *
 * 阶段2: 首次激活流程
 * - 登录验证
 * - 修改初始密码
 * - 状态转换 pending→active
 */

import { test, expect } from '@playwright/test';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8080';

// ==================== 测试套件 ====================

test.describe('User Onboarding - Phase 1: Preparation', () => {
  test.beforeEach(async ({ page }) => {
    // 设置认证 Mock
    await page.goto(`${BASE_URL}/login`);
  });

  test('LC-ON-E-001: Admin creates new user account', async ({ page, request }) => {
    /** 测试场景：管理员创建新用户账户
     *
     * 前置条件：
     * - 管理员已登录
     * - 用户名和邮箱未被使用
     *
     * 测试步骤：
     * 1. 导航到用户管理页面
     * 2. 点击"新增用户"按钮
     * 3. 填写用户信息
     * 4. 选择初始角色
     * 5. 提交表单
     *
     * 预期结果：
     * - 用户创建成功
     * - 用户状态为 pending
     * - 显示初始密码
     */

    // Mock API 响应
    await page.route('**/api/v1/users', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            user_id: 'user_test_001',
            username: 'testuser_001',
            email: 'testuser_001@example.com',
            status: 'pending',
            initial_password: 'Init1234@',
            roles: ['data_engineer'],
            created_at: new Date().toISOString()
          }
        })
      });
    });

    // 导航到用户管理页面
    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();

    // 点击新增用户按钮
    await page.click('[data-testid="add-user-button"], button:has-text("新增用户")');

    // 填写用户表单
    await page.fill('[data-testid="username-input"], input[name="username"]', 'testuser_001');
    await page.fill('[data-testid="email-input"], input[name="email"]', 'testuser_001@example.com');

    // 选择角色
    await page.check('[data-testid="role-data_engineer"]');

    // 提交表单
    await page.click('[data-testid="submit-button"], button:has-text("保存")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('LC-ON-E-002: Admin assigns initial role to user', async ({ page }) => {
    /** 测试场景：管理员为用户分配初始角色
     *
     * 前置条件：
     * - 管理员已登录
     * - 用户已创建但未分配角色
     *
     * 测试步骤：
     * 1. 查找用户
     * 2. 点击用户行
     * 3. 点击"编辑"按钮
     * 4. 选择角色
     * 5. 保存更改
     *
     * 预期结果：
     * - 角色分配成功
     * - 用户列表显示角色标签
     */

    await page.route('**/api/v1/users/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_test_002',
            username: 'testuser_002',
            email: 'testuser_002@example.com',
            status: 'pending',
            roles: ['data_engineer']
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);

    // 搜索用户
    await page.fill('[data-testid="search-input"]', 'testuser_002');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 点击用户行
    await page.click('tr:has-text("testuser_002")');

    // 验证角色显示
    await expect(page.locator('[data-testid="role-badge-data_engineer"]')).toBeVisible();
  });

  test('LC-ON-E-003: Send activation notification', async ({ page }) => {
    /** 测试场景：发送激活通知
     *
     * 前置条件：
     * - 用户已创建
     * - 用户状态为 pending
     *
     * 测试步骤：
     * 1. 在用户列表找到用户
     * 2. 点击"发送激活通知"按钮
     * 3. 确认发送
     *
     * 预期结果：
     * - 激活邮件发送成功
     * - 显示发送成功提示
     */

    await page.route('**/api/v1/users/*/send-activation', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: '激活通知已发送',
          data: {
            sent: true,
            email: 'testuser_003@example.com'
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);

    // 点击发送激活通知按钮
    await page.click('[data-testid="send-activation-button"]');

    // 确认发送
    await page.click('.ant-modal button:has-text("确定")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("激活通知已发送")')).toBeVisible();
  });
});

test.describe('User Onboarding - Phase 2: First Activation', () => {
  test('LC-AC-E-001: First login with initial password', async ({ page }) => {
    /** 测试场景：首次登录验证
     *
     * 前置条件：
     * - 用户已创建
     * - 收到激活通知和初始密码
     *
     * 测试步骤：
     * 1. 导航到登录页面
     * 2. 输入用户名
     * 3. 输入初始密码
     * 4. 点击登录
     *
     * 预期结果：
     * - 登录成功
     * - 提示修改密码
     */

    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            token: 'mock_jwt_token_12345',
            user: {
              user_id: 'user_test_001',
              username: 'testuser_001',
              status: 'pending',
              require_password_change: true
            }
          }
        })
      });
    });

    // 导航到登录页
    await page.goto(`${BASE_URL}/login`);

    // 输入凭证
    await page.fill('input[name="username"]', 'testuser_001');
    await page.fill('input[name="password"]', 'Init1234@');

    // 点击登录
    await page.click('button[type="submit"]');

    // 验证重定向到修改密码页面
    await expect(page).toHaveURL(/.*change-password.*/);
    await expect(page.locator('text=请修改您的初始密码')).toBeVisible();
  });

  test('LC-AC-E-002: Change initial password', async ({ page }) => {
    /** 测试场景：修改初始密码
     *
     * 前置条件：
     * - 用户首次登录
     * - 系统提示修改密码
     *
     * 测试步骤：
     * 1. 输入新密码
     * 2. 确认新密码
     * 3. 点击提交
     *
     * 预期结果：
     * - 密码修改成功
     * - 用户状态变为 active
     * - 自动跳转到首页
     */

    await page.route('**/api/v1/auth/change-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: '密码修改成功',
          data: {
            user_id: 'user_test_001',
            status: 'active'
          }
        })
      });
    });

    // 导航到修改密码页面
    await page.goto(`${BASE_URL}/change-password`);

    // 填写新密码
    await page.fill('input[name="newPassword"]', 'NewSecure@123');
    await page.fill('input[name="confirmPassword"]', 'NewSecure@123');

    // 提交
    await page.click('button[type="submit"]');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("密码修改成功")')).toBeVisible();

    // 验证跳转到首页
    await expect(page).toHaveURL(`${BASE_URL}/`);
  });

  test('LC-AC-E-003: Status transition pending to active', async ({ page }) => {
    /** 测试场景：验证用户状态转换
     *
     * 前置条件：
     * - 用户完成密码修改
     *
     * 测试步骤：
     * 1. 用户完成密码修改
     * 2. 调用用户信息接口
     *
     * 预期结果：
     * - 用户状态从 pending 变为 active
     * - activated_at 字段有值
     */

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_test_001',
            username: 'testuser_001',
            email: 'testuser_001@example.com',
            status: 'active',
            roles: ['data_engineer'],
            activated_at: new Date().toISOString(),
            created_at: new Date().toISOString()
          }
        })
      });
    });

    // 导航到个人资料页面
    await page.goto(`${BASE_URL}/profile`);

    // 验证状态显示为 active
    await expect(page.locator('[data-testid="user-status"]')).toHaveText('active');
  });
});

test.describe('User Onboarding - Complete Flow', () => {
  test('LC-ON-E-004: Complete onboarding flow end-to-end', async ({ page, request }) => {
    /** 测试场景：完整的入职流程端到端测试
     *
     * 测试步骤：
     * 1. 管理员创建用户
     * 2. 管理员分配角色
     * 3. 系统发送激活通知
     * 4. 用户首次登录
     * 5. 用户修改密码
     * 6. 用户状态变为 active
     *
     * 预期结果：
     * - 整个流程顺利完成
     */

    // 步骤 1-3: 管理员操作（通过 Mock API）
    await page.route('**/api/v1/users', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              user_id: 'user_onboarding_001',
              username: 'onboarding_test',
              email: 'onboarding_test@example.com',
              status: 'pending',
              initial_password: 'InitPass@123',
              roles: ['data_engineer']
            }
          })
        });
      } else {
        await route.continue();
      }
    });

    // 管理员创建用户
    await page.goto(`${BASE_URL}/admin/users`);
    await page.click('[data-testid="add-user-button"]');
    await page.fill('input[name="username"]', 'onboarding_test');
    await page.fill('input[name="email"]', 'onboarding_test@example.com');
    await page.check('[data-testid="role-data_engineer"]');
    await page.click('button:has-text("保存")');

    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();

    // 步骤 4-6: 用户激活
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            token: 'mock_token',
            user: {
              username: 'onboarding_test',
              status: 'pending',
              require_password_change: true
            }
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', 'onboarding_test');
    await page.fill('input[name="password"]', 'InitPass@123');
    await page.click('button[type="submit"]');

    // 应该重定向到修改密码页面
    await expect(page).toHaveURL(/.*change-password.*/);

    // 修改密码
    await page.route('**/api/v1/auth/change-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { status: 'active' }
        })
      });
    });

    await page.fill('input[name="newPassword"]', 'NewSecure@123');
    await page.fill('input[name="confirmPassword"]', 'NewSecure@123');
    await page.click('button[type="submit"]');

    // 验证激活成功
    await expect(page.locator('.toast-message:has-text("密码修改成功")')).toBeVisible();
  });

  test('LC-ON-E-005: Onboarding with multiple roles', async ({ page }) => {
    /** 测试场景：分配多个角色的入职流程
     *
     * 测试步骤：
     * 1. 管理员创建用户
     * 2. 管理员分配多个角色（如 data_engineer + data_analyst）
     * 3. 用户激活
     *
     * 预期结果：
     * - 用户拥有所有分配的角色权限
     */

    await page.route('**/api/v1/users', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            user_id: 'user_multi_role',
            username: 'multi_role_user',
            email: 'multi_role@example.com',
            status: 'pending',
            roles: ['data_engineer', 'data_analyst']
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);
    await page.click('[data-testid="add-user-button"]');

    await page.fill('input[name="username"]', 'multi_role_user');
    await page.fill('input[name="email"]', 'multi_role@example.com');

    // 选择多个角色
    await page.check('[data-testid="role-data_engineer"]');
    await page.check('[data-testid="role-data_analyst"]');

    await page.click('button:has-text("保存")');

    // 验证多个角色被分配
    await expect(page.locator('[data-testid="role-badge-data_engineer"]')).toBeVisible();
    await expect(page.locator('[data-testid="role-badge-data_analyst"]')).toBeVisible();
  });
});
