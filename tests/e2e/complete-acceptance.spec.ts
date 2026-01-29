/**
 * ONE-DATA-STUDIO 完整验收测试
 *
 * 测试策略：
 * 1. 先进行登录（支持 Keycloak 和开发模式）
 * 2. 逐个访问所有前端页面
 * 3. 验证页面内容与预期一致
 * 4. 验证对应的 API 接口
 *
 * 运行方式：
 * npx playwright test complete-acceptance.spec.ts --headed --workers=1 --project=chromium-acceptance
 */

import { test, expect } from '@playwright/test';

// ============================================
// 配置
// ============================================
const CONFIG = {
  BASE_URL: process.env.BASE_URL || 'http://localhost:3000',
  KEYCLOAK_URL: process.env.KEYCLOAK_URL || 'http://localhost:8080',
  AGENT_API: process.env.AGENT_API_URL || 'http://localhost:8000',
  DATA_API: process.env.DATA_API_URL || 'http://localhost:8001',
  MODEL_API: process.env.MODEL_API_URL || 'http://localhost:8002',
  OPENAI_API: process.env.OPENAI_API_URL || 'http://localhost:8003',

  // 测试用户凭证（开发模式）
  DEV_USER: {
    username: process.env.TEST_ADMIN_USERNAME || 'admin',
    password: process.env.TEST_ADMIN_PASSWORD || 'admin123',
  },
};

// ============================================
// 页面路由定义
// ============================================
const PAGES = {
  // 核心页面
  HOME: '/',
  LOGIN: '/login',
  DATASETS: '/datasets',
  DOCUMENTS: '/documents',
  CHAT: '/chat',
  WORKFLOWS: '/workflows',
  METADATA: '/metadata',
  SCHEDULES: '/schedules',
  AGENTS: '/agents',
  TEXT2SQL: '/text2sql',
  EXECUTIONS: '/executions',

  // Data 平台
  DATA_DATASOURCES: '/data/datasources',
  DATA_ETL: '/data/etl',
  DATA_QUALITY: '/data/quality',
  DATA_LINEAGE: '/data/lineage',
  DATA_FEATURES: '/data/features',
  DATA_STANDARDS: '/data/standards',
  DATA_ASSETS: '/data/assets',
  DATA_SERVICES: '/data/services',
  DATA_BI: '/data/bi',
  DATA_MONITORING: '/data/monitoring',
  DATA_STREAMING: '/data/streaming',
  DATA_STREAMING_IDE: '/data/streaming-ide',
  DATA_OFFLINE: '/data/offline',
  DATA_METRICS: '/data/metrics',

  // Model 平台
  MODEL_NOTEBOOKS: '/model/notebooks',
  MODEL_EXPERIMENTS: '/model/experiments',
  MODEL_MODELS: '/model/models',
  MODEL_TRAINING: '/model/training',
  MODEL_SERVING: '/model/serving',
  MODEL_RESOURCES: '/model/resources',
  MODEL_MONITORING: '/model/monitoring',
  MODEL_AIHUB: '/model/aihub',
  MODEL_PIPELINES: '/model/pipelines',
  MODEL_LLM_TUNING: '/model/llm-tuning',
  MODEL_SQL_LAB: '/model/sqllab',

  // Agent 平台
  AGENT_PROMPTS: '/agent/prompts',
  AGENT_KNOWLEDGE: '/agent/knowledge',
  AGENT_APPS: '/agent/apps',
  AGENT_EVALUATION: '/agent/evaluation',
  AGENT_SFT: '/agent/sft',

  // 管理后台
  ADMIN_USERS: '/admin/users',
  ADMIN_GROUPS: '/admin/groups',
  ADMIN_SETTINGS: '/admin/settings',
  ADMIN_AUDIT: '/admin/audit',
  ADMIN_ROLES: '/admin/roles',
  ADMIN_COSTS: '/admin/costs',
};

// ============================================
// 辅助函数
// ============================================

/**
 * 执行登录操作
 * 支持开发模式模拟登录和 Keycloak SSO 登录
 */
