/**
 * Feature Management Page Object Model
 *
 * Page: /data/features
 * Features: Features List, Feature Groups, Feature Sets, Feature Services
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class FeaturesPage extends BasePage {
  readonly PAGE_PATH = '/data/features';

  // Tab locators
  readonly featuresTab: Locator;
  readonly groupsTab: Locator;
  readonly setsTab: Locator;
  readonly servicesTab: Locator;

  // Features tab locators
  readonly createFeatureButton: Locator;
  readonly featureTable: Locator;
  readonly featureDrawer: Locator;
  readonly featuresTabPane: Locator;

  // Feature form locators
  readonly featureNameInput: Locator;
  readonly featureGroupSelect: Locator;
  readonly dataTypeSelect: Locator;
  readonly valueTypeSelect: Locator;
  readonly sourceTableInput: Locator;
  readonly sourceColumnInput: Locator;

  // Groups tab locators
  readonly createGroupButton: Locator;
  readonly groupTable: Locator;

  // Sets tab locators
  readonly createSetButton: Locator;
  readonly setTable: Locator;

  // Services tab locators
  readonly createServiceButton: Locator;
  readonly serviceTable: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize tab locators
    this.featuresTab = page.locator('.ant-tabs-tab:has-text("特征列表"), .ant-tabs-tab:has-text("Features")');
    this.groupsTab = page.locator('.ant-tabs-tab:has-text("特征组"), .ant-tabs-tab:has-text("Groups")');
    this.setsTab = page.locator('.ant-tabs-tab:has-text("特征集"), .ant-tabs-tab:has-text("Sets")');
    this.servicesTab = page.locator('.ant-tabs-tab:has-text("特征服务"), .ant-tabs-tab:has-text("Services")');

    // Features tab locators
    this.featuresTabPane = page.locator('.ant-tabs-tabpane').nth(0);
    this.createFeatureButton = page.locator('.ant-tabs-tabpane').nth(0).locator('button:has-text("注册特征"), button:has-text("Register Feature")');
    this.featureTable = page.locator('.ant-tabs-tabpane').nth(0).locator('.ant-table');
    this.featureDrawer = page.locator('.ant-drawer:has-text("特征详情"), [data-testid="feature-drawer"]');

    // Feature form locators
    this.featureNameInput = page.locator('input[placeholder*="特征名称"], input[name="name"]');
    this.featureGroupSelect = page.locator('.ant-modal:visible select[name="feature_group"]');
    this.dataTypeSelect = page.locator('.ant-modal:visible select[name="data_type"]');
    this.valueTypeSelect = page.locator('.ant-modal:visible select[name="value_type"]');
    this.sourceTableInput = page.locator('input[placeholder*="来源表"], input[name="source_table"]');
    this.sourceColumnInput = page.locator('input[placeholder*="来源列"], input[name="source_column"]');

    // Groups tab locators
    this.createGroupButton = page.locator('.ant-tabs-tabpane').nth(1).locator('button:has-text("创建特征组"), button:has-text("Create Group")');
    this.groupTable = page.locator('.ant-tabs-tabpane').nth(1).locator('.ant-table');

    // Sets tab locators
    this.createSetButton = page.locator('.ant-tabs-tabpane').nth(2).locator('button:has-text("创建特征集"), button:has-text("Create Set")');
    this.setTable = page.locator('.ant-tabs-tabpane').nth(2).locator('.ant-table');

    // Services tab locators
    this.createServiceButton = page.locator('.ant-tabs-tabpane').nth(3).locator('button:has-text("发布服务"), button:has-text("Publish Service")');
    this.serviceTable = page.locator('.ant-tabs-tabpane').nth(3).locator('.ant-table');
  }

  /**
   * Navigate to features page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to features tab
   */
  async switchToFeatures(): Promise<void> {
    if (await this.featuresTab.isVisible()) {
      await this.featuresTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to groups tab
   */
  async switchToGroups(): Promise<void> {
    if (await this.groupsTab.isVisible()) {
      await this.groupsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to sets tab
   */
  async switchToSets(): Promise<void> {
    if (await this.setsTab.isVisible()) {
      await this.setsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to services tab
   */
  async switchToServices(): Promise<void> {
    if (await this.servicesTab.isVisible()) {
      await this.servicesTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Get feature count
   */
  async getFeatureCount(): Promise<number> {
    await this.waitForLoading();
    const rows = this.featureTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Click create feature button
   */
  async clickCreateFeature(): Promise<void> {
    await this.createFeatureButton.click();
    await this.waitForModal();
  }

  /**
   * Fill feature form
   */
  async fillFeatureForm(data: {
    name: string;
    description?: string;
    featureGroup: string;
    dataType: string;
    valueType: string;
    sourceTable: string;
    sourceColumn: string;
  }): Promise<void> {
    await this.featureNameInput.fill(data.name);

    if (data.description) {
      await this.page.locator('textarea[name="description"]').fill(data.description);
    }

    await this.featureGroupSelect.click();
    await this.page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await this.page.locator('.ant-select-item:has-text("创建特征组")').click();

    await this.dataTypeSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${data.dataType}")`).click();

    await this.valueTypeSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${data.valueType}")`).click();

    await this.sourceTableInput.fill(data.sourceTable);
    await this.sourceColumnInput.fill(data.sourceColumn);
  }

  /**
   * Submit feature form
   */
  async submitFeatureForm(): Promise<void> {
    await this.page.locator('.ant-modal:visible button:has-text("确定"), .ant-modal:visible button[type="submit"]').click();
  }

  /**
   * Click feature by name to view details
   */
  async viewFeatureDetails(featureName: string): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('a').click();
    await this.featureDrawer.waitFor({ state: 'visible' });
  }

  /**
   * Close feature drawer
   */
  async closeFeatureDrawer(): Promise<void> {
    await this.featureDrawer.locator('.ant-drawer-close').click();
    await this.featureDrawer.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Get feature group count
   */
  async getGroupCount(): Promise<number> {
    const rows = this.groupTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Get feature set count
   */
  async getSetCount(): Promise<number> {
    const rows = this.setTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Get feature service count
   */
  async getServiceCount(): Promise<number> {
    const rows = this.serviceTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Delete feature by name
   */
  async deleteFeature(featureName: string): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-delete), button[danger]').click();
    await this.page.locator('.ant-popconfirm:visible button:has-text("确定")').click();
  }

  // =============================================================================
  // Extended Methods (Phase 4)
  // =============================================================================

  /**
   * Search features by keyword
   */
  async searchFeatures(keyword: string): Promise<void> {
    const searchInput = this.featuresTabPane.locator('input[placeholder*="搜索"], input[data-testid="search"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Filter features by criteria
   */
  async filterFeatures(filter: {
    group?: string;
    dataType?: string;
    valueType?: string;
  }): Promise<void> {
    const filterButton = this.featuresTabPane.locator('button:has(.anticon-filter), button:has-text("筛选")');
    if (await filterButton.isVisible()) {
      await filterButton.click();
      await this.page.waitForTimeout(300);

      if (filter.group) {
        await this.page.locator('.ant-dropdown:visible select[name="group"]').selectOption(filter.group);
      }
      if (filter.dataType) {
        await this.page.locator('.ant-dropdown:visible select[name="dataType"]').selectOption(filter.dataType);
      }
      if (filter.valueType) {
        await this.page.locator('.ant-dropdown:visible select[name="valueType"]').selectOption(filter.valueType);
      }

      await this.page.locator('.ant-dropdown:visible button:has-text("确定")').click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Sort features by column
   */
  async sortFeatures(column: string): Promise<void> {
    const tableHeader = this.featureTable.locator('.ant-table-thead .ant-table-cell').filter({ hasText: column });
    await tableHeader.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Batch delete features
   */
  async batchDeleteFeatures(featureIds: string[]): Promise<void> {
    for (const featureName of featureIds) {
      const row = this.findTableRowByText(featureName);
      await row.locator('input[type="checkbox"]').check();
    }

    const batchDeleteButton = this.page.locator('button:has-text("批量删除"), button:has-text("Batch Delete")').first();
    if (await batchDeleteButton.isVisible()) {
      await batchDeleteButton.click();
      await this.page.waitForTimeout(300);
      await this.confirmDialog();
    }
  }

  /**
   * View feature versions
   */
  async viewFeatureVersions(featureName: string): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-history), button:has-text("版本")').click();
    await this.waitForDrawer();
  }

  /**
   * Manage feature tags
   */
  async manageFeatureTags(featureName: string, tags: string[]): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-tag), button:has-text("标签")').click();
    await this.waitForModal();

    for (const tag of tags) {
      const tagInput = this.page.locator('.ant-modal:visible input[placeholder*="标签"]');
      await tagInput.fill(tag);
      await this.page.locator('.ant-modal:visible button:has-text("添加")').click();
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Get feature group details
   */
  async getGroupDetails(groupName: string): Promise<any> {
    await this.switchToGroups();
    const row = this.findTableRowByText(groupName);
    const cells = row.locator('.ant-table-cell');
    const name = await cells.nth(0).textContent() || '';
    const sourceTable = await cells.nth(1).textContent() || '';
    const featureCount = await cells.nth(2).textContent() || '';
    return { name: name.trim(), sourceTable: sourceTable.trim(), featureCount: parseInt(featureCount) || 0 };
  }

  /**
   * View group details
   */
  async viewGroupDetails(groupName: string): Promise<void> {
    await this.switchToGroups();
    const row = this.findTableRowByText(groupName);
    await row.locator('a, button:has-text("详情")').click();
    await this.waitForDrawer();
  }

  /**
   * Edit group
   */
  async editGroup(groupId: string, data: { name?: string; description?: string }): Promise<void> {
    await this.switchToGroups();
    const row = this.findTableRowByText(groupId);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    if (data.name) {
      await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    }
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Delete group
   */
  async deleteGroup(groupId: string): Promise<void> {
    await this.switchToGroups();
    const row = this.findTableRowByText(groupId);
    await row.locator('button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Add feature to set
   */
  async addFeatureToSet(setId: string, featureId: string): Promise<void> {
    await this.switchToSets();
    const row = this.findTableRowByText(setId);
    await row.locator('button:has-text("添加特征"), button:has(.anticon-plus)').click();
    await this.waitForModal();

    const featureSelect = this.page.locator('.ant-modal:visible .ant-select');
    await featureSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${featureId}")`).click();

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Remove feature from set
   */
  async removeFeatureFromSet(setId: string, featureId: string): Promise<void> {
    await this.switchToSets();
    const row = this.findTableRowByText(setId);
    await row.locator('a, button:has-text("详情")').click();
    await this.waitForDrawer();

    const featureRow = this.page.locator('.ant-drawer-body .ant-table-row').filter({ hasText: featureId });
    await featureRow.locator('button:has(.anticon-minus), button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * View set details
   */
  async viewSetDetails(setName: string): Promise<any> {
    await this.switchToSets();
    const row = this.findTableRowByText(setName);
    await row.locator('a').click();
    await this.waitForDrawer();

    const name = await this.page.locator('.ant-drawer-body .set-name').textContent() || '';
    const description = await this.page.locator('.ant-drawer-body .set-description').textContent() || '';
    const featureCount = await this.page.locator('.ant-drawer-body .feature-count').textContent() || '0';
    return { name: name.trim(), description: description.trim(), featureCount: parseInt(featureCount) };
  }

  /**
   * Enable service
   */
  async enableService(serviceId: string): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    const switchControl = row.locator('.ant-switch');
    if (!(await switchControl.getAttribute('class'))?.includes('ant-switch-checked')) {
      await switchControl.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Disable service
   */
  async disableService(serviceId: string): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    const switchControl = row.locator('.ant-switch');
    if ((await switchControl.getAttribute('class'))?.includes('ant-switch-checked')) {
      await switchControl.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Test service call
   */
  async testServiceCall(serviceId: string, params: Record<string, any>): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    await row.locator('button:has-text("测试"), button:has(.anticon-play-circle)').click();
    await this.waitForModal();

    const paramsInput = this.page.locator('.ant-modal:visible textarea[name="params"]');
    await paramsInput.fill(JSON.stringify(params));

    await this.page.locator('.ant-modal:visible button:has-text("执行")').click();
    await this.page.waitForTimeout(2000);
  }

  /**
   * Get service statistics
   */
  async getServiceStats(serviceId: string): Promise<{ calls: number; avgLatency: number; errorRate: number }> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    await row.locator('button:has-text("统计"), button:has(.anticon-bar-chart)').click();
    await this.waitForDrawer();

    const callsText = await this.page.locator('.stat-calls').textContent() || '0';
    const latencyText = await this.page.locator('.stat-latency').textContent() || '0';
    const errorRateText = await this.page.locator('.stat-error-rate').textContent() || '0';

    return {
      calls: parseInt(callsText.replace(/\D/g, '')) || 0,
      avgLatency: parseFloat(latencyText) || 0,
      errorRate: parseFloat(errorRateText.replace('%', '')) || 0
    };
  }

  /**
   * Copy service endpoint
   */
  async copyServiceEndpoint(serviceId: string): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    await row.locator('button:has(.anticon-copy), button:has-text("复制")').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get service API example
   */
  async getServiceApiExample(serviceId: string): Promise<string> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceId);
    await row.locator('button:has-text("API"), button:has(.anticon-code)').click();
    await this.waitForDrawer();

    const codeElement = this.page.locator('.ant-drawer-body code, .ant-drawer-body pre');
    return await codeElement.textContent() || '';
  }

  /**
   * Create feature group
   */
  async createFeatureGroup(data: { name: string; description?: string; sourceTable?: string }): Promise<void> {
    await this.switchToGroups();
    await this.createGroupButton.click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }
    if (data.sourceTable) {
      await this.page.locator('.ant-modal:visible input[name="sourceTable"]').fill(data.sourceTable);
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Create feature set
   */
  async createFeatureSet(data: { name: string; description?: string; features: string[] }): Promise<void> {
    await this.switchToSets();
    await this.createSetButton.click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }

    const featureSelect = this.page.locator('.ant-modal:visible .ant-select');
    await featureSelect.click();
    for (const feature of data.features) {
      await this.page.locator(`.ant-select-item:has-text("${feature}")`).click();
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Publish feature service
   */
  async publishFeatureService(data: {
    name: string;
    setId: string;
    endpoint?: string;
    description?: string;
  }): Promise<void> {
    await this.switchToServices();
    await this.createServiceButton.click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    await this.page.locator('.ant-modal:visible select[name="setId"]').selectOption(data.setId);
    if (data.endpoint) {
      await this.page.locator('.ant-modal:visible input[name="endpoint"]').fill(data.endpoint);
    }
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }

    await this.page.locator('.ant-modal:visible button:has-text("发布")').click();
    await this.waitForModalClose();
  }

  /**
   * Get feature list with pagination
   */
  async getFeatureListWithPagination(): Promise<string[]> {
    await this.waitForTableLoad();
    const features: string[] = [];

    while (true) {
      const rows = this.featureTable.locator('.ant-table-body .ant-table-row');
      const count = await rows.count();

      for (let i = 0; i < count; i++) {
        const name = await rows.nth(i).locator('.ant-table-cell').nth(0).textContent() || '';
        if (name) features.push(name.trim());
      }

      const nextButton = this.page.locator('.ant-pagination-next:not(.ant-pagination-disabled)');
      if (!(await nextButton.isVisible())) break;

      await nextButton.click();
      await this.waitForTableLoad();
    }

    return features;
  }

  /**
   * Edit feature
   */
  async editFeature(featureName: string, data: Partial<{
    description: string;
    dataType: string;
    valueType: string;
  }>): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }
    if (data.dataType) {
      await this.page.locator('.ant-modal:visible select[name="dataType"]').selectOption(data.dataType);
    }
    if (data.valueType) {
      await this.page.locator('.ant-modal:visible select[name="valueType"]').selectOption(data.valueType);
    }

    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Clone feature
   */
  async cloneFeature(featureName: string, newName: string): Promise<void> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-copy), button:has-text("克隆")').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="name"]').fill(newName);
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Get feature dependencies
   */
  async getFeatureDependencies(featureName: string): Promise<string[]> {
    const row = this.findTableRowByText(featureName);
    await row.locator('button:has(.anticon-node-index), button:has-text("依赖")').click();
    await this.waitForDrawer();

    const depRows = this.page.locator('.ant-drawer-body .ant-table-row');
    const count = await depRows.count();
    const dependencies: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await depRows.nth(i).locator('.ant-table-cell').nth(0).textContent() || '';
      if (text) dependencies.push(text.trim());
    }

    return dependencies;
  }

  /**
   * Get feature usage statistics
   */
  async getFeatureUsageStats(featureName: string): Promise<{ services: number; lastUsed: string }> {
    const row = this.findTableRowByText(featureName);
    const statsCell = await row.locator('.ant-table-cell').nth(-1).textContent() || '';
    return {
      services: parseInt(statsCell) || 0,
      lastUsed: ''
    };
  }

  /**
   * Export features
   */
  async exportFeatures(format: 'csv' | 'json' = 'csv'): Promise<void> {
    const exportButton = this.featuresTabPane.locator('button:has-text("导出"), button:has(.anticon-export)');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(300);
      await this.page.locator(`.ant-dropdown-item:has-text("${format}")`).click();
    }
  }

  /**
   * Import features
   */
  async importFeatures(filePath: string): Promise<void> {
    const importButton = this.featuresTabPane.locator('button:has-text("导入"), button:has(.anticon-import)');
    if (await importButton.isVisible()) {
      await importButton.click();
      await this.waitForModal();

      const fileInput = this.page.locator('.ant-modal:visible input[type="file"]');
      await fileInput.setInputFiles(filePath);

      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.waitForModalClose();
    }
  }

  /**
   * Search in group list
   */
  async searchGroups(keyword: string): Promise<void> {
    await this.switchToGroups();
    const searchInput = this.page.locator('.ant-tabs-tabpane').nth(1).locator('input[placeholder*="搜索"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Search in set list
   */
  async searchSets(keyword: string): Promise<void> {
    await this.switchToSets();
    const searchInput = this.page.locator('.ant-tabs-tabpane').nth(2).locator('input[placeholder*="搜索"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Search in services
   */
  async searchServices(keyword: string): Promise<void> {
    await this.switchToServices();
    const searchInput = this.page.locator('.ant-tabs-tabpane').nth(3).locator('input[placeholder*="搜索"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(keyword);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Get service health status
   */
  async getServiceHealthStatus(serviceName: string): Promise<'healthy' | 'degraded' | 'down'> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceName);
    const statusBadge = row.locator('.ant-badge-status');

    const classList = await statusBadge.getAttribute('class') || '';
    if (classList.includes('success')) return 'healthy';
    if (classList.includes('warning')) return 'degraded';
    return 'down';
  }

  /**
   * View service logs
   */
  async viewServiceLogs(serviceName: string): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceName);
    await row.locator('button:has-text("日志"), button:has(.anticon-file-text)').click();
    await this.waitForDrawer();
  }

  /**
   * Configure service monitoring
   */
  async configureServiceMonitoring(serviceName: string, config: {
    alertThreshold?: number;
    enableLogging?: boolean;
  }): Promise<void> {
    await this.switchToServices();
    const row = this.findTableRowByText(serviceName);
    await row.locator('button:has-text("配置"), button:has(.anticon-setting)').click();
    await this.waitForModal();

    if (config.alertThreshold !== undefined) {
      const thresholdInput = this.page.locator('.ant-modal:visible input[name="alertThreshold"]');
      await thresholdInput.fill(String(config.alertThreshold));
    }
    if (config.enableLogging !== undefined) {
      const loggingSwitch = this.page.locator('.ant-modal:visible .ant-switch');
      const isChecked = (await loggingSwitch.getAttribute('class'))?.includes('checked');
      if (config.enableLogging && !isChecked) {
        await loggingSwitch.click();
      } else if (!config.enableLogging && isChecked) {
        await loggingSwitch.click();
      }
    }

    await this.page.locator('.ant-modal:visible button:has-text("保存")').click();
    await this.waitForModalClose();
  }
}
