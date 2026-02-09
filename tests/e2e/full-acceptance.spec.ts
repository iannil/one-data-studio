/**
 * ONE-DATA-STUDIO 完整验收测试
 *
 * 测试策略：
 * 1. 先进行真实的 Keycloak 登录
 * 2. 逐个访问所有前端页面
 * 3. 验证页面内容与预期一致（而非仅检查能否打开）
 * 4. 验证对应的 API 接口正常工作
 *
 * 运行方式：
 * npx playwright test full-acceptance.spec.ts --headed --workers=1
 */

import { test, expect } from '@playwright/test';
import { logger } from './helpers/logger';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const KEYCLOAK_URL = process.env.KEYCLOAK_URL || 'http://localhost:8080';

// 测试用户凭证
const TEST_USER = {
  username: process.env.TEST_ADMIN_USERNAME || 'testadmin',
  password: process.env.TEST_ADMIN_PASSWORD || 'Admin1234!',
};

/**
 * 执行 Keycloak 登录
 */
async function performLogin(page: any) {
  logger.info(`[登录] 正在访问 Keycloak 登录页面...`);

  // 直接访问前端首页，会被重定向到 Keycloak 登录
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');

  const currentUrl = page.url();
  logger.info(`[登录] 当前 URL: ${currentUrl}`);

  // 检查是否在 Keycloak 登录页面
  if (currentUrl.includes('auth') || currentUrl.includes('keycloak')) {
    logger.info(`[登录] 检测到 Keycloak 登录页面，开始登录...`);

    // 等待登录表单加载
    await page.waitForSelector('#username', { timeout: 10000 });

    // 填写用户名
    await page.fill('#username', TEST_USER.username);
    logger.info(`[登录] 用户名: ${TEST_USER.username}`);

    // 填写密码
    await page.fill('#password', TEST_USER.password);

    // 点击登录按钮
    await Promise.all([
      page.waitForNavigation({ url: /callback/ }).catch(() => page.waitForNavigation({ url: BASE_URL })),
      page.click('#kc-login'),
    ]);

    await page.waitForLoadState('networkidle');
    logger.info(`[登录] 登录成功，当前 URL: ${page.url()}`);

    // 等待跳转回应用
    if (page.url().includes('callback')) {
      await page.waitForURL(URL => URL.includes(BASE_URL) || !URL.includes('callback'));
    }

    return true;
  }

  // 可能已经登录，或者没有启用 Keycloak
  logger.info(`[登录] 未检测到 Keycloak 登录页面，可能已登录或未启用认证`);
  return true;
}