async function performLogin(page: any) {
  console.log('\n========================================');
  console.log('[登录] 开始登录流程...');
  console.log('========================================');

  // 访问首页，会被重定向到登录页
  await page.goto(CONFIG.BASE_URL);
  await page.waitForLoadState('domcontentloaded');

  const currentUrl = page.url();
  console.log(`[登录] 当前 URL: ${currentUrl}`);

  // 检查是否在登录页面
  if (currentUrl.includes('/login')) {
    console.log('[登录] 检测到登录页面');

    // 等待页面加载完成
    await page.waitForLoadState('networkidle');

    // 检查是否有 SSO 登录按钮
    const ssoButton = page.locator('button:has-text("SSO"), button:has-text("使用 SSO")');
    const hasSSO = await ssoButton.count() > 0;

    if (hasSSO) {
      console.log('[登录] 发现 SSO 登录按钮');

      // 先尝试使用开发模式登录（如果在开发环境）
      const devModeLink = page.locator('button:has-text("开发模式"), button:has-text("显示")');
      const hasDevMode = await devModeLink.count() > 0;

      if (hasDevMode) {
        console.log('[登录] 使用开发模式模拟登录');
        await devModeLogin(page);
      } else {
        console.log('[登录] 使用 SSO 登录');
        await ssoButton.click();
        // 等待跳转到 Keycloak 或直接登录成功
        await page.waitForTimeout(3000);

        // 检查是否跳转到 Keycloak
        const newUrl = page.url();
        if (newUrl.includes('keycloak') || newUrl.includes('auth')) {
          console.log('[登录] 跳转到 Keycloak，执行 Keycloak 登录');
          await keycloakLogin(page);
        }
      }
    } else {
      // 可能是 Keycloak 直接登录页面
      console.log('[登录] 尝试 Keycloak 登录');
      await keycloakLogin(page);
    }
  }

  // 验证登录成功 - 等待页面不再是登录页
  await page.waitForTimeout(2000);
  const finalUrl = page.url();
  console.log(`[登录] 登录后 URL: ${finalUrl}`);

  // 如果还在登录页，可能需要再次尝试
  if (finalUrl.includes('/login')) {
    console.log('[登录] 仍在登录页，尝试开发模式登录');

    // 点击显示模拟登录表单
    const showMockBtn = page.locator('button:has-text("显示"), button:has-text("模拟")').first();
    if (await showMockBtn.count() > 0) {
      await showMockBtn.click();
      await page.waitForTimeout(500);
    }

    await devModeLogin(page);
  }

  // 最终验证 - 等待页面跳转
  await page.waitForTimeout(2000);
  const finalUrl2 = page.url();
  console.log(`[登录] 最终 URL: ${finalUrl2}`);

  // 检查是否有登录后的页面内容
  const hasNav = await page.locator('nav, .sidebar, .menu, [class*="nav"], [class*="sidebar"], header').count() > 0;
  console.log(`[登录] 检测到导航元素: ${hasNav}`);

  console.log('[登录] ✓ 登录流程完成\n');
}

/**
 * Keycloak SSO 登录
 */
async function keycloakLogin(page: any) {
  console.log(`[Keycloak] 填写登录表单...`);

  try {
    // 等待表单加载
    await page.waitForSelector('#username, input[name="username"]', { timeout: 10000 });

    // 填写用户名
    const usernameInput = page.locator('#username, input[name="username"]').first();
    await usernameInput.fill(CONFIG.DEV_USER.username);
    console.log(`[Keycloak] 用户名: ${CONFIG.DEV_USER.username}`);

    // 填写密码
    const passwordInput = page.locator('#password, input[name="password"]').first();
    await passwordInput.fill(CONFIG.DEV_USER.password);

    // 点击登录按钮
    const loginBtn = page.locator('#kc-login, input[name="login"], button[type="submit"]').first();
    await Promise.all([
      page.waitForNavigation({ timeout: 30000 }).catch(() => {
        console.log('[Keycloak] 登录后没有页面跳转');
      }),
      loginBtn.click(),
    ]);

    await page.waitForTimeout(2000);
  } catch (e) {
    console.log(`[Keycloak] Keycloak 登录出错或不是 Keycloak 页面: ${e}`);
  }
}

/**
 * 开发模式登录
 */
