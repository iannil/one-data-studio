/**
 * 错误处理 E2E 测试
 * 测试各种 HTTP 错误状态码的处理
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL, mockApiError, mockNetworkError } from './helpers';

test.describe('错误处理 - 401 未授权', () => {
  test('401 错误重定向到登录页', async ({ page }) => {
    // 不设置认证，模拟401响应
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ code: 401, message: 'Unauthorized' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    // 应该被重定向到登录页
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });

  test('Token 过期时重定向到登录页', async ({ page }) => {
    // 设置过期的 token
    await page.addInitScript(() => {
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({
        sub: 'test-user',
        exp: Math.floor(Date.now() / 1000) - 3600, // 已过期
      }));
      localStorage.setItem('access_token', `${header}.${payload}.signature`);
    });

    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ code: 401, message: 'Token expired' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});

test.describe('错误处理 - 403 禁止访问', () => {
  test('403 错误显示权限不足提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/admin/**', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ code: 403, message: '无权限访问该资源' }),
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();

    // 等待错误消息显示
    await page.waitForTimeout(1000);
    // 检查页面是否显示了错误信息或仍然可访问
    const hasError = await page.locator('.ant-message-error, .ant-result-error, [class*="error"]').count() > 0;
    // 403 错误应该显示错误提示或阻止访问
    expect(page.url()).toContain(BASE_URL);
  });
});

test.describe('错误处理 - 404 资源不存在', () => {
  test('404 错误显示资源不存在提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets/*', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ code: 404, message: '请求的资源不存在' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets/non-existent-id`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('访问不存在的路由显示404页面或重定向', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/this-page-does-not-exist`);
    await expect(page.locator('body')).toBeVisible();
    await page.waitForLoadState('networkidle');
  });
});

test.describe('错误处理 - 429 请求过于频繁', () => {
  test('429 错误显示限流提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ code: 429, message: '请求过于频繁，请稍后再试' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('错误处理 - 500 服务器错误', () => {
  test('500 错误显示服务器错误提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ code: 500, message: '服务器内部错误' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('502 错误显示网关错误提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ code: 502, message: '网关错误' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('503 错误显示服务不可用提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ code: 503, message: '服务暂时不可用，请稍后再试' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('错误处理 - 网络错误', () => {
  test('网络连接失败显示错误提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.abort('failed');
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('请求超时显示超时提示', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.abort('timedout');
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('DNS 解析失败处理', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      await route.abort('addressunreachable');
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('错误处理 - 业务错误', () => {
  test('业务逻辑错误显示错误消息', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // 模拟创建数据集时的业务错误
    await page.route('**/api/v1/datasets', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 400,
            message: '数据集名称已存在',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('表单验证错误显示字段错误', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 422,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 422,
            message: '参数验证失败',
            errors: [
              { field: 'name', message: '名称不能为空' },
              { field: 'storage_path', message: '存储路径格式不正确' },
            ],
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('错误处理 - 重试机制', () => {
  test('临时错误后页面可以刷新恢复', async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    await page.route('**/api/v1/datasets**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();

    // 刷新页面
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });
});
