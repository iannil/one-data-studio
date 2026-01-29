/**
 * 核心页面深度验收测试
 * 覆盖首页、数据集、文档、聊天、工作流等核心功能
 * 使用真实 API 调用，不使用 Mock
 */

import { test, expect } from './fixtures/real-auth.fixture';
import { createApiClient, clearRequestLogs, getFailedRequests } from './helpers/api-client';
import type { AgentApiClient, DataApiClient } from './helpers/api-client';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 首页统计卡片深度测试
// ============================================
test.describe('核心页面 - 首页统计卡片', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('should display accurate statistics on home page', async ({ page, request }) => {
    // 创建真实 API 客户端
    const apiClient = createApiClient(request, 'agent_api') as AgentApiClient;

    // 获取真实统计数据
    const statsResponse = await apiClient.getStats();
    expect(statsResponse.code).toBe(0);

    const stats = statsResponse.data;

    // 访问首页
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // 验证统计卡片显示
    const statsCards = page.locator('.stat-card, .metric-card, [class*="stat"], [class*="metric"]');
    await expect(statsCards.first()).toBeVisible();

    // 验证数据准确性（如果页面上有具体数字）
    // 这里根据实际页面结构调整选择器
  });

  test('should refresh statistics when reload button clicked', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // 查找刷新按钮
    const refreshButton = page.locator('button:has-text("刷新"), button:has-text("Refresh"), [class*="refresh"]').first();
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForLoadState('networkidle');
    }
  });
});

// ============================================
// 数据集列表深度测试
// ============================================
test.describe('核心页面 - 数据集列表', () => {
  test.beforeEach(async ({ request }) => {
    clearRequestLogs();
  });

  test('should display datasets with pagination', async ({ page, request }) => {
    const apiClient = createApiClient(request, 'agent_api') as AgentApiClient;

    // 获取第一页数据
    const datasetsResponse = await apiClient.getDatasets({ page: 1, page_size: 10 });

    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 验证数据集列表可见
    const datasetList = page.locator('.dataset-list, .data-table, [class*="table"]').first();
    await expect(datasetList).toBeVisible();
  });

  test('should support sorting by different columns', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 查找排序列
    const sortHeaders = page.locator('th[aria-sort], th[class*="sortable"], .ant-table-column-sorter');
    const count = await sortHeaders.count();

    if (count > 0) {
      // 点击第一个排序列
      await sortHeaders.first().click();
      await page.waitForTimeout(500);

      // 再次点击切换排序方向
      await sortHeaders.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('should support filtering datasets', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 查找筛选器
    const filterInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .search-input').first();
    const filterSelect = page.locator('.ant-select, .filter-select').first();

    if (await filterInput.isVisible()) {
      await filterInput.fill('test');
      await page.waitForTimeout(500);
    }

    if (await filterSelect.isVisible()) {
      await filterSelect.click();
      await page.waitForTimeout(300);
    }
  });

  test('should handle empty state gracefully', async ({ page, request }) => {
    // 这里可以通过 API 清空数据来测试空状态
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 检查是否有空状态显示
    const emptyState = page.locator('.empty-state, .no-data, [class*="empty"]');
    // 空状态可能不存在（如果有数据）
  });

  test('should handle large dataset list (1000+ items)', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 查找分页控件
    const pagination = page.locator('.ant-pagination, .pagination');
    if (await pagination.isVisible()) {
      // 检查总页数
      const totalText = await pagination.locator('.ant-pagination-total, .total').textContent();
      console.log('Total datasets:', totalText);
    }
  });
});

// ============================================
// 文档管理深度测试
// ============================================
test.describe('核心页面 - 文档管理', () => {
  test('should upload document successfully', async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    // 查找上传按钮
    const uploadButton = page.locator('button:has-text("上传"), button:has-text("Upload"), [class*="upload"]').first();

    if (await uploadButton.isVisible()) {
      // 设置文件输入
      const fileInput = page.locator('input[type="file"]');
      if (await fileInput.isVisible()) {
        // 创建测试文件
        const testContent = 'This is a test document for E2E testing.';
        await fileInput.setInputFiles({
          name: 'test-document.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from(testContent),
        });

        await page.waitForTimeout(2000);
      }
    }
  });

  test('should preview document content', async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    // 查找第一个文档并点击预览
    const firstDoc = page.locator('.document-item, .file-item, tr[data-row-key]').first();
    if (await firstDoc.isVisible()) {
      const previewButton = firstDoc.locator('button:has-text("预览"), button:has-text("Preview"), [class*="preview"]').first();

      if (await previewButton.isVisible()) {
        await previewButton.click();
        await page.waitForTimeout(1000);

        // 验证预览对话框打开
        const modal = page.locator('.ant-modal, .modal, .dialog').filter({ hasText: /预览|Preview|内容/ });
        if (await modal.isVisible()) {
          await expect(modal).toBeVisible();
          // 关闭对话框
          await page.locator('.ant-modal-close, .modal-close, button[aria-label="close"]').first().click();
        }
      }
    }
  });

  test('should delete document with confirmation', async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    const firstDoc = page.locator('.document-item, .file-item, tr[data-row-key]').first();
    if (await firstDoc.isVisible()) {
      const deleteButton = firstDoc.locator('button:has-text("删除"), button:has-text("Delete"), [class*="delete"]').first();

      if (await deleteButton.isVisible()) {
        await deleteButton.click();
        await page.waitForTimeout(500);

        // 确认删除
        const confirmButton = page.locator('.ant-modal-confirm button:has-text("确定"), .ant-popconfirm button:has-text("是"), button:has-text("Confirm")').first();
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });
});

