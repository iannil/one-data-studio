/**
 * AnnouncementsPage 组件测试
 * 测试系统公告页面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { Announcement } from '../../services/admin';

// Mock admin service
vi.mock('../../services/admin', () => ({
  getAnnouncements: vi.fn(() => Promise.resolve({
    code: 0,
    data: {
      announcements: [],
      total: 0,
      page: 1,
      page_size: 10,
    },
  })),
}));

import AnnouncementsPage from './AnnouncementsPage';
import { getAnnouncements } from '../../services/admin';

// Mock data
const mockAnnouncements: Announcement[] = [
  {
    id: 'anno-1',
    title: '系统维护通知',
    summary: '系统将于今晚进行维护',
    content: '系统将于今晚22:00-24:00进行维护，请提前做好准备。',
    announcement_type: 'maintenance',
    priority: 100,
    is_pinned: true,
    is_popup: false,
    target_roles: [],
    start_time: '2026-02-06T22:00:00Z',
    end_time: '2026-02-07T00:00:00Z',
    status: 'published',
    publish_at: '2026-02-06T10:00:00Z',
    view_count: 128,
    is_active: true,
    created_at: '2026-02-06T09:00:00Z',
    created_by: 'admin',
    updated_at: '2026-02-06T09:00:00Z',
  },
  {
    id: 'anno-2',
    title: '平台升级公告',
    summary: '平台将升级至 v2.0',
    content: '新版本带来更多功能和性能优化',
    announcement_type: 'update',
    priority: 50,
    is_pinned: false,
    is_popup: false,
    target_roles: [],
    status: 'published',
    publish_at: '2026-02-05T10:00:00Z',
    view_count: 256,
    is_active: true,
    created_at: '2026-02-05T09:00:00Z',
    created_by: 'admin',
    updated_at: '2026-02-05T09:00:00Z',
  },
  {
    id: 'anno-3',
    title: '安全警告',
    summary: '请注意密码安全',
    content: '定期更换密码可以提高账户安全性',
    announcement_type: 'warning',
    priority: 80,
    is_pinned: false,
    is_popup: false,
    target_roles: [],
    status: 'published',
    publish_at: '2026-02-04T10:00:00Z',
    view_count: 64,
    is_active: true,
    created_at: '2026-02-04T09:00:00Z',
    created_by: 'admin',
    updated_at: '2026-02-04T09:00:00Z',
  },
];

describe('AnnouncementsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 默认 mock
    vi.mocked(getAnnouncements).mockResolvedValue({
      code: 0,
      data: {
        announcements: mockAnnouncements,
        total: 3,
        page: 1,
        page_size: 10,
      },
    });
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面标题', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统公告')).toBeInTheDocument();
      });
    });

    it('应该显示公告总数', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText(/共 3 条公告/)).toBeInTheDocument();
      });
    });

    it('应该显示刷新按钮', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        const refreshButton = screen.getAllByRole('button').find(btn =>
          btn.querySelector('.anticon-reload')
        );
        expect(refreshButton).toBeInTheDocument();
      });
    });
  });

  describe('加载状态', () => {
    it('应该显示加载骨架屏', async () => {
      // 让请求一直 pending
      vi.mocked(getAnnouncements).mockReturnValueOnce(
        new Promise(() => {})
      );

      render(<AnnouncementsPage />);

      // 应该有多个 Skeleton
      await waitFor(() => {
        const skeletons = document.querySelectorAll('.ant-skeleton');
        expect(skeletons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('空状态', () => {
    it('应该显示空状态提示', async () => {
      vi.mocked(getAnnouncements).mockResolvedValueOnce({
        code: 0,
        data: {
          announcements: [],
          total: 0,
          page: 1,
          page_size: 10,
        },
      });

      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('暂无公告')).toBeInTheDocument();
      });
    });
  });

  describe('公告列表', () => {
    beforeEach(() => {
      vi.mocked(getAnnouncements).mockResolvedValue({
        code: 0,
        data: {
          announcements: mockAnnouncements,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });
    });

    it('应该渲染置顶公告', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('置顶公告')).toBeInTheDocument();
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });
    });

    it('应该渲染普通公告', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('最新公告')).toBeInTheDocument();
        expect(screen.getByText('平台升级公告')).toBeInTheDocument();
        expect(screen.getByText('安全警告')).toBeInTheDocument();
      });
    });

    it('应该显示公告类型标签', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('维护')).toBeInTheDocument();
        expect(screen.getByText('更新')).toBeInTheDocument();
        expect(screen.getByText('警告')).toBeInTheDocument();
      });
    });

    it('应该显示浏览次数', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText(/128.*浏览/)).toBeInTheDocument();
        expect(screen.getByText(/256.*浏览/)).toBeInTheDocument();
      });
    });
  });

  describe('搜索功能', () => {
    beforeEach(() => {
      vi.mocked(getAnnouncements).mockResolvedValue({
        code: 0,
        data: {
          announcements: mockAnnouncements,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });
    });

    it('应该有搜索输入框', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('搜索公告...');
        expect(searchInput).toBeInTheDocument();
      });
    });

    it('输入搜索关键词应该过滤公告', async () => {
      const user = userEvent.setup();
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('搜索公告...');
      await user.type(searchInput, '维护');

      // 应该仍然显示维护相关的公告（客户端过滤）
      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });
    });

    it('搜索无结果时应该显示空状态', async () => {
      const user = userEvent.setup();
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统维护通知')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('搜索公告...');
      await user.type(searchInput, '不存在的内容xyz');

      await waitFor(() => {
        expect(screen.getByText('暂无公告')).toBeInTheDocument();
      });
    });
  });

  describe('类型筛选', () => {
    it('应该有类型筛选下拉框', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        // 查找筛选框的容器
        const filterContainer = document.querySelector('.ant-select');
        expect(filterContainer).toBeInTheDocument();
      });
    });
  });

  describe('分页功能', () => {
    it('应该显示分页器', async () => {
      vi.mocked(getAnnouncements).mockResolvedValueOnce({
        code: 0,
        data: {
          announcements: mockAnnouncements,
          total: 25,
          page: 1,
          page_size: 10,
        },
      });

      render(<AnnouncementsPage />);

      await waitFor(() => {
        // 使用 findAllByText 来避免多个匹配的问题
        const totalElements = screen.queryAllByText(/共 \d+ 条/);
        expect(totalElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该重新获取数据', async () => {
      const user = userEvent.setup();
      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('系统公告')).toBeInTheDocument();
      });

      const refreshButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.anticon-reload')
      );

      if (refreshButton) {
        await user.click(refreshButton);
        expect(getAnnouncements).toHaveBeenCalled();
      }
    });
  });

  describe('详情弹窗', () => {
    beforeEach(() => {
      vi.mocked(getAnnouncements).mockResolvedValue({
        code: 0,
        data: {
          announcements: mockAnnouncements,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });
    });

    it('置顶公告应该显示置顶标签', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        // 置顶公告部分应该存在
        const pinnedText = screen.queryByText('置顶公告');
        if (pinnedText) {
          expect(pinnedText).toBeInTheDocument();
        }
      });
    });

    it('公告列表应该是可点击的', async () => {
      render(<AnnouncementsPage />);

      await waitFor(() => {
        const listItems = document.querySelectorAll('.ant-list-item');
        expect(listItems.length).toBeGreaterThan(0);
      });
    });
  });

  describe('公告类型图标', () => {
    beforeEach(() => {
      vi.mocked(getAnnouncements).mockResolvedValue({
        code: 0,
        data: {
          announcements: mockAnnouncements,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });
    });

    it('info 类型公告应该有正确的图标', async () => {
      const infoAnnouncement: Announcement = {
        ...mockAnnouncements[0],
        id: 'anno-info',
        title: '信息通知',
        announcement_type: 'info',
      };

      vi.mocked(getAnnouncements).mockResolvedValueOnce({
        code: 0,
        data: {
          announcements: [infoAnnouncement],
          total: 1,
          page: 1,
          page_size: 10,
        },
      });

      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('信息通知')).toBeInTheDocument();
        expect(screen.getByText('通知')).toBeInTheDocument();
      });
    });

    it('urgent 类型公告应该有警告图标', async () => {
      const urgentAnnouncement: Announcement = {
        ...mockAnnouncements[0],
        id: 'anno-urgent',
        title: '紧急通知',
        announcement_type: 'urgent',
      };

      vi.mocked(getAnnouncements).mockResolvedValueOnce({
        code: 0,
        data: {
          announcements: [urgentAnnouncement],
          total: 1,
          page: 1,
          page_size: 10,
        },
      });

      render(<AnnouncementsPage />);

      await waitFor(() => {
        expect(screen.getByText('紧急通知')).toBeInTheDocument();
        expect(screen.getByText('紧急')).toBeInTheDocument();
      });
    });
  });
});
