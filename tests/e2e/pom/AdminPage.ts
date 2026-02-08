/**
 * Admin Page Object Model
 *
 * Page: /admin
 * Features: User management, role management, audit logs, cost reports
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class AdminPage extends BasePage {
  readonly PAGE_PATH = '/admin';

  // Menu locators
  readonly usersMenu: Locator;
  readonly rolesMenu: Locator;
  readonly auditMenu: Locator;
  readonly costsMenu: Locator;
  readonly settingsMenu: Locator;

  // Users tab locators
  readonly createUserButton: Locator;
  readonly usernameInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly roleSelect: Locator;
  readonly saveUserButton: Locator;
  readonly usersTable: Locator;

  // Roles tab locators
  readonly createRoleButton: Locator;
  readonly roleNameInput: Locator;
  readonly permissionsList: Locator;
  readonly saveRoleButton: Locator;
  readonly rolesTable: Locator;

  // Audit tab locators
  readonly auditTable: Locator;
  readonly dateRangePicker: Locator;
  readonly exportAuditButton: Locator;
  readonly filterInput: Locator;

  // Costs tab locators
  readonly costTable: Locator;
  readonly costChart: Locator;
  readonly exportCostButton: Locator;
  readonly timeRangeSelect: Locator;

  constructor(page: Page) {
    super(page);

    // Menu locators
    this.usersMenu = page.locator('.ant-menu-item:has-text("用户"), .ant-menu-item:has-text("Users"), a[href*="/admin/users"]');
    this.rolesMenu = page.locator('.ant-menu-item:has-text("角色"), .ant-menu-item:has-text("Roles"), a[href*="/admin/roles"]');
    this.auditMenu = page.locator('.ant-menu-item:has-text("审计"), .ant-menu-item:has-text("Audit"), a[href*="/admin/audit"]');
    this.costsMenu = page.locator('.ant-menu-item:has-text("成本"), .ant-menu-item:has-text("Cost"), a[href*="/admin/costs"]');
    this.settingsMenu = page.locator('.ant-menu-item:has-text("设置"), .ant-menu-item:has-text("Settings")');

    // Users tab locators
    this.createUserButton = page.locator('button:has-text("新建用户"), button:has-text("创建"), button:has(.anticon-plus)');
    this.usernameInput = page.locator('.ant-modal input[name="username"], .ant-modal label:has-text("用户名") + input');
    this.emailInput = page.locator('.ant-modal input[name="email"], .ant-modal label:has-text("邮箱") + input');
    this.passwordInput = page.locator('.ant-modal input[type="password"], .ant-modal label:has-text("密码") + input');
    this.roleSelect = page.locator('.ant-modal .ant-select:has-text("角色"), .ant-modal label:has-text("角色") + .ant-select');
    this.saveUserButton = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定"), .ant-modal .ant-btn-primary');
    this.usersTable = page.locator('.ant-table');

    // Roles tab locators
    this.createRoleButton = page.locator('button:has-text("新建角色"), button:has-text("创建")');
    this.roleNameInput = page.locator('.ant-modal input[name="name"], .ant-modal label:has-text("角色名称") + input');
    this.permissionsList = page.locator('.ant-modal .ant-checkbox-group, .permissions-list');
    this.saveRoleButton = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定")');
    this.rolesTable = page.locator('.ant-table');

    // Audit tab locators
    this.auditTable = page.locator('.ant-table');
    this.dateRangePicker = page.locator('.ant-picker-range');
    this.exportAuditButton = page.locator('button:has-text("导出"), button:has-text("Export")');
    this.filterInput = page.locator('input[placeholder*="筛选"], input[placeholder*="filter"]');

    // Costs tab locators
    this.costTable = page.locator('.ant-table');
    this.costChart = page.locator('.cost-chart, .ant-chart, canvas');
    this.exportCostButton = page.locator('button:has-text("导出"), button:has-text("Export")');
    this.timeRangeSelect = page.locator('.ant-select:has-text("时间"), .ant-select:has-text("Time")');
  }

  /**
   * Navigate to admin page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.PAGE_PATH);
    await this.waitForStable();
  }

  /**
   * Navigate to users section
   */
  async gotoUsers(): Promise<void> {
    await this.page.goto('/admin/users');
    await this.waitForStable();
  }

  /**
   * Navigate to roles section
   */
  async gotoRoles(): Promise<void> {
    await this.page.goto('/admin/roles');
    await this.waitForStable();
  }

  /**
   * Navigate to audit section
   */
  async gotoAudit(): Promise<void> {
    await this.page.goto('/admin/audit');
    await this.waitForStable();
  }

  /**
   * Navigate to costs section
   */
  async gotoCosts(): Promise<void> {
    await this.page.goto('/admin/costs');
    await this.waitForStable();
  }

  // ============================================================================
  // Users Management
  // ============================================================================

  /**
   * Click create user button
   */
  async clickCreateUser(): Promise<void> {
    await this.gotoUsers();
    await this.createUserButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill user form
   */
  async fillUserForm(data: {
    username: string;
    email: string;
    password: string;
    role?: string;
  }): Promise<void> {
    // Username
    await this.usernameInput.fill(data.username);
    await this.page.waitForTimeout(200);

    // Email
    await this.emailInput.fill(data.email);
    await this.page.waitForTimeout(200);

    // Password
    await this.passwordInput.fill(data.password);
    await this.page.waitForTimeout(200);

    // Role (optional)
    if (data.role && await this.roleSelect.isVisible()) {
      await this.roleSelect.click();
      await this.page.waitForTimeout(200);
      await this.page.locator(`.ant-select-item:has-text("${data.role}")`).click();
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Create a user
   */
  async createUser(data: {
    username: string;
    email: string;
    password: string;
    role?: string;
  }): Promise<boolean> {
    await this.clickCreateUser();
    await this.fillUserForm(data);

    await this.saveUserButton.first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Get user count
   */
  async getUserCount(): Promise<number> {
    await this.gotoUsers();
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if user exists
   */
  async userExists(username: string): Promise<boolean> {
    await this.gotoUsers();
    const row = this.usersTable.locator('.ant-table-row').filter({ hasText: username });
    return await row.count() > 0;
  }

  /**
   * Delete a user
   */
  async deleteUser(username: string): Promise<boolean> {
    await this.gotoUsers();

    const row = this.usersTable.locator('.ant-table-row').filter({ hasText: username });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("删除")').click();
    await this.confirmDialog();

    return await this.verifyToastMessage('success');
  }

  /**
   * Edit user role
   */
  async editUserRole(username: string, newRole: string): Promise<boolean> {
    await this.gotoUsers();

    const row = this.usersTable.locator('.ant-table-row').filter({ hasText: username });
    await row.locator('button:has(.anticon-ellipsis), .ant-dropdown-trigger').first().click();
    await this.page.waitForTimeout(300);

    await this.page.locator('.ant-dropdown-menu-item:has-text("编辑")').click();
    await this.page.waitForTimeout(500);

    await this.roleSelect.click();
    await this.page.waitForTimeout(200);
    await this.page.locator(`.ant-select-item:has-text("${newRole}")`).click();
    await this.page.waitForTimeout(200);

    await this.saveUserButton.click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  // ============================================================================
  // Roles Management
  // ============================================================================

  /**
   * Click create role button
   */
  async clickCreateRole(): Promise<void> {
    await this.gotoRoles();
    await this.createRoleButton.first().click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill role form
   */
  async fillRoleForm(data: {
    name: string;
    permissions?: string[];
  }): Promise<void> {
    // Name
    await this.roleNameInput.fill(data.name);
    await this.page.waitForTimeout(200);

    // Permissions (optional)
    if (data.permissions && data.permissions.length > 0) {
      for (const permission of data.permissions) {
        const checkbox = this.page.locator(`.ant-checkbox-wrapper:has-text("${permission}")`);
        if (await checkbox.isVisible()) {
          await checkbox.locator('.ant-checkbox-input').check();
          await this.page.waitForTimeout(100);
        }
      }
    }
  }

  /**
   * Create a role
   */
  async createRole(data: {
    name: string;
    permissions?: string[];
  }): Promise<boolean> {
    await this.clickCreateRole();
    await this.fillRoleForm(data);

    await this.saveRoleButton.first().click();
    await this.page.waitForTimeout(1000);

    return await this.verifyToastMessage('success');
  }

  /**
   * Get role count
   */
  async getRoleCount(): Promise<number> {
    await this.gotoRoles();
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Check if role exists
   */
  async roleExists(name: string): Promise<boolean> {
    await this.gotoRoles();
    const row = this.rolesTable.locator('.ant-table-row').filter({ hasText: name });
    return await row.count() > 0;
  }

  // ============================================================================
  // Audit Logs
  // ============================================================================

  /**
   * Get audit log count
   */
  async getAuditLogCount(): Promise<number> {
    await this.gotoAudit();
    await this.waitForTableLoad();
    return await this.getTableRowCount();
  }

  /**
   * Filter audit logs by user
   */
  async filterAuditByUser(username: string): Promise<void> {
    await this.gotoAudit();
    await this.filterInput.fill(username);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Filter audit logs by date range
   */
  async filterAuditByDateRange(startDate: string, endDate: string): Promise<void> {
    await this.gotoAudit();
    await this.dateRangePicker.click();
    await this.page.waitForTimeout(300);

    // Select dates (implementation depends on date picker component)
    await this.page.waitForTimeout(500);
  }

  /**
   * Export audit logs
   */
  async exportAuditLogs(): Promise<boolean> {
    await this.gotoAudit();

    if (await this.exportAuditButton.isVisible()) {
      await this.exportAuditButton.click();
      await this.page.waitForTimeout(500);
      return true;
    }

    return false;
  }

  // ============================================================================
  // Cost Reports
  // ============================================================================

  /**
   * Get cost report data
   */
  async getCostReportData(): Promise<{
    totalCost: string;
    byService: Array<{ service: string; cost: string }>;
  }> {
    await this.gotoCosts();
    await this.page.waitForTimeout(1000);

    // Get total cost from the page
    const totalCostElement = this.page.locator('.total-cost, .cost-summary .amount');
    const totalCost = await totalCostElement.textContent() || '0';

    // Get cost by service from table
    await this.waitForTableLoad();
    const rows = this.costTable.locator('.ant-table-row');
    const count = await rows.count();
    const byService: Array<{ service: string; cost: string }> = [];

    for (let i = 0; i < Math.min(count, 10); i++) {
      const cells = rows.nth(i).locator('.ant-table-cell');
      const service = await cells.nth(0).textContent() || '';
      const cost = await cells.nth(1).textContent() || '';
      byService.push({ service: service.trim(), cost: cost.trim() });
    }

    return { totalCost, byService };
  }

  /**
   * Change time range for cost report
   */
  async changeCostTimeRange(range: '7d' | '30d' | '90d' | 'custom'): Promise<void> {
    await this.gotoCosts();

    if (await this.timeRangeSelect.isVisible()) {
      await this.timeRangeSelect.click();
      await this.page.waitForTimeout(200);
      await this.page.locator(`.ant-select-item:has-text("${range}")`).click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Export cost report
   */
  async exportCostReport(): Promise<boolean> {
    await this.gotoCosts();

    if (await this.exportCostButton.isVisible()) {
      await this.exportCostButton.click();
      await this.page.waitForTimeout(500);
      return true;
    }

    return false;
  }

  /**
   * Check if cost chart is visible
   */
  async isCostChartVisible(): Promise<boolean> {
    await this.gotoCosts();
    await this.page.waitForTimeout(1000);
    return await this.costChart.isVisible().catch(() => false);
  }

  // ============================================================================
  // Common Methods
  // ============================================================================

  /**
   * Search in admin tables
   */
  async search(query: string): Promise<void> {
    const searchInput = this.page.locator('input[placeholder*="搜索"], .ant-input-search input');
    await searchInput.fill(query);
    await this.page.waitForTimeout(1000);
  }

  /**
   * Refresh current table
   */
  async refresh(): Promise<void> {
    const refreshButton = this.page.locator('button:has(.anticon-reload), button:has-text("刷新")');
    await refreshButton.click();
    await this.waitForTableLoad();
  }
}
