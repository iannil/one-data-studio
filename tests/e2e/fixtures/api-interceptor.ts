/**
 * API 拦截器工具
 * 用于拦截、捕获和验证 API 调用
 */

import { Page, Route, Response } from '@playwright/test';

/**
 * API 调用记录
 */
export interface ApiCall {
  url: string;
  method: string;
  requestBody?: unknown;
  responseStatus: number;
  responseBody?: unknown;
  timestamp: number;
  duration?: number;
}

/**
 * API 拦截器类
 */
export class ApiInterceptor {
  private page: Page;
  private calls: ApiCall[] = [];
  private isRecording = false;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * 开始记录 API 调用
   */
  startRecording(): void {
    if (this.isRecording) return;
    this.isRecording = true;
    this.calls = [];

    this.page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const startTime = Date.now();
        try {
          const body = await response.json().catch(() => null);
          this.calls.push({
            url: response.url(),
            method: response.request().method(),
            responseStatus: response.status(),
            responseBody: body,
            timestamp: startTime,
          });
        } catch {
          this.calls.push({
            url: response.url(),
            method: response.request().method(),
            responseStatus: response.status(),
            timestamp: startTime,
          });
        }
      }
    });
  }

  /**
   * 停止记录
   */
  stopRecording(): void {
    this.isRecording = false;
  }

  /**
   * 获取所有记录的调用
   */
  getCalls(): ApiCall[] {
    return [...this.calls];
  }

  /**
   * 获取匹配模式的调用
   */
  getCallsMatching(pattern: string | RegExp): ApiCall[] {
    return this.calls.filter(call => {
      if (typeof pattern === 'string') {
        return call.url.includes(pattern);
      }
      return pattern.test(call.url);
    });
  }

  /**
   * 清除记录
   */
  clearCalls(): void {
    this.calls = [];
  }

  /**
   * 等待特定 API 调用
   */
  async waitForCall(
    pattern: string | RegExp,
    options?: { timeout?: number; method?: string }
  ): Promise<Response> {
    const timeout = options?.timeout || 30000;
    const method = options?.method?.toUpperCase();

    return this.page.waitForResponse(
      (response) => {
        const url = response.url();
        const urlMatches = typeof pattern === 'string'
          ? url.includes(pattern)
          : pattern.test(url);
        const methodMatches = method
          ? response.request().method() === method
          : true;
        return urlMatches && methodMatches;
      },
      { timeout }
    );
  }
}

/**
 * Mock API 响应配置
 */
export interface MockConfig {
  status?: number;
  body?: unknown;
  delay?: number;
  headers?: Record<string, string>;
}

/**
 * 创建 API Mock
 */
export async function mockApi(
  page: Page,
  pattern: string,
  config: MockConfig
): Promise<void> {
  await page.route(pattern, async (route: Route) => {
    if (config.delay) {
      await new Promise(resolve => setTimeout(resolve, config.delay));
    }

    await route.fulfill({
      status: config.status || 200,
      contentType: 'application/json',
      headers: config.headers,
      body: JSON.stringify(config.body || { code: 0, data: null }),
    });
  });
}

/**
 * 创建列表类 API Mock
 */
export async function mockListApi<T>(
  page: Page,
  pattern: string,
  items: T[],
  options?: { total?: number; delay?: number }
): Promise<void> {
  await mockApi(page, pattern, {
    status: 200,
    delay: options?.delay,
    body: {
      code: 0,
      data: {
        items,
        total: options?.total ?? items.length,
        page: 1,
        page_size: 20,
      },
    },
  });
}

/**
 * 创建详情类 API Mock
 */
export async function mockDetailApi<T>(
  page: Page,
  pattern: string,
  data: T,
  options?: { delay?: number }
): Promise<void> {
  await mockApi(page, pattern, {
    status: 200,
    delay: options?.delay,
    body: {
      code: 0,
      data,
    },
  });
}

/**
 * 创建创建/更新成功 API Mock
 */
export async function mockMutationApi(
  page: Page,
  pattern: string,
  result?: unknown,
  options?: { delay?: number }
): Promise<void> {
  await mockApi(page, pattern, {
    status: 200,
    delay: options?.delay,
    body: {
      code: 0,
      data: result || { success: true },
      message: '操作成功',
    },
  });
}

/**
 * 创建删除成功 API Mock
 */
export async function mockDeleteApi(
  page: Page,
  pattern: string,
  options?: { delay?: number }
): Promise<void> {
  await mockApi(page, pattern, {
    status: 200,
    delay: options?.delay,
    body: {
      code: 0,
      data: null,
      message: '删除成功',
    },
  });
}

/**
 * 创建错误 API Mock
 */
export async function mockErrorApi(
  page: Page,
  pattern: string,
  statusCode: number,
  message?: string
): Promise<void> {
  const errorMessages: Record<number, string> = {
    400: '请求参数错误',
    401: '未授权，请重新登录',
    403: '无权限访问该资源',
    404: '请求的资源不存在',
    429: '请求过于频繁，请稍后再试',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务暂时不可用',
  };

  await mockApi(page, pattern, {
    status: statusCode,
    body: {
      code: statusCode,
      message: message || errorMessages[statusCode] || '未知错误',
    },
  });
}

/**
 * 模拟网络错误
 */
export async function mockNetworkError(
  page: Page,
  pattern: string
): Promise<void> {
  await page.route(pattern, async (route) => {
    await route.abort('failed');
  });
}

/**
 * 模拟超时
 */
export async function mockTimeout(
  page: Page,
  pattern: string,
  timeoutMs = 60000
): Promise<void> {
  await page.route(pattern, async (route) => {
    await new Promise(resolve => setTimeout(resolve, timeoutMs));
    await route.abort('timedout');
  });
}

/**
 * 验证 API 响应格式
 */
export function validateApiResponse(
  response: unknown,
  expectedFields: string[]
): boolean {
  if (!response || typeof response !== 'object') {
    return false;
  }

  const obj = response as Record<string, unknown>;

  // 检查标准响应格式
  if (!('code' in obj)) {
    return false;
  }

  // 检查必需字段
  for (const field of expectedFields) {
    if (!(field in obj)) {
      return false;
    }
  }

  return true;
}
