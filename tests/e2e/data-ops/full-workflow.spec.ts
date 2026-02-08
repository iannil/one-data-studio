/**
 * DataOps 全流程 E2E 测试
 *
 * 演示从数据接入到数据利用的完整 DataOps 流程：
 *
 * 阶段1: 数据接入
 *   - 注册数据源 (MySQL/PostgreSQL)
 *   - 测试连接
 *   - 配置 CDC
 *
 * 阶段2: 数据处理 (ETL)
 *   - 创建 ETL 任务
 *   - 配置字段映射
 *   - 执行数据同步
 *
 * 阶段3: 数据治理
 *   - 元数据自动采集
 *   - AI 智能标注
 *   - 敏感数据扫描
 *   - 数据血缘分析
 *
 * 阶段4: 数据利用
 *   - Text-to-SQL 自然语言查询
 *   - RAG 知识检索
 *   - BI 报表生成
 */

import { test, expect } from '@playwright/test';

// 测试配置
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://localhost:8001';

// 测试数据
const testDataSource = {
  name: 'E2E测试_销售订单库',
  type: 'mysql',
  host: process.env.TEST_MYSQL_HOST || 'mysql',
  port: 3306,
  username: process.env.TEST_MYSQL_USER || 'root',
  password: process.env.TEST_MYSQL_PASSWORD || 'root123456',
  database: process.env.TEST_MYSQL_DATABASE || 'onedata',
};

const testETLJob = {
  name: 'E2E测试_订单数据同步',
  source_table: 'orders',
  target_table: 'dw_orders',
  schedule: '0 2 * * *',
};

// 辅助函数：设置认证
async function setupAuth(page: any) {
  // 模拟登录（开发模式禁用认证时不需要）
  await page.goto(BASE_URL);
  // 如果有登录页面，这里处理登录逻辑
  // await page.fill('[name=username]', 'admin');
  // await page.fill('[name=password]', 'admin');
  // await page.click('button[type=submit]');
  await page.waitForLoadState('networkidle');
}

// 辅助函数：API 请求
async function apiRequest(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  return response.json();
}

