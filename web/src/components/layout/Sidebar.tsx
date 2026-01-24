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
        key: '/alldata/datasources',
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
        label: '元数据',
      },
      {
        key: '/alldata/features',
        icon: <AppstoreOutlined />,
        label: '特征存储',
      },
      {
        key: '/alldata/standards',
        icon: <FileTextOutlined />,
        label: '数据标准',
      },
      {
        key: '/alldata/assets',
        icon: <ShopOutlined />,
        label: '数据资产',
      },
      {
        key: '/alldata/services',
        icon: <CloudServerOutlined />,
        label: '数据服务',
      },
      {
        key: '/alldata/bi',
        icon: <LineChartOutlined />,
        label: 'BI 报表',
      },
      {
        key: '/alldata/metrics',
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
        key: '/alldata/etl',
        icon: <SwapOutlined />,
        label: 'ETL 任务',
      },
      {
        key: '/alldata/quality',
        icon: <SafetyOutlined />,
        label: '数据质量',
      },
      {
        key: '/alldata/lineage',
        icon: <ApartmentOutlined />,
        label: '数据血缘',
      },
      {
        key: '/alldata/offline',
        icon: <BranchesOutlined />,
        label: '离线开发',
      },
      {
        key: '/alldata/streaming',
        icon: <RadarChartOutlined />,
        label: '实时开发',
      },
      {
        key: '/alldata/streaming-ide',
        icon: <CodeOutlined />,
        label: '实时 IDE',
      },
      {
        key: '/cube/notebooks',
        icon: <LaptopOutlined />,
        label: 'Notebook',
      },
      {
        key: '/cube/sql-lab',
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
        key: '/cube/experiments',
        icon: <ExperimentOutlined />,
        label: '实验管理',
      },
      {
        key: '/cube/training',
        icon: <DeploymentUnitOutlined />,
        label: '训练任务',
      },
      {
        key: '/cube/models',
        icon: <ClusterOutlined />,
        label: '模型仓库',
      },
      {
        key: '/cube/aihub',
        icon: <ShopOutlined />,
        label: 'AIHub',
      },
      {
        key: '/cube/pipelines',
        icon: <BranchesOutlined />,
        label: 'Pipeline',
      },
      {
        key: '/cube/llm-tuning',
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
        key: '/cube/serving',
        icon: <CloudServerOutlined />,
        label: '在线服务',
      },
      {
        key: '/cube/resources',
        icon: <ClusterOutlined />,
        label: '资源管理',
      },
      {
        key: '/cube/monitoring',
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
        key: '/bisheng/prompts',
        icon: <BgColorsOutlined />,
        label: 'Prompt 管理',
      },
      {
        key: '/bisheng/knowledge',
        icon: <BookOutlined />,
        label: '知识库',
      },
      {
        key: '/bisheng/evaluation',
        icon: <ExperimentOutlined />,
        label: '模型评估',
      },
      {
        key: '/bisheng/sft',
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
        key: '/bisheng/apps',
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
        key: '/alldata/monitoring',
        icon: <MonitorOutlined />,
        label: '系统监控',
      },
      {
        key: '/schedules',
        icon: <ClockCircleOutlined />,
        label: '调度管理',
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
    if (pathname.startsWith('/alldata/datasources')) return '/alldata/datasources';
    if (pathname === '/datasets') return '/datasets';
    if (pathname === '/metadata') return '/metadata';
    if (pathname.startsWith('/alldata/features')) return '/alldata/features';
    if (pathname.startsWith('/alldata/standards')) return '/alldata/standards';
    if (pathname.startsWith('/alldata/assets')) return '/alldata/assets';
    if (pathname.startsWith('/alldata/services')) return '/alldata/services';
    if (pathname.startsWith('/alldata/bi')) return '/alldata/bi';
    if (pathname.startsWith('/alldata/metrics')) return '/alldata/metrics';

    // 数据开发
    if (pathname.startsWith('/alldata/etl')) return '/alldata/etl';
    if (pathname.startsWith('/alldata/quality')) return '/alldata/quality';
    if (pathname.startsWith('/alldata/lineage')) return '/alldata/lineage';
    if (pathname.startsWith('/alldata/offline')) return '/alldata/offline';
    if (pathname.startsWith('/alldata/streaming-ide')) return '/alldata/streaming-ide';
    if (pathname.startsWith('/alldata/streaming')) return '/alldata/streaming';
    if (pathname.startsWith('/cube/notebooks')) return '/cube/notebooks';

    // 模型开发
    if (pathname.startsWith('/cube/experiments')) return '/cube/experiments';
    if (pathname.startsWith('/cube/training')) return '/cube/training';
    if (pathname.startsWith('/cube/models')) return '/cube/models';
    if (pathname.startsWith('/cube/aihub')) return '/cube/aihub';
    if (pathname.startsWith('/cube/pipelines')) return '/cube/pipelines';
    if (pathname.startsWith('/cube/llm-tuning')) return '/cube/llm-tuning';

    // 模型服务
    if (pathname.startsWith('/cube/serving')) return '/cube/serving';
    if (pathname.startsWith('/cube/resources')) return '/cube/resources';
    if (pathname.startsWith('/cube/monitoring')) return '/cube/monitoring';

    // AI 应用
    if (pathname === '/chat') return '/chat';
    if (pathname.startsWith('/bisheng/prompts')) return '/bisheng/prompts';
    if (pathname.startsWith('/bisheng/knowledge')) return '/bisheng/knowledge';
    if (pathname.startsWith('/bisheng/evaluation')) return '/bisheng/evaluation';
    if (pathname.startsWith('/bisheng/sft')) return '/bisheng/sft';
    if (pathname === '/agents') return '/agents';
    if (pathname.startsWith('/workflows')) return '/workflows';
    if (pathname === '/text2sql') return '/text2sql';
    if (pathname.startsWith('/bisheng/apps')) return '/bisheng/apps';

    // 运维中心
    if (pathname.startsWith('/alldata/monitoring')) return '/alldata/monitoring';
    if (pathname === '/schedules') return '/schedules';
    if (pathname === '/executions') return '/executions';
    if (pathname === '/documents') return '/documents';

    // 系统管理
    if (pathname.startsWith('/admin/users')) return '/admin/users';
    if (pathname.startsWith('/admin/groups')) return '/admin/groups';
    if (pathname.startsWith('/admin/settings')) return '/admin/settings';
    if (pathname.startsWith('/admin/audit')) return '/admin/audit';

    return pathname;
  };

  const getOpenKeys = () => {
    const pathname = location.pathname;
    const keys: string[] = [];

    // 数据管理
    if (pathname.startsWith('/alldata/datasources') || pathname === '/datasets' ||
        pathname === '/metadata' || pathname.startsWith('/alldata/features') ||
        pathname.startsWith('/alldata/standards') || pathname.startsWith('/alldata/assets') ||
        pathname.startsWith('/alldata/services') || pathname.startsWith('/alldata/bi')) {
      keys.push('data');
    }

    // 数据开发
    if (pathname.startsWith('/alldata/etl') || pathname.startsWith('/alldata/quality') ||
        pathname.startsWith('/alldata/lineage') || pathname.startsWith('/alldata/offline') ||
        pathname.startsWith('/alldata/streaming') || pathname.startsWith('/alldata/streaming-ide') ||
        pathname.startsWith('/cube/notebooks') || pathname.startsWith('/cube/sql-lab')) {
      keys.push('dev');
    }

    // 模型开发
    if (pathname.startsWith('/cube/experiments') || pathname.startsWith('/cube/training') ||
        pathname.startsWith('/cube/models') || pathname.startsWith('/cube/aihub') ||
        pathname.startsWith('/cube/pipelines') || pathname.startsWith('/cube/llm-tuning')) {
      keys.push('model');
    }

    // 模型服务
    if (pathname.startsWith('/cube/serving') || pathname.startsWith('/cube/resources') ||
        pathname.startsWith('/cube/monitoring')) {
      keys.push('serving');
    }

    // AI 应用
    if (pathname.startsWith('/chat') || pathname.startsWith('/bisheng/') ||
        pathname.startsWith('/agents') || pathname.startsWith('/workflows') ||
        pathname.startsWith('/text2sql')) {
      keys.push('ai');
    }

    // 运维中心
    if (pathname.startsWith('/alldata/monitoring') || pathname.startsWith('/schedules') ||
        pathname.startsWith('/executions') || pathname.startsWith('/documents')) {
      keys.push('ops');
    }

    // 系统管理
    if (pathname.startsWith('/admin/')) {
      keys.push('admin');
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
