/**
 * 认证上下文
 * Sprint 3.1: 全局认证状态管理
 *
 * 功能：
 * - 提供全局认证状态
 * - 自动 Token 刷新
 * - 路由守卫支持
 */

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { message } from 'antd';
import { logError } from '../services/logger';
import {
  isAuthenticated,
  getAccessToken,
  getUserInfo,
  UserInfo,
  refreshAccessToken,
  clearAuthData,
  logout,
  refreshUserInfo,
} from '../services/auth';

// ============= 类型定义 =============

interface AuthContextValue {
  authenticated: boolean;
  loading: boolean;
  user: UserInfo | null;
  token: string | null;
  login: (redirectUri?: string) => void;
  logout: (redirectUri?: string) => void;
  refresh: () => Promise<boolean>;
  checkAuth: () => Promise<boolean>;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

interface AuthProviderProps {
  children: ReactNode;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

// ============= Context 创建 =============

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ============= AuthProvider 组件 =============

export function AuthProvider({ children, autoRefresh = true, refreshInterval = 300000 }: AuthProviderProps) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // 检查认证状态
  const checkAuth = useCallback(async (): Promise<boolean> => {
    setLoading(true);

    const isAuth = isAuthenticated();
    const accessToken = getAccessToken();
    const userInfo = getUserInfo();

    if (isAuth && accessToken) {
      // Token 未过期
      setAuthenticated(true);
      setToken(accessToken);
      setUser(userInfo);

      // 如果没有用户信息，尝试从 Token 解析
      if (!userInfo) {
        const parsed = refreshUserInfo();
        if (parsed) {
          setUser(parsed);
        }
      }

      setLoading(false);
      return true;
    }

    // Token 过期或不存在，尝试刷新
    if (accessToken) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        setAuthenticated(true);
        setToken(getAccessToken());
        setUser(getUserInfo());
        setLoading(false);
        return true;
      }
    }

    // 认证失败
    setAuthenticated(false);
    setToken(null);
    setUser(null);
    setLoading(false);
    return false;
  }, []);

  // 登录
  const login = useCallback((redirectUri?: string) => {
    const authUrl = new URL('/login', window.location.origin);
    if (redirectUri) {
      authUrl.searchParams.set('redirect', redirectUri);
    }
    window.location.href = authUrl.toString();
  }, []);

  // 登出
  const handleLogout = useCallback((redirectUri?: string) => {
    clearAuthData();
    setAuthenticated(false);
    setToken(null);
    setUser(null);
    message.info('已退出登录');
    logout(redirectUri);
  }, []);

  // 刷新 Token
  const refresh = useCallback(async (): Promise<boolean> => {
    const success = await refreshAccessToken();
    if (success) {
      setToken(getAccessToken());
      setUser(getUserInfo());
    } else {
      setAuthenticated(false);
      setToken(null);
      setUser(null);
    }
    return success;
  }, []);

  // 检查角色
  const hasRole = useCallback((role: string): boolean => {
    return user?.roles?.includes(role) || false;
  }, [user]);

  // 检查是否有任一角色
  const hasAnyRole = useCallback((roles: string[]): boolean => {
    if (!user?.roles) return false;
    return roles.some(role => user.roles.includes(role));
  }, [user]);

  // 初始化检查
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // 自动刷新 Token
  useEffect(() => {
    if (!autoRefresh || !authenticated) return;

    const interval = setInterval(async () => {
      // 检查是否即将过期（提前 5 分钟）
      const token = getAccessToken();
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          const expiresAt = payload.exp * 1000;
          const now = Date.now();

          if (expiresAt - now < 5 * 60 * 1000) {
            await refresh();
          }
        } catch (e) {
          logError('Token check failed', 'AuthContext', e);
        }
      }
    }, refreshInterval / 2); // 更频繁地检查

    return () => clearInterval(interval);
  }, [authenticated, autoRefresh, refreshInterval, refresh]);

  // 值
  const value: AuthContextValue = {
    authenticated,
    loading,
    user,
    token,
    login,
    logout: handleLogout,
    refresh,
    checkAuth,
    hasRole,
    hasAnyRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ============= useAuth Hook =============

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// ============= ProtectedRoute 组件 =============

interface ProtectedRouteProps {
  children: ReactNode;
  requireAuth?: boolean;
  requiredRoles?: string[];
  fallback?: ReactNode;
}

export function ProtectedRoute({
  children,
  requireAuth = true,
  requiredRoles,
  fallback,
}: ProtectedRouteProps) {
  const { authenticated, loading, user } = useAuth();

  // 加载中
  if (loading) {
    return fallback || <div>Loading...</div>;
  }

  // 需要认证但未认证
  if (requireAuth && !authenticated) {
    // 重定向到登录页
    const currentPath = window.location.pathname;
    const loginUrl = new URL('/login', window.location.origin);
    loginUrl.searchParams.set('redirect', currentPath);
    window.location.href = loginUrl.toString();
    return null;
  }

  // 需要特定角色
  if (requiredRoles && requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some(role => user?.roles?.includes(role));
    if (!hasRequiredRole) {
      return (
        fallback || (
          <div style={{ padding: '50px', textAlign: 'center' }}>
            <h2>无权限访问</h2>
            <p>您需要以下角色之一: {requiredRoles.join(', ')}</p>
          </div>
        )
      );
    }
  }

  return <>{children}</>;
}

export default AuthContext;
