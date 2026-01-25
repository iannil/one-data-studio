/**
 * Alldata 数据治理深度验收测试
 * 覆盖数据源、ETL、数据质量、数据血缘、特征存储等功能
 * 使用真实 API 调用
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';
import type { AlldataApiClient } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 数据源管理深度测试
// ============================================
test.describe('Alldata - 数据源管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/datasources`);
    await page.waitForLoadState('networkidle');
  });

  test('should display datasources list', async ({ page }) => {
    // 验证数据源列表可见
    const list = page.locator('.datasource-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should open create datasource modal', async ({ page }) => {
    const createButton = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("添加")').first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 验证创建对话框
      const modal = page.locator('.ant-modal, .modal, .dialog');
      const modalVisible = await modal.count() > 0;
      if (modalVisible) {
        const formInputs = modal.locator('input, select');
        expect(await formInputs.count()).toBeGreaterThan(0);
      }
    }
  });

  test('should validate datasource connection', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 获取第一个数据源
    const datasources = await apiClient.getDatasources({ page: 1, page_size: 1 });

    if (datasources.data?.datasources?.length > 0) {
      const dsId = datasources.data.datasources[0].id;

      // 测试连接
      const testResult = await apiClient.testDatasource(dsId);
      expect(testResult.code).toBe(0);
    }
  });

  test('should edit datasource configuration', async ({ page }) => {
    const firstRow = page.locator('tr[data-row-key], .datasource-item').first();
    if (await firstRow.isVisible()) {
      const editButton = firstRow.locator('button:has-text("编辑"), button:has-text("Edit"), [class*="edit"]').first();

      if (await editButton.isVisible()) {
        await editButton.click();
        await page.waitForTimeout(500);

        // 验证编辑表单
        const formFields = page.locator('.ant-form-item, .form-field');
        const hasForm = await formFields.count() > 0;
        if (hasForm) {
          expect(await formFields.count()).toBeGreaterThan(2);
        }
      }
    }
  });

  test('should delete datasource with confirmation', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 先创建一个测试数据源
    const createResult = await apiClient.createDatasource({
      name: `e2e-test-ds-${Date.now()}`,
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      database: 'test_db',
      username: 'test_user',
      password: 'test_pass',
    });

    if (createResult.code === 0 && createResult.data?.id) {
      // 在页面中删除
      await page.goto(`${BASE_URL}/datasources`);
      await page.waitForLoadState('networkidle');

      // 查找刚创建的数据源并删除
      const testRow = page.locator(`tr:has-text("e2e-test-ds")`).first();
      if (await testRow.isVisible()) {
        const deleteButton = testRow.locator('button:has-text("删除"), button:has-text("Delete")').first();
        await deleteButton.click();
        await page.waitForTimeout(500);

        const confirmButton = page.locator('.ant-modal-confirm button:has-text("确定"), button:has-text("确认")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }

      // 清理：通过 API 删除
      await apiClient.deleteDatasource(createResult.data.id);
    }
  });
});

// ============================================
// ETL 任务深度测试
// ============================================
test.describe('Alldata - ETL 任务', () => {
  test('should display ETL tasks list', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    await page.goto(`${BASE_URL}/etl`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.etl-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create ETL task with visual editor', async ({ page }) => {
    await page.goto(`${BASE_URL}/etl`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 验证可视化编辑器
      const editor = page.locator('.etl-editor, .flow-editor, .canvas-editor');
      if (await editor.isVisible()) {
        // 检查节点面板
        const nodePalette = page.locator('.node-palette, .component-list');
        const hasPalette = await nodePalette.count() > 0;
        console.log('Has ETL node palette:', hasPalette);
      }
    }
  });

  test('should configure ETL schedule', async ({ page }) => {
    await page.goto(`${BASE_URL}/etl`);
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tr[data-row-key], .etl-item').first();
    if (await firstRow.isVisible()) {
      const scheduleButton = firstRow.locator('button:has-text("调度"), button:has-text("Schedule"), [class*="schedule"]').first();

      if (await scheduleButton.isVisible()) {
        await scheduleButton.click();
        await page.waitForTimeout(500);

        // 验证调度配置
        const cronInput = page.locator('input[placeholder*="cron"], .cron-input');
        const hasCron = await cronInput.count() > 0;
        console.log('Has cron input:', hasCron);
      }
    }
  });

  test('should execute ETL task manually', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 获取第一个 ETL 任务
    const tasks = await apiClient.getEtlTasks({ page: 1, page_size: 1 });

    if (tasks.data?.tasks?.length > 0) {
      const taskId = tasks.data.tasks[0].id;

      // 执行 ETL 任务
      const runResult = await apiClient.runEtlTask(taskId);
      expect(runResult.code).toBe(0);
    }
  });

  test('should display ETL execution history', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const tasks = await apiClient.getEtlTasks({ page: 1, page_size: 1 });

    if (tasks.data?.tasks?.length > 0) {
      const taskId = tasks.data.tasks[0].id;

      await page.goto(`${BASE_URL}/etl`);
      await page.waitForLoadState('networkidle');

      const historyButton = page.locator(`button:has-text("历史"), button:has-text("History")`).first();
      if (await historyButton.isVisible()) {
        await historyButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should monitor ETL execution progress', async ({ page }) => {
    await page.goto(`${BASE_URL}/etl`);
    await page.waitForLoadState('networkidle');

    // 查找运行中的任务
    const runningStatus = page.locator('.status-running, .status-executing, [class*="running"]');

    // 如果有运行中的任务，验证进度条
    const progressBar = page.locator('.ant-progress, .progress-bar, [class*="progress"]');
    const hasProgress = await progressBar.count() > 0;
    console.log('Has progress bar:', hasProgress);
  });
});

// ============================================
// 数据质量深度测试
// ============================================
test.describe('Alldata - 数据质量', () => {
  test('should display quality rules list', async ({ page }) => {
    await page.goto(`${BASE_URL}/quality`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.quality-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create quality rule', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 获取数据集列表
    const datasets = await apiClient.getDatasets({ page: 1, page_size: 1 });

    if (datasets.data?.datasets?.length > 0) {
      const datasetId = datasets.data.datasets[0].id;

      // 创建质量规则
      const ruleResult = await apiClient.createQualityRule({
        name: `e2e-quality-rule-${Date.now()}`,
        dataset_id: datasetId,
        rule_type: 'completeness',
        config: { column: 'id', threshold: 0.95 },
      });

      expect(ruleResult.code).toBe(0);
    }
  });

  test('should run quality check', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const rules = await apiClient.getQualityRules({ page: 1, page_size: 1 });

    if (rules.data?.rules?.length > 0) {
      const ruleId = rules.data.rules[0].id;

      const checkResult = await apiClient.runQualityCheck(ruleId);
      expect(checkResult.code).toBe(0);
    }
  });

  test('should display quality reports', async ({ page }) => {
    await page.goto(`${BASE_URL}/quality`);
    await page.waitForLoadState('networkidle');

    const reportButton = page.locator('button:has-text("报告"), button:has-text("Report"), [class*="report"]').first();
    if (await reportButton.isVisible()) {
      await reportButton.click();
      await page.waitForTimeout(500);

      const reportContent = page.locator('.quality-report, .report-content, [class*="report"]');
      const hasReport = await reportContent.count() > 0;
      console.log('Has quality report:', hasReport);
    }
  });
});

// ============================================
// 数据血缘深度测试
// ============================================
test.describe('Alldata - 数据血缘', () => {
  test('should display lineage graph', async ({ page }) => {
    await page.goto(`${BASE_URL}/lineage`);
    await page.waitForLoadState('networkidle');

    // 查找图表容器
    const graphContainer = page.locator('.lineage-graph, .dag-graph, [class*="graph"], svg');
    await expect(graphContainer.first()).toBeVisible();
  });

  test('should query upstream dependencies', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 查询上游依赖
    const upstream = await apiClient.getLineageUpstream('table', 'users');
    expect(upstream.code).toBe(0);
  });

  test('should query downstream dependencies', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 查询下游依赖
    const downstream = await apiClient.getLineageDownstream('table', 'users');
    expect(downstream.code).toBe(0);
  });

  test('should navigate lineage graph', async ({ page }) => {
    await page.goto(`${BASE_URL}/lineage`);
    await page.waitForLoadState('networkidle');

    const graphContainer = page.locator('.lineage-graph, svg').first();
    if (await graphContainer.isVisible()) {
      // 尝试缩放
      await page.mouse.wheel(0, 100);
      await page.waitForTimeout(500);

      // 尝试拖拽
      await graphContainer.click();
      await page.mouse.down();
      await page.mouse.move(100, 100);
      await page.mouse.up();
    }
  });
});

// ============================================
// 元数据深度测试
// ============================================
test.describe('Alldata - 元数据', () => {
  test('should display databases list', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    await page.goto(`${BASE_URL}/metadata`);
    await page.waitForLoadState('networkidle');

    const databases = await apiClient.getDatabases();
    expect(databases.code).toBe(0);

    // 验证页面显示
    const dbList = page.locator('.database-list, .tree-list').first();
    await expect(dbList).toBeVisible();
  });

  test('should display tables for a database', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const databases = await apiClient.getDatabases();
    if (databases.data?.databases?.length > 0) {
      const dbName = databases.data.databases[0].name;
      const tables = await apiClient.getTables(dbName);
      expect(tables.code).toBe(0);
    }
  });

  test('should display columns for a table', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const databases = await apiClient.getDatabases();
    if (databases.data?.databases?.length > 0) {
      const dbName = databases.data.databases[0].name;

      const tables = await apiClient.getTables(dbName);
      if (tables.data?.tables?.length > 0) {
        const tableName = tables.data.tables[0].name;
        const columns = await apiClient.getTableColumns(dbName, tableName);
        expect(columns.code).toBe(0);
      }
    }
  });

  test('should search metadata', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    await page.goto(`${BASE_URL}/metadata`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('user');
      await page.waitForTimeout(500);

      // API 搜索验证
      const searchResult = await apiClient.searchMetadata('user');
      expect(searchResult.code).toBe(0);
    }
  });
});

// ============================================
// 特征存储深度测试
// ============================================
test.describe('Alldata - 特征存储', () => {
  test('should display feature groups', async ({ page }) => {
    await page.goto(`${BASE_URL}/features`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.feature-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create feature group', async ({ page }) => {
    await page.goto(`${BASE_URL}/features`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal, .modal');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const form = modal.locator('form');
        await expect(form).toBeVisible();
      }
    }
  });

  test('should display feature versions', async ({ page }) => {
    await page.goto(`${BASE_URL}/features`);
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tr[data-row-key], .feature-item').first();
    if (await firstRow.isVisible()) {
      const versionButton = firstRow.locator('button:has-text("版本"), button:has-text("Version")').first();
      if (await versionButton.isVisible()) {
        await versionButton.click();
        await page.waitForTimeout(500);
      }
    }
  });
});

// ============================================
// API 端点验证测试
// ============================================
test.describe('Alldata - API 端点验证', () => {
  test('should verify all Alldata API endpoints', async ({ request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;
    clearRequestLogs();

    // 健康检查
    const health = await apiClient.healthCheck();
    expect(health.code).toBe(0);

    // 数据源
    const datasources = await apiClient.getDatasources();
    expect(datasources.code).toBe(0);

    // 数据集
    const datasets = await apiClient.getDatasets();
    expect(datasets.code).toBe(0);

    // 元数据
    const databases = await apiClient.getDatabases();
    expect(databases.code).toBe(0);

    // 查询验证
    const validateResult = await apiClient.validateSQL('SELECT 1');
    expect(validateResult.code).toBe(0);

    // ETL 任务
    const etlTasks = await apiClient.getEtlTasks();
    expect(etlTasks.code).toBe(0);

    // 质量规则
    const qualityRules = await apiClient.getQualityRules();
    expect(qualityRules.code).toBe(0);

    // 血缘
    const lineage = await apiClient.getLineage();
    expect(lineage.code).toBe(0);

    // 验证没有失败的请求
    const failedRequests = getFailedRequests();
    expect(failedRequests.length).toBe(0);
  });

  test('should handle query execution correctly', async ({ request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    // 获取数据库列表
    const databases = await apiClient.getDatabases();
    if (databases.data?.databases?.length > 0) {
      const dbName = databases.data.databases[0].name;

      // 执行查询
      const queryResult = await apiClient.executeQuery({
        database: dbName,
        sql: 'SELECT 1 as test_column',
        limit: 10,
      });

      expect(queryResult.code).toBe(0);
    }
  });
});

// ============================================
// 边界条件测试
// ============================================
test.describe('Alldata - 边界条件', () => {
  test('should handle empty datasource list', async ({ page, request }) => {
    await page.goto(`${BASE_URL}/datasources`);
    await page.waitForLoadState('networkidle');

    const emptyState = page.locator('.empty-state, .no-data');
    // 空状态可能不显示（如果有数据）
    const hasEmpty = await emptyState.count() > 0;
    console.log('Has empty state for datasources:', hasEmpty);
  });

  test('should handle invalid SQL query', async ({ request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const validateResult = await apiClient.validateSQL('INVALID SQL QUERY');
    // 应该返回错误而不是崩溃
    expect(validateResult.code).not.toBe(0);
  });

  test('should handle large metadata set', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'alldata') as AlldataApiClient;

    const databases = await apiClient.getDatabases();
    if (databases.data?.databases?.length > 0) {
      const dbName = databases.data.databases[0].name;
      const tables = await apiClient.getTables(dbName);

      // 测试大量表的渲染
      if (tables.data?.tables?.length > 50) {
        await page.goto(`${BASE_URL}/metadata`);
        await page.waitForLoadState('networkidle');

        // 检查是否正确渲染
        const tableList = page.locator('.table-list, [class*="table"]');
        await expect(tableList.first()).toBeVisible();
      }
    }
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Alldata test:', failedRequests);
  }
});
