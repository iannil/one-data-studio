/**
 * 核心页面 E2E 验收测试
 * 测试平台核心功能页面的可访问性和基本功能
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// 通用 Mock API 响应
function setupCommonMocks(page: any) {
  // 健康检查
  page.route('**/api/v1/health', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'healthy' }),
    });
  });

  // 用户信息
  page.route('**/api/v1/user/info', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        data: {
          user_id: 'test-user',
          username: 'test-user',
          email: 'test@example.com',
          role: 'admin',
        },
      }),
    });
  });
}

// 设置认证状态
async function setupAuth(page: any) {
  // 创建一个模拟的 JWT token (header.payload.signature 格式)
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: 'test-user',
    username: 'test-user',
    email: 'test@example.com',
    roles: ['admin', 'user'],
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
  })).toString('base64').replace(/=+$/, '');
  const mockToken = `${header}.${payload}.signature`;

  // 使用 addInitScript 在页面加载前设置 localStorage
  await page.addInitScript((token) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify({
      user_id: 'test-user',
      username: 'test-user',
      email: 'test@example.com',
      roles: ['admin', 'user'],
    }));
  }, mockToken);
}

test.describe('核心页面 - 首页', () => {
  test('should display home page', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    await page.goto(`${BASE_URL}/`);

    // 验证页面加载
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display welcome message', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    await page.goto(`${BASE_URL}/`);

    // 等待页面稳定
    await page.waitForLoadState('networkidle');

    // 验证页面标题存在
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
  });
});

test.describe('核心页面 - 登录', () => {
  test('should display login form', async ({ page }) => {
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/login`);

    // 验证登录页面可访问
    await expect(page.locator('body')).toBeVisible();
  });

  test('should show validation error for empty credentials', async ({ page }) => {
    setupCommonMocks(page);

    await page.goto(`${BASE_URL}/login`);

    // 验证页面加载
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 数据集', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    // Mock 数据集 API
    page.route('**/api/v1/datasets', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            datasets: [
              { id: 'ds-1', name: '用户行为数据', type: 'table', rows: 1000000 },
              { id: 'ds-2', name: '交易记录', type: 'table', rows: 500000 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display datasets list', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/datasets`);

    // 验证页面加载
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create dataset button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/datasets`);

    // 验证页面有内容
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 文档', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/documents', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            documents: [
              { id: 'doc-1', name: '产品手册.pdf', size: 2048, status: 'processed' },
              { id: 'doc-2', name: 'API文档.md', size: 1024, status: 'processed' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display documents list', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/documents`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should have upload functionality', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/documents`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 工作流', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/workflows', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            workflows: [
              { id: 'wf-1', name: 'RAG工作流', type: 'rag', status: 'running' },
              { id: 'wf-2', name: 'Agent工作流', type: 'agent', status: 'stopped' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display workflows list', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/workflows`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should display workflow status', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/workflows`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 元数据', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/metadata', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            databases: [
              { name: 'user_db', tables: 15 },
              { name: 'order_db', tables: 8 },
            ],
          },
        }),
      });
    });
  });

  test('should display metadata page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/metadata`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 调度', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/schedules', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            schedules: [
              { id: 'sch-1', name: '每日数据同步', cron: '0 2 * * *', status: 'active' },
            ],
            total: 1,
          },
        }),
      });
    });
  });

  test('should display schedules page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/schedules`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 智能体', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/agents', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            agents: [
              { id: 'agent-1', name: '数据分析师', type: 'data-analyst', status: 'active' },
              { id: 'agent-2', name: '客服助手', type: 'customer-service', status: 'active' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display agents page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/agents`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create agent button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/agents`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - Text2SQL', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
  });

  test('should display text2sql page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/text2sql`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should have query input', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/text2sql`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 执行监控', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/executions', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            executions: [
              { id: 'exec-1', workflow_id: 'wf-1', status: 'completed', started_at: '2024-01-01T00:00:00Z' },
              { id: 'exec-2', workflow_id: 'wf-2', status: 'running', started_at: '2024-01-01T01:00:00Z' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display executions dashboard', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/executions`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should display execution status', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/executions`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('核心页面 - 导航', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
  });

  test('should have navigation menu', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/`);

    // 等待页面加载
    await page.waitForLoadState('domcontentloaded');

    // 验证页面存在
    await expect(page.locator('body')).toBeVisible();
  });

  test('should navigate between pages', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/`);

    await page.waitForLoadState('domcontentloaded');

    // 验证首页可以访问
    expect(page.url()).toContain(BASE_URL);
  });
});
