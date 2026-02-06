/**
 * Auth service 测试
 * 测试认证服务功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock logger
vi.mock('./logger', () => ({
  logError: vi.fn(),
  logDebug: vi.fn(),
}));

import {
  getCsrfToken,
  storeTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  clearAuthData,
  parseJwtToken,
  storeUserInfo,
  getUserInfo,
  refreshUserInfo,
  buildLoginUrl,
  buildLogoutUrl,
  isAuthenticated,
  getKeycloakConfig,
  mockLogin,
} from './auth';

describe('Auth Service', () => {
  let mockWindow: Window & {
    location: { origin: string; pathname: string; href: string };
  };

  beforeEach(() => {
    // Clear sessionStorage and localStorage
    sessionStorage.clear();
    localStorage.clear();

    // Mock window.location
    mockWindow = {
      location: {
        origin: 'http://localhost:3000',
        pathname: '/test',
        href: 'http://localhost:3000/test',
      },
    } as unknown as Window & { location: { origin: string; pathname: string; href: string } };
    Object.defineProperty(global, 'window', {
      value: mockWindow,
      writable: true,
    });

    // Mock document.cookie
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: '',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ==================== Token 管理 ====================

  describe('Token Management', () => {
    it('should store tokens in sessionStorage', () => {
      const tokens = {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        expires_in: 3600,
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      expect(sessionStorage.getItem('access_token')).toBe('test-access-token');
      expect(sessionStorage.getItem('refresh_token')).toBe('test-refresh-token');
    });

    it('should get access token if not expired', () => {
      const tokens = {
        access_token: 'test-access-token',
        expires_in: 3600,
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      const token = getAccessToken();
      expect(token).toBe('test-access-token');
    });

    it('should return null if token is expired', () => {
      const tokens = {
        access_token: 'test-access-token',
        expires_in: -1, // Already expired
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      const token = getAccessToken();
      expect(token).toBeNull();
    });

    it('should return null for refresh token (HttpOnly)', () => {
      const token = getRefreshToken();
      expect(token).toBeNull();
    });

    it('should check if token is expired', () => {
      const tokens = {
        access_token: 'test-access-token',
        expires_in: -1,
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      expect(isTokenExpired()).toBe(true);
    });

    it('should clear auth data', () => {
      sessionStorage.setItem('access_token', 'test-token');
      sessionStorage.setItem('user_info', '{"sub":"123"}');
      localStorage.setItem('access_token', 'old-token');

      clearAuthData();

      expect(sessionStorage.getItem('access_token')).toBeNull();
      expect(sessionStorage.getItem('user_info')).toBeNull();
      expect(localStorage.getItem('access_token')).toBeNull();
    });
  });

  // ==================== JWT 解析 ====================

  describe('JWT Token Parsing', () => {
    it('should parse valid JWT token', () => {
      // Create a mock JWT token (header.payload.signature)
      const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
      const payload = btoa(
        JSON.stringify({
          sub: 'user-123',
          preferred_username: 'testuser',
          email: 'test@example.com',
          resource_access: {
            'web-frontend': { roles: ['user', 'admin'] },
          },
          realm_access: { roles: ['offline_access'] },
        })
      );
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;

      const userInfo = parseJwtToken(token);

      expect(userInfo).not.toBeNull();
      expect(userInfo?.sub).toBe('user-123');
      expect(userInfo?.preferred_username).toBe('testuser');
      expect(userInfo?.email).toBe('test@example.com');
      expect(userInfo?.roles).toContain('user');
      expect(userInfo?.roles).toContain('admin');
      expect(userInfo?.roles).toContain('offline_access');
    });

    it('should return null for invalid token', () => {
      const userInfo = parseJwtToken('invalid-token');
      expect(userInfo).toBeNull();
    });

    it('should return null for token with wrong number of parts', () => {
      const userInfo = parseJwtToken('only.two.parts');
      expect(userInfo).toBeNull();
    });
  });

  // ==================== 用户信息管理 ====================

  describe('User Info Management', () => {
    it('should store user info', () => {
      const userInfo = {
        sub: 'user-123',
        preferred_username: 'testuser',
        email: 'test@example.com',
        roles: ['user'],
      };
      storeUserInfo(userInfo);

      const stored = sessionStorage.getItem('user_info');
      expect(stored).toBe(JSON.stringify(userInfo));
    });

    it('should get stored user info', () => {
      const userInfo = {
        sub: 'user-123',
        preferred_username: 'testuser',
        email: 'test@example.com',
        roles: ['user'],
      };
      sessionStorage.setItem('user_info', JSON.stringify(userInfo));

      const retrieved = getUserInfo();
      expect(retrieved).toEqual(userInfo);
    });

    it('should migrate user info from localStorage to sessionStorage', () => {
      const userInfo = {
        sub: 'user-123',
        preferred_username: 'testuser',
        roles: ['user'],
      };
      localStorage.setItem('user_info', JSON.stringify(userInfo));

      const retrieved = getUserInfo();

      expect(retrieved).toEqual(userInfo);
      expect(sessionStorage.getItem('user_info')).toBe(JSON.stringify(userInfo));
      expect(localStorage.getItem('user_info')).toBeNull();
    });

    it('should return null if no user info stored', () => {
      const retrieved = getUserInfo();
      expect(retrieved).toBeNull();
    });

    it('should refresh user info from token', () => {
      const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
      const payload = btoa(
        JSON.stringify({
          sub: 'user-123',
          preferred_username: 'testuser',
          email: 'test@example.com',
          resource_access: {},
          realm_access: { roles: [] },
        })
      );
      const token = `${header}.${payload}.signature`;
      sessionStorage.setItem('access_token', token);
      // Set token expiry to a future time so it's not expired
      sessionStorage.setItem('token_expires_at', (Date.now() + 3600000).toString());

      const userInfo = refreshUserInfo();

      expect(userInfo).not.toBeNull();
      expect(userInfo?.sub).toBe('user-123');
      expect(sessionStorage.getItem('user_info')).toBe(JSON.stringify(userInfo));
    });
  });

  // ==================== OAuth URL 构建 ====================

  describe('OAuth URL Building', () => {
    it('should build login URL', () => {
      const url = buildLoginUrl('http://localhost:3000/callback');

      expect(url).toContain('/auth/realms/one-data-studio/protocol/openid-connect/auth');
      expect(url).toContain('response_type=code');
      expect(url).toContain('client_id=web-frontend');
      expect(url).toContain('redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback');
      expect(url).toContain('state=');
    });

    it('should store oauth state in sessionStorage', () => {
      buildLoginUrl();

      expect(sessionStorage.getItem('oauth_state')).not.toBeNull();
      expect(sessionStorage.getItem('oauth_redirect')).toBe('/test');
    });

    it('should build logout URL', () => {
      const url = buildLogoutUrl('http://localhost:3000');

      expect(url).toContain('/auth/realms/one-data-studio/protocol/openid-connect/logout');
      expect(url).toContain('client_id=web-frontend');
      expect(url).toContain('post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A3000');
    });
  });

  // ==================== 认证状态检查 ====================

  describe('Authentication Status', () => {
    it('should return true when authenticated with valid token', () => {
      const tokens = {
        access_token: 'test-access-token',
        expires_in: 3600,
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      expect(isAuthenticated()).toBe(true);
    });

    it('should return false when no token', () => {
      expect(isAuthenticated()).toBe(false);
    });

    it('should return false when token expired', () => {
      const tokens = {
        access_token: 'test-access-token',
        expires_in: -1,
        token_type: 'Bearer',
      };
      storeTokens(tokens);

      expect(isAuthenticated()).toBe(false);
    });
  });

  // ==================== Keycloak 配置 ====================

  describe('Keycloak Configuration', () => {
    it('should get Keycloak config', () => {
      const config = getKeycloakConfig();

      expect(config).toHaveProperty('url');
      expect(config).toHaveProperty('realm');
      expect(config).toHaveProperty('clientId');
      expect(config.realm).toBe('one-data-studio');
      expect(config.clientId).toBe('web-frontend');
    });
  });

  // ==================== CSRF Token ====================

  describe('CSRF Token', () => {
    it('should get csrf_token from cookie', () => {
      document.cookie = 'csrf_token=test-csrf-token';

      const token = getCsrfToken();
      expect(token).toBe('test-csrf-token');
    });

    it('should get X-CSRF-Token from cookie', () => {
      document.cookie = 'X-CSRF-Token=test-csrf-token';

      const token = getCsrfToken();
      expect(token).toBe('test-csrf-token');
    });

    it('should return null when no csrf cookie', () => {
      const token = getCsrfToken();
      expect(token).toBeNull();
    });
  });

  // ==================== 模拟登录 (开发模式) ====================

  describe('Mock Login (Development)', () => {
    it('should mock login successfully in dev mode', async () => {
      // Mock import.meta.env.DEV
      vi.stubGlobal('import.meta', { env: { DEV: true } });

      const result = await mockLogin('testuser', 'password');

      expect(result).toBe(true);
      expect(sessionStorage.getItem('user_info')).not.toBeNull();

      vi.unstubAllGlobals();
    });

    it('should fail mock login with empty credentials', async () => {
      vi.stubGlobal('import.meta', { env: { DEV: true } });

      const result = await mockLogin('', '');

      expect(result).toBe(false);

      vi.unstubAllGlobals();
    });
  });
});
