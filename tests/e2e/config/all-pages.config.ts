/**
 * 所有页面的测试配置
 * 包含 70+ 个页面的完整配置信息
 */

import { PageType } from '../helpers/data-ops-validator';

// ==================== 类型定义 ====================

export interface OperationConfig {
  enabled?: boolean;
  [key: string]: any;
}

export interface CreateOperationConfig extends OperationConfig {
  formSelector?: string;
  submitSelector?: string;
  testData?: any;
  verifySuccess?: string[];
  skip?: boolean;
}

export interface ReadOperationConfig extends OperationConfig {
  tableSelector?: string;
  searchSelector?: string;
  expectedRowCount?: number;
}

export interface UpdateOperationConfig extends OperationConfig {
  editSelector?: string;
  updateField?: string;
  updateValue?: string;
  saveSelector?: string;
}

export interface DeleteOperationConfig extends OperationConfig {
  deleteSelector?: string;
  confirmSelector?: string;
  skipCleanup?: boolean;
}

export interface PageOperations {
  create?: CreateOperationConfig;
  read?: ReadOperationConfig;
  update?: UpdateOperationConfig;
  delete?: DeleteOperationConfig;
}

export interface PageTestConfig {
  /** 页面所属模块 */
  module: string;
  /** 页面路由 */
  route: string;
  /** 页面名称 */
  name: string;
  /** 页面类型 */
  type: PageType;
  /** 是否启用测试 */
  enabled?: boolean;
  /** 需要 CRUD 操作验证 */
  operations?: PageOperations;
  /** 预期的页面标题 */
  expectedTitle?: string;
  /** 是否需要特定权限 */
  requiredRoles?: string[];
  /** 测试超时时间（毫秒） */
  timeout?: number;
  /** 是否跳过此页面 */
  skip?: boolean;
  /** 跳过原因 */
  skipReason?: string;
}

// ==================== 基础认证模块 ====================

export const AUTH_PAGES: PageTestConfig[] = [
  {
    module: 'auth',
    route: '/login',
    name: '登录页面',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '登录',
    operations: {
      read: {
        tableSelector: '.login-form',
        searchSelector: 'input[name="username"]',
      },
    },
  },
  {
    module: 'auth',
    route: '/callback',
    name: 'OAuth回调页面',
    type: PageType.Generic,
    enabled: true,
    skip: true,
    skipReason: 'OAuth回调页面不需要直接测试',
  },
];

// ==================== DataOps 数据治理模块 ====================

