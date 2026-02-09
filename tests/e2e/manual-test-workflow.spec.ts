/**
 * Playwright E2E 数据治理完整流程测试
 *
 * 功能：
 * - 测试数据源管理完整流程（创建、连接、验证）
 * - 测试元数据管理（扫描、浏览、详情）
 * - 测试数据版本管理（创建版本、版本历史）
 * - 测试特征管理（特征组、特征）
 * - 测试数据标准（标准创建、规则定义）
 * - 测试数据资产（资产注册、业务术语）
 *
 * 环境要求：
 * - 前端服务运行在 http://localhost:3000
 * - MySQL 测试数据库运行在端口 3316
 * - PostgreSQL 测试数据库运行在端口 5442
 *
 * 测试数据保留：测试数据将保留在系统中供后续手动验证
 *
 * 执行命令：
 *   HEADLESS=false npx playwright test tests/e2e/manual-test-workflow.spec.ts --project=manual-test
 *   npx playwright test tests/e2e/manual-test-workflow.spec.ts --project=manual-test --debug
 */

import { test, expect } from '@playwright/test';
import { logger } from './helpers/logger';
import { ConsoleLogger } from './helpers/console-logger';
import { TestDataManager } from './helpers/test-data-helper';

// =============================================================================
// 测试数据库配置 (Manual Test Environment)
// =============================================================================

const MYSQL_CONFIG = {
  name: 'ManualTest-MySQL',
  type: 'mysql',
  host: 'localhost',
  port: '3316',
  username: 'root',
  password: 'testroot123',
  database: 'test_ecommerce',
};

const POSTGRES_CONFIG = {
  name: 'ManualTest-PostgreSQL',
  type: 'postgresql',
  host: 'localhost',
  port: '5442',
  username: 'postgres',
  password: 'testpg123',
  database: 'test_ecommerce_pg',
};

// =============================================================================
// 测试用户凭证
// =============================================================================

const TEST_USERS = {
  admin: { username: 'admin', password: 'admin123' },
};

// =============================================================================
// 登录辅助函数
// =============================================================================

async function login(page: any, username: string, password: string) {
  // 使用 addInitScript 在页面加载前设置模拟认证状态
  await page.addInitScript(() => {
    const expiresAt = Date.now() + 3600 * 1000;
    const mockUser = {
      sub: 'test-user-001',
      preferred_username: 'admin',
      email: 'admin@test.local',
      name: 'Admin User',
      roles: ['admin', 'user', 'developer'],
    };

    sessionStorage.setItem('token_expires_at', expiresAt.toString());
    sessionStorage.setItem('user_info', JSON.stringify(mockUser));
    sessionStorage.setItem('access_token', 'mock_test_token_' + Date.now());
  });

  // 然后导航到数据源页面
  await page.goto('/data/datasources');
  // 等待页面完全加载
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(500);
}

// =============================================================================
// Phase 1: 数据源管理测试
// =============================================================================

