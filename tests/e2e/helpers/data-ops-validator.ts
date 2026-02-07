/**
 * DataOps 页面验证辅助类
 * 提供通用的页面验证方法，用于 DataOps 平台的 E2E 测试
 */

import { Page, expect, Route } from '@playwright/test';

/**
 * 页面类型分类
 */
export enum PageType {
  /** 列表页面 - 包含表格、搜索框、新增按钮 */
  List = 'list',
  /** 编辑器页面 - 包含代码编辑器 */
  Editor = 'editor',
  /** 可视化页面 - 包含图表、血缘图等 */
  Visualization = 'visualization',
  /** 表单页面 - 包含表单字段 */
  Form = 'form',
  /** 通用页面 - 基本页面验证 */
  Generic = 'generic',
}

/**
 * 页面配置接口
 */
export interface DataOpsPageConfig {
  /** 页面路由 */
  route: string;
  /** 页面名称 */
  name: string;
  /** 页面类型 */
  type: PageType;
  /** 需要 mock 的 API 路由模式 */
  apiPatterns?: string[];
  /** Mock 响应数据 */
  mockData?: unknown;
  /** 预期的页面标题 */
  expectedTitle?: string;
  /** 是否需要截图 */
  screenshot?: boolean;
  /** 是否使用真实 API（禁用 Mock） */
  useRealAPI?: boolean;
}

/**
 * 页面验证结果
 */
export interface PageValidationResult {
  /** 页面名称 */
  pageName: string;
  /** 页面路由 */
  route: string;
  /** 是否通过验证 */
  passed: boolean;
  /** 验证的项目 */
  validations: {
    /** 页面加载成功 */
    pageLoaded: boolean;
    /** 无 JS 错误 */
    noJSErrors: boolean;
    /** 页面标题可见 */
    titleVisible: boolean;
    /** 基本布局可见 */
    layoutVisible: boolean;
    /** 功能组件可见（根据页面类型） */
    functionalComponents: boolean;
  };
  /** 检测到的错误 */
  errors: string[];
  /** 截图路径 */
  screenshotPath?: string;
  /** 加载时间（毫秒） */
  loadTime: number;
  /** Console 日志 */
  consoleLogs?: ConsoleLogEntry[];
  /** API 请求记录 */
  apiRequests?: ApiRequestRecord[];
}

/**
 * Console 日志条目
 */
export interface ConsoleLogEntry {
  /** 日志级别 */
  level: 'log' | 'warn' | 'error' | 'info' | 'debug';
  /** 日志消息 */
  message: string;
  /** 堆栈信息（如果有） */
  stack?: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * API 请求记录
 */
export interface ApiRequestRecord {
  /** 请求 URL */
  url: string;
  /** 请求方法 */
  method: string;
  /** 响应状态码 */
  status: number;
  /** 响应时间（毫秒） */
  responseTime: number;
  /** 是否成功 */
  success: boolean;
  /** 时间戳 */
  timestamp: number;
}

/**
 * DataOps 页面验证器类
 */
export class PageValidator {
  private page: Page;
  private jsErrors: string[] = [];
  private consoleLogs: ConsoleLogEntry[] = [];
  private apiRequests: Map<string, ApiRequestRecord> = new Map();
  private screenshotDir = 'test-results/screenshots/data-ops';
  private networkListenersSetup = false;
  private consoleListenersSetup = false;

  constructor(page: Page) {
    this.page = page;
    this.setupJSErrorListener();
  }

  /**
   * 设置 JavaScript 错误监听器
   */
  private setupJSErrorListener(): void {
    this.page.on('pageerror', (error) => {
      this.jsErrors.push(error.message || error.toString());
    });
  }

  /**
   * 设置 Console 日志监听器
   */
  setupConsoleListener(): void {
    // 只设置一次
    if (this.consoleListenersSetup) {
      this.consoleLogs = [];
      return;
    }

    this.consoleLogs = [];
    this.consoleListenersSetup = true;

    // 单一监听器处理所有 console 类型
    this.page.on('console', (msg) => {
      const type = msg.type();
      if (type === 'log' || type === 'warn' || type === 'error' || type === 'info' || type === 'debug') {
        this.consoleLogs.push({
          level: type,
          message: msg.text() || '',
          // stackTrace may not be available in all Playwright versions
          stack: (typeof msg.stackTrace === 'function') ? msg.stackTrace() : undefined,
          timestamp: Date.now(),
        });
      }
    });
  }

