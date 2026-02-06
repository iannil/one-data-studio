/**
 * 认证 Fixture
 * 提供预配置的认证上下文用于测试
 */

import { test as base, Page } from '@playwright/test';

/**
 * 认证 Fixture 类型定义
 */
type AuthFixtures = {
  /** 已认证的普通用户页面 */
  authenticatedPage: Page;
  /** 已认证的管理员页面 */
  adminPage: Page;
  /** 未认证的页面 */
  unauthenticatedPage: Page;
};

/**
 * 设置认证状态到页面
 * 需要匹配 AuthContext 的认证检查逻辑
 */
async function setupAuthToPage(page: Page, roles: string[] = ['user']): Promise<void> {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64').replace(/=+$/, '');
  const payload = Buffer.from(JSON.stringify({
    sub: 'test-user',
    preferred_username: 'test-user',
    email: 'test@example.com',
    roles: roles,
    exp: Math.floor(Date.now() / 1000) + 3600 * 24,
    resource_access: {
      'web-frontend': {
        roles: roles,
      },
    },
  })).toString('base64').replace(/=+$/, '');
  const mockToken = `${header}.${payload}.signature`;

  const expiresAt = Date.now() + 3600 * 24 * 1000;

  await page.addInitScript(({ token, expiresAt, roles }) => {
    // 设置 sessionStorage (AuthContext 需要)
    sessionStorage.setItem('access_token', token);
    sessionStorage.setItem('token_expires_at', expiresAt.toString());
    sessionStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user',
      preferred_username: 'test-user',
      email: 'test@example.com',
      roles: roles,
    }));

    // 也设置 localStorage 以防万一
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_info', JSON.stringify({
      sub: 'test-user',
      preferred_username: 'test-user',
      email: 'test@example.com',
      roles: roles,
    }));
  }, { token: mockToken, expiresAt, roles });
}

/**
 * 设置通用 API Mock
 */
function setupCommonApiMocks(page: Page): void {
  page.route('**/api/v1/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'healthy' }),
    });
  });

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
 * 扩展的测试对象，包含认证 fixtures
 */
export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await setupAuthToPage(page, ['user']);
    setupCommonApiMocks(page);
    await use(page);
  },

  adminPage: async ({ page }, use) => {
    await setupAuthToPage(page, ['admin', 'user']);
    setupCommonApiMocks(page);
    await use(page);
  },

  unauthenticatedPage: async ({ page }, use) => {
    // 不设置认证，但设置通用 mock
    setupCommonApiMocks(page);
    await use(page);
  },
});

export { expect } from '@playwright/test';
