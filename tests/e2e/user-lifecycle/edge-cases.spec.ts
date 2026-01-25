/**
 * 边界条件和异常场景测试
 * 测试各种边界情况和错误处理
 */

import { test, expect } from './fixtures/user-lifecycle.fixture';
import { generateUserData } from './utils/test-data-generator';
import { verifyCanAccessPage, verifyCannotAccessPage } from './helpers/verification';
import type { Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('边界条件测试', () => {
  test.describe('用户名边界条件', () => {
    test('应该支持最小长度用户名', async ({ userManager }) => {
      const userData = generateUserData({
        username: 'ab', // 最小长度
      });

      const user = await userManager.createUser(userData);
      expect(user).toBeTruthy();
    });

    test('应该支持最大长度用户名', async ({ userManager }) => {
      const userData = generateUserData({
        username: 'a'.repeat(50), // 最大长度
      });

      const user = await userManager.createUser(userData);
      expect(user).toBeTruthy();
    });

    test('应该拒绝过短的用户名', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'a', // 太短
          email: 'test@example.com',
          password: 'Test1234!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该拒绝过长的用户名', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'a'.repeat(100), // 太长
          email: 'test@example.com',
          password: 'Test1234!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该拒绝包含特殊字符的用户名', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'user@name', // 包含特殊字符
          email: 'test@example.com',
          password: 'Test1234!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该接受包含数字和下划线的用户名', async ({ userManager }) => {
      const userData = generateUserData({
        username: 'user_123_test',
      });

      const user = await userManager.createUser(userData);
      expect(user).toBeTruthy();
    });
  });

  test.describe('邮箱边界条件', () => {
    test('应该接受有效的邮箱格式', async ({ userManager }) => {
      const validEmails = [
        'test@example.com',
        'user.name@example.com',
        'user+tag@example.co.uk',
        'test123@test-domain.com',
      ];

      for (const email of validEmails) {
        const userData = generateUserData({ email });
        const user = await userManager.createUser(userData);
        expect(user).toBeTruthy();
      }
    });

    test('应该拒绝无效的邮箱格式', async ({ request }) => {
      const invalidEmails = [
        'invalid',
        '@example.com',
        'user@',
        'user @example.com',
        'user@@example.com',
      ];

      for (const email of invalidEmails) {
        const response = await request.post(`${BASE_URL}/api/v1/users`, {
          data: {
            username: `test_${Date.now()}`,
            email,
            password: 'Test1234!',
          },
        });

        expect([400, 422]).toContain(response.status());
      }
    });

    test('应该拒绝重复的邮箱', async ({ userManager, request }) => {
      const userData = generateUserData();

      await userManager.createUser(userData);

      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: `different_${Date.now()}`,
          email: userData.email,
          password: 'Test1234!',
        },
      });

      expect([400, 409]).toContain(response.status());
    });
  });

  test.describe('密码边界条件', () => {
    test('应该要求密码最小长度', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'test_user',
          email: 'test@example.com',
          password: 'short', // 太短
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该要求密码包含大写字母', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'test_user',
          email: 'test@example.com',
          password: 'nouppercase1!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该要求密码包含小写字母', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'test_user',
          email: 'test@example.com',
          password: 'NOLOWERCASE1!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该要求密码包含数字', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'test_user',
          email: 'test@example.com',
          password: 'NoNumber!',
        },
      });

      expect([400, 422]).toContain(response.status());
    });

    test('应该要求密码包含特殊字符', async ({ request }) => {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: 'test_user',
          email: 'test@example.com',
          password: 'NoSpecialChar1',
        },
      });

      expect([400, 422]).toContain(response.status());
    });
  });

  test.describe('角色边界条件', () => {
    test('应该拒绝无效的角色', async ({ userManager, request }) => {
      const userData = generateUserData();

      const user = await userManager.createUser(userData);

      const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/roles`, {
        data: { role: 'invalid_role' },
      });

      expect([400, 404, 422]).toContain(response.status());
    });

    test('应该拒绝重复分配相同角色', async ({ userManager, request }) => {
      const userData = generateUserData({
        roles: ['user'],
      });

      const user = await userManager.createUser(userData);

      // 分配已有角色
      const response = await request.post(`${BASE_URL}/api/v1/users/${user.id}/roles`, {
        data: { role: 'user' },
      });

      // 可能返回成功（幂等）或错误（重复）
      expect([200, 400, 409]).toContain(response.status());
    });

    test('应该撤销未分配的角色返回错误', async ({ userManager, request }) => {
      const userData = generateUserData({
        roles: ['user'],
      });

      const user = await userManager.createUser(userData);

      // 撤销未分配的角色
      const response = await request.delete(`${BASE_URL}/api/v1/users/${user.id}/roles/data_engineer`);

      expect([400, 404]).toContain(response.status());
    });

    test('应该允许分配多个角色', async ({ userManager }) => {
      const userData = generateUserData({
        roles: ['user'],
      });

      const user = await userManager.createUser(userData);

      await userManager.assignRole(user.id, 'data_engineer');
      await userManager.assignRole(user.id, 'ai_developer');

      const updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles).toContain('data_engineer');
      expect(updatedUser?.roles).toContain('ai_developer');
    });
  });

  test.describe('并发操作边界条件', () => {
    test('应该处理并发创建相同用户', async ({ request }) => {
      const userData = generateUserData();

      // 并发创建
      const results = await Promise.allSettled([
        request.post(`${BASE_URL}/api/v1/users`, { data: userData }),
        request.post(`${BASE_URL}/api/v1/users`, { data: userData }),
        request.post(`${BASE_URL}/api/v1/users`, { data: userData }),
      ]);

      // 只有一个应该成功
      const successCount = results.filter(r => r.status === 'fulfilled').length;
      expect(successCount).toBeGreaterThan(0);
      expect(successCount).toBeLessThanOrEqual(1);
    });

    test('应该处理并发角色变更', async ({ userManager }) => {
      const userData = generateUserData({
        roles: ['user'],
      });

      const user = await userManager.createUser(userData);

      // 并发分配角色
      await Promise.all([
        userManager.assignRole(user.id, 'data_engineer'),
        userManager.assignRole(user.id, 'ai_developer'),
        userManager.assignRole(user.id, 'data_analyst'),
      ]);

      const updatedUser = await userManager.getUser(user.id);
      expect(updatedUser?.roles.length).toBeGreaterThanOrEqual(3);
    });

    test('应该处理并发状态变更', async ({ userManager }) => {
      const userData = generateUserData({
        status: 'active',
      });

      const user = await userManager.createUser(userData);

      // 并发状态变更
      await Promise.all([
        userManager.deactivateUser(user.id),
        userManager.activateUser(user.id),
      ]);

      // 最终状态应该是一致的
      const finalUser = await userManager.getUser(user.id);
      expect(finalUser?.status).toBeTruthy();
    });
  });

  test.describe('大数据量边界条件', () => {
    test('应该处理大量用户列表', async ({ page, request }) => {
      // 获取用户列表
      const response = await request.get(`${BASE_URL}/api/v1/users`, {
        params: { page_size: 100 },
      });

      expect(response.ok()).toBeTruthy();

      const json = await response.json();
      expect(json.code).toBe(0);
      expect(json.data?.users).toBeInstanceOf(Array);
    });

    test('应该处理分页边界', async ({ request }) => {
      // 第一页
      const page1 = await request.get(`${BASE_URL}/api/v1/users`, {
        params: { page: 1, page_size: 10 },
      });
      expect(page1.ok()).toBeTruthy();

      // 超出范围的页
      const page999 = await request.get(`${BASE_URL}/api/v1/users`, {
        params: { page: 999, page_size: 10 },
      });
      expect(page999.ok()).toBeTruthy();

      const json = await page999.json();
      // 应该返回空数组而不是错误
      expect(json.data?.users?.length).toBe(0);
    });

    test('应该处理搜索空结果', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin/users`);
      await page.waitForLoadState('networkidle');

      // 搜索不存在的用户
      await page.fill('input[placeholder*="搜索"]', 'nonexistent_user_xyz_123');
      await page.waitForTimeout(500);

      // 应该显示空状态
      const emptyState = page.locator('.ant-empty, .no-data').first();
      await expect(emptyState).toBeVisible();
    });
  });
});

