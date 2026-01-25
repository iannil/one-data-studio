/**
 * E2E 测试辅助函数
 */

import { Page, Response, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

/**
 * API 调用记录接口
 */
export interface ApiCall {
  url: string;
  method: string;
  requestBody?: unknown;
  responseStatus: number;
  responseBody?: unknown;
  timestamp: number;
}

/**
 * 设置认证状态 - 在页面加载前设置 localStorage
 */
export async function setupAuth(page: Page, options?: { roles?: string[] }) {
  const roles = options?.roles || ['admin', 'user'];

  // 创建一个模拟的 JWT token (header.payload.signature 格式)
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: 'test-user',
    username: 'test-user',
    email: 'test@example.com',
    roles: roles,
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
  })).toString('base64').replace(/=+$/, '');
  const mockToken = `${header}.${payload}.signature`;

  // 使用 addInitScript 在页面加载前设置 localStorage
  await page.addInitScript(({ token, roles }) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify({
      user_id: 'test-user',
      username: 'test-user',
      email: 'test@example.com',
      roles: roles,
    }));
  }, { token: mockToken, roles });
}

/**
 * 设置通用的 Mock API 响应
 */
export function setupCommonMocks(page: Page) {
  // 健康检查
  page.route('**/api/v1/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'healthy' }),
    });
  });

  // 用户信息
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
 * 等待特定 API 调用完成并返回响应
 */
export async function waitForApiCall(
  page: Page,
  pattern: string,
  options?: { timeout?: number; method?: string }
): Promise<Response> {
  const timeout = options?.timeout || 30000;
  const method = options?.method?.toUpperCase();

  const response = await page.waitForResponse(
    (resp) => {
      const urlMatches = resp.url().includes(pattern.replace(/\*\*/g, ''));
      const methodMatches = method ? resp.request().method() === method : true;
      return urlMatches && methodMatches;
    },
    { timeout }
  );

  return response;
}

/**
 * 拦截 API 调用
 */
export async function interceptApiCall(
  page: Page,
  pattern: string,
  handler: (route: { fulfill: (options: { status: number; body: string }) => Promise<void> }) => Promise<void>
): Promise<void> {
  await page.route(pattern, handler);
}

/**
 * 捕获多个 API 调用
 */
export async function captureApiCalls(
  page: Page,
  patterns: string[]
): Promise<ApiCall[]> {
  const calls: ApiCall[] = [];

  for (const pattern of patterns) {
    page.on('response', async (response) => {
      const url = response.url();
      if (patterns.some(p => url.includes(p.replace(/\*\*/g, '')))) {
        try {
          const body = await response.json();
          calls.push({
            url,
            method: response.request().method(),
            responseStatus: response.status(),
            responseBody: body,
            timestamp: Date.now(),
          });
        } catch {
          calls.push({
            url,
            method: response.request().method(),
            responseStatus: response.status(),
            timestamp: Date.now(),
          });
        }
      }
    });
  }

  return calls;
}

/**
 * 验证 Ant Design Message 消息提示
 */
export async function verifyAntMessage(
  page: Page,
  type: 'success' | 'error' | 'warning' | 'info',
  text?: string
): Promise<void> {
  const messageSelector = `.ant-message-${type}`;
  await expect(page.locator(messageSelector).first()).toBeVisible({ timeout: 10000 });

  if (text) {
    await expect(page.locator(messageSelector).first()).toContainText(text);
  }
}

/**
 * 验证 Ant Design Table 表格状态
 */
export async function verifyAntTable(
  page: Page,
  options?: { loading?: boolean; empty?: boolean; rowCount?: number }
): Promise<void> {
  const tableSelector = '.ant-table';
  await expect(page.locator(tableSelector).first()).toBeVisible();

  if (options?.loading) {
    await expect(page.locator('.ant-table-loading')).toBeVisible();
  }

  if (options?.empty) {
    await expect(page.locator('.ant-table-empty, .ant-empty')).toBeVisible();
  }

  if (options?.rowCount !== undefined) {
    const rows = page.locator('.ant-table-tbody .ant-table-row');
    await expect(rows).toHaveCount(options.rowCount);
  }
}

/**
 * 验证 Ant Design Modal 对话框
 */
