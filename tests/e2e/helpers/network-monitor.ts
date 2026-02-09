/**
 * Network Monitor for Playwright E2E Tests
 *
 * 功能：
 * - 监听网络请求
 * - 检测 4xx/5xx 错误
 * - 记录请求详情
 */

import { Page, Response } from '@playwright/test';
import { logger } from './logger';

export interface NetworkIssue {
  url: string;
  status: number;
  method: string;
  timestamp: string;
  responseType?: string;
}

export class NetworkMonitor {
  private page: Page;
  private issues: NetworkIssue[] = [];
  private allResponses: NetworkIssue[] = [];
  private isListening = false;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * 开始监听网络请求
   */
  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    this.issues = [];
    this.allResponses = [];
    this.isListening = true;

    this.page.on('response', (response: Response) => {
      const status = response.status();
      const url = response.url();
      const method = response.request().method();

      // 记录所有响应
      this.allResponses.push({
        url,
        status,
        method,
        timestamp: new Date().toISOString(),
        responseType: response.headers()['content-type'],
      });

      // 记录错误响应
      if (status >= 400) {
        this.issues.push({
          url,
          status,
          method,
          timestamp: new Date().toISOString(),
          responseType: response.headers()['content-type'],
        });
      }
    });
  }

  /**
   * 停止监听并返回问题列表
   */
  async stop(): Promise<NetworkIssue[]> {
    this.isListening = false;
    return [...this.issues];
  }

  /**
   * 获取当前错误列表（不停止监听）
   */
  getErrors(): NetworkIssue[] {
    return [...this.issues];
  }

  /**
   * 获取所有响应记录
   */
  getAllResponses(): NetworkIssue[] {
    return [...this.allResponses];
  }

  /**
   * 清空错误列表
   */
  clearErrors(): void {
    this.issues = [];
    this.allResponses = [];
  }

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.issues.length > 0;
  }

  /**
   * 格式化错误为可读字符串
   */
  formatErrors(): string {
    return this.issues.map((err, i) =>
      `[${i + 1}] ${err.method} ${err.url} - ${err.status} at ${err.timestamp}`
    ).join('\n');
  }

  /**
   * 获取特定状态码的请求
   */
  getErrorsByStatus(status: number): NetworkIssue[] {
    return this.issues.filter(err => err.status === status);
  }

  /**
   * 获取特定URL模式的请求
   */
  getErrorsByPattern(pattern: RegExp): NetworkIssue[] {
    return this.issues.filter(err => pattern.test(err.url));
  }

  /**
   * 获取API错误（忽略静态资源错误）
   */
  getAPIErrors(): NetworkIssue[] {
    return this.issues.filter(err =>
      err.url.includes('/api/') ||
      err.url.includes('/graphql')
    );
  }

  /**
   * 打印错误摘要
   */
  printSummary(): void {
    if (this.issues.length === 0) {
      logger.info('Network: No errors detected');
      return;
    }

    const apiErrors = this.getAPIErrors();
    const staticErrors = this.issues.length - apiErrors.length;

    logger.info(`Network: ${this.issues.length} errors (${apiErrors.length} API, ${staticErrors} static)`);

    // 按 HTTP 状态码分组
    const byStatus: Record<number, number> = {};
    for (const err of this.issues) {
      byStatus[err.status] = (byStatus[err.status] || 0) + 1;
    }

    for (const [status, count] of Object.entries(byStatus)) {
      logger.info(`  ${status}: ${count} requests`);
    }
  }

  /**
   * 保存错误到文件
   */
  async saveToFile(filePath: string): Promise<void> {
    const { writeFile } = await import('fs/promises');
    const content = this.formatErrors();
    await writeFile(filePath, content, 'utf-8');
    logger.info(`Network errors saved to: ${filePath}`);
  }
}
