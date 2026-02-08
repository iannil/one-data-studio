/**
 * Data Assets Page Object Model
 *
 * Page: /data/assets
 * Features: Asset Catalog Tree, Asset List, AI Search, Asset Inventory, Value Assessment
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class AssetsPage extends BasePage {
  readonly PAGE_PATH = '/data/assets';

  // Asset catalog tree locators
  readonly assetTree: Locator;
  readonly treeSearchInput: Locator;
  readonly treeRefreshButton: Locator;

  // Tab locators
  readonly assetsListTab: Locator;
  readonly aiSearchTab: Locator;
  readonly inventoryTab: Locator;
  readonly valueAssessmentTab: Locator;

  // Asset list tab locators
  readonly assetTable: Locator;
  readonly typeFilterSelect: Locator;
  readonly refreshButton: Locator;
  readonly assetProfileDrawer: Locator;

  // AI search tab locators
  readonly aiSearchInput: Locator;
  readonly aiSearchResults: Locator;

  // Inventory tab locators
  readonly createInventoryButton: Locator;
  readonly inventoryTable: Locator;

  // Value assessment tab locators
  readonly valueAssessmentPanel: Locator;

  // Asset profile drawer locators
  readonly profileBasicInfo: Locator;
  readonly profileStatistics: Locator;
  readonly profileQuality: Locator;
  readonly profileLineage: Locator;

  // AI value assessment modal locators
  readonly aiValueModal: Locator;

  constructor(page: Page) {
    super(page);

    // Asset catalog tree locators
    this.assetTree = page.locator('.ant-tree');
    this.treeSearchInput = page.locator('input[placeholder*="搜索资产"]');
    this.treeRefreshButton = page.locator('button:has-text("刷新"), .anticon-reload').first();

    // Tab locators
    this.assetsListTab = page.locator('.ant-tabs-tab:has-text("资产列表")');
    this.aiSearchTab = page.locator('.ant-tabs-tab:has-text("AI")');
    this.inventoryTab = page.locator('.ant-tabs-tab:has-text("资产盘点")');
    this.valueAssessmentTab = page.locator('.ant-tabs-tab:has-text("价值评估")');

    // Asset list tab locators
    this.assetsListTabPane = page.locator('.ant-tabs-tabpane').nth(0);
    this.assetTable = page.locator('.ant-tabs-tabpane').nth(0).locator('.ant-table');
    this.typeFilterSelect = page.locator('select[placeholder*="类型筛选"]');
    this.refreshButton = page.locator('button:has-text("刷新")');
    this.assetProfileDrawer = page.locator('.ant-drawer:has-text("资产画像"), [data-testid="asset-profile-drawer"]');

    // AI search tab locators
    this.aiSearchInput = page.locator('textarea[placeholder*="自然语言"], input[placeholder*="搜索"]').first();
    this.aiSearchResults = page.locator('[data-testid="ai-search-results"]');

    // Inventory tab locators
    this.createInventoryButton = page.locator('button:has-text("创建盘点任务")');
    this.inventoryTable = page.locator('[data-testid="inventory-table"], .inventory-table');

    // Value assessment tab locators
    this.valueAssessmentPanel = page.locator('[data-testid="value-assessment-panel"]');

    // Asset profile drawer locators
    this.profileBasicInfo = page.locator('[data-testid="profile-basic-info"]');
    this.profileStatistics = page.locator('[data-testid="profile-statistics"]');
    this.profileQuality = page.locator('[data-testid="profile-quality"]');
    this.profileLineage = page.locator('[data-testid="profile-lineage"]');

    // AI value assessment modal locators
    this.aiValueModal = page.locator('.ant-modal:has-text("价值评估"), [data-testid="ai-value-modal"]');
  }

  /**
   * Navigate to assets page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to asset list tab
   */
  async switchToAssetsList(): Promise<void> {
    await this.assetsListTab.click();
    await this.waitForStable();
  }

  /**
   * Switch to AI search tab
   * Returns true if tab was found and clicked, false otherwise
   */
  async switchToAISearch(): Promise<boolean> {
    try {
      await this.aiSearchTab.waitFor({ state: 'visible', timeout: 5000 });
      await this.aiSearchTab.click();
      await this.waitForStable();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Switch to inventory tab
   */
  async switchToInventory(): Promise<void> {
    await this.inventoryTab.click();
    await this.waitForStable();
  }

  /**
   * Switch to value assessment tab
   */
  async switchToValueAssessment(): Promise<void> {
    await this.valueAssessmentTab.click();
    await this.waitForStable();
  }

  /**
   * Search in asset tree
   */
  async searchTree(keyword: string): Promise<void> {
    await this.treeSearchInput.fill(keyword);
    await this.page.waitForTimeout(500);
  }

  /**
   * Select asset node in tree
   */
  async selectAssetNode(assetName: string): Promise<void> {
    const treeNode = this.page.locator(`.ant-tree-treenode:has-text("${assetName}")`);
    await treeNode.click();
    await this.waitForStable();
  }

  /**
   * Get asset count
   */
  async getAssetCount(): Promise<number> {
    await this.waitForLoading();
    const rows = this.assetTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Filter by asset type
   */
  async filterByType(type: string): Promise<void> {
    await this.typeFilterSelect.click();
    await this.page.locator(`.ant-select-item:has-text("${type}")`).click();
    await this.page.waitForTimeout(500);
  }

  /**
   * View asset details
   */
  async viewAssetDetails(assetName: string): Promise<void> {
    const row = this.findTableRowByText(assetName);
    await row.locator('a').first().click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });
  }

  /**
   * Close asset profile drawer
   */
  async closeAssetProfile(): Promise<void> {
    await this.assetProfileDrawer.locator('.ant-drawer-close').click();
    await this.assetProfileDrawer.waitFor({ state: 'hidden' }).catch(() => {});
  }

  /**
   * Perform AI semantic search
   * Returns true if search was executed, false otherwise
   */
  async aiSearch(query: string): Promise<boolean> {
    const switched = await this.switchToAISearch();
    if (!switched) {
      return false;
    }

    try {
      await this.aiSearchInput.fill(query);
      await this.page.locator('button:has-text("搜索"), button[type="submit"]').first().click();
      await this.page.waitForTimeout(1000);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get AI search result count
   */
  async getAiSearchResultCount(): Promise<number> {
    const results = this.aiSearchResults.locator('.ant-table-row, .search-result-item');
    return await results.count();
  }

  /**
   * Click create inventory button
   */
  async clickCreateInventory(): Promise<void> {
    await this.createInventoryButton.click();
    await this.waitForModal();
  }

  /**
   * Fill inventory form
   */
  async fillInventoryForm(data: { name: string; scope?: string[] }): Promise<void> {
    await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);

    if (data.scope && data.scope.length > 0) {
      const scopeSelect = this.page.locator('.ant-modal:visible select[name="scope"]');
      for (const item of data.scope) {
        await scopeSelect.click();
        await this.page.locator(`.ant-select-item:has-text("${item}")`).click();
      }
    }
  }

  /**
   * Submit inventory form
   */
  async submitInventoryForm(): Promise<void> {
    await this.page.locator('.ant-modal:visible button:has-text("确定"), .ant-modal:visible button[type="submit"]').click();
  }

  /**
   * Get inventory task count
   */
  async getInventoryTaskCount(): Promise<number> {
    const rows = this.inventoryTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Get inventory task status by name
   */
  async getInventoryTaskStatus(taskName: string): Promise<string> {
    const row = this.findTableRowByText(taskName);
    const statusCell = row.locator('.ant-table-cell').nth(1);
    return await statusCell.textContent() || '';
  }

  /**
   * Get profile basic info
   */
  async getProfileBasicInfo(): Promise<{ name: string; type: string; owner: string; department: string }> {
    const name = await this.profileBasicInfo.locator('.ant-descriptions-item-label:has-text("名称") + .ant-descriptions-item-content').textContent() || '';
    const type = await this.profileBasicInfo.locator('.ant-descriptions-item-label:has-text("类型") + .ant-descriptions-item-content').textContent() || '';
    const owner = await this.profileBasicInfo.locator('.ant-descriptions-item-label:has-text("所有者") + .ant-descriptions-item-content').textContent() || '';
    const department = await this.profileBasicInfo.locator('.ant-descriptions-item-label:has-text("部门") + .ant-descriptions-item-content').textContent() || '';

    return { name: name.trim(), type: type.trim(), owner: owner.trim(), department: department.trim() };
  }

  /**
   * Get quality scores
   */
  async getQualityScores(): Promise<{ completeness: number; accuracy: number; consistency: number; timeliness: number }> {
    const getTextAndParse = async (label: string): Promise<number> => {
      const text = await this.profileQuality.locator(`.ant-descriptions-item-label:has-text("${label}") + *`).textContent() || '';
      return parseInt(text.replace(/\D/g, '')) || 0;
    };

    return {
      completeness: await getTextAndParse('完整性'),
      accuracy: await getTextAndParse('准确性'),
      consistency: await getTextAndParse('一致性'),
      timeliness: await getTextAndParse('时效性'),
    };
  }

  // =============================================================================
  // Extended Methods (Phase 6)
  // =============================================================================

  /**
   * Expand tree node
   */
  async expandTreeNode(nodeName: string): Promise<void> {
    const treeNode = this.assetTree.locator('.ant-tree-treenode').filter({ hasText: nodeName });
    const switcher = treeNode.locator('.ant-tree-switcher');
    if (await switcher.isVisible()) {
      await switcher.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Collapse tree node
   */
  async collapseTreeNode(nodeName: string): Promise<void> {
    const treeNode = this.assetTree.locator('.ant-tree-treenode').filter({ hasText: nodeName });
    const switcher = treeNode.locator('.ant-tree-switcher_open');
    if (await switcher.isVisible()) {
      await switcher.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Search in tree
   */
  async searchInTree(keyword: string): Promise<void> {
    await this.treeSearchInput.fill(keyword);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Refresh asset tree
   */
  async refreshAssetTree(): Promise<void> {
    await this.treeRefreshButton.click();
    await this.page.waitForTimeout(2000);
  }

  /**
   * Multi-select assets
   */
  async multiSelectAssets(assetIds: string[]): Promise<void> {
    for (const assetId of assetIds) {
      const row = this.findTableRowByText(assetId);
      await row.locator('input[type="checkbox"]').check();
    }
  }

  /**
   * Sort assets by column
   */
  async sortAssets(column: string): Promise<void> {
    const tableHeader = this.assetTable.locator('.ant-table-thead .ant-table-cell').filter({ hasText: column });
    await tableHeader.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Advanced filter for assets
   */
  async advancedFilter(filters: {
    type?: string;
    owner?: string;
    department?: string;
    tags?: string[];
    dateRange?: { start: Date; end: Date };
  }): Promise<void> {
    const filterButton = this.page.locator('button:has-text("高级筛选"), button:has(.anticon-filter)');
    if (await filterButton.isVisible()) {
      await filterButton.click();
      await this.waitForModal();

      if (filters.type) {
        await this.page.locator('.ant-modal:visible select[name="type"]').selectOption(filters.type);
      }
      if (filters.owner) {
        await this.page.locator('.ant-modal:visible input[name="owner"]').fill(filters.owner);
      }
      if (filters.department) {
        await this.page.locator('.ant-modal:visible input[name="department"]').fill(filters.department);
      }
      if (filters.tags && filters.tags.length > 0) {
        for (const tag of filters.tags) {
          await this.page.locator('.ant-modal:visible input[placeholder*="标签"]').fill(tag);
          await this.page.locator('.ant-modal:visible button:has-text("添加")').click();
        }
      }
      if (filters.dateRange) {
        await this.page.locator('.ant-modal:visible input[name="startDate"]').fill(filters.dateRange.start.toISOString().split('T')[0]);
        await this.page.locator('.ant-modal:visible input[name="endDate"]').fill(filters.dateRange.end.toISOString().split('T')[0]);
      }

      await this.page.locator('.ant-modal:visible button:has-text("应用")').click();
      await this.waitForModalClose();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Manage asset tags
   */
  async manageAssetTags(assetId: string, tags: string[]): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-tag), button:has-text("标签")').click();
    await this.waitForModal();

    const tagInput = this.page.locator('.ant-modal:visible input[placeholder*="标签"]');
    for (const tag of tags) {
      await tagInput.fill(tag);
      await this.page.locator('.ant-modal:visible button:has-text("添加")').click();
    }

    await this.page.locator('.ant-modal:visible button:has-text("保存")').click();
    await this.waitForModalClose();
  }

  /**
   * Change asset owner
   */
  async changeAssetOwner(assetId: string, newOwner: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("变更所有者"), button:has(.anticon-user-switch)').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="newOwner"]').fill(newOwner);
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Get search history
   */
  async getSearchHistory(): Promise<string[]> {
    const historyButton = this.page.locator('button:has-text("历史"), button:has(.anticon-history)');
    if (await historyButton.isVisible()) {
      await historyButton.click();
      await this.page.waitForTimeout(300);

      const historyItems = this.page.locator('.search-history-item');
      const count = await historyItems.count();
      const history: string[] = [];

      for (let i = 0; i < count; i++) {
        const text = await historyItems.nth(i).textContent() || '';
        history.push(text.trim());
      }
      return history;
    }
    return [];
  }

  /**
   * Natural language filter
   */
  async naturalLanguageFilter(query: string): Promise<void> {
    const nlFilterInput = this.page.locator('input[placeholder*="自然语言"], textarea[placeholder*="描述需求"]');
    if (await nlFilterInput.isVisible()) {
      await nlFilterInput.fill(query);
      await this.page.locator('button:has-text("筛选")').click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Execute inventory task
   */
  async executeInventory(taskId: string): Promise<void> {
    await this.switchToInventory();
    const row = this.findTableRowByText(taskId);
    await row.locator('button:has(.anticon-play-circle), button:has-text("执行")').click();
    await this.page.waitForTimeout(500);
    await this.confirmDialog();
  }

  /**
   * View inventory results
   */
  async viewInventoryResults(taskId: string): Promise<void> {
    await this.switchToInventory();
    const row = this.findTableRowByText(taskId);
    await row.locator('button:has-text("查看结果"), button:has(.anticon-eye)').click();
    await this.waitForDrawer();
  }

  /**
   * Delete inventory task
   */
  async deleteInventory(taskId: string): Promise<void> {
    await this.switchToInventory();
    const row = this.findTableRowByText(taskId);
    await row.locator('button:has(.anticon-delete)').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Export inventory report
   */
  async exportInventoryReport(taskId: string, format: 'pdf' | 'excel' = 'pdf'): Promise<void> {
    await this.switchToInventory();
    const row = this.findTableRowByText(taskId);
    await row.locator('button:has-text("导出报告")').click();
    await this.page.waitForTimeout(300);

    await this.page.locator(`.ant-dropdown-item:has-text("${format}")`).click();
  }

  /**
   * Manual assess value
   */
  async manualAssessValue(assetId: string, value: number): Promise<void> {
    await this.switchToValueAssessment();
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("评估"), button:has(.anticon-like)').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="value"]').fill(String(value));
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Configure assessment rules
   */
  async configureAssessmentRules(rules: {
    qualityWeight?: number;
    usageWeight?: number;
    freshnessWeight?: number;
  }): Promise<void> {
    await this.switchToValueAssessment();
    const configButton = this.page.locator('button:has-text("配置规则")');
    if (await configButton.isVisible()) {
      await configButton.click();
      await this.waitForModal();

      if (rules.qualityWeight !== undefined) {
        await this.page.locator('.ant-modal:visible input[name="qualityWeight"]').fill(String(rules.qualityWeight));
      }
      if (rules.usageWeight !== undefined) {
        await this.page.locator('.ant-modal:visible input[name="usageWeight"]').fill(String(rules.usageWeight));
      }
      if (rules.freshnessWeight !== undefined) {
        await this.page.locator('.ant-modal:visible input[name="freshnessWeight"]').fill(String(rules.freshnessWeight));
      }

      await this.page.locator('.ant-modal:visible button:has-text("保存")').click();
      await this.waitForModalClose();
    }
  }

  /**
   * Get value trend
   */
  async getValueTrend(assetId: string): Promise<Array<{ date: string; value: number }>> {
    await this.switchToValueAssessment();
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("趋势"), button:has(.anticon-line-chart)').click();
    await this.waitForDrawer();

    const trendData: Array<{ date: string; value: number }> = [];
    const trendPoints = this.page.locator('.trend-chart .data-point');
    const count = await trendPoints.count();

    for (let i = 0; i < Math.min(count, 30); i++) {
      const date = await trendPoints.nth(i).getAttribute('data-date') || '';
      const valueText = await trendPoints.nth(i).textContent() || '0';
      trendData.push({ date, value: parseFloat(valueText) || 0 });
    }
    return trendData;
  }

  /**
   * Batch assess values
   */
  async batchAssessValues(assetIds: string[], value: number): Promise<void> {
    await this.switchToValueAssessment();

    for (const assetId of assetIds) {
      const row = this.findTableRowByText(assetId);
      await row.locator('input[type="checkbox"]').check();
    }

    const batchAssessButton = this.page.locator('button:has-text("批量评估")');
    if (await batchAssessButton.isVisible()) {
      await batchAssessButton.click();
      await this.waitForModal();

      await this.page.locator('.ant-modal:visible input[name="value"]').fill(String(value));
      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.waitForModalClose();
    }
  }

  /**
   * Edit asset info
   */
  async editAssetInfo(assetId: string, data: {
    name?: string;
    description?: string;
    businessOwner?: string;
    technicalOwner?: string;
  }): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-edit)').click();
    await this.waitForModal();

    if (data.name) {
      await this.page.locator('.ant-modal:visible input[name="name"]').fill(data.name);
    }
    if (data.description) {
      await this.page.locator('.ant-modal:visible textarea[name="description"]').fill(data.description);
    }
    if (data.businessOwner) {
      await this.page.locator('.ant-modal:visible input[name="businessOwner"]').fill(data.businessOwner);
    }
    if (data.technicalOwner) {
      await this.page.locator('.ant-modal:visible input[name="technicalOwner"]').fill(data.technicalOwner);
    }

    await this.page.locator('.ant-modal:visible button:has-text("保存")').click();
    await this.waitForModalClose();
  }

  /**
   * View asset relations
   */
  async viewAssetRelations(assetId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    await this.page.locator('.ant-drawer-body button:has-text("血缘"), button:has(.anticon-node-index)').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get asset usage stats
   */
  async getAssetUsageStats(assetId: string): Promise<{
    queryCount: number;
    lastQueried: string;
    topUsers: string[];
  }> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    const queryCountText = await this.profileStatistics.locator('.query-count').textContent() || '0';
    const lastQueried = await this.profileStatistics.locator('.last-queried').textContent() || '';

    const topUsers: string[] = [];
    const userItems = this.profileStatistics.locator('.top-user-item');
    const count = await userItems.count();
    for (let i = 0; i < Math.min(count, 5); i++) {
      const user = await userItems.nth(i).textContent() || '';
      topUsers.push(user.trim());
    }

    await this.closeAssetProfile();

    return {
      queryCount: parseInt(queryCountText) || 0,
      lastQueried: lastQueried.trim(),
      topUsers
    };
  }

  /**
   * View asset history
   */
  async viewAssetHistory(assetId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    await this.page.locator('.ant-drawer-body button:has-text("历史"), button:has(.anticon-history)').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Subscribe to asset changes
   */
  async subscribeAsset(assetId: string, notificationType: 'email' | 'webhook' = 'webhook'): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-bell), button:has-text("订阅")').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible .ant-radio-group').locator(`:has-text("${notificationType}")`).click();
    await this.page.locator('.ant-modal:visible button:has-text("订阅")').click();
    await this.waitForModalClose();
  }

  /**
   * Unsubscribe from asset
   */
  async unsubscribeAsset(assetId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-bell-filled), button:has-text("取消订阅")').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get asset lineage graph
   */
  async getAssetLineageGraph(assetId: string): Promise<Array<{ source: string; target: string; type: string }>> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    await this.page.locator('.ant-drawer-body button:has-text("血缘")').click();
    await this.page.waitForTimeout(1000);

    const edges: Array<{ source: string; target: string; type: string }> = [];
    const edgeElements = this.page.locator('.lineage-graph .edge');
    const count = await edgeElements.count();

    for (let i = 0; i < count; i++) {
      const source = await edgeElements.nth(i).getAttribute('data-source') || '';
      const target = await edgeElements.nth(i).getAttribute('data-target') || '';
      const type = await edgeElements.nth(i).getAttribute('data-type') || '';
      edges.push({ source, target, type });
    }

    await this.closeAssetProfile();
    return edges;
  }

  /**
   * Export asset data
   */
  async exportAssetData(assetId: string, format: 'csv' | 'json' | 'excel' = 'csv'): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("导出数据"), button:has(.anticon-download)').click();
    await this.page.waitForTimeout(300);

    await this.page.locator(`.ant-dropdown-item:has-text("${format}")`).click();
  }

  /**
   * Share asset
   */
  async shareAsset(assetId: string, users: string[]): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-share-alt), button:has-text("分享")').click();
    await this.waitForModal();

    const userSelect = this.page.locator('.ant-modal:visible .ant-select');
    for (const user of users) {
      await userSelect.click();
      await this.page.locator(`.ant-select-item:has-text("${user}")`).click();
    }

    await this.page.locator('.ant-modal:visible button:has-text("分享")').click();
    await this.waitForModalClose();
  }

  /**
   * Get asset quality report
   */
  async getAssetQualityReport(assetId: string): Promise<{
    completeness: number;
    accuracy: number;
    consistency: number;
    timeliness: number;
    overall: number;
  }> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    const report = await this.getQualityScores();
    const overallText = await this.profileQuality.locator('.overall-score').textContent() || '0';
    const overall = parseInt(overallText) || 0;

    await this.closeAssetProfile();

    return {
      ...report,
      overall
    };
  }

  /**
   * Create asset folder
   */
  async createAssetFolder(folderName: string, parentId?: string): Promise<void> {
    const createButton = this.page.locator('button:has-text("新建文件夹"), button:has(.anticon-folder-add)');
    if (await createButton.isVisible()) {
      await createButton.click();
      await this.waitForModal();

      await this.page.locator('.ant-modal:visible input[name="name"]').fill(folderName);
      if (parentId) {
        await this.page.locator('.ant-modal:visible input[name="parentId"]').fill(parentId);
      }

      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.waitForModalClose();
    }
  }

  /**
   * Move asset to folder
   */
  async moveAssetToFolder(assetId: string, folderId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('input[type="checkbox"]').check();

    const moveButton = this.page.locator('button:has-text("移动"), button:has(.anticon-arrow-right)');
    if (await moveButton.isEnabled()) {
      await moveButton.click();
      await this.waitForModal();

      await this.page.locator('.ant-modal:visible .ant-tree-treenode:has-text("' + folderId + '")').click();
      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.waitForModalClose();
    }
  }

  /**
   * Copy asset
   */
  async copyAsset(assetId: string, newAssetName: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-copy)').click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-item:has-text("复制")').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible input[name="name"]').fill(newAssetName);
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Archive asset
   */
  async archiveAsset(assetId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("更多")').click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-item:has-text("归档")').click();
    await this.page.waitForTimeout(300);
    await this.confirmDialog();
  }

  /**
   * Restore archived asset
   */
  async restoreAsset(assetId: string): Promise<void> {
    const archivedTab = this.page.locator('.ant-tabs-tab:has-text("已归档")');
    if (await archivedTab.isVisible()) {
      await archivedTab.click();
      await this.page.waitForTimeout(500);

      const row = this.findTableRowByText(assetId);
      await row.locator('button:has-text("还原")').click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Batch delete assets
   */
  async batchDeleteAssets(assetIds: string[]): Promise<void> {
    for (const assetId of assetIds) {
      const row = this.findTableRowByText(assetId);
      await row.locator('input[type="checkbox"]').check();
    }

    const batchDeleteButton = this.page.locator('button:has-text("批量删除")');
    if (await batchDeleteButton.isEnabled()) {
      await batchDeleteButton.click();
      await this.page.waitForTimeout(300);
      await this.confirmDialog();
    }
  }

  /**
   * Get asset annotations
   */
  async getAssetAnnotations(assetId: string): Promise<Array<{ user: string; content: string; createdAt: string }>> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-message), button:has-text("备注")').click();
    await this.waitForDrawer();

    const annotations: Array<{ user: string; content: string; createdAt: string }> = [];
    const annotationItems = this.page.locator('.annotation-item');
    const count = await annotationItems.count();

    for (let i = 0; i < count; i++) {
      const user = await annotationItems.nth(i).locator('.user-name').textContent() || '';
      const content = await annotationItems.nth(i).locator('.content').textContent() || '';
      const createdAt = await annotationItems.nth(i).locator('.created-at').textContent() || '';
      annotations.push({ user: user.trim(), content: content.trim(), createdAt: createdAt.trim() });
    }

    await this.page.locator('.ant-drawer-close').click();
    return annotations;
  }

  /**
   * Add asset annotation
   */
  async addAssetAnnotation(assetId: string, content: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has(.anticon-message), button:has-text("备注")').click();
    await this.waitForDrawer();

    const textarea = this.page.locator('.ant-drawer-body textarea[placeholder*="备注"]');
    await textarea.fill(content);
    await this.page.locator('.ant-drawer-body button:has-text("添加")').click();
    await this.page.waitForTimeout(500);

    await this.page.locator('.ant-drawer-close').click();
  }

  /**
   * Get related assets
   */
  async getRelatedAssets(assetId: string): Promise<string[]> {
    const row = this.findTableRowByText(assetId);
    await row.locator('a').click();
    await this.assetProfileDrawer.waitFor({ state: 'visible' });

    const relatedAssets: string[] = [];
    const relatedItems = this.page.locator('.ant-drawer-body .related-asset-item');
    const count = await relatedItems.count();

    for (let i = 0; i < Math.min(count, 10); i++) {
      const name = await relatedItems.nth(i).locator('.asset-name').textContent() || '';
      if (name) relatedAssets.push(name.trim());
    }

    await this.closeAssetProfile();
    return relatedAssets;
  }

  /**
   * Run AI value assessment
   */
  async runAiValueAssessment(assetId: string): Promise<void> {
    const row = this.findTableRowByText(assetId);
    await row.locator('button:has-text("AI评估")').click();
    await this.aiValueModal.waitFor({ state: 'visible' });

    await this.aiValueModal.locator('button:has-text("开始评估")').click();
    await this.page.waitForTimeout(3000);

    await this.aiValueModal.locator('.ant-modal-close, button:has-text("关闭")').click();
    await this.aiValueModal.waitFor({ state: 'hidden' }).catch(() => {});
  }
}
