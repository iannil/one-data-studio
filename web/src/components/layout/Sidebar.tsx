import { Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DatabaseOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  TableOutlined,
  HomeOutlined,
} from '@ant-design/icons';

const menuItems = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '首页',
  },
  {
    key: '/datasets',
    icon: <DatabaseOutlined />,
    label: '数据集管理',
  },
  {
    key: '/chat',
    icon: <MessageOutlined />,
    label: 'AI 聊天',
  },
  {
    key: '/workflows',
    icon: <NodeIndexOutlined />,
    label: '工作流',
  },
  {
    key: '/metadata',
    icon: <TableOutlined />,
    label: '元数据',
  },
];

interface SidebarProps {
  collapsed: boolean;
}

function Sidebar({ collapsed }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  // 处理子路由情况，获取当前选中的主菜单
  const getSelectedKey = () => {
    const pathname = location.pathname;
    if (pathname.startsWith('/datasets')) return '/datasets';
    if (pathname.startsWith('/chat')) return '/chat';
    if (pathname.startsWith('/workflows')) return '/workflows';
    if (pathname.startsWith('/metadata')) return '/metadata';
    return pathname;
  };

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={[getSelectedKey()]}
      items={menuItems}
      onClick={handleMenuClick}
      inlineCollapsed={collapsed}
    />
  );
}

export default Sidebar;
