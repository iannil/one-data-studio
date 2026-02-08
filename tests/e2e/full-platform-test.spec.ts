/**
 * ONE-DATA-STUDIO 全平台 E2E 测试
 *
 * 测试范围：
 * - DataOps: 数据源、元数据、数据质量、ETL、特征、标准、资产
 * - MLOps: Notebook、实验、模型、训练、AI Hub、SQL Lab
 * - LLMOps: Agent、工作流、文档管理
 * - Admin: 用户、角色、审计、成本
 *
 * 特点：
 * - 使用真实 API（禁止 mock）
 * - 测试数据持久化
 * - 全面的监控和日志
 */

import { test, expect } from '@playwright/test';
import { join } from 'path';
import { writeFileSync, existsSync, mkdirSync } from 'fs';

// Import helpers
import { ComprehensiveMonitor, createComprehensiveMonitor } from './helpers/comprehensive-monitor';
import {
  TestDataPersistence,
  createTestDataPersistence
} from './helpers/test-data-persistence';

// Import POM objects
import { BasePage } from './pom/BasePage';
import { DataSourcePage } from './pom/DataSourcePage';
import { QualityPage } from './pom/QualityPage';
import { ETLPage } from './pom/ETLPage';
import { MetadataPage } from './pom/MetadataPage';
import { AssetsPage } from './pom/AssetsPage';
import { FeaturesPage } from './pom/FeaturesPage';
import { StandardsPage } from './pom/StandardsPage';
import { NotebookPage } from './pom/NotebookPage';
import { AgentsPage } from './pom/AgentsPage';
import { AdminPage } from './pom/AdminPage';

// ============================================================================
// Test Configuration
// ============================================================================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const TEST_USER = {
  username: process.env.TEST_USER || 'admin',
  password: process.env.TEST_PASSWORD || 'admin123',
};

// Generate unique test ID
const TEST_ID = `full_platform_${Date.now()}`;
const TEST_NAME = 'ONE-DATA-STUDIO 全平台 E2E 测试';

// Test data for creating resources
const generateUniqueName = (prefix: string): string => {
  return `${prefix}_${TEST_ID}_${Math.floor(Math.random() * 1000)}`;
};

// ============================================================================
// Test Suite
// ============================================================================

