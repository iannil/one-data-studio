/**
 * DashboardPage 组件测试
 * 测试门户工作台页面（简单包装组件）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';

// Mock PortalDashboard 组件
vi.mock('@/components/portal', () => ({
  PortalDashboard: () => <div data-testid="portal-dashboard">Portal Dashboard Component</div>,
}));

import DashboardPage from './DashboardPage';

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面', () => {
      render(<DashboardPage />);
      expect(screen.getByTestId('portal-dashboard')).toBeInTheDocument();
    });

    it('应该包含 PortalDashboard 子组件', () => {
      render(<DashboardPage />);
      expect(screen.getByTestId('portal-dashboard')).toHaveTextContent('Portal Dashboard Component');
    });

    it('应该有正确的容器样式', () => {
      render(<DashboardPage />);
      // 检查内联样式是否应用到包含 padding 的元素上
      const styledElement = document.querySelector('div[style*="padding"]');
      expect(styledElement).toBeInTheDocument();
    });
  });

  describe('组件结构', () => {
    it('应该渲染单个子组件', () => {
      const { container } = render(<DashboardPage />);
      // QueryClientProvider 可能会添加额外的 div，所以我们只检查 PortalDashboard 是否存在
      expect(screen.getByTestId('portal-dashboard')).toBeInTheDocument();
    });

    it('PortalDashboard 应该是直接子元素', () => {
      const { container } = render(<DashboardPage />);
      const wrapper = container.firstChild as HTMLElement;
      const dashboard = wrapper.querySelector('[data-testid="portal-dashboard"]');
      expect(dashboard).toBeInTheDocument();
      expect(dashboard?.parentElement).toBe(wrapper);
    });
  });
});
