/**
 * DataOps 平台页面 E2E 验证测试
 * 遍历所有 DataOps 平台页面，验证页面能正常加载并检查基本功能
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';
import {
  PageValidator,
  DATA_OPS_PAGES,
  DATA_OPS_PAGES_BY_TYPE,
  PageType,
  type PageValidationResult,
} from './helpers/data-ops-validator';

/**
 * 测试结果收集器
 */
const results: PageValidationResult[] = [];

/**
 * 生成测试摘要报告
 */
function generateSummaryReport(): void {
  console.log('\n========================================');
  console.log('DataOps 页面验证测试摘要');
  console.log('========================================\n');

  const passed = results.filter(r => r.passed);
  const failed = results.filter(r => !r.passed);

  console.log(`总页面数: ${results.length}`);
  console.log(`通过: ${passed.length}`);
  console.log(`失败: ${failed.length}`);
  console.log(`通过率: ${((passed.length / results.length) * 100).toFixed(1)}%\n`);

  // 失败页面详情
  if (failed.length > 0) {
    console.log('----------------------------------------');
    console.log('失败页面详情:');
    console.log('----------------------------------------\n');

    for (const result of failed) {
      console.log(`❌ ${result.pageName} (${result.route})`);
      for (const error of result.errors) {
        console.log(`   - ${error}`);
      }
      console.log('');
    }
  }

  // 通过页面列表
  console.log('----------------------------------------');
  console.log('通过页面列表:');
  console.log('----------------------------------------\n');

  for (const result of passed) {
    console.log(`✅ ${result.pageName} (${result.loadTime}ms)`);
  }

  // 加载时间统计
  const avgLoadTime = results.reduce((sum, r) => sum + r.loadTime, 0) / results.length;
  const maxLoadTime = Math.max(...results.map(r => r.loadTime));
  const minLoadTime = Math.min(...results.map(r => r.loadTime));

  console.log('\n----------------------------------------');
  console.log('加载时间统计:');
  console.log('----------------------------------------\n');
  console.log(`平均: ${avgLoadTime.toFixed(0)}ms`);
  console.log(`最快: ${minLoadTime}ms`);
  console.log(`最慢: ${maxLoadTime}ms`);

  console.log('\n========================================\n');
}

/**
 * 在所有测试结束后生成报告
 */
test.afterAll(generateSummaryReport);

/**
 * 数据管理页面测试
 */
test.describe('DataOps - 数据管理页面', () => {
  const dataManagementPages = [
    '/data/datasources',
    '/metadata',
    '/metadata/version-diff',
    '/data/features',
    '/data/standards',
    '/data/assets',
    '/data/services',
    '/data/bi',
    '/data/metrics',
  ];

  for (const route of dataManagementPages) {
    const config = DATA_OPS_PAGES.find(p => p.route === route);
    if (!config) continue;

    test(`${config.name} - 基本验证`, async ({ page }) => {
      setupCommonMocks(page);
      await setupAuth(page);

      const validator = new PageValidator(page);
      await validator.setupPageMocks(config);

      const result = await validator.validatePage(config);
      results.push(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      expect(result.validations.layoutVisible, '基本布局应可见').toBe(true);
    });
  }
});

/**
 * 数据开发页面测试
 */
test.describe('DataOps - 数据开发页面', () => {
  const dataDevelopmentPages = [
    '/data/etl',
    '/data/kettle',
    '/data/kettle-generator',
    '/data/ocr',
    '/data/quality',
    '/data/lineage',
    '/data/offline',
    '/data/streaming',
    '/data/streaming-ide',
  ];

  for (const route of dataDevelopmentPages) {
    const config = DATA_OPS_PAGES.find(p => p.route === route);
    if (!config) continue;

    test(`${config.name} - 基本验证`, async ({ page }) => {
      setupCommonMocks(page);
      await setupAuth(page);

      const validator = new PageValidator(page);
      await validator.setupPageMocks(config);

      const result = await validator.validatePage(config);
      results.push(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      expect(result.validations.layoutVisible, '基本布局应可见').toBe(true);
    });
  }
});

/**
 * 分析工具页面测试
 */
test.describe('DataOps - 分析工具页面', () => {
  const analysisToolPages = [
    '/model/notebooks',
    '/model/sql-lab',
  ];

  for (const route of analysisToolPages) {
    const config = DATA_OPS_PAGES.find(p => p.route === route);
    if (!config) continue;

    test(`${config.name} - 基本验证`, async ({ page }) => {
      setupCommonMocks(page);
      await setupAuth(page);

      const validator = new PageValidator(page);
      await validator.setupPageMocks(config);

      const result = await validator.validatePage(config);
      results.push(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      expect(result.validations.layoutVisible, '基本布局应可见').toBe(true);
    });
  }
});

/**
 * 其他 DataOps 页面测试
 */
test.describe('DataOps - 其他页面', () => {
  const otherPages = [
    '/datasets',
    '/data/monitoring',
    '/data/alerts',
  ];

  for (const route of otherPages) {
    const config = DATA_OPS_PAGES.find(p => p.route === route);
    if (!config) continue;

    test(`${config.name} - 基本验证`, async ({ page }) => {
      setupCommonMocks(page);
      await setupAuth(page);

      const validator = new PageValidator(page);
      await validator.setupPageMocks(config);

      const result = await validator.validatePage(config);
      results.push(result);

      // 断言
      expect(result.validations.pageLoaded, '页面应成功加载').toBe(true);
      expect(result.validations.noJSErrors, '不应有 JavaScript 错误').toBe(true);
      expect(result.validations.layoutVisible, '基本布局应可见').toBe(true);
    });
  }
});

/**
 * 按页面类型分组测试
 */
test.describe('DataOps - 列表页面验证', () => {
  const listPages = DATA_OPS_PAGES_BY_TYPE[PageType.List];

  test(`应验证所有列表页面 (${listPages.length} 个)`, async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    const listResults: PageValidationResult[] = [];

    for (const config of listPages) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);
      listResults.push(result);
    }

    // 至少 80% 的列表页面应通过
    const passRate = listResults.filter(r => r.passed).length / listResults.length;
    expect(passRate, '列表页面通过率应至少 80%').toBeGreaterThanOrEqual(0.8);
  });
});

