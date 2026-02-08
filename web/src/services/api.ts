import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { showError as showErrorMsg } from './message';
import { getCsrfToken, getAccessToken } from './auth';

// API 响应基础类型
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
  timestamp?: string;
}

// API 错误类型
export interface ApiError {
  code: number;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

// 创建 axios 实例
const apiClient = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // SECURITY: Include credentials (HttpOnly cookies) with all requests
  // This is required for the HttpOnly cookie-based authentication to work
  withCredentials: true,
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加请求 ID
    if (config.headers) {
      config.headers['X-Request-ID'] = generateRequestId();

      // 添加 Authorization header（使用 sessionStorage 中的 token）
      const accessToken = getAccessToken();
      if (accessToken) {
        config.headers['Authorization'] = `Bearer ${accessToken}`;
      }

      // SECURITY: Add CSRF token for state-changing requests
      // Token is stored in a non-HttpOnly cookie that JavaScript can read
      if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method?.toUpperCase() || '')) {
        const csrfToken = getCsrfToken();
        if (csrfToken) {
          config.headers['X-CSRF-Token'] = csrfToken;
        }
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error: AxiosError<ApiError>) => {
    handleApiError(error);
    return Promise.reject(error);
  }
);

// 生成请求 ID
function generateRequestId(): string {
  return `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// 处理 API 错误
function handleApiError(error: AxiosError<ApiError>): void {
  const { response, request } = error;

  if (response) {
    // 服务器返回了错误响应
    const { status, data } = response;
    const errorMessage = data?.message || getErrorMessage(status);

    switch (status) {
      case 401:
        showErrorMsg('未授权，请重新登录');
        // Clear session storage data
        sessionStorage.removeItem('token_expires_at');
        sessionStorage.removeItem('user_info');
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        break;
      case 403:
        showErrorMsg('无权限访问该资源');
        break;
      case 404:
        // 404 错误不显示提示，由页面处理
        break;
      case 429:
        showErrorMsg('请求过于频繁，请稍后再试');
        break;
      case 500:
      case 502:
      case 503:
        showErrorMsg('服务暂时不可用，请稍后再试');
        break;
      default:
        showErrorMsg(errorMessage);
    }
  } else if (request) {
    // 请求已发送但没有收到响应
    showErrorMsg('网络连接失败，请检查网络设置');
  } else {
    // 请求配置出错
    showErrorMsg('请求配置错误');
  }
}

// 根据状态码获取错误消息
function getErrorMessage(status: number): string {
  const errorMessages: Record<number, string> = {
    400: '请求参数错误',
    401: '未授权',
    403: '禁止访问',
    404: '资源不存在',
    405: '请求方法不允许',
    409: '资源冲突',
    429: '请求过于频繁',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务不可用',
    504: '网关超时',
  };
  return errorMessages[status] || '未知错误';
}

// 通用请求方法
export async function request<T = unknown>(
  config: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  // The response interceptor already extracts response.data, so apiClient returns ApiResponse<T> directly
  const response = await apiClient.request<ApiResponse<T>>(config);
  return response as unknown as ApiResponse<T>;
}

// 导出 axios 实例供特定服务使用
export { apiClient };

// 导出默认实例
export default apiClient;
