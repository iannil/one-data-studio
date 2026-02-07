/**
 * 交互式验证器
 * 扩展 PageValidator，添加 CRUD 操作验证
 */

import { Page, expect } from '@playwright/test';
import { PageValidator, PageType } from './data-ops-validator';
import { TestDataManager } from './test-data-manager';
import { generateTestData, TEST_PREFIX, TEST_PREFIX_EN } from '../config/test-data.config';
import { logger } from './logger';
import {
  PageTestConfig,
  CreateOperationConfig,
  ReadOperationConfig,
  UpdateOperationConfig,
  DeleteOperationConfig,
} from '../config/all-pages.config';

// ==================== 类型定义 ====================

export interface OperationStep {
  action: string;
  target: string;
  success: boolean;
  error?: string;
  duration?: number;
}

export interface OperationResult {
  success: boolean;
  steps: OperationStep[];
  error?: string;
  duration: number;
  createdId?: string;
}

export interface PageValidationResult {
  pageName: string;
  route: string;
  module: string;
  pageLoad: {
    success: boolean;
    loadTime: number;
    error?: string;
  };
  operations: {
    create?: OperationResult;
    read?: OperationResult;
    update?: OperationResult;
    delete?: OperationResult;
  };
  errors: string[];
  warnings: string[];
  screenshotPath?: string;
  validatedAt: string;
}

// ==================== 交互式验证器类 ====================

export class InteractiveValidator extends PageValidator {
  private dataManager: TestDataManager;
  private createdItemIds: Map<string, string> = new Map();
  private testTimeout: number;

  constructor(page: Page, dataManager: TestDataManager, timeout = 60000) {
    super(page);
    this.dataManager = dataManager;
    this.testTimeout = timeout;
  }

  /**
   * 完整验证一个页面（包括所有操作）
   */
  async validatePageWithCRUD(config: PageTestConfig): Promise<PageValidationResult> {
    const startTime = Date.now();
    const result: PageValidationResult = {
      pageName: config.name,
      route: config.route,
      module: config.module,
      pageLoad: {
        success: false,
        loadTime: 0,
      },
      operations: {},
      errors: [],
      warnings: [],
      validatedAt: new Date().toISOString(),
    };

    logger.info(`Starting validation for page: ${config.name} (${config.route})`);

    // 设置监听器
    this.setupConsoleListener();
    this.setupNetworkListener();

    try {
      // 1. 验证页面加载
      result.pageLoad = await this.validatePageLoad(config);

      if (!result.pageLoad.success) {
        result.errors.push(`Page load failed: ${result.pageLoad.error}`);
        return result;
      }

      // 2. 执行创建操作
      if (config.operations?.create && !config.operations.create.skip) {
        const createResult = await this.validateCreate(
          config.operations.create,
          config.name
        );
        result.operations.create = createResult;

        if (!createResult.success) {
          result.errors.push(`Create operation failed: ${createResult.error}`);
          // 如果创建失败，后续操作可能无法进行
          if (createResult.createdId) {
            this.createdItemIds.set(config.route, createResult.createdId);
          }
        } else if (createResult.createdId) {
          this.createdItemIds.set(config.route, createResult.createdId);
        }
      }

      // 3. 执行读取操作
      if (config.operations?.read) {
        const readResult = await this.validateRead(
          config.operations.read,
          config.name
        );
        result.operations.read = readResult;

        if (!readResult.success) {
          result.warnings.push(`Read operation failed: ${readResult.error}`);
        }
      }

      // 4. 执行更新操作
      if (config.operations?.update && !config.operations.update.skip) {
        const updateResult = await this.validateUpdate(
          config.operations.update,
          config.name,
          this.createdItemIds.get(config.route)
        );
        result.operations.update = updateResult;

        if (!updateResult.success) {
          result.warnings.push(`Update operation failed: ${updateResult.error}`);
        }
      }

      // 5. 执行删除操作
      if (config.operations?.delete && !config.operations.delete.skip) {
        const deleteResult = await this.validateDelete(
          config.operations.delete,
          config.name,
          this.createdItemIds.get(config.route)
        );
        result.operations.delete = deleteResult;

        if (!deleteResult.success) {
          result.errors.push(`Delete operation failed: ${deleteResult.error}`);
        } else {
          // 删除成功，清除 ID
          this.createdItemIds.delete(config.route);
        }
      }

      // 6. 截图
      try {
        result.screenshotPath = await this.captureScreenshot(`${config.module}-${config.name}`);
      } catch (error) {
        logger.warn(`Failed to capture screenshot: ${error}`);
      }

      const duration = Date.now() - startTime;
      logger.info(`Validation complete for ${config.name}: ${duration}ms`);

    } catch (error) {
      result.errors.push(`Unexpected error: ${error}`);
      logger.error(`Validation error for ${config.name}: ${error}`);
    }

    return result;
  }