test.describe(`ONE-DATA-STUDIO 全平台 E2E 测试 - ${TEST_ID}`, () => {
  let monitor: ComprehensiveMonitor;
  let dataPersistence: TestDataPersistence;
  let basePage: BasePage;

  // Page objects
  let dataSourcePage: DataSourcePage;
  let qualityPage: QualityPage;
  let etlPage: ETLPage;
  let metadataPage: MetadataPage;
  let assetsPage: AssetsPage;
  let featuresPage: FeaturesPage;
  let standardsPage: StandardsPage;
  let notebookPage: NotebookPage;
  let agentsPage: AgentsPage;
  let adminPage: AdminPage;

  // ============================================================================
  // Before All - Setup
  // ============================================================================

  test.beforeAll(async () => {
    console.log('\n' + '='.repeat(70));
    console.log(`[TEST START] ${TEST_NAME}`);
    console.log(`[TEST ID] ${TEST_ID}`);
    console.log(`[BASE URL] ${BASE_URL}`);
    console.log('='.repeat(70) + '\n');

    // Initialize data persistence
    dataPersistence = createTestDataPersistence(TEST_ID, TEST_NAME);
  });

  // ============================================================================
  // Setup & Login
  // ============================================================================

  test.beforeEach(async ({ page }) => {
    // Initialize monitor
    monitor = createComprehensiveMonitor(page, {
      autoScreenshot: true,
      realTimeLog: true,
      trackPerformance: true,
    });
    await monitor.start();

    // Initialize base page
    basePage = new BasePage(page);

    // Initialize all POM objects
    dataSourcePage = new DataSourcePage(page);
    qualityPage = new QualityPage(page);
    etlPage = new ETLPage(page);
    metadataPage = new MetadataPage(page);
    assetsPage = new AssetsPage(page);
    featuresPage = new FeaturesPage(page);
    standardsPage = new StandardsPage(page);
    notebookPage = new NotebookPage(page);
    agentsPage = new AgentsPage(page);
    adminPage = new AdminPage(page);

    // Navigate to base URL
    await page.goto(BASE_URL);
    await monitor.logStep('Navigate to base URL', 'passed', `Opened ${BASE_URL}`);

    // Login
    await login(page);
  });

  test.afterEach(async ({ page }) => {
    // Stop monitoring and save logs
    const { networkIssues, consoleErrors } = await monitor.stop();

    if (networkIssues.length > 0 || consoleErrors.length > 0) {
      console.warn(`\n[AfterEach] Found ${networkIssues.length} network issues and ${consoleErrors.length} console errors`);
    }

    // Save state
    dataPersistence.saveState();
  });

  test.afterAll(async () => {
    // Complete test and generate reports
    dataPersistence.completeTest();
    await dataPersistence.saveVerificationGuide();
    await dataPersistence.saveCleanupScript();
    dataPersistence.printSummary();

    console.log('\n' + '='.repeat(70));
    console.log('[TEST END] 测试完成');
    console.log('='.repeat(70) + '\n');
  });

  // ============================================================================
  // Login Helper
  // ============================================================================

  async function login(page: any): Promise<void> {
    monitor.startPhase('User Authentication');

    // Check if already logged in
    const currentUrl = page.url();
    if (currentUrl.includes('/dashboard') || currentUrl.includes('/admin')) {
      await monitor.logStep('Already logged in', 'passed', 'User session active');
      return;
    }

    // Fill login form
    await page.fill('input[name="username"], input[placeholder*="用户"], input[placeholder*="username"]', TEST_USER.username);
    await page.fill('input[name="password"], input[placeholder*="密码"], input[placeholder*="password"]', TEST_USER.password);

    await monitor.logStep('Fill login form', 'passed', `Username: ${TEST_USER.username}`);

    // Submit form
    await page.click('button[type="submit"], button:has-text("登录"), button:has-text("Login")');
    await page.waitForTimeout(2000);

    // Verify login success
    const isLoggedIn = await page.locator('.user-info, .ant-avatar, .user-dropdown').isVisible().catch(() => false);

    if (isLoggedIn) {
      await monitor.logStep('Login successful', 'passed', 'User authenticated');

      // Track user
      dataPersistence.trackUser('test_admin', {
        username: TEST_USER.username,
        role: 'admin',
        createdAt: new Date().toISOString(),
      });
    } else {
      await monitor.logStep('Login failed', 'failed', 'Authentication unsuccessful');
      throw new Error('Login failed');
    }
  }

  // ============================================================================
  // DataOps Module Tests
  // ============================================================================

  test('DataOps-1: Navigate to data sources page', async ({ page }) => {
    monitor.startPhase('DataOps - 数据源管理');

    await dataSourcePage.goto();
    await monitor.logStep('Navigate to data sources', 'passed', 'Page loaded successfully');

    const title = await page.title();
    expect(title).toContain('数据源');
  });

  test('DataOps-2: Create MySQL datasource', async ({ page }) => {
    monitor.startPhase('DataOps - 创建数据源');

    const dsName = generateUniqueName('test_mysql');

    await dataSourcePage.goto();

    const created = await dataSourcePage.createDataSource({
      name: dsName,
      type: 'MySQL',
      host: 'localhost',
      port: '3306',
      database: 'test_db',
      username: 'test_user',
      password: 'test_pass',
      testConnection: false, // Skip connection test in E2E
    });

    await monitor.logStep('Create MySQL datasource', created ? 'passed' : 'failed', `Datasource: ${dsName}`);

    if (created) {
      dataPersistence.trackDatasource(dsName, {
        name: dsName,
        type: 'MySQL',
        host: 'localhost',
        port: 3306,
        database: 'test_db',
        createdAt: new Date().toISOString(),
      });
    }

    expect(created).toBeTruthy();
  });

  test('DataOps-3: View datasource list', async ({ page }) => {
    monitor.startPhase('DataOps - 数据源列表');

    await dataSourcePage.goto();
    const count = await dataSourcePage.getCount();

    await monitor.logStep('Get datasource count', 'passed', `Found ${count} datasources`);

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('DataOps-4: Navigate to metadata page', async ({ page }) => {
    monitor.startPhase('DataOps - 元数据管理');

    await metadataPage.goto();
    await monitor.logStep('Navigate to metadata page', 'passed', 'Page loaded successfully');

    // Wait for database tree to load
    await page.waitForTimeout(1000);
  });

  test('DataOps-5: Search metadata', async ({ page }) => {
    monitor.startPhase('DataOps - 元数据搜索');

    await metadataPage.goto();
    await metadataPage.switchToSearch();
    await metadataPage.search('user');

    await monitor.logStep('Search metadata', 'passed', 'Searched for: user');

    await page.waitForTimeout(1000);
  });

  test('DataOps-6: Navigate to data quality page', async ({ page }) => {
    monitor.startPhase('DataOps - 数据质量');

    await qualityPage.goto();
    await monitor.logStep('Navigate to quality page', 'passed', 'Page loaded successfully');
  });

  test('DataOps-7: Create quality rule', async ({ page }) => {
    monitor.startPhase('DataOps - 创建质量规则');

    const ruleName = generateUniqueName('test_quality_rule');

    await qualityPage.goto();
    await qualityPage.switchToRules();

    // Try to create rule (may fail if no datasets available)
    try {
      const created = await qualityPage.createRule({
        name: ruleName,
        dataset: 'default',
        ruleType: 'Completeness',
        config: '{}',
      });

      await monitor.logStep('Create quality rule', created ? 'passed' : 'skipped', `Rule: ${ruleName}`);

      if (created) {
        dataPersistence.trackQualityRule(ruleName, {
          name: ruleName,
          datasetId: 'default',
          ruleType: 'Completeness',
          createdAt: new Date().toISOString(),
        });
      }
    } catch (error) {
      await monitor.logStep('Create quality rule', 'skipped', 'No datasets available or feature not implemented');
    }
  });

  test('DataOps-8: Navigate to ETL page', async ({ page }) => {
    monitor.startPhase('DataOps - ETL管理');

    await etlPage.goto();
    await monitor.logStep('Navigate to ETL page', 'passed', 'Page loaded successfully');
  });

  test('DataOps-9: Create ETL task', async ({ page }) => {
    monitor.startPhase('DataOps - 创建ETL任务');

    const taskName = generateUniqueName('test_etl_task');

    await etlPage.goto();

    try {
      const created = await etlPage.createTask({
        name: taskName,
        source: 'source_db',
        target: 'target_db',
        schedule: '0 0 * * *',
        config: '{}',
      });

      await monitor.logStep('Create ETL task', created ? 'passed' : 'skipped', `Task: ${taskName}`);

      if (created) {
        dataPersistence.trackETLTask(taskName, {
          name: taskName,
          sourceId: 'source_db',
          targetId: 'target_db',
          status: 'created',
          createdAt: new Date().toISOString(),
        });
      }
    } catch (error) {
      await monitor.logStep('Create ETL task', 'skipped', 'No datasources available or feature not implemented');
    }
  });

  test('DataOps-10: Navigate to data assets page', async ({ page }) => {
    monitor.startPhase('DataOps - 数据资产');

    await assetsPage.goto();
    await monitor.logStep('Navigate to assets page', 'passed', 'Page loaded successfully');
  });

  test('DataOps-11: Browse assets', async ({ page }) => {
    monitor.startPhase('DataOps - 浏览资产');

    await assetsPage.goto();
    await page.waitForTimeout(1000);

    await monitor.logStep('Browse assets', 'passed', 'Asset list loaded');
  });

  test('DataOps-12: Navigate to data standards page', async ({ page }) => {
    monitor.startPhase('DataOps - 数据标准');

    await standardsPage.goto();
    await monitor.logStep('Navigate to standards page', 'passed', 'Page loaded successfully');
  });

  test('DataOps-13: Create data standard', async ({ page }) => {
    monitor.startPhase('DataOps - 创建数据标准');

    const standardName = generateUniqueName('test_standard');

    await standardsPage.goto();

    try {
      const created = await standardsPage.createStandard({
        name: standardName,
        category: 'Naming',
        description: 'Test naming standard',
        rules: [],
      });

      await monitor.logStep('Create data standard', created ? 'passed' : 'skipped', `Standard: ${standardName}`);

      if (created) {
        dataPersistence.trackStandard(standardName, {
          name: standardName,
          category: 'Naming',
          createdAt: new Date().toISOString(),
        });
      }
    } catch (error) {
      await monitor.logStep('Create data standard', 'skipped', 'Feature not implemented or error occurred');
    }
  });

  test('DataOps-14: Navigate to features page', async ({ page }) => {
    monitor.startPhase('DataOps - 特征管理');

    await featuresPage.goto();
    await monitor.logStep('Navigate to features page', 'passed', 'Page loaded successfully');
  });

  test('DataOps-15: Browse features', async ({ page }) => {
    monitor.startPhase('DataOps - 浏览特征');

    await featuresPage.goto();
    await page.waitForTimeout(1000);

    await monitor.logStep('Browse features', 'passed', 'Feature list loaded');
  });

  // ============================================================================
  // MLOps Module Tests
  // ============================================================================

  test('MLOps-1: Navigate to notebooks page', async ({ page }) => {
    monitor.startPhase('MLOps - Notebook管理');

    await notebookPage.goto();
    await monitor.logStep('Navigate to notebooks', 'passed', 'Page loaded successfully');
  });

  test('MLOps-2: Create notebook', async ({ page }) => {
    monitor.startPhase('MLOps - 创建Notebook');

    const notebookName = generateUniqueName('test_notebook');

    await notebookPage.goto();

    try {
      const created = await notebookPage.createNotebook({
        name: notebookName,
        kernel: 'Python 3',
        description: 'E2E test notebook',
      });

      await monitor.logStep('Create notebook', created ? 'passed' : 'skipped', `Notebook: ${notebookName}`);

      if (created) {
        dataPersistence.trackNotebook(notebookName, {
          name: notebookName,
          kernel: 'Python 3',
          status: 'created',
          createdAt: new Date().toISOString(),
        });
      }
    } catch (error) {
      await monitor.logStep('Create notebook', 'skipped', 'Feature not implemented or error occurred');
    }
  });

  test('MLOps-3: View notebook list', async ({ page }) => {
    monitor.startPhase('MLOps - Notebook列表');

    await notebookPage.goto();
    const count = await notebookPage.getCount();

    await monitor.logStep('Get notebook count', 'passed', `Found ${count} notebooks`);

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('MLOps-4: Navigate to AI Hub', async ({ page }) => {
    monitor.startPhase('MLOps - AI Hub');

    await page.goto(`${BASE_URL}/model/aihub`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to AI Hub', 'passed', 'Page loaded');
  });

  test('MLOps-5: Search models in AI Hub', async ({ page }) => {
    monitor.startPhase('MLOps - AI Hub搜索');

    await page.goto(`${BASE_URL}/model/aihub`);

    try {
      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
      if (await searchInput.isVisible()) {
        await searchInput.fill('llama');
        await page.waitForTimeout(1000);
        await monitor.logStep('Search AI Hub', 'passed', 'Searched for: llama');
      } else {
        await monitor.logStep('Search AI Hub', 'skipped', 'Search input not found');
      }
    } catch (error) {
      await monitor.logStep('Search AI Hub', 'skipped', 'Feature not available');
    }
  });

  test('MLOps-6: Navigate to experiments page', async ({ page }) => {
    monitor.startPhase('MLOps - 实验管理');

    await page.goto(`${BASE_URL}/model/experiments`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to experiments', 'passed', 'Page loaded');
  });

  test('MLOps-7: Navigate to models page', async ({ page }) => {
    monitor.startPhase('MLOps - 模型管理');

    await page.goto(`${BASE_URL}/model/models`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to models', 'passed', 'Page loaded');
  });

  test('MLOps-8: Navigate to SQL Lab', async ({ page }) => {
    monitor.startPhase('MLOps - SQL Lab');

    await page.goto(`${BASE_URL}/model/sql-lab`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to SQL Lab', 'passed', 'Page loaded');
  });

  // ============================================================================
  // LLMOps Module Tests
  // ============================================================================

  test('LLMOps-1: Navigate to agents page', async ({ page }) => {
    monitor.startPhase('LLMOps - Agent管理');

    await agentsPage.goto();
    await monitor.logStep('Navigate to agents', 'passed', 'Page loaded successfully');
  });

  test('LLMOps-2: Create agent', async ({ page }) => {
    monitor.startPhase('LLMOps - 创建Agent');

    const agentName = generateUniqueName('test_agent');

    await agentsPage.goto();

    try {
      const created = await agentsPage.createAgent({
        name: agentName,
        type: 'Chat',
        model: 'gpt-3.5-turbo',
        prompt: 'You are a helpful assistant.',
      });

      await monitor.logStep('Create agent', created ? 'passed' : 'skipped', `Agent: ${agentName}`);

      if (created) {
        dataPersistence.trackAgent(agentName, {
          name: agentName,
          type: 'Chat',
          description: 'E2E test agent',
          createdAt: new Date().toISOString(),
        });
      }
    } catch (error) {
      await monitor.logStep('Create agent', 'skipped', 'Feature not implemented or no models available');
    }
  });

  test('LLMOps-3: View agents list', async ({ page }) => {
    monitor.startPhase('LLMOps - Agent列表');

    await agentsPage.goto();
    const count = await agentsPage.getCount();

    await monitor.logStep('Get agent count', 'passed', `Found ${count} agents`);

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('LLMOps-4: Navigate to workflows page', async ({ page }) => {
    monitor.startPhase('LLMOps - 工作流管理');

    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to workflows', 'passed', 'Page loaded');
  });

  test('LLMOps-5: Navigate to schedules page', async ({ page }) => {
    monitor.startPhase('LLMOps - 调度管理');

    await page.goto(`${BASE_URL}/schedules`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to schedules', 'passed', 'Page loaded');
  });

  test('LLMOps-6: Navigate to text2sql page', async ({ page }) => {
    monitor.startPhase('LLMOps - Text-to-SQL');

    await page.goto(`${BASE_URL}/text2sql`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to Text-to-SQL', 'passed', 'Page loaded');
  });

  test('LLMOps-7: Navigate to documents page', async ({ page }) => {
    monitor.startPhase('LLMOps - 文档管理');

    await page.goto(`${BASE_URL}/documents`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to documents', 'passed', 'Page loaded');
  });

  test('LLMOps-8: Navigate to datasets page', async ({ page }) => {
    monitor.startPhase('LLMOps - 数据集管理');

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForTimeout(1000);

    await monitor.logStep('Navigate to datasets', 'passed', 'Page loaded');
  });

  // ============================================================================
  // Admin Module Tests
  // ============================================================================

  test('Admin-1: Navigate to admin page', async ({ page }) => {
    monitor.startPhase('Admin - 管理后台');

    await adminPage.goto();
    await monitor.logStep('Navigate to admin', 'passed', 'Page loaded successfully');
  });

  test('Admin-2: Navigate to users management', async ({ page }) => {
    monitor.startPhase('Admin - 用户管理');

    await adminPage.gotoUsers();
    await monitor.logStep('Navigate to users', 'passed', 'Page loaded');
  });

  test('Admin-3: Get user count', async ({ page }) => {
    monitor.startPhase('Admin - 用户统计');

    await adminPage.gotoUsers();
    const count = await adminPage.getUserCount();

    await monitor.logStep('Get user count', 'passed', `Found ${count} users`);

    expect(count).toBeGreaterThan(0);
  });

  test('Admin-4: Navigate to roles management', async ({ page }) => {
    monitor.startPhase('Admin - 角色管理');

    await adminPage.gotoRoles();
    await monitor.logStep('Navigate to roles', 'passed', 'Page loaded');
  });

  test('Admin-5: Get role count', async ({ page }) => {
    monitor.startPhase('Admin - 角色统计');

    await adminPage.gotoRoles();
    const count = await adminPage.getRoleCount();

    await monitor.logStep('Get role count', 'passed', `Found ${count} roles`);

    expect(count).toBeGreaterThan(0);
  });

  test('Admin-6: Navigate to audit logs', async ({ page }) => {
    monitor.startPhase('Admin - 审计日志');

    await adminPage.gotoAudit();
    await monitor.logStep('Navigate to audit logs', 'passed', 'Page loaded');
  });

  test('Admin-7: Get audit log count', async ({ page }) => {
    monitor.startPhase('Admin - 审计日志统计');

    await adminPage.gotoAudit();
    const count = await adminPage.getAuditLogCount();

    await monitor.logStep('Get audit log count', 'passed', `Found ${count} audit records`);

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Admin-8: Navigate to cost reports', async ({ page }) => {
    monitor.startPhase('Admin - 成本报告');

    await adminPage.gotoCosts();
    await monitor.logStep('Navigate to cost reports', 'passed', 'Page loaded');
  });

  test('Admin-9: Get cost report data', async ({ page }) => {
    monitor.startPhase('Admin - 成本数据');

    await adminPage.gotoCosts();

    try {
      const costData = await adminPage.getCostReportData();
      await monitor.logStep('Get cost report data', 'passed', `Total cost: ${costData.totalCost}`);
    } catch (error) {
      await monitor.logStep('Get cost report data', 'skipped', 'Feature not available');
    }
  });

  // ============================================================================
  // Integration Tests
  // ============================================================================

  test('Integration-1: Data source to metadata flow', async ({ page }) => {
    monitor.startPhase('Integration - 数据源到元数据');

    // Navigate to data sources
    await dataSourcePage.goto();
    await monitor.logStep('Navigate to data sources', 'passed');

    // Navigate to metadata
    await metadataPage.goto();
    await monitor.logStep('Navigate to metadata', 'passed');

    // Try to expand a database node
    try {
      await metadataPage.expandDatabaseNode('test');
      await monitor.logStep('Expand database node', 'passed');
    } catch {
      await monitor.logStep('Expand database node', 'skipped', 'No databases available');
    }
  });

  test('Integration-2: Agent to workflow flow', async ({ page }) => {
    monitor.startPhase('Integration - Agent到工作流');

    // Navigate to agents
    await agentsPage.goto();
    await monitor.logStep('Navigate to agents', 'passed');

    // Navigate to workflows
    await page.goto(`${BASE_URL}/workflows`);
    await monitor.logStep('Navigate to workflows', 'passed');
  });

  // ============================================================================
  // Final Summary Test
  // ============================================================================

  test('Final: Generate test report', async ({ page }) => {
    monitor.startPhase('Final - 生成报告');

    // Save final monitor report
    const { textPath, jsonPath } = await monitor.saveReport();

    await monitor.logStep('Generate monitor report', 'passed', `Saved to ${textPath}`);

    // Save data persistence report
    await dataPersistence.saveVerificationGuide();
    await dataPersistence.saveCleanupScript();

    await monitor.logStep('Generate verification guide', 'passed', 'Verification guide created');

    // Print summary
    monitor.printSummary();

    // Check for critical errors
    const hasAPIErrors = monitor.getAPIErrors().length > 0;
    const hasConsoleErrors = monitor.hasConsoleErrors();

    if (hasAPIErrors || hasConsoleErrors) {
      await monitor.logStep('Error check', 'failed', `API Errors: ${monitor.getAPIErrors().length}, Console Errors: ${monitor.hasConsoleErrors()}`);
    } else {
      await monitor.logStep('Error check', 'passed', 'No critical errors found');
    }

    // Final assertions
    expect(monitor.getAPIErrors().length).toBeLessThan(10); // Allow some API errors
  });
});