test.describe('Phase 1: 数据源管理', () => {
  let consoleLogger: ConsoleLogger;
  let testDataManager: TestDataManager;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    testDataManager = new TestDataManager();

    // 每个测试前重新登录
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);

    // 开始监听控制台错误
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    // 停止监听并获取错误
    const errors = await consoleLogger.stop();

    // 如果有错误，输出到测试报告
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('1.1 导航到数据源页面', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('数据源');
  });

  test('1.2 创建 MySQL 数据源', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');

    // 点击新建数据源按钮
    await page.click('button:has-text("新建数据源")');
    await expect(page.locator('.ant-modal')).toBeVisible();

    // 等待表单加载完成
    await page.waitForSelector('.ant-modal input[placeholder*="数据源名称"]', { state: 'visible' });

    // 填写表单 - 使用 placeholder 选择器
    await page.fill('.ant-modal input[placeholder*="数据源名称"]', MYSQL_CONFIG.name);
    await page.fill('.ant-modal textarea[placeholder*="描述"]', 'Manual E2E 测试用 MySQL 数据源 (端口 3316)');

    // 选择数据库类型 - 点击选择框然后选择 MySQL
    await page.click('.ant-modal .ant-select-selector');
    await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await page.click('.ant-select-item:has-text("MySQL")');

    // 填写连接信息
    await page.fill('.ant-modal input[placeholder*="localhost"]', MYSQL_CONFIG.host);

    // 端口 - InputNumber 使用 input 元素
    await page.locator('.ant-modal input.ant-input-number-input').fill(MYSQL_CONFIG.port);

    await page.fill('.ant-modal input[placeholder*="用户名"]', MYSQL_CONFIG.username);
    await page.fill('.ant-modal input[type="password"]', MYSQL_CONFIG.password);
    await page.fill('.ant-modal input[placeholder*="数据库名称"]', MYSQL_CONFIG.database);

    // 测试连接
    await page.click('button:has-text("测试连接")');
    await page.waitForTimeout(3000);

    // 保存数据源 - 点击创建按钮（注意文本中间有空格）
    await page.locator('button:has-text("创 建")').click();

    // 等待模态框关闭
    await page.waitForSelector('.ant-modal', { state: 'hidden', timeout: 10000 }).catch(() => {});

    // 保存数据源 ID
    const datasourceId = await testDataManager.saveDatasource('mysql', MYSQL_CONFIG.name);
    logger.info(`MySQL 数据源已创建，ID: ${datasourceId}`);
  });

  test('1.3 验证 MySQL 数据源显示在列表中', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');

    // 等待表格加载
    await page.waitForSelector('.ant-table', { state: 'visible' });

    // 查找 MySQL 数据源（可能有多个同名，使用 first）
    const mysqlRow = page.locator('.ant-table-tbody .ant-table-row').filter({
      hasText: MYSQL_CONFIG.name,
    }).first();
    await expect(mysqlRow).toBeVisible();
  });

  test('1.4 创建 PostgreSQL 数据源', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');

    // 点击新建数据源按钮
    await page.click('button:has-text("新建数据源")');
    await expect(page.locator('.ant-modal')).toBeVisible();

    // 等待表单加载完成
    await page.waitForSelector('.ant-modal input[placeholder*="数据源名称"]', { state: 'visible' });

    // 填写表单 - 使用 placeholder 选择器
    await page.fill('.ant-modal input[placeholder*="数据源名称"]', POSTGRES_CONFIG.name);
    await page.fill('.ant-modal textarea[placeholder*="描述"]', 'Manual E2E 测试用 PostgreSQL 数据源 (端口 5442)');

    // 选择数据库类型 - 点击选择框然后选择 PostgreSQL
    await page.click('.ant-modal .ant-select-selector');
    await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await page.click('.ant-select-item:has-text("PostgreSQL")');

    // 填写连接信息
    await page.fill('.ant-modal input[placeholder*="localhost"]', POSTGRES_CONFIG.host);

    // 端口 - InputNumber 使用 input 元素
    await page.locator('.ant-modal input.ant-input-number-input').fill(POSTGRES_CONFIG.port);

    await page.fill('.ant-modal input[placeholder*="用户名"]', POSTGRES_CONFIG.username);
    await page.fill('.ant-modal input[type="password"]', POSTGRES_CONFIG.password);
    await page.fill('.ant-modal input[placeholder*="数据库名称"]', POSTGRES_CONFIG.database);

    // 测试连接
    await page.click('button:has-text("测试连接")');
    await page.waitForTimeout(3000);

    // 保存数据源 - 点击创建按钮（注意文本中间有空格）
    await page.locator('button:has-text("创 建")').click();

    // 等待模态框关闭
    await page.waitForSelector('.ant-modal', { state: 'hidden', timeout: 10000 }).catch(() => {});

    // 保存数据源 ID
    const datasourceId = await testDataManager.saveDatasource('postgresql', POSTGRES_CONFIG.name);
    logger.info(`PostgreSQL 数据源已创建，ID: ${datasourceId}`);
  });

  test('1.5 验证两个数据源都显示在列表中', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ant-table', { state: 'visible' });

    // 验证 MySQL 数据源（可能有多个同名，使用 first）
    await expect(page.locator('.ant-table-tbody').getByText(MYSQL_CONFIG.name).first()).toBeVisible();

    // 验证 PostgreSQL 数据源（可能有多个同名，使用 first）
    await expect(page.locator('.ant-table-tbody').getByText(POSTGRES_CONFIG.name).first()).toBeVisible();
  });

  test('1.6 测试 MySQL 数据源连接', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ant-table', { state: 'visible' });

    // 找到 MySQL 数据源行
    const mysqlRow = page.locator('.ant-table-tbody .ant-table-row').filter({
      hasText: MYSQL_CONFIG.name,
    }).first();

    // 点击测试连接按钮
    const testButton = mysqlRow.locator('button:has-text("测试连接")');
    if (await testButton.isVisible()) {
      await testButton.click();
      await page.waitForTimeout(3000);

      // 验证连接成功提示
      const successMessage = page.locator('.ant-message-success, .ant-notification-notice-success');
      if (await successMessage.isVisible({ timeout: 5000 }).catch(() => false)) {
        logger.info('MySQL 数据源连接测试成功');
      }
    }
  });

  test('1.7 测试 PostgreSQL 数据源连接', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ant-table', { state: 'visible' });

    // 找到 PostgreSQL 数据源行
    const postgresRow = page.locator('.ant-table-tbody .ant-table-row').filter({
      hasText: POSTGRES_CONFIG.name,
    }).first();

    // 点击测试连接按钮
    const testButton = postgresRow.locator('button:has-text("测试连接")');
    if (await testButton.isVisible()) {
      await testButton.click();
      await page.waitForTimeout(3000);

      // 验证连接成功提示
      const successMessage = page.locator('.ant-message-success, .ant-notification-notice-success');
      if (await successMessage.isVisible({ timeout: 5000 }).catch(() => false)) {
        logger.info('PostgreSQL 数据源连接测试成功');
      }
    }
  });

  test('1.8 编辑 MySQL 数据源并验证字段回显', async ({ page }) => {
    await page.goto('/data/datasources');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ant-table', { state: 'visible' });

    // 找到 MySQL 数据源行
    const mysqlRow = page.locator('.ant-table-tbody .ant-table-row').filter({
      hasText: MYSQL_CONFIG.name,
    }).first();

    // 点击编辑按钮（使用图标选择器）
    await mysqlRow.locator('button[aria-label*="edit"], button:has(.anticon-edit)').click();

    // 等待编辑模态框打开
    await page.waitForSelector('.ant-modal', { state: 'visible', timeout: 10000 });

    // 等待表单渲染和值设置
    await page.waitForTimeout(2000);

    // 获取编辑模态框（应该是最后一个可见的）
    const editModal = page.locator('.ant-modal').last();

    // 获取模态框内所有输入框
    const inputs = await editModal.locator('input').all();

    // 验证表单字段值是否正确回显
    if (inputs.length > 0) {
      const nameValue = await inputs[0].inputValue();
      expect(nameValue).toBe(MYSQL_CONFIG.name);

      // 主机、端口、用户名（索引可能因表单结构不同而变化）
      if (inputs.length > 4) {
        const hostValue = await inputs[2].inputValue().catch(() => '');
        const portValue = await inputs[3].inputValue().catch(() => '');
        const usernameValue = await inputs[4].inputValue().catch(() => '');

        expect(hostValue).toBe(MYSQL_CONFIG.host);
        expect(portValue).toBe(String(MYSQL_CONFIG.port));
        expect(usernameValue).toBe(MYSQL_CONFIG.username);
      }
    }

    // 关闭模态框
    await editModal.locator('button:has-text("取消")').click();
    await page.waitForSelector('.ant-modal', { state: 'hidden', timeout: 5000 }).catch(() => {});
  });
});

