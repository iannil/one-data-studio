import { Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  HomeOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SwapOutlined,
  SafetyOutlined,
  ApartmentOutlined,
  TableOutlined,
  AppstoreOutlined,
  ExperimentOutlined,
  LaptopOutlined,
  DeploymentUnitOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  MonitorOutlined,
  MessageOutlined,
  BgColorsOutlined,
  BookOutlined,
  RobotOutlined,
  NodeIndexOutlined,
  CodeOutlined,
  RocketOutlined,
  ClockCircleOutlined,
  HistoryOutlined,
  FileTextOutlined,
  ShopOutlined,
  LineChartOutlined,
  SettingOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  RadarChartOutlined,
  BranchesOutlined,
  FundOutlined,
  FileSearchOutlined,
  ControlOutlined as AntControlOutlined,
  AuditOutlined as AntAuditOutlined,
  ToolOutlined,
  BellOutlined,
  ScanOutlined,
  DashboardOutlined,
  DiffOutlined,
  CalendarOutlined,
  UserOutlined,
  CheckCircleOutlined,
  NotificationOutlined,
} from '@ant-design/icons';

const menuItems = [
  // 首页
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '工作台',
  },

  // 数据管理 - 统一的数据入口
  {
    key: 'data',
    icon: <DatabaseOutlined />,
    label: '数据管理',
    children: [
      {
        key: '/data/datasources',
        icon: <ApiOutlined />,
        label: '数据源',
      },
      {
        key: '/datasets',
        icon: <DatabaseOutlined />,
        label: '数据集',
      },
      {
        key: '/metadata',
        icon: <TableOutlined />,
        label: '元数据管理',
      },
      {
        key: '/metadata/version-diff',
        icon: <DiffOutlined />,
        label: '版本对比',
      },
      {
        key: '/data/features',
        icon: <AppstoreOutlined />,
        label: '特征存储',
      },
      {
        key: '/data/standards',
        icon: <FileTextOutlined />,
        label: '数据标准',
      },
      {
        key: '/data/assets',
        icon: <ShopOutlined />,
        label: '数据资产',
      },
      {
        key: '/data/services',
        icon: <CloudServerOutlined />,
        label: '数据服务',
      },
      {
        key: '/data/bi',
        icon: <LineChartOutlined />,
        label: 'BI 报表',
      },
      {
        key: '/data/metrics',
        icon: <FundOutlined />,
        label: '指标体系',
      },
    ],
  },

  // 数据开发 - ETL 和数据处理
  {
    key: 'dev',
    icon: <SwapOutlined />,
    label: '数据开发',
    children: [
      {
        key: '/data/etl',
        icon: <SwapOutlined />,
        label: 'ETL 任务',
      },
      {
        key: '/data/kettle',
        icon: <ToolOutlined />,
        label: 'Kettle 引擎',
      },
      {
        key: '/data/kettle-generator',
        icon: <SettingOutlined />,
        label: 'Kettle 配置生成',
      },
      {
        key: '/data/ocr',
        icon: <ScanOutlined />,
        label: '文档 OCR',
      },
      {
        key: '/data/quality',
        icon: <SafetyOutlined />,
        label: '数据质量',
      },
      {
        key: '/data/lineage',
        icon: <ApartmentOutlined />,
        label: '数据血缘',
      },
      {
        key: '/data/offline',
        icon: <BranchesOutlined />,
        label: '离线开发',
      },
      {
        key: '/data/streaming',
        icon: <RadarChartOutlined />,
        label: '实时开发',
      },
      {
        key: '/data/streaming-ide',
        icon: <CodeOutlined />,
        label: '实时 IDE',
      },
      {
        key: '/model/notebooks',
        icon: <LaptopOutlined />,
        label: 'Notebook',
      },
      {
        key: '/model/sql-lab',
        icon: <FileSearchOutlined />,
        label: 'SQL Lab',
      },
    ],
  },

  // 模型开发 - MLOps 核心
  {
    key: 'model',
    icon: <ExperimentOutlined />,
    label: '模型开发',
    children: [
      {
        key: '/model/experiments',
        icon: <ExperimentOutlined />,
        label: '实验管理',
      },
      {
        key: '/model/training',
        icon: <DeploymentUnitOutlined />,
        label: '训练任务',
      },
      {
        key: '/model/models',
        icon: <ClusterOutlined />,
        label: '模型仓库',
      },
      {
        key: '/model/aihub',
        icon: <ShopOutlined />,
        label: 'AIHub',
      },
      {
        key: '/model/pipelines',
        icon: <BranchesOutlined />,
        label: 'Pipeline',
      },
      {
        key: '/model/llm-tuning',
        icon: <ThunderboltOutlined />,
        label: 'LLM 微调',
      },
    ],
  },

  // 模型服务 - 模型部署与监控
  {
    key: 'serving',
    icon: <CloudServerOutlined />,
    label: '模型服务',
    children: [
      {
        key: '/model/serving',
        icon: <CloudServerOutlined />,
        label: '在线服务',
      },
      {
        key: '/model/resources',
        icon: <ClusterOutlined />,
        label: '资源管理',
      },
      {
        key: '/model/monitoring',
        icon: <MonitorOutlined />,
        label: '监控告警',
      },
    ],
  },

  // AI 应用 - LLM 应用开发
  {
    key: 'ai',
    icon: <RobotOutlined />,
    label: 'AI 应用',
    children: [
      {
        key: '/chat',
        icon: <MessageOutlined />,
        label: 'AI 对话',
      },
      {
        key: '/agent-platform/prompts',
        icon: <BgColorsOutlined />,
        label: 'Prompt 管理',
      },
      {
        key: '/agent-platform/knowledge',
        icon: <BookOutlined />,
        label: '知识库',
      },
      {
        key: '/agent-platform/evaluation',
        icon: <ExperimentOutlined />,
        label: '模型评估',
      },
      {
        key: '/agent-platform/sft',
        icon: <ThunderboltOutlined />,
        label: 'SFT 微调',
      },
      {
        key: '/agents',
        icon: <RobotOutlined />,
        label: 'Agent',
      },
      {
        key: '/workflows',
        icon: <NodeIndexOutlined />,
        label: '工作流',
      },
      {
        key: '/text2sql',
        icon: <CodeOutlined />,
        label: 'Text2SQL',
      },
      {
        key: '/agent-platform/apps',
        icon: <RocketOutlined />,
        label: '应用发布',
      },
    ],
  },

  // 运维中心 - 通用运维功能
  {
    key: 'ops',
    icon: <ClockCircleOutlined />,
    label: '运维中心',
    children: [
      {
        key: '/data/monitoring',
        icon: <MonitorOutlined />,
        label: '系统监控',
      },
      {
        key: '/data/alerts',
        icon: <ThunderboltOutlined />,
        label: '智能预警',
      },
      {
        key: '/schedules',
        icon: <CalendarOutlined />,
        label: '工作流调度',
      },
      {
        key: '/scheduler/smart',
        icon: <ClockCircleOutlined />,
        label: '智能任务调度',
      },
      {
        key: '/executions',
        icon: <HistoryOutlined />,
        label: '执行记录',
      },
      {
        key: '/documents',
        icon: <FileTextOutlined />,
        label: '文档中心',
      },
    ],
  },

  // 系统管理
  {
    key: 'admin',
    icon: <SettingOutlined />,
    label: '系统管理',
    children: [
      {
        key: '/admin/users',
        icon: <TeamOutlined />,
        label: '用户管理',
      },
      {
        key: '/admin/groups',
        icon: <TeamOutlined />,
        label: '用户组管理',
      },
      {
        key: '/admin/notifications',
        icon: <NotificationOutlined />,
        label: '通知管理',
      },
      {
        key: '/admin/content',
        icon: <FileTextOutlined />,
        label: '内容管理',
      },
      {
        key: '/admin/roles',
        icon: <SafetyOutlined />,
        label: '角色管理',
      },
      {
        key: '/admin/behavior',
        icon: <RadarChartOutlined />,
        label: '行为概览',
      },
      {
        key: '/admin/behavior/audit-log',
        icon: <AntAuditOutlined />,
        label: '行为审计',
      },
      {
        key: '/admin/behavior/profile-view',
        icon: <UserOutlined />,
        label: '画像视图',
      },
      {
        key: '/admin/user-profiles',
        icon: <UserOutlined />,
        label: '用户画像',
      },
      {
        key: '/admin/user-segments',
        icon: <TeamOutlined />,
        label: '用户分群',
      },
      {
        key: '/admin/cost-report',
        icon: <FundOutlined />,
        label: '成本报告',
      },
      {
        key: '/admin/api-tester',
        icon: <ApiOutlined />,
        label: 'API 测试',
      },
      {
        key: '/admin/settings',
        icon: <AntControlOutlined />,
        label: '系统设置',
      },
      {
        key: '/admin/audit',
        icon: <AntAuditOutlined />,
        label: '审计日志',
      },
    ],
  },

  // 统一门户
  {
    key: 'portal',
    icon: <DashboardOutlined />,
    label: '统一门户',
    children: [
      {
        key: '/portal/dashboard',
        icon: <HomeOutlined />,
        label: '工作台',
      },
      {
        key: '/portal/notifications',
        icon: <BellOutlined />,
        label: '消息通知',
      },
      {
        key: '/portal/todos',
        icon: <CheckCircleOutlined />,
        label: '待办事项',
      },
      {
        key: '/portal/announcements',
        icon: <BellOutlined />,
        label: '公告管理',
      },
      {
        key: '/portal/profile',
        icon: <UserOutlined />,
        label: '个人中心',
      },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
}

function Sidebar({ collapsed }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const getSelectedKey = () => {
    const pathname = location.pathname;

    // 数据管理
    if (pathname.startsWith('/data/datasources')) return '/data/datasources';
    if (pathname === '/datasets') return '/datasets';
    if (pathname === '/metadata' || pathname.startsWith('/metadata/graph')) return '/metadata';
    if (pathname.startsWith('/metadata/version')) return '/metadata/version-diff';
    if (pathname.startsWith('/data/features')) return '/data/features';
    if (pathname.startsWith('/data/standards')) return '/data/standards';
    if (pathname.startsWith('/data/assets')) return '/data/assets';
    if (pathname.startsWith('/data/services')) return '/data/services';
    if (pathname.startsWith('/data/bi')) return '/data/bi';
    if (pathname.startsWith('/data/metrics')) return '/data/metrics';

    // 数据开发
    if (pathname.startsWith('/data/etl')) return '/data/etl';
    if (pathname.startsWith('/data/kettle')) return '/data/kettle';
    if (pathname.startsWith('/data/kettle-generator')) return '/data/kettle-generator';
    if (pathname.startsWith('/data/ocr')) return '/data/ocr';
    if (pathname.startsWith('/data/quality')) return '/data/quality';
    if (pathname.startsWith('/data/lineage')) return '/data/lineage';
    if (pathname.startsWith('/data/offline')) return '/data/offline';
    if (pathname.startsWith('/data/streaming-ide')) return '/data/streaming-ide';
    if (pathname.startsWith('/data/streaming')) return '/data/streaming';
    if (pathname.startsWith('/model/notebooks')) return '/model/notebooks';
    if (pathname.startsWith('/model/sql-lab')) return '/model/sql-lab';

    // 模型开发
    if (pathname.startsWith('/model/experiments')) return '/model/experiments';
    if (pathname.startsWith('/model/training')) return '/model/training';
    if (pathname.startsWith('/model/models')) return '/model/models';
    if (pathname.startsWith('/model/aihub')) return '/model/aihub';
    if (pathname.startsWith('/model/pipelines')) return '/model/pipelines';
    if (pathname.startsWith('/model/llm-tuning')) return '/model/llm-tuning';

    // 模型服务
    if (pathname.startsWith('/model/serving')) return '/model/serving';
    if (pathname.startsWith('/model/resources')) return '/model/resources';
    if (pathname.startsWith('/model/monitoring')) return '/model/monitoring';

    // AI 应用
    if (pathname === '/chat') return '/chat';
    if (pathname.startsWith('/agent-platform/prompts')) return '/agent-platform/prompts';
    if (pathname.startsWith('/agent-platform/knowledge')) return '/agent-platform/knowledge';
    if (pathname.startsWith('/agent-platform/evaluation')) return '/agent-platform/evaluation';
    if (pathname.startsWith('/agent-platform/sft')) return '/agent-platform/sft';
    if (pathname === '/agents') return '/agents';
    if (pathname.startsWith('/workflows')) return '/workflows';
    if (pathname === '/text2sql') return '/text2sql';
    if (pathname.startsWith('/agent-platform/apps')) return '/agent-platform/apps';

    // 运维中心
    if (pathname.startsWith('/data/monitoring')) return '/data/monitoring';
    if (pathname.startsWith('/data/alerts')) return '/data/alerts';
    if (pathname === '/schedules' || pathname.startsWith('/schedules/')) return '/schedules';
    if (pathname.startsWith('/scheduler/smart')) return '/scheduler/smart';
    if (pathname === '/executions') return '/executions';
    if (pathname === '/documents') return '/documents';

    // 系统管理
    if (pathname.startsWith('/admin/users')) return '/admin/users';
    if (pathname.startsWith('/admin/groups')) return '/admin/groups';
    if (pathname.startsWith('/admin/notifications')) return '/admin/notifications';
    if (pathname.startsWith('/admin/content')) return '/admin/content';
    if (pathname.startsWith('/admin/roles')) return '/admin/roles';
    if (pathname.startsWith('/admin/behavior')) return '/admin/behavior';
    if (pathname.startsWith('/admin/user-profiles')) return '/admin/user-profiles';
    if (pathname.startsWith('/admin/user-segments')) return '/admin/user-segments';
    if (pathname.startsWith('/admin/cost-report')) return '/admin/cost-report';
    if (pathname.startsWith('/admin/api-tester')) return '/admin/api-tester';
    if (pathname.startsWith('/admin/settings')) return '/admin/settings';
    if (pathname.startsWith('/admin/audit')) return '/admin/audit';

    // 统一门户
    if (pathname.startsWith('/portal/dashboard')) return '/portal/dashboard';
    if (pathname.startsWith('/portal/notifications')) return '/portal/notifications';
    if (pathname.startsWith('/portal/todos')) return '/portal/todos';
    if (pathname.startsWith('/portal/announcements')) return '/portal/announcements';
    if (pathname.startsWith('/portal/profile')) return '/portal/profile';

    return pathname;
  };

  const getOpenKeys = () => {
    const pathname = location.pathname;
    const keys: string[] = [];

    // 数据管理
    if (pathname.startsWith('/data/datasources') || pathname === '/datasets' ||
        pathname.startsWith('/metadata') || pathname.startsWith('/data/features') ||
        pathname.startsWith('/data/standards') || pathname.startsWith('/data/assets') ||
        pathname.startsWith('/data/services') || pathname.startsWith('/data/bi') ||
        pathname.startsWith('/data/metrics')) {
      keys.push('data');
    }

    // 数据开发
    if (pathname.startsWith('/data/etl') || pathname.startsWith('/data/kettle') ||
        pathname.startsWith('/data/kettle-generator') || pathname.startsWith('/data/ocr') ||
        pathname.startsWith('/data/quality') ||
        pathname.startsWith('/data/lineage') || pathname.startsWith('/data/offline') ||
        pathname.startsWith('/data/streaming') || pathname.startsWith('/data/streaming-ide') ||
        pathname.startsWith('/model/notebooks') || pathname.startsWith('/model/sql-lab')) {
      keys.push('dev');
    }

    // 模型开发
    if (pathname.startsWith('/model/experiments') || pathname.startsWith('/model/training') ||
        pathname.startsWith('/model/models') || pathname.startsWith('/model/aihub') ||
        pathname.startsWith('/model/pipelines') || pathname.startsWith('/model/llm-tuning')) {
      keys.push('model');
    }

    // 模型服务
    if (pathname.startsWith('/model/serving') || pathname.startsWith('/model/resources') ||
        pathname.startsWith('/model/monitoring')) {
      keys.push('serving');
    }

    // AI 应用
    if (pathname.startsWith('/chat') || pathname.startsWith('/agent-platform/') ||
        pathname.startsWith('/agents') || pathname.startsWith('/workflows') ||
        pathname.startsWith('/text2sql')) {
      keys.push('ai');
    }

    // 运维中心
    if (pathname.startsWith('/data/monitoring') || pathname.startsWith('/data/alerts') ||
        pathname.startsWith('/schedules') || pathname.startsWith('/scheduler/') ||
        pathname.startsWith('/executions') || pathname.startsWith('/documents')) {
      keys.push('ops');
    }

    // 系统管理
    if (pathname.startsWith('/admin/')) {
      keys.push('admin');
    }

    // 统一门户
    if (pathname.startsWith('/portal/')) {
      keys.push('portal');
    }

    return keys;
  };

  const [openKeys, setOpenKeys] = useState<string[]>(getOpenKeys());

  useEffect(() => {
    setOpenKeys(getOpenKeys());
  }, [location.pathname]);

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleOpenChange = (keys: string[]) => {
    setOpenKeys(keys);
  };

  return (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={[getSelectedKey()]}
      openKeys={openKeys}
      onOpenChange={handleOpenChange}
      items={menuItems}
      onClick={handleMenuClick}
      inlineCollapsed={collapsed}
    />
  );
}

export default Sidebar;
