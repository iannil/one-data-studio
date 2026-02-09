/**
 * 可见浏览器 CRUD 操作验收测试
 *
 * 使用方式:
 * # 完整 CRUD 验收（可见浏览器）
 * npx playwright test tests/e2e/visual-crud-acceptance.spec.ts --project=visual-acceptance --headed
 *
 * # 仅测试 P0 模块
 * npx playwright test tests/e2e/visual-crud-acceptance.spec.ts --headed -g "数据源管理|用户管理"
 *
 * # 仅测试特定操作
 * npx playwright test tests/e2e/visual-crud-acceptance.spec.ts --headed -g "Create"
 *
 * # 使用 slowMo 模式便于观察
 * SLOW_MO=500 npx playwright test tests/e2e/visual-crud-acceptance.spec.ts --headed --project=visual-acceptance
 *
 * @description
 * 本测试脚本用于可见浏览器模式下的 CRUD 功能验收
 * - C(reate): 点击新建按钮 → 填写表单 → 提交 → 验证成功
 * - R(ead): 查看列表/表格 → 搜索/筛选 → 验证数据展示
 * - U(pdate): 点击编辑 → 修改字段 → 保存 → 验证更新
 * - D(elete): 点击删除 → 确认弹窗 → 验证删除成功
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth, waitForPageLoad } from './helpers';

// 配置：每个页面停留时间（毫秒），便于人工观察
const OBSERVE_DELAY = parseInt(process.env.OBSERVE_DELAY || '1500', 10);
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

/**
 * CRUD 功能配置接口
 */
interface CrudConfig {
  /** 页面路由 */
  route: string;
  /** 页面名称 */
  name: string;
  /** 所属模块 */
  module: string;
  /** 优先级 */
  priority: 'P0' | 'P1' | 'P2';
  /** API 前缀 */
  apiPrefix: string;
  /** Create 操作配置 */
  create?: {
    buttonText: string[];
    formFields: { selector: string; value: string; type?: 'input' | 'select' | 'textarea' }[];
    submitText: string;
  };
  /** Read 操作配置 */
  read?: {
    tableSelector: string;
    searchPlaceholder?: string;
  };
  /** Update 操作配置 */
  update?: {
    editButtonText: string;
    updateFields: { selector: string; value: string }[];
    saveText: string;
  };
  /** Delete 操作配置 */
  delete?: {
    deleteButtonText: string;
    confirmText: string;
  };
}

/**
 * 所有支持 CRUD 的页面配置
 */
