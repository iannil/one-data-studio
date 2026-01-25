/**
 * 认证服务
 * Sprint 3.1: Keycloak SSO 集成
 * Sprint 21: Security Hardening - HttpOnly Cookie 认证
 *
 * 功能：
 * - Keycloak OAuth2/OIDC 登录流程
 * - Token 管理（HttpOnly Cookie 存储，防止 XSS）
 * - 登出处理
 * - 自动 Token 刷新
 */

import { logError } from './logger';

// ============= 类型定义 =============

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  token_type: string;
}

export interface KeycloakConfig {
  url: string;
  realm: string;
  clientId: string;
}

export interface UserInfo {
  sub: string;
  preferred_username: string;
  email?: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  roles: string[];
}

export interface AuthState {
  authenticated: boolean;
  loading: boolean;
  user: UserInfo | null;
  token: string | null;
}

// ============= Keycloak 配置 =============

// 在生产环境使用代理路径，开发环境直接访问
const getKeycloakUrl = () => {
  // 如果设置了 VITE_KEYCLOAK_URL 并且是开发模式，直接使用
  if (import.meta.env.DEV && import.meta.env.VITE_KEYCLOAK_URL) {
    return import.meta.env.VITE_KEYCLOAK_URL;
  }
  // 生产环境使用 nginx 代理
  return window.location.origin + '/auth';
};

const KEYCLOAK_CONFIG: KeycloakConfig = {
  url: getKeycloakUrl(),
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'one-data-studio',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'web-frontend',
};

// 本地存储键（仅用于非敏感数据）
// Token 现在存储在 HttpOnly Cookie 中，不再使用 localStorage
const STORAGE_KEYS = {
  USER_INFO: 'user_info',
  TOKEN_EXPIRES_AT: 'token_expires_at',
  // DEPRECATED: access_token 和 refresh_token 现在由后端通过 HttpOnly Cookie 管理
};

// ============= Cookie 工具函数 =============

/**
 * 获取 Cookie 值（仅用于非 HttpOnly Cookie）
 * 注意：HttpOnly Cookie 无法通过 JavaScript 读取，这是安全特性
 */
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

/**
 * 获取 CSRF Token
 * CSRF Token 存储在可读 Cookie 中，用于发送到服务器验证
 */
export function getCsrfToken(): string | null {
  return getCookie('csrf_token') || getCookie('X-CSRF-Token');
}

// ============= Token 管理 =============

/**
 * 存储用户信息（非敏感数据）
 * Token 现在通过 HttpOnly Cookie 存储
 */
export function storeTokens(tokens: AuthTokens): void {
  const expiresAt = Date.now() + tokens.expires_in * 1000;
  sessionStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());

  // 注意：Token 现在由服务器通过 Set-Cookie 头设置为 HttpOnly Cookie
  // 前端不再直接存储 access_token 和 refresh_token
}

/**
 * 获取访问 Token 状态
 * 由于使用 HttpOnly Cookie，前端无法读取实际 Token
 * 返回 'httponly' 表示 Token 存在于 Cookie 中
 */
export function getAccessToken(): string | null {
  // 检查 Token 是否未过期
  const expiresAt = sessionStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  if (expiresAt && Date.now() < parseInt(expiresAt, 10)) {
    return 'httponly'; // 表示 Token 存在但无法读取（HttpOnly）
  }
  return null;
}

/**
 * 获取刷新 Token（已废弃）
 * HttpOnly Cookie 中的 refresh_token 无法直接访问
 */
export function getRefreshToken(): string | null {
  // refresh_token 现在是 HttpOnly Cookie，无法通过 JavaScript 访问
  // 刷新操作由后端自动处理
  return null;
}

/**
 * 检查 Token 是否过期
 */
export function isTokenExpired(): boolean {
  const expiresAt = sessionStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  if (!expiresAt) return true;
  // 提前 5 分钟判断为过期
  return Date.now() > parseInt(expiresAt, 10) - 5 * 60 * 1000;
}

/**
 * 清除所有认证信息
 */
