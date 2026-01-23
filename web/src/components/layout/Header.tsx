import { Layout, Button, Space, Typography, Dropdown, Avatar } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuth } from '../../contexts/AuthContext';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

function Header({ collapsed, onToggle }: HeaderProps) {
  const { user, logout } = useAuth();

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: (
        <Space>
          <div>
            <div>{user?.name || user?.preferred_username || '用户'}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {user?.email || ''}
            </Text>
          </div>
        </Space>
      ),
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'roles',
      label: (
        <Space direction="vertical" size={0}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            角色
          </Text>
          {user?.roles?.map((role) => (
            <span key={role} style={{ fontSize: 12 }}>
              {role}
            </span>
          ))}
        </Space>
      ),
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: () => logout(),
    },
  ];

  return (
    <AntHeader
      style={{
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #e8e8e8',
      }}
    >
      <Space>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggle}
          style={{ fontSize: '16px', width: 48, height: 48 }}
        />
        <Text strong style={{ fontSize: '18px' }}>
          ONE-DATA-STUDIO
        </Text>
      </Space>

      <Space>
        <Text type="secondary" style={{ display: { xs: 'none', md: 'block' } }}>
          数据 + AI + LLM 融合平台
        </Text>

        {user && (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar
              icon={<UserOutlined />}
              style={{ cursor: 'pointer', backgroundColor: '#1677ff' }}
            />
          </Dropdown>
        )}
      </Space>
    </AntHeader>
  );
}

export default Header;
