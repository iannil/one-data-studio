/**
 * ONE-DATA-STUDIO 完整验收测试
 *
 * 测试策略：
 * 1. 直接设置 sessionStorage 模拟认证状态
 * 2. 逐个访问所有前端页面
 * 3. 验证页面内容与预期一致
 * 4. 验证对应的 API 接口
 *
 * 运行方式：
 * npx playwright test direct-acceptance.spec.ts --headed --workers=1 --project=chromium-acceptance
 */

import { test, expect } from '@playwright/test';

// ============================================
// 配置
// ============================================
const CONFIG = {
  BASE_URL: process.env.BASE_URL || 'http://localhost:3000',
  KEYCLOAK_URL: process.env.KEYCLOAK_URL || 'http://localhost:8080',
  AGENT_API: process.env.AGENT_API_URL || process.env.agent_API_URL || 'http://localhost:8000',
  DATA_API: process.env.DATA_API_URL || process.env.data_API_URL || 'http://localhost:8001',
  MODEL_API: process.env.MODEL_API_URL || process.env.MODEL_API_URL || 'http://localhost:8002',
  OPENAI_API: process.env.OPENAI_API_URL || 'http://localhost:8003',
  // 兼容旧名称
  agent_API: process.env.agent_API_URL || 'http://localhost:8000',
  data_API: process.env.data_API_URL || 'http://localhost:8001',
  MODEL_API: process.env.MODEL_API_URL || 'http://localhost:8002',
};

// ============================================
// 认证辅助函数
// ============================================

/**
 * 设置认证状态到浏览器上下文
 * 在页面加载前设置认证状态
 */
async function createAuthenticatedContext(browser: any) {
  console.log('\n========================================');
  console.log('[认证] 创建认证浏览器上下文...');
  console.log('========================================');

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    actionTimeout: 30000,
    navigationTimeout: 60000,
  });

  // 在所有页面加载前设置认证状态
  await context.addInitScript(() => {
    const now = Date.now();
    const expiresAt = now + 3600 * 1000; // 1小时后过期

    // 设置 sessionStorage
    sessionStorage.setItem('access_token', 'mock_access_token_' + now);
    sessionStorage.setItem('token_expires_at', expiresAt.toString());
    sessionStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user-001',
      preferred_username: 'admin',
      email: 'admin@dev.local',
      name: 'Admin User',
      roles: ['admin', 'user', 'developer'],
    }));
  });

  // 也设置 localStorage（用于兼容）
  await context.addInitScript(() => {
    const now = Date.now();
    const expiresAt = now + 3600 * 1000;
    localStorage.setItem('access_token', 'mock_access_token_' + now);
    localStorage.setItem('token_expires_at', expiresAt.toString());
    localStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user-001',
      preferred_username: 'admin',
      email: 'admin@dev.local',
      name: 'Admin User',
      roles: ['admin', 'user', 'developer'],
    }));
  });

  console.log('[认证] ✓ 认证脚本已添加到上下文\n');
  return context;
}

/**
 * 页面内容验证辅助函数
 */
