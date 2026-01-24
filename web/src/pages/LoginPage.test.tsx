import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import * as authService from '../services/auth';

// Mock auth 服务
vi.mock('../services/auth', () => ({
  buildLoginUrl: vi.fn(() => 'https://keycloak.example.com/auth'),
  mockLogin: vi.fn(),
  getKeycloakConfig: vi.fn(() => ({
    url: 'https://keycloak.example.com',
    realm: 'one-data-studio',
    clientId: 'web-client',
  })),
  isAuthenticated: vi.fn(() => false),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams()],
  };
});

// Mock window.location
const mockLocation = {
  href: '',
  origin: 'http://localhost:5173',
};
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
  });

  it('应该正确渲染登录页面', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('ONE DATA STUDIO')).toBeInTheDocument();
    });
  });

  it('应该显示平台描述', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('企业级 AI 融合平台')).toBeInTheDocument();
    });
  });

  it('应该显示 SSO 登录按钮', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /使用 SSO 登录/i })).toBeInTheDocument();
    });
  });

  it('应该显示认证服务器信息', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('认证服务器:')).toBeInTheDocument();
      expect(screen.getByText(/keycloak.example.com/)).toBeInTheDocument();
    });
  });

  it('应该显示开发模式分隔线', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('开发模式')).toBeInTheDocument();
    });
  });

  it('应该显示模拟登录表单切换按钮', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('显示模拟登录表单')).toBeInTheDocument();
    });
  });
});

describe('LoginPage SSO 登录', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
  });

  it('点击 SSO 登录按钮应该跳转到认证服务器', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /使用 SSO 登录/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /使用 SSO 登录/i }));

    expect(mockLocation.href).toBe('https://keycloak.example.com/auth');
  });
});

describe('LoginPage 模拟登录', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
    vi.mocked(authService.mockLogin).mockResolvedValue(true);
  });

  it('应该能够显示模拟登录表单', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('显示模拟登录表单')).toBeInTheDocument();
    });

    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户名 (admin)')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('密码 (admin)')).toBeInTheDocument();
    });
  });

  it('应该能够提交模拟登录表单', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    // 显示表单
    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户名 (admin)')).toBeInTheDocument();
    });

    // 默认值已经填充，直接点击登录
    await user.click(screen.getByRole('button', { name: /模拟登录/i }));

    await waitFor(() => {
      expect(authService.mockLogin).toHaveBeenCalledWith('admin', 'admin');
    });
  });

  it('模拟登录成功应该跳转', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户名 (admin)')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /模拟登录/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('模拟登录失败应该显示错误', async () => {
    vi.mocked(authService.mockLogin).mockResolvedValue(false);

    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户名 (admin)')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /模拟登录/i }));

    await waitFor(() => {
      expect(screen.getByText('用户名或密码错误')).toBeInTheDocument();
    });
  });

  it('应该显示默认账号提示', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByText(/默认账号/)).toBeInTheDocument();
    });
  });
});

describe('LoginPage 已登录状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
  });

  it('已登录应该自动跳转', async () => {
    renderWithRouter(<LoginPage />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });
});

describe('LoginPage 表单验证', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
  });

  it('用户名必填', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LoginPage />);

    await user.click(screen.getByText('显示模拟登录表单'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户名 (admin)')).toBeInTheDocument();
    });

    // 清空用户名
    const usernameInput = screen.getByPlaceholderText('用户名 (admin)');
    await user.clear(usernameInput);

    await user.click(screen.getByRole('button', { name: /模拟登录/i }));

    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument();
    });
  });
});
