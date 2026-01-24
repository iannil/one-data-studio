import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RolesPage from './RolesPage';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        'admin.rolesManagement': 'Roles Management',
        'admin.createRole': 'Create Role',
        'admin.editRole': 'Edit Role',
        'admin.deleteRole': 'Delete Role',
        'admin.deleteRoleConfirmation': `Are you sure you want to delete ${options?.name || 'this role'}?`,
        'admin.roleName': 'Role Name',
        'admin.displayName': 'Display Name',
        'admin.description': 'Description',
        'admin.parentRole': 'Parent Role',
        'admin.permissions': 'Permissions',
        'admin.type': 'Type',
        'admin.status': 'Status',
        'common.actions': 'Actions',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.delete': 'Delete',
        'common.edit': 'Edit',
        'common.none': 'None',
        'common.active': 'Active',
        'common.inactive': 'Inactive',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockRoles = [
  {
    id: 'role-001',
    name: 'admin',
    displayName: 'Administrator',
    description: 'Full system access',
    roleType: 'system',
    tenantId: null,
    parentRoleId: null,
    isActive: true,
    isSystem: true,
    priority: 100,
    permissions: [
      { id: 'perm-1', name: 'user:create', displayName: 'Create User', resource: 'user', operation: 'create', scope: 'all', isSystem: true },
      { id: 'perm-2', name: 'user:read', displayName: 'Read User', resource: 'user', operation: 'read', scope: 'all', isSystem: true },
      { id: 'perm-3', name: 'user:update', displayName: 'Update User', resource: 'user', operation: 'update', scope: 'all', isSystem: true },
      { id: 'perm-4', name: 'user:delete', displayName: 'Delete User', resource: 'user', operation: 'delete', scope: 'all', isSystem: true },
    ],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'role-002',
    name: 'viewer',
    displayName: 'Viewer',
    description: 'Read-only access',
    roleType: 'custom',
    tenantId: 'tenant-001',
    parentRoleId: null,
    isActive: true,
    isSystem: false,
    priority: 10,
    permissions: [
      { id: 'perm-2', name: 'user:read', displayName: 'Read User', resource: 'user', operation: 'read', scope: 'all', isSystem: true },
    ],
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
  {
    id: 'role-003',
    name: 'editor',
    displayName: 'Editor',
    description: 'Can edit content',
    roleType: 'custom',
    tenantId: 'tenant-001',
    parentRoleId: null,
    isActive: false,
    isSystem: false,
    priority: 50,
    permissions: [
      { id: 'perm-2', name: 'user:read', displayName: 'Read User', resource: 'user', operation: 'read', scope: 'all', isSystem: true },
      { id: 'perm-3', name: 'user:update', displayName: 'Update User', resource: 'user', operation: 'update', scope: 'all', isSystem: true },
    ],
    createdAt: '2024-01-03T00:00:00Z',
    updatedAt: '2024-01-03T00:00:00Z',
  },
];

const mockPermissions = [
  { id: 'perm-1', name: 'user:create', displayName: 'Create User', resource: 'user', operation: 'create', scope: 'all', isSystem: true },
  { id: 'perm-2', name: 'user:read', displayName: 'Read User', resource: 'user', operation: 'read', scope: 'all', isSystem: true },
  { id: 'perm-3', name: 'user:update', displayName: 'Update User', resource: 'user', operation: 'update', scope: 'all', isSystem: true },
  { id: 'perm-4', name: 'user:delete', displayName: 'Delete User', resource: 'user', operation: 'delete', scope: 'all', isSystem: true },
  { id: 'perm-5', name: 'workflow:create', displayName: 'Create Workflow', resource: 'workflow', operation: 'create', scope: 'all', isSystem: true },
  { id: 'perm-6', name: 'workflow:read', displayName: 'Read Workflow', resource: 'workflow', operation: 'read', scope: 'all', isSystem: true },
];

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    });
  });

  it('应该正确渲染页面标题', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Roles Management')).toBeInTheDocument();
    });
  });

  it('应该显示创建角色按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });
  });

  it('加载时应该显示 CircularProgress', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // 永不解析

    render(<RolesPage />);

    expect(document.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
  });
});