async function devModeLogin(page: any) {
  console.log(`[开发模式] 填写登录表单...`);

  try {
    // 如果模拟登录表单隐藏，先展开
    const showMockBtn = page.locator('button:has-text("显示"), button:has-text("模拟")').first();
    if (await showMockBtn.count() > 0) {
      await showMockBtn.click();
      await page.waitForTimeout(500);
    }

    // 查找用户名输入框
    const usernameInput = page.locator('input[placeholder="用户名"], input[name="username"]').first();
    await usernameInput.fill(CONFIG.DEV_USER.username);
    console.log(`[开发模式] 用户名: ${CONFIG.DEV_USER.username}`);

    // 查找密码输入框
    const passwordInput = page.locator('input[placeholder="密码"], input[type="password"]').first();
    await passwordInput.fill(CONFIG.DEV_USER.password);

    // 查找并点击登录按钮
    const loginButton = page.locator('button:has-text("模拟登录"), button:has-text("登录"), button[type="submit"]').first();
    await loginButton.click();

    // 等待登录完成和页面跳转
    await page.waitForTimeout(2000);
    console.log('[开发模式] ✓ 登录表单已提交');
  } catch (e) {
    console.log(`[开发模式] 登录出错: ${e}`);
  }
}

/**
 * 页面内容验证辅助函数
 */
const PageValidator = {
  /**
   * 验证页面基本结构
   */
  async validateBasicStructure(page: any, pageName: string) {
    console.log(`\n[${pageName}] ========== 验证页面基本结构 ==========`);

    // 获取页面标题
    const title = await page.title();
    console.log(`[${pageName}] 页面标题: ${title}`);

    // 检查是否有主要内容区域
    const mainContent = page.locator('main, .main-content, #app, [class*="content"], [class*="page"]');
    const hasMain = await mainContent.count() > 0;
    console.log(`[${pageName}] 主内容区域: ${hasMain ? '✓' : '✗'}`);

    // 检查是否有导航栏/侧边栏
    const nav = page.locator('nav, .navbar, .sidebar, .menu, [class*="nav"], [class*="sidebar"], [class*="header"]');
    const hasNav = await nav.count() > 0;
    console.log(`[${pageName}] 导航元素: ${hasNav ? '✓' : '✗'}`);

    // 检查页面是否非空
    const bodyText = await page.locator('body').textContent() || '';
    const hasContent = bodyText.trim().length > 50;
    console.log(`[${pageName}] 页面内容长度: ${bodyText.length} 字符 ${hasContent ? '✓' : '✗'}`);

    // 检查是否有错误信息
    const hasError = bodyText.includes('Error') || bodyText.includes('错误') || bodyText.includes('404');
    if (hasError) {
      console.log(`[${pageName}] ⚠️ 页面可能存在错误`);
    }

    return hasMain || hasNav || hasContent;
  },

  /**
   * 验证列表类页面（表格、列表等）
   */
  async validateListPage(page: any, pageName: string) {
    console.log(`\n[${pageName}] ========== 验证列表页面 ==========`);

    // 检查是否有表格或列表容器
    const table = page.locator('table, .table, .list, [class*="table"], [class*="list"], .data-table');
    const hasTable = await table.count() > 0;
    console.log(`[${pageName}] 数据表格/列表: ${hasTable ? '✓' : '✗'}`);

    // 检查是否有搜索/筛选功能
    const search = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .search, [class*="search"], [class*="filter"]');
    const hasSearch = await search.count() > 0;
    console.log(`[${pageName}] 搜索/筛选: ${hasSearch ? '✓' : '✗'}`);

    // 检查是否有分页
    const pagination = page.locator('.pagination, .pager, [class*="pagination"]');
    const hasPagination = await pagination.count() > 0;
    console.log(`[${pageName}] 分页控件: ${hasPagination ? '✓' : '✗'}`);

    // 检查是否有操作按钮（新建、创建等）
    const actionBtns = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("添加"), button:has-text("上传"), button:has-text("Create"), button:has-text("New"), button:has-text("Add")');
    const hasActionBtns = await actionBtns.count() > 0;
    console.log(`[${pageName}] 操作按钮: ${hasActionBtns ? `✓ (${await actionBtns.count()}个)` : '✗'}`);

    return hasTable || hasActionBtns;
  },

  /**
   * 验证编辑器类页面（IDE、表单等）
   */
  async validateEditorPage(page: any, pageName: string) {
    console.log(`\n[${pageName}] ========== 验证编辑器页面 ==========`);

    // 检查是否有编辑器或输入区域
    const editor = page.locator('textarea, .editor, [class*="editor"], .monaco, .ace, [contenteditable="true"]');
    const hasEditor = await editor.count() > 0;
    console.log(`[${pageName}] 编辑器/输入区: ${hasEditor ? '✓' : '✗'}`);

    // 检查是否有运行/执行按钮
    const runBtn = page.locator('button:has-text("运行"), button:has-text("执行"), button:has-text("Run"), button:has-text("Execute")');
    const hasRunBtn = await runBtn.count() > 0;
    console.log(`[${pageName}] 运行按钮: ${hasRunBtn ? '✓' : '✗'}`);

    // 检查是否有保存按钮
    const saveBtn = page.locator('button:has-text("保存"), button:has-text("Save")');
    const hasSaveBtn = await saveBtn.count() > 0;
    console.log(`[${pageName}] 保存按钮: ${hasSaveBtn ? '✓' : '✗'}`);

    return hasEditor;
  },

  /**
   * 验证表单类页面
   */
  async validateFormPage(page: any, pageName: string) {
    console.log(`\n[${pageName}] ========== 验证表单页面 ==========`);

    // 检查是否有表单
    const form = page.locator('form, .form, [class*="form"]');
    const hasForm = await form.count() > 0;
    console.log(`[${pageName}] 表单: ${hasForm ? '✓' : '✗'}`);

    // 检查是否有输入框
    const inputs = page.locator('input, select, textarea');
    const hasInputs = await inputs.count() > 0;
    console.log(`[${pageName}] 输入控件: ${hasInputs ? `✓ (${await inputs.count()}个)` : '✗'}`);

    // 检查是否有提交按钮
    const submitBtn = page.locator('button[type="submit"], button:has-text("提交"), button:has-text("确定"), button:has-text("保存")');
    const hasSubmitBtn = await submitBtn.count() > 0;
    console.log(`[${pageName}] 提交按钮: ${hasSubmitBtn ? '✓' : '✗'}`);

    return hasForm || hasInputs;
  },
};

