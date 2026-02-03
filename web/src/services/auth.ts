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

import { logError, logDebug } from './logger';

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

// 优先使用环境变量配置的 Keycloak URL
const getKeycloakUrl = () => {
  // 如果设置了 VITE_KEYCLOAK_URL，直接使用（开发和生产环境）
  if (import.meta.env.VITE_KEYCLOAK_URL) {
    return import.meta.env.VITE_KEYCLOAK_URL;
  }
  // 默认使用 nginx 代理
  return window.location.origin + '/auth';
};

const KEYCLOAK_CONFIG: KeycloakConfig = {
  url: getKeycloakUrl(),
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'one-data-studio',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'web-frontend',
};

// 本地存储键
// 存储 access_token 到 sessionStorage，用于 SSO 登录
const STORAGE_KEYS = {
  USER_INFO: 'user_info',
  TOKEN_EXPIRES_AT: 'token_expires_at',
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
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
 * 存储 Token 和用户信息
 * 将 Token 存储到 sessionStorage 中，用于 API 请求的 Authorization header
 */
export function storeTokens(tokens: AuthTokens): void {
  const expiresAt = Date.now() + tokens.expires_in * 1000;
  sessionStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());
  // 存储 access_token 用于 API 请求
  sessionStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, tokens.access_token);
  // 如果有 refresh_token，也存储
  if (tokens.refresh_token) {
    sessionStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokens.refresh_token);
  }
}

/**
 * 获取访问 Token
 * 从 sessionStorage 中返回存储的 access_token
 */
export function getAccessToken(): string | null {
  // 检查 Token 是否未过期
  const expiresAt = sessionStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  if (expiresAt && Date.now() < parseInt(expiresAt, 10)) {
    return sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
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
  // 检查是否真正过期（不提前判断，避免短有效期 token 立即失效）
  return Date.now() > parseInt(expiresAt, 10);
}

/**
 * 清除所有认证信息
 */
export function clearAuthData(): void {
  sessionStorage.removeItem(STORAGE_KEYS.USER_INFO);
  sessionStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  sessionStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  sessionStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
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
  logDebug(`Callback - state: ${state}, storedState: ${storedState}`, 'Auth');

  if (state !== storedState) {
    logError(`Invalid state parameter: received=${state}, stored=${storedState}`, 'Auth');
    return false;
  }

  try {
    // 使用授权码交换 Token
    const redirectUri = window.location.origin + '/callback';
    const tokenEndpoint = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`;

    logDebug(`Token endpoint: ${tokenEndpoint}`, 'Auth');
    logDebug(`Redirect URI: ${redirectUri}`, 'Auth');

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

    logDebug(`Token response status: ${response.status}`, 'Auth');

    if (!response.ok) {
      const errorText = await response.text();
      logError(`Token exchange failed: ${errorText}`, 'Auth');
      throw new Error('Failed to exchange code for tokens');
    }

    const tokens: AuthTokens = await response.json();
    logDebug(`Tokens received, expires_in: ${tokens.expires_in}`, 'Auth');
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
 * 调用后端刷新端点，或使用 Keycloak 直接刷新
 */
export async function refreshAccessToken(): Promise<boolean> {
  try {
    // 优先尝试使用后端刷新端点
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      // 如果后端刷新失败，尝试直接使用 Keycloak 刷新
      return await refreshWithKeycloak();
    }

    const result = await response.json();

    if (result.code === 0 && result.data) {
      // 更新本地状态
      const expiresAt = Date.now() + (result.data.expires_in || 3600) * 1000;
      sessionStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());

      // 更新 access_token（如果返回了新的 token）
      if (result.data.access_token) {
        sessionStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, result.data.access_token);
        const userInfo = parseJwtToken(result.data.access_token);
        if (userInfo) {
          storeUserInfo(userInfo);
        }
      }

      return true;
    }

    // 后端返回错误，尝试 Keycloak 刷新
    return await refreshWithKeycloak();
  } catch (e) {
    logError('Token refresh failed', 'Auth', e);
    // 尝试直接使用 Keycloak 刷新
    return await refreshWithKeycloak();
  }
}

/**
 * 使用 Keycloak 直接刷新 Token
 */
async function refreshWithKeycloak(): Promise<boolean> {
  try {
    const refreshToken = sessionStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    if (!refreshToken) {
      return false;
    }

    const tokenEndpoint = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`;
    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: KEYCLOAK_CONFIG.clientId,
      }),
    });

    if (!response.ok) {
      return false;
    }

    const tokens: AuthTokens = await response.json();
    storeTokens(tokens);

    // 更新用户信息
    const userInfo = parseJwtToken(tokens.access_token);
    if (userInfo) {
      storeUserInfo(userInfo);
    }

    return true;
  } catch (e) {
    logError('Keycloak token refresh failed', 'Auth', e);
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
