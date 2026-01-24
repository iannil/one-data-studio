/**
 * 工作流功能 E2E 测试
 * Sprint 9: E2E 测试扩展
 *
 * 使用 Playwright 测试工作流功能的关键场景
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8081';

test.describe('Workflow List', () => {
  test.beforeEach(async ({ page }) => {
    // 设置 mock 响应
    await page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, message: 'healthy' }),
      });
    });

    await page.route('**/api/v1/workflows', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            workflows: [
              {
                workflow_id: 'wf-1',
                name: 'RAG 工作流',
                type: 'rag',
                status: 'stopped',
                created_at: '2024-01-01T00:00:00Z',
              },
              {
                workflow_id: 'wf-2',
                name: 'Agent 工作流',
                type: 'agent',
                status: 'running',
                created_at: '2024-01-02T00:00:00Z',
              },
            ],
          },
        }),
      });
    });
  });

  test('should display workflow list', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);

    // 验证工作流列表显示
    await expect(page.locator('text=RAG 工作流')).toBeVisible();
    await expect(page.locator('text=Agent 工作流')).toBeVisible();
  });

  test('should show workflow status badges', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);

    // 验证状态标签
    await expect(page.locator('[data-status="stopped"]')).toBeVisible();
    await expect(page.locator('[data-status="running"]')).toBeVisible();
  });

  test('should open workflow editor', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);

    // 点击工作流卡片
    await page.click('[data-workflow-id="wf-1"]');

    // 验证跳转到编辑器
    await page.waitForURL('**/workflows/wf-1/edit');
    await expect(page.locator('[data-testid="workflow-editor"]')).toBeVisible();
  });
});

test.describe('Workflow Editor', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/workflows/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            workflow_id: 'wf-1',
            name: '测试工作流',
            type: 'rag',
            definition: {
              version: '1.0',
              nodes: [
                { id: 'input-1', type: 'input', position: { x: 100, y: 100 } },
                { id: 'retriever-1', type: 'retriever', position: { x: 300, y: 100 } },
                { id: 'llm-1', type: 'llm', position: { x: 500, y: 100 } },
                { id: 'output-1', type: 'output', position: { x: 700, y: 100 } },
              ],
              edges: [
                { source: 'input-1', target: 'retriever-1' },
                { source: 'retriever-1', target: 'llm-1' },
                { source: 'llm-1', target: 'output-1' },
              ],
            },
          },
        }),
      });
    });
  });

  test('should display workflow canvas', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 验证画布显示
    await expect(page.locator('[data-testid="flow-canvas"]')).toBeVisible();
  });

  test('should display node palette', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 验证节点面板显示
    await expect(page.locator('[data-testid="node-palette"]')).toBeVisible();

    // 验证常用节点类型
    await expect(page.locator('text=输入')).toBeVisible();
    await expect(page.locator('text=LLM')).toBeVisible();
    await expect(page.locator('text=检索器')).toBeVisible();
    await expect(page.locator('text=输出')).toBeVisible();
  });

  test('should drag and drop node to canvas', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 拖拽节点到画布
    const paletteNode = page.locator('[data-node-type="llm"]').first();
    const canvas = page.locator('[data-testid="flow-canvas"]');

    await paletteNode.dragTo(canvas);

    // 验证节点添加成功
    await expect(page.locator('[data-node-type="llm"]').last()).toBeVisible();
  });

  test('should select node and show config panel', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 选择现有节点
    await page.click('[data-node-id="llm-1"]');

    // 验证配置面板显示
    await expect(page.locator('[data-testid="node-config-panel"]')).toBeVisible();
    await expect(page.locator('label=模型')).toBeVisible();
  });

  test('should update node configuration', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 选择 LLM 节点
    await page.click('[data-node-id="llm-1"]');

    // 修改模型选择
    await page.selectOption('select[name="model"]', 'gpt-4o');

    // 修改温度参数
    await page.fill('input[name="temperature"]', '0.8');

    // 保存配置
    await page.click('[data-testid="save-config-button"]');

    // 验证保存成功提示
    await expect(page.locator('text=配置已保存')).toBeVisible();
  });

  test('should connect two nodes', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 拖拽创建连接
    const sourceNode = page.locator('[data-node-id="input-1"]');
    const targetNode = page.locator('[data-node-id="retriever-1"]');

    // 模拟连接操作
    await sourceNode.dragTo(targetNode);

    // 验证连接创建
    await expect(page.locator('[data-edge-source="input-1"][data-edge-target="retriever-1"]')).toBeVisible();
  });

  test('should delete node', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 选择节点
    await page.click('[data-node-id="llm-1"]');

    // 按删除键
    await page.keyboard.press('Delete');

    // 验证删除确认对话框
    await expect(page.locator('text=确认删除此节点')).toBeVisible();

    // 确认删除
    await page.click('button:has-text("确认")');

    // 验证节点已删除
    await expect(page.locator('[data-node-id="llm-1"]')).not.toBeVisible();
  });
});