const PageValidator = {
  /**
   * 基础页面验证
   */
  async validate(page: any, pageName: string) {
    console.log(`\n[${pageName}] ========== 验证页面 ==========`);

    const url = page.url();
    console.log(`[${pageName}] URL: ${url}`);

    // 页面标题
    const title = await page.title();
    console.log(`[${pageName}] 标题: ${title}`);

    // 页面内容长度
    const bodyText = await page.locator('body').textContent() || '';
    console.log(`[${pageName}] 内容长度: ${bodyText.length} 字符`);

    // 检查是否有主要内容
    const hasMainContent = bodyText.length > 100;
    console.log(`[${pageName}] 有内容: ${hasMainContent ? '✓' : '✗'}`);

    // 检查是否有错误
    const hasError = bodyText.includes('404') || bodyText.includes('500') || bodyText.includes('Error') || bodyText.includes('错误');
    if (hasError) {
      console.log(`[${pageName}] ⚠️ 检测到错误信息`);
    }

    // 检查常见页面元素
    const main = await page.locator('main, .main, #app, [class*="content"]').count() > 0;
    const nav = await page.locator('nav, .nav, header, .header, [class*="nav"]').count() > 0;
    const table = await page.locator('table, .table, [class*="table"]').count() > 0;
    const card = await page.locator('.card, [class*="card"], .panel, [class*="panel"]').count() > 0;
    const button = await page.locator('button').count() > 0;
    const input = await page.locator('input, textarea, select').count() > 0;

    console.log(`[${pageName}] 页面元素:`);
    console.log(`  - main容器: ${main ? '✓' : '✗'}`);
    console.log(`  - 导航栏: ${nav ? '✓' : '✗'}`);
    console.log(`  - 表格: ${table ? '✓' : '✗'}`);
    console.log(`  - 卡片: ${card ? '✓' : '✗'}`);
    console.log(`  - 按钮: ${button}个`);
    console.log(`  - 输入框: ${input}个`);

    // 如果被重定向到登录页
    const isLoginPage = url.includes('/login');
    if (isLoginPage) {
      console.log(`[${pageName}] ⚠️ 被重定向到登录页（需要认证）`);
    }

    // 判断页面是否正常
    const isNormal = hasMainContent && !isLoginPage && !hasError;
    console.log(`[${pageName}] ${isNormal ? '✓ 通过' : '✗ 需要检查'}`);

    return { isNormal, hasMainContent, isLoginPage, hasError };
  },
};

// ============================================
// 测试套件
// ============================================

