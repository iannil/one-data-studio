/**
 * ONE-DATA-STUDIO 应用编排深度 E2E 测试
 * 覆盖用例: BU-KB-*, BU-IQ-*
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

// 测试配置
const TEST_USER = { username: 'business_user', password: 'bu123456' };

// 登录辅助函数
async function login(page: Page) {
  await page.goto('/login');
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|bisheng)/);
}

test.describe('知识库管理 (BU-KB)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/bisheng/knowledge');
  });

  test('BU-KB-001: 创建知识库', async ({ page }) => {
    await page.click('button:has-text("新建知识库")');

    await page.fill('input[name="name"]', 'test_knowledge_base');
    await page.fill('textarea[name="description"]', '测试知识库');

    await page.click('button:has-text("创建")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('BU-KB-002: 上传文档到知识库', async ({ page }) => {
    // 选择知识库
    await page.click('.knowledge-base-item:first-child');

    // 上传文档
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(path.join(__dirname, 'fixtures/test-document.pdf'));

    // 等待上传完成
    await expect(page.locator('.ant-message-success')).toBeVisible({ timeout: 30000 });
  });

  test('BU-KB-004: 文档解析和分块', async ({ page }) => {
    await page.click('.knowledge-base-item:first-child');

    // 检查文档列表
    await expect(page.locator('.document-list .document-item')).toBeVisible();

    // 检查分块信息
    await page.click('.document-item:first-child');
    await expect(page.locator('.chunk-info, .segment-count')).toBeVisible();
  });

  test('BU-KB-005: 向量化和索引', async ({ page }) => {
    await page.click('.knowledge-base-item:first-child');
    await page.click('.document-item:first-child');

    // 验证向量化状态
    await expect(page.locator('text=已索引')).toBeVisible();
  });

  test('BU-KB-010: 删除知识库', async ({ page }) => {
    // 选择要删除的知识库
    await page.click('.knowledge-base-item:last-child .more-actions');
    await page.click('text=删除');

    // 确认删除
    await page.click('.ant-modal-confirm-btns button:has-text("确定")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });
});

test.describe('智能查询 (BU-IQ)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/bisheng/chat');
  });

  test('BU-IQ-001: 纯 SQL 查询', async ({ page }) => {
    // 创建新会话
    await page.click('button:has-text("新建会话")');

    // 输入自然语言查询
    await page.fill('textarea[name="message"]', '查询所有用户的总销售额');
    await page.click('button[type="submit"]');

    // 等待 SQL 生成
    await expect(page.locator('.sql-code, code')).toBeVisible({ timeout: 30000 });
  });

  test('BU-IQ-002: RAG 检索查询', async ({ page }) => {
    await page.click('button:has-text("新建会话")');

    // 选择知识库模式
    await page.click('[data-testid="mode-rag"]');

    // 输入查询
    await page.fill('textarea[name="message"]', '销售政策是什么？');
    await page.click('button[type="submit"]');

    // 验证检索结果
    await expect(page.locator('.rag-result, .source-citation')).toBeVisible({ timeout: 30000 });
  });

  test('BU-IQ-003: 混合查询 (SQL + RAG)', async ({ page }) => {
    await page.click('button:has-text("新建会话")');

    // 选择混合模式
    await page.click('[data-testid="mode-hybrid"]');

    // 输入复合查询
    await page.fill('textarea[name="message"]', '根据销售政策，计算本季度符合优惠条件的订单总额');
    await page.click('button[type="submit"]');

    // 验证混合结果
    await expect(page.locator('.hybrid-result')).toBeVisible({ timeout: 60000 });
  });

  test('BU-IQ-005: 查询结果可视化', async ({ page }) => {
    await page.click('button:has-text("新建会话")');

    await page.fill('textarea[name="message"]', '按月统计销售趋势');
    await page.click('button[type="submit"]');

    // 验证图表展示
    await expect(page.locator('.recharts-wrapper, canvas, .chart-container')).toBeVisible({ timeout: 30000 });
  });

  test('BU-IQ-009: 追问上下文理解', async ({ page }) => {
    await page.click('button:has-text("新建会话")');

    // 第一个问题
    await page.fill('textarea[name="message"]', '查询最畅销的产品');
    await page.click('button[type="submit"]');
    await expect(page.locator('.message-content').last()).toBeVisible({ timeout: 30000 });

    // 追问
    await page.fill('textarea[name="message"]', '它的销售额是多少？');
    await page.click('button[type="submit"]');

    // 验证上下文理解
    await expect(page.locator('.message-content').last()).toContainText(/销售额|金额/);
  });
});

test.describe('工作流编排', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/bisheng/workflows');
  });

  test('创建 RAG 工作流', async ({ page }) => {
    await page.click('button:has-text("新建工作流")');

    await page.fill('input[name="name"]', 'test_rag_workflow');
    await page.click('[data-testid="template-rag"]');
    await page.click('button:has-text("创建")');

    await expect(page).toHaveURL(/\/workflows\/\w+\/edit/);
  });

  test('工作流节点拖拽', async ({ page }) => {
    // 进入工作流编辑器
    await page.click('.workflow-item:first-child');

    // 拖拽节点
    const node = page.locator('[data-testid="node-llm"]');
    const canvas = page.locator('.workflow-canvas');

    await node.dragTo(canvas);
    await expect(page.locator('.workflow-node')).toHaveCount(1);
  });

  test('发布工作流', async ({ page }) => {
    await page.click('.workflow-item:first-child');
    await page.click('button:has-text("发布")');

    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('text=已发布')).toBeVisible();
  });
});