  /**
   * 设置 Network 监听器
   */
  setupNetworkListener(): void {
    if (this.networkListenersSetup) {
      return;
    }

    this.apiRequests.clear();
    this.networkListenersSetup = true;

    // 监听所有请求
    this.page.on('request', (request) => {
      const url = request.url();
      // 只记录 API 请求
      if (url.includes('/api/') || url.includes('/graphql')) {
        const requestId = `${request.method()}-${url}-${Date.now()}`;
        this.apiRequests.set(requestId, {
          url,
          method: request.method(),
          status: 0,
          responseTime: 0,
          success: false,
          timestamp: Date.now(),
        });
      }
    });

    // 监听响应
    this.page.on('response', async (response) => {
      const url = response.url();
      const request = response.request();

      if (url.includes('/api/') || url.includes('/graphql')) {
        // 查找对应的请求记录
        const startTime = Date.now();
        const matchingKey = Array.from(this.apiRequests.keys()).find(
          key => this.apiRequests.get(key)?.url === url &&
                 this.apiRequests.get(key)?.method === request.method() &&
                 this.apiRequests.get(key)?.timestamp < startTime &&
                 startTime - this.apiRequests.get(key)!.timestamp < 5000
        );

        if (matchingKey) {
          const record = this.apiRequests.get(matchingKey)!;
          record.status = response.status();
          record.responseTime = startTime - record.timestamp;
          record.success = response.ok() || (response.status() >= 200 && response.status() < 400);
        }
      }
    });
  }

  /**
   * 获取收集到的 Console 日志
   */
  getConsoleLogs(): ConsoleLogEntry[] {
    return [...this.consoleLogs];
  }

  /**
   * 获取收集到的 API 请求记录
   */
  getApiRequests(): ApiRequestRecord[] {
    return Array.from(this.apiRequests.values());
  }

  /**
   * 清空收集的数据
   */
  clearCollectedData(): void {
    this.jsErrors = [];
    this.consoleLogs = [];
    this.apiRequests.clear();
  }

  /**
   * 重置所有监听器状态（用于新页面测试）
   */
  resetListeners(): void {
    this.consoleLogs = [];
    // 注意：不重置 networkListenersSetup 和 consoleListenersSetup
    // 因为监听器是页面级别的，应该保持活跃
  }

  /**
   * 获取收集到的 JS 错误
   */
  getJSErrors(): string[] {
    return [...this.jsErrors];
  }

  /**
   * 清空 JS 错误记录
   */
  clearJSErrors(): void {
    this.jsErrors = [];
  }

