/**
 * 测试数据管理器
 * 负责测试数据的创建、追踪和清理
 */

import { APIRequestContext } from '@playwright/test';
import { logger } from './logger';
import { TEST_DATA, TEST_PREFIX, TEST_PREFIX_EN, isTestData, generateTestData } from '../config/test-data.config';

// ==================== 类型定义 ====================

export interface TrackedItem {
  id: string;
  category: string;
  data: any;
  createdAt: Date;
  cleaned?: boolean;
}

export interface CleanupOptions {
  force?: boolean;
  dryRun?: boolean;
  categories?: string[];
}

export interface CleanupResult {
  success: boolean;
  cleaned: number;
  failed: number;
  errors: string[];
}

// ==================== 测试数据管理器类 ====================

export class TestDataManager {
  private createdItems: Map<string, TrackedItem[]> = new Map();
  private apiBaseUrl: string;
  private authToken?: string;

  constructor(apiBaseUrl?: string, authToken?: string) {
    this.apiBaseUrl = apiBaseUrl || process.env.ADMIN_API_URL || 'http://localhost:8080';
    this.authToken = authToken;
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  /**
   * 记录创建的项目
   */
  track(category: string, item: any, id?: string): TrackedItem {
    const trackedItem: TrackedItem = {
      id: id || this.generateItemId(category, item),
      category,
      data: item,
      createdAt: new Date(),
    };

    if (!this.createdItems.has(category)) {
      this.createdItems.set(category, []);
    }

    this.createdItems.get(category)!.push(trackedItem);
    logger.info(`Tracked ${category} item: ${trackedItem.id}`);

    return trackedItem;
  }

  /**
   * 生成项目 ID
   */
  private generateItemId(category: string, item: any): string {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 10000);
    return `${category}_${timestamp}_${random}`;
  }

  /**
   * 获取指定类别的所有追踪项目
   */
  getTrackedItems(category?: string): TrackedItem[] {
    if (category) {
      return this.createdItems.get(category) || [];
    }

    const all: TrackedItem[] = [];
    for (const items of this.createdItems.values()) {
      all.push(...items);
    }
    return all;
  }

  /**
   * 获取指定 ID 的追踪项目
   */
  getTrackedItem(id: string): TrackedItem | undefined {
    for (const items of this.createdItems.values()) {
      const found = items.find(item => item.id === id);
      if (found) return found;
    }
    return undefined;
  }

  /**
   * 更新追踪项目的 ID（用于创建后获取真实 ID）
   */
  updateItemId(category: string, tempId: string, realId: string): void {
    const items = this.createdItems.get(category);
    if (items) {
      const item = items.find(i => i.id === tempId);
      if (item) {
        item.id = realId;
        logger.info(`Updated ${category} item ID: ${tempId} -> ${realId}`);
      }
    }
  }

  /**
   * 获取测试数据标识
   */
  getTestDataId(category: string, subCategory?: string): string {
    const data = generateTestData(category, subCategory);
    return data.name || data.username || data.id || `test_${category}_${Date.now()}`;
  }

  /**
   * 通过 API 清理指定类别的测试数据
   */
  async cleanupCategoryByApi(
    request: APIRequestContext,
    category: string,
    options: CleanupOptions = {}
  ): Promise<CleanupResult> {
    const result: CleanupResult = {
      success: true,
      cleaned: 0,
      failed: 0,
      errors: [],
    };

    const items = this.createdItems.get(category) || [];
    const itemsToClean = items.filter(item => !item.cleaned);

    if (itemsToClean.length === 0) {
      logger.info(`No items to clean for category: ${category}`);
      return result;
    }

    logger.info(`Cleaning ${itemsToClean.length} items for category: ${category}`);

    for (const item of itemsToClean) {
      try {
        if (options.dryRun) {
          logger.info(`[DRY RUN] Would delete ${category} item: ${item.id}`);
          result.cleaned++;
        } else {
          await this.deleteItemByApi(request, category, item);
          item.cleaned = true;
          result.cleaned++;
          logger.info(`Cleaned ${category} item: ${item.id}`);
        }
      } catch (error) {
        result.failed++;
        result.errors.push(`${category}/${item.id}: ${error}`);
        logger.error(`Failed to clean ${category} item ${item.id}: ${error}`);
      }
    }

    result.success = result.failed === 0;
    return result;
  }

  /**
   * 通过 API 删除单个项目
   */
  private async deleteItemByApi(
    request: APIRequestContext,
    category: string,
    item: TrackedItem
  ): Promise<void> {
    const headers = this.getAuthHeaders();

    // 根据类别构建删除请求
    const endpoints: Record<string, string> = {
      datasource: '/api/v1/datasources',
      etl: '/api/v1/etl/tasks',
      user: '/api/v1/users',
      workflow: '/api/v1/workflows',
      prompt: '/api/v1/prompts',
      knowledge: '/api/v1/knowledge',
      notebook: '/api/v1/notebooks',
      experiment: '/api/v1/experiments',
      model: '/api/v1/models',
      dataset: '/api/v1/datasets',
      schedule: '/api/v1/schedules',
      quality_rule: '/api/v1/quality/rules',
      alert_rule: '/api/v1/alerts/rules',
      feature: '/api/v1/features',
    };

    const endpoint = endpoints[category];
    if (!endpoint) {
      logger.warn(`No delete endpoint for category: ${category}`);
      return;
    }

    const url = `${this.apiBaseUrl}${endpoint}/${item.id}`;
    const response = await request.delete(url, { headers });

    if (!response.ok()) {
      const text = await response.text();
      throw new Error(`Delete failed: ${response.status()} ${text}`);
    }
  }