export const DATA_OPS_PAGES: PageTestConfig[] = [
  // 数据源管理
  {
    module: 'data',
    route: '/data/datasources',
    name: '数据源管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据源',
    operations: {
      create: {
        formSelector: '.datasource-form, .ant-modal',
        submitSelector: 'button:has-text("创建"), button:has-text("保存")',
        testData: { category: 'datasource', subCategory: 'mysql' },
        verifySuccess: ['.ant-message-success', '.ant-notification-notice-success'],
      },
      read: {
        tableSelector: '.ant-table',
        searchSelector: 'input[placeholder*="搜索"]',
      },
      update: {
        editSelector: 'button:has-text("编辑")',
        updateField: 'description',
        updateValue: 'E2E测试更新',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // ETL 任务
  {
    module: 'data',
    route: '/data/etl',
    name: 'ETL流程',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'ETL',
    operations: {
      create: {
        formSelector: '.etl-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'etl', subCategory: 'mysql_to_clickhouse' },
        verifySuccess: ['.ant-message-success'],
      },
      read: {
        tableSelector: '.ant-table',
        searchSelector: 'input[placeholder*="搜索"]',
      },
      update: {
        editSelector: 'button:has-text("编辑")',
        updateField: 'description',
        updateValue: 'E2E测试更新',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-popconfirm button:has-text("确定")',
      },
    },
  },

  // Kettle 引擎
  {
    module: 'data',
    route: '/data/kettle',
    name: 'Kettle引擎',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: 'Kettle',
    operations: {
      read: {
        tableSelector: '.kettle-job-list',
      },
    },
  },

  // Kettle 配置生成器
  {
    module: 'data',
    route: '/data/kettle-generator',
    name: 'Kettle配置生成',
    type: PageType.Form,
    enabled: true,
    expectedTitle: 'Kettle生成器',
    operations: {
      create: {
        formSelector: '.kettle-generator-form',
        submitSelector: 'button:has-text("生成")',
      },
    },
  },

  // 数据质量
  {
    module: 'data',
    route: '/data/quality',
    name: '数据质量',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据质量',
    operations: {
      create: {
        formSelector: '.quality-rule-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'quality_rule', subCategory: 'not_null' },
        verifySuccess: ['.ant-message-success'],
      },
      read: {
        tableSelector: '.ant-table',
        searchSelector: 'input[placeholder*="搜索"]',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // 数据血缘
  {
    module: 'data',
    route: '/data/lineage',
    name: '数据血缘',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '血缘',
    operations: {
      read: {
        tableSelector: '.lineage-graph, .dagre, .react-flow',
      },
    },
  },

  // 特征存储
  {
    module: 'data',
    route: '/data/features',
    name: '特征存储',
    type: PageType.List,
    enabled: true,
    expectedTitle: '特征',
    operations: {
      create: {
        formSelector: '.feature-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'feature', subCategory: 'user_feature' },
        verifySuccess: ['.ant-message-success'],
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 数据标准
  {
    module: 'data',
    route: '/data/standards',
    name: '数据标准',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据标准',
    operations: {
      create: {
        formSelector: '.standard-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 数据资产
  {
    module: 'data',
    route: '/data/assets',
    name: '数据资产',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据资产',
    operations: {
      read: {
        tableSelector: '.ant-table, .asset-grid',
      },
    },
  },

  // 数据服务
  {
    module: 'data',
    route: '/data/services',
    name: '数据服务',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据服务',
    operations: {
      create: {
        formSelector: '.service-form',
        submitSelector: 'button:has-text("发布")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // BI 报表
  {
    module: 'data',
    route: '/data/bi',
    name: 'BI报表',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: 'BI',
    operations: {
      read: {
        tableSelector: '.dashboard, .chart-container',
      },
    },
  },

  // 系统监控
  {
    module: 'data',
    route: '/data/monitoring',
    name: '系统监控',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '监控',
    operations: {
      read: {
        tableSelector: '.monitoring-chart, .metric-card',
      },
    },
  },

  // 实时开发
  {
    module: 'data',
    route: '/data/streaming',
    name: '实时开发',
    type: PageType.List,
    enabled: true,
    expectedTitle: '实时',
    operations: {
      create: {
        formSelector: '.stream-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 实时 IDE
  {
    module: 'data',
    route: '/data/streaming-ide',
    name: '实时IDE',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: '实时IDE',
    operations: {
      read: {
        tableSelector: '.ide-editor, .monaco-editor',
      },
    },
  },

  // 离线开发
  {
    module: 'data',
    route: '/data/offline',
    name: '离线开发',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: '离线开发',
    operations: {
      read: {
        tableSelector: '.task-list, .editor-container',
      },
    },
  },

  // 指标体系
  {
    module: 'data',
    route: '/data/metrics',
    name: '指标体系',
    type: PageType.List,
    enabled: true,
    expectedTitle: '指标',
    operations: {
      create: {
        formSelector: '.metric-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 智能预警
  {
    module: 'data',
    route: '/data/alerts',
    name: '智能预警',
    type: PageType.List,
    enabled: true,
    expectedTitle: '预警',
    operations: {
      create: {
        formSelector: '.alert-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'alert_rule', subCategory: 'etl_failed' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 文档 OCR
  {
    module: 'data',
    route: '/data/ocr',
    name: '文档OCR',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'OCR',
    operations: {
      create: {
        formSelector: '.ocr-form',
        submitSelector: 'button:has-text("上传")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },
];

// ==================== MLOps 模型管理模块 ====================

export const ML_OPS_PAGES: PageTestConfig[] = [
  // Notebook 开发
  {
    module: 'model',
    route: '/model/notebooks',
    name: 'Notebook开发',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'Notebook',
    operations: {
      create: {
        formSelector: '.notebook-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'notebook', subCategory: 'python' },
        verifySuccess: ['.ant-message-success'],
      },
      read: {
        tableSelector: '.ant-table, .notebook-list',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // 实验管理
  {
    module: 'model',
    route: '/model/experiments',
    name: '实验管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '实验',
    operations: {
      create: {
        formSelector: '.experiment-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'experiment', subCategory: 'classification' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 模型管理
  {
    module: 'model',
    route: '/model/models',
    name: '模型管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '模型',
    operations: {
      create: {
        formSelector: '.model-form',
        submitSelector: 'button:has-text("注册")',
        testData: { category: 'model', subCategory: 'sklearn' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 模型训练
  {
    module: 'model',
    route: '/model/training',
    name: '模型训练',
    type: PageType.List,
    enabled: true,
    expectedTitle: '训练',
    operations: {
      create: {
        formSelector: '.training-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 模型服务
  {
    module: 'model',
    route: '/model/serving',
    name: '模型服务',
    type: PageType.List,
    enabled: true,
    expectedTitle: '服务',
    operations: {
      create: {
        formSelector: '.deployment-form',
        submitSelector: 'button:has-text("部署")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 资源管理
  {
    module: 'model',
    route: '/model/resources',
    name: '资源管理',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '资源',
    operations: {
      read: {
        tableSelector: '.resource-chart, .gpu-list',
      },
    },
  },

  // 模型监控
  {
    module: 'model',
    route: '/model/monitoring',
    name: '模型监控',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '监控',
    operations: {
      read: {
        tableSelector: '.monitoring-chart',
      },
    },
  },

  // AI Hub
  {
    module: 'model',
    route: '/model/aihub',
    name: 'AI Hub',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'AI Hub',
    operations: {
      read: {
        tableSelector: '.model-market, .hub-grid',
      },
    },
  },

  // 模型流水线
  {
    module: 'model',
    route: '/model/pipelines',
    name: '模型流水线',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '流水线',
    operations: {
      create: {
        formSelector: '.pipeline-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.pipeline-graph',
      },
    },
  },

  // LLM 微调
  {
    module: 'model',
    route: '/model/llm-tuning',
    name: 'LLM微调',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '微调',
    operations: {
      create: {
        formSelector: '.tuning-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.tuning-list',
      },
    },
  },

  // SQL Lab
  {
    module: 'model',
    route: '/model/sql-lab',
    name: 'SQL Lab',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: 'SQL Lab',
    operations: {
      read: {
        tableSelector: '.sql-editor, .query-result',
      },
    },
  },
];

// ==================== LLMOps Agent 平台模块 ====================

export const AGENT_PAGES: PageTestConfig[] = [
  // Prompt 管理
  {
    module: 'agent',
    route: '/agent-platform/prompts',
    name: 'Prompt管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'Prompt',
    operations: {
      create: {
        formSelector: '.prompt-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'prompt', subCategory: 'chat' },
        verifySuccess: ['.ant-message-success'],
      },
      read: {
        tableSelector: '.ant-table',
      },
      update: {
        editSelector: 'button:has-text("编辑")',
        updateField: 'content',
        updateValue: 'E2E测试更新内容',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // 知识库管理
  {
    module: 'agent',
    route: '/agent-platform/knowledge',
    name: '知识库管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '知识库',
    operations: {
      create: {
        formSelector: '.knowledge-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'knowledge', subCategory: 'document' },
      },
      read: {
        tableSelector: '.ant-table',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // Agent 应用
  {
    module: 'agent',
    route: '/agent-platform/apps',
    name: 'Agent应用',
    type: PageType.List,
    enabled: true,
    expectedTitle: '应用',
    operations: {
      create: {
        formSelector: '.app-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'agent', subCategory: 'chatbot' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 效果评估
  {
    module: 'agent',
    route: '/agent-platform/evaluation',
    name: '效果评估',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '评估',
    operations: {
      read: {
        tableSelector: '.evaluation-chart, .metric-list',
      },
    },
  },

  // SFT 训练
  {
    module: 'agent',
    route: '/agent-platform/sft',
    name: 'SFT训练',
    type: PageType.Form,
    enabled: true,
    expectedTitle: 'SFT',
    operations: {
      create: {
        formSelector: '.sft-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.sft-list',
      },
    },
  },
];

// ==================== 工作流管理模块 ====================

export const WORKFLOW_PAGES: PageTestConfig[] = [
  // 工作流列表
  {
    module: 'workflow',
    route: '/workflows',
    name: '工作流列表',
    type: PageType.List,
    enabled: true,
    expectedTitle: '工作流',
    operations: {
      create: {
        formSelector: '.workflow-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'workflow', subCategory: 'simple' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 新建工作流
  {
    module: 'workflow',
    route: '/workflows/new',
    name: '新建工作流',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: '工作流编辑',
    operations: {
      read: {
        tableSelector: '.flow-editor, .node-canvas',
      },
    },
  },

  // 工作流执行
  {
    module: 'workflow',
    route: '/executions',
    name: '执行监控',
    type: PageType.List,
    enabled: true,
    expectedTitle: '执行',
    operations: {
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // Text2SQL
  {
    module: 'workflow',
    route: '/text2sql',
    name: 'Text2SQL',
    type: PageType.Editor,
    enabled: true,
    expectedTitle: 'Text2SQL',
    operations: {
      read: {
        tableSelector: '.sql-input, .query-result',
      },
    },
  },
];

// ==================== 元数据管理模块 ====================

export const METADATA_PAGES: PageTestConfig[] = [
  // 元数据查询
  {
    module: 'metadata',
    route: '/metadata',
    name: '元数据查询',
    type: PageType.List,
    enabled: true,
    expectedTitle: '元数据',
    operations: {
      read: {
        tableSelector: '.ant-table, .metadata-tree',
      },
    },
  },

  // 元数据图谱
  {
    module: 'metadata',
    route: '/metadata/graph',
    name: '元数据图谱',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '图谱',
    operations: {
      read: {
        tableSelector: '.graph-container, .relation-graph',
      },
    },
  },

  // 版本对比
  {
    module: 'metadata',
    route: '/metadata/version-diff',
    name: '版本对比',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '版本对比',
    operations: {
      read: {
        tableSelector: '.diff-container, .version-compare',
      },
    },
  },
];

// ==================== 管理后台模块 ====================

export const ADMIN_PAGES: PageTestConfig[] = [
  // 用户管理
  {
    module: 'admin',
    route: '/admin/users',
    name: '用户管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '用户',
    requiredRoles: ['system_admin', 'data_admin'],
    operations: {
      create: {
        formSelector: '.user-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'user', subCategory: 'data_engineer' },
      },
      read: {
        tableSelector: '.ant-table',
        searchSelector: 'input[placeholder*="搜索"]',
      },
      update: {
        editSelector: 'button:has-text("编辑")',
        updateField: 'status',
        updateValue: 'active',
      },
      delete: {
        deleteSelector: 'button:has-text("删除")',
        confirmSelector: '.ant-modal-confirm button:has-text("确定")',
      },
    },
  },

  // 角色管理
  {
    module: 'admin',
    route: '/admin/roles',
    name: '角色管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '角色',
    requiredRoles: ['system_admin'],
    operations: {
      create: {
        formSelector: '.role-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 权限管理
  {
    module: 'admin',
    route: '/admin/permissions',
    name: '权限管理',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '权限',
    requiredRoles: ['system_admin'],
    operations: {
      read: {
        tableSelector: '.permission-tree, .role-permission-matrix',
      },
    },
  },

  // 系统设置
  {
    module: 'admin',
    route: '/admin/settings',
    name: '系统设置',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '设置',
    requiredRoles: ['system_admin'],
    operations: {
      update: {
        editSelector: '.setting-item',
        updateField: 'value',
        updateValue: 'test',
      },
    },
  },

  // 审计日志
  {
    module: 'admin',
    route: '/admin/audit',
    name: '审计日志',
    type: PageType.List,
    enabled: true,
    expectedTitle: '审计',
    requiredRoles: ['system_admin', 'data_admin'],
    operations: {
      read: {
        tableSelector: '.ant-table',
        searchSelector: 'input[placeholder*="搜索"]',
      },
    },
  },

  // 分组管理
  {
    module: 'admin',
    route: '/admin/groups',
    name: '分组管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '分组',
    requiredRoles: ['system_admin'],
    operations: {
      create: {
        formSelector: '.group-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 成本报告
  {
    module: 'admin',
    route: '/admin/cost-report',
    name: '成本报告',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '成本',
    requiredRoles: ['system_admin', 'data_admin'],
    operations: {
      read: {
        tableSelector: '.cost-chart, .report-table',
      },
    },
  },

  // 通知管理
  {
    module: 'admin',
    route: '/admin/notifications',
    name: '通知管理',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '通知',
    requiredRoles: ['system_admin'],
    operations: {
      create: {
        formSelector: '.notification-form',
        submitSelector: 'button:has-text("发送")',
      },
      read: {
        tableSelector: '.notification-list',
      },
    },
  },

  // 内容管理
  {
    module: 'admin',
    route: '/admin/content',
    name: '内容管理',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '内容',
    requiredRoles: ['system_admin'],
    operations: {
      read: {
        tableSelector: '.content-list',
      },
    },
  },

  // 用户画像
  {
    module: 'admin',
    route: '/admin/user-profiles',
    name: '用户画像',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '画像',
    requiredRoles: ['system_admin'],
    operations: {
      read: {
        tableSelector: '.profile-chart, .user-stats',
      },
    },
  },

  // 用户分群
  {
    module: 'admin',
    route: '/admin/user-segments',
    name: '用户分群',
    type: PageType.List,
    enabled: true,
    expectedTitle: '分群',
    requiredRoles: ['system_admin'],
    operations: {
      create: {
        formSelector: '.segment-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // API 测试器
  {
    module: 'admin',
    route: '/admin/api-tester',
    name: 'API测试器',
    type: PageType.Form,
    enabled: true,
    expectedTitle: 'API测试',
    operations: {
      read: {
        tableSelector: '.api-tester, .request-panel',
      },
    },
  },

  // 行为分析
  {
    module: 'admin',
    route: '/admin/behavior',
    name: '行为分析',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '行为分析',
    operations: {
      read: {
        tableSelector: '.behavior-chart, .heatmap',
      },
    },
  },

  // 行为审计日志
  {
    module: 'admin',
    route: '/admin/behavior/audit-log',
    name: '行为审计日志',
    type: PageType.List,
    enabled: true,
    expectedTitle: '审计日志',
    operations: {
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 画像查看
  {
    module: 'admin',
    route: '/admin/behavior/profile-view',
    name: '画像查看',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '画像',
    operations: {
      read: {
        tableSelector: '.profile-view, .user-attributes',
      },
    },
  },
];

// ==================== 门户模块 ====================

export const PORTAL_PAGES: PageTestConfig[] = [
  // 门户仪表板
  {
    module: 'portal',
    route: '/portal/dashboard',
    name: '门户仪表板',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '仪表板',
    operations: {
      read: {
        tableSelector: '.dashboard, .widget-grid',
      },
    },
  },

  // 通知中心
  {
    module: 'portal',
    route: '/portal/notifications',
    name: '通知中心',
    type: PageType.List,
    enabled: true,
    expectedTitle: '通知',
    operations: {
      read: {
        tableSelector: '.notification-list',
      },
    },
  },

  // 待办事项
  {
    module: 'portal',
    route: '/portal/todos',
    name: '待办事项',
    type: PageType.List,
    enabled: true,
    expectedTitle: '待办',
    operations: {
      create: {
        formSelector: '.todo-form',
        submitSelector: 'button:has-text("添加")',
      },
      read: {
        tableSelector: '.todo-list',
      },
    },
  },

  // 公告管理
  {
    module: 'portal',
    route: '/portal/announcements',
    name: '公告管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '公告',
    operations: {
      read: {
        tableSelector: '.announcement-list',
      },
    },
  },

  // 个人中心
  {
    module: 'portal',
    route: '/portal/profile',
    name: '个人中心',
    type: PageType.Form,
    enabled: true,
    expectedTitle: '个人',
    operations: {
      update: {
        editSelector: '.profile-form input',
        updateField: 'nickname',
        updateValue: 'E2E测试用户',
      },
    },
  },
];

// ==================== 通用模块 ====================

export const COMMON_PAGES: PageTestConfig[] = [
  // 数据集管理
  {
    module: 'common',
    route: '/datasets',
    name: '数据集管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '数据集',
    operations: {
      create: {
        formSelector: '.dataset-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'dataset', subCategory: 'table' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 文档管理
  {
    module: 'common',
    route: '/documents',
    name: '文档管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '文档',
    operations: {
      create: {
        formSelector: '.document-form',
        submitSelector: 'button:has-text("上传")',
      },
      read: {
        tableSelector: '.ant-table, .document-grid',
      },
    },
  },

  // 调度管理
  {
    module: 'common',
    route: '/schedules',
    name: '调度管理',
    type: PageType.List,
    enabled: true,
    expectedTitle: '调度',
    operations: {
      create: {
        formSelector: '.schedule-form',
        submitSelector: 'button:has-text("创建")',
        testData: { category: 'schedule', subCategory: 'daily' },
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },

  // 智能调度
  {
    module: 'common',
    route: '/scheduler/smart',
    name: '智能调度',
    type: PageType.Visualization,
    enabled: true,
    expectedTitle: '智能调度',
    operations: {
      read: {
        tableSelector: '.smart-schedule, .optimization-list',
      },
    },
  },

  // Agents 列表
  {
    module: 'common',
    route: '/agents',
    name: 'Agents列表',
    type: PageType.List,
    enabled: true,
    expectedTitle: 'Agent',
    operations: {
      create: {
        formSelector: '.agent-form',
        submitSelector: 'button:has-text("创建")',
      },
      read: {
        tableSelector: '.ant-table',
      },
    },
  },
];

// ==================== 汇总所有页面配置 ====================

/**
 * 所有页面配置
 */
export const ALL_PAGES_CONFIG: PageTestConfig[] = [
  ...AUTH_PAGES,
  ...DATA_OPS_PAGES,
  ...ML_OPS_PAGES,
  ...AGENT_PAGES,
  ...WORKFLOW_PAGES,
  ...METADATA_PAGES,
  ...ADMIN_PAGES,
  ...PORTAL_PAGES,
  ...COMMON_PAGES,
];

/**
 * 过滤出启用的页面配置
 */
export function getEnabledPages(): PageTestConfig[] {
  return ALL_PAGES_CONFIG.filter(page => page.enabled !== false && !page.skip);
}

/**
 * 按模块分组页面配置
 */
export function getPagesByModule(): Record<string, PageTestConfig[]> {
  const grouped: Record<string, PageTestConfig[]> = {};

  for (const page of ALL_PAGES_CONFIG) {
    if (!grouped[page.module]) {
      grouped[page.module] = [];
    }
    grouped[page.module].push(page);
  }

  return grouped;
}

/**
 * 按页面类型分组
 */
export function getPagesByType(): Record<PageType, PageTestConfig[]> {
  const grouped: Record<PageType, PageTestConfig[]> = {
    [PageType.List]: [],
    [PageType.Editor]: [],
    [PageType.Visualization]: [],
    [PageType.Form]: [],
    [PageType.Generic]: [],
  };

  for (const page of ALL_PAGES_CONFIG) {
    grouped[page.type].push(page);
  }

  return grouped;
}

/**
 * 获取需要 CRUD 验证的页面
 */
export function getCRUDPages(): PageTestConfig[] {
  return ALL_PAGES_CONFIG.filter(page => {
    if (page.skip || page.enabled === false) return false;
    const ops = page.operations;
    return ops && (ops.create || ops.read || ops.update || ops.delete);
  });
}

/**
 * 获取页面统计信息
 */
export function getPageStats() {
  const stats = {
    total: ALL_PAGES_CONFIG.length,
    enabled: getEnabledPages().length,
    byModule: getPagesByModule(),
    byType: getPagesByType(),
    crud: getCRUDPages().length,
    skipped: ALL_PAGES_CONFIG.filter(p => p.skip).length,
  };

  // 添加模块计数
  stats.byModule = Object.fromEntries(
    Object.entries(stats.byModule).map(([module, pages]) => [
      module,
      pages.filter(p => p.enabled !== false && !p.skip).length,
    ])
  ) as Record<string, PageTestConfig[]>;

  return stats;
}
