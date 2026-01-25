/**
 * 权限验证辅助函数
 * 提供各种权限和访问验证的辅助函数
 */

import { Page, APIRequestContext, expect } from '@playwright/test';
import { createApiClient } from '../../helpers/api-client';
import type { TestRole, UserStatus } from '../fixtures/user-lifecycle.fixture';
import { ROLE_PERMISSIONS, canRolePerformAction } from './role-management';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// ============================================
// 类型定义
// ============================================

/**
 * 功能模块
 */
export type FeatureModule =
  | 'admin_users'
  | 'admin_roles'
  | 'admin_groups'
  | 'admin_audit'
  | 'admin_settings'
  | 'data_datasources'
  | 'data_datasets'
  | 'data_metadata'
  | 'data_features'
  | 'data_standards'
  | 'data_lineage'
  | 'data_quality'
  | 'dev_notebook'
  | 'dev_sql_lab'
  | 'dev_etl'
  | 'model_experiments'
  | 'model_training'
  | 'model_serving'
  | 'ai_chat'
  | 'ai_workflows'
  | 'ai_prompts'
  | 'ai_knowledge'
  | 'ai_agents';

/**
 * 权限验证结果
 */
export interface PermissionCheckResult {
  hasAccess: boolean;
  reason?: string;
  httpStatus?: number;
}

/**
 * 路由权限配置
 */
export const ROUTE_PERMISSIONS: Record<FeatureModule, {
  path: string;
  requiredRoles: TestRole[];
  requiredPermissions: string[];
}> = {
  // 系统管理
  admin_users: {
    path: '/admin/users',
    requiredRoles: ['admin'],
    requiredPermissions: ['manage_users'],
  },
  admin_roles: {
    path: '/admin/roles',
    requiredRoles: ['admin'],
    requiredPermissions: ['manage_roles'],
  },
  admin_groups: {
    path: '/admin/groups',
    requiredRoles: ['admin'],
    requiredPermissions: ['manage_users'],
  },
  admin_audit: {
    path: '/admin/audit',
    requiredRoles: ['admin'],
    requiredPermissions: ['access_admin'],
  },
  admin_settings: {
    path: '/admin/settings',
    requiredRoles: ['admin'],
    requiredPermissions: ['access_admin'],
  },

  // 数据管理
  data_datasources: {
    path: '/data/datasources',
    requiredRoles: ['admin', 'data_engineer'],
    requiredPermissions: ['manage_datasources'],
  },
  data_datasets: {
    path: '/data/datasets',
    requiredRoles: ['admin', 'data_engineer', 'ai_developer', 'data_analyst', 'user', 'guest'],
    requiredPermissions: [],
  },
  data_metadata: {
    path: '/data/metadata',
    requiredRoles: ['admin', 'data_engineer', 'ai_developer', 'data_analyst'],
    requiredPermissions: [],
  },
  data_features: {
    path: '/data/features',
    requiredRoles: ['admin', 'data_engineer', 'data_analyst'],
    requiredPermissions: [],
  },
  data_standards: {
    path: '/data/standards',
    requiredRoles: ['admin', 'data_engineer', 'data_analyst'],
    requiredPermissions: [],
  },
  data_lineage: {
    path: '/data/lineage',
    requiredRoles: ['admin', 'data_engineer'],
    requiredPermissions: [],
  },
  data_quality: {
    path: '/data/quality',
    requiredRoles: ['admin', 'data_engineer'],
    requiredPermissions: [],
  },

  // 开发工具
  dev_notebook: {
    path: '/development/notebook',
    requiredRoles: ['admin', 'data_engineer', 'ai_developer'],
    requiredPermissions: ['execute_notebook'],
  },
  dev_sql_lab: {
    path: '/development/sql-lab',
    requiredRoles: ['admin', 'data_engineer', 'ai_developer', 'data_analyst'],
    requiredPermissions: ['execute_sql'],
  },
  dev_etl: {
    path: '/development/etl',
    requiredRoles: ['admin', 'data_engineer'],
    requiredPermissions: [],
  },

  // 模型开发
  model_experiments: {
    path: '/model/experiments',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_models'],
  },
  model_training: {
    path: '/model/training',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_models'],
  },
  model_serving: {
    path: '/model/serving',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_models'],
  },

  // AI 应用
  ai_chat: {
    path: '/ai/chat',
    requiredRoles: ['admin', 'data_engineer', 'ai_developer', 'user'],
    requiredPermissions: ['access_ai_chat'],
  },
  ai_workflows: {
    path: '/ai/workflows',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_workflows'],
  },
  ai_prompts: {
    path: '/ai/prompts',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_workflows'],
  },
  ai_knowledge: {
    path: '/ai/knowledge',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_workflows'],
  },
  ai_agents: {
    path: '/ai/agents',
    requiredRoles: ['admin', 'ai_developer'],
    requiredPermissions: ['create_workflows'],
  },
};

