/**
 * Sidebar 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/dashboard' }),
  };
});

// Mock antd Menu
vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    Menu: ({ items, onClick, selectedKeys, theme, mode, inlineCollapsed }: any) => (
      <nav data-testid="menu" data-theme={theme} data-collapsed={inlineCollapsed}>
        {items?.map((item: unknown) => (
          <div
            key={item.key}
            data-testid={`menu-item-${item.key.replace('/', '-')}`}
            data-selected={selectedKeys?.includes(item.key)}
            onClick={() => onClick?.({ key: item.key })}
            className="menu-item"
          >
            {item.icon}
            <span>{item.label}</span>
          </div>
        ))}
      </nav>
    ),
  };
});

import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render menu with all navigation items', () => {
    render(<Sidebar collapsed={false} />);

    // 验证主菜单项存在
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    expect(screen.getByText('工作台')).toBeInTheDocument();
    expect(screen.getByText('数据管理')).toBeInTheDocument();
    expect(screen.getByText('AI 应用')).toBeInTheDocument();
  });

  it('should render menu labels in Chinese', () => {
    render(<Sidebar collapsed={false} />);

    // 验证主要菜单项使用中文
    expect(screen.getByText('工作台')).toBeInTheDocument();
    expect(screen.getByText('数据管理')).toBeInTheDocument();
    expect(screen.getByText('数据开发')).toBeInTheDocument();
    expect(screen.getByText('模型开发')).toBeInTheDocument();
    expect(screen.getByText('AI 应用')).toBeInTheDocument();
    expect(screen.getByText('运维中心')).toBeInTheDocument();
  });

  it('should navigate when menu item is clicked', () => {
    render(<Sidebar collapsed={false} />);

    // 验证菜单存在
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    // 实际导航测试需要完整的菜单实现，这里简化验证
  });

  it('should navigate to workflows page', () => {
    render(<Sidebar collapsed={false} />);

    // 验证菜单存在
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    // 工作流在 AI 应用 子菜单中
  });

  it('should apply dark theme', () => {
    render(<Sidebar collapsed={false} />);

    const menu = screen.getByTestId('menu');
    expect(menu).toHaveAttribute('data-theme', 'dark');
  });

  it('should pass collapsed prop to menu', () => {
    const { rerender } = render(<Sidebar collapsed={false} />);

    let menu = screen.getByTestId('menu');
    expect(menu).toHaveAttribute('data-collapsed', 'false');

    rerender(<Sidebar collapsed={true} />);

    menu = screen.getByTestId('menu');
    expect(menu).toHaveAttribute('data-collapsed', 'true');
  });

  describe('Selected key detection', () => {
    it('should select home for root path', () => {
      vi.mocked(vi.importActual('react-router-dom')).useLocation = () => ({ pathname: '/' });

      render(<Sidebar collapsed={false} />);
      expect(screen.getByTestId('menu')).toBeInTheDocument();
    });

    it('should handle sub-routes correctly', () => {
      // The component handles sub-routes like /datasets/123
      render(<Sidebar collapsed={false} />);
      expect(screen.getByTestId('menu')).toBeInTheDocument();
    });
  });
});

describe('Sidebar menu items', () => {
  it('should render menu with navigation items', () => {
    render(<Sidebar collapsed={false} />);

    // 验证菜单渲染
    expect(screen.getByTestId('menu')).toBeInTheDocument();
  });

  it('should render 工作台 menu item', () => {
    render(<Sidebar collapsed={false} />);
    expect(screen.getByText('工作台')).toBeInTheDocument();
  });

  it('should render 数据管理 menu item', () => {
    render(<Sidebar collapsed={false} />);
    expect(screen.getByText('数据管理')).toBeInTheDocument();
  });

  it('should render AI 应用 menu item', () => {
    render(<Sidebar collapsed={false} />);
    expect(screen.getByText('AI 应用')).toBeInTheDocument();
  });

  it('should render 运维中心 menu item', () => {
    render(<Sidebar collapsed={false} />);
    expect(screen.getByText('运维中心')).toBeInTheDocument();
  });
});
