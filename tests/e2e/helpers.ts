/**
 * E2E 测试辅助函数
 */

import { Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

/**
 * 设置认证状态 - 在页面加载前设置 localStorage
 */
export async function setupAuth(page: Page) {
  // 创建一个模拟的 JWT token (header.payload.signature 格式)
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: 'test-user',
    username: 'test-user',
    email: 'test@example.com',
    roles: ['admin', 'user'],
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
  })).toString('base64').replace(/=+$/, '');
  const mockToken = `${header}.${payload}.signature`;

  // 使用 addInitScript 在页面加载前设置 localStorage
  await page.addInitScript((token) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify({
      user_id: 'test-user',
      username: 'test-user',
      email: 'test@example.com',
      roles: ['admin', 'user'],
    }));
  }, mockToken);
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

export { BASE_URL };