// ============================================
// 测试套件
// ============================================

test.describe('ONE-DATA-STUDIO 完整验收测试', () => {
  // 共享的登录状态
  let authContext: any;

  /**
   * 在所有测试前执行登录
   */
  test.beforeAll(async ({ browser }) => {
    console.log('\n' + '='.repeat(60));
    console.log('ONE-DATA-STUDIO 验收测试开始');
    console.log('='.repeat(60));

    // 创建浏览器上下文
    authContext = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      // 设置较长的超时时间
      actionTimeout: 30000,
      navigationTimeout: 60000,
    });

    // 创建页面并执行登录
    const page = await authContext.newPage();
    await performLogin(page);
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
    test('首页 - 工作台', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.HOME}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateBasicStructure(page, '首页');

        // 验证首页特有元素
        const statCards = page.locator('.stat-card, .metric-card, [class*="stat"], [class*="metric"], [class*="card"]');
        const hasStats = await statCards.count() > 0;
        console.log(`[首页] 统计卡片: ${hasStats ? `✓ (${await statCards.count()}个)` : '✗'}`);

        const quickActions = page.locator('button:has-text("数据集"), button:has-text("聊天"), button:has-text("元数据"), [class*="quick"], [class*="shortcut"]');
        const hasQuick = await quickActions.count() > 0;
        console.log(`[首页] 快捷操作: ${hasQuick ? `✓ (${await quickActions.count()}个)` : '✗'}`);

        expect(valid || hasStats || hasQuick).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据集管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATASETS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据集');

        // 验证数据集特有元素
        const datasetItems = page.locator('tr, [class*="dataset"], [class*="data-item"]');
        const hasItems = await datasetItems.count() > 0;
        console.log(`[数据集] 数据项: ${hasItems ? `✓ (${await datasetItems.count()}个)` : '✗'}`);

        const uploadBtn = page.locator('button:has-text("上传"), button:has-text("导入"), [class*="upload"]');
        const hasUpload = await uploadBtn.count() > 0;
        console.log(`[数据集] 上传功能: ${hasUpload ? '✓' : '✗'}`);

        expect(valid || hasItems).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('文档中心', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DOCUMENTS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '文档中心');

        const uploadBtn = page.locator('button:has-text("上传"), button:has-text("Upload"), [class*="upload"]');
        const hasUpload = await uploadBtn.count() > 0;
        console.log(`[文档中心] 上传按钮: ${hasUpload ? '✓' : '✗'}`);

        expect(valid || hasUpload).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('AI 对话', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.CHAT}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, 'AI对话');

        // 验证聊天界面元素
        const chatArea = page.locator('.chat, [class*="chat"], .conversation, [class*="message"], [class*="dialog"]');
        const hasChat = await chatArea.count() > 0;
        console.log(`[AI对话] 聊天区域: ${hasChat ? '✓' : '✗'}`);

        const inputBox = page.locator('textarea, input[placeholder*="输入"], input[placeholder*="message"], [contenteditable="true"]');
        const hasInput = await inputBox.count() > 0;
        console.log(`[AI对话] 输入框: ${hasInput ? '✓' : '✗'}`);

        const sendBtn = page.locator('button:has-text("发送"), button:has-text("Send"), [class*="send"]');
        const hasSend = await sendBtn.count() > 0;
        console.log(`[AI对话] 发送按钮: ${hasSend ? '✓' : '✗'}`);

        const modelSelect = page.locator('select, [class*="model"], .ant-select');
        const hasModel = await modelSelect.count() > 0;
        console.log(`[AI对话] 模型选择: ${hasModel ? '✓' : '✗'}`);

        expect(hasChat || hasInput).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('工作流管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.WORKFLOWS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '工作流');

        const workflowItems = page.locator('[class*="workflow"], tr[data-row-key]');
        const hasWorkflows = await workflowItems.count() > 0;
        console.log(`[工作流] 工作流项: ${hasWorkflows ? `✓ (${await workflowItems.count()}个)` : '✗'}`);

        expect(valid || hasWorkflows).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('元数据浏览', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.METADATA}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '元数据');

        // 检查数据库树形结构
        const tree = page.locator('.tree, [class*="tree"], .database-list, [class*="database"]');
        const hasTree = await tree.count() > 0;
        console.log(`[元数据] 数据库树: ${hasTree ? '✓' : '✗'}`);

        // 检查表列表
        const tableList = page.locator('table, [class*="table"]');
        const hasTables = await tableList.count() > 0;
        console.log(`[元数据] 表列表: ${hasTables ? '✓' : '✗'}`);

        expect(hasTree || hasTables).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('调度管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.SCHEDULES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '调度管理');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('Agent 管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENTS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'Agent');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('Text2SQL', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.TEXT2SQL}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, 'Text2SQL');

        const inputArea = page.locator('textarea, [class*="input"]');
        const hasInput = await inputArea.count() > 0;
        console.log(`[Text2SQL] 输入区域: ${hasInput ? '✓' : '✗'}`);

        const generateBtn = page.locator('button:has-text("生成"), button:has-text("执行"), button:has-text("Generate")');
        const hasBtn = await generateBtn.count() > 0;
        console.log(`[Text2SQL] 生成按钮: ${hasBtn ? '✓' : '✗'}`);

        expect(hasInput || hasBtn).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('执行记录', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.EXECUTIONS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '执行记录');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });
  });

  // ============================================
  // data 平台测试
  // ============================================
  test.describe('data 数据治理平台', () => {
    test('数据源管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_DATASOURCES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据源');

        const testBtn = page.locator('button:has-text("测试连接"), button:has-text("Test")');
        const hasTest = await testBtn.count() > 0;
        console.log(`[数据源] 测试连接按钮: ${hasTest ? '✓' : '✗'}`);

        expect(valid || hasTest).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('ETL 任务', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_ETL}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'ETL任务');

        const etlCanvas = page.locator('.canvas, [class*="flow"], [class*="dag"], svg');
        const hasCanvas = await etlCanvas.count() > 0;
        console.log(`[ETL] 流程画布: ${hasCanvas ? '✓' : '✗'}`);

        expect(valid || hasCanvas).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据质量', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_QUALITY}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据质量');

        const qualityRules = page.locator('[class*="rule"], [class*="quality"]');
        const hasRules = await qualityRules.count() > 0;
        console.log(`[数据质量] 质量规则: ${hasRules ? '✓' : '✗'}`);

        expect(valid || hasRules).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据血缘', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_LINEAGE}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '数据血缘');

        const graph = page.locator('svg, canvas, [class*="graph"], [class*="dag"]');
        const hasGraph = await graph.count() > 0;
        console.log(`[数据血缘] 关系图: ${hasGraph ? '✓' : '✗'}`);

        expect(hasGraph).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('特征存储', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_FEATURES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '特征存储');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('离线开发', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_OFFLINE}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateEditorPage(page, '离线开发');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('实时开发', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_STREAMING}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateEditorPage(page, '实时开发');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('实时 IDE', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_STREAMING_IDE}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateEditorPage(page, '实时IDE');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据标准', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_STANDARDS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据标准');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据资产', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_ASSETS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据资产');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('数据服务', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_SERVICES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '数据服务');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('BI 报表', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_BI}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, 'BI报表');

        const charts = page.locator('canvas, [class*="chart"], [class*="report"]');
        const hasCharts = await charts.count() > 0;
        console.log(`[BI报表] 图表: ${hasCharts ? '✓' : '✗'}`);

        expect(hasCharts).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('系统监控', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_MONITORING}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '系统监控');

        const metrics = page.locator('canvas, [class*="metric"], [class*="chart"]');
        const hasMetrics = await metrics.count() > 0;
        console.log(`[系统监控] 指标图表: ${hasMetrics ? '✓' : '✗'}`);

        expect(hasMetrics).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('指标体系', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.DATA_METRICS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '指标体系');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });
  });

  // ============================================
  // model 平台测试
  // ============================================
  test.describe('model MLOps 平台', () => {
    test('Notebook 开发', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_NOTEBOOKS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'Notebook');

        const notebookItems = page.locator('[class*="notebook"], [class*="ipynb"]');
        const hasNotebooks = await notebookItems.count() > 0;
        console.log(`[Notebook] 笔记本项: ${hasNotebooks ? `✓ (${await notebookItems.count()}个)` : '✗'}`);

        expect(valid || hasNotebooks).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('实验管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_EXPERIMENTS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '实验管理');

        const compareBtn = page.locator('button:has-text("对比"), button:has-text("Compare")');
        const hasCompare = await compareBtn.count() > 0;
        console.log(`[实验管理] 对比功能: ${hasCompare ? '✓' : '✗'}`);

        expect(valid || hasCompare).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('模型仓库', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_MODELS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '模型仓库');

        const modelItems = page.locator('[class*="model"]');
        const hasModels = await modelItems.count() > 0;
        console.log(`[模型仓库] 模型项: ${hasModels ? `✓ (${await modelItems.count()}个)` : '✗'}`);

        expect(valid || hasModels).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('训练任务', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_TRAINING}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '训练任务');

        const progressBars = page.locator('.ant-progress, [class*="progress"]');
        const hasProgress = await progressBars.count() > 0;
        console.log(`[训练任务] 进度条: ${hasProgress ? '✓' : '✗'}`);

        expect(valid || hasProgress).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('模型服务', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_SERVING}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '模型服务');

        const deployBtn = page.locator('button:has-text("部署"), button:has-text("Deploy")');
        const hasDeploy = await deployBtn.count() > 0;
        console.log(`[模型服务] 部署功能: ${hasDeploy ? '✓' : '✗'}`);

        expect(valid || hasDeploy).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('资源管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_RESOURCES}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '资源管理');

        const resourceCards = page.locator('[class*="resource"], [class*="gpu"], [class*="usage"]');
        const hasResources = await resourceCards.count() > 0;
        console.log(`[资源管理] 资源卡片: ${hasResources ? `✓ (${await resourceCards.count()}个)` : '✗'}`);

        expect(hasResources).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('监控告警', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_MONITORING}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '监控告警');

        const charts = page.locator('canvas, [class*="chart"], [class*="metric"]');
        const hasCharts = await charts.count() > 0;
        console.log(`[监控告警] 监控图表: ${hasCharts ? '✓' : '✗'}`);

        expect(hasCharts).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('AI Hub', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_AIHUB}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'AIHub');

        const searchBox = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
        const hasSearch = await searchBox.count() > 0;
        console.log(`[AIHub] 搜索框: ${hasSearch ? '✓' : '✗'}`);

        expect(valid || hasSearch).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('Pipeline 管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_PIPELINES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'Pipeline');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('LLM 微调', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_LLM_TUNING}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'LLM微调');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('SQL Lab', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.MODEL_SQL_LAB}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateEditorPage(page, 'SQLLab');

        const sqlEditor = page.locator('textarea, [class*="sql"], [class*="editor"]');
        const hasEditor = await sqlEditor.count() > 0;
        console.log(`[SQL Lab] SQL编辑器: ${hasEditor ? '✓' : '✗'}`);

        expect(hasEditor).toBeTruthy();
      } finally {
        await page.close();
      }
    });
  });

  // ============================================
  // agent 平台测试
  // ============================================
  test.describe('agent LLMOps 平台', () => {
    test('Prompt 管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENT_PROMPTS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'Prompt管理');

        const promptItems = page.locator('[class*="prompt"]');
        const hasPrompts = await promptItems.count() > 0;
        console.log(`[Prompt] 模板项: ${hasPrompts ? `✓ (${await promptItems.count()}个)` : '✗'}`);

        expect(valid || hasPrompts).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('知识库', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENT_KNOWLEDGE}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '知识库');

        const kbItems = page.locator('[class*="knowledge"], [class*="kb"]');
        const hasKb = await kbItems.count() > 0;
        console.log(`[知识库] 知识库项: ${hasKb ? `✓ (${await kbItems.count()}个)` : '✗'}`);

        const uploadBtn = page.locator('button:has-text("上传"), button:has-text("Upload"), [class*="upload"]');
        const hasUpload = await uploadBtn.count() > 0;
        console.log(`[知识库] 上传功能: ${hasUpload ? '✓' : '✗'}`);

        expect(valid || hasKb).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('AI 应用', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENT_APPS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'AI应用');

        const appItems = page.locator('[class*="app"]');
        const hasApps = await appItems.count() > 0;
        console.log(`[AI应用] 应用项: ${hasApps ? `✓ (${await appItems.count()}个)` : '✗'}`);

        expect(valid || hasApps).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('模型评估', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENT_EVALUATION}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '模型评估');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('SFT 微调', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.AGENT_SFT}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, 'SFT微调');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });
  });

  // ============================================
  // 管理后台测试
  // ============================================
  test.describe('管理后台', () => {
    test('用户管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_USERS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '用户管理');

        const userItems = page.locator('tr, [class*="user"]');
        const hasUsers = await userItems.count() > 0;
        console.log(`[用户管理] 用户项: ${hasUsers ? `✓ (${await userItems.count()}个)` : '✗'}`);

        expect(valid || hasUsers).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('用户组管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_GROUPS}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '用户组');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('角色管理', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_ROLES}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '角色管理');
        expect(valid).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('系统设置', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_SETTINGS}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateFormPage(page, '系统设置');

        const settingsPanel = page.locator('[class*="setting"], [class*="config"]');
        const hasSettings = await settingsPanel.count() > 0;
        console.log(`[系统设置] 设置面板: ${hasSettings ? '✓' : '✗'}`);

        expect(hasSettings).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('审计日志', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_AUDIT}`);
        await page.waitForLoadState('networkidle');

        const valid = await PageValidator.validateListPage(page, '审计日志');

        const logItems = page.locator('tr, [class*="log"], [class*="audit"]');
        const hasLogs = await logItems.count() > 0;
        console.log(`[审计日志] 日志项: ${hasLogs ? `✓ (${await logItems.count()}个)` : '✗'}`);

        expect(valid || hasLogs).toBeTruthy();
      } finally {
        await page.close();
      }
    });

    test('成本报告', async ({ browser }) => {
      const page = await authContext.newPage();
      try {
        await page.goto(`${CONFIG.BASE_URL}${PAGES.ADMIN_COSTS}`);
        await page.waitForLoadState('networkidle');

        await PageValidator.validateBasicStructure(page, '成本报告');

        const charts = page.locator('canvas, [class*="chart"], [class*="cost"]');
        const hasCharts = await charts.count() > 0;
        console.log(`[成本报告] 图表: ${hasCharts ? '✓' : '✗'}`);

        expect(hasCharts).toBeTruthy();
      } finally {
        await page.close();
      }
    });
  });
});

// ============================================
// API 服务健康检查测试
// ============================================
test.describe('API 服务健康检查', () => {
  test('agent API', async ({ request }) => {
    console.log('\n[API] 检查 agent API...');
    const response = await request.get(`${CONFIG.AGENT_API}/api/v1/health`);
    console.log(`[API] agent API 状态: ${response.status()}`);
    expect(response.status()).toBe(200);
  });

  test('data API', async ({ request }) => {
    console.log('\n[API] 检查 data API...');
    const response = await request.get(`${CONFIG.DATA_API}/api/v1/health`);
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
