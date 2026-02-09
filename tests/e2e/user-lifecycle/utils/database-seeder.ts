/**
 * 数据库种子数据工具
 * 用于在测试环境中创建预设的测试数据
 */

import { APIRequestContext } from '@playwright/test';
import { logger } from '../../helpers/logger';
import type { TestRole, UserStatus } from '../fixtures/user-lifecycle.fixture';

// ============================================
// 类型定义
// ============================================

interface SeedConfig {
  users?: boolean;
  roles?: boolean;
  datasets?: boolean;
  workflows?: boolean;
  models?: boolean;
}

interface SeedUser {
  username: string;
  email: string;
  password: string;
  roles: TestRole[];
  status: UserStatus;
}

// ============================================
// 种子用户配置
// ============================================

const SEED_USERS: SeedUser[] = [
  {
    username: 'seed_admin',
    email: 'seed_admin@example.com',
    password: 'Admin1234!',
    roles: ['admin'],
    status: 'active',
  },
  {
    username: 'seed_de',
    email: 'seed_de@example.com',
    password: 'De1234!',
    roles: ['data_engineer'],
    status: 'active',
  },
  {
    username: 'seed_ai',
    email: 'seed_ai@example.com',
    password: 'Ai1234!',
    roles: ['ai_developer'],
    status: 'active',
  },
  {
    username: 'seed_da',
    email: 'seed_da@example.com',
    password: 'Da1234!',
    roles: ['data_analyst'],
    status: 'active',
  },
  {
    username: 'seed_user',
    email: 'seed_user@example.com',
    password: 'User1234!',
    roles: ['user'],
    status: 'active',
  },
  {
    username: 'seed_guest',
    email: 'seed_guest@example.com',
    password: 'Guest1234!',
    roles: ['guest'],
    status: 'active',
  },
];

// ============================================
// 数据库种子类
// ============================================

export class DatabaseSeeder {
  constructor(
    private readonly request: APIRequestContext,
    private readonly baseUrl: string = process.env.BASE_URL || 'http://localhost:3000'
  ) {}

  /**
   * 执行种子数据
   */
  async seed(config: SeedConfig = {}): Promise<void> {
    const defaultConfig: SeedConfig = {
      users: true,
      roles: false,
      datasets: false,
      workflows: false,
      models: false,
      ...config,
    };

    if (defaultConfig.users) {
      await this.seedUsers();
    }

    if (defaultConfig.roles) {
      await this.seedRoles();
    }

    if (defaultConfig.datasets) {
      await this.seedDatasets();
    }

    if (defaultConfig.workflows) {
      await this.seedWorkflows();
    }

    if (defaultConfig.models) {
      await this.seedModels();
    }
  }

  /**
   * 种子用户
   */
  async seedUsers(): Promise<void> {
    logger.info('开始种子用户...');

    for (const user of SEED_USERS) {
      await this.ensureUser(user);
    }

    logger.info('种子用户完成');
  }

  /**
   * 确保用户存在
   */
  private async ensureUser(user: SeedUser): Promise<void> {
    // 检查用户是否已存在
    const checkResponse = await this.request.get(
      `${this.baseUrl}/api/v1/users/by-username/${user.username}`
    );

    if (checkResponse.ok()) {
      const json = await checkResponse.json();
      if (json.code === 0 && json.data) {
        logger.info(`  用户 ${user.username} 已存在`);
        return;
      }
    }

    // 创建用户
    const createResponse = await this.request.post(`${this.baseUrl}/api/v1/users`, {
      data: {
        username: user.username,
        email: user.email,
        password: user.password,
        roles: user.roles,
        status: user.status,
      },
    });

    if (createResponse.ok()) {
      logger.info(`  ✓ 用户 ${user.username} 创建成功`);
    } else {
      console.error(`  ✗ 用户 ${user.username} 创建失败`);
    }
  }

  /**
   * 种子角色
   */
  async seedRoles(): Promise<void> {
    logger.info('开始种子角色...');

    const roles = [
      { name: 'admin', description: '系统管理员', permissions: ['*'] },
      { name: 'data_engineer', description: '数据工程师', permissions: ['data.*', 'development.*'] },
      { name: 'ai_developer', description: 'AI 开发者', permissions: ['ai.*', 'model.*'] },
      { name: 'data_analyst', description: '数据分析师', permissions: ['data.read', 'development.sql'] },
      { name: 'user', description: '普通用户', permissions: ['basic'] },
      { name: 'guest', description: '访客', permissions: ['read'] },
    ];

    for (const role of roles) {
      await this.ensureRole(role);
    }

    logger.info('种子角色完成');
  }

