/**
 * 认证服务
 * Sprint 3.1: Keycloak SSO 集成
 *
 * 功能：
 * - Keycloak OAuth2/OIDC 登录流程
 * - Token 管理（存储、刷新、验证）
 * - 登出处理
 */

import { apiClient } from './api';

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

const KEYCLOAK_CONFIG: KeycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://keycloak.one-data.local',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'one-data-studio',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'web-frontend',
};

// 本地存储键
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_INFO: 'user_info',
  TOKEN_EXPIRES_AT: 'token_expires_at',
};

// ============= Token 管理 =============

/**
 * 存储 Token
 */
export function storeTokens(tokens: AuthTokens): void {
  const expiresAt = Date.now() + tokens.expires_in * 1000;
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, tokens.access_token);
  if (tokens.refresh_token) {
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokens.refresh_token);
  }
  localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());
}

/**
 * 获取访问 Token
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

/**
 * 获取刷新 Token
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
}

/**
 * 检查 Token 是否过期
 */
export function isTokenExpired(): boolean {
  const expiresAt = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  if (!expiresAt) return true;
  // 提前 5 分钟判断为过期
  return Date.now() > parseInt(expiresAt, 10) - 5 * 60 * 1000;
}

/**
 * 清除所有认证信息
 */
export function clearAuthData(): void {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.USER_INFO);
  localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
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
      Object.values(payload.resource_access).forEach((clientAccess: any) => {
        if (clientAccess.roles) {
          roles.push(...clientAccess.roles);
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
    console.error('Failed to parse JWT token:', e);
    return null;
  }
}

/**
 * 存储用户信息
 */
export function storeUserInfo(userInfo: UserInfo): void {
  localStorage.setItem(STORAGE_KEYS.USER_INFO, JSON.stringify(userInfo));
}

/**
 * 获取用户信息
 */
export function getUserInfo(): UserInfo | null {
  const stored = localStorage.getItem(STORAGE_KEYS.USER_INFO);
  if (stored) {
    try {
      return JSON.parse(stored);
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
 * 生成 PKCE code verifier 和 challenge
 */
function generatePKCE(): { codeVerifier: string; codeChallenge: string } {
  // 生成随机 code_verifier
  const codeVerifier = Array.from(crypto.getRandomValues(new Uint8Array(32)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // 存储 code_verifier
  sessionStorage.setItem('pkce_code_verifier', codeVerifier);

  // 生成 code_challenge (SHA256)
  async function generateChallenge(codeVerifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(codeVerifier);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(hash)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }

  // 注意：由于是同步函数，这里简化处理
  // 实际使用时应该使用 async 版本
  const challenge = btoa(codeVerifier.substring(0, 43))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  return { codeVerifier, codeChallenge: challenge };
}

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
  if (state !== storedState) {
    console.error('Invalid state parameter');
    return false;
  }

  try {
    // 使用授权码交换 Token
    const redirectUri = window.location.origin + '/callback';
    const tokenEndpoint = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`;

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

    if (!response.ok) {
      throw new Error('Failed to exchange code for tokens');
    }

    const tokens: AuthTokens = await response.json();
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
    console.error('Callback handling failed:', e);
    return false;
  }
}

/**
 * 刷新 Token
 */
export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
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
      throw new Error('Failed to refresh token');
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
    console.error('Token refresh failed:', e);
    clearAuthData();
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

/**
 * 模拟登录（用于开发环境）
 */
export function mockLogin(username: string, password: string): Promise<boolean> {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (username === 'admin' && password === 'admin') {
        // 创建模拟 Token
        const mockToken = btoa(JSON.stringify({
          sub: 'user-001',
          preferred_username: 'admin',
          email: 'admin@example.com',
          name: 'Administrator',
          exp: Math.floor(Date.now() / 1000) + 3600,
          realm_access: { roles: ['admin'] },
        }));

        const mockTokens: AuthTokens = {
          access_token: mockToken,
          refresh_token: 'mock_refresh_token',
          expires_in: 3600,
          token_type: 'Bearer',
        };

        storeTokens(mockTokens);

        const userInfo: UserInfo = {
          sub: 'user-001',
          preferred_username: 'admin',
          email: 'admin@example.com',
          name: 'Administrator',
          roles: ['admin'],
        };
        storeUserInfo(userInfo);

        resolve(true);
      } else {
        resolve(false);
      }
    }, 500);
  });
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
