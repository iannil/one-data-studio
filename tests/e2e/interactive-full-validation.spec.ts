/**
 * 全面功能交互式验证测试
 *
 * 执行流程：
 * 1. 启动浏览器并登录
 * 2. 按模块逐个验证页面
 * 3. 执行 CRUD 操作
 * 4. 收集结果并生成报告
 * 5. 清理测试数据
 */

import { test, expect } from '@playwright/test';
import { Page } from '@playwright/test';
import { InteractiveValidator } from './helpers/interactive-validator';
import { TestDataManager } from './helpers/test-data-manager';
import { ReportGenerator } from './helpers/report-generator';
import { ALL_PAGES_CONFIG, getEnabledPages, getPagesByModule, getPageStats } from './config/all-pages.config';
import { setupAuth } from './fixtures/real-auth.fixture';
import { logger } from './helpers/logger';

// ==================== 全局变量 ====================

let dataManager: TestDataManager;
let reportGenerator: ReportGenerator;
const allResults: import('./helpers/interactive-validator').PageValidationResult[] = [];
let testStartTime: number = 0;
let globalAuthToken: string | null = null;

// ==================== 测试配置 ====================

// 配置超时
test.setTimeout(300 * 1000); // 5 分钟总超时

// ==================== 全局钩子 ====================

test.beforeAll(async () => {
  testStartTime = Date.now();
  logger.info('='.repeat(60));
  logger.info('Starting Interactive Full Validation Test Suite');
  logger.info('='.repeat(60));

  // 初始化数据管理器
  const apiBaseUrl = process.env.ADMIN_API_URL || 'http://localhost:8080';
  dataManager = new TestDataManager(apiBaseUrl);

  // 初始化报告生成器
  reportGenerator = new ReportGenerator();

  // 打印页面统计信息
  const stats = getPageStats();
  logger.info(`Total pages configured: ${stats.total}`);
  logger.info(`Enabled pages: ${stats.enabled}`);
  logger.info(`CRUD pages: ${stats.crud}`);
  logger.info(`Skipped pages: ${stats.skipped}`);
});

test.afterAll(async () => {
  const duration = Date.now() - testStartTime;

  logger.info('='.repeat(60));
  logger.info('All tests completed. Generating reports...');
  logger.info('='.repeat(60));

  // 生成最终报告
  const reportFiles = await reportGenerator.generateFullReport(allResults, duration);

  logger.info('Reports generated:');
  for (const file of reportFiles) {
    logger.info(`  - ${file}`);
  }

  // 打印汇总
  const passed = allResults.filter(r => isPagePassed(r)).length;
  const failed = allResults.length - passed;
  const passRate = allResults.length > 0 ? (passed / allResults.length) * 100 : 0;

  logger.info('='.repeat(60));
  logger.info('FINAL RESULTS');
  logger.info('='.repeat(60));
  logger.info(`Total: ${allResults.length}`);
  logger.info(`Passed: ${passed} (${passRate.toFixed(1)}%)`);
  logger.info(`Failed: ${failed}`);

  if (failed > 0) {
    logger.info('');
    logger.info('Failed pages:');
    for (const result of allResults) {
      if (!isPagePassed(result)) {
        logger.info(`  - ${result.pageName} (${result.route})`);
        for (const error of result.errors) {
          logger.info(`    Error: ${error}`);
        }
      }
    }
  }

  logger.info('='.repeat(60));
});

/**
 * 判断页面是否通过
 */
function isPagePassed(result: import('./helpers/interactive-validator').PageValidationResult): boolean {
  // 页面加载必须成功
  if (!result.pageLoad.success) return false;

  // 不能有错误（警告可以接受）
  if (result.errors.length > 0) return false;

  return true;
}

/**
 * 辅助函数：验证单个页面
 */
async function validateSinglePage(
  page: Page,
  request: any,
  pageConfig: any,
  role: string = 'admin'
): Promise<void> {
  // 每个测试都进行认证
  await setupAuth(page, request, { role });

  // 获取并存储 token
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  if (token) {
    globalAuthToken = token;
    dataManager.setAuthToken(token);
  }

  const validator = new InteractiveValidator(page, dataManager);
  const result = await validator.validatePageWithCRUD(pageConfig);

  allResults.push(result);

  // 基础断言
  expect(result.pageLoad.success, `${pageConfig.name} should load successfully`).toBe(true);

  // 打印操作结果
  if (result.operations.create) {
    logger.info(`  ${pageConfig.name} - Create: ${result.operations.create.success ? 'PASS' : 'FAIL'}`);
  }
  if (result.operations.read) {
    logger.info(`  ${pageConfig.name} - Read: ${result.operations.read.success ? 'PASS' : 'FAIL'}`);
  }
  if (result.operations.update) {
    logger.info(`  ${pageConfig.name} - Update: ${result.operations.update.success ? 'PASS' : 'FAIL'}`);
  }
  if (result.operations.delete) {
    logger.info(`  ${pageConfig.name} - Delete: ${result.operations.delete.success ? 'PASS' : 'FAIL'}`);
  }
}

// ==================== 基础认证模块 ====================

