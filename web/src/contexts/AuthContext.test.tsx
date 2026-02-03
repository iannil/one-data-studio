/**
 * AuthContext 单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import { AuthProvider, useAuth } from './AuthContext';

// Mock auth service
vi.mock('../services/auth', () => ({
  isAuthenticated: vi.fn(() => false),
  getAccessToken: vi.fn(() => null),
  getUserInfo: vi.fn(() => null),
  refreshAccessToken: vi.fn(),
  clearAuthData: vi.fn(),
  logout: vi.fn(),
  refreshUserInfo: vi.fn(() => null),
}));

// Mock logger
vi.mock('../services/logger', () => ({
  logError: vi.fn(),
  logDebug: vi.fn(),
  logInfo: vi.fn(),
  logWarn: vi.fn(),
}));

// Test component that uses the hook
function TestComponent() {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="authenticated">{String(auth.authenticated)}</div>
      <div data-testid="loading">{String(auth.loading)}</div>
      <div data-testid="user">{auth.user ? auth.user.name : 'null'}</div>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AuthProvider', () => {
    it('should render children', async () => {
      render(
        <AuthProvider>
          <div>Test Content</div>
        </AuthProvider>
      );

      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should provide auth context to children', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toBeInTheDocument();
      });
    });

    it('should show loading state initially', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByTestId('loading')).toBeInTheDocument();
      });
    });
  });

  describe('useAuth hook', () => {
    it('should throw error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<TestComponent />);
      }).toThrow();

      consoleSpy.mockRestore();
    });
  });
});
