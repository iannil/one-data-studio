/**
 * 角色管理辅助函数
 * 提供角色分配、权限验证等辅助函数
 */

import { Page, expect } from '@playwright/test';
import type { TestRole } from '../fixtures/user-lifecycle.fixture';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 角色定义和权限
// ============================================

/**
 * 角色权限配置
 * 每个角色可以访问的功能模块
 */
export const ROLE_PERMISSIONS: Record<TestRole, {
  canAccessAdmin: boolean;
  canManageUsers: boolean;
  canManageRoles: boolean;
  canManageDatasources: boolean;
  canCreateDatasets: boolean;
  canCreateWorkflows: boolean;
  canCreateModels: boolean;
  canExecuteNotebook: boolean;
  canExecuteSQL: boolean;
  canAccessAIChat: boolean;
  description: string;
}> = {
  admin: {
    canAccessAdmin: true,
    canManageUsers: true,
    canManageRoles: true,
    canManageDatasources: true,
    canCreateDatasets: true,
    canCreateWorkflows: true,
    canCreateModels: true,
    canExecuteNotebook: true,
    canExecuteSQL: true,
    canAccessAIChat: true,
    description: '系统管理员 - 拥有所有权限',
  },
  data_engineer: {
    canAccessAdmin: false,
    canManageUsers: false,
    canManageRoles: false,
    canManageDatasources: true,
    canCreateDatasets: true,
    canCreateWorkflows: false,
    canCreateModels: false,
    canExecuteNotebook: true,
    canExecuteSQL: true,
    canAccessAIChat: true,
    description: '数据工程师 - 数据管理权限',
  },
  ai_developer: {
    canAccessAdmin: false,
    canManageUsers: false,
    canManageRoles: false,
    canManageDatasources: false,
    canCreateDatasets: false,
    canCreateWorkflows: true,
    canCreateModels: true,
    canExecuteNotebook: true,
    canExecuteSQL: false,
    canAccessAIChat: true,
    description: 'AI 开发者 - AI 应用开发权限',
  },
  data_analyst: {
    canAccessAdmin: false,
    canManageUsers: false,
    canManageRoles: false,
    canManageDatasources: false,
    canCreateDatasets: false,
    canCreateWorkflows: false,
    canCreateModels: false,
    canExecuteNotebook: false,
    canExecuteSQL: true,
    canAccessAIChat: false,
    description: '数据分析师 - 只读数据访问',
  },
  user: {
    canAccessAdmin: false,
    canManageUsers: false,
    canManageRoles: false,
    canManageDatasources: false,
    canCreateDatasets: false,
    canCreateWorkflows: false,
    canCreateModels: false,
    canExecuteNotebook: false,
    canExecuteSQL: false,
    canAccessAIChat: true,
    description: '普通用户 - 基础访问权限',
  },
  guest: {
    canAccessAdmin: false,
    canManageUsers: false,
    canManageRoles: false,
    canManageDatasources: false,
    canCreateDatasets: false,
    canCreateWorkflows: false,
    canCreateModels: false,
    canExecuteNotebook: false,
    canExecuteSQL: false,
    canAccessAIChat: false,
    description: '访客 - 最小访问权限',
  },
};

/**
 * 角色优先级（数值越高，权限越高）
 */
export const ROLE_PRIORITY: Record<TestRole, number> = {
  admin: 100,
  data_engineer: 50,
  ai_developer: 50,
  data_analyst: 30,
  user: 10,
  guest: 0,
};

/**
 * 角色显示名称映射
 */
export const ROLE_DISPLAY_NAMES: Record<TestRole, string> = {
  admin: '管理员',
  data_engineer: '数据工程师',
  ai_developer: 'AI 开发者',
  data_analyst: '数据分析师',
  user: '普通用户',
  guest: '访客',
};

// ============================================
// 页面选择器
// ============================================

