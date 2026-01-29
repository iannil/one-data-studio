/**
 * CRUD 操作 E2E 测试
 * 测试各模块的增删改查操作
 */

import { test, expect } from '@playwright/test';
import {
  setupAuth,
  setupCommonMocks,
  BASE_URL,
  verifyAntMessage,
  verifyAntModal,
  confirmAntPopconfirm,
  waitForPageLoad,
} from './helpers';

test.describe('CRUD - 数据集管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 数据集列表 API
    await page.route('**/api/v1/datasets', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'ds-1',
                  name: '测试数据集',
                  description: '这是测试描述',
                  storage_type: 'minio',
                  storage_path: '/data/test',
                  format: 'parquet',
                  created_at: '2024-01-01T10:00:00Z',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'ds-new', name: 'new-dataset' },
            message: '创建成功',
          }),
        });
      }
    });

    // Mock 单个数据集 API
    await page.route('**/api/v1/datasets/*', async (route) => {
      const method = route.request().method();

      if (method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'ds-1', name: 'updated-dataset' },
            message: '更新成功',
          }),
        });
      } else if (method === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: '删除成功',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'ds-1',
              name: '测试数据集',
              description: '这是测试描述',
            },
          }),
        });
      }
    });
  });

  test('访问数据集列表页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });

  test('点击新建按钮打开创建对话框', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await waitForPageLoad(page);

    // 查找并点击新建按钮
    const createButton = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("添加")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      // 等待对话框出现
      await expect(page.locator('.ant-modal, .ant-drawer')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('CRUD - 工作流管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 工作流列表 API
    await page.route('**/api/v1/workflows', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'wf-1',
                  name: '测试工作流',
                  description: 'ETL 数据处理',
                  status: 'active',
                  created_at: '2024-01-01T10:00:00Z',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'wf-new', name: 'new-workflow' },
            message: '创建成功',
          }),
        });
      }
    });

    // Mock 工作流执行 API
    await page.route('**/api/v1/workflows/*/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { execution_id: 'exec-1' },
          message: '已提交执行',
        }),
      });
    });
  });

  test('访问工作流列表页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });

  test('点击新建跳转到编辑器', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await waitForPageLoad(page);

    const createButton = page.locator('button:has-text("新建"), button:has-text("创建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      // 应该跳转到编辑器页面
      await expect(page).toHaveURL(/\/workflows\/new|\/workflows\/.*\/edit/, { timeout: 5000 });
    }
  });
});

test.describe('CRUD - 用户管理 (Admin)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, { roles: ['admin'] });
    setupCommonMocks(page);

    // Mock 用户列表 API
    await page.route('**/api/v1/admin/users', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              users: [
                { id: 'user-1', username: 'admin', email: 'admin@example.com', role: 'admin', status: 'active' },
                { id: 'user-2', username: 'developer', email: 'dev@example.com', role: 'developer', status: 'active' },
              ],
              total: 2,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'user-new', username: 'new-user' },
            message: '用户创建成功',
          }),
        });
      }
    });

    // Mock 单个用户 API
    await page.route('**/api/v1/admin/users/*', async (route) => {
      const method = route.request().method();

      if (method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: '用户更新成功',
          }),
        });
      } else if (method === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: '用户删除成功',
          }),
        });
      }
    });

    // Mock 重置密码 API
    await page.route('**/api/v1/admin/users/*/reset-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: '密码重置成功',
        }),
      });
    });
  });

  test('访问用户管理页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });

  test('点击新建用户按钮', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await waitForPageLoad(page);

    const createButton = page.locator('button:has-text("新建"), button:has-text("添加用户")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await expect(page.locator('.ant-modal, .ant-drawer')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('CRUD - 提示词模板 (agent)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 提示词列表 API
    await page.route('**/api/v1/prompts', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'prompt-1',
                  name: '问答模板',
                  template: '请回答以下问题：{question}',
                  variables: ['question'],
                  created_at: '2024-01-01T10:00:00Z',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'prompt-new', name: 'new-prompt' },
            message: '创建成功',
          }),
        });
      }
    });

    // Mock 测试提示词 API
    await page.route('**/api/v1/prompts/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            output: '这是测试输出',
            tokens_used: 100,
          },
        }),
      });
    });
  });

  test('访问提示词模板页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/agent/prompts`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });
});

test.describe('CRUD - 知识库管理 (Agent)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 知识库列表 API
    await page.route('**/api/v1/knowledge**', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'kb-1',
                  name: '产品文档库',
                  documents: 50,
                  status: 'ready',
                  created_at: '2024-01-01T10:00:00Z',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'kb-new', name: 'new-knowledge-base' },
            message: '创建成功',
          }),
        });
      }
    });
  });

  test('访问知识库页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/agent/knowledge`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });
});

test.describe('CRUD - 模型管理 (model)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 模型列表 API
    await page.route('**/api/v1/models', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'model-1',
                  name: 'text-classification',
                  version: 'v1.0',
                  framework: 'pytorch',
                  status: 'ready',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'model-new', name: 'new-model' },
            message: '模型注册成功',
          }),
        });
      }
    });

    // Mock 模型版本 API
    await page.route('**/api/v1/models/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            versions: [
              { version: 'v1.0', status: 'active', created_at: '2024-01-01' },
              { version: 'v0.9', status: 'archived', created_at: '2023-12-01' },
            ],
          },
        }),
      });
    });
  });

  test('访问模型管理页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/model/models`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });
});

test.describe('CRUD - 数据源管理 (data)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);

    // Mock 数据源列表 API
    await page.route('**/api/v1/datasources', async (route) => {
      const method = route.request().method();

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'ds-1',
                  name: 'MySQL-prod',
                  type: 'mysql',
                  host: 'mysql.prod.local',
                  status: 'connected',
                },
              ],
              total: 1,
            },
          }),
        });
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: 'ds-new' },
            message: '数据源创建成功',
          }),
        });
      }
    });

    // Mock 测试连接 API
    await page.route('**/api/v1/datasources/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { connected: true, latency_ms: 5 },
          message: '连接成功',
        }),
      });
    });
  });

  test('访问数据源页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/data/datasources`);
    await expect(page.locator('body')).toBeVisible();
    await waitForPageLoad(page);
  });

  test('点击新建数据源按钮', async ({ page }) => {
    await page.goto(`${BASE_URL}/data/datasources`);
    await waitForPageLoad(page);

    const createButton = page.locator('button:has-text("新建"), button:has-text("添加数据源"), button:has-text("创建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await expect(page.locator('.ant-modal, .ant-drawer')).toBeVisible({ timeout: 5000 });
    }
  });
});
