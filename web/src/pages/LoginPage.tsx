/**
 * 登录页面
 * Sprint 3.1: Keycloak SSO 登录
 *
 * 功能：
 * - Keycloak OAuth2 登录
 * - 模拟登录（开发模式）
 * - 登录状态展示
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card, Form, Input, message, Alert, Space, Typography, Divider } from 'antd';
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons';
import { buildLoginUrl, mockLogin, getKeycloakConfig, isAuthenticated } from '../services/auth';

const { Title, Text, Paragraph } = Typography;

interface LoginFormData {
  username: string;
  password: string;
}

function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [useMock, setUseMock] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirect = searchParams.get('redirect') || '/';

  // 检查是否已登录
  useEffect(() => {
    if (isAuthenticated()) {
      navigate(redirect, { replace: true });
    }
  }, [navigate, redirect]);

  // Keycloak 登录
  const handleKeycloakLogin = useCallback(() => {
    setLoading(true);
    const loginUrl = buildLoginUrl(window.location.origin + '/callback');
    window.location.href = loginUrl;
  }, []);

  // 模拟登录（开发模式）
  const handleMockLogin = useCallback(async (values: LoginFormData) => {
    setLoading(true);
    setError(null);

    try {
      const success = await mockLogin(values.username, values.password);
      if (success) {
        message.success('登录成功');
        navigate(redirect, { replace: true });
      } else {
        setError('用户名或密码错误');
      }
    } catch (err) {
      setError('登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [navigate, redirect]);

  const keycloakConfig = getKeycloakConfig();

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '24px',
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1)',
          borderRadius: 16,
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Logo 和标题 */}
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: 64,
                height: 64,
                background: 'linear-gradient(135deg, #1677ff 0%, #722ed1 100%)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <UserOutlined style={{ fontSize: 32, color: '#fff' }} />
            </div>
            <Title level={3} style={{ margin: 0 }}>
              ONE DATA STUDIO
            </Title>
            <Text type="secondary">企业级 AI 融合平台</Text>
          </div>

          {/* 错误提示 */}
          {error && (
            <Alert
              message={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
            />
          )}

          {/* SSO 登录按钮 */}
          <Button
            type="primary"
            size="large"
            icon={<LoginOutlined />}
            onClick={handleKeycloakLogin}
            loading={loading}
            block
            style={{ height: 44, fontSize: 16 }}
          >
            使用 SSO 登录
          </Button>

          {/* 环境信息 */}
          <Alert
            message={
              <Space direction="vertical" size={0}>
                <Text type="secondary">认证服务器:</Text>
                <Text code style={{ fontSize: 12 }}>
                  {keycloakConfig.url}/realms/{keycloakConfig.realm}
                </Text>
              </Space>
            }
            type="info"
            showIcon={false}
            style={{ background: '#f5f5f5', border: 'none' }}
          />

          {/* 开发模式模拟登录 - 仅在开发环境显示 */}
          {import.meta.env.DEV && (
            <>
              <Divider style={{ margin: '12px 0' }}>开发模式</Divider>

              <div>
                <Button
                  type="link"
                  size="small"
                  onClick={() => setUseMock(!useMock)}
                  style={{ padding: 0 }}
                >
                  {useMock ? '隐藏' : '显示'}模拟登录表单
                </Button>

                {useMock && (
                  <Form
                    name="mock_login"
                    onFinish={handleMockLogin}
                    autoComplete="off"
                    layout="vertical"
                  >
                    <Form.Item
                      name="username"
                      rules={[{ required: true, message: '请输入用户名' }]}
                    >
                      <Input
                        prefix={<UserOutlined />}
                        placeholder="用户名"
                        size="large"
                      />
                    </Form.Item>

                    <Form.Item
                      name="password"
                      rules={[{ required: true, message: '请输入密码' }]}
                    >
                      <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="密码"
                        size="large"
                      />
                    </Form.Item>

                    <Form.Item>
                      <Button
                        type="default"
                        htmlType="submit"
                        loading={loading}
                        block
                        size="large"
                      >
                        模拟登录
                      </Button>
                    </Form.Item>

                    <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
                      开发模式: 输入任意用户名和密码即可登录
                    </Paragraph>
                  </Form>
                )}
              </div>
            </>
          )}
        </Space>
      </Card>
    </div>
  );
}

export default LoginPage;
