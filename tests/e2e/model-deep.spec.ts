/**
 * ONE-DATA-STUDIO 算法引擎深度 E2E 测试
 * 覆盖用例: AE-NB-*, AE-TR-*, AE-DP-*
 */

import { test, expect, Page } from '@playwright/test';

// 测试配置
const TEST_USER = { username: 'algo_engineer', password: 'ae123456' };

// 登录辅助函数
async function login(page: Page) {
  await page.goto('/login');
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|model)/);
}

test.describe('开发环境 (AE-NB)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/model/notebooks');
  });

  test('AE-NB-001: 启动 Notebook', async ({ page }) => {
    await page.click('button:has-text("新建 Notebook")');

    // 选择环境
    await page.click('[data-testid="env-pytorch"]');
    await page.fill('input[name="name"]', 'test_notebook');

    await page.click('button:has-text("创建")');

    // 等待 Notebook 启动
    await expect(page.locator('text=运行中')).toBeVisible({ timeout: 120000 });
  });

  test('AE-NB-002: Notebook 中查询数据集', async ({ page }) => {
    // 打开已有 Notebook
    await page.click('.notebook-item:first-child');

    // 等待 JupyterLab 加载
    await expect(page.locator('.jp-Notebook, iframe')).toBeVisible({ timeout: 60000 });
  });

  test('AE-NB-004: 安装依赖包', async ({ page }) => {
    await page.click('.notebook-item:first-child');

    // 使用终端安装包
    await page.click('button:has-text("终端")');
    await expect(page.locator('.terminal, .jp-Terminal')).toBeVisible({ timeout: 30000 });
  });
});

test.describe('模型训练 (AE-TR)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/model/training');
  });

  test('AE-TR-001: 提交训练任务', async ({ page }) => {
    await page.click('button:has-text("新建任务")');

    // 填写任务信息
    await page.fill('input[name="name"]', 'test_training_job');

    // 选择框架
    await page.click('[data-testid="framework-pytorch"]');

    // 选择数据集
    await page.click('[data-testid="dataset-select"]');
    await page.click('.ant-select-item:first-child');

    // 配置资源
    await page.fill('input[name="gpu_count"]', '1');
    await page.fill('input[name="epochs"]', '10');

    // 提交
    await page.click('button:has-text("提交")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('AE-TR-003: 分布式训练配置', async ({ page }) => {
    await page.click('button:has-text("新建任务")');

    // 开启分布式
    await page.click('[data-testid="distributed-toggle"]');

    // 配置节点数
    await page.fill('input[name="worker_count"]', '4');

    await expect(page.locator('text=分布式训练')).toBeVisible();
  });

  test('AE-TR-005: 监控训练进度', async ({ page }) => {
    // 点击运行中的任务
    await page.click('.training-job-row:has-text("运行中")');

    // 验证监控信息
    await expect(page.locator('.training-metrics, .loss-chart')).toBeVisible();
    await expect(page.locator('text=Loss')).toBeVisible();
    await expect(page.locator('text=Epoch')).toBeVisible();
  });

  test('AE-TR-007: 超参数调优', async ({ page }) => {
    await page.click('button:has-text("超参数调优")');

    // 配置搜索空间
    await page.fill('input[name="learning_rate_min"]', '0.0001');
    await page.fill('input[name="learning_rate_max"]', '0.01');
    await page.fill('input[name="batch_size"]', '32,64,128');

    // 选择搜索策略
    await page.click('[data-testid="search-bayesian"]');

    await page.click('button:has-text("开始调优")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('AE-TR-008: 保存模型', async ({ page }) => {
    // 选择已完成的任务
    await page.click('.training-job-row:has-text("已完成")');

    // 保存模型
    await page.click('button:has-text("保存模型")');
    await page.fill('input[name="model_name"]', 'test_model_v1');
    await page.fill('textarea[name="description"]', '测试模型');

    await page.click('button:has-text("确定")');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });
});

test.describe('模型部署 (AE-DP)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/model/deployment');
  });

  test('AE-DP-001: 部署模型服务', async ({ page }) => {
    await page.click('button:has-text("新建服务")');

    // 选择模型
    await page.click('[data-testid="model-select"]');
    await page.click('.ant-select-item:first-child');

    // 配置服务
    await page.fill('input[name="service_name"]', 'test_model_service');
    await page.fill('input[name="replicas"]', '2');

    // 选择推理框架
    await page.click('[data-testid="runtime-vllm"]');

    // 部署
    await page.click('button:has-text("部署")');
    await expect(page.locator('.ant-message-success')).toBeVisible();

    // 等待部署完成
    await expect(page.locator('text=运行中')).toBeVisible({ timeout: 300000 });
  });

  test('AE-DP-005: API 测试', async ({ page }) => {
    // 选择已部署的服务
    await page.click('.deployment-item:has-text("运行中")');

    // 进入 API 测试
    await page.click('button:has-text("API 测试")');

    // 输入测试数据
    await page.fill('textarea[name="input"]', '{"text": "测试输入"}');
    await page.click('button:has-text("发送")');

    // 验证响应
    await expect(page.locator('.api-response, .response-json')).toBeVisible({ timeout: 30000 });
  });

  test('AE-DP-006: 扩缩容', async ({ page }) => {
    await page.click('.deployment-item:has-text("运行中")');

    // 调整副本数
    await page.click('button:has-text("扩缩容")');
    await page.fill('input[name="replicas"]', '3');
    await page.click('button:has-text("确定")');

    await expect(page.locator('.ant-message-success')).toBeVisible();
  });

  test('AE-DP-008: 服务监控', async ({ page }) => {
    await page.click('.deployment-item:has-text("运行中")');

    // 查看监控
    await page.click('button:has-text("监控")');

    // 验证监控图表
    await expect(page.locator('.metrics-chart, .qps-chart')).toBeVisible();
    await expect(page.locator('text=QPS')).toBeVisible();
    await expect(page.locator('text=延迟')).toBeVisible();
  });
});
