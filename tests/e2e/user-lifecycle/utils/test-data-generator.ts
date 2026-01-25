/**
 * 测试数据生成器
 * 提供各种类型的测试数据生成工具
 */

import { type TestRole, type UserStatus, type CreateUserRequest } from '../fixtures/user-lifecycle.fixture';

// ============================================
// 用户名生成器
// ============================================

/**
 * 生成随机用户名
 */
export function generateUsername(prefix: string = 'test_user'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * 生成带角色的用户名
 */
export function generateUsernameWithRole(role: TestRole): string {
  const roleShort: Record<TestRole, string> = {
    admin: 'admin',
    data_engineer: 'de',
    ai_developer: 'ai',
    data_analyst: 'da',
    user: 'usr',
    guest: 'gst',
  };
  return generateUsername(roleShort[role]);
}

// ============================================
// 邮箱生成器
// ============================================

/**
 * 生成随机邮箱
 */
export function generateEmail(username?: string): string {
  const name = username || generateUsername();
  return `${name}@example.com`;
}

/**
 * 生成带域名的邮箱
 */
export function generateEmailWithDomain(domain: string, username?: string): string {
  const name = username || generateUsername();
  return `${name}@${domain}`;
}

// ============================================
// 密码生成器
// ============================================

/**
 * 生成强密码
 */
export function generateStrongPassword(length: number = 12): string {
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  const numbers = '0123456789';
  const symbols = '!@#$%^&*';

  let password = '';
  password += uppercase[Math.floor(Math.random() * uppercase.length)];
  password += lowercase[Math.floor(Math.random() * lowercase.length)];
  password += numbers[Math.floor(Math.random() * numbers.length)];
  password += symbols[Math.floor(Math.random() * symbols.length)];

  const allChars = uppercase + lowercase + numbers + symbols;
  for (let i = password.length; i < length; i++) {
    password += allChars[Math.floor(Math.random() * allChars.length)];
  }

  return password.split('').sort(() => Math.random() - 0.5).join('');
}

/**
 * 生成测试密码（固定格式）
 */
export function generateTestPassword(role?: TestRole): string {
  const passwords: Record<TestRole, string> = {
    admin: 'Admin1234!',
    data_engineer: 'De1234!',
    ai_developer: 'Ai1234!',
    data_analyst: 'Da1234!',
    user: 'User1234!',
    guest: 'Guest1234!',
  };
  return role ? passwords[role] : 'Test1234!';
}

// ============================================
// 用户数据生成器
// ============================================

/**
 * 生成基础用户数据
 */
export function generateUserData(overrides?: Partial<CreateUserRequest>): CreateUserRequest {
  const username = generateUsername();
  return {
    username,
    email: generateEmail(username),
    password: generateTestPassword(),
    roles: ['user'],
    status: 'pending',
    ...overrides,
  };
}

/**
 * 生成指定角色的用户数据
 */
export function generateUserDataWithRole(role: TestRole, overrides?: Partial<CreateUserRequest>): CreateUserRequest {
  const username = generateUsernameWithRole(role);
  return {
    username,
    email: generateEmail(username),
    password: generateTestPassword(role),
    roles: [role],
    status: 'active',
    ...overrides,
  };
}

/**
 * 生成指定状态的用户数据
 */
export function generateUserDataWithStatus(status: UserStatus, overrides?: Partial<CreateUserRequest>): CreateUserRequest {
  const username = generateUsername(`user_${status}`);
  return {
    username,
    email: generateEmail(username),
    password: generateTestPassword(),
    roles: ['user'],
    status,
    ...overrides,
  };
}

/**
 * 批量生成用户数据
 */
export function generateBatchUserData(count: number, overrides?: Partial<CreateUserRequest>): CreateUserRequest[] {
  const users: CreateUserRequest[] = [];
  for (let i = 0; i < count; i++) {
    users.push(generateUserData({
      ...overrides,
      username: overrides?.username ? `${overrides.username}_${i}` : undefined,
    }));
  }
  return users;
}

// ============================================
// 数据集生成器
// ============================================

/**
 * 生成数据集名称
 */
export function generateDatasetName(prefix: string = 'test_dataset'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * 生成数据集配置
 */
export function generateDatasetConfig(overrides?: { name?: string; description?: string; type?: string }) {
  return {
    name: overrides?.name || generateDatasetName(),
    description: overrides?.description || 'E2E 测试数据集',
    type: overrides?.type || 'table',
  };
}

// ============================================
// 工作流生成器
// ============================================

/**
 * 生成工作流名称
 */
export function generateWorkflowName(prefix: string = 'test_workflow'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * 生成工作流配置
 */
export function generateWorkflowConfig(overrides?: { name?: string; description?: string; type?: string }) {
  return {
    name: overrides?.name || generateWorkflowName(),
    description: overrides?.description || 'E2E 测试工作流',
    type: overrides?.type || 'rag',
    config: {
      nodes: [],
      edges: [],
    },
  };
}

// ============================================
// 模型生成器
// ============================================

/**
 * 生成模型名称
 */
export function generateModelName(prefix: string = 'test_model'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * 生成模型版本
 */
export function generateModelVersion(): string {
  return `1.${Date.now() % 1000}.0`;
}

/**
 * 生成模型配置
 */
export function generateModelConfig(overrides?: { name?: string; version?: string }) {
  return {
    name: overrides?.name || generateModelName(),
    version: overrides?.version || generateModelVersion(),
  };
}

// ============================================
// 时间戳生成器
// ============================================

/**
 * 生成过去的时间戳
 */
export function generatePastTimestamp(minutesAgo: number = 30): Date {
  const date = new Date();
  date.setMinutes(date.getMinutes() - minutesAgo);
  return date;
}

/**
 * 生成未来的时间戳
 */
export function generateFutureTimestamp(minutesFromNow: number = 30): Date {
  const date = new Date();
  date.setMinutes(date.getMinutes() + minutesFromNow);
  return date;
}

// ============================================
// 随机数据生成器
// ============================================

/**
 * 生成随机字符串
 */
export function generateRandomString(length: number = 10, prefix: string = ''): string {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = prefix;
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * 生成随机数字
 */
export function generateRandomNumber(min: number = 0, max: number = 1000): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 从数组中随机选择
 */
export function randomChoice<T>(array: T[]): T {
  return array[Math.floor(Math.random() * array.length)];
}

/**
 * 从数组中随机选择多个
 */
export function randomChoices<T>(array: T[], count: number): T[] {
  const shuffled = [...array].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, Math.min(count, array.length));
}

// ============================================
// 测试场景数据生成器
// ============================================

/**
 * 生成完整的用户生命周期测试数据
 */
export function generateLifecycleScenarioData() {
  const timestamp = Date.now();
  const baseUsername = `lifecycle_${timestamp}`;

  return {
    newUser: generateUserData({ username: `${baseUsername}_new`, status: 'pending' }),
    activeUser: generateUserDataWithRole('data_engineer', { username: `${baseUsername}_active` }),
    toBeDeactivated: generateUserData({ username: `${baseUsername}_to_deactivate`, status: 'active' }),
    toBeLocked: generateUserData({ username: `${baseUsername}_to_lock`, status: 'active' }),
    toBeDeleted: generateUserData({ username: `${baseUsername}_to_delete`, status: 'active' }),
  };
}

/**
 * 生成角色变更测试数据
 */
export function generateRoleChangeScenarioData() {
  const timestamp = Date.now();
  const baseUsername = `role_change_${timestamp}`;

  return {
    toUpgrade: generateUserData({ username: `${baseUsername}_upgrade`, roles: ['user'] }),
    toDowngrade: generateUserDataWithRole('data_engineer', { username: `${baseUsername}_downgrade` }),
    toMultiRole: generateUserData({ username: `${baseUsername}_multi`, roles: ['user'] }),
    toRevoke: generateUserData({ username: `${baseUsername}_revoke`, roles: ['user', 'data_engineer'] }),
  };
}

/**
 * 生成权限测试场景数据
 */
export function generatePermissionScenarioData() {
  const timestamp = Date.now();
  const baseUsername = `perm_test_${timestamp}`;

  return {
    admin: generateUserDataWithRole('admin', { username: `${baseUsername}_admin` }),
    dataEngineer: generateUserDataWithRole('data_engineer', { username: `${baseUsername}_de` }),
    aiDeveloper: generateUserDataWithRole('ai_developer', { username: `${baseUsername}_ai` }),
    dataAnalyst: generateUserDataWithRole('data_analyst', { username: `${baseUsername}_da` }),
    regularUser: generateUserDataWithRole('user', { username: `${baseUsername}_user` }),
    guest: generateUserDataWithRole('guest', { username: `${baseUsername}_guest` }),
  };
}

// ============================================
// 导出所有生成器
// ============================================

export const TestDataGenerators = {
  // 用户名
  generateUsername,
  generateUsernameWithRole,

  // 邮箱
  generateEmail,
  generateEmailWithDomain,

  // 密码
  generateStrongPassword,
  generateTestPassword,

  // 用户数据
  generateUserData,
  generateUserDataWithRole,
  generateUserDataWithStatus,
  generateBatchUserData,

  // 资源数据
  generateDatasetName,
  generateDatasetConfig,
  generateWorkflowName,
  generateWorkflowConfig,
  generateModelName,
  generateModelVersion,
  generateModelConfig,

  // 时间
  generatePastTimestamp,
  generateFutureTimestamp,

  // 随机数据
  generateRandomString,
  generateRandomNumber,
  randomChoice,
  randomChoices,

  // 场景数据
  generateLifecycleScenarioData,
  generateRoleChangeScenarioData,
  generatePermissionScenarioData,
};
