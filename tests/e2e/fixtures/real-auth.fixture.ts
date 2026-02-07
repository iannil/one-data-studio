/**
 * 真实认证 Fixture
 * 支持 Keycloak 真实浏览器登录流程
 * 不使用 Mock，直接与 Keycloak 交互
 */

import { test as base, Page, BrowserContext } from '@playwright/test';

// 加载环境变量
const KEYCLOAK_URL = process.env.KEYCLOAK_URL || 'http://localhost:8080';
const REALM = process.env.KEYCLOAK_REALM || 'one-data-studio';
const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'web-frontend';

// 测试用户角色
export type UserRole = 'admin' | 'developer' | 'user' | 'viewer';

// 测试用户凭证
const TEST_USERS: Record<UserRole, { username: string; password: string; email: string }> = {
  admin: {
    username: process.env.TEST_ADMIN_USERNAME || 'admin',
    password: process.env.TEST_ADMIN_PASSWORD || 'admin123',
    email: process.env.TEST_ADMIN_EMAIL || 'admin@onedata.local',
  },
  developer: {
    username: process.env.TEST_DEVELOPER_USERNAME || 'admin',
    password: process.env.TEST_DEVELOPER_PASSWORD || 'admin123',
    email: process.env.TEST_DEVELOPER_EMAIL || 'admin@onedata.local',
  },
  user: {
    username: process.env.TEST_USER_USERNAME || 'admin',
    password: process.env.TEST_USER_PASSWORD || 'admin123',
    email: process.env.TEST_USER_EMAIL || 'admin@onedata.local',
  },
  viewer: {
    username: process.env.TEST_VIEWER_USERNAME || 'admin',
    password: process.env.TEST_VIEWER_PASSWORD || 'admin123',
    email: process.env.TEST_VIEWER_EMAIL || 'admin@onedata.local',
  },
};

// 存储的认证信息
interface AuthSession {
  accessToken: string;
  refreshToken: string;
  idToken: string;
  tokenType: string;
  expiresIn: number;
  expiresAt: number;
  userInfo: {
    sub: string;
    username: string;
    email: string;
    roles: string[];
  };
}

// 会话存储
const authSessions = new Map<UserRole, AuthSession>();

/**
 * 通过浏览器进行真实的 Keycloak 登录
 */
async function performKeycloakLogin(
  page: Page,
  role: UserRole = 'user'
): Promise<AuthSession> {
  const user = TEST_USERS[role];

  // 如果已有有效会话，直接返回
  const existingSession = authSessions.get(role);
  if (existingSession && existingSession.expiresAt > Date.now()) {
    return existingSession;
  }

  // 构造 Keycloak 登录 URL
  const redirectUri = process.env.BASE_URL || 'http://localhost:3000';
  const loginUrl = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/auth?` +
    `client_id=${CLIENT_ID}&` +
    `redirect_uri=${encodeURIComponent(redirectUri + '/callback')}&` +
    `response_type=code&` +
    `scope=openid profile email&` +
    `state=${Date.now()}`;

  // 访问登录页面
  await page.goto(loginUrl);

  // 等待登录表单加载
  await page.waitForLoadState('networkidle');

  // 检查是否已经在登录页面
  const currentUrl = page.url();
  if (currentUrl.includes('/auth/')) {
    // 填写登录表单
    await page.fill('#username', user.username);
    await page.fill('#password', user.password);

    // 点击登录按钮
    await Promise.all([
      page.waitForNavigation({ url: /callback/ }),
      page.click('#kc-login'),
    ]);
  } else if (currentUrl.includes('/callback')) {
    // 已经登录，直接处理回调
  }

  // 等待回调完成并获取 token
  await page.waitForURL(/callback/);

  // 从 URL 中提取授权码
  const callbackUrl = page.url();
  const codeMatch = callbackUrl.match(/[?&]code=([^&]+)/);

  if (!codeMatch) {
    throw new Error('未能从回调 URL 中获取授权码');
  }

  const code = codeMatch[1];

  // 使用授权码交换 token
  const tokenResponse = await fetch(`${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code: code,
      redirect_uri: redirectUri + '/callback',
    }),
  });

  if (!tokenResponse.ok) {
    throw new Error(`Token 交换失败: ${tokenResponse.statusText}`);
  }

  const tokenData = await tokenResponse.json();

  // 解析 JWT 获取用户信息
  const idTokenPayload = parseJwt(tokenData.id_token);

  const session: AuthSession = {
    accessToken: tokenData.access_token,
    refreshToken: tokenData.refresh_token,
    idToken: tokenData.id_token,
    tokenType: tokenData.token_type || 'Bearer',
    expiresIn: tokenData.expires_in,
    expiresAt: Date.now() + (tokenData.expires_in * 1000),
    userInfo: {
      sub: idTokenPayload.sub,
      username: idTokenPayload.preferred_username || idTokenPayload.name,
      email: idTokenPayload.email,
      roles: idTokenPayload.realm_access?.roles || [role],
    },
  };

  // 保存会话
  authSessions.set(role, session);

  return session;
}

