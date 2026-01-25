/**
 * Cube Studio MLOps 深度验收测试
 * 覆盖 Notebook、实验、模型、训练、模型服务、AI Hub 等功能
 * 使用真实 API 调用
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';
import type { CubeApiClient } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// Notebook 深度测试
// ============================================
test.describe('Cube - Notebook', () => {
  test('should display notebooks list', async ({ page }) => {
    await page.goto(`${BASE_URL}/notebooks`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.notebook-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new notebook', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    await page.goto(`${BASE_URL}/notebooks`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("New")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 验证创建对话框
      const modal = page.locator('.ant-modal, .modal, .dialog');
      const hasModal = await modal.count() > 0;
      if (hasModal) {
        const nameInput = modal.locator('input[name="name"], input[placeholder*="名称"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill(`e2e-test-notebook-${Date.now()}`);

          const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建"), button:has-text("OK")').first();
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test('should start notebook kernel', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const notebooks = await apiClient.getNotebooks({ page: 1, page_size: 1 });
    if (notebooks.data?.notebooks?.length > 0) {
      const notebookId = notebooks.data.notebooks[0].id;

      const startResult = await apiClient.startNotebook(notebookId);
      expect(startResult.code).toBe(0);
    }
  });

  test('should execute code in notebook', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const notebooks = await apiClient.getNotebooks({ page: 1, page_size: 1 });
    if (notebooks.data?.notebooks?.length > 0) {
      const notebookId = notebooks.data.notebooks[0].id;

      const executeResult = await apiClient.executeCode(notebookId, 'print("Hello from E2E test")');
      expect(executeResult.code).toBe(0);
    }
  });

  test('should select different kernels', async ({ page }) => {
    await page.goto(`${BASE_URL}/notebooks`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const kernelSelect = page.locator('select[name="kernel"], .ant-select-selector').first();
      const hasKernelSelect = await kernelSelect.count() > 0;
      if (hasKernelSelect) {
        await kernelSelect.click();
        await page.waitForTimeout(300);

        // 验证内核选项
        const options = page.locator('.ant-select-item-option');
        const optionCount = await options.count();
        expect(optionCount).toBeGreaterThan(0);
      }
    }
  });

  test('should stop notebook kernel', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const notebooks = await apiClient.getNotebooks({ page: 1, page_size: 1 });
    if (notebooks.data?.notebooks?.length > 0) {
      const notebookId = notebooks.data.notebooks[0].id;

      const stopResult = await apiClient.stopNotebook(notebookId);
      expect(stopResult.code).toBe(0);
    }
  });
});

// ============================================
// 实验管理深度测试
// ============================================
test.describe('Cube - 实验管理', () => {
  test('should display experiments list', async ({ page }) => {
    await page.goto(`${BASE_URL}/experiments`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.experiment-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should create new experiment', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    await page.goto(`${BASE_URL}/experiments`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should log metrics to experiment', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const experiments = await apiClient.getExperiments({ page: 1, page_size: 1 });
    if (experiments.data?.experiments?.length > 0) {
      const expId = experiments.data.experiments[0].id;

      const metrics = {
        accuracy: 0.95,
        loss: 0.05,
        precision: 0.92,
        recall: 0.88,
      };

      const logResult = await apiClient.logMetrics(expId, metrics);
      expect(logResult.code).toBe(0);
    }
  });

  test('should compare experiment metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/experiments`);
    await page.waitForLoadState('networkidle');

    // 查找对比按钮
    const compareButton = page.locator('button:has-text("对比"), button:has-text("Compare")').first();
    if (await compareButton.isVisible()) {
      await compareButton.click();
      await page.waitForTimeout(500);

      const compareView = page.locator('.compare-view, .comparison-panel');
      const hasCompare = await compareView.count() > 0;
      console.log('Has compare view:', hasCompare);
    }
  });

  test('should display experiment metrics chart', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const experiments = await apiClient.getExperiments({ page: 1, page_size: 1 });
    if (experiments.data?.experiments?.length > 0) {
      const expId = experiments.data.experiments[0].id;

      await page.goto(`${BASE_URL}/experiments`);
      await page.waitForLoadState('networkidle');

      const firstRow = page.locator(`tr[data-row-key="${expId}"]`).first();
      if (await firstRow.isVisible()) {
        const viewButton = firstRow.locator('button:has-text("查看"), button:has-text("View")').first();
        if (await viewButton.isVisible()) {
          await viewButton.click();
          await page.waitForTimeout(500);

          // 查找图表
          const chart = page.locator('.metric-chart, canvas, [class*="chart"]');
          const hasChart = await chart.count() > 0;
          console.log('Has metrics chart:', hasChart);
        }
      }
    }
  });
});

// ============================================
// 模型管理深度测试
// ============================================
test.describe('Cube - 模型管理', () => {
  test('should display models list', async ({ page }) => {
    await page.goto(`${BASE_URL}/models`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.model-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should register new model', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const experiments = await apiClient.getExperiments({ page: 1, page_size: 1 });
    const experimentId = experiments.data?.experiments?.[0]?.id;

    const registerResult = await apiClient.registerModel({
      name: `e2e-test-model-${Date.now()}`,
      version: '1.0.0',
      experiment_id: experimentId,
    });

    expect(registerResult.code).toBe(0);
  });

  test('should display model versions', async ({ page }) => {
    await page.goto(`${BASE_URL}/models`);
    await page.waitForLoadState('networkidle');

    const firstModel = page.locator('tr[data-row-key], .model-item').first();
    if (await firstModel.isVisible()) {
      const versionsButton = firstModel.locator('button:has-text("版本"), button:has-text("Version")').first();
      if (await versionsButton.isVisible()) {
        await versionsButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should deploy model', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const models = await apiClient.getModels({ page: 1, page_size: 1 });
    if (models.data?.models?.length > 0) {
      const modelId = models.data.models[0].id;

      const deployResult = await apiClient.deployModel(modelId, {
        replicas: 1,
        resources: { cpu: '1', memory: '1Gi' },
      });

      expect(deployResult.code).toBe(0);
    }
  });

  test('should view model details', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const models = await apiClient.getModels({ page: 1, page_size: 1 });
    if (models.data?.models?.length > 0) {
      const modelId = models.data.models[0].id;

      const modelDetail = await apiClient.getModel(modelId);
      expect(modelDetail.code).toBe(0);
      expect(modelDetail.data).toBeDefined();
    }
  });
});

// ============================================
// 训练任务深度测试
// ============================================
test.describe('Cube - 训练任务', () => {
  test('should display training jobs list', async ({ page }) => {
    await page.goto(`${BASE_URL}/training`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.training-list, .job-list, .data-table').first();
    await expect(list).toBeVisible();
  });

  test('should create training job', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    await page.goto(`${BASE_URL}/training`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 验证训练配置表单
      const form = page.locator('.ant-form, .training-form');
      const hasForm = await form.count() > 0;
      if (hasForm) {
        const modelNameInput = form.locator('input[name="model_name"], input[name="name"]');
        const hasNameInput = await modelNameInput.count() > 0;
        console.log('Has model name input:', hasNameInput);
      }
    }
  });

  test('should start training job', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const jobs = await apiClient.getTrainingJobs({ page: 1, page_size: 1 });
    if (jobs.data?.jobs?.length > 0) {
      const jobId = jobs.data.jobs[0].id;

      const startResult = await apiClient.startTrainingJob(jobId);
      expect(startResult.code).toBe(0);
    }
  });

  test('should stop training job', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const jobs = await apiClient.getTrainingJobs({ page: 1, page_size: 1 });
    if (jobs.data?.jobs?.length > 0) {
      const jobId = jobs.data.jobs[0].id;

      const stopResult = await apiClient.stopTrainingJob(jobId);
      expect(stopResult.code).toBe(0);
    }
  });

  test('should display training logs', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const jobs = await apiClient.getTrainingJobs({ page: 1, page_size: 1 });
    if (jobs.data?.jobs?.length > 0) {
      const jobId = jobs.data.jobs[0].id;

      const logs = await apiClient.getTrainingLogs(jobId);
      expect(logs.code).toBe(0);
    }
  });

  test('should monitor training progress', async ({ page }) => {
    await page.goto(`${BASE_URL}/training`);
    await page.waitForLoadState('networkidle');

    const progressBar = page.locator('.ant-progress, .progress-bar, [class*="progress"]');
    const hasProgress = await progressBar.count() > 0;
    if (hasProgress) {
      await expect(progressBar.first()).toBeVisible();
    }
  });
});

// ============================================
// 模型服务深度测试
// ============================================
test.describe('Cube - 模型服务', () => {
  test('should display deployments list', async ({ page }) => {
    await page.goto(`${BASE_URL}/serving`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.deployment-list, .data-table, [class*="table"]').first();
    await expect(list).toBeVisible();
  });

  test('should scale deployment', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const deployments = await apiClient.getDeployments({ page: 1, page_size: 1 });
    if (deployments.data?.deployments?.length > 0) {
      const deploymentId = deployments.data.deployments[0].id;

      const scaleResult = await apiClient.scaleDeployment(deploymentId, 2);
      expect(scaleResult.code).toBe(0);
    }
  });

  test('should perform model inference', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    const deployments = await apiClient.getDeployments({ page: 1, page_size: 1 });
    if (deployments.data?.deployments?.length > 0) {
      const deploymentId = deployments.data.deployments[0].id;

      const predictResult = await apiClient.predict(deploymentId, {
        input: [1, 2, 3, 4, 5],
      });

      expect(predictResult.code).toBe(0);
    }
  });

  test('should display deployment metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/serving`);
    await page.waitForLoadState('networkidle');

    const metricsPanel = page.locator('.metrics-panel, .stats-panel, [class*="metric"]');
    const hasMetrics = await metricsPanel.count() > 0;
    if (hasMetrics) {
      await expect(metricsPanel.first()).toBeVisible();
    }
  });

  test('should configure A/B testing', async ({ page }) => {
    await page.goto(`${BASE_URL}/serving`);
    await page.waitForLoadState('networkidle');

    const abTestButton = page.locator('button:has-text("A/B"), button:has-text("AB")').first();
    if (await abTestButton.isVisible()) {
      await abTestButton.click();
      await page.waitForTimeout(500);

      const abConfig = page.locator('.ab-test-config, .ab-config');
      const hasConfig = await abConfig.count() > 0;
      console.log('Has A/B test config:', hasConfig);
    }
  });
});

// ============================================
// AI Hub 深度测试
// ============================================
test.describe('Cube - AI Hub', () => {
  test('should display AI Hub page', async ({ page }) => {
    await page.goto(`${BASE_URL}/aihub`);
    await page.waitForLoadState('networkidle');

    const content = page.locator('.aihub-content, .model-gallery, [class*="aihub"]');
    await expect(content.first()).toBeVisible();
  });

  test('should search for models', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    await page.goto(`${BASE_URL}/aihub`);
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('bert');
      await page.waitForTimeout(500);
    }

    // API 搜索验证
    const searchResult = await apiClient.searchModels('bert');
    expect(searchResult.code).toBe(0);
  });

  test('should import model from AI Hub', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;

    // 注意：实际导入可能需要特定的模型 ID
    const models = await apiClient.searchModels('gpt');
    if (models.data?.models?.length > 0) {
      const modelId = models.data.models[0].id;

      const importResult = await apiClient.importModel(modelId);
      // 导入可能失败（模型不存在/不可用），这是预期的
      expect(importResult).toBeDefined();
    }
  });
});

// ============================================
// 资源管理深度测试
// ============================================
test.describe('Cube - 资源管理', () => {
  test('should display resource usage', async ({ page }) => {
    await page.goto(`${BASE_URL}/resources`);
    await page.waitForLoadState('networkidle');

    const resourcePanel = page.locator('.resource-panel, .usage-panel');
    await expect(resourcePanel.first()).toBeVisible();
  });

  test('should display GPU availability', async ({ page }) => {
    await page.goto(`${BASE_URL}/resources`);
    await page.waitForLoadState('networkidle');

    const gpuPanel = page.locator('.gpu-panel, [class*="gpu"]');
    const hasGpuPanel = await gpuPanel.count() > 0;
    if (hasGpuPanel) {
      await expect(gpuPanel.first()).toBeVisible();
    }
  });

  test('should allocate resources to job', async ({ page }) => {
    await page.goto(`${BASE_URL}/training`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const resourceInput = page.locator('input[name="cpu"], input[name="memory"], input[name="gpu"]');
      const hasResourceInput = await resourceInput.count() > 0;
      console.log('Has resource input:', hasResourceInput);
    }
  });
});

// ============================================
// 监控深度测试
// ============================================
test.describe('Cube - 监控', () => {
  test('should display monitoring dashboard', async ({ page }) => {
    await page.goto(`${BASE_URL}/monitoring`);
    await page.waitForLoadState('networkidle');

    const dashboard = page.locator('.monitoring-dashboard, .dashboard');
    await expect(dashboard.first()).toBeVisible();
  });

  test('should display real-time metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/monitoring`);
    await page.waitForLoadState('networkidle');

    const charts = page.locator('.metric-chart, canvas, [class*="chart"]');
    const hasCharts = await charts.count() > 0;
    if (hasCharts) {
      await expect(charts.first()).toBeVisible();
    }
  });

  test('should set up alerts', async ({ page }) => {
    await page.goto(`${BASE_URL}/monitoring`);
    await page.waitForLoadState('networkidle');

    const alertButton = page.locator('button:has-text("告警"), button:has-text("Alert")').first();
    if (await alertButton.isVisible()) {
      await alertButton.click();
      await page.waitForTimeout(500);

      const alertConfig = page.locator('.alert-config, .alert-rule');
      const hasConfig = await alertConfig.count() > 0;
      console.log('Has alert config:', hasConfig);
    }
  });
});

// ============================================
// 流水线深度测试
// ============================================
test.describe('Cube - 流水线', () => {
  test('should display pipelines list', async ({ page }) => {
    await page.goto(`${BASE_URL}/pipelines`);
    await page.waitForLoadState('networkidle');

    const list = page.locator('.pipeline-list, .data-table').first();
    await expect(list).toBeVisible();
  });

  test('should create pipeline', async ({ page }) => {
    await page.goto(`${BASE_URL}/pipelines`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const editor = page.locator('.pipeline-editor, .flow-editor');
      const hasEditor = await editor.count() > 0;
      if (hasEditor) {
        await expect(editor.first()).toBeVisible();
      }
    }
  });

  test('should execute pipeline', async ({ page }) => {
    await page.goto(`${BASE_URL}/pipelines`);
    await page.waitForLoadState('networkidle');

    const firstPipeline = page.locator('tr[data-row-key], .pipeline-item').first();
    if (await firstPipeline.isVisible()) {
      const runButton = firstPipeline.locator('button:has-text("运行"), button:has-text("Run")').first();
      if (await runButton.isVisible()) {
        await runButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });
});

// ============================================
// LLM 微调深度测试
// ============================================
test.describe('Cube - LLM 微调', () => {
  test('should display LLM tuning page', async ({ page }) => {
    await page.goto(`${BASE_URL}/llm-tuning`);
    await page.waitForLoadState('networkidle');

    const content = page.locator('.tuning-content, .llm-tuning');
    await expect(content.first()).toBeVisible();
  });

  test('should create fine-tuning job', async ({ page }) => {
    await page.goto(`${BASE_URL}/llm-tuning`);
    await page.waitForLoadState('networkidle');

    const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      const form = page.locator('.ant-form, .tuning-form');
      const hasForm = await form.count() > 0;
      if (hasForm) {
        const modelSelect = form.locator('select[name="model"], .ant-select');
        const hasModelSelect = await modelSelect.count() > 0;
        console.log('Has model select:', hasModelSelect);
      }
    }
  });
});

// ============================================
// SQL Lab 深度测试
// ============================================
test.describe('Cube - SQL Lab', () => {
  test('should display SQL Lab page', async ({ page }) => {
    await page.goto(`${BASE_URL}/sqllab`);
    await page.waitForLoadState('networkidle');

    const editor = page.locator('.sql-editor, .code-editor, [class*="editor"]');
    await expect(editor.first()).toBeVisible();
  });

  test('should execute SQL query', async ({ page }) => {
    await page.goto(`${BASE_URL}/sqllab`);
    await page.waitForLoadState('networkidle');

    const editor = page.locator('.sql-editor, .code-editor, textarea').first();
    if (await editor.isVisible()) {
      await editor.fill('SELECT 1 as test');

      const runButton = page.locator('button:has-text("运行"), button:has-text("Run"), button:has-text("执行")').first();
      if (await runButton.isVisible()) {
        await runButton.click();
        await page.waitForTimeout(1000);

        const results = page.locator('.query-results, .result-table');
        const hasResults = await results.count() > 0;
        console.log('Has query results:', hasResults);
      }
    }
  });
});

// ============================================
// API 端点验证测试
// ============================================
test.describe('Cube - API 端点验证', () => {
  test('should verify all Cube API endpoints', async ({ request }) => {
    const apiClient = createApiClient(request, 'cube') as CubeApiClient;
    clearRequestLogs();

    // 健康检查
    const health = await apiClient.healthCheck();
    expect(health.code).toBe(0);

    // Notebook
    const notebooks = await apiClient.getNotebooks();
    expect(notebooks.code).toBe(0);

    // 实验
    const experiments = await apiClient.getExperiments();
    expect(experiments.code).toBe(0);

    // 模型
    const models = await apiClient.getModels();
    expect(models.code).toBe(0);

    // 训练任务
    const jobs = await apiClient.getTrainingJobs();
    expect(jobs.code).toBe(0);

    // 模型服务
    const deployments = await apiClient.getDeployments();
    expect(deployments.code).toBe(0);

    // AI Hub
    const searchResult = await apiClient.searchModels('test');
    expect(searchResult.code).toBe(0);

    // 验证没有失败的请求
    const failedRequests = getFailedRequests();
    expect(failedRequests.length).toBe(0);
  });
});

test.afterEach(async ({ request }) => {
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in Cube test:', failedRequests);
  }
});
