/**
 * Comprehensive Monitor for Playwright E2E Tests
 *
 * 功能：
 * - 综合网络、控制台、性能监控
 * - 每步操作日志记录
 * - 错误检测与报告
 * - 性能指标采集
 */

import { Page, Response } from '@playwright/test';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface NetworkIssue {
  url: string;
  status: number;
  method: string;
  timestamp: string;
  responseType?: string;
  duration?: number;
}

export interface ConsoleError {
  type: 'console' | 'page' | 'network';
  text: string;
  timestamp: string;
  url?: string;
  stack?: string;
}

export interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: string;
  unit: string;
}

export interface StepLog {
  phase: string;
  step: string;
  timestamp: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  consoleErrors: ConsoleError[];
  networkIssues: NetworkIssue[];
  performanceMetrics: PerformanceMetric[];
  screenshot?: string;
  details?: string;
  pageUrl?: string;
}

export interface MonitorOptions {
  logDir?: string;
  autoScreenshot?: boolean;
  realTimeLog?: boolean;
  trackPerformance?: boolean;
  maxStoredLogs?: number;
}

// ============================================================================
// Comprehensive Monitor Class
// ============================================================================

export class ComprehensiveMonitor {
  private page: Page;
  private networkIssues: NetworkIssue[] = [];
  private consoleErrors: ConsoleError[] = [];
  private performanceMetrics: PerformanceMetric[] = [];
  private stepLogs: StepLog[] = [];
  private logDir: string;
  private options: Required<MonitorOptions>;
  private testStartTime: number;
  private phaseStartTime: number;
  private currentPhase: string = '';
  private stepStartTime: number;
  private isListening = false;

  // 性能观察器
  private performanceObserver?: PerformanceObserver;

  constructor(page: Page, options: MonitorOptions = {}) {
    this.page = page;
    this.testStartTime = Date.now();
    this.phaseStartTime = Date.now();
    this.stepStartTime = Date.now();
    this.logDir = options.logDir || 'test-results/logs/full-platform';
    this.options = {
      logDir: options.logDir || 'test-results/logs/full-platform',
      autoScreenshot: options.autoScreenshot ?? true,
      realTimeLog: options.realTimeLog ?? true,
      trackPerformance: options.trackPerformance ?? true,
      maxStoredLogs: options.maxStoredLogs ?? 1000,
    };

    // 确保日志目录存在
    this.ensureLogDir();
  }

  // ============================================================================
  // Setup & Teardown
  // ============================================================================

  /**
   * 开始监听
   */
  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    this.isListening = true;
    this.networkIssues = [];
    this.consoleErrors = [];
    this.performanceMetrics = [];

    // 监听网络请求
    this.setupNetworkMonitoring();

    // 监听控制台错误
    this.setupConsoleMonitoring();

    // 监听页面错误
    this.setupPageErrorMonitoring();

    // 监听性能指标
    if (this.options.trackPerformance) {
      this.setupPerformanceMonitoring();
    }

