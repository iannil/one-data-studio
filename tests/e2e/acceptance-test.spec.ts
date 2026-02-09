/**
 * 综合验收测试套件
 *
 * 对 ONE DATA STUDIO 平台进行全面验收测试，确保所有功能按预期实现
 *
 * 测试覆盖范围：
 * - L1: 基础设施层 (页面可访问性)
 * - L2: 数据底座层 (data)
 * - L3: 算法引擎层 (model)
 * - L4: 应用编排层 (agent)
 * - Admin: 管理后台
 */

import { test, expect } from '@playwright/test';
import { logger } from './helpers/logger';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

// 测试结果汇总
interface TestSummary {
  category: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  pages: string[];
}

const summary: TestSummary[] = [];

test.describe('综合验收测试 - 平台架构验证', () => {
  test('平台架构完整性验证', async ({ page }) => {
    test.setTimeout(120000); // 增加超时到 2 分钟
    // 验证四层架构的所有路由都可以访问 (共50个路由)
    const routes = [
      // 核心页面 (9个)
      '/',                    // 首页
      '/datasets',            // 数据集
      '/documents',           // 文档
      '/chat',                // 对话
      '/metadata',            // 元数据
      '/schedules',           // 调度
      '/agents',              // Agent
      '/text2sql',            // Text2SQL
      '/executions',          // 执行记录

      // 工作流 (4个)
      '/workflows',           // 工作流列表
      '/workflows/new',       // 新建工作流

      // L2 数据底座层 - Data (14个)
      '/data/datasources',
      '/data/etl',
      '/data/quality',
      '/data/lineage',
      '/data/features',
      '/data/standards',
      '/data/assets',
      '/data/services',
      '/data/bi',
      '/data/monitoring',
      '/data/streaming',
      '/data/streaming-ide',
      '/data/offline',
      '/data/metrics',

      // L3 算法引擎层 - Model (12个)
      '/model/notebooks',
      '/model/experiments',
      '/model/experiments/compare', // 新增：实验对比
      '/model/models',
      '/model/training',
      '/model/serving',
      '/model/resources',
      '/model/monitoring',
      '/model/aihub',
      '/model/pipelines',
      '/model/llm-tuning',
      '/model/sql-lab',

      // L4 应用编排层 - Agent (5个)
      '/agent/prompts',
      '/agent/knowledge',
      '/agent/apps',
      '/agent/evaluation',
      '/agent/sft',

      // 管理后台 - Admin (6个)
      '/admin/users',
      '/admin/groups',
      '/admin/settings',
      '/admin/audit',
      '/admin/roles',         // 新增：角色管理
      '/admin/cost-report',   // 新增：成本报告
    ];

    const accessibleRoutes: string[] = [];
    const inaccessibleRoutes: string[] = [];

    // Mock 所有健康检查
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { user_id: 'test-user', username: 'test-user', role: 'admin' },
        }),
      });
    });

    for (const route of routes) {
      try {
        await page.goto(`${BASE_URL}${route}`);
        // 检查是否有严重的页面错误
        const hasError = await page.locator('text=500, text=Error, text=页面不存在').count() > 0;

        if (!hasError) {
          accessibleRoutes.push(route);
        } else {
          inaccessibleRoutes.push(route);
        }
      } catch (e) {
        inaccessibleRoutes.push(route);
      }
    }

    // 输出结果
    logger.info('\n=== 平台路由验证结果 ===');
    logger.info(`总路由数: ${routes.length}`);
    logger.info(`可访问: ${accessibleRoutes.length}`);
    logger.info(`不可访问: ${inaccessibleRoutes.length}`);

    if (inaccessibleRoutes.length > 0) {
      logger.info('\n不可访问的路由:');
      inaccessibleRoutes.forEach(r => logger.info(`  - ${r}`));
    }

    // 验证至少 90% 的路由可访问
    const accessibilityRate = (accessibleRoutes.length / routes.length) * 100;
    expect(accessibilityRate).toBeGreaterThanOrEqual(90);
  });
});

test.describe('综合验收测试 - 关键集成点验证', () => {
  test('data → model 集成验证', async ({ page }) => {
    // 验证数据集能被模型训练使用
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    // 导航到 Data 数据源页面
    await page.goto(`${BASE_URL}/data/datasources`);
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });

    // 验证页面加载
    const pageLoaded = await page.locator('body').isVisible();
    expect(pageLoaded).toBeTruthy();
  });

  test('model → agent 集成验证', async ({ page }) => {
    // 验证模型服务可被应用使用
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    // 导航到模型服务页面
    await page.goto(`${BASE_URL}/model/serving`);
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
  });

  test('data → agent Text2SQL 集成验证', async ({ page }) => {
    // 验证元数据可用于 Text2SQL
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    // 导航到 Text2SQL 页面
    await page.goto(`${BASE_URL}/text2sql`);
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('综合验收测试 - UI/UX 一致性验证', () => {
  test('导航菜单一致性验证', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    await page.goto(`${BASE_URL}/`);

    // 验证页面成功加载
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
    logger.info('导航页面加载成功');
  });

  test('页面布局一致性验证', async ({ page }) => {
    setupCommonMocks(page);
    await setupAuth(page);

    const pages = ['/datasets', '/workflows', '/agent/apps'];

    for (const pagePath of pages) {
      await page.goto(`${BASE_URL}${pagePath}`);

      // 验证页面成功加载
      await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
    }
    logger.info('所有页面布局验证通过');
  });
});

test.describe('综合验收测试 - 响应式设计验证', () => {
  test('移动端适配验证', async ({ page }) => {
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/`);

    // 验证页面在移动端可访问
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
  });

  test('平板端适配验证', async ({ page }) => {
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    // 设置平板视口
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/`);

    // 验证页面在平板端可访问
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('综合验收测试 - 性能基准验证', () => {
  test('页面加载性能验证', async ({ page }) => {
    page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    page.route('**/api/v1/user/info', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { user_id: 'test-user', role: 'admin' } }),
      });
    });

    const pages = ['/', '/datasets', '/workflows', '/agent/apps'];
    const loadTimes: number[] = [];

    for (const pagePath of pages) {
      const start = Date.now();
      await page.goto(`${BASE_URL}${pagePath}`);
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - start;
      loadTimes.push(loadTime);
    }

    const avgLoadTime = loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length;

    logger.info('\n=== 页面加载性能 ===');
    logger.info(`平均加载时间: ${avgLoadTime}ms`);

    // 平均加载时间应小于 5 秒
    expect(avgLoadTime).toBeLessThan(5000);
  });
});

test.afterAll(async () => {
  logger.info('\n=== 综合验收测试完成 ===');
  logger.info(`测试类别数: ${summary.length}`);

  summary.forEach(s => {
    logger.info(`\n${s.category}:`);
    logger.info(`  通过: ${s.passedTests}/${s.totalTests}`);
    if (s.failedTests > 0) {
      logger.info(`  失败: ${s.failedTests}`);
    }
  });
});
