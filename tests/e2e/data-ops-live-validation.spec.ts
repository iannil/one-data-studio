/**
 * DataOps 平台真实 API 验证测试
 * 连接真实后端 API，验证所有 DataOps 平台页面
 * 不使用 Mock 数据，捕获 Console 日志和 Network 请求
 */

import { test, expect } from '@playwright/test';
import { logger } from './helpers/logger';
import { setupAuth, BASE_URL } from './helpers';
import {
  PageValidator,
  DATA_OPS_LIVE_PAGES,
  DATA_OPS_PAGES_BY_MODULE,
  type PageValidationResult,
  type ConsoleLogEntry,
  type ApiRequestRecord,
} from './helpers/data-ops-validator';

/**
 * 测试结果收集器
 */
const results: PageValidationResult[] = [];

/**
 * 打印页面验证报告
 */
function printPageReport(result: PageValidationResult): void {
  const status = result.passed ? '✅' : '❌';
  const separator = '━'.repeat(50);

  logger.info(`\n${separator}`);
  logger.info(`${status} [${result.pageName}] ${result.route}`);
  logger.info(separator);

  // 页面加载状态
  const loadStatus = result.validations.pageLoaded ? '✓' : '✗';
  logger.info(`页面加载: ${(result.loadTime / 1000).toFixed(1)}s ${loadStatus}`);

  // 布局检查
  const layoutChecks = [
    result.validations.titleVisible ? '✓' : '✗',
    result.validations.layoutVisible ? '✓' : '✗',
  ];
  logger.info(`布局检查: ${layoutChecks.join(' ')}`);

  // JS 错误
  const jsErrors = result.errors.filter(e => e.includes('JavaScript'));
  logger.info(`JS错误: ${jsErrors.length > 0 ? jsErrors.length + '个' : '无'}`);

  // API 请求统计
  if (result.apiRequests && result.apiRequests.length > 0) {
    const successCount = result.apiRequests.filter(r => r.success).length;
    const failCount = result.apiRequests.length - successCount;
    logger.info(`API请求: ${result.apiRequests.length}个 (${successCount}成功, ${failCount}失败)`);

    // 显示失败的请求
    if (failCount > 0) {
      for (const req of result.apiRequests.filter(r => !r.success)) {
        logger.info(`  ✗ ${req.method} ${req.url} (${req.status})`);
      }
    }

    // 显示成功的请求（最多 5 个）
    const successRequests = result.apiRequests.filter(r => r.success).slice(0, 5);
    for (const req of successRequests) {
      logger.info(`  ✓ ${req.method} ${req.url} (${req.status}, ${req.responseTime}ms)`);
    }

    if (result.apiRequests.filter(r => r.success).length > 5) {
      logger.info(`  ... 还有 ${result.apiRequests.filter(r => r.success).length - 5} 个成功请求`);
    }
  } else {
    logger.info('API请求: 无');
  }

  // Console 日志
  if (result.consoleLogs && result.consoleLogs.length > 0) {
    const errorCount = result.consoleLogs.filter(l => l.level === 'error').length;
    const warnCount = result.consoleLogs.filter(l => l.level === 'warn').length;
    logger.info(`Console日志: ${result.consoleLogs.length}条 (错误:${errorCount}, 警告:${warnCount})`);

    // 显示错误日志
    for (const log of result.consoleLogs.filter(l => l.level === 'error')) {
      logger.info(`  ✗ [Error] ${log.message.substring(0, 100)}`);
    }

    // 显示警告日志（最多 3 个）
    const warnings = result.consoleLogs.filter(l => l.level === 'warn').slice(0, 3);
    for (const log of warnings) {
      logger.info(`  ⚠ [Warn] ${log.message.substring(0, 100)}`);
    }
  } else {
    logger.info('Console日志: 无');
  }

  // 截图路径
  if (result.screenshotPath) {
    logger.info(`截图: ${result.screenshotPath}`);
  }

  // 错误详情
  if (result.errors.length > 0) {
    logger.info('\n错误详情:');
    for (const error of result.errors) {
      logger.info(`  - ${error.substring(0, 150)}`);
    }
  }
}

/**
 * 生成最终汇总报告
 */