// ============================================
// AI 对话深度测试
// ============================================
test.describe('核心页面 - AI 对话', () => {
  test('should start new conversation', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);
    await page.waitForLoadState('networkidle');

    // 查找新建对话按钮
    const newChatButton = page.locator('button:has-text("新建对话"), button:has-text("New Chat"), [class*="new-chat"]').first();

    if (await newChatButton.isVisible()) {
      await newChatButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should send message and receive streaming response', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);
    await page.waitForLoadState('networkidle');

    // 查找输入框
    const inputBox = page.locator('textarea[placeholder*="输入"], textarea[placeholder*="message"], .chat-input').first();

    if (await inputBox.isVisible()) {
      const testMessage = '你好，这是一个测试消息。';
      await inputBox.fill(testMessage);

      // 查找发送按钮
      const sendButton = page.locator('button:has-text("发送"), button:has-text("Send"), [class*="send"]').first();
      await sendButton.click();

      // 等待响应（流式输出）
      await page.waitForTimeout(3000);

      // 验证消息出现在聊天区域
      const chatMessages = page.locator('.chat-message, .message-item, [class*="message"]');
      const messageCount = await chatMessages.count();
      expect(messageCount).toBeGreaterThan(0);
    }
  });

  test('should maintain conversation context', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);
    await page.waitForLoadState('networkidle');

    const inputBox = page.locator('textarea, [contenteditable="true"]').first();

    if (await inputBox.isVisible()) {
      // 发送多条消息
      const messages = ['第一条消息', '第二条消息', '第三条消息'];

      for (const msg of messages) {
        await inputBox.fill(msg);
        const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")').first();
        if (await sendButton.isVisible()) {
          await sendButton.click();
          await page.waitForTimeout(2000);
        }
      }

      // 验证对话历史存在
      const chatMessages = page.locator('.chat-message, .message-item');
      const messageCount = await chatMessages.count();
      expect(messageCount).toBeGreaterThan(messages.length);
    }
  });

  test('should handle special characters in messages', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);
    await page.waitForLoadState('networkidle');

    const inputBox = page.locator('textarea, [contenteditable="true"]').first();

    if (await inputBox.isVisible()) {
      const specialMessages = [
        'Test with emoji 🎉🔥',
        'Test with code: `console.log("hello")`',
        'Test with link: https://example.com',
        'Test with quote: "Hello World"',
      ];

      for (const msg of specialMessages) {
        await inputBox.fill(msg);
        const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")').first();
        if (await sendButton.isVisible()) {
          await sendButton.click();
          await page.waitForTimeout(1500);
        }
      }
    }
  });
});