export const ROLE_SELECTORS = {
  // 角色管理页面
  roleList: '.role-list, .data-table, [class*="table"]',
  roleRow: 'tr[data-row-key], .role-item',
  roleRowByName: (name: string) => `tr:has-text("${name}"), .role-item:has-text("${name}")`,

  // 按钮
  createRoleButton: 'button:has-text("创建"), button:has-text("新建")',
  editRoleButton: 'button:has-text("编辑"), button:has-text("Edit")',
  deleteRoleButton: 'button:has-text("删除"), button:has-text("Delete")',
  permissionButton: 'button:has-text("权限"), button:has-text("Permission")',

  // 表单
  roleNameInput: 'input[name="name"], input[name="role_name"]',
  roleDescInput: 'textarea[name="description"]',

  // 权限面板
  permissionPanel: '.permission-panel, .permission-tree',
  permissionCheckbox: '.ant-tree-checkbox, input[type="checkbox"]',

  // 用户角色标签
  userRoleTag: '.user-role-tag, .ant-tag',
  roleSelect: 'select[name="role"], .role-select',

  // 模态框
  modal: '.ant-modal, .modal',
  modalConfirm: '.ant-modal button:has-text("确定")',
};

// ============================================
// 角色管理 UI 操作
// ============================================

/**
 * 导航到角色管理页面
 */