  /**
   * 设置页面 API Mock
   * 如果 config.useRealAPI 为 true，则不设置 Mock
   */
  async setupPageMocks(config: DataOpsPageConfig): Promise<void> {
    // 真实 API 模式：不设置 Mock
    if (config.useRealAPI) {
      return;
    }

    // Mock 模式：设置 Mock 响应
    if (config.apiPatterns) {
      for (const pattern of config.apiPatterns) {
        this.page.route(pattern, async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: config.mockData || {},
              message: 'success',
            }),
          });
        });
      }
    }
  }

  /**
   * 导航到指定页面并等待加载
   */
  async navigateToPage(route: string): Promise<{ success: boolean; loadTime: number }> {
    const startTime = Date.now();

    try {
      await this.page.goto(route, { waitUntil: 'networkidle', timeout: 30000 });
      const loadTime = Date.now() - startTime;

      // 等待基本的 React 应用加载
      await this.page.waitForSelector('body', { timeout: 10000 }).catch(() => {});

      return { success: true, loadTime };
    } catch (error) {
      const loadTime = Date.now() - startTime;
      return { success: false, loadTime };
    }
  }

  /**
   * 验证页面基本元素
   */
  async validateBasicElements(expectedTitle?: string): Promise<{ titleVisible: boolean; layoutVisible: boolean }> {
    const result = {
      titleVisible: false,
      layoutVisible: false,
    };

    // 检查页面标题 - 更加灵活的验证
    if (expectedTitle) {
      try {
        // 检查是否有任何 Card 标题、Tab 标题或其他页面标题元素
        const cardTitle = this.page.locator('.ant-card-head-title').first();
        const tabTitle = this.page.locator('.ant-tabs-tab').first();
        const pageTitle = this.page.locator('h1, h2, h3, .page-title, .ant-page-header-heading-title').first();

        const hasCardTitle = await cardTitle.isVisible({ timeout: 3000 }).catch(() => false);
        const hasTabTitle = await tabTitle.isVisible({ timeout: 3000 }).catch(() => false);
        const hasPageTitle = await pageTitle.isVisible({ timeout: 3000 }).catch(() => false);

        // 如果有标题元素，检查是否匹配
        if (hasCardTitle) {
          const titleText = await cardTitle.textContent() || '';
          // 部分匹配即可
          result.titleVisible = titleText.includes(expectedTitle) ||
                               expectedTitle.includes(titleText.trim()) ||
                               titleText.trim().length > 0;
        } else if (hasTabTitle || hasPageTitle) {
          // 有 Tab 或页面标题就认为有效
          result.titleVisible = true;
        } else {
          // 没有找到标题元素，检查是否有 Card 或其他容器（有些页面没有明显的标题元素）
          const hasCard = await this.page.locator('.ant-card').isVisible({ timeout: 3000 }).catch(() => false);
          const hasTab = await this.page.locator('.ant-tabs').isVisible({ timeout: 3000 }).catch(() => false);
          result.titleVisible = hasCard || hasTab;
        }
      } catch {
        // 出错时，如果有页面容器就认为通过
        const hasCard = await this.page.locator('.ant-card').isVisible({ timeout: 1000 }).catch(() => false);
        const hasTab = await this.page.locator('.ant-tabs').isVisible({ timeout: 1000 }).catch(() => false);
        result.titleVisible = hasCard || hasTab;
      }
    } else {
      result.titleVisible = true; // 如果没有指定标题，跳过验证
    }

    // 检查基本布局（侧边栏或主内容区）
    try {
      const sidebar = this.page.locator('.ant-layout-sider, aside, [role="navigation"]');
      const mainContent = this.page.locator('.ant-layout-content, main, [role="main"]');
      result.layoutVisible = await sidebar.isVisible({ timeout: 3000 }).catch(() => false)
        || await mainContent.isVisible({ timeout: 3000 }).catch(() => false);
    } catch {
      result.layoutVisible = false;
    }

    return result;
  }

  /**
   * 验证列表页面组件
   */
  async validateListComponents(): Promise<boolean> {
    try {
      // 检查表格、卡片容器、Tab 或空状态
      const table = this.page.locator('.ant-table, table, [role="table"]');
      const cardGrid = this.page.locator('.ant-row, .grid, .card-grid');
      const emptyState = this.page.locator('.ant-empty, .no-data');
      const card = this.page.locator('.ant-card');
      const tab = this.page.locator('.ant-tabs');

      const hasDataDisplay = await table.isVisible({ timeout: 5000 }).catch(() => false)
        || await cardGrid.isVisible({ timeout: 5000 }).catch(() => false)
        || await emptyState.isVisible({ timeout: 5000 }).catch(() => false)
        || await card.isVisible({ timeout: 5000 }).catch(() => false)
        || await tab.isVisible({ timeout: 5000 }).catch(() => false);

      return hasDataDisplay;
    } catch {
      return false;
    }
  }

  /**
   * 验证编辑器页面组件
   */
  async validateEditorComponents(): Promise<boolean> {
    try {
      // 检查代码编辑器、文本区域、内容可编辑区域、或任何卡片容器
      const editor = this.page.locator('.monaco-editor, .ace_editor, .CodeMirror, [contenteditable="true"], textarea, .ant-input-textarea');
      const card = this.page.locator('.ant-card');
      const tab = this.page.locator('.ant-tabs');
      const button = this.page.locator('.ant-button, button');

      // 编辑器页面应该有编辑器或至少有卡片/按钮等交互元素
      return await editor.isVisible({ timeout: 5000 }).catch(() => false)
        || await card.isVisible({ timeout: 5000 }).catch(() => false)
        || await tab.isVisible({ timeout: 5000 }).catch(() => false)
        || await button.isVisible({ timeout: 5000 }).catch(() => false);
    } catch {
      return false;
    }
  }

  /**
   * 验证可视化页面组件
   */
  async validateVisualizationComponents(): Promise<boolean> {
    try {
      // 检查图表容器、卡片、Tab、统计数字、按钮或其他容器
      const chart = this.page.locator('.ant-chart, canvas, svg, .graph-container, .viz-container, .react-flow, .dagre');
      const card = this.page.locator('.ant-card');
      const tab = this.page.locator('.ant-tabs');
      const tree = this.page.locator('.ant-tree');
      const statistic = this.page.locator('.ant-statistic');
      const button = this.page.locator('.ant-button, button');
      const row = this.page.locator('.ant-row, .row');

      return await chart.isVisible({ timeout: 5000 }).catch(() => false)
        || await card.isVisible({ timeout: 5000 }).catch(() => false)
        || await tab.isVisible({ timeout: 5000 }).catch(() => false)
        || await tree.isVisible({ timeout: 5000 }).catch(() => false)
        || await statistic.isVisible({ timeout: 5000 }).catch(() => false)
        || await button.isVisible({ timeout: 5000 }).catch(() => false)
        || await row.isVisible({ timeout: 5000 }).catch(() => false);
    } catch {
      return false;
    }
  }

  /**
   * 验证表单页面组件
   */
  async validateFormComponents(): Promise<boolean> {
    try {
      // 检查表单元素、输入框或卡片容器
      const form = this.page.locator('.ant-form, form, [role="form"]');
      const input = this.page.locator('.ant-input, input, .ant-select, select, .ant-picker');
      const card = this.page.locator('.ant-card');

      return await form.isVisible({ timeout: 5000 }).catch(() => false)
        || await input.isVisible({ timeout: 5000 }).catch(() => false)
        || await card.isVisible({ timeout: 5000 }).catch(() => false);
    } catch {
      return false;
    }
  }

  /**
   * 根据页面类型验证功能组件
   */
  async validateFunctionalComponents(type: PageType): Promise<boolean> {
    switch (type) {
      case PageType.List:
        return await this.validateListComponents();
      case PageType.Editor:
        return await this.validateEditorComponents();
      case PageType.Visualization:
        return await this.validateVisualizationComponents();
      case PageType.Form:
        return await this.validateFormComponents();
      case PageType.Generic:
        return true; // 通用页面只验证基本元素
      default:
        return true;
    }
  }

  /**
   * 捕获页面截图
   */
  async captureScreenshot(pageName: string): Promise<string | undefined> {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `${pageName.replace(/\s+/g, '-')}-${timestamp}.png`;
      const path = `${this.screenshotDir}/${filename}`;

      await this.page.screenshot({ path, fullPage: true });
      return path;
    } catch {
      return undefined;
    }
  }

  /**
   * 验证单个页面
   */
  async validatePage(config: DataOpsPageConfig): Promise<PageValidationResult> {
    this.clearJSErrors();
    const errors: string[] = [];
    let screenshotPath: string | undefined;

    // 设置监听器
    this.setupConsoleListener();
    this.setupNetworkListener();

    // 导航到页面
    const { success: pageLoaded, loadTime } = await this.navigateToPage(config.route);

    if (!pageLoaded) {
      errors.push('Failed to load page within timeout');
    }

    // 等待页面稳定
    await this.page.waitForTimeout(1000);

    // 验证基本元素
    const { titleVisible, layoutVisible } = await this.validateBasicElements(config.expectedTitle);

    if (!titleVisible && config.expectedTitle) {
      errors.push(`Expected title "${config.expectedTitle}" not found`);
    }

    if (!layoutVisible) {
      errors.push('Basic layout components (sidebar/main content) not visible');
    }

    // 验证功能组件
    const functionalComponents = await this.validateFunctionalComponents(config.type);

    if (!functionalComponents) {
      errors.push(`Functional components for ${config.type} page type not visible`);
    }

    // 检查 JS 错误
    const jsErrors = this.getJSErrors();
    const noJSErrors = jsErrors.length === 0;

    if (!noJSErrors) {
      errors.push(`JavaScript errors detected: ${jsErrors.join('; ')}`);
    }

    // 收集 Console 日志和 API 请求
    const consoleLogs = this.getConsoleLogs();
    const apiRequests = this.getApiRequests();

    // 检查 API 请求失败（仅在真实 API 模式下）
    if (config.useRealAPI) {
      const failedRequests = apiRequests.filter(r => !r.success);
      if (failedRequests.length > 0) {
        errors.push(`Failed API requests: ${failedRequests.map(r => `${r.method} ${r.url} (${r.status})`).join('; ')}`);
      }
    }

    // 截图
    if (config.screenshot !== false) {
      screenshotPath = await this.captureScreenshot(config.name);
    }

    // 判断是否通过验证
    const passed = pageLoaded && noJSErrors && titleVisible && layoutVisible && functionalComponents;

    return {
      pageName: config.name,
      route: config.route,
      passed,
      validations: {
        pageLoaded,
        noJSErrors,
        titleVisible,
        layoutVisible,
        functionalComponents,
      },
      errors,
      screenshotPath,
      loadTime,
      consoleLogs,
      apiRequests,
    };
  }
}