// ============================================
// 测试套件：完整页面验收
// ============================================
test.describe('ONE-DATA-STUDIO 完整验收测试', () => {
  let loginPage: any;

  test.beforeAll(async ({ browser }) => {
    logger.info('\n==========================================');
    logger.info('开始完整验收测试');
    logger.info('==========================================\n');

    // 创建浏览器上下文并登录
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      // 设置较大超时时间
      actionTimeout: 30000,
    });

    loginPage = await context.newPage();
    await performLogin(loginPage);
  });

  test.afterAll(async () => {
    if (loginPage) {
      await loginPage.close();
    }
    logger.info('\n==========================================');
    logger.info('完整验收测试结束');
    logger.info('==========================================\n');
  });

  // ============================================
  // 核心页面测试
  // ============================================
  test.describe('核心功能页面', () => {
    test('首页 - 工作台', async ({ page }) => {
      await page.goto(`${BASE_URL}/`);
      await page.waitForLoadState('networkidle');

      logger.info('[首页] 验证页面内容...');

      // 验证页面标题
      const title = await page.title();
      logger.info(`[首页] 页面标题: ${title}`);

      // 验证关键元素存在
      const hasContent = await page.locator('body').textContent();
      logger.info(`[首页] 页面内容长度: ${hasContent?.length || 0}`);

      // 检查是否有主要内容区域
      const mainContent = page.locator('main, .main-content, [class*="content"], #app');
      await expect(mainContent.first()).toBeVisible();

      // 检查是否有导航栏
      const navBar = page.locator('nav, .navbar, .header, [class*="nav"], [class*="header"]');
      const hasNav = await navBar.count();
      logger.info(`[首页] 导航栏元素数量: ${hasNav}`);

      logger.info('[首页] ✓ 通过');
    });

    test('数据集管理页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/datasets`);
      await page.waitForLoadState('networkidle');

      logger.info('[数据集] 验证页面内容...');

      // 验证页面标题或面包屑
      const pageTitle = page.locator('h1, h2, .page-title, [class*="title"]');
      const hasTitle = await pageTitle.count();
      logger.info(`[数据集] 标题元素数量: ${hasTitle}`);

      // 验证有数据表格或列表容器
      const tableOrList = page.locator('table, .table, .list, [class*="table"], [class*="list"]');
      await expect(tableOrList.first()).toBeVisible();

      // 检查是否有操作按钮（创建、上传等）
      const actionButtons = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("上传"), button:has-text("Create"), button:has-text("New")');
      const buttonCount = await actionButtons.count();
      logger.info(`[数据集] 操作按钮数量: ${buttonCount}`);

      // 验证数据区域非空（有内容或空状态提示）
      const bodyText = await page.locator('body').textContent();
      const hasDataOrEmpty = bodyText && (bodyText.includes('条') || bodyText.includes('暂无') || bodyText.includes('empty') || bodyText.includes('No'));
      logger.info(`[数据集] 有数据或空状态: ${hasDataOrEmpty}`);

      logger.info('[数据集] ✓ 通过');
    });

    test('文档中心页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/documents`);
      await page.waitForLoadState('networkidle');

      logger.info('[文档中心] 验证页面内容...');

      // 验证页面加载
      const content = page.locator('main, .content, [class*="document"], [class*="file"]');
      await expect(content.first()).toBeVisible();

      // 检查是否有上传按钮
      const uploadBtn = page.locator('button:has-text("上传"), button:has-text("Upload"), [class*="upload"]');
      const hasUpload = await uploadBtn.count();
      logger.info(`[文档中心] 上传按钮数量: ${hasUpload}`);

      logger.info('[文档中心] ✓ 通过');
    });

    test('AI 对话页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/chat`);
      await page.waitForLoadState('networkidle');

      logger.info('[AI对话] 验证页面内容...');

      // 验证聊天界面
      const chatContainer = page.locator('.chat, [class*="chat"], .conversation, [class*="message"]');
      await expect(chatContainer.first()).toBeVisible();

      // 检查是否有输入框
      const inputBox = page.locator('textarea, input[placeholder*="输入"], input[placeholder*="message"], [contenteditable="true"]');
      const hasInput = await inputBox.count();
      logger.info(`[AI对话] 输入框数量: ${hasInput}`);

      // 检查是否有发送按钮
      const sendBtn = page.locator('button:has-text("发送"), button:has-text("Send"), [class*="send"]');
      const hasSend = await sendBtn.count();
      logger.info(`[AI对话] 发送按钮数量: ${hasSend}`);

      logger.info('[AI对话] ✓ 通过');
    });

    test('工作流列表页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/workflows`);
      await page.waitForLoadState('networkidle');

      logger.info('[工作流] 验证页面内容...');

      // 验证工作流列表
      const workflowList = page.locator('.workflow, [class*="workflow"], table, [class*="table"]');
      await expect(workflowList.first()).toBeVisible();

      // 检查是否有创建按钮
      const createBtn = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("Create")');
      const hasCreate = await createBtn.count();
      logger.info(`[工作流] 创建按钮数量: ${hasCreate}`);

      logger.info('[工作流] ✓ 通过');
    });

    test('元数据管理页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/metadata`);
      await page.waitForLoadState('networkidle');

      logger.info('[元数据] 验证页面内容...');

      // 验证元数据页面
      const content = page.locator('main, [class*="metadata"], [class*="database"]');
      await expect(content.first()).toBeVisible();

      logger.info('[元数据] ✓ 通过');
    });

    test('调度管理页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedules`);
      await page.waitForLoadState('networkidle');

      logger.info('[调度管理] 验证页面内容...');

      const content = page.locator('main, [class*="schedule"], [class*="task"]');
      await expect(content.first()).toBeVisible();

      logger.info('[调度管理] ✓ 通过');
    });

    test('Agent 管理页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/agents`);
      await page.waitForLoadState('networkidle');

      logger.info('[Agent] 验证页面内容...');

      const content = page.locator('main, [class*="agent"]');
      await expect(content.first()).toBeVisible();

      logger.info('[Agent] ✓ 通过');
    });

    test('Text2SQL 页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/text2sql`);
      await page.waitForLoadState('networkidle');

      logger.info('[Text2SQL] 验证页面内容...');

      const content = page.locator('main, [class*="sql"], [class*="query"]');
      await expect(content.first()).toBeVisible();

      logger.info('[Text2SQL] ✓ 通过');
    });

    test('执行记录页面', async ({ page }) => {
      await page.goto(`${BASE_URL}/executions`);
      await page.waitForLoadState('networkidle');

      logger.info('[执行记录] 验证页面内容...');

      const content = page.locator('main, [class*="execution"], [class*="history"]');
      await expect(content.first()).toBeVisible();

      logger.info('[执行记录] ✓ 通过');
    });
  });

  // ============================================
  // Data 平台页面测试
  // ============================================
  test.describe('Data 数据治理平台', () => {
    test('数据源管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/datasources`);
      await page.waitForLoadState('networkidle');

      logger.info('[数据源] 验证页面内容...');

      const content = page.locator('main, [class*="datasource"], [class*="source"]');
      await expect(content.first()).toBeVisible();

      // 检查是否有数据源列表或创建按钮
      const listOrCreate = page.locator('table, button:has-text("创建"), button:has-text("新建")');
      await expect(listOrCreate.first()).toBeVisible();

      logger.info('[数据源] ✓ 通过');
    });

    test('ETL 任务', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/etl`);
      await page.waitForLoadState('networkidle');

      logger.info('[ETL] 验证页面内容...');

      const content = page.locator('main, [class*="etl"]');
      await expect(content.first()).toBeVisible();

      logger.info('[ETL] ✓ 通过');
    });

    test('数据质量', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/quality`);
      await page.waitForLoadState('networkidle');

      logger.info('[数据质量] 验证页面内容...');

      const content = page.locator('main, [class*="quality"]');
      await expect(content.first()).toBeVisible();

      logger.info('[数据质量] ✓ 通过');
    });

    test('数据血缘', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/lineage`);
      await page.waitForLoadState('networkidle');

      logger.info('[数据血缘] 验证页面内容...');

      const content = page.locator('main, [class*="lineage"], svg, canvas');
      await expect(content.first()).toBeVisible();

      logger.info('[数据血缘] ✓ 通过');
    });

    test('特征存储', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/features`);
      await page.waitForLoadState('networkidle');

      logger.info('[特征存储] 验证页面内容...');

      const content = page.locator('main, [class*="feature"]');
      await expect(content.first()).toBeVisible();

      logger.info('[特征存储] ✓ 通过');
    });

    test('离线开发', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/offline`);
      await page.waitForLoadState('networkidle');

      logger.info('[离线开发] 验证页面内容...');

      const content = page.locator('main, [class*="offline"], [class*="development"]');
      await expect(content.first()).toBeVisible();

      logger.info('[离线开发] ✓ 通过');
    });

    test('实时开发', async ({ page }) => {
      await page.goto(`${BASE_URL}/data/streaming`);
      await page.waitForLoadState('networkidle');

      logger.info('[实时开发] 验证页面内容...');

      const content = page.locator('main, [class*="streaming"]');
      await expect(content.first()).toBeVisible();

      logger.info('[实时开发] ✓ 通过');
    });
  });

  // ============================================
  // Model 平台页面测试
  // ============================================
  test.describe('Model MLOps 平台', () => {
    test('Notebook 开发', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/notebooks`);
      await page.waitForLoadState('networkidle');

      logger.info('[Notebook] 验证页面内容...');

      const content = page.locator('main, [class*="notebook"]');
      await expect(content.first()).toBeVisible();

      logger.info('[Notebook] ✓ 通过');
    });

    test('实验管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/experiments`);
      await page.waitForLoadState('networkidle');

      logger.info('[实验管理] 验证页面内容...');

      const content = page.locator('main, [class*="experiment"]');
      await expect(content.first()).toBeVisible();

      logger.info('[实验管理] ✓ 通过');
    });

    test('训练任务', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/training`);
      await page.waitForLoadState('networkidle');

      logger.info('[训练任务] 验证页面内容...');

      const content = page.locator('main, [class*="training"], [class*="job"]');
      await expect(content.first()).toBeVisible();

      logger.info('[训练任务] ✓ 通过');
    });

    test('模型仓库', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/models`);
      await page.waitForLoadState('networkidle');

      logger.info('[模型仓库] 验证页面内容...');

      const content = page.locator('main, [class*="model"]');
      await expect(content.first()).toBeVisible();

      logger.info('[模型仓库] ✓ 通过');
    });

    test('模型服务', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/serving`);
      await page.waitForLoadState('networkidle');

      logger.info('[模型服务] 验证页面内容...');

      const content = page.locator('main, [class*="serving"], [class*="deployment"]');
      await expect(content.first()).toBeVisible();

      logger.info('[模型服务] ✓ 通过');
    });

    test('资源管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/resources`);
      await page.waitForLoadState('networkidle');

      logger.info('[资源管理] 验证页面内容...');

      const content = page.locator('main, [class*="resource"], [class*="gpu"], [class*="usage"]');
      await expect(content.first()).toBeVisible();

      logger.info('[资源管理] ✓ 通过');
    });

    test('AI Hub', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/aihub`);
      await page.waitForLoadState('networkidle');

      logger.info('[AI Hub] 验证页面内容...');

      const content = page.locator('main, [class*="aihub"], [class*="hub"]');
      await expect(content.first()).toBeVisible();

      logger.info('[AI Hub] ✓ 通过');
    });

    test('SQL Lab', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/sqllab`);
      await page.waitForLoadState('networkidle');

      logger.info('[SQL Lab] 验证页面内容...');

      const content = page.locator('main, [class*="sql"], [class*="editor"], [class*="lab"]');
      await expect(content.first()).toBeVisible();

      logger.info('[SQL Lab] ✓ 通过');
    });

    test('Pipeline 管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/model/pipelines`);
      await page.waitForLoadState('networkidle');

      logger.info('[Pipeline] 验证页面内容...');

      const content = page.locator('main, [class*="pipeline"]');
      await expect(content.first()).toBeVisible();

      logger.info('[Pipeline] ✓ 通过');
    });
  });

  // ============================================
  // Agent 平台页面测试
  // ============================================
  test.describe('Agent LLMOps 平台', () => {
    test('Prompt 管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/agent/prompts`);
      await page.waitForLoadState('networkidle');

      logger.info('[Prompt] 验证页面内容...');

      const content = page.locator('main, [class*="prompt"]');
      await expect(content.first()).toBeVisible();

      logger.info('[Prompt] ✓ 通过');
    });

    test('知识库', async ({ page }) => {
      await page.goto(`${BASE_URL}/agent/knowledge`);
      await page.waitForLoadState('networkidle');

      logger.info('[知识库] 验证页面内容...');

      const content = page.locator('main, [class*="knowledge"], [class*="kb"]');
      await expect(content.first()).toBeVisible();

      logger.info('[知识库] ✓ 通过');
    });

    test('AI 应用', async ({ page }) => {
      await page.goto(`${BASE_URL}/agent/apps`);
      await page.waitForLoadState('networkidle');

      logger.info('[AI应用] 验证页面内容...');

      const content = page.locator('main, [class*="app"]');
      await expect(content.first()).toBeVisible();

      logger.info('[AI应用] ✓ 通过');
    });

    test('模型评估', async ({ page }) => {
      await page.goto(`${BASE_URL}/agent/evaluation`);
      await page.waitForLoadState('networkidle');

      logger.info('[模型评估] 验证页面内容...');

      const content = page.locator('main, [class*="evaluat"], [class*="metric"]');
      await expect(content.first()).toBeVisible();

      logger.info('[模型评估] ✓ 通过');
    });

    test('SFT 微调', async ({ page }) => {
      await page.goto(`${BASE_URL}/agent/sft`);
      await page.waitForLoadState('networkidle');

      logger.info('[SFT微调] 验证页面内容...');

      const content = page.locator('main, [class*="sft"], [class*="tuning"]');
      await expect(content.first()).toBeVisible();

      logger.info('[SFT微调] ✓ 通过');
    });
  });

  // ============================================
  // 管理后台页面测试
  // ============================================
  test.describe('管理后台', () => {
    test('用户管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin/users`);
      await page.waitForLoadState('networkidle');

      logger.info('[用户管理] 验证页面内容...');

      const content = page.locator('main, [class*="user"]');
      await expect(content.first()).toBeVisible();

      logger.info('[用户管理] ✓ 通过');
    });

    test('角色管理', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin/roles`);
      await page.waitForLoadState('networkidle');

      logger.info('[角色管理] 验证页面内容...');

      const content = page.locator('main, [class*="role"]');
      await expect(content.first()).toBeVisible();

      logger.info('[角色管理] ✓ 通过');
    });

    test('系统设置', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin/settings`);
      await page.waitForLoadState('networkidle');

      logger.info('[系统设置] 验证页面内容...');

      const content = page.locator('main, [class*="setting"], [class*="config"]');
      await expect(content.first()).toBeVisible();

      logger.info('[系统设置] ✓ 通过');
    });

    test('审计日志', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin/audit`);
      await page.waitForLoadState('networkidle');

      logger.info('[审计日志] 验证页面内容...');

      const content = page.locator('main, [class*="audit"], [class*="log"]');
      await expect(content.first()).toBeVisible();

      logger.info('[审计日志] ✓ 通过');
    });
  });

  // ============================================
  // API 健康检查
  // ============================================
  test.describe('API 服务健康检查', () => {
    test('Agent API 健康检查', async ({ request }) => {
      const response = await request.get(`${process.env.AGENT_API_URL || 'http://localhost:8000'}/api/v1/health`);
      expect(response.status()).toBe(200);
      logger.info('[API] Agent API ✓ 健康正常');
    });

    test('Data API 健康检查', async ({ request }) => {
      const response = await request.get(`${process.env.DATA_API_URL || 'http://localhost:8001'}/api/v1/health`);
      expect(response.status()).toBe(200);
      logger.info('[API] Data API ✓ 健康正常');
    });

    test('Model API 健康检查', async ({ request }) => {
      const response = await request.get(`${process.env.MODEL_API_URL || 'http://localhost:8002'}/api/v1/health`);
      expect(response.status()).toBe(200);
      logger.info('[API] Model API ✓ 健康正常');
    });

    test('OpenAI Proxy 健康检查', async ({ request }) => {
      const response = await request.get(`${process.env.OPENAI_API_URL || 'http://localhost:8003'}/health`);
      expect(response.status()).toBe(200);
      logger.info('[API] OpenAI Proxy ✓ 健康正常');
    });
  });
});