export async function navigateToRoleManagement(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/admin/roles`);
  await page.waitForLoadState('networkidle');
}

/**
 * 导航到用户详情页面
 */
export async function navigateToUserDetail(page: Page, userId: string): Promise<void> {
  await page.goto(`${BASE_URL}/admin/users/${userId}`);
  await page.waitForLoadState('networkidle');
}

/**
 * 为用户分配角色（通过 UI）
 */
export async function assignRoleViaUI(page: Page, username: string, role: TestRole): Promise<void> {
  // 导航到用户管理页面
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');

  // 找到用户行
  const userRow = page.locator(`tr:has-text("${username}"), .user-item:has-text("${username}")`).first();

  // 点击编辑按钮
  const editButton = userRow.locator('button:has-text("编辑"), button:has-text("Edit")').first();
  await editButton.click();
  await page.waitForTimeout(500);

  // 找到角色选择器
  const roleSelect = page.locator(ROLE_SELECTORS.roleSelect).first();
  if (await roleSelect.isVisible()) {
    await roleSelect.click();
    await page.waitForTimeout(300);

    // 选择角色
    const roleOption = page.locator(`.ant-select-item:has-text("${ROLE_DISPLAY_NAMES[role]}")`).first();
    if (await roleOption.isVisible()) {
      await roleOption.click();
    }
  }

  // 提交表单
  const confirmButton = page.locator(ROLE_SELECTORS.modalConfirm).first();
  await confirmButton.click();
  await page.waitForTimeout(1000);
}

/**
 * 撤销用户角色（通过 UI）
 */
export async function revokeRoleViaUI(page: Page, username: string, role: TestRole): Promise<void> {
  // 导航到用户管理页面
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');

  // 找到用户行
  const userRow = page.locator(`tr:has-text("${username}"), .user-item:has-text("${username}")`).first();

  // 点击编辑按钮
  const editButton = userRow.locator('button:has-text("编辑"), button:has-text("Edit")').first();
  await editButton.click();
  await page.waitForTimeout(500);

  // 找到角色选择器并取消选择
  const roleSelect = page.locator(ROLE_SELECTORS.roleSelect).first();
  if (await roleSelect.isVisible()) {
    await roleSelect.click();
    await page.waitForTimeout(300);

    // 取消选择角色（点击已选中的选项来取消）
    const roleOption = page.locator(`.ant-select-item-option-selected:has-text("${ROLE_DISPLAY_NAMES[role]}")`).first();
    if (await roleOption.isVisible()) {
      await roleOption.click();
    }
  }

  // 提交表单
  const confirmButton = page.locator(ROLE_SELECTORS.modalConfirm).first();
  await confirmButton.click();
  await page.waitForTimeout(1000);
}

/**
 * 获取用户的角色列表（通过 UI）
 */
export async function getUserRolesUI(page: Page, username: string): Promise<TestRole[]> {
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');

  const userRow = page.locator(`tr:has-text("${username}"), .user-item:has-text("${username}")`).first();
  const roleTags = userRow.locator(ROLE_SELECTORS.userRoleTag);

  const roles: TestRole[] = [];
  const count = await roleTags.count();

  for (let i = 0; i < count; i++) {
    const tagText = await roleTags.nth(i).textContent();
    if (tagText) {
      // 映射显示名称到角色类型
      const role = Object.entries(ROLE_DISPLAY_NAMES).find(
        ([, displayName]) => tagText.includes(displayName)
      )?.[0] as TestRole;
      if (role) {
        roles.push(role);
      }
    }
  }

  return roles;
}

/**
 * 验证用户是否拥有指定角色
 */
export async function verifyUserHasRole(page: Page, username: string, role: TestRole): Promise<boolean> {
  const roles = await getUserRolesUI(page, username);
  return roles.includes(role);
}

/**
 * 验证用户不拥有指定角色
 */
export async function verifyUserDoesNotHaveRole(page: Page, username: string, role: TestRole): Promise<boolean> {
  const roles = await getUserRolesUI(page, username);
  return !roles.includes(role);
}

// ============================================
// 权限验证辅助函数
// ============================================

/**
 * 检查角色是否有指定权限
 */
export function roleHasPermission(role: TestRole, permission: keyof typeof ROLE_PERMISSIONS.admin): boolean {
  return ROLE_PERMISSIONS[role][permission];
}

/**
 * 验证角色可以访问指定页面
 */
export async function verifyRoleCanAccessPage(page: Page, role: TestRole, pagePath: string): Promise<boolean> {
  await page.goto(`${BASE_URL}${pagePath}`);
  await page.waitForLoadState('networkidle');

  // 检查是否有权限错误
  const accessDenied = page.locator('.access-denied, .error-page, [class*="forbidden"]');
  const hasAccessDenied = await accessDenied.count() > 0;

  if (hasAccessDenied && await accessDenied.first().isVisible()) {
    return false;
  }

  // 检查页面内容是否正常加载
  const content = page.locator('main, .main-content, [class*="content"]');
  return await content.count() > 0;
}

/**
 * 验证角色不能访问指定页面
 */
export async function verifyRoleCannotAccessPage(page: Page, role: TestRole, pagePath: string): Promise<boolean> {
  await page.goto(`${BASE_URL}${pagePath}`);
  await page.waitForLoadState('networkidle');

  // 检查是否有权限错误或重定向
  const accessDenied = page.locator('.access-denied, .error-page, [class*="forbidden"], .no-permission');
  const hasAccessDenied = await accessDenied.count() > 0;

  if (hasAccessDenied && await accessDenied.first().isVisible()) {
    return true;
  }

  // 检查是否被重定向到首页
  const currentPath = new URL(page.url()).pathname;
  return currentPath === '/' || currentPath === '/dashboard';
}

/**
 * 获取角色的所有权限
 */
export function getRolePermissions(role: TestRole): typeof ROLE_PERMISSIONS.admin {
  return ROLE_PERMISSIONS[role];
}

/**
 * 比较两个角色的优先级
 */
export function compareRolePriority(role1: TestRole, role2: TestRole): number {
  return ROLE_PRIORITY[role1] - ROLE_PRIORITY[role2];
}

/**
 * 获取用户的有效角色（最高优先级）
 */
export function getHighestPriorityRole(roles: TestRole[]): TestRole {
  if (roles.length === 0) {
    return 'guest';
  }

  return roles.reduce((highest, current) =>
    compareRolePriority(current, highest) > 0 ? current : highest
  );
}

/**
 * 检查角色是否可以执行特定操作
 */
export function canRolePerformAction(role: TestRole, action: string): boolean {
  const permissions = ROLE_PERMISSIONS[role];

  const actionMap: Record<string, keyof typeof ROLE_PERMISSIONS.admin> = {
    // 管理类操作
    'manage_users': 'canManageUsers',
    'manage_roles': 'canManageRoles',

    // 数据操作
    'manage_datasources': 'canManageDatasources',
    'create_datasets': 'canCreateDatasets',
    'create_workflows': 'canCreateWorkflows',
    'create_models': 'canCreateModels',

    // 执行操作
    'execute_notebook': 'canExecuteNotebook',
    'execute_sql': 'canExecuteSQL',

    // 访问操作
    'access_admin': 'canAccessAdmin',
    'access_ai_chat': 'canAccessAIChat',
  };

  const permissionKey = actionMap[action];
  if (!permissionKey) {
    return false;
  }

  return permissions[permissionKey];
}

/**
 * 验证角色权限矩阵
 */
export function verifyRolePermissionMatrix(): void {
  // 用于测试的角色权限完整性检查
  const allPermissions = Object.keys(ROLE_PERMISSIONS.admin) as Array<keyof typeof ROLE_PERMISSIONS.admin>;

  for (const role of Object.keys(ROLE_PERMISSIONS) as TestRole[]) {
    const rolePerms = ROLE_PERMISSIONS[role];

    // 验证所有权限字段都存在
    for (const perm of allPermissions) {
      if (typeof rolePerms[perm] !== 'boolean') {
        throw new Error(`角色 ${role} 的权限 ${perm} 不是布尔值`);
      }
    }

    // 验证权限层级关系
    // admin 应该拥有所有权限
    if (role === 'admin') {
      for (const perm of allPermissions) {
        if (!rolePerms[perm]) {
          throw new Error(`管理员角色应该拥有权限 ${perm}`);
        }
      }
    }

    // guest 应该只有最小权限
    if (role === 'guest') {
      const hasPermission = Object.values(rolePerms).some(v => v === true);
      if (hasPermission) {
        // guest 可能有一些基础权限，但不应该有管理权限
        if (rolePerms.canManageUsers || rolePerms.canManageRoles) {
          throw new Error(`访客角色不应该有管理权限`);
        }
      }
    }
  }
}

/**
 * 获取角色可访问的路由列表
 */
export function getAccessibleRoutesForRole(role: TestRole): string[] {
  const routes: string[] = ['/dashboard', '/workspace']; // 所有角色都能访问

  const permissions = ROLE_PERMISSIONS[role];

  if (permissions.canAccessAdmin) {
    routes.push('/admin/users', '/admin/roles', '/admin/groups', '/admin/audit', '/admin/settings');
  }

  if (permissions.canManageDatasources || permissions.canCreateDatasets) {
    routes.push('/data/datasources', '/data/datasets', '/data/metadata');
  }

  if (permissions.canExecuteNotebook || permissions.canExecuteSQL) {
    routes.push('/development/notebook', '/development/sql-lab');
  }

  if (permissions.canCreateWorkflows) {
    routes.push('/ai/workflows', '/ai/prompts', '/ai/knowledge-base');
  }

  if (permissions.canCreateModels) {
    routes.push('/model/experiments', '/model/training', '/model/serving');
  }

  if (permissions.canAccessAIChat) {
    routes.push('/ai/chat');
  }

  return routes;
}

/**
 * 获取角色的测试数据模板
 */
export function getRoleTestData(role: TestRole): {
  username: string;
  email: string;
  password: string;
  roles: TestRole[];
} {
  const timestamp = Date.now();
  return {
    username: `test_${role}_${timestamp}`,
    email: `test_${role}_${timestamp}@example.com`,
    password: 'Test1234!',
    roles: [role],
  };
}
