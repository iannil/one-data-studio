/**
 * ONE-DATA-STUDIO 核心页面 E2E 测试
 * 覆盖用例: 基础页面可访问性和导航
 */

import { test, expect, Page } from '@playwright/test';

// 测试用户凭证
const TEST_USERS = {
  admin: { username: 'admin', password: 'admin123' },
  dataAdmin: { username: 'data_admin', password: 'da123456' },
  dataEngineer: { username: 'data_engineer', password: 'de123456' },
  algoEngineer: { username: 'algo_engineer', password: 'ae123456' },
  businessUser: { username: 'business_user', password: 'bu123456' },
};

// 登录辅助函数
async function login(page: Page, username: string, password: string) {
  await page.goto('/login');
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|home)/);
}

test.describe('核心页面测试', () => {
  test.describe('登录页面', () => {
    test('应显示登录表单', async ({ page }) => {
      await page.goto('/login');

      await expect(page.locator('input[name="username"]')).toBeVisible();
      await expect(page.locator('input[name="password"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('无效凭证应显示错误', async ({ page }) => {
      await page.goto('/login');

      await page.fill('input[name="username"]', 'invalid');
      await page.fill('input[name="password"]', 'wrong');
      await page.click('button[type="submit"]');

      await expect(page.locator('.ant-message-error, .error-message')).toBeVisible({ timeout: 5000 });
    });

    test('有效凭证应登录成功', async ({ page }) => {
      await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);

      await expect(page).toHaveURL(/\/(dashboard|home)/);
    });
  });

  test.describe('导航测试', () => {
    test.beforeEach(async ({ page }) => {
      await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    });

    test('应能访问数据治理页面', async ({ page }) => {
      await page.click('text=数据治理');
      await expect(page).toHaveURL(/\/data/);
    });

    test('应能访问应用编排页面', async ({ page }) => {
      await page.click('text=应用编排');
      await expect(page).toHaveURL(/\/agent/);
    });

    test('应能访问算法引擎页面', async ({ page }) => {
      await page.click('text=算法引擎');
      await expect(page).toHaveURL(/\/cube/);
    });

    test('应能访问系统设置页面', async ({ page }) => {
      await page.click('text=系统设置');
      await expect(page).toHaveURL(/\/admin/);
    });
  });

  test.describe('仪表盘测试', () => {
    test.beforeEach(async ({ page }) => {
      await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    });

    test('仪表盘应显示关键指标', async ({ page }) => {
      await page.goto('/dashboard');

      // 检查关键指标卡片
      await expect(page.locator('[data-testid="metric-card"]').first()).toBeVisible();
    });

    test('仪表盘应显示图表', async ({ page }) => {
      await page.goto('/dashboard');

      // 等待图表加载
      await expect(page.locator('.recharts-wrapper, canvas, svg.chart')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('响应式布局测试', () => {
    test('桌面视图应正常显示', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);

      await expect(page.locator('.ant-layout-sider, .sidebar')).toBeVisible();
    });

    test('平板视图应正常显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/login');

      await expect(page.locator('input[name="username"]')).toBeVisible();
    });
  });
});

test.describe('API 健康检查', () => {
  test('Alldata API 应可用', async ({ request }) => {
    const response = await request.get('http://localhost:8001/api/v1/health');
    expect(response.ok()).toBeTruthy();
  });

  test('Bisheng API 应可用', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/health');
    expect(response.ok()).toBeTruthy();
  });

  test('Cube API 应可用', async ({ request }) => {
    const response = await request.get('http://localhost:8002/api/v1/health');
    expect(response.ok()).toBeTruthy();
  });
});
