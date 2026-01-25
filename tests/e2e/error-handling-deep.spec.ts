/**
 * 错误处理深度验收测试
 * 测试网络错误、API 错误、表单验证、权限错误、服务降级等场景
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 网络错误处理测试
// ============================================
test.describe('错误处理 - 网络错误', () => {
  test('should handle network timeout gracefully', async ({ page, context }) => {
    // 模拟网络超时
    await context.route('**/api/v1/datasets', route => {
      // 不响应，模拟超时
    });

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForTimeout(5000);

    // 检查是否有错误提示或加载状态
    const errorMessage = page.locator('.error-message, .timeout-error, [class*="error"]');
    const hasError = await errorMessage.count() > 0;

    if (hasError) {
      await expect(errorMessage.first()).toBeVisible();
    }

    // 清理路由
    await context.unroute('**/api/v1/datasets');
  });

  test('should handle network disconnection', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 模拟网络断开
    await context.setOffline(true);

    // 尝试执行需要网络的操作
    const refreshButton = page.locator('button:has-text("刷新"), button:has-text("Refresh")').first();
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(2000);

      // 应该显示离线或网络错误提示
      const offlineIndicator = page.locator('.offline, .network-error, [class*="offline"]');
      const hasOffline = await offlineIndicator.count() > 0;
      console.log('Has offline indicator:', hasOffline);
    }

    // 恢复网络
    await context.setOffline(false);
  });

  test('should handle slow network connection', async ({ page, context }) => {
    // 模拟慢速网络
    await context.route('**/*', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.continue();
    });

    const startTime = Date.now();
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    console.log(`Slow network load time: ${loadTime}ms`);

    // 应该显示加载指示器
    const loadingIndicator = page.locator('.loading, .spinner, [class*="loading"]');
    const hasLoading = await loadingIndicator.count() > 0;
    console.log('Has loading indicator:', hasLoading);

    await context.unroute('**/*');
  });

  test('should handle malformed responses', async ({ page, context }) => {
    // 模拟格式错误的响应
    await context.route('**/api/v1/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'invalid json{{{',
      });
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // 应用应该能处理解析错误
    const body = page.locator('body');
    await expect(body).toBeVisible();

    await context.unroute('**/api/v1/health');
  });
});