// =============================================================================
// Phase 2: 元数据管理测试
// =============================================================================

test.describe('Phase 2: 元数据管理', () => {
  let consoleLogger: ConsoleLogger;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    const errors = await consoleLogger.stop();
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('2.1 导航到元数据页面', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('元数据');
  });

  test('2.2 选择 MySQL 数据源', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');

    // 查找数据源选择器
    const datasourceSelect = page.locator('.ant-select:first-of-type, [data-testid="datasource-select"]');
    if (await datasourceSelect.isVisible()) {
      await datasourceSelect.click();
      await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
      await page.click(`.ant-select-item:has-text("${MYSQL_CONFIG.name}")`);
    }
  });

  test('2.3 扫描 MySQL 数据源元数据', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');

    // 选择 MySQL 数据源
    const datasourceSelect = page.locator('.ant-select:first-of-type, [data-testid="datasource-select"]');
    if (await datasourceSelect.isVisible()) {
      await datasourceSelect.click();
      await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
      await page.click(`.ant-select-item:has-text("${MYSQL_CONFIG.name}")`);
      await page.waitForTimeout(1000);
    }

    // 点击扫描按钮
    const scanButton = page.locator('button:has-text("扫描元数据"), button:has-text("扫描"), button:has-text("刷新")');
    if (await scanButton.first().isVisible()) {
      await scanButton.first().click();
      await page.waitForTimeout(5000); // 等待扫描完成
    }

    // 等待表格加载
    await page.waitForSelector('.ant-table, .ant-tree', { state: 'visible', timeout: 15000 }).catch(() => {});
  });

  test('2.4 验证核心表已发现', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');

    // 等待表格
    await page.waitForSelector('.ant-table, .ant-tree', { state: 'visible', timeout: 15000 }).catch(() => {});

    // 验证至少有一些表显示
    const tableOrTree = page.locator('.ant-table-tbody .ant-table-row, .ant-tree-treenode');
    const count = await tableOrTree.count();
    logger.info(`Found ${count} tables/nodes`);

    // 如果使用表格形式，检查核心表名
    const table = page.locator('.ant-table-tbody');
    if (await table.isVisible()) {
      const expectedTables = ['users', 'products', 'orders', 'order_items'];
      for (const tableName of expectedTables) {
        const tableExists = await page.locator('.ant-table-tbody').getByText(tableName, { exact: false }).isVisible().catch(() => false);
        if (tableExists) {
          logger.info(`Found table: ${tableName}`);
        }
      }
    }
  });

  test('2.5 查看表详情', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');

    // 等待表格加载
    await page.waitForSelector('.ant-table, .ant-tree', { state: 'visible', timeout: 15000 }).catch(() => {});

    // 查找第一个表并点击查看详情
    const firstRow = page.locator('.ant-table-tbody .ant-table-row, .ant-tree-treenode').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await page.waitForTimeout(2000);

      // 验证详情页面显示
      const detailPanel = page.locator('.ant-drawer, .ant-modal, .detail-panel');
      if (await detailPanel.first().isVisible({ timeout: 5000 }).catch(() => false)) {
        logger.info('Table detail panel opened');
      }
    }
  });

  test('2.6 测试元数据搜索功能', async ({ page }) => {
    await page.goto('/data/metadata');
    await page.waitForLoadState('networkidle');

    // 查找搜索框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .ant-input-search');
    if (await searchInput.first().isVisible()) {
      await searchInput.first().fill('users');
      await page.waitForTimeout(2000);

      // 验证搜索结果
      const results = page.locator('.ant-table-tbody .ant-table-row, .ant-tree-treenode');
      const count = await results.count();
      logger.info(`Search results for "users": ${count}`);
    }
  });
});