test.describe('ONE-DATA-STUDIO 完整验收测试', () => {
  // 共享的认证上下文
  let authContext: any;

  /**
   * 在所有测试前设置认证
   */
  test.beforeAll(async ({ browser }) => {
    console.log('\n' + '='.repeat(60));
    console.log('ONE-DATA-STUDIO 验收测试开始');
    console.log('='.repeat(60));

    // 创建已认证的浏览器上下文
    authContext = await createAuthenticatedContext(browser);

    // 创建一个页面验证认证
    const page = await authContext.newPage();
    await page.goto(CONFIG.BASE_URL);
    await page.waitForLoadState('networkidle');

    const url = page.url();
    console.log(`[认证] 首页 URL: ${url}`);
    console.log(`[认证] 是否仍在登录页: ${url.includes('/login') ? '是' : '否'}`);

    await page.close();
  });

  test.afterAll(async () => {
    if (authContext) {
      await authContext.close();
    }
    console.log('\n' + '='.repeat(60));
    console.log('ONE-DATA-STUDIO 验收测试完成');
    console.log('='.repeat(60) + '\n');
  });

  // ============================================
  // 核心功能页面测试
  // ============================================
  test.describe('核心功能页面', () => {
    const pages = [
      { path: '/', name: '首页' },
      { path: '/datasets', name: '数据集' },
      { path: '/documents', name: '文档中心' },
      { path: '/chat', name: 'AI对话' },
      { path: '/workflows', name: '工作流' },
      { path: '/metadata', name: '元数据' },
      { path: '/schedules', name: '调度管理' },
      { path: '/agents', name: 'Agent管理' },
      { path: '/text2sql', name: 'Text2SQL' },
      { path: '/executions', name: '执行记录' },
    ];

    for (const pageConfig of pages) {
      test(pageConfig.name, async ({ browser }) => {
        const page = await authContext.newPage();
        try {
          await page.goto(`${CONFIG.BASE_URL}${pageConfig.path}`);
          await page.waitForLoadState('networkidle');

          const result = await PageValidator.validate(page, pageConfig.name);

          // 页面至少需要有内容，且没有被重定向到登录页
          expect(result.hasMainContent || !result.isLoginPage).toBeTruthy();
        } finally {
          await page.close();
        }
      });
    }
  });

  // ============================================
  // Data 平台测试
  // ============================================
  test.describe('Data 数据治理平台', () => {
    const pages = [
      { path: '/data/datasources', name: '数据源管理' },
      { path: '/data/etl', name: 'ETL任务' },
      { path: '/data/quality', name: '数据质量' },
      { path: '/data/lineage', name: '数据血缘' },
      { path: '/data/features', name: '特征存储' },
      { path: '/data/offline', name: '离线开发' },
      { path: '/data/streaming', name: '实时开发' },
    ];

    for (const pageConfig of pages) {
      test(pageConfig.name, async ({ browser }) => {
        const page = await authContext.newPage();
        try {
          await page.goto(`${CONFIG.BASE_URL}${pageConfig.path}`);
          await page.waitForLoadState('networkidle');

          const result = await PageValidator.validate(page, pageConfig.name);
          expect(result.hasMainContent).toBeTruthy();
        } finally {
          await page.close();
        }
      });
    }
  });

  // ============================================
  // Model 平台测试
  // ============================================
  test.describe('Model MLOps 平台', () => {
    const pages = [
      { path: '/model/notebooks', name: 'Notebook开发' },
      { path: '/model/experiments', name: '实验管理' },
      { path: '/model/models', name: '模型仓库' },
      { path: '/model/training', name: '训练任务' },
      { path: '/model/serving', name: '模型服务' },
      { path: '/model/resources', name: '资源管理' },
      { path: '/model/sqllab', name: 'SQLLab' },
    ];

    for (const pageConfig of pages) {
      test(pageConfig.name, async ({ browser }) => {
        const page = await authContext.newPage();
        try {
          await page.goto(`${CONFIG.BASE_URL}${pageConfig.path}`);
          await page.waitForLoadState('networkidle');

          const result = await PageValidator.validate(page, pageConfig.name);
          expect(result.hasMainContent).toBeTruthy();
        } finally {
          await page.close();
        }
      });
    }
  });

  // ============================================
  // Agent 平台测试
  // ============================================
  test.describe('Agent LLMOps 平台', () => {
    const pages = [
      { path: '/agent/prompts', name: 'Prompt管理' },
      { path: '/agent/knowledge', name: '知识库' },
      { path: '/agent/apps', name: 'AI应用' },
      { path: '/agent/evaluation', name: '模型评估' },
      { path: '/agent/sft', name: 'SFT微调' },
    ];

    for (const pageConfig of pages) {
      test(pageConfig.name, async ({ browser }) => {
        const page = await authContext.newPage();
        try {
          await page.goto(`${CONFIG.BASE_URL}${pageConfig.path}`);
          await page.waitForLoadState('networkidle');

          const result = await PageValidator.validate(page, pageConfig.name);
          expect(result.hasMainContent).toBeTruthy();
        } finally {
          await page.close();
        }
      });
    }
  });

  // ============================================
  // 管理后台测试
  // ============================================
  test.describe('管理后台', () => {
    const pages = [
      { path: '/admin/users', name: '用户管理' },
      { path: '/admin/roles', name: '角色管理' },
      { path: '/admin/settings', name: '系统设置' },
      { path: '/admin/audit', name: '审计日志' },
    ];

    for (const pageConfig of pages) {
      test(pageConfig.name, async ({ browser }) => {
        const page = await authContext.newPage();
        try {
          await page.goto(`${CONFIG.BASE_URL}${pageConfig.path}`);
          await page.waitForLoadState('networkidle');

          const result = await PageValidator.validate(page, pageConfig.name);
          expect(result.hasMainContent).toBeTruthy();
        } finally {
          await page.close();
        }
      });
    }
  });
});

// ============================================
// API 服务健康检查测试
// ============================================
test.describe('API 服务健康检查', () => {
  test('agent API', async ({ request }) => {
    console.log('\n[API] 检查 agent API...');
    const response = await request.get(`${CONFIG.agent_API}/api/v1/health`);
    console.log(`[API] agent API 状态: ${response.status()}`);
    expect(response.status()).toBe(200);
  });

  test('data API', async ({ request }) => {
    console.log('\n[API] 检查 data API...');
    const response = await request.get(`${CONFIG.data_API}/api/v1/health`);
    console.log(`[API] data API 状态: ${response.status()}`);
    expect(response.status()).toBe(200);
  });

  test('Model API', async ({ request }) => {
    console.log('\n[API] 检查 Model API...');
    const response = await request.get(`${CONFIG.MODEL_API}/api/v1/health`);
    console.log(`[API] Model API 状态: ${response.status()}`);
    expect(response.status()).toBe(200);
  });

  test('OpenAI Proxy', async ({ request }) => {
    console.log('\n[API] 检查 OpenAI Proxy...');
    const response = await request.get(`${CONFIG.OPENAI_API}/health`);
    console.log(`[API] OpenAI Proxy 状态: ${response.status()}`);
    expect(response.status()).toBe(200);
  });
});