  /**
   * 确保角色存在
   */
  private async ensureRole(role: { name: string; description: string; permissions: string[] }): Promise<void> {
    const checkResponse = await this.request.get(`${this.baseUrl}/api/v1/roles/by-name/${role.name}`);

    if (checkResponse.ok()) {
      const json = await checkResponse.json();
      if (json.code === 0 && json.data) {
        logger.info(`  角色 ${role.name} 已存在`);
        return;
      }
    }

    const createResponse = await this.request.post(`${this.baseUrl}/api/v1/roles`, {
      data: role,
    });

    if (createResponse.ok()) {
      logger.info(`  ✓ 角色 ${role.name} 创建成功`);
    } else {
      console.error(`  ✗ 角色 ${role.name} 创建失败`);
    }
  }

  /**
   * 种子数据集
   */
  async seedDatasets(): Promise<void> {
    logger.info('开始种子数据集...');

    const datasets = [
      { name: '种子数据集 A', description: '用于 E2E 测试的数据集 A', type: 'table' },
      { name: '种子数据集 B', description: '用于 E2E 测试的数据集 B', type: 'view' },
      { name: '种子数据集 C', description: '用于 E2E 测试的数据集 C', type: 'api' },
    ];

    for (const dataset of datasets) {
      await this.ensureDataset(dataset);
    }

    logger.info('种子数据集完成');
  }

  /**
   * 确保数据集存在
   */
  private async ensureDataset(dataset: { name: string; description: string; type: string }): Promise<void> {
    const checkResponse = await this.request.get(`${this.baseUrl}/api/v1/datasets/by-name/${dataset.name}`);

    if (checkResponse.ok()) {
      const json = await checkResponse.json();
      if (json.code === 0 && json.data) {
        logger.info(`  数据集 ${dataset.name} 已存在`);
        return;
      }
    }

    const createResponse = await this.request.post(`${this.baseUrl}/api/v1/datasets`, {
      data: dataset,
    });

    if (createResponse.ok()) {
      logger.info(`  ✓ 数据集 ${dataset.name} 创建成功`);
    }
  }

  /**
   * 种子工作流
   */
  async seedWorkflows(): Promise<void> {
    logger.info('开始种子工作流...');

    const workflows = [
      { name: '种子工作流 A', description: '用于 E2E 测试的工作流 A', type: 'rag' },
      { name: '种子工作流 B', description: '用于 E2E 测试的工作流 B', type: 'agent' },
      { name: '种子工作流 C', description: '用于 E2E 测试的工作流 C', type: 'chain' },
    ];

    for (const workflow of workflows) {
      await this.ensureWorkflow(workflow);
    }

    logger.info('种子工作流完成');
  }

  /**
   * 确保工作流存在
   */
  private async ensureWorkflow(workflow: { name: string; description: string; type: string }): Promise<void> {
    const checkResponse = await this.request.get(`${this.baseUrl}/api/v1/workflows/by-name/${workflow.name}`);

    if (checkResponse.ok()) {
      const json = await checkResponse.json();
      if (json.code === 0 && json.data) {
        logger.info(`  工作流 ${workflow.name} 已存在`);
        return;
      }
    }

    const createResponse = await this.request.post(`${this.baseUrl}/api/v1/workflows`, {
      data: {
        ...workflow,
        config: { nodes: [], edges: [] },
      },
    });

    if (createResponse.ok()) {
      logger.info(`  ✓ 工作流 ${workflow.name} 创建成功`);
    }
  }

  /**
   * 种子模型
   */
  async seedModels(): Promise<void> {
    logger.info('开始种子模型...');

    const models = [
      { name: '种子模型 A', version: '1.0.0', type: 'llm' },
      { name: '种子模型 B', version: '1.0.0', type: 'embedding' },
      { name: '种子模型 C', version: '1.0.0', type: 'rerank' },
    ];

    for (const model of models) {
      await this.ensureModel(model);
    }

    logger.info('种子模型完成');
  }

