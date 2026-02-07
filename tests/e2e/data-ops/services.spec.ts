/**
 * 数据服务 API E2E 测试
 * 测试用例编号: DA-SV-E-001 ~ DA-SV-E-005
 *
 * 数据服务 API 功能测试：
 * - 创建数据服务
 * - API密钥管理
 * - 服务监控
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Data Services API', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['dataservice:*'] }
        })
      });
    });
  });

  test('DA-SV-E-001: Create data service', async ({ page }) => {
    /** 测试场景：创建数据服务
     *
     * 测试步骤：
     * 1. 导航到数据服务页面
     * 2. 点击"新建服务"
     * 3. 选择数据源和表
     * 4. 配置API参数
     * 5. 发布服务
     *
     * 预期结果：
     * - 服务创建成功
     * - 生成API端点
     */

    await page.route('**/api/v1/data/services', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              service_id: 'svc_001',
              name: '用户查询服务',
              api_endpoint: '/api/v1/data/services/svc_001',
              status: 'online'
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { services: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/data/services`);

    // 点击新建服务
    await page.click('[data-testid="create-service-button"]');

    // 填写服务信息
    await page.fill('input[name="name"]', '用户查询服务');
    await page.selectOption('select[name="datasource"]', 'ds_mysql_001');
    await page.selectOption('select[name="table"]', 'users');

    // 配置 API
    await page.check('[data-testid="enable-auth"]');

    // 发布
    await page.click('button[type="submit"]');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('DA-SV-E-002: Generate API key', async ({ page }) => {
    /** 测试场景：生成 API 密钥
     *
     * 前置条件：服务已创建
     *
     * 测试步骤：
     * 1. 进入服务详情
     * 2. 点击"生成密钥"
     * 3. 配置密钥权限
     * 4. 确认生成
     *
     * 预期结果：
     * - API 密钥生成成功
     * - 显示密钥信息
     */

    await page.route('**/api/v1/data/services/*/api-keys', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            api_key: 'sk_test_xxxxx',
            key_id: 'key_001',
            created_at: new Date().toISOString()
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/services/svc_001`);

    // 点击生成密钥
    await page.click('[data-testid="generate-apikey-button"]');

    // 配置权限
    await page.selectOption('select[name="rate_limit"]', '1000');

    // 确认
    await page.click('button:has-text("生成")');

    // 验证密钥显示
    await expect(page.locator('text=sk_test_')).toBeVisible();
  });

  test('DA-SV-E-003: View service statistics', async ({ page }) => {
    /** 测试场景：查看服务统计
     *
     * 前置条件：服务有使用记录
     *
     * 测试步骤：
     * 1. 进入服务详情
     * 2. 查看统计数据
     *
     * 预期结果：
     * - 显示调用量、成功率、响应时间等
     */

    await page.route('**/api/v1/data/services/*/statistics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            service_id: 'svc_001',
            total_calls: 15000,
            successful_calls: 14250,
            failed_calls: 750,
            success_rate: 95.0,
            avg_latency_ms: 120,
            p95_latency_ms: 250,
            p99_latency_ms: 500
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/services/svc_001/statistics`);

    // 验证统计显示
    await expect(page.locator('text=15000')).toBeVisible();
    await expect(page.locator('text=95%')).toBeVisible();
    await expect(page.locator('text=120ms')).toBeVisible();
  });

  test('DA-SV-E-004: Revoke API key', async ({ page }) => {
    /** 测试场景：撤销 API 密钥
     *
     * 前置条件：API 密钥已存在
     *
     * 测试步骤：
     * 1. 进入服务详情
     * 2. 找到目标密钥
     * 3. 点击撤销
     * 4. 确认
     *
     * 预期结果：
     * - 密钥被撤销
     */

    await page.route('**/api/v1/data/services/*/api-keys/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { revoked: true }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/services/svc_001/api-keys`);

    // 点击撤销按钮
    await page.click('[data-testid="revoke-key-key_001"]');

    // 确认
    await page.click('.ant-modal button:has-text("确定")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("密钥已撤销")')).toBeVisible();
  });
});
