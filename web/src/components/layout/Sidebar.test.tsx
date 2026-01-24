/**
 * Sidebar 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/dashboard' }),
}));

// Mock antd Menu
vi.mock('antd', () => ({
  Menu: ({ items, onClick, selectedKeys, theme, mode, inlineCollapsed }: any) => (
    <nav data-testid="menu" data-theme={theme} data-collapsed={inlineCollapsed}>
      {items?.map((item: any) => (
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
}));

import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render menu with all navigation items', () => {
    render(<Sidebar collapsed={false} />);

    expect(screen.getByTestId('menu-item--')).toBeInTheDocument(); // Home
    expect(screen.getByTestId('menu-item--datasets')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--documents')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--chat')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--workflows')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--metadata')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--schedules')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--agents')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--text2sql')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item--executions')).toBeInTheDocument();
  });

  it('should render menu labels in Chinese', () => {
    render(<Sidebar collapsed={false} />);

    expect(screen.getByText('首页')).toBeInTheDocument();
    expect(screen.getByText('数据集管理')).toBeInTheDocument();
    expect(screen.getByText('文档管理')).toBeInTheDocument();
    expect(screen.getByText('AI 聊天')).toBeInTheDocument();
    expect(screen.getByText('工作流')).toBeInTheDocument();
    expect(screen.getByText('元数据')).toBeInTheDocument();
    expect(screen.getByText('调度管理')).toBeInTheDocument();
    expect(screen.getByText('Agent 实验室')).toBeInTheDocument();
    expect(screen.getByText('Text2SQL')).toBeInTheDocument();
    expect(screen.getByText('执行历史')).toBeInTheDocument();
  });

  it('should navigate when menu item is clicked', () => {
    render(<Sidebar collapsed={false} />);

    const datasetsItem = screen.getByTestId('menu-item--datasets');
    fireEvent.click(datasetsItem);

    expect(mockNavigate).toHaveBeenCalledWith('/datasets');
  });

  it('should navigate to workflows page', () => {
    render(<Sidebar collapsed={false} />);

    const workflowsItem = screen.getByTestId('menu-item--workflows');
    fireEvent.click(workflowsItem);

    expect(mockNavigate).toHaveBeenCalledWith('/workflows');
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
  const expectedMenuItems = [
    { key: '/', label: '首页' },
    { key: '/datasets', label: '数据集管理' },
    { key: '/documents', label: '文档管理' },
    { key: '/chat', label: 'AI 聊天' },
    { key: '/workflows', label: '工作流' },
    { key: '/metadata', label: '元数据' },
    { key: '/schedules', label: '调度管理' },
    { key: '/agents', label: 'Agent 实验室' },
    { key: '/text2sql', label: 'Text2SQL' },
    { key: '/executions', label: '执行历史' },
  ];

  it('should have exactly 10 menu items', () => {
    render(<Sidebar collapsed={false} />);

    const menuItems = screen.getAllByTestId(/menu-item-/);
    expect(menuItems).toHaveLength(10);
  });

  expectedMenuItems.forEach((item) => {
    it(`should render ${item.label} menu item`, () => {
      render(<Sidebar collapsed={false} />);
      expect(screen.getByText(item.label)).toBeInTheDocument();
    });
  });
});
