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
import { logError, logDebug } from '../services/logger';
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

    // 使用日志记录器而非 console.log
    logDebug('checkAuth called', 'AuthContext');
    logDebug(`isAuthenticated(): ${isAuth}`, 'AuthContext');
    logDebug(`getAccessToken(): ${accessToken ? 'exists' : 'null'}`, 'AuthContext');
    logDebug(`getUserInfo(): ${userInfo ? 'exists' : 'null'}`, 'AuthContext');

    // 检查 sessionStorage 中的值
    const tokenExpiresAt = sessionStorage.getItem('token_expires_at');
    const storedToken = sessionStorage.getItem('access_token');
    logDebug(`sessionStorage token_expires_at: ${tokenExpiresAt}`, 'AuthContext');
    logDebug(`sessionStorage access_token: ${storedToken ? 'exists' : 'null'}`, 'AuthContext');
    if (tokenExpiresAt) {
      const now = Date.now();
      const expires = parseInt(tokenExpiresAt, 10);
      logDebug(`Time check: now=${now}, expires=${expires}, diff=${expires - now}`, 'AuthContext');
    }

    if (isAuth && accessToken) {
      // Token 未过期
      logDebug('Token valid, setting authenticated=true', 'AuthContext');
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

    // Token 不存在或已过期
    logDebug('Token invalid or missing, setting authenticated=false', 'AuthContext');
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
    // 在 callback 页面跳过初始认证检查，让 CallbackPage 处理
    if (window.location.pathname === '/callback') {
      setLoading(false);
      return;
    }
    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时运行一次

  // 自动刷新 Token
  useEffect(() => {
    if (!autoRefresh || !authenticated) return;

    const interval = setInterval(async () => {
      // 检查是否即将过期（提前 30 秒刷新，避免 token 过期）
      const token = getAccessToken();
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          const expiresAt = payload.exp * 1000;
          const now = Date.now();

          // 提前 30 秒刷新
          if (expiresAt - now < 30 * 1000) {
            logDebug('Token expiring soon, refreshing...', 'AuthContext');
            await refresh();
          }
        } catch (e) {
          logError('Token check failed', 'AuthContext', e);
        }
      }
    }, Math.min(refreshInterval / 2, 30000)); // 最多 30 秒检查一次

    return () => clearInterval(interval);
  }, [authenticated, autoRefresh, refresh]);

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

  logDebug(`Check - loading: ${loading}, authenticated: ${authenticated}, path: ${window.location.pathname}`, 'ProtectedRoute');

  // 加载中
  if (loading) {
    return fallback || <div>Loading...</div>;
  }

  // 需要认证但未认证
  if (requireAuth && !authenticated) {
    logDebug('Not authenticated, redirecting to login', 'ProtectedRoute');
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