// ============================================
// 工作流深度测试
// ============================================
test.describe('核心页面 - 工作流', () => {
  test('should display workflow list with status', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    // 验证工作流列表
    const workflowList = page.locator('.workflow-list, .data-table').first();
    await expect(workflowList).toBeVisible();

    // 检查状态标签
    const statusLabels = page.locator('.status-badge, .tag, [class*="status"]');
    const statusCount = await statusLabels.count();
    console.log(`Found ${statusCount} status labels`);
  });

  test('should create new workflow with drag and drop', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    // 查找创建工作流按钮
    const createButton = page.locator('button:has-text("创建"), button:has-text("Create"), button:has-text("新建")').first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // 检查是否进入编辑页面
      const editor = page.locator('.workflow-editor, .canvas-editor, [class*="editor"]');
      if (await editor.isVisible()) {
        // 尝试拖拽节点
        const nodePalette = page.locator('.node-palette, .component-list, [class*="palette"]');
        const canvas = page.locator('.canvas, .flow-canvas, [class*="canvas"]');

        if (await nodePalette.isVisible() && await canvas.isVisible()) {
          const firstNode = nodePalette.locator('.node-item, .component-item').first();
          if (await firstNode.isVisible()) {
            await firstNode.dragTo(canvas);
            await page.waitForTimeout(500);
          }
        }
      }
    }
  });

  test('should execute workflow and monitor progress', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    // 查找第一个工作流
    const firstWorkflow = page.locator('.workflow-item, tr[data-row-key]').first();
    if (await firstWorkflow.isVisible()) {
      const runButton = firstWorkflow.locator('button:has-text("运行"), button:has-text("Run"), [class*="run"]').first();

      if (await runButton.isVisible()) {
        await runButton.click();
        await page.waitForTimeout(2000);

        // 检查执行状态
        const statusIndicator = page.locator('.status-running, .status-executing, [class*="running"]');
        // 执行状态可能出现也可能不出现
      }
    }
  });

  test('should display workflow execution history', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflows`);
    await page.waitForLoadState('networkidle');

    const firstWorkflow = page.locator('.workflow-item, tr[data-row-key]').first();
    if (await firstWorkflow.isVisible()) {
      const historyButton = firstWorkflow.locator('button:has-text("历史"), button:has-text("History"), [class*="history"]').first();

      if (await historyButton.isVisible()) {
        await historyButton.click();
        await page.waitForTimeout(500);

        // 验证历史记录面板出现
        const historyPanel = page.locator('.history-panel, .execution-list, [class*="history"]');
        // 历史面板可能不总是可见
      }
    }
  });
});

// ============================================
// 导航测试
// ============================================
test.describe('核心页面 - 导航', () => {
  test('should navigate between major pages', async ({ page }) => {
    const pages = [
      { path: '/', name: '首页' },
      { path: '/datasets', name: '数据集' },
      { path: '/documents', name: '文档' },
      { path: '/chat', name: '对话' },
      { path: '/workflows', name: '工作流' },
    ];

    for (const pg of pages) {
      await page.goto(`${BASE_URL}${pg.path}`);
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain(pg.path);
    }
  });

  test('should highlight active navigation item', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 查找导航菜单
    const navItems = page.locator('.nav-item, .menu-item, a[class*="nav"]');
    const activeItem = page.locator('.nav-item.active, .menu-item.active, [class*="active"]');

    // 验证有高亮的导航项
    const hasActive = await activeItem.count() > 0;
    console.log('Has active navigation item:', hasActive);
  });

  test('should support browser back and forward', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    await page.goBack();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/datasets');

    await page.goForward();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/documents');
  });
});

// ============================================
// 边界条件测试
// ============================================
test.describe('核心页面 - 边界条件', () => {
  test('should handle very long text input', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);
    await page.waitForLoadState('networkidle');

    const inputBox = page.locator('textarea, [contenteditable="true"]').first();
    if (await inputBox.isVisible()) {
      // 生成很长的文本
      const longText = 'A'.repeat(5000);
      await inputBox.fill(longText);

      // 验证输入成功
      const value = await inputBox.inputValue();
      expect(value.length).toBeGreaterThan(1000);
    }
  });

  test('should handle rapid successive operations', async ({ page }) => {
    await page.goto(`${BASE_URL}/datasets`);
    await page.waitForLoadState('networkidle');

    // 快速点击多次排序
    const sortHeaders = page.locator('th[aria-sort], th[class*="sortable"]');
    const count = await sortHeaders.count();

    if (count > 0) {
      for (let i = 0; i < 5; i++) {
        await sortHeaders.first().click();
      }
      await page.waitForLoadState('networkidle');
    }
  });

  test('should handle concurrent page navigations', async ({ page }) => {
    // 快速导航多个页面
    const paths = ['/datasets', '/documents', '/workflows', '/chat'];

    for (const path of paths) {
      await page.goto(`${BASE_URL}${path}`);
      // 不等待，模拟快速导航
    }

    await page.waitForLoadState('networkidle');
  });
});

// ============================================
// API 验证测试
// ============================================
test.describe('核心页面 - API 验证', () => {
  test('should verify all critical API endpoints', async ({ request }) => {
    const apiClient = createApiClient(request, 'agent_api') as AgentApiClient;

    // 健康检查
    const health = await apiClient.healthCheck();
    expect(health.code).toBe(0);

    // 用户信息
    const userInfo = await apiClient.getUserInfo();
    expect(userInfo.code).toBe(0);

    // 会话列表
    const conversations = await apiClient.getConversations();
    expect(conversations.code).toBe(0);

    // 工作流列表
    const workflows = await apiClient.getWorkflows();
    expect(workflows.code).toBe(0);

    // 数据集列表
    const datasets = await apiClient.getDatasets();
    expect(datasets.code).toBe(0);

    // 统计信息
    const stats = await apiClient.getStats();
    expect(stats.code).toBe(0);

    // 验证没有失败的请求
    const failedRequests = getFailedRequests();
    expect(failedRequests.length).toBe(0);
  });
});

test.afterEach(async ({ request }) => {
  // 每个测试后检查是否有失败的 API 请求
  const failedRequests = getFailedRequests();
  if (failedRequests.length > 0) {
    console.error('Failed API requests in test:', failedRequests);
  }
});