export function clearAuthData(): void {
  sessionStorage.removeItem(STORAGE_KEYS.USER_INFO);
  sessionStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  // localStorage 中的历史数据也清理
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_info');
  localStorage.removeItem('token_expires_at');
}

// ============= 用户信息管理 =============

/**
 * 解析 JWT Token 获取用户信息
 */
export function parseJwtToken(token: string): UserInfo | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1]));

    // 提取角色
    const roles: string[] = [];
    if (payload.resource_access) {
      Object.values(payload.resource_access).forEach((clientAccess: unknown) => {
        const access = clientAccess as { roles?: string[] };
        if (access.roles) {
          roles.push(...access.roles);
        }
      });
    }
    if (payload.realm_access?.roles) {
      roles.push(...payload.realm_access.roles);
    }

    return {
      sub: payload.sub,
      preferred_username: payload.preferred_username || payload.email || payload.sub,
      email: payload.email,
      name: payload.name,
      given_name: payload.given_name,
      family_name: payload.family_name,
      roles: [...new Set(roles)], // 去重
    };
  } catch (e) {
    logError('Failed to parse JWT token', 'Auth', e);
    return null;
  }
}

/**
 * 存储用户信息
 */
export function storeUserInfo(userInfo: UserInfo): void {
  sessionStorage.setItem(STORAGE_KEYS.USER_INFO, JSON.stringify(userInfo));
}

/**
 * 获取用户信息
 */
export function getUserInfo(): UserInfo | null {
  const stored = sessionStorage.getItem(STORAGE_KEYS.USER_INFO);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch (e) {
      return null;
    }
  }
  // Fallback to localStorage for migration
  const legacyStored = localStorage.getItem('user_info');
  if (legacyStored) {
    try {
      const userInfo = JSON.parse(legacyStored);
      // Migrate to sessionStorage
      storeUserInfo(userInfo);
      localStorage.removeItem('user_info');
      return userInfo;
    } catch (e) {
      return null;
    }
  }
  return null;
}

/**
 * 从 Token 刷新用户信息
 */
export function refreshUserInfo(): UserInfo | null {
  const token = getAccessToken();
  if (!token) return null;
  const userInfo = parseJwtToken(token);
  if (userInfo) {
    storeUserInfo(userInfo);
  }
  return userInfo;
}

// ============= 认证流程 =============

/**
 * 构建 Keycloak 登录 URL
 */
export function buildLoginUrl(redirectUri?: string): string {
  const redirect = redirectUri || window.location.origin + '/callback';
  const state = Math.random().toString(36).substring(2, 15);

  // 存储状态用于验证
  sessionStorage.setItem('oauth_state', state);
  sessionStorage.setItem('oauth_redirect', window.location.pathname);

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CONFIG.clientId,
    redirect_uri: redirect,
    response_type: 'code',
    scope: 'openid profile email',
    state: state,
  });

  return `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/auth?${params.toString()}`;
}

/**
 * 构建 Keycloak 登出 URL
 */
export function buildLogoutUrl(redirectUri?: string): string {
  const redirect = redirectUri || window.location.origin;

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CONFIG.clientId,
    post_logout_redirect_uri: redirect,
  });

  return `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/logout?${params.toString()}`;
}

/**
 * 处理 OAuth 回调
 */