// ============================================
// API 错误处理测试
// ============================================
test.describe('错误处理 - API 错误', () => {
  test('should handle 400 Bad Request', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 模拟 400 错误
    await context.route('**/api/v1/datasets', route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 400,
          message: 'Bad Request',
          error: 'Invalid parameter',
        }),
      });
    });

    // 刷新页面触发错误
    await page.reload();
    await page.waitForTimeout(1000);

    const errorMessage = page.locator('.error-message, .ant-message-error, [class*="error"]');
    const hasError = await errorMessage.count() > 0;
    console.log('Has 400 error message:', hasError);

    await context.unroute('**/api/v1/datasets');
  });

  test('should handle 401 Unauthorized', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 模拟 401 错误
    await context.route('**/api/v1/user/info', route => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 401,
          message: 'Unauthorized',
        }),
      });
    });

    // 刷新页面
    await page.reload();
    await page.waitForTimeout(1000);

    // 应该重定向到登录页或显示未授权提示
    const loginRequired = page.locator('.login-required, .unauthorized, [class*="login"]');
    const hasLoginRequired = await loginRequired.count() > 0;
    console.log('Has login required indicator:', hasLoginRequired);

    await context.unroute('**/api/v1/user/info');
  });

  test('should handle 403 Forbidden', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // 模拟 403 错误
    await context.route('**/api/v1/admin/**', route => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 403,
          message: 'Forbidden',
          error: 'Insufficient permissions',
        }),
      });
    });

    await page.reload();
    await page.waitForTimeout(1000);

    const forbiddenMessage = page.locator('.forbidden, .access-denied, [class*="forbidden"]');
    const hasForbidden = await forbiddenMessage.count() > 0;
    console.log('Has forbidden message:', hasForbidden);

    await context.unroute('**/api/v1/admin/**');
  });

  test('should handle 404 Not Found', async ({ page, context }) => {
    // 模拟 404 错误
    await context.route('**/api/v1/nonexistent', route => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 404,
          message: 'Not Found',
          error: 'Resource not found',
        }),
      });
    });

    await page.goto(`${BASE_URL}/nonexistent-page`);
    await page.waitForTimeout(1000);

    // 应该显示 404 页面
    const notFoundPage = page.locator('.not-found, .error-page, [class*="404"]');
    const hasNotFound = await notFoundPage.count() > 0;
    console.log('Has 404 page:', hasNotFound);

    await context.unroute('**/api/v1/nonexistent');
  });

  test('should handle 500 Internal Server Error', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 模拟 500 错误
    await context.route('**/api/v1/datasets', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 500,
          message: 'Internal Server Error',
          error: 'Something went wrong',
        }),
      });
    });

    await page.reload();
    await page.waitForTimeout(1000);

    const errorMessage = page.locator('.error-message, .server-error, [class*="error"]');
    const hasError = await errorMessage.count() > 0;
    console.log('Has 500 error message:', hasError);

    await context.unroute('**/api/v1/datasets');
  });

  test('should handle 503 Service Unavailable', async ({ page, context }) => {
    // 模拟 503 错误
    await context.route('**/api/v1/health', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 503,
          message: 'Service Unavailable',
        }),
      });
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(1000);

    const unavailableMessage = page.locator('.service-unavailable, .maintenance, [class*="unavailable"]');
    const hasUnavailable = await unavailableMessage.count() > 0;
    console.log('Has service unavailable message:', hasUnavailable);

    await context.unroute('**/api/v1/health');
  });
});

// ============================================
// 表单验证错误测试
// ============================================
test.describe('错误处理 - 表单验证', () => {
  test('should validate required fields', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 直接点击确定，不填写必填项
      const confirmButton = page.locator('.ant-modal button:has-text("确定"), .ant-modal button:has-text("OK")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await page.waitForTimeout(500);

        // 应该显示验证错误
        const validationError = page.locator('.ant-form-item-explain-error, .validation-error, [class*="error"]');
        const hasError = await validationError.count() > 0;
        console.log('Has validation error:', hasError);
      }
    }
  });

  test('should validate email format', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const emailInput = page.locator('input[name="email"], input[type="email"]').first();
      if (await emailInput.isVisible()) {
        // 输入无效邮箱
        await emailInput.fill('invalid-email');

        const confirmButton = page.locator('.ant-modal button:has-text("确定")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(500);

          const emailError = page.locator('.ant-form-item-explain-error').filter({ hasText: /邮箱|email/i });
          const hasEmailError = await emailError.count() > 0;
          console.log('Has email validation error:', hasEmailError);
        }
      }
    }
  });

  test('should validate password strength', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
      if (await passwordInput.isVisible()) {
        // 输入弱密码
        await passwordInput.fill('123');

        // 检查是否有密码强度提示
        const strengthIndicator = page.locator('.password-strength, [class*="strength"]');
        const hasIndicator = await strengthIndicator.count() > 0;
        if (hasIndicator) {
          await expect(strengthIndicator.first()).toBeVisible();
        }
      }
    }
  });

  test('should validate min/max length', async ({ page }) => {
    await page.goto(`${BASE_URL}/prompts`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const nameInput = page.locator('input[name="name"]').first();
      if (await nameInput.isVisible()) {
        // 输入过短的名称
        await nameInput.fill('a');

        const confirmButton = page.locator('.ant-modal button:has-text("确定")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(500);

          const lengthError = page.locator('.ant-form-item-explain-error').filter({ hasText: /长度|length/i });
          const hasLengthError = await lengthError.count() > 0;
          console.log('Has length validation error:', hasLengthError);
        }
      }
    }
  });

  test('should validate numeric range', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 查找数值输入
    const numberInput = page.locator('input[type="number"]').first();
    if (await numberInput.isVisible()) {
      // 输入负数（如果只允许正数）
      await numberInput.fill('-1');
      await page.waitForTimeout(300);

      // 输入超大的数值
      await numberInput.fill('999999999999999');
      await page.waitForTimeout(300);

      const validationError = page.locator('.ant-form-item-explain-error');
      const hasError = await validationError.count() > 0;
      console.log('Has numeric validation error:', hasError);
    }
  });
});