// ============================================
// UI 权限验证
// ============================================

/**
 * 验证用户可以访问指定页面
 */
export async function verifyCanAccessPage(
  page: Page,
  pagePath: string,
  options?: { timeout?: number }
): Promise<PermissionCheckResult> {
  const timeout = options?.timeout || 10000;

  try {
    await page.goto(`${BASE_URL}${pagePath}`, { timeout });
    await page.waitForLoadState('networkidle', { timeout });

    // 检查是否有权限拒绝提示
    const accessDeniedSelectors = [
      '.access-denied',
      '.error-page',
      '[class*="forbidden"]',
      '.no-permission',
      '.unauthorized',
    ];

    for (const selector of accessDeniedSelectors) {
      const element = page.locator(selector).first();
      if (await element.count() > 0 && await element.isVisible()) {
        const text = await element.textContent();
        return {
          hasAccess: false,
          reason: text || '权限不足',
        };
      }
    }

    // 检查页面是否正常加载
    const contentSelectors = [
      'main',
      '.main-content',
      '[class*="content"]',
      '.page-content',
    ];

    for (const selector of contentSelectors) {
      const element = page.locator(selector).first();
      if (await element.count() > 0 && await element.isVisible()) {
        return { hasAccess: true };
      }
    }

    // 如果没有找到明确的拒绝或内容，检查 URL 是否被重定向
    const currentUrl = new URL(page.url());
    const expectedUrl = new URL(`${BASE_URL}${pagePath}`);

    if (currentUrl.pathname !== expectedUrl.pathname && currentUrl.pathname !== '/login') {
      return {
        hasAccess: false,
        reason: `重定向到 ${currentUrl.pathname}`,
      };
    }

    return { hasAccess: true };
  } catch (error) {
    return {
      hasAccess: false,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * 验证用户不能访问指定页面
 */
export async function verifyCannotAccessPage(
  page: Page,
  pagePath: string,
  options?: { timeout?: number }
): Promise<PermissionCheckResult> {
  const result = await verifyCanAccessPage(page, pagePath, options);
  return {
    hasAccess: !result.hasAccess,
    reason: result.reason,
  };
}

/**
 * 验证用户可以执行指定操作
 */
export async function verifyCanPerformAction(
  page: Page,
  action: string,
  options?: { buttonSelector?: string; timeout?: number }
): Promise<boolean> {
  const { buttonSelector, timeout } = options || {};

  // 查找操作按钮
  const selectors = [
    buttonSelector,
    `button:has-text("${action}")`,
    `[data-action="${action}"]`,
    `a:has-text("${action}")`,
  ].filter(Boolean);

  for (const selector of selectors) {
    const element = page.locator(selector as string).first();
    if (await element.count() > 0) {
      // 检查按钮是否可见且可点击
      const isVisible = await element.isVisible();
      const isDisabled = await element.isDisabled().catch(() => false);

      return isVisible && !isDisabled;
    }
  }

  return false;
}

/**
 * 验证用户不能执行指定操作（按钮不存在或被禁用）
 */
export async function verifyCannotPerformAction(
  page: Page,
  action: string,
  options?: { buttonSelector?: string; timeout?: number }
): Promise<boolean> {
  const canPerform = await verifyCanPerformAction(page, action, options);
  return !canPerform;
}

/**
 * 验证功能模块可见性
 */
export async function verifyModuleVisibility(
  page: Page,
  moduleName: string,
  expectedVisible: boolean
): Promise<boolean> {
  const selectors = [
    `[data-module="${moduleName}"]`,
    `a[href*="${moduleName}"]`,
    `.menu-item:has-text("${moduleName}")`,
    `.nav-item:has-text("${moduleName}")`,
  ];

  for (const selector of selectors) {
    const element = page.locator(selector).first();
    if (await element.count() > 0) {
      const isVisible = await element.isVisible();
      return expectedVisible ? isVisible : !isVisible;
    }
  }

  return !expectedVisible;
}

// ============================================
// API 权限验证
// ============================================

/**
 * 验证 API 访问权限
 */
export async function verifyApiAccess(
  request: APIRequestContext,
  apiPath: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  options?: { body?: any; headers?: Record<string, string> }
): Promise<PermissionCheckResult> {
  const url = `${BASE_URL}${apiPath}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options?.headers,
  };

  try {
    const response = await request.fetch(url, {
      method,
      headers,
      data: options?.body,
    });

    const status = response.status();

    // 200-299 表示有权限
    if (status >= 200 && status < 300) {
      return { hasAccess: true, httpStatus: status };
    }

    // 403 表示权限不足
    if (status === 403) {
      return {
        hasAccess: false,
        reason: 'API 返回 403 Forbidden',
        httpStatus: status,
      };
    }

    // 401 表示未认证
    if (status === 401) {
      return {
        hasAccess: false,
        reason: 'API 返回 401 Unauthorized',
        httpStatus: status,
      };
    }

    // 其他状态码
    return {
      hasAccess: false,
      reason: `API 返回 ${status}`,
      httpStatus: status,
    };
  } catch (error) {
    return {
      hasAccess: false,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * 验证多个 API 端点的访问权限
 */
export async function verifyMultipleApiAccess(
  request: APIRequestContext,
  apiEndpoints: Array<{
    path: string;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    body?: any;
  }>
): Promise<Map<string, PermissionCheckResult>> {
  const results = new Map<string, PermissionCheckResult>();

  for (const endpoint of apiEndpoints) {
    const key = `${endpoint.method || 'GET'} ${endpoint.path}`;
    const result = await verifyApiAccess(
      request,
      endpoint.path,
      endpoint.method,
      { body: endpoint.body }
    );
    results.set(key, result);
  }

  return results;
}

// ============================================
// 角色权限矩阵验证
// ============================================

/**
 * 验证角色是否应该能访问指定模块
 */
export function shouldRoleAccessModule(role: TestRole, module: FeatureModule): boolean {
  const config = ROUTE_PERMISSIONS[module];
  return config.requiredRoles.includes(role);
}

/**
 * 验证角色的完整权限矩阵
 */
export async function verifyRolePermissionMatrix(
  page: Page,
  role: TestRole
): Promise<{
  module: FeatureModule;
  path: string;
  expectedAccess: boolean;
  actualAccess: boolean;
  passed: boolean;
}[]> {
  const results: Array<{
    module: FeatureModule;
    path: string;
    expectedAccess: boolean;
    actualAccess: boolean;
    passed: boolean;
  }> = [];

  for (const [module, config] of Object.entries(ROUTE_PERMISSIONS)) {
    const expectedAccess = shouldRoleAccessModule(role, module as FeatureModule);
    const actualResult = await verifyCanAccessPage(page, config.path);

    results.push({
      module: module as FeatureModule,
      path: config.path,
      expectedAccess,
      actualAccess: actualResult.hasAccess,
      passed: expectedAccess === actualResult.hasAccess,
    });
  }

  return results;
}

/**
 * 获取权限验证报告
 */
export function generatePermissionReport(
  results: Array<{
    module: FeatureModule;
    path: string;
    expectedAccess: boolean;
    actualAccess: boolean;
    passed: boolean;
  }>
): {
  total: number;
  passed: number;
  failed: number;
  failures: Array<{ module: FeatureModule; path: string; expected: boolean; actual: boolean }>;
} {
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed);

  return {
    total: results.length,
    passed,
    failed: failed.length,
    failures: failed.map(f => ({
      module: f.module,
      path: f.path,
      expected: f.expectedAccess,
      actual: f.actualAccess,
    })),
  };
}

// ============================================
// 用户状态验证
// ============================================

/**
 * 验证用户登录状态
 */
export async function verifyUserLoggedIn(page: Page): Promise<boolean> {
  // 检查是否有用户信息
  const userInfo = await page.evaluate(() => {
    const info = localStorage.getItem('user_info');
    return info ? JSON.parse(info) : null;
  });

  if (!userInfo) {
    return false;
  }

  // 检查页面是否有登录后的元素
  const loggedInSelectors = [
    '.user-avatar',
    '.user-profile',
    '[data-testid="user-menu"]',
    '.logout-button',
  ];

  for (const selector of loggedInSelectors) {
    const element = page.locator(selector).first();
    if (await element.count() > 0 && await element.isVisible()) {
      return true;
    }
  }

  return false;
}

/**
 * 验证用户未登录状态
 */
export async function verifyUserNotLoggedIn(page: Page): Promise<boolean> {
  return !(await verifyUserLoggedIn(page));
}

/**
 * 验证用户状态
 */
export async function verifyUserStatus(
  page: Page,
  username: string,
  expectedStatus: UserStatus
): Promise<boolean> {
  await page.goto(`${BASE_URL}/admin/users`);
  await page.waitForLoadState('networkidle');

  const userRow = page.locator(`tr:has-text("${username}"), .user-item:has-text("${username}")`).first();
  const statusTag = userRow.locator('.ant-tag, [class*="status"]').first();

  if (await statusTag.isVisible()) {
    const statusText = await statusTag.textContent();
    return statusText?.toLowerCase().includes(expectedStatus) ?? false;
  }

  return false;
}

// ============================================
// 批量权限验证
// ============================================

/**
 * 批量验证多个页面的访问权限
 */
export async function verifyMultiplePageAccess(
  page: Page,
  paths: string[]
): Promise<Map<string, PermissionCheckResult>> {
  const results = new Map<string, PermissionCheckResult>();

  for (const path of paths) {
    const result = await verifyCanAccessPage(page, path);
    results.set(path, result);
  }

  return results;
}

/**
 * 验证所有指定角色可访问的页面
 */
export async function verifyAllAccessiblePagesForRole(
  page: Page,
  role: TestRole
): Promise<{
  accessible: string[];
  inaccessible: string[];
  unexpected: string[];
}> {
  const allPaths = Object.values(ROUTE_PERMISSIONS).map(c => c.path);
  const results = await verifyMultiplePageAccess(page, allPaths);

  const accessible: string[] = [];
  const inaccessible: string[] = [];
  const unexpected: string[] = [];

  for (const [path, result] of results.entries()) {
    const shouldAccess = Object.values(ROUTE_PERMISSIONS).some(
      c => c.path === path && c.requiredRoles.includes(role)
    );

    if (result.hasAccess) {
      if (shouldAccess) {
        accessible.push(path);
      } else {
        unexpected.push(path);
      }
    } else {
      if (!shouldAccess) {
        inaccessible.push(path);
      } else {
        unexpected.push(path);
      }
    }
  }

  return { accessible, inaccessible, unexpected };
}

// ============================================
// 辅助函数
// ============================================

/**
 * 等待并验证页面权限提示
 */
export async function waitForPermissionMessage(
  page: Page,
  expectedType: 'access-denied' | 'unauthorized' | 'success'
): Promise<boolean> {
  const selectors = {
    'access-denied': ['.access-denied', '.no-permission', '[class*="forbidden"]'],
    'unauthorized': ['.unauthorized', '.login-required', '[class*="unauthorized"]'],
    'success': ['.main-content', 'main', '[class*="content"]'],
  };

  const targetSelectors = selectors[expectedType];

  for (const selector of targetSelectors) {
    try {
      await page.waitForSelector(selector, { timeout: 5000 });
      return true;
    } catch {
      continue;
    }
  }

  return false;
}

/**
 * 获取当前登录用户信息
 */
export async function getCurrentUserInfo(page: Page): Promise<{
  userId?: string;
  username?: string;
  roles?: string[];
} | null> {
  const userInfo = await page.evaluate(() => {
    const info = localStorage.getItem('user_info');
    return info ? JSON.parse(info) : null;
  });

  return userInfo;
}
