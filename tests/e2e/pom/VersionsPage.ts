/**
 * Data Version Management Page Object Model
 *
 * Page: /data/versions
 * Features: Snapshots, Version Comparison, Version History
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class VersionsPage extends BasePage {
  readonly PAGE_PATH = '/data/versions';

  // Tab locators
  readonly snapshotsTab: Locator;
  readonly historyTab: Locator;

  // Snapshots tab locators
  readonly createSnapshotButton: Locator;
  readonly snapshotTable: Locator;
  readonly compareSnapshotsButton: Locator;
  readonly snapshotCheckbox: (index: number) => Locator;

  // Comparison locators
  readonly comparisonModal: Locator;
  readonly comparisonSummary: Locator;
  readonly comparisonNewTables: Locator;
  readonly comparisonDeletedTables: Locator;
  readonly comparisonModifiedTables: Locator;
  readonly viewSqlButton: Locator;
  readonly copyAllSqlButton: Locator;

  // History tab locators
  readonly timeline: Locator;
  readonly timelineItems: Locator;
  readonly currentVersionBadge: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize tab locators
    this.snapshotsTab = page.locator('.ant-tabs-tab:has-text("快照"), .ant-tabs-tab:has-text("Snapshots")');
    this.historyTab = page.locator('.ant-tabs-tab:has-text("历史"), .ant-tabs-tab:has-text("History")');

    // Snapshots tab locators
    this.createSnapshotButton = page.locator('button:has-text("创建版本"), button:has-text("创建快照"), button:has-text("Create Version")').first();
    this.snapshotTable = page.locator('[data-testid="snapshot-table"], .snapshots-table');
    this.compareSnapshotsButton = page.locator('button:has-text("对比选中"), button:has-text("Compare Selected")');
    this.snapshotCheckbox = (index: number) => page.locator(`.ant-table-tbody .ant-table-row`).nth(index).locator('input[type="checkbox"]');

    // Comparison locators
    this.comparisonModal = page.locator('.ant-modal:has-text("对比"), [data-testid="comparison-modal"]');
    this.comparisonSummary = page.locator('[data-testid="comparison-summary"]');
    this.comparisonNewTables = page.locator('[data-testid="new-tables"], .new-tables-list');
    this.comparisonDeletedTables = page.locator('[data-testid="deleted-tables"], .deleted-tables-list');
    this.comparisonModifiedTables = page.locator('[data-testid="modified-tables"], .modified-tables-list');
    this.viewSqlButton = page.locator('button:has-text("查看 SQL"), button:has-text("View SQL")');
    this.copyAllSqlButton = page.locator('button:has-text("复制全部"), button:has-text("Copy All")');

    // History tab locators
    this.timeline = page.locator('.ant-timeline, [data-testid="version-timeline"]');
    this.timelineItems = page.locator('.ant-timeline-item');
    this.currentVersionBadge = page.locator('.ant-timeline-item .ant-badge-status-success, [data-testid="current-version"]');
  }

  /**
   * Navigate to versions page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Switch to snapshots tab
   */
  async switchToSnapshots(): Promise<void> {
    if (await this.snapshotsTab.isVisible()) {
      await this.snapshotsTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Switch to history tab
   */
  async switchToHistory(): Promise<void> {
    if (await this.historyTab.isVisible()) {
      await this.historyTab.click();
      await this.waitForStable();
    }
  }

  /**
   * Get snapshot count
   */
  async getSnapshotCount(): Promise<number> {
    await this.waitForLoading();
    const rows = this.snapshotTable.locator('.ant-table-body .ant-table-row');
    return await rows.count();
  }

  /**
   * Select snapshot by index
   */
  async selectSnapshot(index: number): Promise<void> {
    await this.snapshotCheckbox(index).check();
  }

  /**
   * Compare selected snapshots
   */
  async compareSelectedSnapshots(): Promise<void> {
    await this.compareSnapshotsButton.click();
    await this.comparisonModal.waitFor({ state: 'visible' });
  }

  /**
   * Get comparison summary text
   */
  async getComparisonSummary(): Promise<string> {
    return await this.comparisonSummary.textContent() || '';
  }

  /**
   * Get new tables count from comparison
   */
  async getNewTablesCount(): Promise<number> {
    const countText = await this.comparisonNewTables.locator('.ant-tag, .count').textContent() || '0';
    return parseInt(countText.replace(/\D/g, '')) || 0;
  }

  /**
   * Get deleted tables count from comparison
   */
  async getDeletedTablesCount(): Promise<number> {
    const countText = await this.comparisonDeletedTables.locator('.ant-tag, .count').textContent() || '0';
    return parseInt(countText.replace(/\D/g, '')) || 0;
  }

  /**
   * Get modified tables count from comparison
   */
  async getModifiedTablesCount(): Promise<number> {
    const countText = await this.comparisonModifiedTables.locator('.ant-tag, .count').textContent() || '0';
    return parseInt(countText.replace(/\D/g, '')) || 0;
  }

  /**
   * View SQL for comparison
   */
  async viewComparisonSql(): Promise<void> {
    await this.viewSqlButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get timeline item count
   */
  async getTimelineItemCount(): Promise<number> {
    return await this.timelineItems.count();
  }

  /**
   * Check if current version badge is visible
   */
  async isCurrentVersionBadgeVisible(): Promise<boolean> {
    return await this.currentVersionBadge.isVisible();
  }

  /**
   * Close comparison modal
   */
  async closeComparisonModal(): Promise<void> {
    await this.comparisonModal.locator('.ant-modal-close, button:has-text("关闭")').click();
    await this.comparisonModal.waitFor({ state: 'hidden' }).catch(() => {});
  }

  // =============================================================================
  // Extended Methods (Phase 3)
  // =============================================================================

  /**
   * Create a new snapshot
   * Returns true if successful, false otherwise
   */
  async createSnapshot(name: string, description?: string): Promise<boolean> {
    try {
      await this.createSnapshotButton.click({ timeout: 10000 });
      await this.waitForModal();

      const modal = this.page.locator('.ant-modal:visible');

      // Wait for input to be ready
      const nameInput = modal.locator('input[name="name"], input[placeholder*="名称"], input.ant-input').first();
      await nameInput.waitFor({ state: 'visible', timeout: 5000 });
      await nameInput.fill(name);

      if (description) {
        const descInput = modal.locator('textarea[name="description"], textarea[placeholder*="描述"], textarea.ant-input').first();
        if (await descInput.count() > 0) {
          await descInput.fill(description);
        }
      }

      const confirmButton = modal.locator('button:has-text("确定"), button:has-text("创建"), button[type="submit"]').first();
      await confirmButton.click();
      await this.waitForModalClose();
      await this.page.waitForTimeout(1000);
      return true;
    } catch (error) {
      console.log('⚠ 创建快照失败:', (error as Error).message);
      return false;
    }
  }

  /**
   * View snapshot details
   */
  async viewSnapshotDetails(snapshotName: string): Promise<void> {
    const row = this.findTableRowByText(snapshotName);
    await row.locator('a, button:has-text("详情")').click();
    await this.waitForDrawer();
  }

  /**
   * Edit snapshot remark
   */
  async editSnapshotRemark(snapshotName: string, remark: string): Promise<void> {
    const row = this.findTableRowByText(snapshotName);
    await row.locator('button:has(.anticon-edit), button:has-text("编辑")').click();
    await this.waitForModal();

    await this.page.locator('.ant-modal:visible textarea[name="remark"]').fill(remark);
    await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
    await this.waitForModalClose();
  }

  /**
   * Download snapshot
   */
  async downloadSnapshot(snapshotName: string): Promise<void> {
    const row = this.findTableRowByText(snapshotName);
    await row.locator('button:has(.anticon-download), button:has-text("下载")').click();
    await this.page.waitForTimeout(2000);
  }

  /**
   * Expand diff item in comparison
   */
  async expandDiffItem(diffId: string): Promise<void> {
    const diffRow = this.page.locator('.diff-row, .comparison-item').filter({ hasText: diffId });
    await diffRow.locator('.anticon-right, .anticon-down').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Filter diff by type
   */
  async filterDiffByType(diffType: 'new' | 'deleted' | 'modified'): Promise<void> {
    const filterButton = this.page.locator('.ant-segmented, .ant-radio-group');
    if (await filterButton.isVisible()) {
      await filterButton.locator(`:has-text("${diffType}")`).click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Export comparison result
   */
  async exportComparisonResult(): Promise<void> {
    const exportButton = this.comparisonModal.locator('button:has-text("导出"), button:has-text("Export")');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Rollback to version
   */
  async rollbackToVersion(versionId: string): Promise<void> {
    const rollbackButton = this.page.locator(`button[data-version="${versionId}"]`).locator('button:has-text("回滚"), button:has-text("Rollback")');
    if (await rollbackButton.isVisible()) {
      await rollbackButton.click();
      await this.page.waitForTimeout(300);

      await this.confirmDialog();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Get snapshot list
   */
  async getSnapshotList(): Promise<Array<{ name: string; description: string; createdAt: string }>> {
    const snapshots: Array<{ name: string; description: string; createdAt: string }> = [];

    const rows = this.snapshotTable.locator('.ant-table-body .ant-table-row');
    const count = await rows.count();

    for (let i = 0; i < count; i++) {
      const cells = rows.nth(i).locator('.ant-table-cell');
      const name = await cells.nth(0).textContent() || '';
      const description = await cells.nth(1).textContent() || '';
      const createdAt = await cells.nth(2).textContent() || '';
      snapshots.push({ name: name.trim(), description: description.trim(), createdAt: createdAt.trim() });
    }
    return snapshots;
  }

  /**
   * Select snapshots by name
   */
  async selectSnapshotsByName(names: string[]): Promise<void> {
    const rows = this.snapshotTable.locator('.ant-table-body .ant-table-row');
    const count = await rows.count();

    for (let i = 0; i < count; i++) {
      const nameCell = await rows.nth(i).locator('.ant-table-cell').nth(0).textContent() || '';
      if (names.some(n => nameCell.includes(n))) {
        await rows.nth(i).locator('input[type="checkbox"]').check();
      }
    }
  }

  /**
   * Get comparison diff details
   */
  async getComparisonDiffDetails(): Promise<{
    newTables: string[];
    deletedTables: string[];
    modifiedTables: Array<{ name: string; changes: string[] }>;
  }> {
    const result = {
      newTables: [] as string[],
      deletedTables: [] as string[],
      modifiedTables: [] as Array<{ name: string; changes: string[] }>
    };

    const newItems = this.comparisonNewTables.locator('.comparison-item, .diff-item');
    const newCount = await newItems.count();
    for (let i = 0; i < newCount; i++) {
      const text = await newItems.nth(i).textContent() || '';
      result.newTables.push(text.trim());
    }

    const deletedItems = this.comparisonDeletedTables.locator('.comparison-item, .diff-item');
    const deletedCount = await deletedItems.count();
    for (let i = 0; i < deletedCount; i++) {
      const text = await deletedItems.nth(i).textContent() || '';
      result.deletedTables.push(text.trim());
    }

    const modifiedItems = this.comparisonModifiedTables.locator('.comparison-item, .diff-item');
    const modifiedCount = await modifiedItems.count();
    for (let i = 0; i < modifiedCount; i++) {
      const text = await modifiedItems.nth(i).locator('.table-name, .item-title').textContent() || '';
      const changesText = await modifiedItems.nth(i).locator('.change-list').textContent() || '';
      result.modifiedTables.push({
        name: text.trim(),
        changes: changesText.split(',').map(c => c.trim())
      });
    }

    return result;
  }

  /**
   * Copy all SQL changes
   */
  async copyAllSql(): Promise<void> {
    await this.copyAllSqlButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get timeline items
   */
  async getTimelineItems(): Promise<Array<{ id: string; action: string; timestamp: string; user: string }>> {
    const items: Array<{ id: string; action: string; timestamp: string; user: string }> = [];

    const timelineElements = this.timeline.locator('.ant-timeline-item');
    const count = await timelineElements.count();

    for (let i = 0; i < count; i++) {
      const element = timelineElements.nth(i);
      const action = await element.locator('.timeline-action, .ant-timeline-item-content').textContent() || '';
      const timestamp = await element.locator('.timeline-time, .ant-timeline-item-time').textContent() || '';
      const user = await element.locator('.timeline-user, .ant-timeline-item-user').textContent() || '';
      items.push({ id: `item-${i}`, action: action.trim(), timestamp: timestamp.trim(), user: user.trim() });
    }
    return items;
  }

  /**
   * Filter timeline by date range
   */
  async filterTimelineByDate(startDate: Date, endDate: Date): Promise<void> {
    const filterButton = this.page.locator('button:has-text("筛选"), button:has-text("Filter")');
    if (await filterButton.isVisible()) {
      await filterButton.click();
      await this.page.waitForTimeout(300);

      const startInput = this.page.locator('.ant-modal:visible input[placeholder*="开始"]');
      await startInput.fill(startDate.toISOString().split('T')[0]);

      const endInput = this.page.locator('.ant-modal:visible input[placeholder*="结束"]');
      await endInput.fill(endDate.toISOString().split('T')[0]);

      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Delete snapshot
   */
  async deleteSnapshot(snapshotName: string): Promise<void> {
    const row = this.findTableRowByText(snapshotName);
    await row.locator('button:has(.anticon-delete), button:has-text("删除")').click();
    await this.page.waitForTimeout(300);

    await this.confirmDialog();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get version detail
   */
  async getVersionDetail(versionId: string): Promise<any> {
    const detailPanel = this.page.locator('.version-detail-panel, [data-version-id]');
    if (await detailPanel.isVisible()) {
      const name = await detailPanel.locator('.version-name').textContent() || '';
      const description = await detailPanel.locator('.version-description').textContent() || '';
      const createdAt = await detailPanel.locator('.version-created-at').textContent() || '';
      return { name: name.trim(), description: description.trim(), createdAt: createdAt.trim() };
    }
    return null;
  }

  /**
   * Compare with current version
   */
  async compareWithCurrent(snapshotName: string): Promise<void> {
    const row = this.findTableRowByText(snapshotName);
    await row.locator('button:has-text("对比"), button:has-text("Compare")').click();
    await this.comparisonModal.waitFor({ state: 'visible' });
  }

  /**
   * Get rollback history
   */
  async getRollbackHistory(): Promise<Array<{ fromVersion: string; toVersion: string; timestamp: string; user: string }>> {
    const history: Array<{ fromVersion: string; toVersion: string; timestamp: string; user: string }> = [];

    const historyRows = this.page.locator('.rollback-history .ant-table-row');
    const count = await historyRows.count();

    for (let i = 0; i < count; i++) {
      const cells = historyRows.nth(i).locator('.ant-table-cell');
      const fromVersion = await cells.nth(0).textContent() || '';
      const toVersion = await cells.nth(1).textContent() || '';
      const timestamp = await cells.nth(2).textContent() || '';
      const user = await cells.nth(3).textContent() || '';
      history.push({ fromVersion: fromVersion.trim(), toVersion: toVersion.trim(), timestamp: timestamp.trim(), user: user.trim() });
    }
    return history;
  }

  /**
   * Schedule auto snapshot
   */
  async scheduleAutoSnapshot(cronExpression: string): Promise<void> {
    const scheduleButton = this.page.locator('button:has-text("定时快照"), button:has-text("Schedule")');
    if (await scheduleButton.isVisible()) {
      await scheduleButton.click();
      await this.waitForModal();

      await this.page.locator('.ant-modal:visible input[name="cron"]').fill(cronExpression);
      await this.page.locator('.ant-modal:visible button:has-text("确定")').click();
      await this.waitForModalClose();
    }
  }
}