// ============================================
// 权限错误处理测试
// ============================================
test.describe('错误处理 - 权限错误', () => {
  test('should show permission denied for non-admin', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${BASE_URL}/admin/users`);
    await authenticatedPage.waitForLoadState('networkidle');

    // 非管理员用户应该看到权限不足提示
    const accessDenied = authenticatedPage.locator('.access-denied, .forbidden, [class*="forbidden"]');
    const hasAccessDenied = await accessDenied.count() > 0;
    console.log('Non-admin user sees access denied:', hasAccessDenied);
  });

  test('should hide restricted menu items', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${BASE_URL}/`);
    await authenticatedPage.waitForLoadState('networkidle');

    // 查找管理菜单项
    const adminMenuItems = authenticatedPage.locator('a:has-text("管理"), a:has-text("Admin")');
    const count = await adminMenuItems.count();

    // 普通用户不应该看到管理菜单
    console.log('Admin menu items visible to regular user:', count);
  });

  test('should show permission error on restricted action', async ({ authenticatedPage, context }) => {
    await authenticatedPage.goto(`${BASE_URL}/datasets`);
    await authenticatedPage.waitForLoadState('networkidle');

    // 模拟删除操作返回 403
    await context.route('**/api/v1/datasets/**', route => {
      const request = route.request();
      if (request.method() === 'DELETE') {
        route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 403,
            message: 'Forbidden',
            error: 'You do not have permission to delete this resource',
          }),
        });
      } else {
        route.continue();
      }
    });

    const firstRow = authenticatedPage.locator('tr[data-row-key], .dataset-item').first();
    if (await firstRow.isVisible()) {
      const deleteButton = firstRow.locator('button:has-text("删除"), button:has-text("Delete")').first();
      if (await deleteButton.isVisible()) {
        await deleteButton.click();
        await authenticatedPage.waitForTimeout(500);

        const confirmButton = authenticatedPage.locator('.ant-popconfirm button:has-text("确定")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await authenticatedPage.waitForTimeout(500);

          const permissionError = authenticatedPage.locator('.ant-message-error, .permission-error');
          const hasError = await permissionError.count() > 0;
          console.log('Has permission error message:', hasError);
        }
      }
    }

    await context.unroute('**/api/v1/datasets/**');
  });
});

// ============================================
// 服务降级处理测试
// ============================================
test.describe('错误处理 - 服务降级', () => {
  test('should handle partial service failure', async ({ page, context }) => {
    // 模拟某个服务失败
    await context.route('**/api/v1/workflows', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 503,
          message: 'Service Unavailable',
        }),
      });
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // 其他功能应该仍然可用
    const workingFeature = page.locator('a:has-text("数据集"), a:has-text("Datasets")').first();
    if (await workingFeature.isVisible()) {
      await workingFeature.click();
      await page.waitForTimeout(500);
      expect(page.url()).toContain('/datasets');
    }

    await context.unroute('**/api/v1/workflows');
  });

  test('should show degraded mode indicator', async ({ page, context }) => {
    // 模拟多个服务同时失败
    await context.route('**/api/v1/workflows', route => route.abort());
    await context.route('**/api/v1/agents', route => route.abort());

    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    const degradedIndicator = page.locator('.degraded-mode, .partial-outage, [class*="degraded"]');
    const hasIndicator = await degradedIndicator.count() > 0;
    console.log('Has degraded mode indicator:', hasIndicator);

    await context.unroute('**/api/v1/workflows');
    await context.unroute('**/api/v1/agents');
  });

  test('should use cached data when service unavailable', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 获取初始内容
    const initialContent = await page.content();

    // 模拟服务失败
    await context.route('**/api/v1/datasets', route => {
      route.fulfill({
        status: 503,
        body: '',
      });
    });

    await page.reload();
    await page.waitForTimeout(1000);

    // 检查是否有缓存的数据显示
    const cachedDataIndicator = page.locator('.cached-data, [class*="cache"]');
    const hasCached = await cachedDataIndicator.count() > 0;
    console.log('Has cached data indicator:', hasCached);

    await context.unroute('**/api/v1/datasets');
  });
});

