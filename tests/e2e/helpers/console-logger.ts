/**
 * Console Logger for Playwright E2E Tests
 *
 * 功能：
 * - 监听浏览器控制台错误
 * - 记录网络请求失败
 * - 保存错误日志到文件
 */

import { Page } from '@playwright/test';

export interface ConsoleError {
  type: string;
  text: string;
  timestamp: string;
  url?: string;
  stack?: string;
}

export class ConsoleLogger {
  private page: Page;
  private errors: ConsoleError[] = [];
  private isListening = false;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * 开始监听控制台错误
   */
  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    this.errors = [];
    this.isListening = true;

    // 监听控制台错误
    this.page.on('console', (message) => {
      if (message.type() === 'error') {
        this.errors.push({
          type: 'console',
          text: message.text(),
          timestamp: new Date().toISOString(),
          url: this.page.url(),
        });
      }
    });

    // 监听页面错误
    this.page.on('pageerror', (error) => {
      this.errors.push({
        type: 'page',
        text: error.message,
        timestamp: new Date().toISOString(),
        stack: error.stack,
      });
    });

    // 监听响应失败
    this.page.on('response', (response) => {
      if (response.status() >= 400) {
        this.errors.push({
          type: 'network',
          text: `${response.status()} ${response.statusText()}`,
          timestamp: new Date().toISOString(),
          url: response.url(),
        });
      }
    });
  }

  /**
   * 停止监听并返回错误列表
   */
  async stop(): Promise<ConsoleError[]> {
    this.isListening = false;
    return [...this.errors];
  }

  /**
   * 获取当前错误列表（不停止监听）
   */
  getErrors(): ConsoleError[] {
    return [...this.errors];
  }

  /**
   * 清空错误列表
   */
  clearErrors(): void {
    this.errors = [];
  }

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.errors.length > 0;
  }

  /**
   * 格式化错误为可读字符串
   */
  formatErrors(): string {
    return this.errors.map((error, index) => {
      return `[${index + 1}] ${error.type} at ${error.timestamp}:
  URL: ${error.url || 'N/A'}
  Message: ${error.text}
  ${error.stack ? `Stack: ${error.stack}` : ''}`;
    }).join('\n\n');
  }

  /**
   * 保存错误到文件
   */
  async saveToFile(filePath: string): Promise<void> {
    const { writeFile } = await import('fs/promises');
    const content = this.formatErrors();
    await writeFile(filePath, content, 'utf-8');
    console.log(`Console errors saved to: ${filePath}`);
  }
}
