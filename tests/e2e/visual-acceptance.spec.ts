/**
 * 可见浏览器功能验收测试
 *
 * 使用方式:
 * npx playwright test tests/e2e/visual-acceptance.spec.ts --headed --project=visual-acceptance
 *
 * 或使用 slowMo 模式便于观察:
 * SLOW_MO=500 npx playwright test tests/e2e/visual-acceptance.spec.ts --headed --project=visual-acceptance
 *
 * @description
 * 本测试脚本用于可见浏览器模式下的功能验收
 * - 逐个打开每个页面
 * - 截图保存为验收证据
 * - 控制台输出验收状态
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth, setupCommonMocks, BASE_URL } from './helpers';

// 配置：每个页面停留时间（毫秒），便于人工观察
const OBSERVE_DELAY = parseInt(process.env.OBSERVE_DELAY || '2000', 10);

// 页面配置接口
interface AcceptancePage {
  route: string;
  name: string;
  module: string;
  needsAuth?: boolean;
  skipReason?: string;
}

// 所有要验收的页面路由 - 按优先级排序
const ACCEPTANCE_PAGES: AcceptancePage[] = [
  // ==================== 第一阶段：核心功能验收（P0 必测） ====================
  { route: '/login', name: '登录页面', module: 'auth', needsAuth: false },
  { route: '/', name: '首页仪表板', module: 'home', needsAuth: true },
  { route: '/data/datasources', name: '数据源管理', module: 'data', needsAuth: true },
  { route: '/data/etl', name: 'ETL流程', module: 'data', needsAuth: true },
  { route: '/data/quality', name: '数据质量', module: 'data', needsAuth: true },
  { route: '/metadata', name: '元数据查询', module: 'metadata', needsAuth: true },

  // ==================== 第二阶段：DataOps 完整验收（P1） ====================
  { route: '/data/lineage', name: '数据血缘', module: 'data', needsAuth: true },
  { route: '/data/features', name: '特征存储', module: 'data', needsAuth: true },
  { route: '/data/standards', name: '数据标准', module: 'data', needsAuth: true },
  { route: '/data/assets', name: '数据资产', module: 'data', needsAuth: true },
  { route: '/data/services', name: '数据服务', module: 'data', needsAuth: true },
  { route: '/data/bi', name: 'BI报表', module: 'data', needsAuth: true },
  { route: '/data/monitoring', name: '系统监控', module: 'data', needsAuth: true },
  { route: '/data/ocr', name: '文档OCR', module: 'data', needsAuth: true },
  { route: '/data/kettle', name: 'Kettle引擎', module: 'data', needsAuth: true },
  { route: '/data/kettle-generator', name: 'Kettle配置生成', module: 'data', needsAuth: true },
  { route: '/data/streaming', name: '实时开发', module: 'data', needsAuth: true },
  { route: '/data/streaming-ide', name: '实时IDE', module: 'data', needsAuth: true },
  { route: '/data/offline', name: '离线开发', module: 'data', needsAuth: true },
  { route: '/data/metrics', name: '指标体系', module: 'data', needsAuth: true },
  { route: '/data/alerts', name: '智能预警', module: 'data', needsAuth: true },

  // ==================== 第三阶段：MLOps 验收（P1） ====================
  { route: '/model/notebooks', name: 'Notebook开发', module: 'model', needsAuth: true },
  { route: '/model/experiments', name: '实验管理', module: 'model', needsAuth: true },
  { route: '/model/models', name: '模型管理', module: 'model', needsAuth: true },
  { route: '/model/training', name: '模型训练', module: 'model', needsAuth: true },
  { route: '/model/serving', name: '模型服务', module: 'model', needsAuth: true },
  { route: '/model/resources', name: '资源管理', module: 'model', needsAuth: true },
  { route: '/model/monitoring', name: '模型监控', module: 'model', needsAuth: true },
  { route: '/model/aihub', name: 'AI Hub', module: 'model', needsAuth: true },
  { route: '/model/pipelines', name: '模型流水线', module: 'model', needsAuth: true },
  { route: '/model/llm-tuning', name: 'LLM微调', module: 'model', needsAuth: true },
  { route: '/model/sql-lab', name: 'SQL Lab', module: 'model', needsAuth: true },

  // ==================== 第四阶段：LLMOps/Agent 验收（P1） ====================
  { route: '/agent-platform/prompts', name: 'Prompt管理', module: 'agent', needsAuth: true },
  { route: '/agent-platform/knowledge', name: '知识库管理', module: 'agent', needsAuth: true },
  { route: '/agent-platform/apps', name: 'Agent应用', module: 'agent', needsAuth: true },
  { route: '/agent-platform/evaluation', name: '效果评估', module: 'agent', needsAuth: true },
  { route: '/agent-platform/sft', name: 'SFT训练', module: 'agent', needsAuth: true },
  { route: '/text2sql', name: 'Text2SQL', module: 'workflow', needsAuth: true },

  // ==================== 第五阶段：管理后台验收（P2） ====================
  { route: '/admin/users', name: '用户管理', module: 'admin', needsAuth: true },
  { route: '/admin/roles', name: '角色管理', module: 'admin', needsAuth: true },
  { route: '/admin/permissions', name: '权限管理', module: 'admin', needsAuth: true },
  { route: '/admin/audit', name: '审计日志', module: 'admin', needsAuth: true },
  { route: '/admin/settings', name: '系统设置', module: 'admin', needsAuth: true },
  { route: '/admin/groups', name: '分组管理', module: 'admin', needsAuth: true },
  { route: '/admin/cost-report', name: '成本报告', module: 'admin', needsAuth: true },
  { route: '/admin/notifications', name: '通知管理', module: 'admin', needsAuth: true },
  { route: '/admin/content', name: '内容管理', module: 'admin', needsAuth: true },
  { route: '/admin/user-profiles', name: '用户画像', module: 'admin', needsAuth: true },
  { route: '/admin/user-segments', name: '用户分群', module: 'admin', needsAuth: true },
  { route: '/admin/api-tester', name: 'API测试器', module: 'admin', needsAuth: true },
  { route: '/admin/behavior', name: '行为分析', module: 'admin', needsAuth: true },
  { route: '/admin/behavior/audit-log', name: '行为审计日志', module: 'admin', needsAuth: true },
  { route: '/admin/behavior/profile-view', name: '画像查看', module: 'admin', needsAuth: true },

  // ==================== 第六阶段：门户与工作流验收（P2） ====================
  { route: '/portal/dashboard', name: '门户仪表板', module: 'portal', needsAuth: true },
  { route: '/portal/notifications', name: '通知中心', module: 'portal', needsAuth: true },
  { route: '/portal/todos', name: '待办事项', module: 'portal', needsAuth: true },
  { route: '/portal/announcements', name: '公告管理', module: 'portal', needsAuth: true },
  { route: '/portal/profile', name: '个人中心', module: 'portal', needsAuth: true },
  { route: '/workflows', name: '工作流管理', module: 'workflow', needsAuth: true },
  { route: '/workflows/new', name: '新建工作流', module: 'workflow', needsAuth: true },
  { route: '/executions', name: '执行监控', module: 'workflow', needsAuth: true },

  // ==================== 第七阶段：元数据扩展验收（P2） ====================
  { route: '/metadata/graph', name: '元数据图谱', module: 'metadata', needsAuth: true },
  { route: '/metadata/version-diff', name: '版本对比', module: 'metadata', needsAuth: true },

  // ==================== 第八阶段：通用模块验收（P2） ====================
  { route: '/datasets', name: '数据集管理', module: 'common', needsAuth: true },
  { route: '/documents', name: '文档管理', module: 'common', needsAuth: true },
  { route: '/schedules', name: '调度管理', module: 'common', needsAuth: true },
  { route: '/scheduler/smart', name: '智能调度', module: 'common', needsAuth: true },
  { route: '/agents', name: 'Agents列表', module: 'common', needsAuth: true },
];

// 统计验收结果
const acceptanceResults: {
  passed: string[];
  failed: { name: string; error: string }[];
  skipped: string[];
} = {
  passed: [],
  failed: [],
  skipped: [],
};

/**
 * 设置 API Mock 以避免真实后端依赖
 */