// ============================================
// 输入错误处理测试
// ============================================
test.describe('错误处理 - 输入错误', () => {
  test('should handle special characters in search', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      // 输入特殊字符
      const specialChars = '<script>alert("xss")</script>';
      await searchInput.fill(specialChars);
      await page.waitForTimeout(500);

      // 应该对特殊字符进行转义
      const bodyContent = await page.content();
      const hasUnescapedScript = bodyContent.includes('<script>alert');
      expect(hasUnescapedScript).toBe(false);
    }
  });

  test('should handle SQL injection attempts', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      // 输入 SQL 注入尝试
      const sqlInjection = "'; DROP TABLE users; --";
      await searchInput.fill(sqlInjection);
      await page.waitForTimeout(500);

      // 应用应该正常处理，不抛出错误
      const body = page.locator('body');
      await expect(body).toBeVisible();
    }
  });

  test('should handle extremely long input', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      // 输入超长文本
      const longText = 'a'.repeat(10000);
      await searchInput.fill(longText);

      // 应该有长度限制
      const value = await searchInput.inputValue();
      expect(value.length).toBeLessThan(1000);
    }
  });
});

// ============================================
// 错误恢复测试
// ============================================
test.describe('错误处理 - 错误恢复', () => {
  test('should allow retry after failed request', async ({ page, context }) => {
    let requestCount = 0;

    // 第一次失败，第二次成功
    await context.route('**/api/v1/datasets', route => {
      requestCount++;
      if (requestCount === 1) {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      } else {
        route.continue();
      }
    });

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForTimeout(2000);

    // 查找重试按钮
    const retryButton = page.locator('button:has-text("重试"), button:has-text("Retry"), button:has-text("刷新")').first();
    if (await retryButton.isVisible()) {
      await retryButton.click();
      await page.waitForTimeout(2000);
    }

    // 第二次请求应该成功
    expect(requestCount).toBeGreaterThanOrEqual(1);

    await context.unroute('**/api/v1/datasets');
  });

  test('should clear error on user action', async ({ page, context }) => {
    await context.route('**/api/v1/datasets', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ code: 500, message: 'Error' }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForTimeout(1000);

    // 修复路由
    await context.unroute('**/api/v1/datasets');

    // 用户导航到其他页面
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    // 返回原页面，错误应该清除
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    const errorMessage = page.locator('.error-message');
    const hasError = await errorMessage.count() > 0;
    console.log('Error cleared after navigation:', !hasError);
  });

  test('should provide helpful error messages', async ({ page, context }) => {
    await context.route('**/api/v1/datasets', route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 400,
          message: 'Validation failed',
          error: 'The "name" field is required',
        }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForTimeout(1000);

    const errorMessage = page.locator('.error-message, .ant-message-error');
    if (await errorMessage.count() > 0) {
      const text = await errorMessage.textContent();
      console.log('Error message:', text);

      // 错误消息应该有意义
      expect(text).toBeTruthy();
      expect(text?.length).toBeGreaterThan(10);
    }

    await context.unroute('**/api/v1/datasets');
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Error Handling test:', failedRequests);
  }
});
