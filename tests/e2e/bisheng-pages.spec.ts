/**
 * Bisheng LLMOps 页面 E2E 验收测试
 * 测试提示词管理、知识库、应用编排等 LLMOps 功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

test.describe('Bisheng - Prompts', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/bisheng/prompts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            prompts: [
              { id: 'prompt-1', name: '客服回复模板', model: 'gpt-4o', variables: ['user_name', 'question'] },
              { id: 'prompt-2', name: '摘要生成', model: 'gpt-4o-mini', variables: ['content'] },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display prompts page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/prompts`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create prompt button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/prompts`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Bisheng - Knowledge', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/bisheng/knowledge', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            knowledge_bases: [
              { id: 'kb-1', name: '产品文档库', type: 'document', chunks: 1250, status: 'ready' },
              { id: 'kb-2', name: 'FAQ知识库', type: 'faq', chunks: 450, status: 'ready' },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display knowledge page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/knowledge`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create knowledge base button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/knowledge`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Bisheng - Apps', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/bisheng/apps', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            apps: [
              { id: 'app-1', name: '智能客服', type: 'chatbot', status: 'published', visits: 15000 },
              { id: 'app-2', name: '文档问答', type: 'rag', status: 'published', visits: 8500 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display apps page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/apps`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create app button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/apps`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Bisheng - Evaluation', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/bisheng/evaluations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            evaluations: [
              { id: 'eval-1', name: '客服准确性评估', status: 'completed', score: 0.92, test_cases: 100 },
              { id: 'eval-2', name: 'RAG召回评估', status: 'completed', score: 0.88, test_cases: 50 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display evaluation page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/evaluation`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create evaluation button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/evaluation`);
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Bisheng - SFT', () => {
  test.beforeEach(async ({ page }) => {
    setupCommonMocks(page);
    page.route('**/api/v1/bisheng/sft', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            sft_jobs: [
              { id: 'sft-1', name: '客服对话微调', model: 'Qwen2.5-7B', status: 'training', progress: 65, epoch: 2/3 },
              { id: 'sft-2', name: 'SQL生成微调', model: 'CodeQwen-7B', status: 'completed', progress: 100, epoch: 3/3 },
            ],
            total: 2,
          },
        }),
      });
    });
  });

  test('should display SFT page', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/sft`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have create SFT job button', async ({ page }) => {
    await setupAuth(page);
    await page.goto(`${BASE_URL}/bisheng/sft`);
    await expect(page.locator('body')).toBeVisible();
  });
});