describe('RolesPage 角色列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('应该显示角色名称', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
      expect(screen.getByText('Viewer')).toBeInTheDocument();
      expect(screen.getByText('Editor')).toBeInTheDocument();
    });
  });

  it('应该显示角色类型', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('system')).toBeInTheDocument();
      expect(screen.getAllByText('custom').length).toBe(2);
    });
  });

  it('应该显示角色状态', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBe(2);
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });
  });

  it('应该显示权限标签', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('user:create')).toBeInTheDocument();
      expect(screen.getByText('user:read')).toBeInTheDocument();
    });
  });

  it('应该显示表头', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Role Name')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Permissions')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
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
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('点击创建按钮应该打开对话框', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });
  });

  it('创建对话框应该显示必要的表单字段', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Role Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Display Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    });
  });

  it('创建对话框应该显示权限选择', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      expect(screen.getByText('Permissions')).toBeInTheDocument();
      expect(screen.getByText('User')).toBeInTheDocument();
      expect(screen.getByText('Workflow')).toBeInTheDocument();
    });
  });

  it('保存按钮和取消按钮应该可见', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
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
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('每行应该有编辑按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      const editButtons = document.querySelectorAll('[data-testid="EditIcon"]');
      expect(editButtons.length).toBeGreaterThan(0);
    });
  });

  it('点击编辑按钮应该打开编辑对话框', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    const editButtons = document.querySelectorAll('[data-testid="EditIcon"]');
    if (editButtons[0]) {
      await user.click(editButtons[0].closest('button')!);

      await waitFor(() => {
        expect(screen.getByText('Edit Role')).toBeInTheDocument();
      });
    }
  });
});

describe('RolesPage 删除角色', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string, options?: any) => {
      if (options?.method === 'DELETE') {
        return Promise.resolve({ ok: true });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('非系统角色应该有删除按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      const deleteButtons = document.querySelectorAll('[data-testid="DeleteIcon"]');
      // 只有非系统角色有删除按钮（2个）
      expect(deleteButtons.length).toBe(2);
    });
  });

  it('系统角色不应该有删除按钮', async () => {
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    // Administrator 是系统角色，其行不应该有删除按钮
    const adminRow = screen.getByText('Administrator').closest('tr');
    expect(adminRow?.querySelector('[data-testid="DeleteIcon"]')).not.toBeInTheDocument();
  });

  it('点击删除按钮应该打开确认对话框', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Viewer')).toBeInTheDocument();
    });

    const deleteButtons = document.querySelectorAll('[data-testid="DeleteIcon"]');
    if (deleteButtons[0]) {
      await user.click(deleteButtons[0].closest('button')!);

      await waitFor(() => {
        expect(screen.getByText('Delete Role')).toBeInTheDocument();
      });
    }
  });

  it('确认删除应该调用 API', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText('Viewer')).toBeInTheDocument();
    });

    const deleteButtons = document.querySelectorAll('[data-testid="DeleteIcon"]');
    if (deleteButtons[0]) {
      await user.click(deleteButtons[0].closest('button')!);

      await waitFor(() => {
        expect(screen.getByText('Delete Role')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /Delete/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/roles/'),
          expect.objectContaining({ method: 'DELETE' })
        );
      });
    }
  });
});

describe('RolesPage 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 错误应该显示错误消息', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
    });
  });

  it('错误消息应该可以关闭', async () => {
    const user = userEvent.setup();
    mockFetch.mockRejectedValue(new Error('Network error'));

    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
    });

    const closeButton = document.querySelector('.MuiAlert-action button');
    if (closeButton) {
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText(/Failed to load data/)).not.toBeInTheDocument();
      });
    }
  });
});

describe('RolesPage 权限分组', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('权限应该按资源分组显示', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      // 应该显示按资源分组的权限
      expect(screen.getByText('User')).toBeInTheDocument();
      expect(screen.getByText('Workflow')).toBeInTheDocument();
    });
  });
});

describe('RolesPage 表单验证', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ roles: mockRoles }),
        });
      }
      if (url.includes('/permissions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ permissions: mockPermissions }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('角色名称为必填项', async () => {
    const user = userEvent.setup();
    render(<RolesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Role Name/i)).toBeInTheDocument();
    });

    // 直接点击保存，不填写角色名称
    await user.click(screen.getByRole('button', { name: /Save/i }));

    await waitFor(() => {
      expect(screen.getByText('Role name is required')).toBeInTheDocument();
    });
  });
});