  /**
   * 确保模型存在
   */
  private async ensureModel(model: { name: string; version: string; type: string }): Promise<void> {
    const checkResponse = await this.request.get(`${this.baseUrl}/api/v1/models/by-name/${model.name}`);

    if (checkResponse.ok()) {
      const json = await checkResponse.json();
      if (json.code === 0 && json.data) {
        logger.info(`  模型 ${model.name} 已存在`);
        return;
      }
    }

    const createResponse = await this.request.post(`${this.baseUrl}/api/v1/models`, {
      data: model,
    });

    if (createResponse.ok()) {
      logger.info(`  ✓ 模型 ${model.name} 创建成功`);
    }
  }

  /**
   * 清理种子数据
   */
  async cleanup(config: SeedConfig = {}): Promise<void> {
    const defaultConfig: SeedConfig = {
      users: true,
      roles: false,
      datasets: true,
      workflows: true,
      models: true,
      ...config,
    };

    if (defaultConfig.users) {
      await this.cleanupUsers();
    }

    if (defaultConfig.datasets) {
      await this.cleanupDatasets();
    }

    if (defaultConfig.workflows) {
      await this.cleanupWorkflows();
    }

    if (defaultConfig.models) {
      await this.cleanupModels();
    }
  }

  /**
   * 清理种子用户
   */
  async cleanupUsers(): Promise<void> {
    logger.info('开始清理种子用户...');

    for (const user of SEED_USERS) {
      const response = await this.request.get(
        `${this.baseUrl}/api/v1/users/by-username/${user.username}`
      );

      if (response.ok()) {
        const json = await response.json();
        if (json.code === 0 && json.data) {
          await this.request.delete(`${this.baseUrl}/api/v1/users/${json.data.id}`);
          logger.info(`  ✓ 用户 ${user.username} 已删除`);
        }
      }
    }

    logger.info('清理种子用户完成');
  }

  /**
   * 清理种子数据集
   */
  async cleanupDatasets(): Promise<void> {
    logger.info('开始清理种子数据集...');

    const response = await this.request.get(`${this.baseUrl}/api/v1/datasets`);
    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.datasets) {
        for (const dataset of json.data.datasets) {
          if (dataset.name.startsWith('种子数据集')) {
            await this.request.delete(`${this.baseUrl}/api/v1/datasets/${dataset.id}`);
            logger.info(`  ✓ 数据集 ${dataset.name} 已删除`);
          }
        }
      }
    }

    logger.info('清理种子数据集完成');
  }

  /**
   * 清理种子工作流
   */
  async cleanupWorkflows(): Promise<void> {
    logger.info('开始清理种子工作流...');

    const response = await this.request.get(`${this.baseUrl}/api/v1/workflows`);
    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.workflows) {
        for (const workflow of json.data.workflows) {
          if (workflow.name.startsWith('种子工作流')) {
            await this.request.delete(`${this.baseUrl}/api/v1/workflows/${workflow.id}`);
            logger.info(`  ✓ 工作流 ${workflow.name} 已删除`);
          }
        }
      }
    }

    logger.info('清理种子工作流完成');
  }

  /**
   * 清理种子模型
   */
  async cleanupModels(): Promise<void> {
    logger.info('开始清理种子模型...');

    const response = await this.request.get(`${this.baseUrl}/api/v1/models`);
    if (response.ok()) {
      const json = await response.json();
      if (json.code === 0 && json.data?.models) {
        for (const model of json.data.models) {
          if (model.name.startsWith('种子模型')) {
            await this.request.delete(`${this.baseUrl}/api/v1/models/${model.id}`);
            logger.info(`  ✓ 模型 ${model.name} 已删除`);
          }
        }
      }
    }

    logger.info('清理种子模型完成');
  }

  /**
   * 重置种子数据（先清理再创建）
   */
  async reset(config: SeedConfig = {}): Promise<void> {
    logger.info('开始重置种子数据...');
    await this.cleanup(config);
    logger.info('');
    await this.seed(config);
    logger.info('重置种子数据完成');
  }
}

/**
 * 创建数据库种子器
 */
export function createDatabaseSeeder(
  request: APIRequestContext,
  baseUrl?: string
): DatabaseSeeder {
  return new DatabaseSeeder(request, baseUrl);
}