function generateSummaryReport(): void {
  logger.info('\n' + '━'.repeat(60));
  logger.info('DataOps 真实 API 验证测试汇总报告');
  logger.info('━'.repeat(60) + '\n');

  const passed = results.filter(r => r.passed);
  const failed = results.filter(r => !r.passed);

  logger.info(`总页面数: ${results.length}`);
  logger.info(`通过: ${passed.length}`);
  logger.info(`失败: ${failed.length}`);
  logger.info(`通过率: ${((passed.length / results.length) * 100).toFixed(1)}%\n`);

  // 失败页面详情
  if (failed.length > 0) {
    logger.info('─'.repeat(60));
    logger.info('失败页面详情:');
    logger.info('─'.repeat(60) + '\n');

    for (const result of failed) {
      logger.info(`❌ ${result.pageName} (${result.route})`);
      for (const error of result.errors) {
        logger.info(`   - ${error}`);
      }
      logger.info('');
    }
  }

  // API 请求统计
  const allApiRequests = results.flatMap(r => r.apiRequests || []);
  if (allApiRequests.length > 0) {
    const successRequests = allApiRequests.filter(r => r.success);
    const failedRequests = allApiRequests.filter(r => !r.success);

    logger.info('─'.repeat(60));
    logger.info('API 请求统计:');
    logger.info('─'.repeat(60) + '\n');
    logger.info(`总请求数: ${allApiRequests.length}`);
    logger.info(`成功: ${successRequests.length}`);
    logger.info(`失败: ${failedRequests.length}`);

    if (failedRequests.length > 0) {
      logger.info('\n失败的 API 请求:');
      const failedByUrl = new Map<string, ApiRequestRecord[]>();
      for (const req of failedRequests) {
        const url = req.url.split('?')[0]; // 移除查询参数
        if (!failedByUrl.has(url)) {
          failedByUrl.set(url, []);
        }
        failedByUrl.get(url)!.push(req);
      }

      for (const [url, reqs] of failedByUrl) {
        logger.info(`  - ${url} (${reqs.length}次失败)`);
      }
    }

    // 平均响应时间
    const avgResponseTime = successRequests.reduce((sum, r) => sum + r.responseTime, 0) / successRequests.length;
    logger.info(`\n平均响应时间: ${avgResponseTime.toFixed(0)}ms`);
  }

  // Console 错误汇总
  const allConsoleLogs = results.flatMap(r => r.consoleLogs || []);
  if (allConsoleLogs.length > 0) {
    const errorLogs = allConsoleLogs.filter(l => l.level === 'error');
    const warnLogs = allConsoleLogs.filter(l => l.level === 'warn');

    logger.info('\n─'.repeat(60));
    logger.info('Console 日志统计:');
    logger.info('─'.repeat(60) + '\n');
    logger.info(`总日志数: ${allConsoleLogs.length}`);
    logger.info(`错误: ${errorLogs.length}`);
    logger.info(`警告: ${warnLogs.length}`);

    if (errorLogs.length > 0) {
      logger.info('\n错误日志汇总:');
      const errorMessages = new Map<string, number>();
      for (const log of errorLogs) {
        const msg = log.message.substring(0, 100);
        errorMessages.set(msg, (errorMessages.get(msg) || 0) + 1);
      }

      for (const [msg, count] of errorMessages) {
        logger.info(`  - ${msg} (${count}次)`);
      }
    }
  }

  // 加载时间排名
  logger.info('\n─'.repeat(60));
  logger.info('页面加载时间排名:');
  logger.info('─'.repeat(60) + '\n');

  const sortedByLoadTime = [...results].sort((a, b) => a.loadTime - b.loadTime);
  logger.info('最快的前 5 个:');
  for (const result of sortedByLoadTime.slice(0, 5)) {
    logger.info(`  ${(result.loadTime / 1000).toFixed(1)}s - ${result.pageName}`);
  }

  logger.info('\n最慢的前 5 个:');
  for (const result of sortedByLoadTime.slice(-5).reverse()) {
    logger.info(`  ${(result.loadTime / 1000).toFixed(1)}s - ${result.pageName}`);
  }

  const avgLoadTime = results.reduce((sum, r) => sum + r.loadTime, 0) / results.length;
  logger.info(`\n平均加载时间: ${avgLoadTime.toFixed(0)}ms`);

  logger.info('\n' + '━'.repeat(60) + '\n');
}

/**
 * 在所有测试结束后生成报告
 */
test.afterAll(generateSummaryReport);

/**
 * 数据管理模块测试
 */
test.describe('DataOps Live - 数据管理模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.dataManagement;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言 - 真实 API 模式下使用更宽松的验证
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);

      // 对于真实 API，允许部分请求失败，但页面应该有基本布局
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 数据开发模块测试
 */
test.describe('DataOps Live - 数据开发模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.dataDevelopment;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 运维中心模块测试
 */
test.describe('DataOps Live - 运维中心模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.operations;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 元数据管理模块测试
 */
test.describe('DataOps Live - 元数据管理模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.metadata;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 分析工具模块测试
 */
test.describe('DataOps Live - 分析工具模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.analysis;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 数据集模块测试
 */
test.describe('DataOps Live - 数据集模块', () => {
  const pages = DATA_OPS_PAGES_BY_MODULE.datasets;

  for (const config of pages) {
    test(`${config.name} - 真实 API 验证`, async ({ page }) => {
      await setupAuth(page);

      const validator = new PageValidator(page);

      const result = await validator.validatePage(config);
      results.push(result);

      // 打印页面报告
      printPageReport(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      const hasBasicLayout = result.validations.layoutVisible || result.validations.titleVisible;
      expect(hasBasicLayout, '页面应有基本布局或标题').toBe(true);
    });
  }
});

/**
 * 综合测试 - 一次性验证所有页面
 */
test.describe('DataOps Live - 综合验证', () => {
  test('应验证所有 DataOps 页面（真实 API）', async ({ page }) => {
    await setupAuth(page);

    const validator = new PageValidator(page);
    let passedCount = 0;
    const allResults: PageValidationResult[] = [];

    for (const config of DATA_OPS_LIVE_PAGES) {
      const result = await validator.validatePage(config);
      allResults.push(result);

      if (result.passed) {
        passedCount++;
      }

      // 打印进度
      process.stdout.write(`\r${passedCount}/${allResults.length} 页面通过`);
    }

    logger.info(`\n\n最终结果: ${passedCount}/${DATA_OPS_LIVE_PAGES.length} 页面通过`);

    // 至少 60% 的页面应通过（真实 API 模式下更宽松）
    const passRate = passedCount / DATA_OPS_LIVE_PAGES.length;
    expect(passRate, '总体通过率应至少 60%').toBeGreaterThanOrEqual(0.6);

    // 将结果添加到全局结果集（用于最终报告）
    results.push(...allResults.filter(r => !results.some(existing => existing.route === r.route)));
  });
});
