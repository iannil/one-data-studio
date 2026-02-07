/**
 * AI 开发者角色 E2E 测试
 * 测试用例编号: AD-WF-E-001 ~ AD-AG-E-005
 *
 * AI 开发者功能测试：
 * - 工作流创建和编辑
 * - Prompt 模板管理
 * - 知识库管理
 * - Agent 应用发布
 */

import { test, expect } from '@playwright/test';

// ==================== 常量定义 ====================

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ==================== 测试套件 ====================

test.describe('AI Developer - Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // 设置 AI 开发者权限 Mock
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            permissions: ['workflow:*', 'prompt:*', 'knowledge:*', 'agent:*']
          }
        })
      });
    });
  });

  test('AD-WF-E-001: Create RAG workflow', async ({ page }) => {
    /** 测试场景：创建 RAG 类型工作流
     *
     * 前置条件：
     * - 用户为 AI 开发者角色
     *
     * 测试步骤：
     * 1. 导航到工作流页面
     * 2. 点击"新建工作流"
     * 3. 选择 RAG 类型
     * 4. 添加节点（输入、检索、LLM、输出）
     * 5. 连接节点
     * 6. 保存工作流
     *
     * 预期结果：
     * - 工作流创建成功
     * - 显示在列表中
     */

    // Mock 创建工作流 API
    await page.route('**/api/v1/agent/workflows', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              workflow_id: 'wf_rag_001',
              name: '知识库问答工作流',
              type: 'rag',
              status: 'stopped',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { workflows: [], total: 0 }
          })
        });
      }
    });

    // 导航到工作流页面
    await page.goto(`${BASE_URL}/workflows`);
    await expect(page.locator('body')).toBeVisible();

    // 点击新建工作流
    await page.click('[data-testid="create-workflow-button"]');

    // 填写工作流信息
    await page.fill('input[name="name"]', '知识库问答工作流');
    await page.selectOption('select[name="type"]', 'rag');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('AD-WF-E-002: Execute workflow', async ({ page }) => {
    /** 测试场景：执行工作流
     *
     * 前置条件：
     * - 工作流已创建
     *
     * 测试步骤：
     * 1. 在工作流列表找到工作流
     * 2. 点击"执行"按钮
     * 3. 输入执行参数
     * 4. 启动执行
     *
     * 预期结果：
     * - 工作流开始执行
     * - 显示执行状态
     */

    // Mock 工作流列表
    await page.route('**/api/v1/agent/workflows', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            workflows: [
              {
                workflow_id: 'wf_rag_001',
                name: '知识库问答工作流',
                type: 'rag',
                status: 'stopped'
              }
            ],
            total: 1
          }
        })
      });
    });

    // Mock 执行 API
    await page.route('**/api/v1/agent/workflows/*/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            execution_id: 'exec_001',
            status: 'running',
            started_at: new Date().toISOString()
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/workflows`);

    // 点击执行按钮
    await page.click('[data-testid="execute-button-wf_rag_001"]');

    // 输入参数
    await page.fill('textarea[name="input"]', '测试问题');

    // 启动执行
    await page.click('.ant-modal button:has-text("执行")');

    // 验证成功消息
    await expect(page.locator('.toast-message:has-text("执行已启动")')).toBeVisible();
  });
});

test.describe('AI Developer - Prompts', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['prompt:*'] }
        })
      });
    });
  });

  test('AD-PM-E-001: Create prompt template', async ({ page }) => {
    /** 测试场景：创建 Prompt 模板
     *
     * 测试步骤：
     * 1. 导航到 Prompt 管理页面
     * 2. 点击"新建模板"
     * 3. 填写模板信息
     * 4. 定义变量
     * 5. 保存模板
     *
     * 预期结果：
     * - 模板创建成功
     */

    // Mock API
    await page.route('**/api/v1/agent/prompts', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              template_id: 'tpl_001',
              name: '客服对话模板',
              category: 'chat',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { templates: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/agent-platform/prompts`);

    // 点击新建模板
    await page.click('[data-testid="create-prompt-button"]');

    // 填写模板信息
    await page.fill('input[name="name"]', '客服对话模板');
    await page.selectOption('select[name="category"]', 'chat');
    await page.fill('textarea[name="content"]', '你是一个专业的客服人员，请根据以下知识库内容回答：{{knowledge}}');

    // 添加变量
    await page.click('[data-testid="add-variable-button"]');
    await page.fill('input[name="variable_name"]', 'knowledge');
    await page.selectOption('select[name="variable_type"]', 'text');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });
});