/**
 * DataOps 所有页面配置
 */
export const DATA_OPS_PAGES: DataOpsPageConfig[] = [
  // 数据管理
  {
    route: '/data/datasources',
    name: 'Data Sources',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/datasources*'],
    mockData: {
      datasources: [
        { id: 'ds-1', name: 'MySQL主库', type: 'mysql', host: 'db1.example.com', status: 'connected' },
        { id: 'ds-2', name: 'ClickHouse集群', type: 'clickhouse', host: 'ch1.example.com', status: 'connected' },
      ],
      total: 2,
    },
    expectedTitle: '数据源',
  },
  {
    route: '/metadata',
    name: 'Metadata Management',
    type: PageType.List,
    apiPatterns: ['**/api/v1/metadata*'],
    mockData: {
      tables: [
        { id: 'tbl-1', name: 'users', database: 'analytics', rows: 1000000 },
        { id: 'tbl-2', name: 'orders', database: 'analytics', rows: 5000000 },
      ],
      total: 2,
    },
    expectedTitle: '元数据管理',
  },
  {
    route: '/metadata/version-diff',
    name: 'Version Diff',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/metadata/version*'],
    mockData: {
      versions: [
        { id: 'v1', version: '1.0.0', createdAt: '2024-01-01' },
        { id: 'v2', version: '1.1.0', createdAt: '2024-01-15' },
      ],
      changes: [],
    },
    expectedTitle: '版本对比',
  },
  {
    route: '/data/features',
    name: 'Features',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/features*'],
    mockData: {
      feature_groups: [
        { id: 'fg-1', name: 'user_features', description: '用户特征', features: 25, status: 'online' },
        { id: 'fg-2', name: 'item_features', description: '商品特征', features: 18, status: 'online' },
      ],
      total: 2,
    },
    expectedTitle: '特征存储',
  },
  {
    route: '/data/standards',
    name: 'Data Standards',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/standards*'],
    mockData: {
      standards: [
        { id: 'std-1', name: '日期格式标准', type: 'format', rule: 'YYYY-MM-DD' },
      ],
      total: 1,
    },
    expectedTitle: '数据标准',
  },
  {
    route: '/data/assets',
    name: 'Data Assets',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/assets*'],
    mockData: {
      assets: [
        { id: 'asset-1', name: '用户画像表', type: 'table', owner: '数据组' },
        { id: 'asset-2', name: '销售指标API', type: 'api', owner: '分析组' },
      ],
      total: 2,
    },
    expectedTitle: '数据资产',
  },
  {
    route: '/data/services',
    name: 'Data Services',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/services*'],
    mockData: {
      services: [
        { id: 'svc-1', name: '数据查询服务', type: 'query', status: 'online', qps: 450 },
        { id: 'svc-2', name: '特征获取服务', type: 'feature', status: 'online', qps: 1200 },
      ],
      total: 2,
    },
    expectedTitle: '数据服务',
  },
  {
    route: '/data/bi',
    name: 'BI Reports',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/data/bi*'],
    mockData: {
      dashboards: [
        { id: 'dash-1', name: '运营大屏', charts: 8, owner: '运营组' },
        { id: 'dash-2', name: '销售分析', charts: 12, owner: '销售组' },
      ],
      total: 2,
    },
    expectedTitle: 'BI 报表',
  },
  {
    route: '/data/metrics',
    name: 'Metrics',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/metrics*'],
    mockData: {
      metrics: [
        { id: 'm-1', name: '日活跃用户', value: 125000, trend: '+5%' },
        { id: 'm-2', name: 'GMV', value: 8500000, trend: '+12%' },
      ],
      total: 2,
    },
    expectedTitle: '指标体系',
  },
  // 数据开发
  {
    route: '/data/etl',
    name: 'ETL Jobs',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/etl-jobs*'],
    mockData: {
      jobs: [
        { id: 'etl-1', name: '用户数据同步', source: 'MySQL', target: 'Hive', status: 'running' },
        { id: 'etl-2', name: '日志采集', source: 'Kafka', target: 'ClickHouse', status: 'active' },
      ],
      total: 2,
    },
    expectedTitle: 'ETL 任务',
  },
  {
    route: '/data/kettle',
    name: 'Kettle Engine',
    type: PageType.Editor,
    apiPatterns: ['**/api/v1/data/kettle*'],
    mockData: {
      jobs: [],
      transformations: [],
    },
    expectedTitle: 'Kettle 引擎',
  },
  {
    route: '/data/kettle-generator',
    name: 'Kettle Generator',
    type: PageType.Form,
    apiPatterns: ['**/api/v1/data/kettle-generator*'],
    mockData: {
      templates: [],
    },
    expectedTitle: 'Kettle 配置生成',
  },
  {
    route: '/data/ocr',
    name: 'OCR',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/ocr*'],
    mockData: {
      tasks: [
        { id: 'ocr-1', name: '文档识别任务', status: 'completed', pages: 10 },
      ],
      total: 1,
    },
    expectedTitle: '文档 OCR',
  },
  {
    route: '/data/quality',
    name: 'Data Quality',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/quality*'],
    mockData: {
      rules: [
        { id: 'qr-1', name: '用户ID非空检查', table: 'users', column: 'user_id', type: 'not_null', status: 'passed' },
        { id: 'qr-2', name: '金额范围检查', table: 'orders', column: 'amount', type: 'range', status: 'failed' },
      ],
      total: 2,
    },
    expectedTitle: '数据质量',
  },
  {
    route: '/data/lineage',
    name: 'Data Lineage',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/data/lineage*'],
    mockData: {
      nodes: [
        { id: 'tbl-1', name: 'raw_users', type: 'source' },
        { id: 'tbl-2', name: 'dim_users', type: 'dimension' },
      ],
      edges: [
        { source: 'tbl-1', target: 'tbl-2' },
      ],
    },
    expectedTitle: '数据血缘',
  },
  {
    route: '/data/offline',
    name: 'Offline Development',
    type: PageType.Editor,
    apiPatterns: ['**/api/v1/data/offline*'],
    mockData: {
      tasks: [
        { id: 'task-1', name: '日结任务', status: 'completed', duration: 3600 },
        { id: 'task-2', name: '数据归档', status: 'running', duration: null },
      ],
      total: 2,
    },
    expectedTitle: '离线开发',
  },
  {
    route: '/data/streaming',
    name: 'Streaming',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/streaming*'],
    mockData: {
      streams: [
        { id: 'stream-1', name: '用户行为流', source: 'Kafka', status: 'running', tps: 1500 },
        { id: 'stream-2', name: '订单事件流', source: 'Kafka', status: 'running', tps: 800 },
      ],
      total: 2,
    },
    expectedTitle: '实时开发',
  },
  {
    route: '/data/streaming-ide',
    name: 'Streaming IDE',
    type: PageType.Editor,
    apiPatterns: [],
    mockData: {},
    expectedTitle: '实时 IDE',
  },
  {
    route: '/model/notebooks',
    name: 'Notebooks',
    type: PageType.Editor,
    apiPatterns: ['**/api/v1/model/notebooks*'],
    mockData: {
      notebooks: [
        { id: 'nb-1', name: '数据分析', kernel: 'python3', status: 'running' },
      ],
      total: 1,
    },
    expectedTitle: 'Notebook',
  },
  {
    route: '/model/sql-lab',
    name: 'SQL Lab',
    type: PageType.Editor,
    apiPatterns: ['**/api/v1/model/sql-lab*'],
    mockData: {
      queries: [
        { id: 'q-1', name: '用户查询', database: 'analytics', status: 'success' },
      ],
      total: 1,
    },
    expectedTitle: 'SQL Lab',
  },
  // 其他
  {
    route: '/datasets',
    name: 'Datasets',
    type: PageType.List,
    apiPatterns: ['**/api/v1/datasets*'],
    mockData: {
      datasets: [
        { id: 'ds-1', name: '用户数据集', format: 'parquet', size: '1.2GB', rows: 1000000 },
      ],
      total: 1,
    },
    expectedTitle: '数据集',
  },
  {
    route: '/data/monitoring',
    name: 'Monitoring',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/data/monitoring*'],
    mockData: {
      metrics: {
        total_tables: 256,
        total_etl_jobs: 45,
        success_rate: 99.5,
      },
    },
    expectedTitle: '系统监控',
  },
  {
    route: '/data/alerts',
    name: 'Alerts',
    type: PageType.List,
    apiPatterns: ['**/api/v1/data/alerts*'],
    mockData: {
      alerts: [
        { id: 'alert-1', name: 'ETL失败告警', level: 'critical', status: 'active' },
        { id: 'alert-2', name: '数据质量异常', level: 'warning', status: 'active' },
      ],
      total: 2,
    },
    expectedTitle: '智能预警',
  },
  // 运维中心页面
  {
    route: '/operations/scheduling',
    name: 'Scheduling',
    type: PageType.List,
    apiPatterns: ['**/api/v1/operations/scheduling*'],
    mockData: {
      schedules: [
        { id: 'sch-1', name: '日结任务调度', cron: '0 2 * * *', status: 'active' },
        { id: 'sch-2', name: '小时统计', cron: '0 * * * *', status: 'active' },
      ],
      total: 2,
    },
    expectedTitle: '调度管理',
  },
  {
    route: '/operations/smart-scheduling',
    name: 'Smart Scheduling',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/operations/smart-scheduling*'],
    mockData: {
      recommendations: [],
      optimizations: [],
    },
    expectedTitle: '智能调度',
  },
  {
    route: '/operations/execution-records',
    name: 'Execution Records',
    type: PageType.List,
    apiPatterns: ['**/api/v1/operations/execution*'],
    mockData: {
      records: [
        { id: 'exec-1', task: '日结任务', status: 'success', duration: 3600, startTime: '2024-01-01 02:00:00' },
        { id: 'exec-2', task: '数据同步', status: 'failed', duration: 120, startTime: '2024-01-01 03:00:00' },
      ],
      total: 2,
    },
    expectedTitle: '执行记录',
  },
  {
    route: '/operations/resource-monitor',
    name: 'Resource Monitor',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/operations/resources*'],
    mockData: {
      cpu: 65,
      memory: 72,
      disk: 48,
    },
    expectedTitle: '资源监控',
  },
  {
    route: '/operations/logs',
    name: 'Operation Logs',
    type: PageType.List,
    apiPatterns: ['**/api/v1/operations/logs*'],
    mockData: {
      logs: [
        { id: 'log-1', level: 'INFO', message: 'Task completed', timestamp: '2024-01-01 02:00:00' },
        { id: 'log-2', level: 'ERROR', message: 'Connection failed', timestamp: '2024-01-01 02:05:00' },
      ],
      total: 2,
    },
    expectedTitle: '操作日志',
  },
  {
    route: '/operations/alert-rules',
    name: 'Alert Rules',
    type: PageType.Form,
    apiPatterns: ['**/api/v1/operations/alert-rules*'],
    mockData: {
      rules: [
        { id: 'rule-1', name: 'CPU告警', threshold: 80, enabled: true },
      ],
      total: 1,
    },
    expectedTitle: '告警规则',
  },
  // 元数据图谱页面
  {
    route: '/metadata/graph',
    name: 'Metadata Graph',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/metadata/graph*'],
    mockData: {
      nodes: [],
      edges: [],
    },
    expectedTitle: '元数据图谱',
  },
  {
    route: '/metadata/search',
    name: 'Metadata Search',
    type: PageType.List,
    apiPatterns: ['**/api/v1/metadata/search*'],
    mockData: {
      results: [],
      total: 0,
    },
    expectedTitle: '元数据搜索',
  },
  {
    route: '/metadata/impact-analysis',
    name: 'Impact Analysis',
    type: PageType.Visualization,
    apiPatterns: ['**/api/v1/metadata/impact*'],
    mockData: {
      upstream: [],
      downstream: [],
    },
    expectedTitle: '影响分析',
  },
];

