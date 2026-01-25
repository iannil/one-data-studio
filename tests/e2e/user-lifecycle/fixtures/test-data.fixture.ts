/**
 * 测试数据管理 Fixture
 * 用于创建和管理测试数据集、工作流、模型等
 */

import { test as base, APIRequestContext } from '@playwright/test';
import { createApiClient } from '../../helpers/api-client';

// ============================================
// 类型定义
// ============================================

/**
 * 测试数据集
 */
export interface TestDataset {
  id: string;
  name: string;
  description?: string;
  type: string;
  datasource_id: string;
  owner_id: string;
  created_at: string;
}

/**
 * 测试工作流
 */
export interface TestWorkflow {
  id: string;
  name: string;
  description?: string;
  type: string;
  config: Record<string, any>;
  owner_id: string;
  created_at: string;
}

/**
 * 测试模型
 */
export interface TestModel {
  id: string;
  name: string;
  version: string;
  experiment_id?: string;
  owner_id: string;
  created_at: string;
}

/**
 * API 响应包装
 */
interface ApiResponse<T = any> {
  code: number;
  message?: string;
  data?: T;
  error?: string;
}

// ============================================
// 测试数据管理类
// ============================================

export class TestDataManager {
  private apiClient: any;
  private bishengClient: any;
  private cubeClient: any;
  private createdDatasets: string[] = [];
  private createdWorkflows: string[] = [];
  private createdModels: string[] = [];

  constructor(request: APIRequestContext) {
    this.apiClient = createApiClient(request, 'alldata');
    this.bishengClient = createApiClient(request, 'bisheng');
    this.cubeClient = createApiClient(request, 'cube');
  }

  // ============================================
  // 数据集管理
  // ============================================

  /**
   * 创建测试数据集
   */
  async createTestDataset(data: {
    name: string;
    description?: string;
    datasource_id?: string;
    owner_id: string;
  }): Promise<TestDataset> {
    const response = await this.apiClient.post<ApiResponse<TestDataset>>('/api/v1/datasets', {
      name: data.name,
      description: data.description || `E2E 测试数据集: ${data.name}`,
      datasource_id: data.datasource_id || 'test-datasource-1',
    });

    if (response.code !== 0 || !response.data) {
      throw new Error(`创建数据集失败: ${response.message || response.error}`);
    }

    const dataset = response.data;
    this.createdDatasets.push(dataset.id);

    return dataset;
  }

