/**
 * DataOps 平台功能测试规范 - 测试配置和辅助函数
 * 基于 docs/03-progress/test-specs/ 文档
 *
 * 功能总数: 321
 * 领域数: 6
 * 模块数: 28
 */

import { Page, expect, Locator } from '@playwright/test';
import { logger } from '../helpers/logger';

export const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// 测试结果统计
export interface TestStats {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  startTime: number;
  endTime?: number;
}

// 功能测试结果
export interface FeatureTestResult {
  featureId: string;
  featureName: string;
  module: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
  screenshot?: string;
}

// 全局测试统计
export const globalStats: TestStats = {
  total: 321,
  passed: 0,
  failed: 0,
  skipped: 0,
  startTime: Date.now(),
};

// 测试结果收集
export const testResults: FeatureTestResult[] = [];

/**
 * 设置认证状态
 */
export async function setupAuth(page: Page, roles: string[] = ['admin', 'user']) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: 'test-user',
    preferred_username: 'test-user',
    email: 'test@example.com',
    roles: roles,
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
    resource_access: { 'web-frontend': { roles } },
  })).toString('base64').replace(/=+$/, '');
  const mockToken = `${header}.${payload}.signature`;
  const expiresAt = Date.now() + 3600 * 24 * 1000;

  await page.addInitScript(({ token, expiresAt, roles }) => {
    sessionStorage.setItem('access_token', token);
    sessionStorage.setItem('token_expires_at', expiresAt.toString());
    sessionStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user',
      preferred_username: 'test-user',
      email: 'test@example.com',
      roles: roles,
    }));
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user',
      preferred_username: 'test-user',
      email: 'test@example.com',
      roles: roles,
    }));
  }, { token: mockToken, expiresAt, roles });
}

/**
 * 设置通用 Mock API
 */
export function setupCommonMocks(page: Page) {
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
        data: {
          user_id: 'test-user',
          username: 'test-user',
          email: 'test@example.com',
          role: 'admin',
        },
      }),
    });
  });
}

/**
 * 验证页面加载成功
 */
export async function verifyPageLoaded(page: Page, timeout = 10000): Promise<boolean> {
  try {
    await expect(page.locator('body')).toBeVisible({ timeout });
    // 等待加载指示器消失
    await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 5000 }).catch(() => {});
    return true;
  } catch {
    return false;
  }
}

/**
 * 验证表格存在
 */