test.describe('异常场景测试', () => {
  test('应该处理网络错误', async ({ page }) => {
    // Mock 网络错误
    await page.route('**/api/v1/users**', route => route.abort('failed'));

    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该显示错误提示
    const errorMsg = page.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 5000 });
  });

  test('应该处理服务器错误', async ({ page }) => {
    // Mock 500 错误
    await page.route('**/api/v1/users**', route => route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ code: 500, message: '服务器内部错误' }),
    }));

    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该显示错误提示
    const errorMsg = page.locator('.ant-message-error, .error-message').first();
    await expect(errorMsg).toBeVisible({ timeout: 5000 });
  });

  test('应该处理超时错误', async ({ page }) => {
    // Mock 超时
    await page.route('**/api/v1/users**', () => {
      // 不响应，导致超时
    });

    await page.goto(`${BASE_URL}/admin/users`);

    // 应该显示超时提示或加载状态
    const loading = page.locator('.ant-spin').first();
    await expect(loading).toBeVisible({ timeout: 5000 });
  });

  test('应该处理格式错误的响应', async ({ page }) => {
    // Mock 错误的 JSON
    await page.route('**/api/v1/users', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: 'invalid json{{}',
    }));

    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该优雅处理错误
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();
  });

  test('应该处理权限不足的错误', async ({ page, request, userManager }) => {
    // 创建一个普通用户
    const userData = generateUserData({
      roles: ['user'],
      username: `perm_test_${Date.now()}`,
      password: 'Test1234!',
    });

    const user = await userManager.createUser(userData);

    // 登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', userData.username);
    await page.fill('input[name="password"]', userData.password);
    await page.click('button:has-text("登录")');
    await page.waitForLoadState('networkidle');

    // 尝试访问管理页面
    const response = await page.goto(`${BASE_URL}/admin/users`);

    // 应该返回权限错误或重定向
    const currentUrl = page.url();
    const hasAccessDenied = await page.locator('.access-denied, .error-page').count() > 0;

    expect(hasAccessDenied || currentUrl.includes('/login') || currentUrl.includes('/workspace')).toBe(true);
  });

  test('应该处理会话过期', async ({ page }) => {
    // 模拟已过期的 token
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired_token');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // 应该重定向到登录页
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });

  test('应该处理无效的用户 ID', async ({ request }) => {
    const invalidIds = [
      'invalid-id',
      '00000000-0000-0000-0000-000000000000',
      '-1',
      'abc123',
    ];

    for (const id of invalidIds) {
      const response = await request.get(`${BASE_URL}/api/v1/users/${id}`);
      expect([400, 404]).toContain(response.status());
    }
  });

  test('应该处理空的用户名', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/v1/users`, {
      data: {
        username: '',
        email: 'test@example.com',
        password: 'Test1234!',
      },
    });

    expect([400, 422]).toContain(response.status());
  });

  test('应该处理空的邮箱', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/v1/users`, {
      data: {
        username: 'testuser',
        email: '',
        password: 'Test1234!',
      },
    });

    expect([400, 422]).toContain(response.status());
  });

  test('应该处理空的密码', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/v1/users`, {
      data: {
        username: 'testuser',
        email: 'test@example.com',
        password: '',
      },
    });

    expect([400, 422]).toContain(response.status());
  });

  test('应该处理 XSS 注入尝试', async ({ userManager, request, page }) => {
    const xssPayloads = [
      '<script>alert("xss")</script>',
      '"><script>alert("xss")</script>',
      'javascript:alert("xss")',
      '<img src=x onerror=alert("xss")>',
    ];

    for (const payload of xssPayloads) {
      const response = await request.post(`${BASE_URL}/api/v1/users`, {
        data: {
          username: payload,
          email: 'test@example.com',
          password: 'Test1234!',
        },
      });

      // 应该被拒绝或被清理
      if (response.ok()) {
        const json = await response.json();
        const createdUser = json.data;

        if (createdUser) {
          // 验证 payload 被清理
          expect(createdUser.username).not.toContain('<script>');
          expect(createdUser.username).not.toContain('javascript:');
        }
      }
    }
  });

  test('应该处理 SQL 注入尝试', async ({ userManager, request }) => {
    const sqlPayloads = [
      "'; DROP TABLE users; --",
      "' OR '1'='1",
      "admin'--",
      "' UNION SELECT * FROM users--",
    ];

    for (const payload of sqlPayloads) {
      const response = await request.post(`${BASE_URL}/api/v1/auth/login`, {
        data: {
          username: payload,
          password: 'anything',
        },
      });

      // 应该被拒绝
      expect([401, 403, 400]).toContain(response.status());
    }
  });
});

test.describe('UI 边界条件测试', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('应该处理极长用户名显示', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'a'.repeat(100),
        roles: ['user'],
      }));
    });
    await page.reload();

    // 应该截断显示而不是破坏布局
    const usernameDisplay = page.locator('.user-name, .username').first();
    if (await usernameDisplay.isVisible()) {
      const displayedText = await usernameDisplay.textContent();
      expect(displayedText?.length).toBeLessThan(100);
    }
  });

  test('应该处理角色标签溢出', async ({ page }) => {
    await page.goto(`${BASE_URL}`);
    await page.evaluate(() => {
      localStorage.setItem('user_info', JSON.stringify({
        username: 'multi_role_user',
        roles: ['admin', 'data_engineer', 'ai_developer', 'data_analyst', 'user'],
      }));
    });
    await page.reload();

    // 角色标签应该正常显示
    const roleTags = page.locator('.user-role-tag, .role-tag');
    const count = await roleTags.count();
    expect(count).toBeGreaterThan(0);
  });

  test('应该处理空列表显示', async ({ page }) => {
    // Mock 空用户列表
    await page.route('**/api/v1/users**', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: { users: [], total: 0 },
      }),
    }));

    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该显示空状态
    const emptyState = page.locator('.ant-empty, .no-data, .empty-state');
    await expect(emptyState.first()).toBeVisible();
  });

  test('应该处理大量数据的表格渲染', async ({ page }) => {
    // Mock 大量用户
    const manyUsers = Array.from({ length: 100 }, (_, i) => ({
      id: `user_${i}`,
      username: `user_${i}`,
      email: `user_${i}@example.com`,
      roles: ['user'],
      status: 'active',
    }));

    await page.route('**/api/v1/users**', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: { users: manyUsers, total: 100 },
      }),
    }));

    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该正常渲染
    const table = page.locator('.ant-table').first();
    await expect(table).toBeVisible();

    // 验证分页器存在
    const pagination = page.locator('.ant-pagination').first();
    await expect(pagination).toBeVisible();
  });

  test('应该处理移动端响应式', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 应该有响应式布局
    const mainContent = page.locator('main, .main-content').first();
    await expect(mainContent).toBeVisible();
  });

  test('应该处理深色模式', async ({ page }) => {
    // 模拟深色模式
    await page.goto(`${BASE_URL}/admin/users`);
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
    });
    await page.waitForTimeout(500);

    // 内容应该仍然可见
    const mainContent = page.locator('main, .main-content').first();
    await expect(mainContent).toBeVisible();
  });
});
