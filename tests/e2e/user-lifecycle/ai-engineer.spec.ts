/**
 * 算法工程师 E2E 测试
 * 测试算法工程师的完整用户旅程
 */

import { test, expect } from '@playwright/test';

test.describe('算法工程师全流程', () => {
  test.beforeEach(async ({ page }) => {
    // 登录为算法工程师
    await page.goto('/login');
    await page.fill('input[name="username"]', 'ai_eng');
    await page.fill('input[name="password"]', 'test_password');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('完整模型训练部署流程', async ({ page }) => {
    // 1. 启动Notebook环境
    await page.click('text=Notebook');
    await page.click('button:has-text("新建Notebook")');

    await page.fill('input[name="notebook_name"]', '模型训练实验');
    await page.selectOption('select[name="image"]', 'pytorch-latest');
    await page.selectOption('select[name="gpu"]', 'T4:1');

    await page.click('button:has-text("启动")');

    // 等待Notebook启动
    await page.waitForSelector('text=运行中', { timeout: 120000 });

    // 2. 提交训练任务
    await page.click('text=模型训练');
    await page.click('button:has-text("新建训练任务")');

    await page.fill('input[name="job_name"]', 'BERT微调任务');
    await page.selectOption('select[name="model"]', 'bert-base-chinese');
    await page.selectOption('select[name="finetuning_type"]', 'lora');

    await page.fill('input[name="dataset_path"]', 's3://datasets/training_data');
    await page.fill('input[name="output_path"]', 's3://models/output');

    await page.click('button:has-text("提交训练")');

    // 等待训练任务提交
    await expect(page.locator('text=任务已提交')).toBeVisible();

    // 3. 监控训练进度
    await page.click('text=任务监控');
    await page.waitForSelector('text=训练中', { timeout: 30000 });

    // 验证训练指标显示
    await expect(page.locator('text=Loss')).toBeVisible();
    await expect(page.locator('text=Epoch')).toBeVisible();

    // 4. 模型部署
    await page.click('text=模型部署');
    await page.click('button:has-text("部署模型")');

    await page.selectOption('select[name="deployment_type"]', 'vllm');
    await page.fill('input[name="replicas"]', '2');

    await page.click('button:has-text("开始部署")');

    // 等待部署完成
    await page.waitForSelector('text=部署成功', { timeout: 300000 });

    // 5. 测试API
    await page.click('text=API测试');

    await page.fill('textarea[name="prompt"]', '你好，请介绍一下你自己');
    await page.click('button:has-text("发送")');

    // 验证响应
    await page.waitForSelector('text=assistant', { timeout: 30000 });
    await expect(page.locator('.message-content')).toContainText('你好');
  });

  test('AE-NB-001: 启动Notebook开发环境', async ({ page }) => {
    await page.click('text=Notebook');
    await page.click('button:has-text("新建Notebook")');

    await page.fill('input[name="notebook_name"]', '测试Notebook');
    await page.selectOption('select[name="gpu"]', 'T4:1');

    await page.click('button:has-text("启动")');

    // 验证Notebook启动
    await page.waitForSelector('text=运行中', { timeout: 120000 });
    await expect(page.locator('iframe')).toBeVisible();
  });

  test('AE-TR-001: 提交分布式训练任务', async ({ page }) => {
    await page.click('text=模型训练');
    await page.click('button:has-text("新建训练任务")');

    await page.fill('input[name="job_name"]', '分布式训练测试');
    await page.selectOption('select[name="training_type"]', 'distributed');
    await page.fill('input[name="workers"]', '4');

    await page.click('button:has-text("提交")');

    await expect(page.locator('text=任务提交成功')).toBeVisible();
  });

  test('AE-DP-001: 一键部署模型', async ({ page }) => {
    await page.click('text=模型管理');

    // 选择已训练的模型
    await page.click('text=bert-finetuned-v1');
    await page.click('button:has-text("部署")');

    await page.selectOption('select[name="inference_engine"]', 'vllm');
    await page.fill('input[name="replicas"]', '2');

    await page.click('button:has-text("确认部署")');

    // 等待部署
    await page.waitForSelector('text=部署成功', { timeout: 300000 });
    await expect(page.locator('text=vLLM')).toBeVisible();
  });
});