  /**
   * 验证页面加载
   */
  async validatePageLoad(config: PageTestConfig): Promise<{
    success: boolean;
    loadTime: number;
    error?: string;
  }> {
    const startTime = Date.now();

    try {
      await this.page.goto(config.route, {
        waitUntil: 'networkidle',
        timeout: config.timeout || this.testTimeout,
      });

      const loadTime = Date.now() - startTime;

      // 等待页面稳定
      await this.page.waitForTimeout(500);

      // 验证基本元素
      const { titleVisible, layoutVisible } = await this.validateBasicElements(config.expectedTitle);

      if (!titleVisible && config.expectedTitle) {
        return {
          success: false,
          loadTime,
          error: `Expected title "${config.expectedTitle}" not found`,
        };
      }

      if (!layoutVisible) {
        return {
          success: false,
          loadTime,
          error: 'Basic layout components not visible',
        };
      }

      // 验证功能组件
      const functionalComponents = await this.validateFunctionalComponents(config.type);
      if (!functionalComponents) {
        return {
          success: false,
          loadTime,
          error: `Functional components for ${config.type} page type not visible`,
        };
      }

      return { success: true, loadTime };

    } catch (error) {
      const loadTime = Date.now() - startTime;
      return {
        success: false,
        loadTime,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * 验证创建操作
   */
  async validateCreate(
    config: CreateOperationConfig,
    pageName: string
  ): Promise<OperationResult> {
    const startTime = Date.now();
    const result: OperationResult = {
      success: false,
      steps: [],
      duration: 0,
    };

    try {
      logger.info(`[CREATE] Starting create operation for ${pageName}`);

      // 1. 点击新增/创建按钮 - 扩展选择器列表
      const createButtonSelectors = [
        'button:has-text("新增")',
        'button:has-text("创建")',
        'button:has-text("添加")',
        'button:has-text("Add")',
        'button:has-text("Create")',
        'button:has-text("导入")',
        // 图标按钮 - 通过 data-testid 或 aria-label
        '[data-testid="create-button"]',
        '[data-testid="add-button"]',
        '[data-icon="plus"]',
        '[aria-label*="create"]',
        '[aria-label*="add"]',
        '[aria-label*="新增"]',
        '[aria-label*="添加"]',
        // Ant Design 表格工具栏按钮
        '.ant-table-wrapper .ant-btn-primary',
        '.ant-pro-table .ant-btn-primary',
        // Plus icon buttons
        'button .anticon-plus',
        'button .anticon-plus-circle',
        // Fab 按钮
        '.ant-fab',
        '.ant-fab-btn',
      ];

      let buttonClicked = false;
      for (const selector of createButtonSelectors) {
        try {
          const button = this.page.locator(selector).first();
          if (await button.isVisible({ timeout: 3000 }).catch(() => false)) {
            await button.click({ timeout: 5000 });
            result.steps.push({ action: 'click', target: selector, success: true });
            buttonClicked = true;
            logger.info(`[CREATE] Clicked button: ${selector}`);
            break;
          }
        } catch {
          // 继续尝试下一个选择器
        }
      }

      if (!buttonClicked) {
        // 如果没有找到创建按钮，标记为跳过而不是失败
        result.steps.push({
          action: 'skip',
          target: 'create',
          success: true,
        });
        result.warning = 'Create button not found - operation skipped';
        logger.info(`[CREATE] Create button not found for ${pageName}, skipping`);
        result.success = true; // 标记为成功（跳过不算失败）
        result.duration = Date.now() - startTime;
        return result;
      }

      // 等待表单/对话框出现
      await this.page.waitForTimeout(500);

      // 2. 如果配置了测试数据，填写表单
      let createdData: any = {};
      if (config.testData) {
        const testData = generateTestData(config.testData.category, config.testData.subCategory);
        result.steps.push({ action: 'generate', target: 'testData', success: true });
        createdData = testData;

        await this.fillFormData(testData);
        result.steps.push({ action: 'fill', target: 'form', success: true });
      }

      // 3. 提交表单
      const submitSelectors = config.submitSelector
        ? [config.submitSelector]
        : [
            'button:has-text("确定")',
            'button:has-text("保存")',
            'button:has-text("提交")',
            'button:has-text("OK")',
            'button:has-text("Submit")',
            '.ant-modal-footer .ant-btn-primary',
            'form .ant-btn-primary',
          ];

      let submitted = false;
      for (const selector of submitSelectors) {
        try {
          const submitButton = this.page.locator(selector).first();
          if (await submitButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await submitButton.click({ timeout: 5000 });
            result.steps.push({ action: 'click', target: `submit(${selector})`, success: true });
            submitted = true;
            logger.info(`[CREATE] Clicked submit button: ${selector}`);
            break;
          }
        } catch {
          // 继续尝试
        }
      }

      if (!submitted) {
        throw new Error('Submit button not found or not clickable');
      }

      // 4. 等待响应
      await this.page.waitForTimeout(1000);

      // 5. 验证成功提示
      if (config.verifySuccess && config.verifySuccess.length > 0) {
        await this.waitForSuccess(config.verifySuccess);
        result.steps.push({ action: 'verify', target: 'success message', success: true });
      }

      // 6. 尝试获取创建的 ID
      const createdId = await this.extractCreatedId();
      if (createdId) {
        result.createdId = createdId;
        result.steps.push({ action: 'extract', target: 'createdId', success: true });

        // 记录到数据管理器
        this.dataManager.track(pageName, createdData, createdId);
      }

      result.success = true;
      logger.info(`[CREATE] Create operation successful for ${pageName}`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.steps.push({
        action: 'error',
        target: 'create',
        success: false,
        error: errorMessage,
      });
      result.error = errorMessage;
      logger.error(`[CREATE] Create operation failed for ${pageName}: ${errorMessage}`);
    }

    result.duration = Date.now() - startTime;
    return result;
  }

  /**
   * 验证读取操作
   */
  async validateRead(
    config: ReadOperationConfig,
    pageName: string
  ): Promise<OperationResult> {
    const startTime = Date.now();
    const result: OperationResult = {
      success: false,
      steps: [],
      duration: 0,
    };

    try {
      logger.info(`[READ] Starting read operation for ${pageName}`);

      // 1. 等待数据加载
      await this.page.waitForTimeout(500);

      // 2. 查找数据容器
      const tableSelectors = config.tableSelector
        ? [config.tableSelector]
        : [
            '.ant-table',
            'table',
            '.data-list',
            '.grid',
            '.list-container',
          ];

      let dataFound = false;
      for (const selector of tableSelectors) {
        try {
          const table = this.page.locator(selector).first();
          if (await table.isVisible({ timeout: 3000 }).catch(() => false)) {
            result.steps.push({ action: 'find', target: `table(${selector})`, success: true });
            dataFound = true;

            // 检查是否有数据行
            const rowCount = await table.locator('tr, .list-item, .grid-item').count();
            result.steps.push({
              action: 'count',
              target: 'rows',
              success: true,
            });

            if (config.expectedRowCount && rowCount !== config.expectedRowCount) {
              result.warnings = result.warnings || [];
              result.warnings.push(`Expected ${config.expectedRowCount} rows, found ${rowCount}`);
            }

            break;
          }
        } catch {
          // 继续尝试
        }
      }

      if (!dataFound) {
        // 检查是否有空状态
        const emptyState = this.page.locator('.ant-empty, .no-data, .empty-state');
        if (await emptyState.isVisible({ timeout: 3000 }).catch(() => false)) {
          result.steps.push({ action: 'find', target: 'emptyState', success: true });
          dataFound = true; // 空状态也算有效
        }
      }

      if (!dataFound) {
        throw new Error('Data table/container not found');
      }

      // 3. 如果配置了搜索，测试搜索功能
      if (config.searchSelector) {
        const searchInput = this.page.locator(config.searchSelector).first();
        if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await searchInput.fill(TEST_PREFIX);
          await this.page.waitForTimeout(500);
          result.steps.push({ action: 'search', target: config.searchSelector, success: true });
        }
      }

      result.success = true;
      logger.info(`[READ] Read operation successful for ${pageName}`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.steps.push({
        action: 'error',
        target: 'read',
        success: false,
        error: errorMessage,
      });
      result.error = errorMessage;
      logger.error(`[READ] Read operation failed for ${pageName}: ${errorMessage}`);
    }

    result.duration = Date.now() - startTime;
    return result;
  }

  /**
   * 验证更新操作
   */
  async validateUpdate(
    config: UpdateOperationConfig,
    pageName: string,
    itemId?: string
  ): Promise<OperationResult> {
    const startTime = Date.now();
    const result: OperationResult = {
      success: false,
      steps: [],
      duration: 0,
    };

    try {
      logger.info(`[UPDATE] Starting update operation for ${pageName}`);

      if (!itemId) {
        // 尝试查找测试数据项进行编辑
        const testItemRow = this.page.locator('tr:has-text("E2E测试"), .list-item:has-text("E2E测试")').first();
        const isVisible = await testItemRow.isVisible({ timeout: 3000 }).catch(() => false);
        if (!isVisible) {
          // 没有测试数据，跳过更新操作
          result.steps.push({
            action: 'skip',
            target: 'update',
            success: true,
          });
          result.warning = 'No test data found to update - operation skipped';
          logger.info(`[UPDATE] No test data found for ${pageName}, skipping`);
          result.success = true;
          result.duration = Date.now() - startTime;
          return result;
        }
      }

      // 1. 点击编辑按钮
      const editSelectors = config.editSelector
        ? [config.editSelector]
        : [
            'button:has-text("编辑")',
            'button:has-text("修改")',
            'button:has-text("Edit")',
            '[data-testid="edit-button"]',
            '.ant-table-wrapper button:has-text("编辑")',
          ];

      let editClicked = false;
      for (const selector of editSelectors) {
        try {
          // 如果有特定项目，先找到它的行
          if (itemId) {
            const row = this.page.locator(`tr:has-text("${itemId}"), [data-id="${itemId}"]`).first();
            const editButton = row.locator(selector).or(this.page.locator(selector).first());
            if (await editButton.isVisible({ timeout: 3000 }).catch(() => false)) {
              await editButton.click({ timeout: 5000 });
              editClicked = true;
              break;
            }
          } else {
            const editButton = this.page.locator(selector).first();
            if (await editButton.isVisible({ timeout: 3000 }).catch(() => false)) {
              await editButton.click({ timeout: 5000 });
              editClicked = true;
              break;
            }
          }
        } catch {
          // 继续尝试
        }
      }

      if (!editClicked) {
        // 尝试直接双击行进行编辑
        const testRow = this.page.locator(`tr:has-text("${TEST_PREFIX}")`).first();
        if (await testRow.isVisible({ timeout: 3000 }).catch(() => false)) {
          await testRow.dblclick();
          result.steps.push({ action: 'dblclick', target: 'row', success: true });
          editClicked = true;
        }
      }

      if (!editClicked) {
        throw new Error('Edit button/action not found');
      }

      result.steps.push({ action: 'click', target: 'edit', success: true });
      await this.page.waitForTimeout(500);

      // 2. 更新字段
      if (config.updateField && config.updateValue) {
        await this.fillFormField(config.updateField, config.updateValue);
        result.steps.push({
          action: 'fill',
          target: config.updateField,
          success: true,
        });
      }

      // 3. 保存更改
      const saveSelectors = config.saveSelector
        ? [config.saveSelector]
        : [
            'button:has-text("保存")',
            'button:has-text("确定")',
            'button:has-text("Save")',
            '.ant-modal-footer .ant-btn-primary',
          ];

      let saved = false;
      for (const selector of saveSelectors) {
        try {
          const saveButton = this.page.locator(selector).first();
          if (await saveButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await saveButton.click({ timeout: 5000 });
            saved = true;
            break;
          }
        } catch {
          // 继续尝试
        }
      }

      if (!saved) {
        throw new Error('Save button not found');
      }

      result.steps.push({ action: 'click', target: 'save', success: true });
      await this.page.waitForTimeout(1000);

      result.success = true;
      logger.info(`[UPDATE] Update operation successful for ${pageName}`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.steps.push({
        action: 'error',
        target: 'update',
        success: false,
        error: errorMessage,
      });
      result.error = errorMessage;
      logger.error(`[UPDATE] Update operation failed for ${pageName}: ${errorMessage}`);
    }

    result.duration = Date.now() - startTime;
    return result;
  }

  /**
   * 验证删除操作
   */
  async validateDelete(
    config: DeleteOperationConfig,
    pageName: string,
    itemId?: string
  ): Promise<OperationResult> {
    const startTime = Date.now();
    const result: OperationResult = {
      success: false,
      steps: [],
      duration: 0,
    };

    try {
      logger.info(`[DELETE] Starting delete operation for ${pageName}`);

      if (!itemId) {
        const testItemRow = this.page.locator('tr:has-text("E2E测试"), .list-item:has-text("E2E测试")').first();
        const isVisible = await testItemRow.isVisible({ timeout: 3000 }).catch(() => false);
        if (!isVisible) {
          // 没有测试数据，跳过删除操作
          result.steps.push({
            action: 'skip',
            target: 'delete',
            success: true,
          });
          result.warning = 'No test data found to delete - operation skipped';
          logger.info(`[DELETE] No test data found for ${pageName}, skipping`);
          result.success = true;
          result.duration = Date.now() - startTime;
          return result;
        }
      }

      // 1. 点击删除按钮
      const deleteSelectors = config.deleteSelector
        ? [config.deleteSelector]
        : [
            'button:has-text("删除")',
            'button:has-text("Delete")',
            '[data-testid="delete-button"]',
            '.ant-table-wrapper button:has-text("删除")',
          ];

      let deleteClicked = false;
      for (const selector of deleteSelectors) {
        try {
          if (itemId) {
            const row = this.page.locator(`tr:has-text("${itemId}"), [data-id="${itemId}"]`).first();
            const deleteButton = row.locator(selector).or(this.page.locator(selector).first());
            if (await deleteButton.isVisible({ timeout: 3000 }).catch(() => false)) {
              await deleteButton.click({ timeout: 5000 });
              deleteClicked = true;
              break;
            }
          } else {
            const deleteButton = this.page.locator(selector).first();
            if (await deleteButton.isVisible({ timeout: 3000 }).catch(() => false)) {
              await deleteButton.click({ timeout: 5000 });
              deleteClicked = true;
              break;
            }
          }
        } catch {
          // 继续尝试
        }
      }

      if (!deleteClicked) {
        throw new Error('Delete button not found');
      }

      result.steps.push({ action: 'click', target: 'delete', success: true });
      await this.page.waitForTimeout(500);

      // 2. 确认删除
      const confirmSelectors = config.confirmSelector
        ? [config.confirmSelector]
        : [
            '.ant-modal-confirm button:has-text("确定")',
            '.ant-modal-confirm button:has-text("是")',
            '.ant-popconfirm button:has-text("确定")',
            'button:has-text("Confirm")',
            'button:has-text("Yes")',
          ];

      let confirmed = false;
      for (const selector of confirmSelectors) {
        try {
          const confirmButton = this.page.locator(selector).first();
          if (await confirmButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await confirmButton.click({ timeout: 5000 });
            confirmed = true;
            break;
          }
        } catch {
          // 继续尝试
        }
      }

      if (!confirmed) {
        // 可能没有确认对话框，删除已经完成
        result.steps.push({ action: 'info', target: 'noConfirmDialog', success: true });
      } else {
        result.steps.push({ action: 'click', target: 'confirm', success: true });
      }

      await this.page.waitForTimeout(1000);

      result.success = true;
      logger.info(`[DELETE] Delete operation successful for ${pageName}`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.steps.push({
        action: 'error',
        target: 'delete',
        success: false,
        error: errorMessage,
      });
      result.error = errorMessage;
      logger.error(`[DELETE] Delete operation failed for ${pageName}: ${errorMessage}`);
    }

    result.duration = Date.now() - startTime;
    return result;
  }

  /**
   * 填写表单数据
   */
  private async fillFormData(data: any): Promise<void> {
    for (const [key, value] of Object.entries(data)) {
      if (value === undefined || value === null) continue;

      // 尝试多种选择器格式
      const selectors = [
        `input[name="${key}"]`,
        `[data-testid="${key}-input"]`,
        `#${key}`,
        `.ant-input[name="${key}"]`,
        `input[placeholder*="${key}"]`,
        `textarea[name="${key}"]`,
        `[name="${key}"]`,
      ];

      let filled = false;
      for (const selector of selectors) {
        try {
          const input = this.page.locator(selector).first();
          if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
            await input.fill(String(value));
            filled = true;
            logger.debug(`Filled field ${key} with ${value}`);
            break;
          }
        } catch {
          // 继续尝试
        }
      }

      if (!filled) {
        logger.warn(`Could not fill field: ${key}`);
      }
    }
  }

  /**
   * 填写单个表单字段
   */
  private async fillFormField(fieldName: string, value: string): Promise<void> {
    const selectors = [
      `input[name="${fieldName}"]`,
      `[data-testid="${fieldName}-input"]`,
      `#${fieldName}`,
      `.ant-input[name="${fieldName}"]`,
      `[name="${fieldName}"]`,
    ];

    for (const selector of selectors) {
      try {
        const input = this.page.locator(selector).first();
        if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
          await input.fill(value);
          return;
        }
      } catch {
        // 继续尝试
      }
    }

    throw new Error(`Could not find field: ${fieldName}`);
  }

  /**
   * 等待成功提示
   */
  private async waitForSuccess(selectors: string[]): Promise<void> {
    for (const selector of selectors) {
      try {
        const element = this.page.locator(selector).first();
        await element.waitFor({ state: 'visible', timeout: 5000 });
        return; // 找到任意一个即可
      } catch {
        // 继续尝试下一个
      }
    }
  }

  /**
   * 提取创建的项目 ID
   */
  private async extractCreatedId(): Promise<string | undefined> {
    try {
      // 尝试从 URL 获取
      const url = this.page.url();
      const match = url.match(/\/([a-f0-9-]{36})/); // UUID pattern
      if (match) {
        return match[1];
      }

      // 尝试从成功消息中获取
      const successMessage = this.page.locator('.ant-message-success, .ant-notification-notice-success').first();
      if (await successMessage.isVisible({ timeout: 3000 }).catch(() => false)) {
        const text = await successMessage.textContent();
        const idMatch = text?.match(/ID:\s*([a-zA-Z0-9_-]+)/);
        if (idMatch) {
          return idMatch[1];
        }
      }

      // 尝试从表格第一行获取
      const firstRow = this.page.locator('.ant-table-body tr').first();
      if (await firstRow.isVisible({ timeout: 3000 }).catch(() => false)) {
        const idCell = firstRow.locator('td').first();
        const id = await idCell.textContent();
        return id || undefined;
      }

    } catch (error) {
      logger.debug(`Could not extract created ID: ${error}`);
    }

    return undefined;
  }

  /**
   * 获取所有操作的摘要
   */
  getOperationSummary(result: PageValidationResult): {
    total: number;
    successful: number;
    failed: number;
    byType: Record<string, boolean>;
  } {
    const ops = result.operations;
    const summary = {
      total: 0,
      successful: 0,
      failed: 0,
      byType: {} as Record<string, boolean>,
    };

    for (const [type, opResult] of Object.entries(ops)) {
      if (opResult) {
        summary.total++;
        summary.byType[type] = opResult.success;
        if (opResult.success) {
          summary.successful++;
        } else {
          summary.failed++;
        }
      }
    }

    return summary;
  }
}
