import { Layout, Button, Space, Typography, Dropdown, Avatar } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { supportedLanguages, changeLanguage } from '../../i18n';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

function Header({ collapsed, onToggle }: HeaderProps) {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();

  // 语言菜单
  const languageMenuItems: MenuProps['items'] = supportedLanguages.map((lang) => ({
    key: lang.code,
    label: (
      <Space>
        <span>{lang.flag}</span>
        <span>{lang.name}</span>
      </Space>
    ),
    onClick: () => changeLanguage(lang.code),
  }));

  // 当前语言
  const currentLanguage = supportedLanguages.find((lang) => lang.code === i18n.language);

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: (
        <Space>
          <div>
            <div>{user?.name || user?.preferred_username || t('user.username')}</div>
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
            {t('user.role')}
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
      label: t('user.settings'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('user.logout'),
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
          {t('app.name')}
        </Text>
      </Space>

      <Space size="middle">
        <Text type="secondary" style={{ display: { xs: 'none', md: 'block' } }}>
          {t('app.title')}
        </Text>

        {/* 语言切换器 */}
        <Dropdown menu={{ items: languageMenuItems }} placement="bottomRight">
          <Button type="text" icon={<GlobalOutlined />}>
            <span style={{ marginLeft: 4 }}>{currentLanguage?.flag}</span>
          </Button>
        </Dropdown>

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