export async function handleCallback(code: string, state: string): Promise<boolean> {
  // 验证状态
  const storedState = sessionStorage.getItem('oauth_state');
  console.log('[Auth] Callback - state:', state, 'storedState:', storedState);

  if (state !== storedState) {
    logError(`Invalid state parameter: received=${state}, stored=${storedState}`, 'Auth');
    console.error('[Auth] State mismatch!');
    return false;
  }

  try {
    // 使用授权码交换 Token
    const redirectUri = window.location.origin + '/callback';
    const tokenEndpoint = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`;

    console.log('[Auth] Token endpoint:', tokenEndpoint);
    console.log('[Auth] Redirect URI:', redirectUri);

    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        client_id: KEYCLOAK_CONFIG.clientId,
        redirect_uri: redirectUri,
      }),
    });

    console.log('[Auth] Token response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Auth] Token exchange failed:', errorText);
      throw new Error('Failed to exchange code for tokens');
    }

    const tokens: AuthTokens = await response.json();
    console.log('[Auth] Tokens received, expires_in:', tokens.expires_in);
    storeTokens(tokens);

    // 解析并存储用户信息
    const userInfo = parseJwtToken(tokens.access_token);
    if (userInfo) {
      storeUserInfo(userInfo);
    }

    // 清理
    sessionStorage.removeItem('oauth_state');

    return true;
  } catch (e) {
    logError('Callback handling failed', 'Auth', e);
    return false;
  }
}

/**
 * 刷新 Token
 *
 * 调用后端刷新端点，后端会从 HttpOnly Cookie 中读取 refresh_token。
 * 这比直接发送 refresh_token 更安全，因为 refresh_token 不会暴露给 JavaScript。
 */
export async function refreshAccessToken(): Promise<boolean> {
  try {
    // 调用后端刷新端点
    // 后端会自动从 HttpOnly Cookie 中读取 refresh_token
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // 重要：包含 Cookie
      body: JSON.stringify({}), // 空 body，refresh_token 从 Cookie 读取
    });

    if (!response.ok) {
      logError(`Token refresh failed: ${response.status}`, 'Auth');
      return false;
    }

    const result = await response.json();

    if (result.code === 0 && result.data) {
      // 更新本地状态（过期时间）
      // 注意：Token 本身由服务器通过 Set-Cookie 头更新
      const expiresAt = Date.now() + (result.data.expires_in || 3600) * 1000;
      sessionStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());

      // 更新用户信息（如果返回了新的 token）
      if (result.data.access_token) {
        const userInfo = parseJwtToken(result.data.access_token);
        if (userInfo) {
          storeUserInfo(userInfo);
        }
      }

      return true;
    }

    return false;
  } catch (e) {
    logError('Token refresh failed', 'Auth', e);
    // 注意：刷新失败不应该清除认证数据，因为原有 token 可能仍然有效
    // clearAuthData(); // 移除此调用
    return false;
  }
}

/**
 * 登出
 */
export function logout(redirectUri?: string): void {
  clearAuthData();
  const logoutUrl = buildLogoutUrl(redirectUri);
  window.location.href = logoutUrl;
}

/**
 * 检查认证状态
 */
export function isAuthenticated(): boolean {
  const token = getAccessToken();
  return token !== null && !isTokenExpired();
}

/**
 * 获取 Keycloak 配置
 */
export function getKeycloakConfig(): KeycloakConfig {
  return KEYCLOAK_CONFIG;
}

// ============= 模拟登录（开发模式）============
// Development mode only - enables local testing without Keycloak

/**
 * 模拟登录（仅开发模式）
 * @param username 用户名
 * @param password 密码
 * @returns 登录结果
 */
export function mockLogin(username: string, password: string): Promise<boolean> {
  // Only allow mock login in development mode
  if (!import.meta.env.DEV) {
    console.warn('Mock login is only available in development mode');
    return Promise.resolve(false);
  }

  // Simple mock validation for development
  if (username && password) {
    // Create mock user info
    const mockUser: UserInfo = {
      sub: 'dev-user-001',
      preferred_username: username,
      email: `${username}@dev.local`,
      name: username,
      roles: ['admin', 'user', 'developer'],
    };

    // Store mock tokens (simulating 1 hour expiry)
    const expiresAt = Date.now() + 3600 * 1000;
    sessionStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());
    storeUserInfo(mockUser);

    return Promise.resolve(true);
  }

  return Promise.resolve(false);
}

/**
 * 导出默认实例
 */
export default {
  buildLoginUrl,
  buildLogoutUrl,
  handleCallback,
  refreshAccessToken,
  logout,
  isAuthenticated,
  getAccessToken,
  getUserInfo,
  storeTokens,
  clearAuthData,
  mockLogin,
  KEYCLOAK_CONFIG,
};