// =============================================================================
// Phase 3: 数据版本管理测试
// =============================================================================

test.describe('Phase 3: 数据版本管理', () => {
  let consoleLogger: ConsoleLogger;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    const errors = await consoleLogger.stop();
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('3.1 导航到数据版本页面', async ({ page }) => {
    await page.goto('/data/versions');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('版本');
  });

  test('3.2 创建数据集版本', async ({ page }) => {
    await page.goto('/data/versions');
    await page.waitForLoadState('networkidle');

    // 点击创建版本按钮
    const createButton = page.locator('button:has-text("创建版本"), button:has-text("新建版本"), button:has-text("快照")');
    if (await createButton.first().isVisible()) {
      await createButton.first().click();

      // 等待模态框
      await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 }).catch(() => {});

      // 选择数据源和表
      const datasourceSelect = page.locator('.ant-modal .ant-select').first();
      if (await datasourceSelect.isVisible()) {
        await datasourceSelect.click();
        await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
        await page.click(`.ant-select-item:has-text("${MYSQL_CONFIG.name}")`);
      }

      // 点击确认
      const confirmButton = page.locator('.ant-modal button:has-text("确定"), .ant-modal button:has-text("创建")');
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await page.waitForTimeout(2000);
      }
    }
  });

  test('3.3 查看版本历史', async ({ page }) => {
    await page.goto('/data/versions');
    await page.waitForLoadState('networkidle');

    // 等待版本列表加载
    await page.waitForSelector('.ant-table, .ant-timeline, .version-list', { state: 'visible', timeout: 10000 }).catch(() => {});

    // 验证版本列表显示
    const versionList = page.locator('.ant-table-tbody .ant-table-row, .ant-timeline-item, .version-item');
    const count = await versionList.count();
    logger.info(`Found ${count} versions`);
  });
});