test.describe('基础认证模块', () => {
  const authPages = getPagesByModule().auth || [];

  for (const pageConfig of authPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 页面加载验证`, async ({ page, request }) => {
      await setupAuth(page, request, { role: 'admin' });

      const validator = new InteractiveValidator(page, dataManager);
      const result = await validator.validatePageWithCRUD(pageConfig);

      allResults.push(result);

      // 断言
      expect(result.pageLoad.success, `${pageConfig.name} should load successfully`).toBe(true);
      expect(result.errors, `${pageConfig.name} should have no errors`).toHaveLength(0);
    });
  }
});

// ==================== DataOps 数据治理模块 ====================

test.describe('DataOps 数据治理', () => {
  const dataPages = getPagesByModule().data || [];

  for (const pageConfig of dataPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'data_admin');
    });
  }
});

// ==================== MLOps 模型管理模块 ====================

test.describe('MLOps 模型管理', () => {
  const modelPages = getPagesByModule().model || [];

  for (const pageConfig of modelPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'admin');
    });
  }
});

// ==================== LLMOps Agent 平台模块 ====================

test.describe('LLMOps Agent 平台', () => {
  const agentPages = getPagesByModule().agent || [];

  for (const pageConfig of agentPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'admin');
    });
  }
});

// ==================== 工作流管理模块 ====================

test.describe('工作流管理', () => {
  const workflowPages = getPagesByModule().workflow || [];

  for (const pageConfig of workflowPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'data_admin');
    });
  }
});

// ==================== 元数据管理模块 ====================

test.describe('元数据管理', () => {
  const metadataPages = getPagesByModule().metadata || [];

  for (const pageConfig of metadataPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'data_admin');
    });
  }
});

// ==================== 管理后台模块 ====================

test.describe('管理后台', () => {
  const adminPages = getPagesByModule().admin || [];

  for (const pageConfig of adminPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'admin');
    });
  }
});

// ==================== 门户模块 ====================

test.describe('门户模块', () => {
  const portalPages = getPagesByModule().portal || [];

  for (const pageConfig of portalPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'admin');
    });
  }
});

// ==================== 通用模块 ====================

test.describe('通用模块', () => {
  const commonPages = getPagesByModule().common || [];

  for (const pageConfig of commonPages) {
    if (pageConfig.skip || pageConfig.enabled === false) {
      test.skip(true, `${pageConfig.name}: ${pageConfig.skipReason || 'Skipped'}`);
      continue;
    }

    test(`${pageConfig.name} - 完整验证`, async ({ page, request }) => {
      await validateSinglePage(page, request, pageConfig, 'data_admin');
    });
  }
});

// ==================== 综合测试 ====================

test.describe('综合测试', () => {
  test('生成综合测试报告', async () => {
    // 这个测试在所有模块测试完成后运行
    // 报告已在 afterAll 中生成

    expect(allResults.length).toBeGreaterThan(0);

    const passed = allResults.filter(r => isPagePassed(r)).length;
    const passRate = allResults.length > 0 ? (passed / allResults.length) * 100 : 0;

    logger.info(`Final pass rate: ${passRate.toFixed(1)}%`);

    // 至少要求 50% 的通过率
    expect(passRate).toBeGreaterThanOrEqual(50);
  });

  test('清理测试数据', async ({ request }) => {
    // 清理所有测试数据
    const cleanupResult = await dataManager.cleanupAll(request);

    logger.info(`Cleanup completed: ${cleanupResult.cleaned} cleaned, ${cleanupResult.failed} failed`);

    // 即使清理失败也不影响测试结果
    expect(cleanupResult.success || cleanupResult.cleaned > 0).toBeTruthy();
  });
});

// ==================== 快速验证模式 ====================

test.describe('快速验证模式', () => {
  /**
   * 仅验证页面加载，不执行 CRUD 操作
   * 用于快速检查所有页面是否可访问
   */
  test('所有页面快速加载验证', async ({ page, request }) => {
    await setupAuth(page, request, { role: 'admin' });

    const enabledPages = getEnabledPages();
    const results: Array<{ name: string; route: string; success: boolean; loadTime: number }> = [];

    for (const pageConfig of enabledPages) {
      try {
        const startTime = Date.now();
        await page.goto(pageConfig.route, { waitUntil: 'domcontentloaded', timeout: 30000 });
        const loadTime = Date.now() - startTime;

        // 检查是否有严重错误
        const hasError = await page.locator('.error-page, .exception, .fatal-error').isVisible({ timeout: 1000 }).catch(() => false);

        results.push({
          name: pageConfig.name,
          route: pageConfig.route,
          success: !hasError,
          loadTime,
        });

        logger.info(`Quick check: ${pageConfig.name} - ${!hasError ? 'OK' : 'FAIL'} (${loadTime}ms)`);

      } catch (error) {
        results.push({
          name: pageConfig.name,
          route: pageConfig.route,
          success: false,
          loadTime: 0,
        });
        logger.error(`Quick check failed: ${pageConfig.name} - ${error}`);
      }
    }

    const successCount = results.filter(r => r.success).length;
    const successRate = results.length > 0 ? (successCount / results.length) * 100 : 0;

    logger.info(`Quick check results: ${successCount}/${results.length} (${successRate.toFixed(1)}%)`);

    // 至少 80% 的页面应该能正常加载
    expect(successRate).toBeGreaterThanOrEqual(80);
  });
});
