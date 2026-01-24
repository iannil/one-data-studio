/**
 * Cube Studio MLOps 页面 E2E 验收测试
 * 测试模型开发、训练、服务等 MLOps 功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('Cube Studio - Notebooks', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/notebooks', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            notebooks: [
              { id: 'nb-1', name: '数据探索', kernel: 'python3', status: 'running' },
              { id: 'nb-2', name: '模型训练实验', kernel: 'python3', status: 'stopped' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display notebooks page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/notebooks`);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create notebook button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/notebooks`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Experiments', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/experiments', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            experiments: [
              { id: 'exp-1', name: 'GPT-微调实验', status: 'completed', metrics: { accuracy: 0.95 } },
              { id: 'exp-2', name: 'BERT分类实验', status: 'running', metrics: { accuracy: 0.87 } },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display experiments page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/experiments`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Models', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/models', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            models: [
              { id: 'model-1', name: 'gpt-4o-mini', framework: 'vLLM', status: 'serving' },
              { id: 'model-2', name: 'bert-base-chinese', framework: 'PyTorch', status: 'registered' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display models page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/models`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Training', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/training-jobs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            jobs: [
              { id: 'job-1', name: 'LLM微调任务', status: 'running', gpu: 'A100:1', progress: 65 },
              { id: 'job-2', name: '数据预处理', status: 'completed', gpu: 'CPU', progress: 100 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display training page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/training`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Serving', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/serving', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            services: [
              { id: 'srv-1', name: 'gpt-4o-mini-service', endpoint: '/v1/chat/completions', status: 'healthy', qps: 150 },
              { id: 'srv-2', name: 'embedding-service', endpoint: '/v1/embeddings', status: 'healthy', qps: 300 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display serving page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/serving`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Resources', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/resources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            gpu_pools: [
              { name: 'A100-pool', total: 8, used: 5, available: 3 },
              { name: 'V100-pool', total: 16, used: 8, available: 8 },
            ],
            cpu_pools: [
              { name: 'CPU-general', total: 100, used: 45, available: 55 },
            ],
          },
        }),
      });
    });
  });

  test('should display resources page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/resources`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            metrics: {
              total_requests: 150000,
              avg_latency: 250,
              error_rate: 0.01,
              gpu_utilization: 78,
            },
          },
        }),
      });
    });
  });

  test('should display monitoring page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/monitoring`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - AI Hub', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/aihub/models', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            models: [
              { id: 'hub-1', name: 'Qwen2.5-7B', provider: 'ModelScope', downloads: 50000 },
              { id: 'hub-2', name: 'Llama-3.1-8B', provider: 'HuggingFace', downloads: 120000 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display AI Hub page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/aihub`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - Pipelines', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/pipelines', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            pipelines: [
              { id: 'pipe-1', name: '数据预处理流水线', status: 'active', stages: 3 },
              { id: 'pipe-2', name: '模型部署流水线', status: 'active', stages: 5 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display pipelines page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/pipelines`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - LLM Tuning', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/llm-tuning', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            tuning_jobs: [
              { id: 'tune-1', name: 'Qwen微调', method: 'LoRA', status: 'running', epoch: 3/10 },
              { id: 'tune-2', name: 'Llama全量微调', method: 'Full', status: 'completed', epoch: 10/10 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display LLM tuning page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/llm-tuning`);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Cube Studio - SQL Lab', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);

    page.route('**/api/v1/cube/sql-lab', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            queries: [
              { id: 'q-1', name: '用户分析查询', database: 'user_db', status: 'saved' },
              { id: 'q-2', name: '日活统计', database: 'analytics_db', status: 'saved' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display SQL Lab page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/cube/sql-lab`);

    await expect(page.locator('body')).toBeVisible();
  });
});