  /**
   * 获取数据集
   */
  async getDataset(datasetId: string): Promise<TestDataset | null> {
    const response = await this.apiClient.get<ApiResponse<TestDataset>>(`/api/v1/datasets/${datasetId}`);

    if (response.code === 0 && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 删除数据集
   */
  async deleteDataset(datasetId: string): Promise<void> {
    const response = await this.apiClient.delete<ApiResponse>(`/api/v1/datasets/${datasetId}`);

    if (response.code !== 0) {
      throw new Error(`删除数据集失败: ${response.message || response.error}`);
    }

    this.createdDatasets = this.createdDatasets.filter(id => id !== datasetId);
  }

  // ============================================
  // 工作流管理
  // ============================================

  /**
   * 创建测试工作流
   */
  async createTestWorkflow(data: {
    name: string;
    description?: string;
    type?: string;
    owner_id: string;
  }): Promise<TestWorkflow> {
    const response = await this.bishengClient.post<ApiResponse<TestWorkflow>>('/api/v1/workflows', {
      name: data.name,
      description: data.description || `E2E 测试工作流: ${data.name}`,
      type: data.type || 'rag',
      config: {
        nodes: [],
        edges: [],
      },
    });

    if (response.code !== 0 || !response.data) {
      throw new Error(`创建工作流失败: ${response.message || response.error}`);
    }

    const workflow = response.data;
    this.createdWorkflows.push(workflow.id);

    return workflow;
  }

  /**
   * 获取工作流
   */
  async getWorkflow(workflowId: string): Promise<TestWorkflow | null> {
    const response = await this.bishengClient.get<ApiResponse<TestWorkflow>>(`/api/v1/workflows/${workflowId}`);

    if (response.code === 0 && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 删除工作流
   */
  async deleteWorkflow(workflowId: string): Promise<void> {
    const response = await this.bishengClient.delete<ApiResponse>(`/api/v1/workflows/${workflowId}`);

    if (response.code !== 0) {
      throw new Error(`删除工作流失败: ${response.message || response.error}`);
    }

    this.createdWorkflows = this.createdWorkflows.filter(id => id !== workflowId);
  }

  // ============================================
  // 模型管理
  // ============================================

  /**
   * 创建测试模型
   */
  async createTestModel(data: {
    name: string;
    version?: string;
    experiment_id?: string;
    owner_id: string;
  }): Promise<TestModel> {
    const response = await this.cubeClient.post<ApiResponse<TestModel>>('/api/v1/models', {
      name: data.name,
      version: data.version || '1.0.0',
      experiment_id: data.experiment_id,
    });

    if (response.code !== 0 || !response.data) {
      throw new Error(`创建模型失败: ${response.message || response.error}`);
    }

    const model = response.data;
    this.createdModels.push(model.id);

    return model;
  }

  /**
   * 获取模型
   */
  async getModel(modelId: string): Promise<TestModel | null> {
    const response = await this.cubeClient.get<ApiResponse<TestModel>>(`/api/v1/models/${modelId}`);

    if (response.code === 0 && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 删除模型
   */
  async deleteModel(modelId: string): Promise<void> {
    const response = await this.cubeClient.delete<ApiResponse>(`/api/v1/models/${modelId}`);

    if (response.code !== 0) {
      throw new Error(`删除模型失败: ${response.message || response.error}`);
    }

    this.createdModels = this.createdModels.filter(id => id !== modelId);
  }

  // ============================================
  // 批量创建预设测试数据
  // ============================================

  /**
   * 为特定角色创建完整测试数据集
   */
  async createTestDataForRole(role: string, ownerId: string): Promise<{
    datasets: TestDataset[];
    workflows: TestWorkflow[];
    models: TestModel[];
  }> {
    const datasets: TestDataset[] = [];
    const workflows: TestWorkflow[] = [];
    const models: TestModel[] = [];
    const timestamp = Date.now();

    // 根据角色创建不同的测试数据
    if (['admin', 'data_engineer'].includes(role)) {
      // 数据工程师需要数据集
      for (let i = 1; i <= 3; i++) {
        const dataset = await this.createTestDataset({
          name: `${role}_test_dataset_${i}_${timestamp}`,
          owner_id: ownerId,
        });
        datasets.push(dataset);
      }
    }

    if (['admin', 'ai_developer'].includes(role)) {
      // AI 开发者需要工作流
      for (let i = 1; i <= 2; i++) {
        const workflow = await this.createTestWorkflow({
          name: `${role}_test_workflow_${i}_${timestamp}`,
          type: 'rag',
          owner_id: ownerId,
        });
        workflows.push(workflow);
      }

      // AI 开发者也需要模型
      for (let i = 1; i <= 2; i++) {
        const model = await this.createTestModel({
          name: `${role}_test_model_${i}_${timestamp}`,
          version: '1.0.0',
          owner_id: ownerId,
        });
        models.push(model);
      }
    }

    if (role === 'admin') {
      // 管理员拥有全部类型的数据
      for (let i = 1; i <= 2; i++) {
        const dataset = await this.createTestDataset({
          name: `admin_test_dataset_${i}_${timestamp}`,
          owner_id: ownerId,
        });
        datasets.push(dataset);

        const workflow = await this.createTestWorkflow({
          name: `admin_test_workflow_${i}_${timestamp}`,
          type: 'agent',
          owner_id: ownerId,
        });
        workflows.push(workflow);

        const model = await this.createTestModel({
          name: `admin_test_model_${i}_${timestamp}`,
          owner_id: ownerId,
        });
        models.push(model);
      }
    }

    return { datasets, workflows, models };
  }

  /**
   * 清理所有测试数据
   */
  async cleanup(): Promise<void> {
    const errors: string[] = [];

    // 清理数据集
    for (const datasetId of [...this.createdDatasets]) {
      try {
        await this.deleteDataset(datasetId);
      } catch (error) {
        errors.push(`数据集 ${datasetId}: ${error}`);
      }
    }

    // 清理工作流
    for (const workflowId of [...this.createdWorkflows]) {
      try {
        await this.deleteWorkflow(workflowId);
      } catch (error) {
        errors.push(`工作流 ${workflowId}: ${error}`);
      }
    }

    // 清理模型
    for (const modelId of [...this.createdModels]) {
      try {
        await this.deleteModel(modelId);
      } catch (error) {
        errors.push(`模型 ${modelId}: ${error}`);
      }
    }

    this.createdDatasets = [];
    this.createdWorkflows = [];
    this.createdModels = [];

    if (errors.length > 0) {
      console.error('清理测试数据时发生错误:', errors);
    }
  }

  /**
   * 获取已创建的资源统计
   */
  getStats(): { datasets: number; workflows: number; models: number } {
    return {
      datasets: this.createdDatasets.length,
      workflows: this.createdWorkflows.length,
      models: this.createdModels.length,
    };
  }
}

// ============================================
// Fixture 类型定义
// ============================================

type TestDataFixtures = {
  /** 测试数据管理器 */
  testDataManager: TestDataManager;
  /** 创建测试数据集 */
  createTestDataset: (data: {
    name: string;
    description?: string;
    datasource_id?: string;
    owner_id: string;
  }) => Promise<TestDataset>;
  /** 创建测试工作流 */
  createTestWorkflow: (data: {
    name: string;
    description?: string;
    type?: string;
    owner_id: string;
  }) => Promise<TestWorkflow>;
  /** 创建测试模型 */
  createTestModel: (data: {
    name: string;
    version?: string;
    experiment_id?: string;
    owner_id: string;
  }) => Promise<TestModel>;
  /** 为角色创建测试数据 */
  createTestDataForRole: (role: string, ownerId: string) => Promise<{
    datasets: TestDataset[];
    workflows: TestWorkflow[];
    models: TestModel[];
  }>;
  /** 清理测试数据 */
  cleanupTestData: () => Promise<void>;
};

// ============================================
// 扩展测试对象
// ============================================

export const test = base.extend<TestDataFixtures>({
  // 测试数据管理器
  testDataManager: async ({ request }, use) => {
    const manager = new TestDataManager(request);
    await use(manager);
    await manager.cleanup();
  },

  // 创建测试数据集
  createTestDataset: async ({ testDataManager }, use) => {
    await use((data) => testDataManager.createTestDataset(data));
  },

  // 创建测试工作流
  createTestWorkflow: async ({ testDataManager }, use) => {
    await use((data) => testDataManager.createTestWorkflow(data));
  },

  // 创建测试模型
  createTestModel: async ({ testDataManager }, use) => {
    await use((data) => testDataManager.createTestModel(data));
  },

  // 为角色创建测试数据
  createTestDataForRole: async ({ testDataManager }, use) => {
    await use((role, ownerId) => testDataManager.createTestDataForRole(role, ownerId));
  },

  // 清理测试数据
  cleanupTestData: async ({ testDataManager }, use) => {
    await use(() => testDataManager.cleanup());
  },
});

export { expect } from '@playwright/test';
export type { TestDataset, TestWorkflow, TestModel };
