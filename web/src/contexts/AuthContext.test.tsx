/**
 * AuthContext 单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ access_token: 'test-token', user: { id: '1', name: 'Test User' } }),
  } as Response)
);

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
  });

  describe('useAuth hook', () => {
    it('should provide auth context', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current).toBeDefined();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should handle login', async () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.login('test-user', 'test-password');
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toBeDefined();
      expect(mockLocalStorage.setItem).toHaveBeenCalled();
    });

    it('should handle logout', async () => {
      // 首先设置已登录状态
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({
        token: 'test-token',
        user: { id: '1', name: 'Test User' }
      }));

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      // 等待初始化
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.isAuthenticated).toBe(true);

      // 执行登出
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(mockLocalStorage.removeItem).toHaveBeenCalled();
    });
  });

  describe('ProtectedRoute component', () => {
    it('should redirect to login when not authenticated', () => {
      // 这个测试需要 ProtectedRoute 组件的实现
      // 在实际项目中需要导入并测试
    });

    it('should render children when authenticated', () => {
      // 这个测试需要 ProtectedRoute 组件的实现
      // 在实际项目中需要导入并测试
    });
  });

  describe('token management', () => {
    it('should store token in localStorage after login', async () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.login('test-user', 'test-password');
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'auth',
        expect.stringContaining('test-token')
      );
    });

    it('should restore token from localStorage on init', async () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({
        token: 'stored-token',
        user: { id: '1', name: 'Stored User' }
      }));

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual({ id: '1', name: 'Stored User' });
    });
  });
});
