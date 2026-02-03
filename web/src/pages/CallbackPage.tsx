/**
 * OAuth2 回调页面
 * Sprint 3.1: 处理 Keycloak 认证回调
 *
 * 功能：
 * - 处理授权码
 * - 交换 Token
 * - 重定向到原页面
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Result, Spin } from 'antd';
import { handleCallback } from '../services/auth';
import { useAuth } from '../contexts/AuthContext';
import { logDebug } from '../services/logger';

function CallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const { checkAuth } = useAuth();

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // 处理错误
      if (error) {
        setStatus('error');
        setError(errorDescription || error);
        return;
      }

      // 检查授权码
      if (!code || !state) {
        setStatus('error');
        setError('Invalid callback parameters');
        return;
      }

      // 处理授权码
      const success = await handleCallback(code, state);
      if (success) {
        setStatus('success');

        // 重新检查认证状态，更新 AuthContext
        await checkAuth();

        // 获取原始重定向路径（排除登录页）
        let redirectPath = sessionStorage.getItem('oauth_redirect') || '/';
        sessionStorage.removeItem('oauth_redirect');

        // 如果重定向路径是登录页，改为首页
        if (redirectPath === '/login' || redirectPath.startsWith('/login')) {
          redirectPath = '/';
        }

        logDebug(`Redirecting to: ${redirectPath}`, 'Callback');

        // 延迟跳转以便展示成功状态
        setTimeout(() => {
          navigate(redirectPath, { replace: true });
        }, 500);
      } else {
        setStatus('error');
        setError('Failed to process authentication');
      }
    };

    processCallback();
  }, [searchParams, navigate, checkAuth]);

  // 加载状态
  if (status === 'loading') {
    return (
      <div
        style={{
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 24,
        }}
      >
        <Spin size="large" />
        <div>正在处理认证...</div>
      </div>
    );
  }

  // 成功状态
  if (status === 'success') {
    return (
      <div
        style={{
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Result
          status="success"
          title="登录成功"
          subTitle="正在跳转..."
        />
      </div>
    );
  }

  // 错误状态
  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <Result
        status="error"
        title="认证失败"
        subTitle={error || '处理认证请求时出错'}
        extra={
          <a href="/login" style={{ textDecoration: 'none' }}>
            返回登录
          </a>
        }
      />
    </div>
  );
}

export default CallbackPage;