test.describe('DataOps - 编辑器页面验证', () => {
  const editorPages = DATA_OPS_PAGES_BY_TYPE[PageType.Editor];

  test(`应验证所有编辑器页面 (${editorPages.length} 个)`, async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    const editorResults: PageValidationResult[] = [];

    for (const config of editorPages) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);
      editorResults.push(result);
    }

    // 至少 80% 的编辑器页面应通过
    const passRate = editorResults.filter(r => r.passed).length / editorPages.length;
    expect(passRate, '编辑器页面通过率应至少 80%').toBeGreaterThanOrEqual(0.8);
  });
});

test.describe('DataOps - 可视化页面验证', () => {
  const vizPages = DATA_OPS_PAGES_BY_TYPE[PageType.Visualization];

  test(`应验证所有可视化页面 (${vizPages.length} 个)`, async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    const vizResults: PageValidationResult[] = [];

    for (const config of vizPages) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);
      vizResults.push(result);
    }

    // 至少 75% 的可视化页面应通过
    const passRate = vizResults.filter(r => r.passed).length / vizPages.length;
    expect(passRate, '可视化页面通过率应至少 75%').toBeGreaterThanOrEqual(0.75);
  });
});

/**
 * 综合测试 - 一次性验证所有页面
 */
test.describe('DataOps - 综合验证', () => {
  test('应验证所有 DataOps 页面', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    let passedCount = 0;
    const allResults: PageValidationResult[] = [];

    for (const config of DATA_OPS_PAGES) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);
      allResults.push(result);

      if (result.passed) {
        passedCount++;
      }

      // 打印进度
      process.stdout.write(`\r${passedCount}/${allResults.length} 页面通过`);
    }

    console.log(`\n\n最终结果: ${passedCount}/${DATA_OPS_PAGES.length} 页面通过`);

    // 至少 75% 的页面应通过
    const passRate = passedCount / DATA_OPS_PAGES.length;
    expect(passRate, '总体通过率应至少 75%').toBeGreaterThanOrEqual(0.75);

    // 将结果添加到全局结果集（用于最终报告）
    results.push(...allResults.filter(r => !results.some(existing => existing.route === r.route)));
  });
});

/**
 * JavaScript 错误检测测试
 */
test.describe('DataOps - JavaScript 错误检测', () => {
  test('所有页面不应有 JavaScript 错误', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    const pagesWithErrors: { name: string; route: string; errors: string[] }[] = [];

    for (const config of DATA_OPS_PAGES) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);

      if (result.validations.noJSErrors === false) {
        pagesWithErrors.push({
          name: result.pageName,
          route: result.route,
          errors: validator.getJSErrors(),
        });
      }
    }

    if (pagesWithErrors.length > 0) {
      console.log('\n检测到 JavaScript 错误的页面:');
      for (const page of pagesWithErrors) {
        console.log(`  - ${page.name} (${page.route})`);
        for (const error of page.errors) {
          console.log(`    ${error}`);
        }
      }
    }

    // 不应有严重 JS 错误（允许少量非关键错误）
    expect(pagesWithErrors.length, '不应有 JavaScript 错误').toBe(0);
  });
});

/**
 * 页面加载性能测试
 */
test.describe('DataOps - 页面加载性能', () => {
  test('所有页面应在合理时间内加载', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const validator = new PageValidator(page);
    const slowPages: { name: string; route: string; loadTime: number }[] = [];
    const slowThreshold = 10000; // 10 秒阈值

    for (const config of DATA_OPS_PAGES) {
      await validator.setupPageMocks(config);
      const result = await validator.validatePage(config);

      if (result.loadTime > slowThreshold) {
        slowPages.push({
          name: result.pageName,
          route: result.route,
          loadTime: result.loadTime,
        });
      }
    }

    if (slowPages.length > 0) {
      console.log('\n加载较慢的页面:');
      for (const page of slowPages) {
        console.log(`  - ${page.name}: ${page.loadTime}ms`);
      }
    }

    // 最多允许 20% 的页面加载超过阈值
    expect(slowPages.length / DATA_OPS_PAGES.length, '超过 10 秒的页面比例应小于 20%').toBeLessThan(0.2);
  });
});
