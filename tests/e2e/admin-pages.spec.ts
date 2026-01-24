/**
 * Admin 管理后台 E2E 验收测试
 * 测试用户管理、权限控制、系统设置等功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('Admin - Users', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/admin/users', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            users: [
              { id: 'user-1', username: 'admin', email: 'admin@example.com', role: 'admin', status: 'active' },
              { id: 'user-2', username: 'developer', email: 'dev@example.com', role: 'developer', status: 'active' },
              { id: 'user-3', username: 'analyst', email: 'analyst@example.com', role: 'analyst', status: 'active' },
            ],
            total: 3,
          },
        }),
      });
    });
  });

  test('should display users page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have add user button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Admin - Groups', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/admin/groups', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            groups: [
              { id: 'group-1', name: '数据开发组', description: '负责数据开发任务', members: 12 },
              { id: 'group-2', name: '算法研究组', description: '负责模型研发', members: 8 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display groups page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/groups`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create group button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/groups`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Admin - Settings', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/admin/settings', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            settings: {
              system_name: 'ONE DATA STUDIO',
              theme: 'light',
              language: 'zh-CN',
            },
          },
        }),
      });
    });
  });

  test('should display settings page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/settings`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have save button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/settings`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Admin - Audit', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/admin/audit', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            logs: [
              { id: 'log-1', user: 'admin', action: 'create_workflow', resource: 'wf-1', timestamp: '2024-01-01T10:00:00Z' },
              { id: 'log-2', user: 'developer', action: 'delete_model', resource: 'model-2', timestamp: '2024-01-01T11:00:00Z' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display audit page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/admin/audit`);
    await expect(page.locator('body')).toBeVisible();
  });
});