test.describe('Workflow Execution', () => {
  test('should start workflow execution', async ({ page }) => {
    await page.route('**/api/v1/workflows/**/start', async (route) => {
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'Workflow started',
          data: {
            execution_id: 'exec-123',
            status: 'running',
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 点击执行按钮
    await page.click('[data-testid="execute-workflow-button"]');

    // 验证执行状态
    await expect(page.locator('text=正在执行')).toBeVisible();
  });

  test('should display execution logs', async ({ page }) => {
    await page.route('**/api/v1/executions/**/logs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            logs: [
              {
                node_id: 'input-1',
                timestamp: '2024-01-01T00:00:00Z',
                message: '输入处理完成',
                status: 'success',
              },
              {
                node_id: 'retriever-1',
                timestamp: '2024-01-01T00:00:01Z',
                message: '检索到 5 条相关文档',
                status: 'success',
              },
            ],
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/workflows/wf-1/executions/exec-123');

    // 验证日志显示
    await expect(page.locator('text=输入处理完成')).toBeVisible();
    await expect(page.locator('text=检索到 5 条相关文档')).toBeVisible();
  });

  test('should stop workflow execution', async ({ page }) => {
    await page.route('**/api/v1/workflows/**/stop', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'Workflow stopped',
        }),
      });
    });

    await page.goto(`${BASE_URL}/workflows/wf-1/edit');

    // 假设工作流正在执行
    await page.click('[data-testid="stop-workflow-button"]');

    // 验证停止成功
    await expect(page.locator('text=已停止')).toBeVisible();
  });
});

test.describe('Workflow CRUD', () => {
  test('should create new workflow', async ({ page }) => {
    await page.route('**/api/v1/workflows', async (route) => {
      const request = route.request();
      if (request.method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: 'success',
            data: { workflow_id: 'wf-new' },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: 'success',
            data: { workflows: [] },
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/workflows`);

    // 点击创建按钮
    await page.click('[data-testid="create-workflow-button"]');

    // 填写表单
    await page.fill('input[name="name"]', '新工作流');
    await page.selectOption('select[name="type"]', 'rag');
    await page.fill('textarea[name="description"]', '这是一个测试工作流');

    // 提交
    await page.click('button[type="submit"]');

    // 验证创建成功
    await expect(page.locator('text=工作流创建成功')).toBeVisible();
  });

  test('should update workflow', async ({ page }) => {
    await page.route('**/api/v1/workflows/**', async (route) => {
      const request = route.request();
      if (request.method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: 'success',
            data: { workflow_id: 'wf-1', name: '更新后的工作流' },
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/workflows/wf-1/edit`);

    // 点击编辑
    await page.click('[data-testid="edit-workflow-button"]');

    // 修改名称
    await page.fill('input[name="name"]', '更新后的工作流');

    // 保存
    await page.click('[data-testid="save-workflow-button"]');

    // 验证保存成功
    await expect(page.locator('text=保存成功')).toBeVisible();
  });

  test('should delete workflow', async ({ page }) => {
    await page.route('**/api/v1/workflows/**', async (route) => {
      const request = route.request();
      if (request.method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            message: 'success',
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/workflows`);

    // 点击删除按钮
    await page.click('[data-workflow-id="wf-1"] [data-testid="delete-button"]');

    // 确认删除
    await page.click('button:has-text("确认")');

    // 验证删除成功
    await expect(page.locator('text=工作流已删除')).toBeVisible();
  });
});
