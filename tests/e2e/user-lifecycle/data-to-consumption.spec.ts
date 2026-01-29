/**
 * ONE-DATA-STUDIO 用户生命周期 E2E 测试
 * 场景 A: 数据从采集到消费的完整链路
 *
 * 流程: 数据管理员 → 数据工程师 → 算法工程师 → 业务用户
 */

import { test, expect, Page } from '@playwright/test';

// 测试用户
const USERS = {
  dataAdmin: { username: 'data_admin', password: 'da123456', role: '数据管理员' },
  dataEngineer: { username: 'data_engineer', password: 'de123456', role: '数据工程师' },
  algoEngineer: { username: 'algo_engineer', password: 'ae123456', role: '算法工程师' },
  businessUser: { username: 'business_user', password: 'bu123456', role: '业务用户' },
};

// 登录辅助函数
async function login(page: Page, username: string, password: string) {
  await page.goto('/login');
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|home)/);
}

test.describe.serial('数据从采集到消费完整链路', () => {
  // 使用 serial 确保测试按顺序执行
  let testId: string;

  test.beforeAll(() => {
    testId = `e2e_${Date.now()}`;
  });

  test('步骤 1: [数据管理员] 注册数据源', async ({ page }) => {
    await login(page, USERS.dataAdmin.username, USERS.dataAdmin.password);
    await page.goto('/data/datasources');

    // 新增数据源
    await page.click('button:has-text("新增数据源")');
    await page.click('[data-testid="datasource-type-mysql"]');

    await page.fill('input[name="name"]', `mysql_${testId}`);
    await page.fill('input[name="host"]', 'localhost');
    await page.fill('input[name="port"]', '3306');
    await page.fill('input[name="database"]', 'e2e_test_db');
    await page.fill('input[name="username"]', 'test_user');
    await page.fill('input[name="password"]', 'test_pass');

    await page.click('button:has-text("测试连接")');
    await expect(page.locator('.ant-message-success')).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("保存")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('步骤 2: [数据管理员] 执行元数据扫描', async ({ page }) => {
    await login(page, USERS.dataAdmin.username, USERS.dataAdmin.password);
    await page.goto('/data/metadata');

    // 选择数据源并扫描
    await page.click(`text=mysql_${testId}`);
    await page.click('button:has-text("扫描元数据")');

    // 等待扫描完成
    await expect(page.locator('text=扫描完成')).toBeVisible({ timeout: 60000 });
  });

  test('步骤 3: [数据管理员] 敏感数据识别', async ({ page }) => {
    await login(page, USERS.dataAdmin.username, USERS.dataAdmin.password);
    await page.goto('/data/sensitive');

    // 扫描敏感数据
    await page.click('button:has-text("扫描敏感数据")');
    await expect(page.locator('.sensitive-result')).toBeVisible({ timeout: 60000 });
  });

  test('步骤 4: [数据工程师] 创建并执行 ETL 任务', async ({ page }) => {
    await login(page, USERS.dataEngineer.username, USERS.dataEngineer.password);
    await page.goto('/data/etl');

    // 创建 ETL 任务
    await page.click('button:has-text("新建任务")');
    await page.fill('input[name="name"]', `etl_${testId}`);

    // 选择源数据
    await page.click('[data-testid="source-select"]');
    await page.click(`.ant-select-item:has-text("mysql_${testId}")`);

    // 保存并执行
    await page.click('button:has-text("保存")');
    await page.click('button:has-text("立即执行")');

    // 等待任务完成
    await expect(page.locator('text=执行成功')).toBeVisible({ timeout: 120000 });
  });

  test('步骤 5: [算法工程师] 训练模型', async ({ page }) => {
    await login(page, USERS.algoEngineer.username, USERS.algoEngineer.password);
    await page.goto('/model/training');

    // 创建训练任务
    await page.click('button:has-text("新建任务")');
    await page.fill('input[name="name"]', `model_${testId}`);

    // 选择数据集
    await page.click('[data-testid="dataset-select"]');
    await page.click('.ant-select-item:first-child');

    // 提交训练
    await page.click('button:has-text("提交")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('步骤 6: [算法工程师] 部署模型服务', async ({ page }) => {
    await login(page, USERS.algoEngineer.username, USERS.algoEngineer.password);
    await page.goto('/model/deployment');

    // 创建部署
    await page.click('button:has-text("新建服务")');
    await page.fill('input[name="service_name"]', `svc_${testId}`);

    // 部署
    await page.click('button:has-text("部署")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('步骤 7: [业务用户] 智能查询', async ({ page }) => {
    await login(page, USERS.businessUser.username, USERS.businessUser.password);
    await page.goto('/agent/chat');

    // 创建新会话
    await page.click('button:has-text("新建会话")');

    // 输入查询
    await page.fill('textarea[name="message"]', '查询销售总额');
    await page.click('button[type="submit"]');

    // 验证结果
    await expect(page.locator('.message-content').last()).toBeVisible({ timeout: 30000 });
  });
});

test.describe('权限验证', () => {
  test('业务用户不能访问数据源管理', async ({ page }) => {
    await login(page, USERS.businessUser.username, USERS.businessUser.password);
    await page.goto('/data/datasources');

    // 应该显示无权限
    await expect(
      page.locator('text=无权限').or(page.locator('text=403')).or(page.locator('text=没有权限'))
    ).toBeVisible({ timeout: 5000 });
  });
});