/**
 * 解析 JWT token
 */
function parseJwt(token: string): any {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
  );
  return JSON.parse(jsonPayload);
}

/**
 * 在页面中设置认证状态
 */
async function setupAuthInPage(page: Page, session: AuthSession): Promise<void> {
  await page.addInitScript(({ token, userInfo }) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('refresh_token', token);
    localStorage.setItem('id_token', token);
    localStorage.setItem('user_info', JSON.stringify(userInfo));
    localStorage.setItem('token_expires_at', String(Date.now() + 3600000));
  }, {
    token: session.accessToken,
    userInfo: session.userInfo,
  });
}

/**
 * 刷新认证 token
 */
async function refreshAuthToken(role: UserRole): Promise<AuthSession | null> {
  const session = authSessions.get(role);
  if (!session || !session.refreshToken) {
    return null;
  }

  try {
    const tokenResponse = await fetch(`${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: session.refreshToken,
      }),
    });

    if (!tokenResponse.ok) {
      return null;
    }

    const tokenData = await tokenResponse.json();
    const idTokenPayload = parseJwt(tokenData.id_token);

    const newSession: AuthSession = {
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token || session.refreshToken,
      idToken: tokenData.id_token,
      tokenType: tokenData.token_type || 'Bearer',
      expiresIn: tokenData.expires_in,
      expiresAt: Date.now() + (tokenData.expires_in * 1000),
      userInfo: {
        sub: idTokenPayload.sub,
        username: idTokenPayload.preferred_username || idTokenPayload.name,
        email: idTokenPayload.email,
        roles: idTokenPayload.realm_access?.roles || [role],
      },
    };

    authSessions.set(role, newSession);
    return newSession;
  } catch {
    return null;
  }
}

/**
 * 清除所有认证会话
 */
function clearAuthSessions(): void {
  authSessions.clear();
}

/**
 * 真实认证 Fixture 类型定义
 */
type RealAuthFixtures = {
  /** 已认证的页面 (普通用户角色) */
  authenticatedPage: Page;
  /** 已认证的管理员页面 */
  adminPage: Page;
  /** 已认证的开发者页面 */
  developerPage: Page;
  /** 已认证的查看者页面 */
  viewerPage: Page;
  /** 执行 Keycloak 登录 */
  loginWithKeycloak: (role?: UserRole) => Promise<AuthSession>;
  /** 刷新认证 token */
  refreshToken: (role: UserRole) => Promise<AuthSession | null>;
  /** 清除认证会话 */
  clearAuth: () => void;
  /** 获取认证会话 */
  getAuthSession: (role: UserRole) => AuthSession | undefined;
};

/**
 * 扩展的测试对象，包含真实认证 fixtures
 */
export const test = base.extend<RealAuthFixtures>({
  // 普通用户认证页面
  authenticatedPage: async ({ page, context }, use) => {
    const session = await performKeycloakLogin(page, 'user');
    await setupAuthInPage(page, session);

    // 设置认证头到 context
    await context.setExtraHTTPHeaders({
      'Authorization': `${session.tokenType} ${session.accessToken}`,
    });

    await use(page);
  },

  // 管理员认证页面
  adminPage: async ({ page, context }, use) => {
    const session = await performKeycloakLogin(page, 'admin');
    await setupAuthInPage(page, session);

    await context.setExtraHTTPHeaders({
      'Authorization': `${session.tokenType} ${session.accessToken}`,
    });

    await use(page);
  },

  // 开发者认证页面
  developerPage: async ({ page, context }, use) => {
    const session = await performKeycloakLogin(page, 'developer');
    await setupAuthInPage(page, session);

    await context.setExtraHTTPHeaders({
      'Authorization': `${session.tokenType} ${session.accessToken}`,
    });

    await use(page);
  },

  // 查看者认证页面
  viewerPage: async ({ page, context }, use) => {
    const session = await performKeycloakLogin(page, 'viewer');
    await setupAuthInPage(page, session);

    await context.setExtraHTTPHeaders({
      'Authorization': `${session.tokenType} ${session.accessToken}`,
    });

    await use(page);
  },

  // Keycloak 登录辅助函数
  loginWithKeycloak: async ({ page }, use) => {
    const loginFn = async (role: UserRole = 'user') => {
      return await performKeycloakLogin(page, role);
    };
    await use(loginFn);
  },

  // Token 刷新辅助函数
  refreshToken: async ({}, use) => {
    await use(refreshAuthToken);
  },

  // 清除认证辅助函数
  clearAuth: async ({}, use) => {
    await use(clearAuthSessions);
  },

  // 获取会话辅助函数
  getAuthSession: async ({}, use) => {
    await use((role: UserRole) => authSessions.get(role));
  },
});

export { expect } from '@playwright/test';
export type { AuthSession, UserRole };
export { TEST_USERS };

// ==================== 便捷认证函数 ====================

/**
 * 设置认证的辅助函数（用于非 Fixture 场景）
 * 支持直接通过 API 或页面登录
 */
export async function setupAuth(
  page: Page,
  request: APIRequestContext,
  options: {
    username?: string;
    password?: string;
    role?: UserRole;
  } = {}
): Promise<void> {
  const { username, password, role = 'admin' } = options;
  const user = TEST_USERS[role] || TEST_USERS.admin;

  const creds = {
    username: username || user.username,
    password: password || user.password,
  };

  // 使用直接密码授权获取 token（推荐方式）
  try {
    const tokenData = await getAuthTokenDirect(creds.username, creds.password);
    if (tokenData && tokenData.access_token) {
      const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

      // 导航到应用首页
      await page.goto(BASE_URL);

      // 设置 sessionStorage 数据（应用使用 sessionStorage 而不是 localStorage）
      await page.evaluate((data) => {
        const expiresAt = Date.now() + (data.expires_in * 1000);
        sessionStorage.setItem('access_token', data.access_token);
        sessionStorage.setItem('token_expires_at', expiresAt.toString());

        // 如果有 refresh_token，也存储
        if (data.refresh_token) {
          sessionStorage.setItem('refresh_token', data.refresh_token);
        }

        // 存储 user_info（从 token 解析）
        try {
          // 解析 JWT 获取用户信息
          const parts = data.access_token.split('.');
          if (parts.length === 3) {
            const payload = JSON.parse(atob(parts[1]));
            const userInfo = {
              sub: payload.sub,
              preferred_username: payload.preferred_username || payload.username || creds.username,
              email: payload.email,
              name: payload.name,
              given_name: payload.given_name,
              family_name: payload.family_name,
              roles: payload.realm_access?.roles || payload.roles || ['admin'],
            };
            sessionStorage.setItem('user_info', JSON.stringify(userInfo));
          }
        } catch (e) {
          // 如果解析失败，存储基本信息
          sessionStorage.setItem('user_info', JSON.stringify({
            sub: 'test',
            preferred_username: creds.username,
            email: creds.email || 'test@test.local',
            roles: ['admin'],
          }));
        }
      }, {
        access_token: tokenData.access_token,
        refresh_token: tokenData.refresh_token,
        expires_in: tokenData.expires_in || 300,
        username: creds.username,
        email: user.email,
      });

      // 刷新页面以应用认证状态
      await page.reload();

      // 等待页面加载完成
      await page.waitForLoadState('domcontentloaded').catch(() => {});
      await page.waitForTimeout(1000);

      return;
    }
  } catch (error) {
    console.warn('Direct token fetch failed, trying browser login:', error);
  }

  // 备用方案：尝试浏览器登录流程
  try {
    const session = await performKeycloakLogin(page, role);
    await setupAuthInPage(page, session);
  } catch (error) {
    console.warn('Keycloak login failed, trying simple form login:', error);
    await simpleFormLogin(page, creds.username, creds.password);
  }
}

/**
 * 直接通过 API 获取 token（使用密码授权）
 */
async function getAuthTokenDirect(username: string, password: string): Promise<any> {
  const KEYCLOAK_URL = process.env.KEYCLOAK_URL || 'http://localhost:8080';
  const REALM = process.env.KEYCLOAK_REALM || 'one-data-studio';
  const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'web-frontend';

  const url = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'password',
        client_id: CLIENT_ID,
        username: username,
        password: password,
      }),
    });

    if (!response.ok) {
      console.error('Token fetch failed:', response.status, response.statusText);
      return null;
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Token fetch error:', error);
    return null;
  }
}

/**
 * 简单表单登录（备用方案）
 */
async function simpleFormLogin(page: Page, username: string, password: string): Promise<void> {
  const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

  // 导航到登录页面
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');

  // 尝试填写表单
  const usernameInput = page.locator('input[name="username"], input[placeholder*="用户名"], input[placeholder*="用户"], #username').first();
  const passwordInput = page.locator('input[name="password"], input[type="password"], #password').first();

  if (await usernameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    await usernameInput.fill(username);
  }

  if (await passwordInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    await passwordInput.fill(password);
  }

  // 点击登录按钮
  const loginButton = page.locator('button:has-text("登录"), button:has-text("登 录"), button[type="submit"], #kc-login').first();
  if (await loginButton.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginButton.click();
    await page.waitForTimeout(1000);
  }
}

/**
 * 检查是否已登录
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    const token = await page.evaluate(() => {
      return localStorage.getItem('access_token') || localStorage.getItem('token');
    });

    if (!token) return false;

    // 检查是否在登录页面
    const currentUrl = page.url();
    return !currentUrl.includes('/login');
  } catch {
    return false;
  }
}

/**
 * 清除认证状态
 */
export async function clearAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('id_token');
    localStorage.removeItem('user_info');
  });
}