test.describe('AI Developer - Knowledge Base', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['knowledge:*'] }
        })
      });
    });
  });

  test('AD-KB-E-001: Create knowledge base', async ({ page }) => {
    /** 测试场景：创建知识库
     *
     * 测试步骤：
     * 1. 导航到知识库页面
     * 2. 点击"新建知识库"
     * 3. 填写知识库信息
     * 4. 配置向量参数
     * 5. 保存
     *
     * 预期结果：
     * - 知识库创建成功
     */

    // Mock API
    await page.route('**/api/v1/agent/knowledge', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              kb_id: 'kb_001',
              name: '产品文档知识库',
              embedding_model: 'text-embedding-ada-002',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { knowledge_bases: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/agent-platform/knowledge`);

    // 点击新建知识库
    await page.click('[data-testid="create-kb-button"]');

    // 填写信息
    await page.fill('input[name="name"]', '产品文档知识库');
    await page.selectOption('select[name="embedding_model"]', 'text-embedding-ada-002');

    // 保存
    await page.click('button:has-text("保存")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("创建成功")')).toBeVisible();
  });

  test('AD-KB-E-002: Upload document to knowledge base', async ({ page }) => {
    /** 测试场景：上传文档到知识库
     *
     * 前置条件：
     * - 知识库已创建
     *
     * 测试步骤：
     * 1. 进入知识库详情
     * 2. 点击"上传文档"
     * 3. 选择文件
     * 4. 确认上传
     *
     * 预期结果：
     * - 文档上传成功
     * - 开始处理
     */

    // Mock 上传 API
    await page.route('**/api/v1/agent/knowledge/*/documents', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            document_id: 'doc_001',
            filename: 'product_manual.pdf',
            status: 'processing'
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/agent-platform/knowledge/kb_001`);

    // 点击上传文档
    await page.click('[data-testid="upload-document-button"]');

    // 模拟文件选择（实际测试中需要真实文件）
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'product_manual.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('mock pdf content')
    });

    // 确认上传
    await page.click('.ant-modal button:has-text("上传")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("上传成功")')).toBeVisible();
  });
});

test.describe('AI Developer - Agent Apps', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/permissions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: { permissions: ['agent:*'] }
        })
      });
    });
  });

  test('AD-AG-E-001: Publish agent app', async ({ page }) => {
    /** 测试场景：发布 Agent 应用
     *
     * 前置条件：
     * - 工作流已创建并测试通过
     *
     * 测试步骤：
     * 1. 在工作流详情页面点击"发布为应用"
     * 2. 填写应用信息
     * 3. 配置 API 设置
     * 4. 发布
     *
     * 预期结果：
     * - 应用发布成功
     * - 生成 API 端点和密钥
     */

    // Mock 发布 API
    await page.route('**/api/v1/agent/apps', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              app_id: 'app_001',
              name: '智能客服助手',
              api_endpoint: '/api/v1/agent/apps/app_001',
              api_key: 'sk_test_xxxxx',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { apps: [], total: 0 }
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/workflows/wf_rag_001`);

    // 点击发布为应用
    await page.click('[data-testid="publish-app-button"]');

    // 填写应用信息
    await page.fill('input[name="app_name"]', '智能客服助手');
    await page.fill('textarea[name="description"]', '基于知识库的智能客服');

    // 配置 API
    await page.check('[data-testid="enable-api"]');

    // 发布
    await page.click('button:has-text("发布")');

    // 验证成功
    await expect(page.locator('.toast-message:has-text("发布成功")')).toBeVisible();

    // 验证 API 信息显示
    await expect(page.locator('text=/api/v1/agent/apps/app_001')).toBeVisible();
  });

  test('AD-AG-E-002: View agent app statistics', async ({ page }) => {
    /** 测试场景：查看 Agent 应用统计
     *
     * 前置条件：
     * - 应用已发布
     *
     * 测试步骤：
     * 1. 导航到应用管理页面
     * 2. 点击应用查看详情
     * 3. 查看统计数据
     *
     * 预期结果：
     * - 显示调用次数、成功率等统计
     */

    // Mock 应用列表和统计
    await page.route('**/api/v1/agent/apps', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            apps: [
              {
                app_id: 'app_001',
                name: '智能客服助手',
                total_executions: 1000,
                successful_executions: 950,
                avg_duration_ms: 1200
              }
            ],
            total: 1
          }
        })
      });
    });

    await page.goto(`${BASE_URL}/agent-platform/apps`);

    // 验证应用显示
    await expect(page.locator('text=智能客服助手')).toBeVisible();
    await expect(page.locator('text=1000')).toBeVisible();
  });
});