    console.log(`[ComprehensiveMonitor] Started monitoring at ${new Date().toISOString()}`);
  }

  /**
   * 停止监听
   */
  async stop(): Promise<{
    networkIssues: NetworkIssue[];
    consoleErrors: ConsoleError[];
    performanceMetrics: PerformanceMetric[];
  }> {
    this.isListening = false;

    // 停止性能监听
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }

    console.log(`[ComprehensiveMonitor] Stopped monitoring at ${new Date().toISOString()}`);

    return {
      networkIssues: [...this.networkIssues],
      consoleErrors: [...this.consoleErrors],
      performanceMetrics: [...this.performanceMetrics],
    };
  }

  // ============================================================================
  // Phase Management
  // ============================================================================

  /**
   * 开始新的测试阶段
   */
  startPhase(phaseName: string): void {
    this.currentPhase = phaseName;
    this.phaseStartTime = Date.now();
    console.log(`\n${'='.repeat(70)}`);
    console.log(`[PHASE] ${phaseName}`);
    console.log('='.repeat(70));
  }

  /**
   * 记录测试步骤
   */
  async logStep(
    stepName: string,
    status: 'passed' | 'failed' | 'skipped' = 'passed',
    details: string = ''
  ): Promise<void> {
    const duration = Date.now() - this.stepStartTime;
    const currentConsoleErrors = this.getCurrentErrors();
    const currentNetworkIssues = this.getCurrentNetworkIssues();
    const currentPerformanceMetrics = this.getCurrentPerformanceMetrics();

    const stepLog: StepLog = {
      phase: this.currentPhase || 'Unknown',
      step: stepName,
      timestamp: new Date().toISOString(),
      status,
      duration,
      consoleErrors: [...currentConsoleErrors],
      networkIssues: [...currentNetworkIssues],
      performanceMetrics: [...currentPerformanceMetrics],
      details,
      pageUrl: this.page.url(),
    };

    this.stepLogs.push(stepLog);

    // 检查是否超过最大存储数量
    if (this.stepLogs.length > this.options.maxStoredLogs) {
      this.stepLogs.shift();
    }

    // 打印步骤日志
    this.printStepLog(stepLog);

    // 如果失败且启用自动截图，保存截图
    if (status === 'failed' && this.options.autoScreenshot) {
      const screenshotPath = await this.saveScreenshot(stepName);
      stepLog.screenshot = screenshotPath;
    }

    // 实时保存日志
    if (this.options.realTimeLog) {
      await this.saveRealtimeLog();
    }

    // 重置步骤计时器
    this.stepStartTime = Date.now();

    // 清空当前错误计数（让每步独立计数）
    this.clearCurrentErrors();
  }

  // ============================================================================
  // Monitoring Setup
  // ============================================================================

  /**
   * 设置网络监控
   */
  private setupNetworkMonitoring(): void {
    const requestStartTimes = new Map<string, number>();

    this.page.on('request', (request) => {
      requestStartTimes.set(request.url(), Date.now());
    });

    this.page.on('response', (response: Response) => {
      const url = response.url();
      const status = response.status();
      const method = response.request().method();
      const startTime = requestStartTimes.get(url) || Date.now();
      const duration = Date.now() - startTime;

      const issue: NetworkIssue = {
        url,
        status,
        method,
        timestamp: new Date().toISOString(),
        responseType: response.headers()['content-type'],
        duration,
      };

      // 总是记录响应（用于分析）
      if (status >= 400) {
        this.networkIssues.push(issue);
        console.warn(`[Network] ${method} ${url} - ${status} (${duration}ms)`);
      }
    });

    this.page.on('requestfailed', (request) => {
      const url = request.url();
      const failureText = request.failure()?.errorText || 'Unknown error';

      this.networkIssues.push({
        url,
        status: 0,
        method: request.method(),
        timestamp: new Date().toISOString(),
        duration: 0,
      });

      console.error(`[Network Failed] ${request.method()} ${url} - ${failureText}`);
    });
  }

  /**
   * 设置控制台监控
   */
  private setupConsoleMonitoring(): void {
    this.page.on('console', (message) => {
      const type = message.type();

      if (type === 'error' || type === 'warning') {
        this.consoleErrors.push({
          type: 'console',
          text: message.text(),
          timestamp: new Date().toISOString(),
          url: this.page.url(),
        });

        if (type === 'error') {
          console.error(`[Console Error] ${message.text()}`);
        }
      }
    });
  }

  /**
   * 设置页面错误监控
   */
  private setupPageErrorMonitoring(): void {
    this.page.on('pageerror', (error) => {
      this.consoleErrors.push({
        type: 'page',
        text: error.message,
        timestamp: new Date().toISOString(),
        stack: error.stack,
        url: this.page.url(),
      });

      console.error(`[Page Error] ${error.message}`);
    });

    this.page.on('loadstate', (state) => {
      if (state === 'load' || state === 'domcontentloaded') {
        this.recordPerformanceMetric('pageLoad', Date.now() - this.testStartTime, 'ms');
      }
    });
  }

  /**
   * 设置性能监控
   */
  private setupPerformanceMonitoring(): void {
    // 通过 CDP 获取性能指标
    this.page.evaluate(() => {
      // 在浏览器上下文中设置性能监听
      if (typeof window !== 'undefined' && 'PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            // 将性能数据存储到 window 对象中，供后续读取
            if (!(window as any).__performanceLogs) {
              (window as any).__performanceLogs = [];
            }
            (window as any).__performanceLogs.push({
              name: entry.name,
              value: entry.duration || entry.startTime,
              type: entry.entryType,
            });
          }
        });
        observer.observe({ entryTypes: ['navigation', 'resource', 'measure'] });
        (window as any).__performanceObserver = observer;
      }
    }).catch(() => {
      // 忽略 evaluate 错误
    });
  }

  // ============================================================================
  // Error & Metrics Access
  // ============================================================================

  /**
   * 获取当前步骤的错误
   */
  private getCurrentErrors(): ConsoleError[] {
    // 返回自上次清空以来的所有错误
    return [...this.consoleErrors];
  }

  /**
   * 获取当前步骤的网络问题
   */
  private getCurrentNetworkIssues(): NetworkIssue[] {
    return [...this.networkIssues];
  }

  /**
   * 获取当前步骤的性能指标
   */
  private getCurrentPerformanceMetrics(): PerformanceMetric[] {
    return [...this.performanceMetrics];
  }

  /**
   * 清空当前错误计数
   */
  private clearCurrentErrors(): void {
    this.consoleErrors = [];
    this.performanceMetrics = [];
    // 注意：networkIssues 不清空，因为我们需要跟踪所有网络问题
  }

  /**
   * 记录性能指标
   */
  recordPerformanceMetric(name: string, value: number, unit: string = 'ms'): void {
    this.performanceMetrics.push({
      name,
      value,
      timestamp: new Date().toISOString(),
      unit,
    });
  }

  // ============================================================================
  // State Checking
  // ============================================================================

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.consoleErrors.length > 0 || this.networkIssues.some(i => i.status >= 500);
  }

  /**
   * 检查是否有网络错误
   */
  hasNetworkErrors(): boolean {
    return this.networkIssues.length > 0;
  }

  /**
   * 检查是否有控制台错误
   */
  hasConsoleErrors(): boolean {
    return this.consoleErrors.length > 0;
  }

  /**
   * 获取 API 错误（忽略静态资源）
   */
  getAPIErrors(): NetworkIssue[] {
    return this.networkIssues.filter(err =>
      err.url.includes('/api/') ||
      err.url.includes('/graphql')
    );
  }

  /**
   * 获取特定状态码的请求
   */
  getErrorsByStatus(status: number): NetworkIssue[] {
    return this.networkIssues.filter(err => err.status === status);
  }

  // ============================================================================
  // Logging & Reporting
  // ============================================================================

  /**
   * 打印步骤日志
   */
  private printStepLog(stepLog: StepLog): void {
    const hasErrors = stepLog.consoleErrors.length > 0 || stepLog.networkIssues.length > 0;
    const icon = stepLog.status === 'passed' ? '✓' : stepLog.status === 'failed' ? '✗' : '○';
    const warningIcon = hasErrors ? ' ⚠' : '';

    console.log(`${icon} [STEP] ${stepLog.step}${warningIcon} (${stepLog.duration}ms)`);

    if (stepLog.consoleErrors.length > 0) {
      console.log(`  ⚠ Console Errors: ${stepLog.consoleErrors.length}`);
    }
    if (stepLog.networkIssues.length > 0) {
      console.log(`  ⚠ Network Issues: ${stepLog.networkIssues.length}`);
    }
    if (stepLog.details) {
      console.log(`  ℹ ${stepLog.details}`);
    }
  }

  /**
   * 保存截图
   */
  async saveScreenshot(stepName: string): Promise<string> {
    this.ensureLogDir();

    // 清理步骤名称
    const safeStepName = stepName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_');
    const filename = `${this.currentPhase}_${safeStepName}_${Date.now()}.png`;
    const filepath = join(process.cwd(), this.logDir, filename);

    await this.page.screenshot({ path: filepath, fullPage: true });
    console.log(`  📸 Screenshot saved: ${filepath}`);
    return filepath;
  }

  /**
   * 确保日志目录存在
   */
  private ensureLogDir(): void {
    const dir = join(process.cwd(), this.logDir);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
  }

  /**
   * 保存实时日志
   */
  async saveRealtimeLog(): Promise<void> {
    this.ensureLogDir();

    const logContent = {
      currentPhase: this.currentPhase,
      totalDuration: Date.now() - this.testStartTime,
      phaseDuration: Date.now() - this.phaseStartTime,
      steps: this.stepLogs,
      updatedAt: new Date().toISOString(),
    };

    const filepath = join(process.cwd(), this.logDir, 'realtime-log.json');
    writeFileSync(filepath, JSON.stringify(logContent, null, 2), 'utf-8');
  }

  /**
   * 生成最终报告
   */
  generateReport(): {
    summary: Record<string, any>;
    textReport: string;
    jsonReport: Record<string, any>;
  } {
    const totalDuration = Date.now() - this.testStartTime;
    const allErrors = this.getAllErrors();
    const apiErrors = this.getAPIErrors();

    // 生成摘要
    const summary = {
      testTime: new Date().toISOString(),
      totalDuration,
      totalDurationSec: (totalDuration / 1000).toFixed(2),
      totalSteps: this.stepLogs.length,
      passedSteps: this.stepLogs.filter(l => l.status === 'passed').length,
      failedSteps: this.stepLogs.filter(l => l.status === 'failed').length,
      skippedSteps: this.stepLogs.filter(l => l.status === 'skipped').length,
      totalConsoleErrors: this.stepLogs.reduce((sum, l) => sum + l.consoleErrors.length, 0),
      totalNetworkIssues: this.networkIssues.length,
      totalAPIErrors: apiErrors.length,
      phases: this.getPhaseSummary(),
    };

    // 生成文本报告
    const textReport = this.generateTextReport(summary);

    // 生成 JSON 报告
    const jsonReport = {
      summary,
      steps: this.stepLogs,
      errors: allErrors,
      networkIssues: this.networkIssues,
    };

    return { summary, textReport, jsonReport };
  }

  /**
   * 生成文本报告
   */
  private generateTextReport(summary: Record<string, any>): string {
    const lines = [
      '='.repeat(70),
      'Full Platform E2E Test Report',
      '='.repeat(70),
      `Test Time: ${summary.testTime}`,
      `Total Duration: ${summary.totalDurationSec}s (${(summary.totalDuration / 60000).toFixed(2)}m)`,
      '',
      'Summary:',
      `  Total Steps: ${summary.totalSteps}`,
      `  Passed: ${summary.passedSteps} ✓`,
      `  Failed: ${summary.failedSteps} ✗`,
      `  Skipped: ${summary.skippedSteps} ○`,
      '',
      'Errors:',
      `  Console Errors: ${summary.totalConsoleErrors}`,
      `  Network Issues: ${summary.totalNetworkIssues}`,
      `  API Errors: ${summary.totalAPIErrors}`,
      '',
      'Phase Summary:',
      ...Object.entries(summary.phases).map(([phase, data]: [string, any]) =>
        `  ${phase}: ${data.steps} steps, ${data.errors} errors, ${data.duration}ms`
      ),
      '',
      'Step Details:',
    ];

    // 添加步骤详情
    for (const log of this.stepLogs) {
      const icon = log.status === 'passed' ? '✓' : log.status === 'failed' ? '✗' : '○';
      const errorCount = log.consoleErrors.length + log.networkIssues.length;
      const errorMark = errorCount > 0 ? ` ⚠ ${errorCount} errors` : '';
      lines.push(`  ${icon} [${log.phase}] ${log.step} (${log.duration}ms)${errorMark}`);
    }

    // 添加错误详情
    if (this.networkIssues.length > 0) {
      lines.push('', 'Network Issues:');
      for (const issue of this.networkIssues.slice(0, 20)) {
        lines.push(`  [${issue.status}] ${issue.method} ${issue.url.substring(0, 100)}...`);
      }
      if (this.networkIssues.length > 20) {
        lines.push(`  ... and ${this.networkIssues.length - 20} more`);
      }
    }

    if (this.consoleErrors.length > 0) {
      lines.push('', 'Console Errors:');
      for (const err of this.consoleErrors.slice(0, 20)) {
        lines.push(`  [${err.type}] ${err.text.substring(0, 100)}...`);
      }
      if (this.consoleErrors.length > 20) {
        lines.push(`  ... and ${this.consoleErrors.length - 20} more`);
      }
    }

    lines.push('', '='.repeat(70));

    return lines.join('\n');
  }

  /**
   * 获取阶段摘要
   */
  private getPhaseSummary(): Record<string, any> {
    const phases: Record<string, any> = {};

    for (const log of this.stepLogs) {
      if (!phases[log.phase]) {
        phases[log.phase] = { steps: 0, errors: 0, duration: 0 };
      }
      phases[log.phase].steps++;
      phases[log.phase].errors += log.consoleErrors.length + log.networkIssues.length;
      phases[log.phase].duration += log.duration;
    }

    return phases;
  }

  /**
   * 获取所有错误
   */
  private getAllErrors(): Array<{ type: string; message: string; step?: string }> {
    const allErrors: Array<{ type: string; message: string; step?: string }> = [];

    for (const log of this.stepLogs) {
      for (const err of log.consoleErrors) {
        allErrors.push({
          type: 'Console',
          message: err.text,
          step: log.step,
        });
      }
      for (const issue of log.networkIssues) {
        allErrors.push({
          type: 'Network',
          message: `${issue.method} ${issue.url} - ${issue.status}`,
          step: log.step,
        });
      }
    }

    return allErrors;
  }

  /**
   * 保存报告到文件
   */
  async saveReport(): Promise<{ textPath: string; jsonPath: string }> {
    this.ensureLogDir();

    const { summary, textReport, jsonReport } = this.generateReport();

    const textPath = join(process.cwd(), this.logDir, 'final-report.txt');
    const jsonPath = join(process.cwd(), this.logDir, 'final-report.json');

    writeFileSync(textPath, textReport, 'utf-8');
    writeFileSync(jsonPath, JSON.stringify(jsonReport, null, 2), 'utf-8');

    console.log(`\n📄 Text report saved: ${textPath}`);
    console.log(`📊 JSON report saved: ${jsonPath}`);

    return { textPath, jsonPath };
  }

  /**
   * 打印摘要到控制台
   */
  printSummary(): void {
    const { summary } = this.generateReport();

    console.log('\n' + '='.repeat(50));
    console.log('Test Summary');
    console.log('='.repeat(50));
    console.log(`Duration: ${summary.totalDurationSec}s`);
    console.log(`Steps: ${summary.passedSteps}/${summary.totalSteps} passed`);
    if (summary.failedSteps > 0) {
      console.log(`Failed: ${summary.failedSteps}`);
    }
    console.log(`Errors: ${summary.totalConsoleErrors + summary.totalNetworkIssues}`);
    console.log('='.repeat(50));
  }

  // ============================================================================
  // Cleanup
  // ============================================================================

  /**
   * 清空日志
   */
  clearLogs(): void {
    this.stepLogs = [];
    this.consoleErrors = [];
    this.networkIssues = [];
    this.performanceMetrics = [];
  }

  /**
   * 获取所有日志
   */
  getLogs(): StepLog[] {
    return [...this.stepLogs];
  }

  /**
   * 获取日志目录路径
   */
  getLogDir(): string {
    return join(process.cwd(), this.logDir);
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * 创建综合监控器
 */
export function createComprehensiveMonitor(
  page: Page,
  options?: MonitorOptions
): ComprehensiveMonitor {
  return new ComprehensiveMonitor(page, options);
}
