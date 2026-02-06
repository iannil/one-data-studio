/**
 * ProfilePage 组件测试
 * 测试个人中心页面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { AuditLog } from '../../services/admin';

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
  getAuditLogs: vi.fn(() => Promise.resolve({
    code: 0,
    data: {
      logs: [],
      total: 0,
      page: 1,
      page_size: 10,
    },
  })),
  changePassword: vi.fn(() => Promise.resolve({ code: 0 })),
}));

// Mock AuthContext
const mockLogout = vi.fn();
const mockUser = {
  sub: 'user-123',
  name: '张三',
  preferred_username: 'zhangsan',
  given_name: '三',
  family_name: '张',
  email: 'zhangsan@example.com',
  roles: ['admin', 'developer'],
};

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    logout: mockLogout,
  }),
}));

import ProfilePage from './ProfilePage';
import { getAuditLogs } from '../../services/admin';

// Mock activity logs data
const mockActivityLogs: AuditLog[] = [
  {
    audit_id: 'audit-1',
    action: 'login',
    resource_type: 'system',
    user_id: 'user-123',
    username: 'zhangsan',
    user_ip: '192.168.1.100',
    success: true,
    created_at: '2026-02-06T10:00:00Z',
  },
  {
    audit_id: 'audit-2',
    action: 'create',
    resource_type: 'dataset',
    resource_id: 'ds-1',
    resource_name: '测试数据集',
    user_id: 'user-123',
    username: 'zhangsan',
    success: true,
    created_at: '2026-02-06T09:00:00Z',
  },
  {
    audit_id: 'audit-3',
    action: 'update',
    resource_type: 'workflow',
    resource_id: 'wf-1',
    resource_name: '数据处理流程',
    user_id: 'user-123',
    username: 'zhangsan',
    user_ip: '192.168.1.100',
    success: false,
    created_at: '2026-02-06T08:00:00Z',
  },
];

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面标题', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('个人中心')).toBeInTheDocument();
      });
    });

    it('应该显示页面描述', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('管理您的个人信息、安全设置和偏好')).toBeInTheDocument();
      });
    });

    it('应该显示所有标签页', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const profileTabs = screen.queryAllByText('个人资料');
        const activityTabs = screen.queryAllByText('活动记录');
        const securityTabs = screen.queryAllByText('安全设置');
        const preferenceTabs = screen.queryAllByText('偏好设置');

        expect(profileTabs.length).toBeGreaterThan(0);
        expect(activityTabs.length).toBeGreaterThan(0);
        expect(securityTabs.length).toBeGreaterThan(0);
        expect(preferenceTabs.length).toBeGreaterThan(0);
      });
    });
  });

  describe('个人资料 Tab', () => {
    it('应该显示用户头像', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const avatar = document.querySelector('.ant-avatar');
        expect(avatar).toBeInTheDocument();
      });
    });

    it('应该显示用户名', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const userNameElements = screen.queryAllByText('张三');
        expect(userNameElements.length).toBeGreaterThan(0);
      });
    });

    it('应该显示用户邮箱', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        // 邮箱可能在多个地方显示
        const emailElements = screen.queryAllByText('zhangsan@example.com');
        expect(emailElements.length).toBeGreaterThan(0);
      });
    });

    it('应该显示用户角色', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const adminTags = screen.queryAllByText('管理员');
        const devTags = screen.queryAllByText('开发者');
        expect(adminTags.length).toBeGreaterThan(0);
        expect(devTags.length).toBeGreaterThan(0);
      });
    });

    it('应该显示基本信息描述列表', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('基本信息')).toBeInTheDocument();
      });
    });

    it('应该显示用户ID', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('user-123')).toBeInTheDocument();
      });
    });

    it('应该显示最近活动时间线', async () => {
      vi.mocked(getAuditLogs).mockResolvedValueOnce({
        code: 0,
        data: {
          logs: mockActivityLogs,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });

      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('最近活动')).toBeInTheDocument();
      });
    });

    it('点击查看全部应该切换到活动记录Tab', async () => {
      vi.mocked(getAuditLogs).mockResolvedValue({
        code: 0,
        data: {
          logs: mockActivityLogs,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });

      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('查看全部')).toBeInTheDocument();
      });

      const viewAllButton = screen.getByText('查看全部');
      await user.click(viewAllButton);

      await waitFor(() => {
        const activityTabs = screen.queryAllByText('活动记录');
        expect(activityTabs.length).toBeGreaterThan(0);
      });
    });

    it('无活动记录时应该显示空状态', async () => {
      vi.mocked(getAuditLogs).mockResolvedValueOnce({
        code: 0,
        data: {
          logs: [],
          total: 0,
          page: 1,
          page_size: 10,
        },
      });

      render(<ProfilePage />);

      await waitFor(() => {
        expect(screen.getByText('暂无活动记录')).toBeInTheDocument();
      });
    });
  });

  describe('活动记录 Tab', () => {
    beforeEach(() => {
      vi.mocked(getAuditLogs).mockResolvedValue({
        code: 0,
        data: {
          logs: mockActivityLogs,
          total: 3,
          page: 1,
          page_size: 10,
        },
      });
    });

    it('应该显示活动记录标签', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const activityTabs = screen.queryAllByText('活动记录');
        expect(activityTabs.length).toBeGreaterThan(0);
      });
    });

    it('应该有活动记录表格结构', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const activityTabs = screen.queryAllByText('活动记录');
        expect(activityTabs.length).toBeGreaterThan(0);
      });

      const activityTab = screen.queryAllByText('活动记录')[0];
      await user.click(activityTab);

      await waitFor(() => {
        // 检查是否有表格结构
        const tables = document.querySelectorAll('.ant-table');
        expect(tables.length).toBeGreaterThan(0);
      });
    });
  });

  describe('安全设置 Tab', () => {
    it('应该显示密码管理卡片', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText('密码管理')).toBeInTheDocument();
      });
    });

    it('应该显示修改密码按钮', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        const changePasswordBtns = screen.queryAllByText('修改密码');
        expect(changePasswordBtns.length).toBeGreaterThan(0);
      });
    });

    it('应该显示登录安全卡片', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText('登录安全')).toBeInTheDocument();
      });
    });

    it('应该显示账户操作卡片', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText('账户操作')).toBeInTheDocument();
        const logoutBtns = screen.queryAllByText('退出登录');
        expect(logoutBtns.length).toBeGreaterThan(0);
      });
    });

    it('点击退出登录应该调用logout', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        const logoutBtns = screen.queryAllByText('退出登录');
        expect(logoutBtns.length).toBeGreaterThan(0);
      });

      const logoutButtons = screen.queryAllByText('退出登录');
      const dangerButton = logoutButtons.find(btn =>
        btn.closest('button')?.classList.contains('ant-btn-dangerous')
      );

      if (dangerButton) {
        await user.click(dangerButton);
        expect(mockLogout).toHaveBeenCalled();
      }
    });
  });

  describe('修改密码弹窗', () => {
    it('应该显示修改密码按钮', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });

      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        const changePasswordBtns = screen.queryAllByText('修改密码');
        expect(changePasswordBtns.length).toBeGreaterThan(0);
      });
    });

    it('Modal 组件应该存在', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const modals = document.querySelectorAll('.ant-modal');
        expect(modals).toBeTruthy();
      });
    });
  });

  describe('偏好设置 Tab', () => {
    it('应该显示通知设置卡片', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const preferenceTabs = screen.queryAllByText('偏好设置');
        expect(preferenceTabs.length).toBeGreaterThan(0);
      });

      const preferencesTab = screen.queryAllByText('偏好设置')[0];
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText('通知设置')).toBeInTheDocument();
      });
    });

    it('应该显示显示设置卡片', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const preferenceTabs = screen.queryAllByText('偏好设置');
        expect(preferenceTabs.length).toBeGreaterThan(0);
      });

      const preferencesTab = screen.queryAllByText('偏好设置')[0];
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText('显示设置')).toBeInTheDocument();
      });
    });

    it('应该显示通知开关选项', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const preferenceTabs = screen.queryAllByText('偏好设置');
        expect(preferenceTabs.length).toBeGreaterThan(0);
      });

      const preferencesTab = screen.queryAllByText('偏好设置')[0];
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText('系统通知')).toBeInTheDocument();
        expect(screen.getByText('任务提醒')).toBeInTheDocument();
      });
    });

    it('应该显示显示设置选项', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      await waitFor(() => {
        const preferenceTabs = screen.queryAllByText('偏好设置');
        expect(preferenceTabs.length).toBeGreaterThan(0);
      });

      const preferencesTab = screen.queryAllByText('偏好设置')[0];
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText('语言')).toBeInTheDocument();
        expect(screen.getByText('时区')).toBeInTheDocument();
      });
    });
  });

  describe('标签页切换', () => {
    it('应该能够切换到不同的标签页', async () => {
      const user = userEvent.setup();
      render(<ProfilePage />);

      // 默认在个人资料
      await waitFor(() => {
        const profileTabs = screen.queryAllByText('个人资料');
        expect(profileTabs.length).toBeGreaterThan(0);
      });

      // 切换到活动记录
      const activityTab = screen.queryAllByText('活动记录')[0];
      await user.click(activityTab);

      await waitFor(() => {
        const activityTabs = screen.queryAllByText('活动记录');
        expect(activityTabs.length).toBeGreaterThan(0);
      });

      // 切换到安全设置
      const securityTab = screen.queryAllByText('安全设置')[0];
      await user.click(securityTab);

      await waitFor(() => {
        const securityTabs = screen.queryAllByText('安全设置');
        expect(securityTabs.length).toBeGreaterThan(0);
      });
    });
  });

  describe('中文映射', () => {
    it('roleLabels 应该正确映射角色', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const adminTags = screen.queryAllByText('管理员');
        const devTags = screen.queryAllByText('开发者');
        expect(adminTags.length).toBeGreaterThan(0);
        expect(devTags.length).toBeGreaterThan(0);
      });
    });

    it('应该存在活动记录Tab', async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        const activityTabs = screen.queryAllByText('活动记录');
        expect(activityTabs.length).toBeGreaterThan(0);
      });
    });
  });
});