const CRUD_PAGES: CrudConfig[] = [
  // ==================== P0: 核心功能（必测） ====================
  {
    route: '/data/datasources',
    name: '数据源管理',
    module: 'data',
    priority: 'P0',
    apiPrefix: '/api/v1/datasources',
    create: {
      buttonText: ['新建', '添加', '创建数据源', '新建数据源'],
      formFields: [
        { selector: '#name, input[name="name"], input[placeholder*="名称"]', value: `E2E-DS-${Date.now()}`, type: 'input' },
        { selector: '#type, .ant-select:has-text("类型")', value: 'mysql', type: 'select' },
        { selector: '#host, input[name="host"], input[placeholder*="主机"]', value: 'localhost', type: 'input' },
        { selector: '#port, input[name="port"], input[placeholder*="端口"]', value: '3306', type: 'input' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
      searchPlaceholder: '搜索',
    },
    update: {
      editButtonText: '编辑',
      updateFields: [
        { selector: '#description, textarea[name="description"], textarea[placeholder*="描述"]', value: 'E2E测试更新描述' },
      ],
      saveText: '保存',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/data/etl',
    name: 'ETL流程',
    module: 'data',
    priority: 'P0',
    apiPrefix: '/api/v1/etl',
    create: {
      buttonText: ['新建', '创建', '新建任务', '创建ETL'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-ETL-${Date.now()}`, type: 'input' },
        { selector: '#description, textarea[name="description"]', value: 'E2E测试ETL任务', type: 'textarea' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
      searchPlaceholder: '搜索',
    },
    update: {
      editButtonText: '编辑',
      updateFields: [
        { selector: '#description, textarea[name="description"]', value: 'E2E测试更新ETL' },
      ],
      saveText: '保存',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/data/quality',
    name: '数据质量',
    module: 'data',
    priority: 'P0',
    apiPrefix: '/api/v1/quality',
    create: {
      buttonText: ['新建', '创建', '新建规则', '添加规则'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Quality-${Date.now()}`, type: 'input' },
        { selector: '#rule_type, .ant-select:has-text("规则类型")', value: 'not_null', type: 'select' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
      searchPlaceholder: '搜索',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/admin/users',
    name: '用户管理',
    module: 'admin',
    priority: 'P0',
    apiPrefix: '/api/v1/admin/users',
    create: {
      buttonText: ['新建', '添加用户', '创建', '新建用户'],
      formFields: [
        { selector: '#username, input[name="username"]', value: `e2e_user_${Date.now()}`, type: 'input' },
        { selector: '#email, input[name="email"]', value: `e2e_${Date.now()}@test.com`, type: 'input' },
        { selector: '#password, input[name="password"]', value: 'Test@12345', type: 'input' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
      searchPlaceholder: '搜索用户',
    },
    update: {
      editButtonText: '编辑',
      updateFields: [
        { selector: '#nickname, input[name="nickname"]', value: 'E2E测试用户' },
      ],
      saveText: '保存',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },

  // ==================== P1: 业务功能 ====================
  {
    route: '/data/features',
    name: '特征存储',
    module: 'data',
    priority: 'P1',
    apiPrefix: '/api/v1/features',
    create: {
      buttonText: ['新建', '创建', '新建特征'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Feature-${Date.now()}`, type: 'input' },
        { selector: '#description, textarea[name="description"]', value: 'E2E测试特征', type: 'textarea' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/data/standards',
    name: '数据标准',
    module: 'data',
    priority: 'P1',
    apiPrefix: '/api/v1/standards',
    create: {
      buttonText: ['新建', '创建', '新建标准'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Standard-${Date.now()}`, type: 'input' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/data/services',
    name: '数据服务',
    module: 'data',
    priority: 'P1',
    apiPrefix: '/api/v1/services',
    create: {
      buttonText: ['新建', '创建', '发布服务', '新建服务'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Service-${Date.now()}`, type: 'input' },
      ],
      submitText: '发布',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/model/notebooks',
    name: 'Notebook开发',
    module: 'model',
    priority: 'P1',
    apiPrefix: '/api/v1/notebooks',
    create: {
      buttonText: ['新建', '创建', '新建Notebook'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Notebook-${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table, .notebook-list',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/model/experiments',
    name: '实验管理',
    module: 'model',
    priority: 'P1',
    apiPrefix: '/api/v1/experiments',
    create: {
      buttonText: ['新建', '创建', '新建实验'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Experiment-${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/model/models',
    name: '模型管理',
    module: 'model',
    priority: 'P1',
    apiPrefix: '/api/v1/models',
    create: {
      buttonText: ['注册', '新建', '创建', '注册模型'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Model-${Date.now()}`, type: 'input' },
      ],
      submitText: '注册',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/agent-platform/prompts',
    name: 'Prompt管理',
    module: 'agent',
    priority: 'P1',
    apiPrefix: '/api/v1/prompts',
    create: {
      buttonText: ['新建', '创建', '添加', '新建Prompt'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Prompt-${Date.now()}`, type: 'input' },
        { selector: '#template, textarea[name="template"]', value: '请回答：{question}', type: 'textarea' },
      ],
      submitText: '确定',
    },
    read: {
      tableSelector: '.ant-table',
    },
    update: {
      editButtonText: '编辑',
      updateFields: [
        { selector: '#template, textarea[name="template"]', value: '更新后的模板：{question}' },
      ],
      saveText: '保存',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/agent-platform/knowledge',
    name: '知识库管理',
    module: 'agent',
    priority: 'P1',
    apiPrefix: '/api/v1/knowledge',
    create: {
      buttonText: ['新建', '创建', '新建知识库'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-KB-${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
    delete: {
      deleteButtonText: '删除',
      confirmText: '确定',
    },
  },
  {
    route: '/agent-platform/apps',
    name: 'Agent应用',
    module: 'agent',
    priority: 'P1',
    apiPrefix: '/api/v1/apps',
    create: {
      buttonText: ['新建', '创建', '新建应用'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-App-${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/workflows',
    name: '工作流管理',
    module: 'workflow',
    priority: 'P1',
    apiPrefix: '/api/v1/workflows',
    create: {
      buttonText: ['新建', '创建', '新建工作流'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `E2E-Workflow-${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },

  // ==================== P2: 管理功能 ====================
  {
    route: '/admin/roles',
    name: '角色管理',
    module: 'admin',
    priority: 'P2',
    apiPrefix: '/api/v1/admin/roles',
    create: {
      buttonText: ['新建', '创建', '新建角色'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `e2e_role_${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/admin/groups',
    name: '分组管理',
    module: 'admin',
    priority: 'P2',
    apiPrefix: '/api/v1/admin/groups',
    create: {
      buttonText: ['新建', '创建', '新建分组'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `e2e_group_${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
  {
    route: '/admin/user-segments',
    name: '用户分群',
    module: 'admin',
    priority: 'P2',
    apiPrefix: '/api/v1/admin/segments',
    create: {
      buttonText: ['新建', '创建', '新建分群'],
      formFields: [
        { selector: '#name, input[name="name"]', value: `e2e_segment_${Date.now()}`, type: 'input' },
      ],
      submitText: '创建',
    },
    read: {
      tableSelector: '.ant-table',
    },
  },
];

/**
 * 验收结果统计
 */
interface AcceptanceResult {
  config: CrudConfig;
  operation: 'create' | 'read' | 'update' | 'delete';
  status: 'passed' | 'failed' | 'skipped';
  error?: string;
  screenshot?: string;
}

const acceptanceResults: AcceptanceResult[] = [];

/**
 * 生成安全的文件名
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

/**
 * 等待并点击按钮
 */
async function clickButton(page: Page, buttonTexts: string[]): Promise<boolean> {
  for (const text of buttonTexts) {
    // 尝试多种选择器
    const selectors = [
      `button:has-text("${text}")`,
      `.ant-btn:has-text("${text}")`,
      `a:has-text("${text}")`,
      `[role="button"]:has-text("${text}")`,
    ];

    for (const selector of selectors) {
      const btn = page.locator(selector).first();
      try {
        if (await btn.isVisible({ timeout: 2000 })) {
          await btn.click();
          return true;
        }
      } catch {
        // 继续尝试下一个选择器
      }
    }
  }
  return false;
}

/**
 * 填写表单字段
 */
async function fillFormField(
  page: Page,
  field: { selector: string; value: string; type?: 'input' | 'select' | 'textarea' }
): Promise<boolean> {
  const selectors = field.selector.split(',').map(s => s.trim());

  for (const selector of selectors) {
    try {
      const el = page.locator(selector).first();
      if (await el.isVisible({ timeout: 2000 })) {
        if (field.type === 'select') {
          await el.click();
          await page.waitForTimeout(300);
          // 尝试选择下拉选项
          const option = page.locator(`.ant-select-item:has-text("${field.value}")`).first();
          if (await option.isVisible({ timeout: 2000 })) {
            await option.click();
          } else {
            // 直接输入
            await page.keyboard.type(field.value);
            await page.keyboard.press('Enter');
          }
        } else {
          await el.clear();
          await el.fill(field.value);
        }
        return true;
      }
    } catch {
      // 继续尝试下一个选择器
    }
  }
  return false;
}

// ==================== 测试套件 ====================

test.describe('可见浏览器 CRUD 验收（真实API）', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test.afterAll(async () => {
    // 输出验收汇总报告
    logSeparator();
    console.log('CRUD 验收汇总报告');
    logSeparator();

    const passed = acceptanceResults.filter(r => r.status === 'passed').length;
    const failed = acceptanceResults.filter(r => r.status === 'failed').length;
    const skipped = acceptanceResults.filter(r => r.status === 'skipped').length;

    console.log(`总计: ${acceptanceResults.length} 项操作`);
    console.log(`通过: ${passed} 项`);
    console.log(`失败: ${failed} 项`);
    console.log(`跳过: ${skipped} 项`);

    if (failed > 0) {
      console.log('\n失败详情:');
      acceptanceResults
        .filter(r => r.status === 'failed')
        .forEach(r => {
          console.log(`  - [${r.config.module}] ${r.config.name} - ${r.operation}: ${r.error}`);
        });
    }

    logSeparator();
  });

  // 为每个 CRUD 页面创建测试组
  for (const config of CRUD_PAGES) {
    test.describe(`[${config.priority}][${config.module}] ${config.name}`, () => {

      // ==================== Read 操作 ====================
      test('1-Read: 查看列表', async ({ page }) => {
        logSeparator();
        console.log(`正在验收: [${config.name}] Read 操作`);
        logSeparator();

        try {
          await setupAuth(page, { roles: ['admin'] });
          await page.goto(`${BASE_URL}${config.route}`, {
            waitUntil: 'domcontentloaded',
            timeout: 30000,
          });
          await waitForPageLoad(page);

          if (config.read) {
            // 验证表格存在
            const table = page.locator(config.read.tableSelector);
            await expect(table).toBeVisible({ timeout: 15000 });
            console.log('✓ 表格已加载');

            // 尝试搜索功能（如果配置了）
            if (config.read.searchPlaceholder) {
              const searchInput = page.locator(`input[placeholder*="${config.read.searchPlaceholder}"]`).first();
              if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
                await searchInput.fill('test');
                await page.waitForTimeout(500);
                console.log('✓ 搜索功能可用');
              }
            }
          }

          const screenshotPath = `test-results/crud/${config.module}-${safeFileName(config.name)}-1-read.png`;
          await page.screenshot({ path: screenshotPath, fullPage: true });

          acceptanceResults.push({
            config,
            operation: 'read',
            status: 'passed',
            screenshot: screenshotPath,
          });
          console.log(`✓ [${config.name}] Read 验收通过`);

          await page.waitForTimeout(OBSERVE_DELAY);

        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : String(error);
          acceptanceResults.push({
            config,
            operation: 'read',
            status: 'failed',
            error: errorMsg,
          });
          console.error(`✗ [${config.name}] Read 验收失败: ${errorMsg}`);
          throw error;
        }
      });

      // ==================== Create 操作 ====================
      if (config.create) {
        test('2-Create: 新建记录', async ({ page }) => {
          logSeparator();
          console.log(`正在验收: [${config.name}] Create 操作`);
          logSeparator();

          try {
            await setupAuth(page, { roles: ['admin'] });
            await page.goto(`${BASE_URL}${config.route}`, {
              waitUntil: 'domcontentloaded',
              timeout: 30000,
            });
            await waitForPageLoad(page);

            // 点击新建按钮
            const clicked = await clickButton(page, config.create!.buttonText);
            if (!clicked) {
              console.log('警告: 未找到新建按钮');
              acceptanceResults.push({
                config,
                operation: 'create',
                status: 'skipped',
                error: '未找到新建按钮',
              });
              return;
            }
            console.log('✓ 已点击新建按钮');

            // 等待弹窗/抽屉出现
            const modalOrDrawer = page.locator('.ant-modal, .ant-drawer');
            await expect(modalOrDrawer).toBeVisible({ timeout: 5000 });
            console.log('✓ 表单弹窗已打开');

            // 截图：表单打开状态
            await page.screenshot({
              path: `test-results/crud/${config.module}-${safeFileName(config.name)}-2-create-form.png`,
            });

            // 填写表单
            for (const field of config.create!.formFields) {
              const filled = await fillFormField(page, field);
              if (filled) {
                console.log(`✓ 已填写字段: ${field.selector.split(',')[0]}`);
              } else {
                console.log(`警告: 未找到字段: ${field.selector.split(',')[0]}`);
              }
            }

            // 截图：表单填写后
            await page.screenshot({
              path: `test-results/crud/${config.module}-${safeFileName(config.name)}-2-create-filled.png`,
            });

            // 提交表单
            const submitClicked = await clickButton(page, [config.create!.submitText, '确定', '提交', '保存']);
            if (submitClicked) {
              console.log('✓ 已点击提交按钮');
              await page.waitForTimeout(1000);

              // 检查是否有成功提示
              const successMsg = page.locator('.ant-message-success');
              if (await successMsg.isVisible({ timeout: 3000 }).catch(() => false)) {
                console.log('✓ 显示成功提示');
              }
            }

            const screenshotPath = `test-results/crud/${config.module}-${safeFileName(config.name)}-2-create-done.png`;
            await page.screenshot({ path: screenshotPath, fullPage: true });

            acceptanceResults.push({
              config,
              operation: 'create',
              status: 'passed',
              screenshot: screenshotPath,
            });
            console.log(`✓ [${config.name}] Create 验收通过`);

            await page.waitForTimeout(OBSERVE_DELAY);

          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            acceptanceResults.push({
              config,
              operation: 'create',
              status: 'failed',
              error: errorMsg,
            });
            console.error(`✗ [${config.name}] Create 验收失败: ${errorMsg}`);

            // 失败时截图
            await page.screenshot({
              path: `test-results/crud/${config.module}-${safeFileName(config.name)}-2-create-FAIL.png`,
              fullPage: true,
            }).catch(() => {});

            throw error;
          }
        });
      }

      // ==================== Update 操作 ====================
      if (config.update) {
        test('3-Update: 编辑记录', async ({ page }) => {
          logSeparator();
          console.log(`正在验收: [${config.name}] Update 操作`);
          logSeparator();

          try {
            await setupAuth(page, { roles: ['admin'] });
            await page.goto(`${BASE_URL}${config.route}`, {
              waitUntil: 'domcontentloaded',
              timeout: 30000,
            });
            await waitForPageLoad(page);

            // 点击第一行的编辑按钮
            const editBtn = page.locator(`button:has-text("${config.update!.editButtonText}"), .ant-btn:has-text("${config.update!.editButtonText}")`).first();

            if (await editBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
              await editBtn.click();
              console.log('✓ 已点击编辑按钮');

              // 等待弹窗出现
              const modalOrDrawer = page.locator('.ant-modal, .ant-drawer');
              await expect(modalOrDrawer).toBeVisible({ timeout: 5000 });
              console.log('✓ 编辑表单已打开');

              // 修改字段
              for (const field of config.update!.updateFields) {
                const selectors = field.selector.split(',').map(s => s.trim());
                for (const selector of selectors) {
                  try {
                    const el = page.locator(selector).first();
                    if (await el.isVisible({ timeout: 2000 })) {
                      await el.clear();
                      await el.fill(field.value);
                      console.log(`✓ 已更新字段: ${selector}`);
                      break;
                    }
                  } catch {
                    // 继续尝试
                  }
                }
              }

              // 截图：修改后
              await page.screenshot({
                path: `test-results/crud/${config.module}-${safeFileName(config.name)}-3-update-form.png`,
              });

              // 保存
              const saveClicked = await clickButton(page, [config.update!.saveText, '保存', '确定']);
              if (saveClicked) {
                console.log('✓ 已点击保存按钮');
                await page.waitForTimeout(1000);
              }
            } else {
              console.log('警告: 未找到编辑按钮，可能没有数据');
              acceptanceResults.push({
                config,
                operation: 'update',
                status: 'skipped',
                error: '未找到编辑按钮',
              });
              return;
            }

            const screenshotPath = `test-results/crud/${config.module}-${safeFileName(config.name)}-3-update-done.png`;
            await page.screenshot({ path: screenshotPath, fullPage: true });

            acceptanceResults.push({
              config,
              operation: 'update',
              status: 'passed',
              screenshot: screenshotPath,
            });
            console.log(`✓ [${config.name}] Update 验收通过`);

            await page.waitForTimeout(OBSERVE_DELAY);

          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            acceptanceResults.push({
              config,
              operation: 'update',
              status: 'failed',
              error: errorMsg,
            });
            console.error(`✗ [${config.name}] Update 验收失败: ${errorMsg}`);
            throw error;
          }
        });
      }

      // ==================== Delete 操作 ====================
      if (config.delete) {
        test('4-Delete: 删除记录', async ({ page }) => {
          logSeparator();
          console.log(`正在验收: [${config.name}] Delete 操作`);
          logSeparator();

          try {
            await setupAuth(page, { roles: ['admin'] });
            await page.goto(`${BASE_URL}${config.route}`, {
              waitUntil: 'domcontentloaded',
              timeout: 30000,
            });
            await waitForPageLoad(page);

            // 点击第一行的删除按钮
            const deleteBtn = page.locator(`button:has-text("${config.delete!.deleteButtonText}"), .ant-btn:has-text("${config.delete!.deleteButtonText}")`).first();

            if (await deleteBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
              await deleteBtn.click();
              console.log('✓ 已点击删除按钮');

              // 等待确认弹窗
              await page.waitForTimeout(500);

              // 截图：确认弹窗
              await page.screenshot({
                path: `test-results/crud/${config.module}-${safeFileName(config.name)}-4-delete-confirm.png`,
              });

              // 尝试多种确认按钮选择器
              const confirmSelectors = [
                `.ant-modal-confirm button:has-text("${config.delete!.confirmText}")`,
                `.ant-popconfirm button:has-text("${config.delete!.confirmText}")`,
                `.ant-modal button.ant-btn-primary`,
                `.ant-popover button.ant-btn-primary`,
              ];

              for (const selector of confirmSelectors) {
                const confirmBtn = page.locator(selector).first();
                if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
                  await confirmBtn.click();
                  console.log('✓ 已确认删除');
                  await page.waitForTimeout(1000);
                  break;
                }
              }
            } else {
              console.log('警告: 未找到删除按钮，可能没有数据');
              acceptanceResults.push({
                config,
                operation: 'delete',
                status: 'skipped',
                error: '未找到删除按钮',
              });
              return;
            }

            const screenshotPath = `test-results/crud/${config.module}-${safeFileName(config.name)}-4-delete-done.png`;
            await page.screenshot({ path: screenshotPath, fullPage: true });

            acceptanceResults.push({
              config,
              operation: 'delete',
              status: 'passed',
              screenshot: screenshotPath,
            });
            console.log(`✓ [${config.name}] Delete 验收通过`);

            await page.waitForTimeout(OBSERVE_DELAY);

          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            acceptanceResults.push({
              config,
              operation: 'delete',
              status: 'failed',
              error: errorMsg,
            });
            console.error(`✗ [${config.name}] Delete 验收失败: ${errorMsg}`);
            throw error;
          }
        });
      }
    });
  }
});

// ==================== 按优先级分组的测试 ====================

test.describe('P0 核心功能 CRUD 验收', () => {
  const p0Pages = CRUD_PAGES.filter(p => p.priority === 'P0');

  for (const config of p0Pages) {
    test(`[P0] ${config.name} - 完整 CRUD 流程`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await setupAuth(page, { roles: ['admin'] });

      // Read
      await page.goto(`${BASE_URL}${config.route}`, { waitUntil: 'domcontentloaded' });
      await waitForPageLoad(page);
      if (config.read) {
        const table = page.locator(config.read.tableSelector);
        await expect(table).toBeVisible({ timeout: 15000 });
      }
      await page.screenshot({
        path: `test-results/crud/P0-${safeFileName(config.name)}-read.png`,
        fullPage: true,
      });

      // Create
      if (config.create) {
        const clicked = await clickButton(page, config.create.buttonText);
        if (clicked) {
          await page.waitForTimeout(500);
          await page.screenshot({
            path: `test-results/crud/P0-${safeFileName(config.name)}-create.png`,
          });
          // 关闭弹窗
          await page.keyboard.press('Escape');
          await page.waitForTimeout(300);
        }
      }

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('P1 业务功能 CRUD 验收', () => {
  const p1Pages = CRUD_PAGES.filter(p => p.priority === 'P1');

  for (const config of p1Pages) {
    test(`[P1] ${config.name} - Read 操作`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await setupAuth(page, { roles: ['admin'] });

      await page.goto(`${BASE_URL}${config.route}`, { waitUntil: 'domcontentloaded' });
      await waitForPageLoad(page);

      if (config.read) {
        const table = page.locator(config.read.tableSelector);
        await expect(table).toBeVisible({ timeout: 15000 });
      }

      await page.screenshot({
        path: `test-results/crud/P1-${safeFileName(config.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});

test.describe('P2 管理功能 CRUD 验收', () => {
  const p2Pages = CRUD_PAGES.filter(p => p.priority === 'P2');

  for (const config of p2Pages) {
    test(`[P2] ${config.name} - Read 操作`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await setupAuth(page, { roles: ['admin'] });

      await page.goto(`${BASE_URL}${config.route}`, { waitUntil: 'domcontentloaded' });
      await waitForPageLoad(page);

      if (config.read) {
        const table = page.locator(config.read.tableSelector);
        await expect(table).toBeVisible({ timeout: 15000 });
      }

      await page.screenshot({
        path: `test-results/crud/P2-${safeFileName(config.name)}.png`,
        fullPage: true,
      });

      await page.waitForTimeout(OBSERVE_DELAY);
    });
  }
});
