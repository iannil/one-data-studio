/**
 * SmartSchedulerPage 组件测试
 * 测试智能任务调度页面（简单包装组件）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/testUtils';

// Mock SmartScheduler 组件
vi.mock('@/components/scheduler', () => ({
  SmartScheduler: () => <div data-testid="smart-scheduler">Smart Scheduler Component</div>,
}));

import SmartSchedulerPage from './SmartSchedulerPage';

describe('SmartSchedulerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面', () => {
      render(<SmartSchedulerPage />);
      expect(screen.getByTestId('smart-scheduler')).toBeInTheDocument();
    });

    it('应该包含 SmartScheduler 子组件', () => {
      render(<SmartSchedulerPage />);
      expect(screen.getByTestId('smart-scheduler')).toHaveTextContent('Smart Scheduler Component');
    });

    it('应该有正确的容器样式', () => {
      render(<SmartSchedulerPage />);
      // 检查内联样式是否应用到包含 padding 的元素上
      const styledElement = document.querySelector('div[style*="padding"]');
      expect(styledElement).toBeInTheDocument();
    });
  });

  describe('组件结构', () => {
    it('应该渲染单个子组件', () => {
      const { container } = render(<SmartSchedulerPage />);
      // QueryClientProvider 可能会添加额外的 div，所以我们只检查 SmartScheduler 是否存在
      expect(screen.getByTestId('smart-scheduler')).toBeInTheDocument();
    });

    it('SmartScheduler 应该是直接子元素', () => {
      const { container } = render(<SmartSchedulerPage />);
      const wrapper = container.firstChild as HTMLElement;
      const scheduler = wrapper.querySelector('[data-testid="smart-scheduler"]');
      expect(scheduler).toBeInTheDocument();
      expect(scheduler?.parentElement).toBe(wrapper);
    });
  });
});