export async function verifyAntModal(
  page: Page,
  title: string,
  visible = true
): Promise<void> {
  const modalSelector = '.ant-modal';

  if (visible) {
    await expect(page.locator(modalSelector)).toBeVisible();
    await expect(page.locator('.ant-modal-title')).toContainText(title);
  } else {
    await expect(page.locator(modalSelector)).not.toBeVisible();
  }
}

/**
 * 验证 Ant Design Drawer 抽屉
 */
export async function verifyAntDrawer(
  page: Page,
  title: string,
  visible = true
): Promise<void> {
  const drawerSelector = '.ant-drawer';

  if (visible) {
    await expect(page.locator(drawerSelector)).toBeVisible();
    await expect(page.locator('.ant-drawer-title')).toContainText(title);
  } else {
    await expect(page.locator(drawerSelector)).not.toBeVisible();
  }
}

/**
 * 填写 Ant Design 表单
 */
export async function fillAntForm(
  page: Page,
  formData: Record<string, string | number | boolean>
): Promise<void> {
  for (const [field, value] of Object.entries(formData)) {
    const input = page.locator(`#${field}, [name="${field}"]`).first();
    const tagName = await input.evaluate(el => el.tagName.toLowerCase());

    if (tagName === 'input') {
      const inputType = await input.getAttribute('type');
      if (inputType === 'checkbox') {
        if (value) {
          await input.check();
        } else {
          await input.uncheck();
        }
      } else {
        await input.fill(String(value));
      }
    } else if (tagName === 'textarea') {
      await input.fill(String(value));
    }
  }
}

/**
 * 选择 Ant Design Select 下拉选项
 */
export async function selectAntOption(
  page: Page,
  selectorId: string,
  optionText: string
): Promise<void> {
  // 点击选择器打开下拉菜单
  await page.click(`#${selectorId}, [id="${selectorId}"]`);
  // 等待下拉菜单出现
  await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
  // 选择选项
  await page.click(`.ant-select-dropdown .ant-select-item:has-text("${optionText}")`);
}

/**
 * 点击 Ant Design Popconfirm 确认按钮
 */
export async function confirmAntPopconfirm(page: Page): Promise<void> {
  await page.click('.ant-popconfirm-buttons .ant-btn-primary');
}

/**
 * 取消 Ant Design Popconfirm
 */
export async function cancelAntPopconfirm(page: Page): Promise<void> {
  await page.click('.ant-popconfirm-buttons .ant-btn:not(.ant-btn-primary)');
}

/**
 * 等待页面加载完成（包括懒加载组件）
 */
export async function waitForPageLoad(page: Page): Promise<void> {
  // 等待 Spin 消失
  await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 30000 }).catch(() => {});
  // 等待网络空闲
  await page.waitForLoadState('networkidle');
}

/**
 * 获取表格中特定行的数据
 */
export async function getTableRowData(
  page: Page,
  rowIndex: number
): Promise<string[]> {
  const cells = page.locator(`.ant-table-tbody .ant-table-row:nth-child(${rowIndex + 1}) .ant-table-cell`);
  const count = await cells.count();
  const data: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await cells.nth(i).textContent();
    data.push(text || '');
  }

  return data;
}

/**
 * 模拟 API 延迟响应（用于测试加载状态）
 */
export async function mockApiWithDelay(
  page: Page,
  pattern: string,
  response: { status: number; body: unknown },
  delayMs: number
): Promise<void> {
  await page.route(pattern, async (route) => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.fulfill({
      status: response.status,
      contentType: 'application/json',
      body: JSON.stringify(response.body),
    });
  });
}

/**
 * 模拟 API 错误响应
 */
export async function mockApiError(
  page: Page,
  pattern: string,
  statusCode: number,
  message?: string
): Promise<void> {
  await page.route(pattern, async (route) => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({
        code: statusCode,
        message: message || `Error ${statusCode}`,
      }),
    });
  });
}

/**
 * 模拟网络错误
 */
export async function mockNetworkError(
  page: Page,
  pattern: string
): Promise<void> {
  await page.route(pattern, async (route) => {
    await route.abort('failed');
  });
}

export { BASE_URL };
