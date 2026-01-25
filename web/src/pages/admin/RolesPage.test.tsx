import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import RolesPage from './RolesPage';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockRoles = [
  {
    id: 'role-001',
    name: 'admin',
    display_name: '管理员',
    description: '完全访问权限',
    role_type: 'system',
    is_system: true,
    is_active: true,
    priority: 100,
    permissions: [
      { id: 'perm-1', name: 'user:create', code: 'user:create', resource: 'user', operation: 'create' },
      { id: 'perm-2', name: 'user:read', code: 'user:read', resource: 'user', operation: 'read' },
    ],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'role-002',
    name: 'viewer',
    display_name: '查看者',
    description: '只读访问',
    role_type: 'custom',
    is_system: false,
    is_active: true,
    priority: 10,
    permissions: [
      { id: 'perm-2', name: 'user:read', code: 'user:read', resource: 'user', operation: 'read' },
    ],
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'role-003',
    name: 'editor',
    display_name: '编辑者',
    description: '可编辑内容',
    role_type: 'custom',
    is_system: false,
    is_active: false,
    priority: 50,
    permissions: [
      { id: 'perm-2', name: 'user:read', code: 'user:read', resource: 'user', operation: 'read' },
      { id: 'perm-3', name: 'user:update', code: 'user:update', resource: 'user', operation: 'update' },
    ],
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z',
  },
];

const mockPermissions = [
  { id: 'perm-1', name: 'user:create', code: 'user:create', resource: 'user', operation: 'create' },
  { id: 'perm-2', name: 'user:read', code: 'user:read', resource: 'user', operation: 'read' },
  { id: 'perm-3', name: 'user:update', code: 'user:update', resource: 'user', operation: 'update' },
  { id: 'perm-4', name: 'user:delete', code: 'user:delete', resource: 'user', operation: 'delete' },
  { id: 'perm-5', name: 'workflow:create', code: 'workflow:create', resource: 'workflow', operation: 'create' },
  { id: 'perm-6', name: 'workflow:read', code: 'workflow:read', resource: 'workflow', operation: 'read' },
];

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: {} }),
      });
    });
  });

  it('应该正确渲染页面标题', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('角色管理')).toBeInTheDocument();
    });
  });

  it('应该显示创建角色按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建角色/i })).toBeInTheDocument();
    });
  });

  it('加载时应该显示 Spin', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // 永不解析

    render(<RolesPage />);

    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

describe('RolesPage 角色列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示角色名称', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('管理员')).toBeInTheDocument();
      expect(screen.getByText('查看者')).toBeInTheDocument();
      expect(screen.getByText('编辑者')).toBeInTheDocument();
    });
  });

  it('应该显示角色类型', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('系统')).toBeInTheDocument();
      expect(screen.getAllByText('自定义').length).toBe(2);
    });
  });

  it('应该显示角色状态', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getAllByText('启用').length).toBe(2);
      expect(screen.getByText('禁用')).toBeInTheDocument();
    });
  });

  it('应该显示表头', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('角色名称')).toBeInTheDocument();
      expect(screen.getByText('类型')).toBeInTheDocument();
      expect(screen.getByText('状态')).toBeInTheDocument();
      expect(screen.getByText('操作')).toBeInTheDocument();
    });
  });
});

describe('RolesPage 创建角色', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('点击创建按钮应该打开对话框', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建角色/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建角色/i }));

    await waitFor(() => {
      // 检查模态框已打开
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeTruthy();
    });
  });

  it('创建对话框应该显示必要的表单字段', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建角色/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建角色/i }));

    await waitFor(() => {
      expect(screen.getByText('角色标识')).toBeInTheDocument();
      expect(screen.getByText('显示名称')).toBeInTheDocument();
      expect(screen.getByText('描述')).toBeInTheDocument();
    });
  });

  it('创建对话框应该显示权限配置', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新建角色/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建角色/i }));

    await waitFor(() => {
      expect(screen.getByText('权限配置')).toBeInTheDocument();
    });
  });
});

describe('RolesPage 编辑角色', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('每行应该有编辑按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      const editButtons = screen.getAllByRole('button', { name: /编辑/i });
      expect(editButtons.length).toBeGreaterThan(0);
    });
  });

  it('点击编辑按钮应该打开编辑对话框', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('管理员')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /编辑/i });
    await user.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/编辑角色/i)).toBeInTheDocument();
    });
  });
});

describe('RolesPage 删除角色', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === 'DELETE') {
        return Promise.resolve({ ok: true });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('非系统角色应该有删除按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      const deleteButtons = screen.getAllByRole('button', { name: /删除/i });
      // 只有非系统角色有删除按钮（2个）
      expect(deleteButtons.length).toBe(2);
    });
  });
});

describe('RolesPage 刷新功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { roles: mockRoles, total: mockRoles.length } }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: { permissions: mockPermissions } }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: {} }) });
    });
  });

  it('应该显示刷新按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /刷新/i })).toBeInTheDocument();
    });
  });
});