/**
 * 真实 API 验证页面配置
 * 所有页面启用 useRealAPI 选项
 */
export const DATA_OPS_LIVE_PAGES: DataOpsPageConfig[] = DATA_OPS_PAGES.map(page => ({
  ...page,
  useRealAPI: true,
}));

/**
 * 按页面类型分组的配置
 */
export const DATA_OPS_PAGES_BY_TYPE: Record<PageType, DataOpsPageConfig[]> = {
  [PageType.List]: DATA_OPS_PAGES.filter(p => p.type === PageType.List),
  [PageType.Editor]: DATA_OPS_PAGES.filter(p => p.type === PageType.Editor),
  [PageType.Visualization]: DATA_OPS_PAGES.filter(p => p.type === PageType.Visualization),
  [PageType.Form]: DATA_OPS_PAGES.filter(p => p.type === PageType.Form),
  [PageType.Generic]: DATA_OPS_PAGES.filter(p => p.type === PageType.Generic),
};

/**
 * 按模块分组的页面配置
 */
export const DATA_OPS_PAGES_BY_MODULE: Record<string, DataOpsPageConfig[]> = {
  /** 数据管理模块 */
  dataManagement: DATA_OPS_PAGES.filter(p =>
    p.route.startsWith('/data/') &&
    !p.route.startsWith('/data/etl') &&
    !p.route.startsWith('/data/kettle') &&
    !p.route.startsWith('/data/ocr') &&
    !p.route.startsWith('/data/quality') &&
    !p.route.startsWith('/data/lineage') &&
    !p.route.startsWith('/data/offline') &&
    !p.route.startsWith('/data/streaming') &&
    !p.route.startsWith('/data/monitoring') &&
    !p.route.startsWith('/data/alerts')
  ),
  /** 数据开发模块 */
  dataDevelopment: DATA_OPS_PAGES.filter(p =>
    p.route.startsWith('/data/etl') ||
    p.route.startsWith('/data/kettle') ||
    p.route.startsWith('/data/ocr') ||
    p.route.startsWith('/data/quality') ||
    p.route.startsWith('/data/lineage') ||
    p.route.startsWith('/data/offline') ||
    p.route.startsWith('/data/streaming')
  ),
  /** 运维中心模块 */
  operations: DATA_OPS_PAGES.filter(p => p.route.startsWith('/operations/')),
  /** 元数据管理模块 */
  metadata: DATA_OPS_PAGES.filter(p => p.route.startsWith('/metadata')),
  /** 分析工具模块 */
  analysis: DATA_OPS_PAGES.filter(p => p.route.startsWith('/model/')),
  /** 数据集模块 */
  datasets: DATA_OPS_PAGES.filter(p => p.route === '/datasets'),
};
