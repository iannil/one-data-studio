import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import CallbackPage from './CallbackPage';
import * as authService from '../services/auth';

// Mock auth 服务
vi.mock('../services/auth', () => ({
  handleCallback: vi.fn(),
  isAuthenticated: vi.fn(() => false),
}));

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    checkAuth: vi.fn().mockResolvedValue(true),
    authenticated: true,
    loading: false,
    user: null,
    token: null,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn().mockResolvedValue(true),
    hasRole: vi.fn(() => false),
    hasAnyRole: vi.fn(() => false),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams],
  };
});

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {};
Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: vi.fn((key: string) => mockSessionStorage[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      mockSessionStorage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete mockSessionStorage[key];
    }),
    clear: vi.fn(() => {
      Object.keys(mockSessionStorage).forEach((key) => delete mockSessionStorage[key]);
    }),
  },
  writable: true,
});

describe('CallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    Object.keys(mockSessionStorage).forEach((key) => delete mockSessionStorage[key]);
  });

  it('应该在加载时显示处理认证状态', async () => {
    mockSearchParams = new URLSearchParams({ code: 'test-code', state: 'test-state' });
    vi.mocked(authService.handleCallback).mockImplementation(
      () => new Promise(() => {}) // 永不解析，保持加载状态
    );

    render(<CallbackPage />);

    expect(screen.getByText('正在处理认证...')).toBeInTheDocument();
  });

  it('应该显示 Spin 组件', async () => {
    mockSearchParams = new URLSearchParams({ code: 'test-code', state: 'test-state' });
    vi.mocked(authService.handleCallback).mockImplementation(
      () => new Promise(() => {})
    );

    render(<CallbackPage />);

    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

describe('CallbackPage 认证成功', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockSessionStorage).forEach((key) => delete mockSessionStorage[key]);
  });

  it('认证成功应该调用 handleCallback', async () => {
    mockSearchParams = new URLSearchParams({ code: 'valid-code', state: 'valid-state' });
    vi.mocked(authService.handleCallback).mockResolvedValue(true);

    render(<CallbackPage />);

    await waitFor(() => {
      expect(authService.handleCallback).toHaveBeenCalledWith('valid-code', 'valid-state');
    });
  });
});

describe('CallbackPage 认证失败', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockSessionStorage).forEach((key) => delete mockSessionStorage[key]);
  });

  it('缺少 code 参数应该显示错误', async () => {
    mockSearchParams = new URLSearchParams({ state: 'test-state' });

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
      expect(screen.getByText('Invalid callback parameters')).toBeInTheDocument();
    });
  });

  it('缺少 state 参数应该显示错误', async () => {
    mockSearchParams = new URLSearchParams({ code: 'test-code' });

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
      expect(screen.getByText('Invalid callback parameters')).toBeInTheDocument();
    });
  });

  it('OAuth 错误应该显示错误描述', async () => {
    mockSearchParams = new URLSearchParams({
      error: 'access_denied',
      error_description: '用户拒绝了授权请求',
    });

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
      expect(screen.getByText('用户拒绝了授权请求')).toBeInTheDocument();
    });
  });

  it('OAuth 错误无描述时应该显示错误码', async () => {
    mockSearchParams = new URLSearchParams({
      error: 'invalid_request',
    });

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
      expect(screen.getByText('invalid_request')).toBeInTheDocument();
    });
  });

  it('handleCallback 失败应该显示错误', async () => {
    mockSearchParams = new URLSearchParams({ code: 'invalid-code', state: 'test-state' });
    vi.mocked(authService.handleCallback).mockResolvedValue(false);

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
      expect(screen.getByText('Failed to process authentication')).toBeInTheDocument();
    });
  });

  it('错误页面应该显示返回登录链接', async () => {
    mockSearchParams = new URLSearchParams({ error: 'access_denied' });

    render(<CallbackPage />);

    await waitFor(() => {
      const loginLink = screen.getByText('返回登录');
      expect(loginLink).toBeInTheDocument();
      expect(loginLink).toHaveAttribute('href', '/login');
    });
  });
});

describe('CallbackPage 调用认证服务', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockSessionStorage).forEach((key) => delete mockSessionStorage[key]);
  });

  it('应该使用 code 和 state 调用 handleCallback', async () => {
    mockSearchParams = new URLSearchParams({ code: 'my-code', state: 'my-state' });
    vi.mocked(authService.handleCallback).mockResolvedValue(true);

    render(<CallbackPage />);

    await waitFor(() => {
      expect(authService.handleCallback).toHaveBeenCalledWith('my-code', 'my-state');
    });
  });

  it('不应该在有 error 参数时调用 handleCallback', async () => {
    mockSearchParams = new URLSearchParams({ error: 'access_denied' });

    render(<CallbackPage />);

    await waitFor(() => {
      expect(screen.getByText('认证失败')).toBeInTheDocument();
    });

    expect(authService.handleCallback).not.toHaveBeenCalled();
  });
});
