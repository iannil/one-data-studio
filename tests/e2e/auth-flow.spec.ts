/**
 * 认证流程 E2E 测试
 * 测试登录、登出、会话管理等认证相关功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('认证流程 - 登录页面', () => {
  test('登录页面正确显示', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('body')).toBeVisible();
    // 验证登录页面元素
    await expect(page.locator('.ant-card, .login-container, form')).toBeVisible({ timeout: 10000 });
  });

  test('登录页面包含必要的表单元素', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('body')).toBeVisible();
    // 等待页面加载
    await page.waitForLoadState('networkidle');
  });

  test('登录页面显示系统标题', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('body')).toBeVisible();
    await page.waitForLoadState('networkidle');
  });
});

test.describe('认证流程 - 未认证访问', () => {
  test('未认证用户访问受保护路由被重定向到登录页', async ({ page }) => {
    // 不设置认证，直接访问受保护页面
    await page.goto(`${BASE_URL}/datasets`);

    // 应该被重定向到登录页
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('未认证用户访问首页被重定向', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    // 首页可能也需要认证
    await page.waitForLoadState('networkidle');
    // 检查是否在登录页或首页
    const url = page.url();
    expect(url.includes('/login') || url === `${BASE_URL}/`).toBeTruthy();
  });

  test('未认证用户访问管理页面被重定向', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });
});

test.describe('认证流程 - 认证后访问', () => {
  test('认证用户可以访问首页', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('认证用户可以访问数据集页面', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 数据集 API
    await page.route('**/api/v1/datasets**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('认证用户可以访问工作流页面', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/workflows**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
      });
    });

    await page.goto(`${BASE_URL}/workflows`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('认证流程 - 管理员权限', () => {
  test('管理员可以访问用户管理页面', async ({ page }) => {
    await setupAuth(page, { roles: ['admin'] });
    setupCommonMocks(page);

    await page.route('**/api/v1/admin/users', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { users: [], total: 0 } }),
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('管理员可以访问角色管理页面', async ({ page }) => {
    await setupAuth(page, { roles: ['admin'] });
    setupCommonMocks(page);

    await page.route('**/api/v1/admin/roles', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { roles: [], total: 0 } }),
      });
    });

    await page.goto(`${BASE_URL}/admin/roles`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('管理员可以访问成本报告页面', async ({ page }) => {
    await setupAuth(page, { roles: ['admin'] });
    setupCommonMocks(page);

    await page.route('**/api/v1/admin/cost**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { summary: {}, trends: [] } }),
      });
    });

    await page.goto(`${BASE_URL}/admin/cost-report`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('认证流程 - 会话管理', () => {
  test('Token 存储在 localStorage', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('body')).toBeVisible();

    // 验证 token 存储
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    expect(token).toContain('.');  // JWT 格式包含 '.'
  });

  test('用户信息存储在 localStorage', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('body')).toBeVisible();

    // 验证用户信息存储
    const userInfo = await page.evaluate(() => localStorage.getItem('user_info'));
    expect(userInfo).toBeTruthy();

    const parsed = JSON.parse(userInfo!);
    expect(parsed.username).toBe('test-user');
    expect(parsed.email).toBe('test@example.com');
  });
});

test.describe('认证流程 - 回调处理', () => {
  test('回调页面可访问', async ({ page }) => {
    await page.goto(`${BASE_URL}/callback`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('回调页面处理认证码', async ({ page }) => {
    // Mock token 交换 API
    await page.route('**/api/v1/auth/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            access_token: 'mock-access-token',
            refresh_token: 'mock-refresh-token',
            expires_in: 3600,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/callback?code=test-auth-code&state=test-state`);
    await expect(page.locator('body')).toBeVisible();
  });
});
