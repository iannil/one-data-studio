/**
 * Superset 嵌入组件
 * 用于在 One Data Studio 中嵌入 Superset 仪表板
 */

import React, { useEffect, useRef, useState } from 'react';
import { Spin, message, Alert } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { supersetApi } from '@/services/superset';

interface SupersetEmbedProps {
  /** Superset 仪表板 ID */
  dashboardId: string | number;
  /** Guest Token（可选，如果不提供会尝试自动获取） */
  token?: string;
  /** 嵌入高度 */
  height?: string | number;
  /** 嵌入宽度 */
  width?: string | number;
  /** 额外的查询参数 */
  params?: Record<string, any>;
  /** 是否显示标题栏 */
  showHeader?: boolean;
  /** 是否显示原生过滤器 */
  showFilters?: boolean;
  /** 是否显示下载按钮 */
  showDownload?: boolean;
  /** 行级权限过滤器 */
  rls?: Array<{ dataset: number; clause: string }>;
  /** 加载完成回调 */
  onLoad?: () => void;
  /** 加载失败回调 */
  onError?: (error: Error) => void;
}

/**
 * Superset 嵌入组件
 *
 * @example
 * ```tsx
 * <SupersetEmbed
 *   dashboardId="1"
 *   height={600}
 *   rls={[{ dataset: 1, clause: "region='North'" }]}
 * />
 * ```
 */
const SupersetEmbed: React.FC<SupersetEmbedProps> = ({
  dashboardId,
  token: propToken,
  height = '600px',
  width = '100%',
  params = {},
  showHeader = true,
  showFilters = true,
  showDownload = false,
  rls = [],
  onLoad,
  onError,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // 获取 Guest Token
  const { data: tokenData } = useQuery({
    queryKey: ['superset', 'guest-token', dashboardId, rls],
    queryFn: () => supersetApi.createGuestToken({
      resources: [{
        type: 'dashboard',
        id: String(dashboardId),
      }],
      rls,
    }),
    select: (data) => data.data.data,
    enabled: !propToken,
    staleTime: 3600000, // 1 hour
    retry: false,
  });

  const token = propToken || tokenData?.token;

  // 构建嵌入 URL
  const buildEmbedUrl = () => {
    const supersetUrl = import.meta.env.VITE_SUPERSET_URL || 'http://localhost:8088';

    // 基础路径
    let embedPath = '/superset/dashboard/' + dashboardId;

    // 构建查询参数
    const queryParams = new URLSearchParams();

    // 界面配置
    queryParams.set('standalone', 'true');
    if (!showHeader) {
      queryParams.set('hide_header', 'true');
    }
    if (!showFilters) {
      queryParams.set('hide_native_filters', 'true');
    }
    if (!showDownload) {
      queryParams.set('hide_download', 'true');
    }

    // 自定义参数
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.set(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    if (queryString) {
      embedPath += '?' + queryString;
    }

    return `${supersetUrl}${embedPath}`;
  };

  // 处理 iframe 加载完成
  const handleIframeLoad = () => {
    setLoading(false);
    onLoad?.();
  };

  // 处理 iframe 加载错误
  const handleIframeError = () => {
    const err = new Error('Failed to load Superset dashboard');
    setError(err);
    setLoading(false);
    onError?.(err);
  };

  // 跨域消息处理
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      // 验证来源
      const supersetUrl = import.meta.env.VITE_SUPERSET_URL || 'http://localhost:8088';
      const supersetOrigin = new URL(supersetUrl).origin;

      if (event.origin !== supersetOrigin) {
        return;
      }

      // 处理来自 Superset 的消息
      if (event.data?.type === 'iframe_ready') {
        // Superset iframe 已准备就绪
        console.debug('[SupersetEmbed] Iframe ready');
      } else if (event.data?.type === 'error') {
        // Superset 报错
        message.error(`Superset error: ${event.data.message}`);
      } else if (event.data?.type === 'resize') {
        // Superset 请求调整大小
        if (iframeRef.current && event.data.height) {
          iframeRef.current.style.height = `${event.data.height}px`;
        }
      }
    };

    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // 当 token 变化时重新加载 iframe
  useEffect(() => {
    if (token && iframeRef.current) {
      iframeRef.current.src = buildEmbedUrl();
    }
  }, [token, dashboardId, JSON.stringify(params)]);

  if (error) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error.message}
        showIcon
        style={{ height, width }}
      />
    );
  }

  return (
    <div style={{ position: 'relative', height, width }}>
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#f5f5f5',
            zIndex: 1,
          }}
        >
          <Spin tip="正在加载 Superset 仪表板..." size="large" />
        </div>
      )}

      {!token ? (
        <div
          style={{
            height,
            width,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Spin tip="正在获取访问令牌..." size="large" />
        </div>
      ) : (
        <iframe
          ref={iframeRef}
          src={buildEmbedUrl()}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            borderRadius: 4,
          }}
          onLoad={handleIframeLoad}
          onError={handleIframeError}
          allow="clipboard-read; clipboard-write"
          allowFullScreen
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
        />
      )}
    </div>
  );
};

export default SupersetEmbed;