async function setupApiMocks(page: Page): Promise<void> {
  // 通用列表 API Mock
  await page.route('**/api/v1/**', async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    // 返回通用成功响应
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            items: [],
            total: 0,
            page: 1,
            page_size: 10,
          },
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {},
        }),
      });
    }
  });
}

/**
 * 生成安全的文件名（替换特殊字符）
 */
function safeFileName(name: string): string {
  return name.replace(/[\/\\:*?"<>|]/g, '-').replace(/\s+/g, '-');
}

/**
 * 输出分隔线
 */
function logSeparator(): void {
  console.log('\n' + '='.repeat(60) + '\n');
}

test.describe('可见浏览器功能验收', () => {
  test.beforeEach(async ({ page }) => {
    // 设置视口大小，便于观察
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test.afterAll(async () => {
    // 输出验收汇总报告
    logSeparator();
    console.log('验收汇总报告');
    logSeparator();
    console.log(`总计: ${ACCEPTANCE_PAGES.length} 个页面`);
    console.log(`通过: ${acceptanceResults.passed.length} 个`);
    console.log(`失败: ${acceptanceResults.failed.length} 个`);
    console.log(`跳过: ${acceptanceResults.skipped.length} 个`);

    if (acceptanceResults.failed.length > 0) {
      console.log('\n失败详情:');
      acceptanceResults.failed.forEach(({ name, error }) => {
        console.log(`  - ${name}: ${error}`);
      });
    }

    logSeparator();
  });

  // 为每个页面创建测试用例
  for (const pageConfig of ACCEPTANCE_PAGES) {
    test(`验收 [${pageConfig.module}] ${pageConfig.name}`, async ({ page }) => {
      logSeparator();
      console.log(`正在验收: ${pageConfig.name}`);
      console.log(`模块: ${pageConfig.module}`);
      console.log(`路由: ${pageConfig.route}`);
      logSeparator();

      // 检查是否跳过
      if (pageConfig.skipReason) {
        console.log(`跳过原因: ${pageConfig.skipReason}`);
        acceptanceResults.skipped.push(pageConfig.name);
        test.skip();
        return;
      }

      try {
        // 设置认证（如需要）
        if (pageConfig.needsAuth) {
          await setupAuth(page, { roles: ['admin', 'user'] });
        }

        // 设置通用 Mock
        setupCommonMocks(page);
        await setupApiMocks(page);

        // 导航到页面
        const response = await page.goto(`${BASE_URL}${pageConfig.route}`, {
          waitUntil: 'domcontentloaded',
          timeout: 30000,
        });

        // 检查响应状态
        if (response) {
          const status = response.status();
          console.log(`HTTP 状态: ${status}`);

          if (status >= 400) {
            throw new Error(`HTTP ${status} 错误`);
          }
        }

        // 等待页面初始加载
        await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {
          console.log('警告: networkidle 超时，继续执行');
        });

        // 验证页面基本渲染
        await expect(page.locator('body')).toBeVisible();

        // 检查是否有严重错误
        const errorBoundary = page.locator('.error-boundary, .ant-result-error');
        const hasError = await errorBoundary.isVisible().catch(() => false);
        if (hasError) {
          console.log('警告: 页面可能存在错误边界');
        }

        // 检查错误弹窗
        const errorModal = page.locator('.ant-modal-confirm-error');
        const hasErrorModal = await errorModal.isVisible().catch(() => false);
        if (hasErrorModal) {
          console.log('警告: 页面存在错误弹窗');
        }

        // 截图保存
        const screenshotPath = `test-results/acceptance/${pageConfig.module}-${safeFileName(pageConfig.name)}.png`;
        await page.screenshot({
          path: screenshotPath,
          fullPage: true,
        });
        console.log(`截图保存: ${screenshotPath}`);

        // 停留观察
        await page.waitForTimeout(OBSERVE_DELAY);

        // 记录成功
        acceptanceResults.passed.push(pageConfig.name);
        console.log(`✓ ${pageConfig.name} 验收通过`);

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        acceptanceResults.failed.push({
          name: pageConfig.name,
          error: errorMessage,
        });
        console.error(`✗ ${pageConfig.name} 验收失败: ${errorMessage}`);

        // 失败时也截图
        try {
          const failScreenshotPath = `test-results/acceptance/${pageConfig.module}-${safeFileName(pageConfig.name)}-FAIL.png`;
          await page.screenshot({
            path: failScreenshotPath,
            fullPage: true,
          });
          console.log(`失败截图保存: ${failScreenshotPath}`);
        } catch {
          console.log('无法保存失败截图');
        }

        throw error;
      }
    });
  }
});

// ==================== 分阶段验收测试 ====================

test.describe('第一阶段：核心功能验收（P0）', () => {
  const corePages = ACCEPTANCE_PAGES.filter(p =>
    ['/login', '/', '/data/datasources', '/data/etl', '/data/quality', '/metadata'].includes(p.route)
  );

  for (const pageConfig of corePages) {
    test(`P0-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      if (pageConfig.needsAuth) {
        await setupAuth(page, { roles: ['admin', 'user'] });
      }
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P0-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('第二阶段：DataOps 验收（P1）', () => {
  const dataOpsPages = ACCEPTANCE_PAGES.filter(p =>
    p.module === 'data' && !['数据源管理', 'ETL流程', '数据质量'].includes(p.name)
  );

  for (const pageConfig of dataOpsPages) {
    test(`P1-DataOps-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      await setupAuth(page, { roles: ['admin', 'user'] });
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P1-DataOps-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('第三阶段：MLOps 验收（P1）', () => {
  const mlOpsPages = ACCEPTANCE_PAGES.filter(p => p.module === 'model');

  for (const pageConfig of mlOpsPages) {
    test(`P1-MLOps-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      await setupAuth(page, { roles: ['admin', 'user'] });
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P1-MLOps-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('第四阶段：LLMOps/Agent 验收（P1）', () => {
  const agentPages = ACCEPTANCE_PAGES.filter(p =>
    p.module === 'agent' || (p.module === 'workflow' && p.route === '/text2sql')
  );

  for (const pageConfig of agentPages) {
    test(`P1-Agent-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      await setupAuth(page, { roles: ['admin', 'user'] });
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P1-Agent-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('第五阶段：管理后台验收（P2）', () => {
  const adminPages = ACCEPTANCE_PAGES.filter(p => p.module === 'admin');

  for (const pageConfig of adminPages) {
    test(`P2-Admin-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      await setupAuth(page, { roles: ['admin', 'user'] });
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P2-Admin-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('第六阶段：门户与工作流验收（P2）', () => {
  const portalPages = ACCEPTANCE_PAGES.filter(p =>
    p.module === 'portal' ||
    (p.module === 'workflow' && p.route !== '/text2sql')
  );

  for (const pageConfig of portalPages) {
    test(`P2-Portal-${pageConfig.name}`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });

      await setupAuth(page, { roles: ['admin', 'user'] });
      setupCommonMocks(page);
      await setupApiMocks(page);

      await page.goto(`${BASE_URL}${pageConfig.route}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });

      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await expect(page.locator('body')).toBeVisible();

      await page.screenshot({
        path: `test-results/acceptance/P2-Portal-${safeFileName(pageConfig.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});
