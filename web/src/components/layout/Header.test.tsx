/**
 * Header 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'app.name': 'ONE-DATA-STUDIO',
        'app.title': 'Enterprise DataOps Platform',
        'user.username': 'User',
        'user.role': 'Role',
        'user.settings': 'Settings',
        'user.logout': 'Logout',
      };
      return translations[key] || key;
    },
    i18n: {
      language: 'zh-CN',
      changeLanguage: vi.fn(),
    },
  }),
}));

// Mock AuthContext
const mockLogout = vi.fn();
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      name: 'Test User',
      email: 'test@example.com',
      preferred_username: 'testuser',
      roles: ['admin', 'user'],
    },
    logout: mockLogout,
  }),
}));

// Mock i18n
vi.mock('../../i18n', () => ({
  supportedLanguages: [
    { code: 'zh-CN', name: '简体中文', flag: '🇨🇳' },
    { code: 'en-US', name: 'English', flag: '🇺🇸' },
  ],
  changeLanguage: vi.fn(),
}));

// Mock antd components
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    Layout: {
      Header: ({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) => (
        <header data-testid="header" style={style}>{children}</header>
      ),
    },
    Button: ({ children, onClick, icon, type }: any) => (
      <button data-testid={`button-${type || 'default'}`} onClick={onClick}>
        {icon}
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => <div data-testid="space">{children}</div>,
    Typography: {
      Text: ({ children, strong, type }: any) => (
        <span data-testid={`text-${type || 'default'}`} style={{ fontWeight: strong ? 'bold' : 'normal' }}>
          {children}
        </span>
      ),
    },
    Dropdown: ({ children, menu }: any) => (
      <div data-testid="dropdown">
        {children}
        <div data-testid="dropdown-menu">
          {menu?.items?.map((item: any, index: number) => (
            <div key={index} data-testid={`menu-item-${item.key}`} onClick={item.onClick}>
              {item.label}
            </div>
          ))}
        </div>
      </div>
    ),
    Avatar: ({ icon }: any) => <div data-testid="avatar">{icon}</div>,
  };
});

import Header from './Header';

describe('Header Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps = {
    collapsed: false,
    onToggle: vi.fn(),
  };

  it('should render header with app name', () => {
    render(<Header {...defaultProps} />);
    expect(screen.getByText('ONE-DATA-STUDIO')).toBeInTheDocument();
  });

  it('should render toggle button', () => {
    render(<Header {...defaultProps} />);
    const buttons = screen.getAllByTestId(/button/);
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should call onToggle when toggle button is clicked', () => {
    const onToggle = vi.fn();
    render(<Header collapsed={false} onToggle={onToggle} />);

    const toggleButton = screen.getByTestId('button-text');
    fireEvent.click(toggleButton);

    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('should render user avatar when user is logged in', () => {
    render(<Header {...defaultProps} />);
    expect(screen.getByTestId('avatar')).toBeInTheDocument();
  });

  it('should render language dropdown', () => {
    render(<Header {...defaultProps} />);
    const dropdowns = screen.getAllByTestId('dropdown');
    expect(dropdowns.length).toBeGreaterThan(0);
  });

  it('should display collapsed state correctly', () => {
    const { rerender } = render(<Header collapsed={false} onToggle={vi.fn()} />);
    expect(screen.getByTestId('header')).toBeInTheDocument();

    rerender(<Header collapsed={true} onToggle={vi.fn()} />);
    expect(screen.getByTestId('header')).toBeInTheDocument();
  });

  describe('User menu', () => {
    it('should render user menu items', () => {
      render(<Header {...defaultProps} />);

      expect(screen.getByTestId('menu-item-profile')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-settings')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-logout')).toBeInTheDocument();
    });

    it('should call logout when logout menu item is clicked', () => {
      render(<Header {...defaultProps} />);

      const logoutItem = screen.getByTestId('menu-item-logout');
      fireEvent.click(logoutItem);

      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });

  describe('Language switching', () => {
    it('should render supported languages', () => {
      render(<Header {...defaultProps} />);

      expect(screen.getByTestId('menu-item-zh-CN')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-en-US')).toBeInTheDocument();
    });
  });
});
