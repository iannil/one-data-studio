/**
 * ONE-DATA-STUDIO 数据治理深度 E2E 测试
 * 覆盖用例: DM-DS-*, DM-MS-*, DM-SD-*, DE-ETL-*
 */

import { test, expect, Page } from '@playwright/test';

// 测试配置
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const TEST_USER = { username: 'data_admin', password: 'da123456' };

// 登录辅助函数
async function login(page: Page) {
  await page.goto('/login');
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|data)/);
}

test.describe('数据源管理 (DM-DS)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/data/datasources');
  });

  test('DM-DS-001: 注册 MySQL 数据源', async ({ page }) => {
    // 点击新增数据源
    await page.click('button:has-text("新增数据源")');

    // 选择 MySQL 类型
    await page.click('[data-testid="datasource-type-mysql"]');

    // 填写连接信息
    await page.fill('input[name="name"]', 'test_mysql_source');
    await page.fill('input[name="host"]', 'localhost');
    await page.fill('input[name="port"]', '3306');
    await page.fill('input[name="database"]', 'test_db');
    await page.fill('input[name="username"]', 'test_user');
    await page.fill('input[name="password"]', 'test_password');

    // 测试连接
    await page.click('button:has-text("测试连接")');
    await expect(page.locator('.ant-message-success')).toBeVisible({ timeout: 10000 });

    // 保存
    await page.click('button:has-text("保存")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('DM-DS-004: 连接失败处理', async ({ page }) => {
    await page.click('button:has-text("新增数据源")');
    await page.click('[data-testid="datasource-type-mysql"]');

    // 填写错误的连接信息
    await page.fill('input[name="name"]', 'invalid_source');
    await page.fill('input[name="host"]', 'invalid-host');
    await page.fill('input[name="port"]', '3306');

    // 测试连接应失败
    await page.click('button:has-text("测试连接")');
    await expect(page.locator('.ant-message-error')).toBeVisible({ timeout: 10000 });
  });

  test('DM-DS-007: 数据源列表展示', async ({ page }) => {
    // 验证数据源列表存在
    await expect(page.locator('table, .datasource-list')).toBeVisible();

    // 验证有分页或列表项
    const rows = page.locator('tr, .datasource-item');
    await expect(rows.first()).toBeVisible();
  });
});

test.describe('元数据扫描 (DM-MS)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('DM-MS-001: 自动元数据扫描', async ({ page }) => {
    await page.goto('/data/metadata');

    // 选择数据源
    await page.click('button:has-text("扫描")');

    // 等待扫描完成
    await expect(page.locator('text=扫描完成')).toBeVisible({ timeout: 60000 });
  });

  test('DM-MS-002: AI 字段标注', async ({ page }) => {
    await page.goto('/data/metadata');

    // 选择表
    await page.click('.table-row:first-child');

    // 触发 AI 标注
    await page.click('button:has-text("AI 标注")');

    // 等待标注完成
    await expect(page.locator('.ai-tag, .field-tag')).toBeVisible({ timeout: 30000 });
  });
});

test.describe('敏感数据识别 (DM-SD)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/data/sensitive');
  });

  test('DM-SD-001: 敏感字段扫描', async ({ page }) => {
    // 触发扫描
    await page.click('button:has-text("扫描敏感数据")');

    // 等待扫描完成
    await expect(page.locator('.sensitive-result, .scan-result')).toBeVisible({ timeout: 60000 });
  });

  test('DM-SD-002: 敏感数据分类', async ({ page }) => {
    // 验证敏感数据分类展示
    await expect(page.locator('text=个人身份信息')).toBeVisible();
    await expect(page.locator('text=财务信息')).toBeVisible();
  });
});

test.describe('ETL 编排 (DE-ETL)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/data/etl');
  });

  test('DE-ETL-001: 创建 ETL 任务', async ({ page }) => {
    await page.click('button:has-text("新建任务")');

    // 填写任务信息
    await page.fill('input[name="name"]', 'test_etl_task');
    await page.fill('textarea[name="description"]', '测试 ETL 任务');

    // 选择源和目标
    await page.click('[data-testid="source-select"]');
    await page.click('.ant-select-item:first-child');

    await page.click('[data-testid="target-select"]');
    await page.click('.ant-select-item:first-child');

    // 保存
    await page.click('button:has-text("保存")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('DE-ETL-003: AI 清洗规则推荐', async ({ page }) => {
    // 进入 ETL 编辑器
    await page.click('.etl-task-row:first-child');

    // 触发 AI 推荐
    await page.click('button:has-text("AI 推荐")');

    // 验证推荐结果
    await expect(page.locator('.ai-recommendation, .cleaning-rule')).toBeVisible({ timeout: 30000 });
  });

  test('DE-ETL-005: 执行 ETL 任务', async ({ page }) => {
    // 选择任务
    await page.click('.etl-task-row:first-child');

    // 执行任务
    await page.click('button:has-text("执行")');

    // 等待任务完成
    await expect(page.locator('text=执行成功')).toBeVisible({ timeout: 120000 });
  });
});
