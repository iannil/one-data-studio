/**
 * 数据分析师角色 E2E 测试
 * 测试用例编号: AN-BI-E-001 ~ AN-SQ-E-005
 *
 * 数据分析师功能测试：
 * - BI 报表创建和查看
 * - 指标定义和监控
 * - SQL 查询执行
 */

import { test, expect } from '@playwright/test';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ==================== 测试套件 ====================

test.describe('Data Analyst - BI Dashboards', () => {
  test.beforeEach(async ({ page }) => {
    // 设置数据分析师权限 Mock
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['bi:*', 'metrics:*', 'sql:execute']
          }
        })
      });
    });
  });

  test('AN-BI-E-001: Create BI dashboard', async ({ page }) => {
    /** 测试场景：创建 BI 仪表板
     *
     * 前置条件：
     * - 用户为数据分析师角色
     *
     * 测试步骤：
     * 1. 导航到 BI 页面
     * 2. 点击"新建仪表板"
     * 3. 填写仪表板信息
     * 4. 保存
     *
     * 预期结果：
     * - 仪表板创建成功
     * - 显示在列表中
     */

    // Mock API
    await page.route('**/api/v1/data/bi/dashboards', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              dashboard_id: 'dash_001',
              name: '销售分析仪表板',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { dashboards: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/data/bi`);

    // 点击新建仪表板
    await page.click('[data-testid="create-dashboard-button"]');

    // 填写信息
    await page.fill('input[name="name"]', '销售分析仪表板');
    await page.fill('textarea[name="description"]', '销售数据分析看板');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('AN-BI-E-002: Add chart to dashboard', async ({ page }) => {
    /** 测试场景：向仪表板添加图表
     *
     * 前置条件：
     * - 仪表板已创建
     *
     * 测试步骤：
     * 1. 进入仪表板详情
     * 2. 点击"添加图表"
     * 3. 选择图表类型
     * 4. 配置数据源
     * 5. 保存
     *
     * 预期结果：
     * - 图表添加成功
     */

    // Mock 图表创建 API
    await page.route('**/api/v1/data/bi/charts', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            chart_id: 'chart_001',
            name: '销售额趋势',
            chart_type: 'line',
            created_at: new Date().toISOString()
          }
        })
      });
    });

    // Mock 仪表板数据
    await page.route('**/api/v1/data/bi/dashboards/dash_001', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            dashboard_id: 'dash_001',
            name: '销售分析仪表板',
            charts: []
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/bi/dashboards/dash_001`);

    // 点击添加图表
    await page.click('[data-testid="add-chart-button"]');

    // 选择图表类型
    await page.selectOption('select[name="chart_type"]', 'line');

    // 填写图表信息
    await page.fill('input[name="name"]', '销售额趋势');
    await page.fill('textarea[name="sql_query"]', 'SELECT date, SUM(amount) FROM sales GROUP BY date');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("添加成功")')).toBeVisible();
  });

  test('AN-BI-E-003: View dashboard with charts', async ({ page }) => {
    /** 测试场景：查看仪表板和图表
     *
     * 前置条件：
     * - 仪表板已创建并添加图表
     *
     * 测试步骤：
     * 1. 导航到仪表板详情
     * 2. 查看图表显示
     *
     * 预期结果：
     * - 仪表板正常显示
     * - 图表数据正确加载
     */

    // Mock 仪表板数据
    await page.route('**/api/v1/data/bi/dashboards/dash_001', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            dashboard_id: 'dash_001',
            name: '销售分析仪表板',
            charts: [
              { chart_id: 'chart_001', name: '销售额趋势', chart_type: 'line' },
              { chart_id: 'chart_002', name: '区域对比', chart_type: 'bar' }
            ]
          }
        })
      });
    });

    // Mock 图表数据
    await page.route('**/api/v1/data/bi/charts/*/data', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            dimensions: ['2024-01', '2024-02', '2024-03'],
            series: [
              { name: '销售额', data: [12000, 15000, 18000] }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/bi/dashboards/dash_001`);

    // 验证仪表板标题
    await expect(page.locator('text=销售分析仪表板')).toBeVisible();

    // 验证图表显示
    await expect(page.locator('text=销售额趋势')).toBeVisible();
    await expect(page.locator('text=区域对比')).toBeVisible();
  });
});

test.describe('Data Analyst - Metrics', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['metrics:*'] }
        })
      });
    });
  });

  test('AN-MS-E-001: Create metric definition', async ({ page }) => {
    /** 测试场景：创建指标定义
     *
     * 测试步骤：
     * 1. 导航到指标管理页面
     * 2. 点击"新建指标"
     * 3. 填写指标信息
     * 4. 编写计算 SQL
     * 5. 保存
     *
     * 预期结果：
     * - 指标创建成功
     */

    // Mock API
    await page.route('**/api/v1/data/metrics', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              metric_id: 'metric_001',
              name: '日活跃用户数',
              code: 'DAU',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { metrics: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/data/metrics`);

    // 点击新建指标
    await page.click('[data-testid="create-metric-button"]');

    // 填写信息
    await page.fill('input[name="name"]', '日活跃用户数');
    await page.fill('input[name="code"]', 'DAU');
    await page.selectOption('select[name="category"]', 'business');
    await page.fill('textarea[name="calculation_sql"]', 'SELECT COUNT(DISTINCT user_id) FROM user_events WHERE event_date = {date}');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('AN-MS-E-002: View metric values and trends', async ({ page }) => {
    /** 测试场景：查看指标值和趋势
     *
     * 前置条件：
     * - 指标已创建
     *
     * 测试步骤：
     * 1. 进入指标详情
     * 2. 查看当前值
     * 3. 查看趋势图
     *
     * 预期结果：
     * - 显示指标值
     * - 显示趋势图
     */

    // Mock 指标数据
    await page.route('**/api/v1/data/metrics/metric_001', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            metric_id: 'metric_001',
            name: '日活跃用户数',
            code: 'DAU',
            current_value: 125000,
            trend: '+5%',
            time_series: [
              { date: '2024-01-01', value: 120000 },
              { date: '2024-01-02', value: 125000 },
              { date: '2024-01-03', value: 118000 }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/metrics/metric_001`);

    // 验证指标值显示
    await expect(page.locator('text=125000')).toBeVisible();
    await expect(page.locator('text=+5%')).toBeVisible();
  });
});

test.describe('Data Analyst - SQL Lab', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['sql:execute'] }
        })
      });
    });
  });

  test('AN-SQ-E-001: Execute SQL query', async ({ page }) => {
    /** 测试场景：执行 SQL 查询
     *
     * 测试步骤：
     * 1. 导航到 SQL Lab 页面
     * 2. 选择数据源
     * 3. 输入 SQL 查询
     * 4. 点击执行
     *
     * 预期结果：
     * - 查询成功执行
     * - 显示结果表格
     */

    // Mock 查询 API
    await page.route('**/api/v1/data/sql/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            query_id: 'q_001',
            status: 'completed',
            columns: ['id', 'name', 'amount'],
            rows: [
              [1, '订单A', 1200.00],
              [2, '订单B', 800.50],
              [3, '订单C', 2500.00]
            ],
            row_count: 3,
            execution_time_ms: 150
          }
        })
      });
    });

    // Mock 数据源列表
    await page.route('**/api/v1/data/datasources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            datasources: [
              { id: 'ds_001', name: 'MySQL主库', type: 'mysql' }
            ]
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/sql-lab`);

    // 选择数据源
    await page.selectOption('select[name="datasource"]', 'ds_001');

    // 输入 SQL
    await page.fill('textarea[name="sql"]', 'SELECT * FROM orders LIMIT 10');

    // 执行查询
    await page.click('[data-testid="execute-query-button"]');

    // 验证结果显示
    await expect(page.locator('text=订单A')).toBeVisible();
    await expect(page.locator('text=1200')).toBeVisible();
  });

  test('AN-SQ-E-002: Save SQL query', async ({ page }) => {
    /** 测试场景：保存 SQL 查询
     *
     * 前置条件：
     * - 查询已执行
     *
     * 测试步骤：
     * 1. 点击"保存查询"按钮
     * 2. 输入查询名称
     * 3. 保存
     *
     * 预期结果：
     * - 查询保存成功
     * - 出现在已保存查询列表中
     */

    // Mock 保存 API
    await page.route('**/api/v1/data/sql/saved-queries', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              saved_query_id: 'sq_001',
              name: '日销售额查询',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { saved_queries: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/data/sql-lab`);

    // 输入查询
    await page.fill('textarea[name="sql"]', 'SELECT date, SUM(amount) FROM orders GROUP BY date');

    // 点击保存
    await page.click('[data-testid="save-query-button"]');

    // 填写名称
    await page.fill('input[name="query_name"]', '日销售额查询');

    // 确认保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("保存成功")')).toBeVisible();
  });

  test('AN-SQ-E-003: Export query results', async ({ page }) => {
    /** 测试场景：导出查询结果
     *
     * 前置条件：
     * - 查询已执行
     *
     * 测试步骤：
     * 1. 点击"导出"按钮
     * 2. 选择导出格式（CSV/Excel/JSON）
     * 3. 确认导出
     *
     * 预期结果：
     * - 文件下载开始
     */

    // Mock 导出 API
    await page.route('**/api/v1/data/sql/exports', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            export_id: 'exp_001',
            download_url: '/api/v1/data/sql/exports/exp_001/download',
            file_size: 2048
          }
        })
      });
    });

    // 先执行查询
    await page.route('**/api/v1/data/sql/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            query_id: 'q_001',
            status: 'completed',
            columns: ['id', 'name'],
            rows: [[1, 'A']],
            row_count: 1
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/data/sql-lab`);

    // 执行查询
    await page.fill('textarea[name="sql"]', 'SELECT * FROM users LIMIT 1');
    await page.click('[data-testid="execute-query-button"]');

    // 等待结果显示
    await page.waitForTimeout(500);

    // 点击导出按钮
    await page.click('[data-testid="export-button"]');

    // 选择格式
    await page.selectOption('select[name="format"]', 'csv');

    // 确认导出
    await page.click('button:has-text("导出")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("导出成功")')).toBeVisible();
  });
});