export async function verifyTableExists(page: Page): Promise<boolean> {
  try {
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * 验证创建按钮存在
 */
export async function verifyCreateButtonExists(page: Page): Promise<Locator | null> {
  const selectors = [
    'button:has-text("新建")',
    'button:has-text("创建")',
    'button:has-text("添加")',
    'button:has-text("新增")',
    '[data-testid="create-btn"]',
    '.ant-btn-primary:has-text("新")',
  ];

  for (const selector of selectors) {
    const btn = page.locator(selector).first();
    if (await btn.isVisible().catch(() => false)) {
      return btn;
    }
  }
  return null;
}

/**
 * 验证筛选功能存在
 */
export async function verifyFilterExists(page: Page): Promise<boolean> {
  const selectors = [
    '.ant-select',
    '.ant-input-search',
    '[data-testid="filter"]',
    '.ant-picker',
  ];

  for (const selector of selectors) {
    if (await page.locator(selector).first().isVisible().catch(() => false)) {
      return true;
    }
  }
  return false;
}

/**
 * 验证分页存在
 */
export async function verifyPaginationExists(page: Page): Promise<boolean> {
  try {
    return await page.locator('.ant-pagination').isVisible();
  } catch {
    return false;
  }
}

/**
 * 点击创建按钮并验证弹窗
 */
export async function clickCreateAndVerifyModal(page: Page): Promise<boolean> {
  const createBtn = await verifyCreateButtonExists(page);
  if (!createBtn) return false;

  try {
    await createBtn.click();
    await page.waitForSelector('.ant-modal, .ant-drawer', { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * 记录功能测试结果
 */
export function recordTestResult(result: FeatureTestResult) {
  testResults.push(result);
  if (result.status === 'passed') {
    globalStats.passed++;
  } else if (result.status === 'failed') {
    globalStats.failed++;
  } else {
    globalStats.skipped++;
  }
  logger.info(`[${result.featureId}] ${result.featureName}: ${result.status.toUpperCase()}`);
}

/**
 * 生成测试报告
 */
export function generateReport(): string {
  globalStats.endTime = Date.now();
  const duration = (globalStats.endTime - globalStats.startTime) / 1000;

  let report = `# DataOps 平台功能测试报告\n\n`;
  report += `## 概览\n\n`;
  report += `| 指标 | 数值 |\n`;
  report += `|------|------|\n`;
  report += `| 总功能数 | ${globalStats.total} |\n`;
  report += `| 已测试 | ${globalStats.passed + globalStats.failed} |\n`;
  report += `| 通过 | ${globalStats.passed} |\n`;
  report += `| 失败 | ${globalStats.failed} |\n`;
  report += `| 跳过 | ${globalStats.skipped} |\n`;
  report += `| 通过率 | ${((globalStats.passed / (globalStats.passed + globalStats.failed)) * 100).toFixed(1)}% |\n`;
  report += `| 总耗时 | ${duration.toFixed(1)}s |\n\n`;

  // 按模块分组
  const byModule: Record<string, FeatureTestResult[]> = {};
  for (const result of testResults) {
    if (!byModule[result.module]) {
      byModule[result.module] = [];
    }
    byModule[result.module].push(result);
  }

  report += `## 按模块统计\n\n`;
  for (const [module, results] of Object.entries(byModule)) {
    const passed = results.filter(r => r.status === 'passed').length;
    const failed = results.filter(r => r.status === 'failed').length;
    report += `### ${module}\n\n`;
    report += `| 功能编号 | 功能名称 | 状态 | 耗时 |\n`;
    report += `|----------|----------|------|------|\n`;
    for (const r of results) {
      const statusIcon = r.status === 'passed' ? '✅' : r.status === 'failed' ? '❌' : '⏭️';
      report += `| ${r.featureId} | ${r.featureName} | ${statusIcon} | ${(r.duration / 1000).toFixed(1)}s |\n`;
    }
    report += `\n通过: ${passed}/${results.length}\n\n`;
  }

  return report;
}

/**
 * 页面路由映射
 */
export const PAGE_ROUTES: Record<string, string> = {
  // 数据接入
  'DS': '/data/datasources',
  'CDC': '/data/cdc',
  'FU': '/data/upload',

  // 数据处理
  'ETL': '/data/etl',
  'FLINK': '/data/streaming',
  'SIDE': '/data/streaming-ide',
  'OFF': '/data/offline',
  'KFK': '/data/streaming/kafka',

  // 数据治理
  'META': '/metadata',
  'LIN': '/data/lineage',
  'QUA': '/data/quality',
  'SEN': '/data/sensitivity',
  'STD': '/data/standards',
  'AST': '/data/assets',
  'FEA': '/data/features',
  'DST': '/datasets',

  // 监控运维
  'MON': '/data/monitoring',
  'ALT': '/data/alerts',
  'MTR': '/data/metrics',
  'AUD': '/admin/audit',

  // 数据利用
  'BI': '/data/bi',
  'SVC': '/data/services',
  'T2S': '/text2sql',
  'RAG': '/chat',

  // 平台支撑
  'APR': '/admin/approval',
  'AI': '/data/ai',
  'AUTH': '/admin/auth',
  'INT': '/admin/integrations',
};

/**
 * 获取功能对应的页面路由
 */
export function getRouteForFeature(featureId: string): string {
  const prefix = featureId.split('-')[0];
  return PAGE_ROUTES[prefix] || '/';
}