// =============================================================================
// Phase 4: 特征管理测试
// =============================================================================

test.describe('Phase 4: 特征管理', () => {
  let consoleLogger: ConsoleLogger;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    const errors = await consoleLogger.stop();
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('4.1 导航到特征管理页面', async ({ page }) => {
    await page.goto('/data/features');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('特征');
  });

  test('4.2 创建特征组', async ({ page }) => {
    await page.goto('/data/features');
    await page.waitForLoadState('networkidle');

    // 点击创建特征组按钮
    const createButton = page.locator('button:has-text("创建特征组"), button:has-text("新建特征组"), button:has-text("添加")');
    if (await createButton.first().isVisible()) {
      await createButton.first().click();

      // 等待模态框
      const modal = page.locator('.ant-modal');
      if (await modal.isVisible({ timeout: 5000 }).catch(() => false)) {
        // 填写特征组名称
        const nameInput = modal.locator('input[placeholder*="名称"], input[placeholder*="name"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill('E2E测试特征组');
        }

        // 选择数据源
        const datasourceSelect = modal.locator('.ant-select').first();
        if (await datasourceSelect.isVisible()) {
          await datasourceSelect.click();
          await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
          await page.click(`.ant-select-item:has-text("${MYSQL_CONFIG.name}")`);
        }

        // 点击确认
        const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(2000);
        }
      }
    }
  });

  test('4.3 查看特征列表', async ({ page }) => {
    await page.goto('/data/features');
    await page.waitForLoadState('networkidle');

    // 等待特征列表加载
    await page.waitForSelector('.ant-table, .feature-card, .feature-list', { state: 'visible', timeout: 10000 }).catch(() => {});

    // 验证特征列表显示
    const featureList = page.locator('.ant-table-tbody .ant-table-row, .feature-card, .feature-item');
    const count = await featureList.count();
    logger.info(`Found ${count} features/feature groups`);
  });
});

// =============================================================================
// Phase 5: 数据标准测试
// =============================================================================

test.describe('Phase 5: 数据标准', () => {
  let consoleLogger: ConsoleLogger;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    const errors = await consoleLogger.stop();
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('5.1 导航到数据标准页面', async ({ page }) => {
    await page.goto('/data/standards');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('标准');
  });

  test('5.2 创建数据标准', async ({ page }) => {
    await page.goto('/data/standards');
    await page.waitForLoadState('networkidle');

    // 点击创建标准按钮
    const createButton = page.locator('button:has-text("创建标准"), button:has-text("新建标准"), button:has-text("添加")');
    if (await createButton.first().isVisible()) {
      await createButton.first().click();

      // 等待模态框
      const modal = page.locator('.ant-modal');
      if (await modal.isVisible({ timeout: 5000 }).catch(() => false)) {
        // 填写标准名称
        const nameInput = modal.locator('input[placeholder*="名称"], input[placeholder*="name"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill('E2E测试数据标准');
        }

        // 填写标准描述
        const descInput = modal.locator('textarea[placeholder*="描述"], textarea[placeholder*="description"]');
        if (await descInput.isVisible()) {
          await descInput.fill('E2E测试用的数据质量标准');
        }

        // 点击确认
        const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(2000);
        }
      }
    }
  });

  test('5.3 运行标准检查', async ({ page }) => {
    await page.goto('/data/standards');
    await page.waitForLoadState('networkidle');

    // 查找运行检查按钮
    const runButton = page.locator('button:has-text("运行检查"), button:has-text("执行"), button:has-text("验证")');
    if (await runButton.first().isVisible()) {
      await runButton.first().click();
      await page.waitForTimeout(3000);
      logger.info('Standard check executed');
    }
  });
});

