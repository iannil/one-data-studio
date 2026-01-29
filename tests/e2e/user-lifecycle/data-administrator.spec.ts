/**
 * 数据管理员 E2E 测试
 * 测试数据管理员的完整用户旅程
 */

import { test, expect } from '@playwright/test';

test.describe('数据管理员全流程', () => {
  test.beforeEach(async ({ page }) => {
    // 登录为数据管理员
    await page.goto('/login');
    await page.fill('input[name="username"]', 'data_admin');
    await page.fill('input[name="password"]', 'test_password');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('完整数据治理流程', async ({ page }) => {
    // 1. 注册数据源
    await page.click('text=数据源管理');
    await page.click('button:has-text("新增数据源")');

    await page.selectOption('select[name="type"]', 'mysql');
    await page.fill('input[name="name"]', '测试MySQL数据源');
    await page.fill('input[name="host"]', 'localhost');
    await page.fill('input[name="port"]', '3306');
    await page.fill('input[name="database"]', 'test_db');
    await page.fill('input[name="username"]', 'root');
    await page.fill('input[name="password"]', 'password');

    await page.click('button:has-text("测试连接")');
    await expect(page.locator('text=连接成功')).toBeVisible();

    await page.click('button:has-text("保存")');
    await expect(page.locator('text=数据源创建成功')).toBeVisible();

    // 2. 启动元数据扫描
    await page.click(`text=测试MySQL数据源`);
    await page.click('button:has-text("启动扫描")');

    // 等待扫描完成
    await page.waitForSelector('text=扫描完成', { timeout: 30000 });
    await expect(page.locator('text=发现表')).toBeVisible();

    // 3. 敏感数据识别
    await page.click('text=敏感数据');
    await page.click('button:has-text("启动敏感扫描")');

    await page.waitForSelector('text=敏感扫描完成', { timeout: 30000 });
    await expect(page.locator('text=PII字段')).toBeVisible();

    // 4. 资产编目
    await page.click('text=资产管理');
    await page.click('button:has-text("自动编目")');

    await page.waitForSelector('text=编目完成', { timeout: 30000 });
    await expect(page.locator('text=数据资产')).toBeVisible();

    // 5. 配置权限
    await page.click('text=权限管理');
    await page.click('button:has-text("新增权限规则")');

    await page.selectOption('select[name="role"]', 'data_engineer');
    await page.selectOption('select[name="resource"]', 'table:users');
    await page.selectOption('select[name="action"]', 'read');

    await page.click('button:has-text("保存")');
    await expect(page.locator('text=权限规则创建成功')).toBeVisible();
  });

  test('DM-DS-001: 注册MySQL数据源', async ({ page }) => {
    await page.click('text=数据源管理');
    await page.click('button:has-text("新增数据源")');

    await page.selectOption('select[name="type"]', 'mysql');
    await page.fill('input[name="name"]', 'E2E测试数据源');
    await page.fill('input[name="host"]', 'localhost');
    await page.fill('input[name="port"]', '3306');
    await page.fill('input[name="database"]', 'test_db');

    await page.click('button:has-text("测试连接")');
    await expect(page.locator('text=连接成功')).toBeVisible();

    await page.click('button:has-text("保存")');
    await expect(page.locator('text=数据源创建成功')).toBeVisible();
  });

  test('DM-MS-001: 元数据自动扫描', async ({ page }) => {
    await page.click('text=数据源管理');

    // 选择已存在的数据源
    await page.click('text=test-mysql-datasource');
    await page.click('button:has-text("启动扫描")');

    // 验证扫描开始
    await expect(page.locator('text=扫描中')).toBeVisible();

    // 等待扫描完成
    await page.waitForSelector('text=扫描完成', { timeout: 60000 });

    // 验证扫描结果
    await expect(page.locator('text=发现表')).toBeVisible();
    await expect(page.locator('text=发现列')).toBeVisible();
  });

  test('DM-SD-001: 敏感数据扫描', async ({ page }) => {
    await page.click('text=敏感数据管理');
    await page.click('button:has-text("启动扫描")');

    await page.waitForSelector('text=扫描完成', { timeout: 60000 });

    // 验证敏感字段识别
    await expect(page.locator('text=PII')).toBeVisible();
    await expect(page.locator('text=FINANCIAL')).toBeVisible();
  });

  test('DM-AS-001: 自动资产编目', async ({ page }) => {
    await page.click('text=资产管理');
    await page.click('button:has-text("自动编目")');

    await page.waitForSelector('text=编目完成', { timeout: 60000 });

    // 验证资产编目结果
    await expect(page.locator('text=数据资产')).toBeVisible();
    await expect(page.locator('text=价值评估')).toBeVisible();
  });

  test('DM-PM-003: 敏感数据访问控制', async ({ page }) => {
    // 配置敏感数据访问权限
    await page.click('text=权限管理');
    await page.click('button:has-text("新增规则")');

    await page.selectOption('select[name="role"]', 'business_user');
    await page.selectOption('select[name="access_level"]', 'masked');

    await page.click('button:has-text("保存")');

    // 验证权限配置
    await expect(page.locator('text=规则已创建')).toBeVisible();
  });
});
