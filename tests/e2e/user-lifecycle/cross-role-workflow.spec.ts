/**
 * 跨角色工作流 E2E 测试
 * 测试跨角色协作场景：数据准备→模型训练→智能查询
 */

import { test, expect } from '@playwright/test';

test.describe('跨角色协作流程', () => {
  test('数据→模型→应用完整流程', async ({ browser }) => {
    // 1. 数据管理员：准备数据资产
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();

    await adminPage.goto('/login');
    await adminPage.fill('input[name="username"]', 'data_admin');
    await adminPage.fill('input[name="password"]', 'admin_password');
    await adminPage.click('button[type="submit"]');

    // 注册数据源
    await adminPage.click('text=数据源管理');
    await adminPage.click('button:has-text("新增数据源")');
    await adminPage.selectOption('select[name="type"]', 'mysql');
    await adminPage.fill('input[name="name"]', '跨流程测试数据源');
    await adminPage.fill('input[name="host"]', 'localhost');
    await adminPage.fill('input[name="port"]', '3306');
    await adminPage.fill('input[name="database"]', 'test_db');
    await adminPage.click('button:has-text("保存")');

    // 启动元数据扫描
    await adminPage.click('text=启动扫描');
    await adminPage.waitForSelector('text=扫描完成', { timeout: 60000 });

    // 敏感数据识别
    await adminPage.click('text=敏感数据');
    await adminPage.click('button:has-text("启动扫描")');
    await adminPage.waitForSelector('text=扫描完成', { timeout: 60000 });

    await adminContext.close();

    // 2. 数据工程师：ETL处理
    const engineerContext = await browser.newContext();
    const engineerPage = await engineerContext.newPage();

    await engineerPage.goto('/login');
    await engineerPage.fill('input[name="username"]', 'data_eng');
    await engineerPage.fill('input[name="password"]', 'engineer_password');
    await engineerPage.click('button[type="submit"]');

    // 创建ETL任务
    await engineerPage.click('text=ETL编排');
    await engineerPage.click('button:has-text("新建ETL任务")');
    await engineerPage.fill('input[name="task_name"]', '用户数据清洗');
    await engineerPage.selectOption('select[name="source_table"]', 'users');
    await engineerPage.click('button:has-text("分析")');

    // 配置清洗和脱敏
    await engineerPage.click('text=下一步');
    await engineerPage.check('input[value="remove_nulls"]');
    await engineerPage.check('input[value="mask_sensitive"]');

    await engineerPage.click('button:has-text("执行")');
    await engineerPage.waitForSelector('text=执行完成', { timeout: 120000 });

    await engineerContext.close();

    // 3. 算法工程师：训练模型
    const aiContext = await browser.newContext();
    const aiPage = await aiContext.newPage();

    await aiPage.goto('/login');
    await aiPage.fill('input[name="username"]', 'ai_eng');
    await aiPage.fill('input[name="password"]', 'ai_password');
    await aiPage.click('button[type="submit"]');

    // 提交训练任务
    await aiPage.click('text=模型训练');
    await aiPage.click('button:has-text("新建训练任务")');
    await aiPage.fill('input[name="job_name"]', '用户行为预测模型');
    await aiPage.selectOption('select[name="dataset"]', 'users_clean');
    await aiPage.selectOption('select[name="model_type"]', 'xgboost');

    await aiPage.click('button:has-text("提交训练")');

    // 等待训练完成（模拟）
    await aiPage.waitForSelector('text=训练完成', { timeout: 300000 });

    // 部署模型
    await aiPage.click('text=模型部署');
    await aiPage.click('button:has-text("部署")');
    await aiPage.selectOption('select[name="deployment_type"]', 'serving');
    await aiPage.click('button:has-text("确认")');
    await aiPage.waitForSelector('text=部署成功', { timeout: 60000 });

    await aiContext.close();

    // 4. 业务用户：使用智能查询
    const businessContext = await browser.newContext();
    const businessPage = await businessContext.newPage();

    await businessPage.goto('/login');
    await businessPage.fill('input[name="username"]', 'business_user');
    await businessPage.fill('input[name="password"]', 'business_password');
    await businessPage.click('button[type="submit"]');

    // 上传文档到知识库
    await businessPage.click('text=知识库');
    await businessPage.click('button:has-text("上传文档")');

    const fileInput = await businessPage.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/data/documents/sample.pdf');

    await businessPage.click('button:has-text("开始上传")');
    await businessPage.waitForSelector('text=处理完成', { timeout: 60000 });

    // 智能查询
    await businessPage.click('text=智能查询');
    await businessPage.fill('textarea[placeholder="输入您的问题"]', '预测下月用户活跃度');
    await businessPage.click('button:has-text("查询")');

    // 验证AI预测结果
    await businessPage.waitForSelector('.prediction-result', { timeout: 30000 });
    await expect(businessPage.locator('.prediction-result')).toContainText('活跃度');

    // 验证使用了训练好的模型
    await expect(businessPage.locator('.model-reference')).toContainText('用户行为预测模型');

    await businessContext.close();
  });

  test('数据治理到智能分析完整流程', async ({ browser }) => {
    // 1. 数据管理员：数据治理
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();

    await adminPage.goto('/login');
    await adminPage.fill('input[name="username"]', 'data_admin');
    await adminPage.fill('input[name="password"]', 'admin_password');
    await adminPage.click('button[type="submit"]');

    // 资产编目和价值评估
    await adminPage.click('text=资产管理');
    await adminPage.click('button:has-text("自动编目")');
    await adminPage.waitForSelector('text=编目完成', { timeout: 60000 });

    await adminPage.click('button:has-text("批量评估")');
    await adminPage.waitForSelector('text=评估完成', { timeout: 60000 });

    await adminContext.close();

    // 2. 业务用户：资产检索和智能分析
    const businessContext = await browser.newContext();
    const businessPage = await businessContext.newPage();

    await businessPage.goto('/login');
    await businessPage.fill('input[name="username"]', 'business_user');
    await businessPage.fill('input[name="password"]', 'business_password');
    await businessPage.click('button[type="submit"]');

    // 资产检索
    await businessPage.click('text=资产检索');
    await businessPage.fill('input[placeholder="搜索数据资产"]', '高价值用户数据');

    await businessPage.click('button:has-text("搜索")');
    await businessPage.waitForSelector('.asset-result', { timeout: 10000 });

    // 选择资产并分析
    await businessPage.click('.asset-result:first-child .select-button');
    await businessPage.click('button:has-text("智能分析")');

    // 生成分析报告
    await businessPage.waitForSelector('.analysis-report', { timeout: 30000 });
    await expect(businessPage.locator('.analysis-report')).toBeVisible();

    await businessContext.close();
  });

  test('多角色权限协同流程', async ({ browser }) => {
    // 1. 系统管理员：配置权限
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();

    await adminPage.goto('/login');
    await adminPage.fill('input[name="username"]', 'sys_admin');
    await adminPage.fill('input[name="password"]', 'admin_password');
    await adminPage.click('button[type="submit"]');

    await adminPage.click('text=权限管理');
    await adminPage.click('button:has-text("新建策略")');

    await adminPage.fill('input[name="policy_name"]', '数据工程师只读权限');
    await adminPage.selectOption('select[name="role"]', 'data_engineer');
    await adminPage.selectOption('select[name="access_level"]', 'masked');

    await adminPage.click('button:has-text("保存")');
    await expect(adminPage.locator('text=策略创建成功')).toBeVisible();

    await adminContext.close();

    // 2. 数据工程师：验证脱敏访问
    const engineerContext = await browser.newContext();
    const engineerPage = await engineerContext.newPage();

    await engineerPage.goto('/login');
    await engineerPage.fill('input[name="username"]', 'data_eng');
    await engineerPage.fill('input[name="password"]', 'engineer_password');
    await engineerPage.click('button[type="submit"]');

    await engineerPage.click('text=数据预览');
    await engineerPage.selectOption('select[name="table"]', 'users');

    // 验证敏感数据已脱敏
    const maskedData = await engineerPage.locator('td:has-text("****")').all();
    expect(maskedData.length).toBeGreaterThan(0);

    await engineerContext.close();
  });
});
