/**
 * CDC 数据同步 E2E 测试
 * 测试用例编号: DE-CDC-E-001 ~ DE-CDC-E-005
 *
 * CDC 数据同步功能测试：
 * - CDC 任务创建
 * - 实时数据同步
 * - 同步监控
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('CDC Data Sync', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['cdc:*'] }
        })
      });
    });
  });

  test('DE-CDC-E-001: Create CDC sync task', async ({ page }) => {
    /** 测试场景：创建 CDC 同步任务
     *
     * 测试步骤：
     * 1. 导航到 CDC 页面
     * 2. 点击"新建同步任务"
     * 3. 选择源和目标数据源
     * 4. 选择要同步的表
     * 5. 配置同步模式
     * 6. 启动同步
     *
     * 预期结果：
     * - CDC 任务创建成功
     * - 同步启动
     */

    await page.route('**/api/v1/data/cdc/tasks', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              task_id: 'cdc_001',
              name: 'MySQL到ClickHouse实时同步',
              source_datasource_id: 'ds_mysql_001',
              target_datasource_id: 'ds_clickhouse_001',
              tables: ['users', 'orders'],
              status: 'running'
            }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/data/cdc`);

    // 点击新建任务
    await page.click('[data-testid="create-cdc-button"]');

    // 选择源和目标
    await page.selectOption('select[name="source_datasource"]', 'ds_mysql_001');
    await page.selectOption('select[name="target_datasource"]', 'ds_clickhouse_001');

    // 选择表
    await page.check('[data-testid="table-users"]');
    await page.check('[data-testid="table-orders"]');

    // 配置同步模式
    await page.selectOption('select[name="sync_mode"]', 'realtime');

    // 启动
    await page.click('button[type="submit"]');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('DE-CDC-E-002: Monitor CDC sync status', async ({ page }) => {
    /** 测试场景：监控 CDC 同步状态
     *
     * 前置条件：CDC 任务运行中
     *
     * 测试步骤：
     * 1. 进入 CDC 任务详情
     * 2. 查看同步状态
     * 3. 查看延迟统计
     *
     * 预期结果：
     * - 显示同步状态
     * - 显示延迟、吞吐量等指标
     */

    await page.route('**/api/v1/data/cdc/tasks/*/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            task_id: 'cdc_001',
            status: 'running',
            tables: [
              { table: 'users', sync_lag_ms: 500, rows_per_second: 1000 },
              { table: 'orders', sync_lag_ms: 300, rows_per_second: 500 }
            ],
            total_throughput: 1500
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/cdc/tasks/cdc_001`);

    // 验证状态显示
    await expect(page.locator('text=running')).toBeVisible();
    await expect(page.locator('text=500ms')).toBeVisible();
    await expect(page.locator('text=300ms')).toBeVisible();
  });

  test('DE-CDC-E-003: Handle CDC sync error', async ({ page }) => {
    /** 测试场景：处理 CDC 同步错误
     *
     * 前置条件：CDC 任务遇到错误
     *
     * 测试步骤：
     * 1. 查看错误日志
     * 2. 重试失败的同步
     * 3. 暂停/恢复任务
     *
     * 预期结果：
     * - 错误被正确记录
     * - 支持重试和恢复
     */

    await page.route('**/api/v1/data/cdc/tasks/*/errors', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            errors: [
              { table: 'orders', error_type: 'connection_timeout', count: 5, last_at: new Date().toISOString() }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/cdc/tasks/cdc_001/errors`);

    // 验证错误显示
    await expect(page.locator('text=connection_timeout')).toBeVisible();
    await expect(page.locator('text=orders')).toBeVisible();

    // 点击重试
    await page.click('[data-testid="retry-button"]');

    // 验证重试命令发送
    await expect(page.locator('.toast-message:has-text("重试已启动")')).toBeVisible();
  });

  test('DE-CDC-E-004: Pause and resume CDC task', async ({ page }) => {
    /** 测试场景：暂停和恢复 CDC 任务
     *
     * 前置条件：CDC 任务运行中
     *
     * 测试步骤：
     * 1. 暂停 CDC 任务
     * 2. 验证任务状态
     * 3. 恢复 CDC 任务
     *
     * 预期结果：
     * - 任务正确暂停
     * - 任务正确恢复
     */

    await page.route('**/api/v1/data/cdc/tasks/*/pause', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { status: 'paused' }
        })
      });
    });

    await page.route('**/api/v1/data/cdc/tasks/*/resume', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { status: 'running' }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/cdc/tasks/cdc_001`);

    // 暂停任务
    await page.click('[data-testid="pause-button"]');

    // 验证状态变为 paused
    await expect(page.locator('[data-testid="task-status"]')).toHaveText('paused');

    // 恢复任务
    await page.click('[data-testid="resume-button"]');

    // 验证状态恢复为 running
    await expect(page.locator('[data-testid="task-status"]')).toHaveText('running');
  });
});