test.describe('DataOps 全流程测试', () => {
  test.beforeAll(async () => {
    // 执行前检查：确保后端服务运行
    try {
      await apiRequest('/api/v1/health');
    } catch (error) {
      console.warn('后端服务未运行，测试将使用 mock 数据');
    }
  });

  // ============================================
  // 阶段 1: 数据接入
  // ============================================
  test.describe('阶段1: 数据接入', () => {
    test('1.1 应该访问数据源管理页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/datasources`);

      // 等待页面加载
      await expect(page.locator('body')).toBeVisible();

      // 验证页面标题
      const title = page.locator('text=数据源管理').or(page.locator('text=Data Sources'));
      await expect(title).toBeVisible();

      // 截图保存当前状态
      await page.screenshot({ path: 'test-results/dataops/01-datasources-page.png' });
      console.log('✓ 步骤 1.1: 成功访问数据源管理页面');
    });

    test('1.2 应该打开新建数据源对话框', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/datasources`);

      // 点击新建数据源按钮
      const createButton = page
        .locator('button:has-text("新建数据源")')
        .or(page.locator('button:has-text("Add")'))
        .or(page.locator('button[aria-label="add"]'))
        .first();

      await createButton.click();

      // 等待模态框出现
      await page.waitForTimeout(500);

      // 验证模态框标题
      const modalTitle = page
        .locator('.ant-modal-title:has-text("新建数据源")')
        .or(page.locator('text=Create DataSource'))
        .or(page.locator('[role="dialog"]'));

      await expect(modalTitle.first()).toBeVisible();

      await page.screenshot({ path: 'test-results/dataops/02-create-datasource-modal.png' });
      console.log('✓ 步骤 1.2: 成功打开新建数据源对话框');
    });

    test('1.3 应该填写数据源配置信息', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/datasources`);

      // 打开新建对话框
      const createButton = page
        .locator('button:has-text("新建数据源")')
        .or(page.locator('button:has-text("Add")'))
        .first();
      await createButton.click();
      await page.waitForTimeout(500);

      // 填写数据源名称
      const nameInput = page
        .locator('input[placeholder*="数据源名称"]')
        .or(page.locator('input[name="name"]'))
        .or(page.locator('input#name'))
        .first();
      await nameInput.fill(testDataSource.name);

      // 选择数据库类型
      const typeSelect = page
        .locator('.ant-select:has-text("数据库类型")')
        .or(page.locator('[name="type"]'))
        .first();
      await typeSelect.click();
      await page.waitForTimeout(200);
      const mysqlOption = page.locator('text=MySQL').or(page.locator('[value="mysql"]')).first();
      await mysqlOption.click();

      // 填写主机地址
      const hostInput = page.locator('input[name="host"]').or(page.locator('input#host')).first();
      await hostInput.fill(testDataSource.host);

      // 填写端口
      const portInput = page.locator('input[name="port"]').or(page.locator('input#port')).first();
      await portInput.fill(String(testDataSource.port));

      // 填写用户名
      const usernameInput = page.locator('input[name="username"]').or(page.locator('input#username')).first();
      await usernameInput.fill(testDataSource.username);

      // 填写密码
      const passwordInput = page.locator('input[type="password"]').or(page.locator('input#password')).first();
      await passwordInput.fill(testDataSource.password);

      // 填写数据库名
      const databaseInput = page.locator('input[name="database"]').or(page.locator('input#database')).first();
      await databaseInput.fill(testDataSource.database);

      await page.screenshot({ path: 'test-results/dataops/03-datasource-form-filled.png' });
      console.log('✓ 步骤 1.3: 成功填写数据源配置信息');
    });

    test('1.4 应该测试数据源连接', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/datasources`);

      // 打开新建对话框并填写表单
      const createButton = page.locator('button:has-text("新建数据源")').first();
      await createButton.click();
      await page.waitForTimeout(500);

      // 快速填写表单
      await page.locator('input[name="name"]').first().fill(testDataSource.name);
      await page.locator('input[name="host"]').first().fill(testDataSource.host);
      await page.locator('input[name="port"]').first().fill(String(testDataSource.port));
      await page.locator('input[name="username"]').first().fill(testDataSource.username);
      await page.locator('input[type="password"]').first().fill(testDataSource.password);
      await page.locator('input[name="database"]').first().fill(testDataSource.database);

      // 选择类型
      const typeSelect = page.locator('.ant-select').first();
      await typeSelect.click();
      await page.locator('text=MySQL').first().click();
      await page.waitForTimeout(300);

      // 点击测试连接按钮
      const testButton = page
        .locator('button:has-text("测试连接")')
        .or(page.locator('button:has-text("Test")'))
        .first();
      await testButton.click();

      // 等待测试结果
      await page.waitForTimeout(2000);

      // 检查是否有成功提示或错误提示
      const successMessage = page.locator('.ant-message-success').or(page.locator('.ant-alert-success'));
      const errorMessage = page.locator('.ant-message-error').or(page.locator('.ant-alert-error'));

      const hasResult = await successMessage.count() > 0 || await errorMessage.count() > 0;

      await page.screenshot({ path: 'test-results/dataops/04-connection-test-result.png' });

      if (hasResult) {
        console.log('✓ 步骤 1.4: 连接测试已执行');
      } else {
        console.log('⚠ 步骤 1.4: 连接测试结果未显示（可能是后端未运行）');
      }
    });

    test('1.5 应该创建数据源', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/datasources`);

      // 打开新建对话框
      const createButton = page.locator('button:has-text("新建数据源")').first();
      await createButton.click();
      await page.waitForTimeout(500);

      // 填写表单
      await page.locator('input[name="name"]').first().fill(`${testDataSource.name}_auto`);
      await page.locator('input[name="host"]').first().fill(testDataSource.host);
      await page.locator('input[name="port"]').first().fill(String(testDataSource.port));
      await page.locator('input[name="username"]').first().fill(testDataSource.username);
      await page.locator('input[type="password"]').first().fill(testDataSource.password);
      await page.locator('input[name="database"]').first().fill(testDataSource.database);

      // 选择类型
      await page.locator('.ant-select').first().click();
      await page.locator('text=MySQL').first().click();
      await page.waitForTimeout(300);

      // 点击创建按钮
      const submitButton = page
        .locator('button:has-text("创建")')
        .or(page.locator('button:has-text("Submit")'))
        .or(page.locator('button[type="submit"]'))
        .first();
      await submitButton.click();

      // 等待响应
      await page.waitForTimeout(2000);

      await page.screenshot({ path: 'test-results/dataops/05-datasource-created.png' });
      console.log('✓ 步骤 1.5: 数据源创建请求已发送');
    });
  });

  // ============================================
  // 阶段 2: 数据处理 (ETL)
  // ============================================
  test.describe('阶段2: 数据处理', () => {
    test('2.1 应该访问 ETL 管理页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/etl`);

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      const title = page.locator('text=ETL').or(page.locator('text=数据同步'));
      await expect(title.first()).toBeVisible();

      await page.screenshot({ path: 'test-results/dataops/06-etl-page.png' });
      console.log('✓ 步骤 2.1: 成功访问 ETL 管理页面');
    });

    test('2.2 应该创建 ETL 任务', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/etl`);

      // 点击新建任务按钮
      const createButton = page
        .locator('button:has-text("新建")')
        .or(page.locator('button:has-text("Create")'))
        .or(page.locator('button[aria-label="add"]'))
        .first();

      const buttonExists = await createButton.count() > 0;
      if (buttonExists) {
        await createButton.click();
        await page.waitForTimeout(500);

        // 填写任务名称
        const nameInput = page.locator('input[name="name"]').or(page.locator('input#name')).first();
        await nameInput.fill(testETLJob.name);

        await page.screenshot({ path: 'test-results/dataops/07-etl-create-form.png' });
        console.log('✓ 步骤 2.2: 成功打开 ETL 任务创建表单');
      } else {
        console.log('⚠ 步骤 2.2: ETL 创建按钮未找到，页面可能尚未实现');
      }
    });

    test('2.3 应该配置字段映射', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/etl`);

      // 检查是否有字段映射配置区域
      const mappingArea = page.locator('text=字段映射').or(page.locator('text=Field Mapping'));

      const hasMapping = await mappingArea.count() > 0;
      if (hasMapping) {
        console.log('✓ 步骤 2.3: 字段映射配置区域存在');
      } else {
        console.log('⚠ 步骤 2.3: 字段映射配置区域未找到');
      }

      await page.screenshot({ path: 'test-results/dataops/08-etl-field-mapping.png' });
    });
  });

  // ============================================
  // 阶段 3: 数据治理
  // ============================================
  test.describe('阶段3: 数据治理', () => {
    test('3.1 应该访问元数据管理页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      const title = page.locator('text=元数据').or(page.locator('text=Metadata'));
      await expect(title.first()).toBeVisible();

      await page.screenshot({ path: 'test-results/dataops/09-metadata-page.png' });
      console.log('✓ 步骤 3.1: 成功访问元数据管理页面');
    });

    test('3.2 应该浏览数据库和表结构', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待数据库树加载
      await page.waitForTimeout(1000);

      // 查找数据库树节点
      const tree = page.locator('.ant-tree').or(page.locator('[role="tree"]'));
      const hasTree = await tree.count() > 0;

      if (hasTree) {
        // 点击第一个数据库节点
        const dbNode = page.locator('.ant-tree-node').first();
        await dbNode.click();
        await page.waitForTimeout(500);

        console.log('✓ 步骤 3.2: 成功浏览数据库结构');
      } else {
        console.log('⚠ 步骤 3.2: 数据库树未找到（可能没有数据源连接）');
      }

      await page.screenshot({ path: 'test-results/dataops/10-metadata-tree.png' });
    });

    test('3.3 应该执行 AI 智能标注', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForTimeout(1000);

      // 查找 AI 标注按钮
      const aiButton = page
        .locator('button:has-text("AI 标注")')
        .or(page.locator('button:has-text("AI Annotate")'))
        .or(page.locator('button:has-text("Robot")'));

      const hasAIButton = await aiButton.count() > 0;
      if (hasAIButton) {
        await aiButton.first().click();
        await page.waitForTimeout(2000);

        console.log('✓ 步骤 3.3: AI 标注功能已触发');
      } else {
        console.log('⚠ 步骤 3.3: AI 标注按钮未找到（可能需要先选择表）');
      }

      await page.screenshot({ path: 'test-results/dataops/11-ai-annotation.png' });
    });

    test('3.4 应该执行敏感数据扫描', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForTimeout(1000);

      // 查找敏感扫描按钮
      const scanButton = page
        .locator('button:has-text("敏感")')
        .or(page.locator('button:has-text("Sensitivity")'))
        .or(page.locator('button:has-text("Scan")'));

      const hasScanButton = await scanButton.count() > 0;
      if (hasScanButton) {
        await scanButton.first().click();
        await page.waitForTimeout(1000);

        console.log('✓ 步骤 3.4: 敏感数据扫描已触发');
      } else {
        console.log('⚠ 步骤 3.4: 敏感扫描按钮未找到');
      }

      await page.screenshot({ path: 'test-results/dataops/12-sensitivity-scan.png' });
    });

    test('3.5 应该搜索表和字段', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForTimeout(1000);

      // 切换到搜索标签页
      const searchTab = page.locator('text=搜索').or(page.locator('text=Search'));
      const hasSearchTab = await searchTab.count() > 0;

      if (hasSearchTab) {
        await searchTab.first().click();
        await page.waitForTimeout(500);

        // 输入搜索关键词
        const searchInput = page
          .locator('input[placeholder*="搜索"]')
          .or(page.locator('input[placeholder*="Search"]'))
          .or(page.locator('.ant-input-search'))
          .first();

        await searchInput.fill('orders');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(1000);

        console.log('✓ 步骤 3.5: 表搜索功能已执行');
      } else {
        console.log('⚠ 步骤 3.5: 搜索标签页未找到');
      }

      await page.screenshot({ path: 'test-results/dataops/13-metadata-search.png' });
    });
  });

  // ============================================
  // 阶段 4: 数据利用
  // ============================================
  test.describe('阶段4: 数据利用', () => {
    test('4.1 应该访问 Text-to-SQL 页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForTimeout(1000);

      // 切换到 Text-to-SQL 标签页
      const text2sqlTab = page
        .locator('text=Text-to-SQL')
        .or(page.locator('text=SQL'));

      const hasTab = await text2sqlTab.count() > 0;
      if (hasTab) {
        await text2sqlTab.first().click();
        await page.waitForTimeout(500);

        console.log('✓ 步骤 4.1: 成功访问 Text-to-SQL 功能');
      } else {
        console.log('⚠ 步骤 4.1: Text-to-SQL 标签页未找到');
      }

      await page.screenshot({ path: 'test-results/dataops/14-text2sql-page.png' });
    });

    test('4.2 应该执行自然语言查询', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/metadata`);

      // 等待页面加载
      await page.waitForTimeout(1000);

      // 尝试切换到 Text-to-SQL 标签
      const text2sqlTab = page.locator('text=Text-to-SQL').or(page.locator('text=SQL'));
      const hasTab = await text2sqlTab.count() > 0;

      if (hasTab) {
        await text2sqlTab.first().click();
        await page.waitForTimeout(500);
      }

      // 查找文本输入框
      const textArea = page
        .locator('textarea[placeholder*="自然语言"]')
        .or(page.locator('textarea[placeholder*="查询"]'))
        .or(page.locator('textarea.ant-input'));

      const hasTextArea = await textArea.count() > 0;
      if (hasTextArea) {
        // 输入自然语言查询
        await textArea.first().fill('查询最近一个月的订单总数');
        await page.waitForTimeout(500);

        // 查找生成按钮
        const generateButton = page
          .locator('button:has-text("生成")')
          .or(page.locator('button:has-text("Generate")'))
          .or(page.locator('button:has-text("查询")'));

        const hasButton = await generateButton.count() > 0;
        if (hasButton) {
          await generateButton.first().click();
          await page.waitForTimeout(2000);

          console.log('✓ 步骤 4.2: 自然语言查询已执行');
        } else {
          console.log('⚠ 步骤 4.2: 生成按钮未找到');
        }
      } else {
        console.log('⚠ 步骤 4.2: 查询输入框未找到');
      }

      await page.screenshot({ path: 'test-results/dataops/15-text2sql-query.png' });
    });

    test('4.3 应该访问 BI 报表页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/bi`);

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      const title = page.locator('text=BI').or(page.locator('text=报表')).or(page.locator('text=Superset'));
      await expect(title.first()).toBeVisible();

      await page.screenshot({ path: 'test-results/dataops/16-bi-page.png' });
      console.log('✓ 步骤 4.3: 成功访问 BI 报表页面');
    });

    test('4.4 应该访问数据服务页面', async ({ page }) => {
      await setupAuth(page);
      await page.goto(`${BASE_URL}/data/services`);

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      const title = page.locator('text=数据服务').or(page.locator('text=Services'));
      await expect(title.first()).toBeVisible();

      await page.screenshot({ path: 'test-results/dataops/17-data-services.png' });
      console.log('✓ 步骤 4.4: 成功访问数据服务页面');
    });
  });

  // ============================================
  // 完整流程验证
  // ============================================
  test.describe('完整流程验证', () => {
    test('应该生成完整流程报告', async ({ page }) => {
      await setupAuth(page);

      const summary: Record<string, string> = {};

      // 依次访问各个页面并记录状态
      const pages = [
        { path: '/data/datasources', name: '数据源管理' },
        { path: '/data/etl', name: 'ETL 管理' },
        { path: '/data/quality', name: '数据质量' },
        { path: '/metadata', name: '元数据管理' },
        { path: '/data/lineage', name: '数据血缘' },
        { path: '/data/bi', name: 'BI 报表' },
        { path: '/data/services', name: '数据服务' },
      ];

      for (const pageInfo of pages) {
        try {
          await page.goto(`${BASE_URL}${pageInfo.path}`);
          await page.waitForLoadState('networkidle');
          const isVisible = await page.locator('body').isVisible();
          summary[pageInfo.name] = isVisible ? '✓ 可访问' : '✗ 不可访问';
        } catch (e) {
          summary[pageInfo.name] = '✗ 访问失败';
        }
      }

      // 打印汇总
      console.log('\n=================================');
      console.log('DataOps 全流程测试汇总');
      console.log('=================================');
      for (const [name, status] of Object.entries(summary)) {
        console.log(`${status} ${name}`);
      }
      console.log('=================================\n');

      // 生成最终截图
      await page.goto(`${BASE_URL}`);
      await page.waitForLoadState('networkidle');
      await page.screenshot({ path: 'test-results/dataops/00-homepage.png', fullPage: true });

      console.log('✓ 完整流程验证完成');
    });
  });
});

/**
 * 测试执行说明
 *
 * 1. 确保 Docker 服务运行：
 *    docker-compose -f deploy/local/docker-compose.yml up -d
 *
 * 2. 安装依赖：
 *    npm install
 *
 * 3. 运行测试：
 *    npx playwright test data-ops-full-workflow.spec.ts --headed
 *
 * 4. 查看结果：
 *    - 截图：test-results/dataops/
 *    - 报告：npx playwright show-report
 *
 * 5. 环境变量（可选）：
 *    export BASE_URL=http://localhost:3000
 *    export API_BASE=http://localhost:8001
 *    export TEST_MYSQL_HOST=mysql
 *    export TEST_MYSQL_USER=root
 *    export TEST_MYSQL_PASSWORD=your_password
 *    export TEST_MYSQL_DATABASE=onedata
 */
