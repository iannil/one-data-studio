/**
 * CRUD 网络请求监控器
 *
 * 功能：
 * - 拦截并记录所有 API 请求
 * - 验证 CRUD 操作是否产生正确的 HTTP 方法
 * - 记录请求/响应详情用于报告
 *
 * @description P0 核心功能 CRUD 验收专用
 */

import { Page, Request, Response } from '@playwright/test';
import { writeFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

// ==================== 类型定义 ====================

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface NetworkRequest {
  /** 请求 URL */
  url: string;
  /** HTTP 方法 */
  method: HttpMethod;
  /** 响应状态码 */
  status: number;
  /** 请求时间戳 */
  timestamp: number;
  /** 请求耗时(ms) */
  duration: number;
  /** 请求体 */
  requestBody?: unknown;
  /** 响应体 */
  responseBody?: unknown;
  /** 响应头 */
  responseHeaders?: Record<string, string>;
  /** 是否为 API 请求 */
  isApiRequest: boolean;
  /** 对应的 CRUD 操作类型 */
  crudOperation?: 'create' | 'read' | 'update' | 'delete';
}

export interface CrudOperationResult {
  /** 操作类型 */
  operation: 'create' | 'read' | 'update' | 'delete';
  /** 是否成功 */
  success: boolean;
  /** 期望的 HTTP 方法 */
  expectedMethod: HttpMethod;
  /** 实际的 HTTP 方法 */
  actualMethod?: HttpMethod;
  /** 期望的状态码 */
  expectedStatus: number[];
  /** 实际状态码 */
  actualStatus?: number;
  /** 匹配的请求 */
  request?: NetworkRequest;
  /** 错误信息 */
  error?: string;
}

export interface ModuleCrudResult {
  /** 模块名称 */
  moduleName: string;
  /** API 前缀 */
  apiPrefix: string;
  /** CRUD 操作结果 */
  operations: CrudOperationResult[];
  /** 所有相关请求 */
  allRequests: NetworkRequest[];
}

// ==================== 监控器类 ====================

export class CrudNetworkMonitor {
  private page: Page;
  private requests: NetworkRequest[] = [];
  private pendingRequests: Map<string, { request: Request; startTime: number }> = new Map();
  private isMonitoring = false;
  private apiPatterns: string[] = ['/api/'];

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * 设置 API 模式（用于识别 API 请求）
   */
  setApiPatterns(patterns: string[]): void {
    this.apiPatterns = patterns;
  }

  /**
   * 开始监控网络请求
   */
  startMonitoring(): void {
    if (this.isMonitoring) {
      return;
    }

    this.requests = [];
    this.pendingRequests.clear();
    this.isMonitoring = true;

    // 监听请求开始
    this.page.on('request', (request: Request) => {
      const requestId = `${request.method()}-${request.url()}-${Date.now()}`;
      this.pendingRequests.set(requestId, {
        request,
        startTime: Date.now(),
      });
    });

    // 监听响应完成
    this.page.on('response', async (response: Response) => {
      const request = response.request();
      const url = request.url();
      const method = request.method() as HttpMethod;

      // 查找对应的 pending request
      let startTime = Date.now();
      for (const [id, pending] of this.pendingRequests.entries()) {
        if (pending.request.url() === url && pending.request.method() === method) {
          startTime = pending.startTime;
          this.pendingRequests.delete(id);
          break;
        }
      }

      const isApiRequest = this.apiPatterns.some(pattern => url.includes(pattern));

      let requestBody: unknown = undefined;
      let responseBody: unknown = undefined;

      try {
        const postData = request.postData();
        if (postData) {
          requestBody = JSON.parse(postData);
        }
      } catch {
        // 非 JSON 请求体
      }

      try {
        responseBody = await response.json();
      } catch {
        // 非 JSON 响应体
      }

      const networkRequest: NetworkRequest = {
        url,
        method,
        status: response.status(),
        timestamp: startTime,
        duration: Date.now() - startTime,
        requestBody,
        responseBody,
        responseHeaders: response.headers(),
        isApiRequest,
        crudOperation: this.detectCrudOperation(method),
      };

      this.requests.push(networkRequest);
    });
  }

  /**
   * 停止监控
   */
  stopMonitoring(): void {
    this.isMonitoring = false;
    this.pendingRequests.clear();
  }

  /**
   * 检测 CRUD 操作类型
   */
  private detectCrudOperation(method: HttpMethod): 'create' | 'read' | 'update' | 'delete' | undefined {
    switch (method) {
      case 'POST':
        return 'create';
      case 'GET':
        return 'read';
      case 'PUT':
      case 'PATCH':
        return 'update';
      case 'DELETE':
        return 'delete';
      default:
        return undefined;
    }
  }

  /**
   * 等待特定 API 请求
   */
  async waitForRequest(
    urlPattern: string | RegExp,
    method?: HttpMethod,
    timeout = 10000
  ): Promise<NetworkRequest | null> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const found = this.requests.find(req => {
        const urlMatches = typeof urlPattern === 'string'
          ? req.url.includes(urlPattern)
          : urlPattern.test(req.url);
        const methodMatches = !method || req.method === method;
        return urlMatches && methodMatches;
      });

      if (found) {
        return found;
      }

      await this.page.waitForTimeout(100);
    }

    return null;
  }

  /**
   * 验证 CRUD 操作
   */
  async verifyCrudOperation(
    operation: 'create' | 'read' | 'update' | 'delete',
    apiPrefix: string,
    timeout = 10000
  ): Promise<CrudOperationResult> {
    const methodMap: Record<string, HttpMethod> = {
      create: 'POST',
      read: 'GET',
      update: 'PUT',
      delete: 'DELETE',
    };

    const successStatusMap: Record<string, number[]> = {
      create: [200, 201],
      read: [200],
      update: [200],
      delete: [200, 204],
    };

    const expectedMethod = methodMap[operation];
    const expectedStatus = successStatusMap[operation];

    const request = await this.waitForRequest(apiPrefix, expectedMethod, timeout);

    if (!request) {
      return {
        operation,
        success: false,
        expectedMethod,
        expectedStatus,
        error: `未检测到 ${expectedMethod} ${apiPrefix} 请求`,
      };
    }

    const success = expectedStatus.includes(request.status);

    return {
      operation,
      success,
      expectedMethod,
      actualMethod: request.method,
      expectedStatus,
      actualStatus: request.status,
      request,
      error: success ? undefined : `状态码 ${request.status} 不在期望范围 [${expectedStatus.join(', ')}]`,
    };
  }

  /**
   * 获取所有请求
   */
  getRequests(): NetworkRequest[] {
    return [...this.requests];
  }

  /**
   * 获取 API 请求
   */
  getApiRequests(): NetworkRequest[] {
    return this.requests.filter(req => req.isApiRequest);
  }

  /**
   * 获取特定 API 前缀的请求
   */
  getRequestsByPrefix(prefix: string): NetworkRequest[] {
    return this.requests.filter(req => req.url.includes(prefix));
  }

  /**
   * 获取按 CRUD 操作分类的请求
   */
  getRequestsByCrudOperation(): Record<string, NetworkRequest[]> {
    const result: Record<string, NetworkRequest[]> = {
      create: [],
      read: [],
      update: [],
      delete: [],
      unknown: [],
    };

    for (const req of this.getApiRequests()) {
      const op = req.crudOperation || 'unknown';
      result[op].push(req);
    }

    return result;
  }

  /**
   * 获取错误请求 (4xx/5xx)
   */
  getErrorRequests(): NetworkRequest[] {
    return this.requests.filter(req => req.status >= 400);
  }

  /**
   * 清空请求记录
   */
  clearRequests(): void {
    this.requests = [];
  }

  /**
   * 生成请求统计
   */
  getStatistics(): {
    total: number;
    api: number;
    byMethod: Record<string, number>;
    byStatus: Record<string, number>;
    errors: number;
    avgDuration: number;
  } {
    const apiRequests = this.getApiRequests();

    const byMethod: Record<string, number> = {};
    const byStatus: Record<string, number> = {};
    let totalDuration = 0;

    for (const req of apiRequests) {
      byMethod[req.method] = (byMethod[req.method] || 0) + 1;

      const statusGroup = `${Math.floor(req.status / 100)}xx`;
      byStatus[statusGroup] = (byStatus[statusGroup] || 0) + 1;

      totalDuration += req.duration;
    }

    return {
      total: this.requests.length,
      api: apiRequests.length,
      byMethod,
      byStatus,
      errors: this.getErrorRequests().length,
      avgDuration: apiRequests.length > 0 ? Math.round(totalDuration / apiRequests.length) : 0,
    };
  }

  /**
   * 生成 JSON 格式报告
   */
  generateJsonReport(): string {
    const report = {
      generatedAt: new Date().toISOString(),
      statistics: this.getStatistics(),
      byCrudOperation: this.getRequestsByCrudOperation(),
      allApiRequests: this.getApiRequests(),
      errors: this.getErrorRequests(),
    };

    return JSON.stringify(report, null, 2);
  }

  /**
   * 生成 Markdown 格式报告
   */
  generateMarkdownReport(title = 'CRUD 网络请求报告'): string {
    const stats = this.getStatistics();
    const byCrud = this.getRequestsByCrudOperation();
    const errors = this.getErrorRequests();

    let md = `# ${title}\n\n`;
    md += `> 生成时间: ${new Date().toISOString()}\n\n`;

    // 统计概览
    md += `## 统计概览\n\n`;
    md += `| 指标 | 数值 |\n`;
    md += `|------|------|\n`;
    md += `| 总请求数 | ${stats.total} |\n`;
    md += `| API 请求数 | ${stats.api} |\n`;
    md += `| 错误请求数 | ${stats.errors} |\n`;
    md += `| 平均耗时 | ${stats.avgDuration}ms |\n\n`;

    // 按方法统计
    md += `## 按 HTTP 方法统计\n\n`;
    md += `| 方法 | 数量 |\n`;
    md += `|------|------|\n`;
    for (const [method, count] of Object.entries(stats.byMethod)) {
      md += `| ${method} | ${count} |\n`;
    }
    md += `\n`;

    // 按 CRUD 操作统计
    md += `## 按 CRUD 操作统计\n\n`;
    md += `| 操作 | 数量 |\n`;
    md += `|------|------|\n`;
    for (const [op, reqs] of Object.entries(byCrud)) {
      if (reqs.length > 0) {
        md += `| ${op.toUpperCase()} | ${reqs.length} |\n`;
      }
    }
    md += `\n`;

    // 错误请求
    if (errors.length > 0) {
      md += `## 错误请求\n\n`;
      md += `| URL | 方法 | 状态码 | 耗时 |\n`;
      md += `|-----|------|--------|------|\n`;
      for (const req of errors) {
        const shortUrl = req.url.length > 60 ? '...' + req.url.slice(-57) : req.url;
        md += `| ${shortUrl} | ${req.method} | ${req.status} | ${req.duration}ms |\n`;
      }
      md += `\n`;
    }

    // API 请求详情
    md += `## API 请求详情\n\n`;
    const apiRequests = this.getApiRequests();
    if (apiRequests.length > 0) {
      md += `| 时间 | 方法 | URL | 状态 | 耗时 |\n`;
      md += `|------|------|-----|------|------|\n`;
      for (const req of apiRequests.slice(0, 50)) { // 最多显示 50 条
        const time = new Date(req.timestamp).toISOString().slice(11, 23);
        const shortUrl = req.url.length > 50 ? '...' + req.url.slice(-47) : req.url;
        const statusIcon = req.status < 400 ? '✅' : '❌';
        md += `| ${time} | ${req.method} | ${shortUrl} | ${statusIcon} ${req.status} | ${req.duration}ms |\n`;
      }
      if (apiRequests.length > 50) {
        md += `\n*显示前 50 条，共 ${apiRequests.length} 条请求*\n`;
      }
    } else {
      md += `*无 API 请求记录*\n`;
    }

    return md;
  }

  /**
   * 保存报告到文件
   */
  async saveReports(outputDir: string): Promise<string[]> {
    if (!existsSync(outputDir)) {
      await mkdir(outputDir, { recursive: true });
    }

    const savedFiles: string[] = [];

    // 保存 JSON 报告
    const jsonPath = join(outputDir, 'network-requests.json');
    await writeFile(jsonPath, this.generateJsonReport(), 'utf-8');
    savedFiles.push(jsonPath);

    // 保存 Markdown 报告
    const mdPath = join(outputDir, 'network-report.md');
    await writeFile(mdPath, this.generateMarkdownReport(), 'utf-8');
    savedFiles.push(mdPath);

    return savedFiles;
  }
}

// ==================== 工厂函数 ====================

/**
 * 创建 CRUD 网络监控器
 */
export function createCrudNetworkMonitor(page: Page): CrudNetworkMonitor {
  return new CrudNetworkMonitor(page);
}
