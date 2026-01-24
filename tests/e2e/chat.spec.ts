/**
 * 聊天功能 E2E 测试
 * Sprint 9: E2E 测试扩展
 *
 * 使用 Playwright 测试聊天功能的关键场景
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8081';

// 测试辅助函数
async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  // 模拟登录（根据实际登录流程调整）
  await page.fill('input[name="username"]', 'test-user');
  await page.fill('input[name="password"]', 'test-password');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');
}

async function navigateToChat(page: Page) {
  await page.click('[data-testid="nav-chat"]');
  await page.waitForURL('**/chat');
}

test.describe('Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // 设置请求拦截以模拟 API 响应
    await page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'healthy',
          service: 'bisheng-api',
        }),
      });
    });

    await page.route('**/api/v1/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            reply: '这是一个测试回复',
            conversation_id: 'test-conv-123',
          },
        }),
      });
    });
  });

  test('should display chat interface', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    // 验证聊天界面元素存在
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="send-button"]')).toBeVisible();
  });

  test('should send message successfully', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    // 输入消息
    await page.fill('[data-testid="chat-input"]', '你好，请介绍一下这个平台');

    // 发送消息
    await page.click('[data-testid="send-button"]');

    // 验证消息显示
    await expect(page.locator('text=你好，请介绍一下这个平台')).toBeVisible();

    // 等待回复（模拟）
    await expect(page.locator('text=这是一个测试回复')).toBeVisible({ timeout: 5000 });
  });

  test('should handle empty message input', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    // 尝试发送空消息
    await page.click('[data-testid="send-button"]');

    // 验证错误提示
    await expect(page.locator('text=请输入消息')).toBeVisible();
  });

  test('should display conversation history', async ({ page }) => {
    // 模拟会话历史 API
    await page.route('**/api/v1/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            conversations: [
              {
                conversation_id: 'conv-1',
                title: '第一个对话',
                created_at: '2024-01-01T00:00:00Z',
              },
              {
                conversation_id: 'conv-2',
                title: '第二个对话',
                created_at: '2024-01-02T00:00:00Z',
              },
            ],
          },
        }),
      });
    });

    await page.goto(`${BASE_URL}/chat`);

    // 验证会话列表显示
    await expect(page.locator('text=第一个对话')).toBeVisible();
    await expect(page.locator('text=第二个对话')).toBeVisible();
  });

  test('should create new conversation', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    // 点击新建对话
    await page.click('[data-testid="new-conversation-button"]');

    // 验证新对话创建
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
  });

  test('should switch between conversations', async ({ page }) => {
    // 模拟会话切换
    await page.goto(`${BASE_URL}/chat`);

    // 点击第一个对话
    await page.click('text=第一个对话');

    // 验证切换成功
    await expect(page).toHaveURL(/conv-1/);
  });
});

test.describe('Chat Input Features', () => {
  test('should support multiline input', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    const message = '第一行\n第二行\n第三行';
    await page.fill('[data-testid="chat-input"]', message);

    const inputValue = await page.inputValue('[data-testid="chat-input"]');
    expect(inputValue).toContain('第一行');
  });

  test('should clear input after sending', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    await page.fill('[data-testid="chat-input"]', '测试消息');
    await page.click('[data-testid="send-button"]');

    // 验证输入框被清空
    const inputValue = await page.inputValue('[data-testid="chat-input"]');
    expect(inputValue).toBe('');
  });

  test('should show typing indicator', async ({ page }) => {
    // 模拟延迟响应
    await page.route('**/api/v1/chat', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: 'success',
          data: { reply: '回复' },
        }),
      });
    });

    await page.goto(`${BASE_URL}/chat`);
    await page.fill('[data-testid="chat-input"]', '测试');
    await page.click('[data-testid="send-button"]');

    // 验证加载指示器显示
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();
  });
});

test.describe('Chat Error Handling', () => {
  test('should handle network error', async ({ page }) => {
    // 模拟网络错误
    await page.route('**/api/v1/chat', async (route) => {
      await route.abort('failed');
    });

    await page.goto(`${BASE_URL}/chat`);
    await page.fill('[data-testid="chat-input"]', '测试消息');
    await page.click('[data-testid="send-button"]');

    // 验证错误提示
    await expect(page.locator('text=网络连接失败')).toBeVisible();
  });

  test('should handle timeout', async ({ page }) => {
    // 模拟超时
    await page.route('**/api/v1/chat', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 35000));
      await route.fulfill({
        status: 200,
        body: '{}',
      });
    });

    await page.goto(`${BASE_URL}/chat`);
    await page.fill('[data-testid="chat-input"]', '测试消息');
    await page.click('[data-testid="send-button"]');

    // 验证超时提示
    await expect(page.locator('text=请求超时')).toBeVisible({ timeout: 35000 });
  });
});

test.describe('Chat Model Selection', () => {
  test('should display model options', async ({ page }) => {
    // 模拟模型列表 API
    await page.route('**/v1/models', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'gpt-4o-mini', object: 'model' },
            { id: 'gpt-4o', object: 'model' },
          ],
        }),
      });
    });

    await page.goto(`${BASE_URL}/chat`);

    // 点击模型选择器
    await page.click('[data-testid="model-selector"]');

    // 验证模型选项
    await expect(page.locator('text=gpt-4o-mini')).toBeVisible();
    await expect(page.locator('text=gpt-4o')).toBeVisible();
  });

  test('should switch model', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`);

    // 选择不同模型
    await page.click('[data-testid="model-selector"]');
    await page.click('text=gpt-4o');

    // 验证模型切换
    await expect(page.locator('[data-testid="current-model"]')).toContainText('gpt-4o');
  });
});
