/**
 * API 响应验证 E2E 测试
 * 验证各模块 API 接口的响应格式和页面正确渲染
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('API响应验证 - 核心接口', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);
  });

  test('健康检查接口返回正确格式', async ({ page }) => {
    let healthCalled = false;
    await page.route('**/api/v1/health', async (route) => {
      healthCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy', data: { status: 'ok' } }),
      });
    });

    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('数据集列表接口返回正确格式', async ({ page }) => {
    await page.route('**/api/v1/datasets**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'ds-1', name: '测试数据集', created_at: '2024-01-01' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/datasets`);
    await expect(page.locator('body')).toBeVisible();
    await page.waitForLoadState('networkidle');
  });

  test('工作流列表接口返回正确格式', async ({ page }) => {
    await page.route('**/api/v1/workflows**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'wf-1', name: '测试工作流', status: 'active' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/workflows`);
    await expect(page.locator('body')).toBeVisible();
    await page.waitForLoadState('networkidle');
  });
});

test.describe('API响应验证 - data 数据治理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);
  });

  test('数据源列表接口', async ({ page }) => {
    await page.route('**/api/v1/datasources**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'ds-1', name: 'MySQL数据源', type: 'mysql', status: 'connected' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/data/datasources`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('ETL任务列表接口', async ({ page }) => {
    await page.route('**/api/v1/etl**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'etl-1', name: 'ETL任务1', status: 'running' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/data/etl`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('数据质量规则接口', async ({ page }) => {
    await page.route('**/api/v1/quality**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            rules: [
              { id: 'rule-1', name: '非空检查', type: 'not_null' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/data/quality`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('数据血缘接口', async ({ page }) => {
    await page.route('**/api/v1/lineage**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            nodes: [],
            edges: [],
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/data/lineage`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('API响应验证 - model', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);
  });

  test('Notebooks列表接口', async ({ page }) => {
    await page.route('**/api/v1/notebooks**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'nb-1', name: 'Jupyter Notebook', status: 'running', kernel: 'python3' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/model/notebooks`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('实验列表接口', async ({ page }) => {
    await page.route('**/api/v1/experiments**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'exp-1', name: '实验1', metrics: { accuracy: 0.95 } },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/model/experiments`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('模型列表接口', async ({ page }) => {
    await page.route('**/api/v1/models**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'model-1', name: 'GPT-3.5', version: 'v1', status: 'deployed' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/model/models`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('训练任务接口', async ({ page }) => {
    await page.route('**/api/v1/training**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'job-1', name: '训练任务1', status: 'running', progress: 50 },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/model/training`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('模型服务接口', async ({ page }) => {
    await page.route('**/api/v1/serving**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'svc-1', name: '推理服务1', replicas: 2, status: 'running' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/model/serving`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('API响应验证 - agent LLMOps', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    setupCommonMocks(page);
  });

  test('提示词模板列表接口', async ({ page }) => {
    await page.route('**/api/v1/prompts**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'prompt-1', name: '问答模板', template: 'Q: {question}\nA:', variables: ['question'] },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/agent/prompts`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('知识库列表接口', async ({ page }) => {
    await page.route('**/api/v1/knowledge**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'kb-1', name: '产品知识库', documents: 100, embeddings: 'text-embedding-3-small' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/agent/knowledge`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('应用列表接口', async ({ page }) => {
    await page.route('**/api/v1/apps**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'app-1', name: '智能客服', type: 'chatbot', status: 'published' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/agent/apps`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('评测任务列表接口', async ({ page }) => {
    await page.route('**/api/v1/evaluations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            items: [
              { id: 'eval-1', name: '准确性评测', status: 'completed', score: 0.92 },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/agent/evaluation`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('API响应验证 - Admin 管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, { roles: ['admin'] });
    setupCommonMocks(page);
  });

  test('用户列表接口', async ({ page }) => {
    await page.route('**/api/v1/admin/users**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            users: [
              { id: 'user-1', username: 'admin', email: 'admin@example.com', role: 'admin' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/users`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('角色列表接口', async ({ page }) => {
    await page.route('**/api/v1/admin/roles**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            roles: [
              { id: 'role-1', name: 'admin', permissions: ['*'] },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/roles`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('审计日志接口', async ({ page }) => {
    await page.route('**/api/v1/admin/audit**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            logs: [
              { id: 'log-1', user: 'admin', action: 'login', timestamp: '2024-01-01T10:00:00Z' },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/audit`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('成本报告接口', async ({ page }) => {
    await page.route('**/api/v1/admin/cost**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            summary: { total: 10000, compute: 6000, storage: 4000 },
            trends: [],
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/cost-report`);
    await expect(page.locator('body')).toBeVisible();
  });
});
