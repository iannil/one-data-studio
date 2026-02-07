/**
 * Kettle ETL 引擎 E2E 测试
 * 测试用例编号: DE-KT-E-001 ~ DE-KT-E-005
 *
 * Kettle ETL 引擎功能测试：
 * - Kettle 作业生成
 * - 作业执行监控
 * - 作业调度
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Kettle ETL Engine', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['kettle:*'] }
        })
      });
    });
  });

  test('DE-KT-E-001: Generate Kettle job from ETL config', async ({ page }) => {
    /** 测试场景：从 ETL 配置生成 Kettle 作业
     *
     * 测试步骤：
     * 1. 创建 ETL 任务
     * 2. 配置转换规则
     * 3. 点击"生成 Kettle 作业"
     * 4. 生成 .kjb 文件
     *
     * 预期结果：
     * - Kettle 作业文件生成成功
     * - 可下载
     */

    await page.route('**/api/v1/data/etl/generate-kettle', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            job_file: 'etl_job_001.kjb',
            download_url: '/api/v1/data/etl/downloads/etl_job_001.kjb'
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/etl`);

    // 点击新建 ETL 任务
    await page.click('[data-testid="create-etl-button"]');

    // 配置转换
    await page.fill('input[name="name"]', '测试ETL任务');
    await page.selectOption('select[name="source_datasource"]', 'ds_mysql_001');
    await page.selectOption('select[name="target_datasource"]', 'ds_clickhouse_001');

    // 添加转换步骤
    await page.click('[data-testid="add-transformation-button"]');
    await page.selectOption('select[name="type"]', 'filter');

    // 生成 Kettle 作业
    await page.click('[data-testid="generate-kettle-button"]');

    // 验证生成成功
    await expect(page.locator('.toast-message:has-text("生成成功")')).toBeVisible();
    await expect(page.locator('text=etl_job_001.kjb')).toBeVisible();
  });

  test('DE-KT-E-002: Execute Kettle job', async ({ page }) => {
    /** 测试场景：执行 Kettle 作业
     *
     * 前置条件：Kettle 作业已生成
     *
     * 测试步骤：
     * 1. 上传或关联 .kjb 文件
     * 2. 配置执行参数
     * 3. 启动执行
     * 4. 查看执行日志
     *
     * 预期结果：
     * - 作业执行成功
     * - 显示执行日志
     */

    await page.route('**/api/v1/data/kettle/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            execution_id: 'kettle_exec_001',
            status: 'running',
            log_url: '/api/v1/data/kettle/logs/kettle_exec_001'
          }
        })
      });
    });

    // Mock 执行日志
    await page.route('**/api/v1/data/kettle/logs/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: '2024/01/01 10:00:00 INFO - Job started\n2024/01/01 10:00:05 INFO - Step 1 completed\n2024/01/01 10:00:10 INFO - Job completed successfully'
      });
    });

    await page.goto(`${BASE_URL}/data/kettle`);

    // 上传作业文件（模拟）
    await page.click('[data-testid="upload-job-button"]');
    await page.setInputFiles('input[type="file"]', {
      name: 'job.kjb',
      mimeType: 'application/xml',
      buffer: Buffer.from('<job></job>')
    });

    // 配置参数
    await page.fill('input[name="param_date"]', '2024-01-01');

    // 执行
    await page.click('[data-testid="execute-button"]');

    // 验证执行启动
    await expect(page.locator('text=running')).toBeVisible();

    // 查看日志
    await page.click('[data-testid="view-logs-button"]');
    await expect(page.locator('text=Job completed successfully')).toBeVisible();
  });

  test('DE-KT-E-003: Schedule Kettle job', async ({ page }) => {
    /** 测试场景：调度 Kettle 作业
     *
     * 测试步骤：
     * 1. 创建 Kettle 作业
     * 2. 配置调度规则（Cron 表达式）
     * 3. 启用调度
     *
     * 预期结果：
     * - 调度配置成功
     * - 作业按计划执行
     */

    await page.route('**/api/v1/data/kettle/schedule', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            schedule_id: 'kettle_sched_001',
            cron_expression: '0 2 * * *',
            next_run: '2024-01-01 02:00:00'
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/kettle`);

    // 点击调度按钮
    await page.click('[data-testid="schedule-button"]');

    // 配置 Cron
    await page.fill('input[name="cron"]', '0 2 * * *');

    // 启用
    await page.check('[data-testid="enabled"]');

    // 保存
    await page.click('button[type="submit"]');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("调度配置成功")')).toBeVisible();
  });

  test('DE-KT-E-004: Monitor Kettle job execution', async ({ page }) => {
    /** 测试场景：监控 Kettle 作业执行
     *
     * 前置条件：作业正在执行
     *
     * 测试步骤：
     * 1. 进入作业详情
     * 2. 查看执行进度
     * 3. 查看步骤执行状态
     *
     * 预期结果：
     * - 显示进度条
     * - 显示各步骤状态
     */

    await page.route('**/api/v1/data/kettle/executions/*/progress', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            execution_id: 'kettle_exec_001',
            progress: 65,
            current_step: 'Step 3: Data Load',
            steps: [
              { name: 'Step 1: Input', status: 'completed', duration_ms: 1000 },
              { name: 'Step 2: Transformation', status: 'completed', duration_ms: 5000 },
              { name: 'Step 3: Data Load', status: 'running', duration_ms: 2000 },
              { name: 'Step 4: Output', status: 'pending', duration_ms: 0 }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/kettle/executions/kettle_exec_001`);

    // 验证进度
    await expect(page.locator('[data-testid="progress-bar"]').toHaveAttribute('value', '65'));

    // 验证步骤状态
    await expect(page.locator('text=Step 1: Input')).toHaveAttribute('data-status', 'completed');
    await expect(page.locator('text=Step 2: Transformation')).toHaveAttribute('data-status', 'completed');
    await expect(page.locator('text=Step 3: Data Load')).toHaveAttribute('data-status', 'running');
  });

  test('DE-KT-E-005: Handle Kettle job failure', async ({ page }) => {
    /** 测试场景：处理 Kettle 作业失败
     *
     * 前置条件：作业执行失败
     *
     * 测试步骤：
     * 1. 查看错误信息
     * 2. 查看失败日志
     * 3. 重试或修复后重执行
     *
     * 预期结果：
     * - 错误信息清晰
     * - 支持查看详细日志
     */

    await page.route('**/api/v1/data/kettle/executions/*/errors', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            error_code: 'CONN_001',
            error_message: '无法连接到目标数据库',
            failed_step: 'Step 3: Data Load',
            logs: [
              { timestamp: '2024-01-01T10:00:05Z', level: 'ERROR', message: 'Connection timeout' }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/kettle/executions/kettle_exec_001/errors`);

    // 验证错误信息
    await expect(page.locator('text=无法连接到目标数据库')).toBeVisible();
    await expect(page.locator('text=Step 3: Data Load')).toBeVisible();

    // 点击查看详细日志
    await page.click('[data-testid="view-detail-logs"]');

    // 验证日志显示
    await expect(page.locator('text=Connection timeout')).toBeVisible();
  });
});