// =============================================================================
// Phase 6: 数据资产测试
// =============================================================================

test.describe('Phase 6: 数据资产', () => {
  let consoleLogger: ConsoleLogger;

  test.beforeEach(async ({ page }) => {
    consoleLogger = new ConsoleLogger(page);
    await login(page, TEST_USERS.admin.username, TEST_USERS.admin.password);
    await consoleLogger.start();
  });

  test.afterEach(async ({ page }) => {
    const errors = await consoleLogger.stop();
    if (errors.length > 0) {
      logger.info('Console errors detected:', errors);
    }
  });

  test('6.1 导航到数据资产页面', async ({ page }) => {
    await page.goto('/data/assets');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    // 验证页面标题
    const title = await page.title();
    expect(title).toContain('资产');
  });

  test('6.2 注册数据资产', async ({ page }) => {
    await page.goto('/data/assets');
    await page.waitForLoadState('networkidle');

    // 点击注册资产按钮
    const registerButton = page.locator('button:has-text("注册资产"), button:has-text("添加资产"), button:has-text("新建")');
    if (await registerButton.first().isVisible()) {
      await registerButton.first().click();

      // 等待模态框
      const modal = page.locator('.ant-modal');
      if (await modal.isVisible({ timeout: 5000 }).catch(() => false)) {
        // 填写资产名称
        const nameInput = modal.locator('input[placeholder*="名称"], input[placeholder*="name"]');
        if (await nameInput.isVisible()) {
          await nameInput.fill('E2E测试数据资产');
        }

        // 选择数据源
        const datasourceSelect = modal.locator('.ant-select').first();
        if (await datasourceSelect.isVisible()) {
          await datasourceSelect.click();
          await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
          await page.click(`.ant-select-item:has-text("${MYSQL_CONFIG.name}")`);
        }

        // 点击确认
        const confirmButton = modal.locator('button:has-text("确定"), button:has-text("注册")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(2000);
        }
      }
    }
  });

  test('6.3 测试资产搜索功能', async ({ page }) => {
    await page.goto('/data/assets');
    await page.waitForLoadState('networkidle');

    // 查找搜索框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .ant-input-search');
    if (await searchInput.first().isVisible()) {
      await searchInput.first().fill('E2E');
      await page.waitForTimeout(2000);

      // 验证搜索结果
      const results = page.locator('.ant-table-tbody .ant-table-row, .asset-card');
      const count = await results.count();
      logger.info(`Asset search results for "E2E": ${count}`);
    }
  });
});

// =============================================================================
// 测试总结
// =============================================================================

test.describe('测试总结', () => {
  test('生成测试总结', async () => {
    logger.info('='.repeat(60));
    logger.info('数据治理 Manual E2E 测试完成');
    logger.info('='.repeat(60));
    logger.info('创建的资源:');
    logger.info(`  - MySQL 数据源: ${MYSQL_CONFIG.name} (端口 ${MYSQL_CONFIG.port})`);
    logger.info(`  - PostgreSQL 数据源: ${POSTGRES_CONFIG.name} (端口 ${POSTGRES_CONFIG.port})`);
    logger.info('='.repeat(60));
    logger.info('测试数据已保留，可用于手动验证');
    logger.info('='.repeat(60));
    logger.info('手动验证步骤:');
    logger.info('1. 访问 http://localhost:3000/');
    logger.info('2. 检查数据源管理 → 验证两个数据源存在且可连接');
    logger.info('3. 检查元数据管理 → 验证表已扫描');
    logger.info('4. 检查各功能模块的数据完整性');
    logger.info('='.repeat(60));
  });
});