  /**
   * 清理所有测试数据
   */
  async cleanupAll(request: APIRequestContext, options: CleanupOptions = {}): Promise<CleanupResult> {
    const result: CleanupResult = {
      success: true,
      cleaned: 0,
      failed: 0,
      errors: [],
    };

    const categories = options.categories || Array.from(this.createdItems.keys());

    logger.info(`Starting cleanup for ${categories.length} categories`);

    for (const category of categories) {
      const categoryResult = await this.cleanupCategoryByApi(request, category, options);
      result.cleaned += categoryResult.cleaned;
      result.failed += categoryResult.failed;
      result.errors.push(...categoryResult.errors);
    }

    result.success = result.failed === 0;

    // 如果所有都清理成功，清空追踪记录
    if (result.success && !options.dryRun) {
      this.createdItems.clear();
    }

    logger.info(`Cleanup complete: ${result.cleaned} cleaned, ${result.failed} failed`);

    return result;
  }

  /**
   * 查询并清理遗留的测试数据
   * 用于清理之前测试失败留下的数据
   */
  async cleanupOrphanedTestData(
    request: APIRequestContext,
    options: CleanupOptions = {}
  ): Promise<CleanupResult> {
    const result: CleanupResult = {
      success: true,
      cleaned: 0,
      failed: 0,
      errors: [],
    };

    logger.info('Scanning for orphaned test data...');

    // 清理测试用户
    try {
      const users = await this.findTestUsers(request);
      for (const user of users) {
        if (options.dryRun) {
          logger.info(`[DRY RUN] Would delete user: ${user.username}`);
          result.cleaned++;
        } else {
          await this.deleteUser(request, user.id);
          result.cleaned++;
        }
      }
    } catch (error) {
      result.errors.push(`Failed to cleanup users: ${error}`);
    }

    // 清理测试数据源
    try {
      const datasources = await this.findTestDatasources(request);
      for (const ds of datasources) {
        if (options.dryRun) {
          logger.info(`[DRY RUN] Would delete datasource: ${ds.name}`);
          result.cleaned++;
        } else {
          await this.deleteDatasource(request, ds.id);
          result.cleaned++;
        }
      }
    } catch (error) {
      result.errors.push(`Failed to cleanup datasources: ${error}`);
    }

    result.success = result.failed === 0;
    return result;
  }

  /**
   * 查找测试用户
   */
  private async findTestUsers(request: APIRequestContext): Promise<Array<{ id: string; username: string }>> {
    const headers = this.getAuthHeaders();
    const response = await request.get(`${this.apiBaseUrl}/api/v1/users`, { headers });

    if (!response.ok()) {
      return [];
    }

    const json = await response.json();
    const users = json.data?.users || json.data || [];

    return users.filter((u: any) =>
      isTestData(u.username) || u.username?.startsWith(TEST_PREFIX_EN)
    );
  }

  /**
   * 查找测试数据源
   */
  private async findTestDatasources(request: APIRequestContext): Promise<Array<{ id: string; name: string }>> {
    const headers = this.getAuthHeaders();
    const response = await request.get(`${this.apiBaseUrl}/api/v1/datasources`, { headers });

    if (!response.ok()) {
      return [];
    }

    const json = await response.json();
    const datasources = json.data?.datasources || json.data || [];

    return datasources.filter((ds: any) =>
      isTestData(ds.name) || ds.name?.startsWith(TEST_PREFIX)
    );
  }

  /**
   * 删除用户
   */
  private async deleteUser(request: APIRequestContext, userId: string): Promise<void> {
    const headers = this.getAuthHeaders();
    await request.delete(`${this.apiBaseUrl}/api/v1/users/${userId}`, { headers });
  }

  /**
   * 删除数据源
   */
  private async deleteDatasource(request: APIRequestContext, datasourceId: string): Promise<void> {
    const headers = this.getAuthHeaders();
    await request.delete(`${this.apiBaseUrl}/api/v1/datasources/${datasourceId}`, { headers });
  }

  /**
   * 获取认证请求头
   */
  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  /**
   * 获取清理统计信息
   */
  getStats(): {
    total: number;
    byCategory: Record<string, number>;
    cleaned: number;
  } {
    const all = this.getTrackedItems();
    const byCategory: Record<string, number> = {};

    for (const [category, items] of this.createdItems) {
      byCategory[category] = items.filter(i => !i.cleaned).length;
    }

    return {
      total: all.length,
      byCategory,
      cleaned: all.filter(i => i.cleaned).length,
    };
  }

  /**
   * 重置所有追踪数据
   */
  reset(): void {
    this.createdItems.clear();
    logger.info('Reset all tracked test data');
  }

  /**
   * 导出追踪数据（用于调试）
   */
  export(): string {
    const data = {
      stats: this.getStats(),
      items: Array.from(this.createdItems.entries()).map(([category, items]) => ({
        category,
        count: items.length,
        items: items.map(i => ({
          id: i.id,
          createdAt: i.createdAt,
          cleaned: i.cleaned,
        })),
      })),
    };
    return JSON.stringify(data, null, 2);
  }
}

// ==================== 单例管理器 ====================

let globalDataManager: TestDataManager | null = null;

/**
 * 获取全局测试数据管理器
 */
export function getDataManager(): TestDataManager {
  if (!globalDataManager) {
    const apiBaseUrl = process.env.ADMIN_API_URL || 'http://localhost:8080';
    globalDataManager = new TestDataManager(apiBaseUrl);
  }
  return globalDataManager;
}

/**
 * 重置全局测试数据管理器
 */
export function resetDataManager(): void {
  if (globalDataManager) {
    globalDataManager.reset();
  }
  globalDataManager = null;
}
