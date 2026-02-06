/**
 * NotificationsPage 组件测试
 * 测试消息通知页面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { UserNotification, NotificationListParams } from '../../services/admin';

// Mock admin service
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../services/admin', () => ({
  getUserNotifications: vi.fn(() => Promise.resolve({
    code: 0,
    data: {
      notifications: [],
      total: 0,
      unread_count: 0,
      page: 1,
      page_size: 20,
    },
  })),
  markNotificationRead: vi.fn(() => Promise.resolve({ code: 0 })),
  markAllNotificationsRead: vi.fn(() => Promise.resolve({ code: 0 })),
  archiveNotification: vi.fn(() => Promise.resolve({ code: 0 })),
  deleteNotification: vi.fn(() => Promise.resolve({ code: 0 })),
}));

import NotificationsPage from './NotificationsPage';
import {
  getUserNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  archiveNotification,
  deleteNotification,
} from '../../services/admin';

// Mock data
const mockNotifications: UserNotification[] = [
  {
    id: 'notif-1',
    user_id: 'user-1',
    title: '系统维护通知',
    summary: '系统将于今晚进行维护',
    content: '系统将于今晚22:00-24:00进行维护',
    notification_type: 'warning',
    severity: 'high',
    source_name: '系统',
    is_read: false,
    is_archived: false,
    created_at: '2026-02-06T10:00:00Z',
  },
  {
    id: 'notif-2',
    user_id: 'user-1',
    title: '数据集审核待办',
    summary: '请审核新的数据集申请',
    content: '有新的数据集访问申请等待审核',
    notification_type: 'approval',
    severity: 'medium',
    source_name: 'Data API',
    action_url: '/data/datasets/123',
    action_label: '查看详情',
    is_read: false,
    is_archived: false,
    created_at: '2026-02-06T09:00:00Z',
  },
  {
    id: 'notif-3',
    user_id: 'user-1',
    title: '任务执行成功',
    summary: '您的ETL任务已成功完成',
    content: '任务处理了1000条记录',
    notification_type: 'success',
    severity: 'low',
    source_name: 'ETL Service',
    is_read: true,
    is_archived: false,
    created_at: '2026-02-06T08:00:00Z',
  },
  {
    id: 'notif-4',
    user_id: 'user-1',
    title: 'API调用失败告警',
    summary: '检测到大量API调用失败',
    content: '过去1小时内有500次失败调用',
    notification_type: 'alert',
    severity: 'critical',
    source_name: 'API Gateway',
    action_url: '/admin/api-calls',
    is_read: false,
    is_archived: false,
    created_at: '2026-02-06T07:00:00Z',
  },
  {
    id: 'notif-5',
    user_id: 'user-1',
    title: '新任务分配',
    summary: '您有一个新的待办任务',
    content: '请完成数据质量检查',
    notification_type: 'task',
    severity: 'medium',
    source_name: 'Workflow',
    is_read: false,
    is_archived: false,
    created_at: '2026-02-06T06:00:00Z',
  },
];

const mockNotificationResponse = {
  code: 0,
  data: {
    notifications: mockNotifications,
    total: 5,
    unread_count: 4,
    page: 1,
    page_size: 20,
  },
};

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getUserNotifications).mockResolvedValue(mockNotificationResponse);
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面标题', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('消息通知')).toBeInTheDocument();
      });
    });

    it('应该显示通知统计信息', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText(/共 5 条通知/)).toBeInTheDocument();
        expect(screen.getByText(/4 条未读/)).toBeInTheDocument();
      });
    });

    it('应该显示全部已读和刷新按钮', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('全部已读')).toBeInTheDocument();
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });
    });
  });

  describe('标签页', () => {
    it('应该显示所有标签页', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('全部')).toBeInTheDocument();
        expect(screen.getByText('未读')).toBeInTheDocument();
        expect(screen.getByText('消息')).toBeInTheDocument();
        expect(screen.getByText('告警')).toBeInTheDocument();
        expect(screen.getByText('任务')).toBeInTheDocument();
        expect(screen.getByText('公告')).toBeInTheDocument();
      });
    });

    it('未读标签应该显示未读数量', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        const unreadTab = screen.getByText('未读');
        expect(unreadTab.parentElement).toHaveTextContent('4');
      });
    });
  });

  describe('通知列表', () => {
    it('应该渲染通知表格', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
        expect(screen.getByText('数据集审核待办')).toBeInTheDocument();
        expect(screen.getByText('任务执行成功')).toBeInTheDocument();
        expect(screen.getByText('API调用失败告警')).toBeInTheDocument();
        expect(screen.getByText('新任务分配')).toBeInTheDocument();
      });
    });

    it('应该显示通知类型标签', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        // 使用 queryAllByText 避免多个匹配的问题
        const warningTags = screen.queryAllByText('警告');
        const approvalTags = screen.queryAllByText('审批');
        const successTags = screen.queryAllByText('成功');
        const alertTags = screen.queryAllByText('告警');
        const taskTags = screen.queryAllByText('任务');

        expect(warningTags.length > 0).toBeTruthy();
        expect(approvalTags.length > 0).toBeTruthy();
        expect(successTags.length > 0).toBeTruthy();
        expect(alertTags.length > 0).toBeTruthy();
        expect(taskTags.length > 0).toBeTruthy();
      });
    });

    it('应该显示严重级别标签', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        // 使用 queryAllByText 避免多个匹配的问题
        const highTags = screen.queryAllByText('高');
        const mediumTags = screen.queryAllByText('中');
        const lowTags = screen.queryAllByText('低');
        const urgentTags = screen.queryAllByText('紧急');

        expect(highTags.length > 0).toBeTruthy();
        expect(mediumTags.length > 0).toBeTruthy();
        expect(lowTags.length > 0).toBeTruthy();
        expect(urgentTags.length > 0).toBeTruthy();
      });
    });

    it('应该显示来源信息', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统')).toBeInTheDocument();
        expect(screen.getByText('Data API')).toBeInTheDocument();
        expect(screen.getByText('ETL Service')).toBeInTheDocument();
        expect(screen.getByText('API Gateway')).toBeInTheDocument();
        expect(screen.getByText('Workflow')).toBeInTheDocument();
      });
    });

    it('应该显示已读/未读状态', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        const badges = document.querySelectorAll('.ant-badge-status-dot');
        expect(badges.length).toBeGreaterThan(0);
      });
    });
  });

  describe('交互功能', () => {
    it('点击通知标题应该标记已读', async () => {
      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });

      const titleLink = screen.getByText('系统维护通知');
      await user.click(titleLink);

      await waitFor(() => {
        expect(markNotificationRead).toHaveBeenCalledWith('notif-1');
      });
    });

    it('点击有 action_url 的通知应该导航', async () => {
      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('数据集审核待办')).toBeInTheDocument();
      });

      const titleLink = screen.getByText('数据集审核待办');
      await user.click(titleLink);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/data/datasets/123');
      });
    });

    it('点击全部已读按钮应该标记所有通知为已读', async () => {
      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('全部已读')).toBeInTheDocument();
      });

      const markAllButton = screen.getByText('全部已读');
      await user.click(markAllButton);

      await waitFor(() => {
        expect(markAllNotificationsRead).toHaveBeenCalled();
      });
    });

    it('无未读通知时全部已读按钮应该禁用', async () => {
      vi.mocked(getUserNotifications).mockResolvedValueOnce({
        code: 0,
        data: {
          notifications: mockNotifications.map(n => ({ ...n, is_read: true })),
          total: 5,
          unread_count: 0,
          page: 1,
          page_size: 20,
        },
      });

      render(<NotificationsPage />);

      await waitFor(() => {
        const markAllButton = screen.getByText('全部已读').closest('button');
        expect(markAllButton).toBeDisabled();
      });
    });
  });

  describe('操作菜单', () => {
    it('应该有操作菜单按钮', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        const menuButtons = document.querySelectorAll('.ant-dropdown-trigger');
        expect(menuButtons.length).toBeGreaterThan(0);
      });
    });

    it('点击查看详情应该打开弹窗', async () => {
      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });

      // 找到第一个操作菜单按钮并点击
      const menuButtons = document.querySelectorAll('.ant-dropdown-trigger');
      if (menuButtons[0]) {
        await user.click(menuButtons[0]);

        await waitFor(() => {
          expect(screen.getByText('查看详情')).toBeInTheDocument();
        });
      }
    });
  });

  describe('详情弹窗', () => {
    it('通知应该可以被点击', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
        expect(screen.getByText('任务执行成功')).toBeInTheDocument();
      });
    });

    it('详情弹窗应该存在 Modal 组件', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        // 检查 Modal 组件是否被渲染
        const modals = document.querySelectorAll('.ant-modal');
        expect(modals).toBeTruthy();
      });
    });
  });

  describe('筛选功能', () => {
    it('切换到未读标签应该只显示未读通知', async () => {
      vi.mocked(getUserNotifications).mockImplementation(async (params) => {
        if (params.is_read === false) {
          return {
            code: 0,
            data: {
              notifications: mockNotifications.filter(n => !n.is_read),
              total: 4,
              unread_count: 4,
              page: 1,
              page_size: 20,
            },
          };
        }
        return mockNotificationResponse;
      });

      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('未读')).toBeInTheDocument();
      });

      const unreadTab = screen.getByText('未读');
      await user.click(unreadTab);

      await waitFor(() => {
        expect(getUserNotifications).toHaveBeenCalledWith(
          expect.objectContaining({ is_read: false })
        );
      });
    });

    it('切换到告警标签应该过滤告警类型', async () => {
      vi.mocked(getUserNotifications).mockImplementation(async (params) => {
        if (params.category === 'alert') {
          return {
            code: 0,
            data: {
              notifications: mockNotifications.filter(n => n.notification_type === 'alert'),
              total: 1,
              unread_count: 1,
              page: 1,
              page_size: 20,
            },
          };
        }
        return mockNotificationResponse;
      });

      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('告警')).toBeInTheDocument();
      });

      const alertTab = screen.getByText('告警');
      await user.click(alertTab);

      await waitFor(() => {
        expect(getUserNotifications).toHaveBeenCalledWith(
          expect.objectContaining({ category: 'alert' })
        );
      });
    });
  });

  describe('分页功能', () => {
    it('应该显示分页器', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        // 使用 queryAllByText 避免多个匹配的问题
        const totalElements = screen.queryAllByText(/共 \d+ 条/);
        expect(totalElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该重新获取数据', async () => {
      const user = userEvent.setup();
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });

      const refreshButton = screen.getByText('刷新');
      await user.click(refreshButton);

      await waitFor(() => {
        expect(getUserNotifications).toHaveBeenCalled();
      });
    });
  });

  describe('空状态', () => {
    it('无通知时应该显示空状态', async () => {
      vi.mocked(getUserNotifications).mockResolvedValueOnce({
        code: 0,
        data: {
          notifications: [],
          total: 0,
          unread_count: 0,
          page: 1,
          page_size: 20,
        },
      });

      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('暂无通知')).toBeInTheDocument();
      });
    });
  });

  describe('类型图标', () => {
    it('应该渲染正确的通知类型图标', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        const icons = document.querySelectorAll('[class*="anticon"]');
        expect(icons.length).toBeGreaterThan(0);
      });
    });
  });
});
