/**
 * Combined Logger for Playwright E2E Tests
 *
 * 功能：
 * - 综合控制台日志、网络监控
 * - 实时日志记录
 * - 自动截图保存
 * - 生成综合测试报告
 */

import { Page } from '@playwright/test';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { ConsoleLogger, ConsoleError } from './console-logger';
import { NetworkMonitor, NetworkIssue } from './network-monitor';

export interface TestStepLog {
  phase: string;
  step: string;
  timestamp: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  consoleErrors: ConsoleError[];
  networkIssues: NetworkIssue[];
  screenshot?: string;
  details?: string;
}

export interface CombinedLoggerOptions {
  logDir?: string;
  autoScreenshot?: boolean;
  realTimeLog?: boolean;
}

export class CombinedLogger {
  private page: Page;
  private consoleLogger: ConsoleLogger;
  private networkMonitor: NetworkMonitor;
  private testStartTime: number;
  private phaseStartTime: number;
  private currentPhase: string = '';
  private logs: TestStepLog[] = [];
  private logDir: string;
  private options: Required<CombinedLoggerOptions>;

  constructor(page: Page, options: CombinedLoggerOptions = {}) {
    this.page = page;
    this.consoleLogger = new ConsoleLogger(page);
    this.networkMonitor = new NetworkMonitor(page);
    this.testStartTime = Date.now();
    this.phaseStartTime = Date.now();
    this.logDir = options.logDir || 'test-results/logs';
    this.options = {
      logDir: options.logDir || 'test-results/logs',
      autoScreenshot: options.autoScreenshot ?? true,
      realTimeLog: options.realTimeLog ?? true,
    };
  }

  /**
   * 开始监听
   */
  async start(): Promise<void> {
    await this.consoleLogger.start();
    await this.networkMonitor.start();

    // 确保日志目录存在
    if (!existsSync(join(process.cwd(), this.logDir))) {
      mkdirSync(join(process.cwd(), this.logDir), { recursive: true });
    }
  }

  /**
   * 停止监听
   */
  async stop(): Promise<{ consoleErrors: ConsoleError[]; networkIssues: NetworkIssue[] }> {
    const consoleErrors = await this.consoleLogger.stop();
    const networkIssues = await this.networkMonitor.stop();
    return { consoleErrors, networkIssues };
  }

  /**
   * 开始一个新的测试阶段
   */
  startPhase(phaseName: string): void {
    this.currentPhase = phaseName;
    this.phaseStartTime = Date.now();
    console.log(`\n${'='.repeat(60)}`);
    console.log(`[PHASE] ${phaseName}`);
    console.log('='.repeat(60));
  }

  /**
   * 记录测试步骤
   */
  async logStep(
    stepName: string,
    status: 'passed' | 'failed' | 'skipped' = 'passed',
    details: string = ''
  ): Promise<void> {
    const duration = Date.now() - this.phaseStartTime;
    const consoleErrors = this.consoleLogger.getErrors();
    const networkIssues = this.networkMonitor.getErrors();

    const stepLog: TestStepLog = {
      phase: this.currentPhase,
      step: stepName,
      timestamp: new Date().toISOString(),
      status,
      duration,
      consoleErrors: [...consoleErrors],
      networkIssues: [...networkIssues],
      details,
    };

    this.logs.push(stepLog);

    // 计算图标
    const hasErrors = consoleErrors.length > 0 || networkIssues.length > 0;
    const icon = status === 'passed' ? '✓' : status === 'failed' ? '✗' : '○';
    const warningIcon = hasErrors ? ' ⚠' : '';

    console.log(`${icon} [${stepName}]${warningIcon} (${duration}ms)`);

    // 详细输出错误信息
    if (hasErrors) {
      console.log(`  ⚠ Console Errors: ${consoleErrors.length}`);
      console.log(`  ⚠ Network Issues: ${networkIssues.length}`);

      // 输出最近的错误（最多3条）
      if (consoleErrors.length > 0) {
        const recentErrors = consoleErrors.slice(-3);
        recentErrors.forEach((err, i) => {
          console.log(`    [${i + 1}] ${err.type}: ${err.text.substring(0, 100)}${err.text.length > 100 ? '...' : ''}`);
        });
      }
      if (networkIssues.length > 0) {
        const recentIssues = networkIssues.slice(-3);
        recentIssues.forEach((issue, i) => {
          console.log(`    [${i + 1}] ${issue.method} ${issue.url.substring(0, 80)}... - ${issue.status}`);
        });
      }
    }

    if (details) {
      console.log(`  ℹ ${details}`);
    }

    // 如果有错误且启用了自动截图，保存截图
    if (hasErrors && status === 'failed' && this.options.autoScreenshot) {
      const screenshotPath = await this.saveScreenshot(stepName);
      stepLog.screenshot = screenshotPath;
    }

    // 实时保存日志到文件
    if (this.options.realTimeLog) {
      await this.saveRealtimeLog();
    }

    // 重置阶段计时器
    this.phaseStartTime = Date.now();
  }

  /**
   * 保存截图
   */
  async saveScreenshot(stepName: string): Promise<string> {
    const dir = join(process.cwd(), this.logDir);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    // 清理步骤名称，移除特殊字符
    const safeStepName = stepName.replace(/[^a-zA-Z0-9]/g, '_');
    const filename = `${this.currentPhase}_${safeStepName}_${Date.now()}.png`;
    const filepath = join(dir, filename);

    await this.page.screenshot({ path: filepath, fullPage: true });
    console.log(`  📸 Screenshot saved: ${filepath}`);
    return filepath;
  }

  /**
   * 保存实时日志
   */
  async saveRealtimeLog(): Promise<void> {
    const dir = join(process.cwd(), this.logDir);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const logContent = {
      currentPhase: this.currentPhase,
      totalDuration: Date.now() - this.testStartTime,
      phaseDuration: Date.now() - this.phaseStartTime,
      steps: this.logs,
      updatedAt: new Date().toISOString(),
    };

    const { writeFile } = await import('fs/promises');
    await writeFile(
      join(dir, 'realtime-log.json'),
      JSON.stringify(logContent, null, 2),
      'utf-8'
    );
  }

  /**
   * 保存最终报告
   */
  async saveFinalReport(): Promise<{ textPath: string; jsonPath: string }> {
    const dir = join(process.cwd(), this.logDir);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const totalDuration = Date.now() - this.testStartTime;

    // 生成可读的文本报告
    const lines = [
      '='.repeat(70),
      'Persistent E2E Test Report',
      '='.repeat(70),
      `Test Time: ${new Date().toISOString()}`,
      `Total Duration: ${(totalDuration / 1000).toFixed(2)}s (${(totalDuration / 60000).toFixed(2)}m)`,
      '',
      'Steps Summary:',
      ...this.logs.map((log, i) => {
        const icon = log.status === 'passed' ? '✓' : log.status === 'failed' ? '✗' : '○';
        const errorCount = log.consoleErrors.length + log.networkIssues.length;
        const errorMark = errorCount > 0 ? ` ⚠ ${errorCount} errors` : '';
        return `  [${i + 1}] ${icon} [${log.phase}] ${log.step} (${log.duration}ms)${errorMark}`;
      }),
      '',
      'Error Summary:',
      `  Console Errors: ${this.logs.reduce((sum, log) => sum + log.consoleErrors.length, 0)}`,
      `  Network Issues: ${this.logs.reduce((sum, log) => sum + log.networkIssues.length, 0)}`,
      '',
    ];

    // 添加详细错误信息
    const allErrors: Array<{ phase: string; step: string; type: string; message: string }> = [];

    for (const log of this.logs) {
      for (const err of log.consoleErrors) {
        allErrors.push({
          phase: log.phase,
          step: log.step,
          type: 'Console',
          message: err.text,
        });
      }
      for (const issue of log.networkIssues) {
        allErrors.push({
          phase: log.phase,
          step: log.step,
          type: 'Network',
          message: `${issue.method} ${issue.url} - ${issue.status}`,
        });
      }
    }

    if (allErrors.length > 0) {
      lines.push('Detailed Errors:');
      lines.push(...allErrors.slice(0, 50).map((err, i) =>
        `  [${i + 1}] [${err.phase}/${err.step}] ${err.type}: ${err.message.substring(0, 120)}${err.message.length > 120 ? '...' : ''}`
      ));

      if (allErrors.length > 50) {
        lines.push(`  ... and ${allErrors.length - 50} more errors`);
      }
    } else {
      lines.push('No errors detected! ✓');
    }

    lines.push('', '='.repeat(70));

    const { writeFile } = await import('fs/promises');

    // 保存文本报告
    const textPath = join(dir, 'final-report.txt');
    await writeFile(textPath, lines.join('\n'), 'utf-8');
    console.log(`\n📄 Text report saved: ${textPath}`);

    // 保存 JSON 报告
    const jsonPath = join(dir, 'final-report.json');
    const jsonReport = {
      testTime: new Date().toISOString(),
      totalDuration,
      logs: this.logs,
      summary: {
        totalSteps: this.logs.length,
        passedSteps: this.logs.filter(l => l.status === 'passed').length,
        failedSteps: this.logs.filter(l => l.status === 'failed').length,
        skippedSteps: this.logs.filter(l => l.status === 'skipped').length,
        totalConsoleErrors: this.logs.reduce((sum, l) => sum + l.consoleErrors.length, 0),
        totalNetworkIssues: this.logs.reduce((sum, l) => sum + l.networkIssues.length, 0),
      },
    };
    await writeFile(jsonPath, JSON.stringify(jsonReport, null, 2), 'utf-8');
    console.log(`📊 JSON report saved: ${jsonPath}`);

    return { textPath, jsonPath };
  }

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.logs.some(log =>
      log.consoleErrors.length > 0 || log.networkIssues.length > 0
    );
  }

  /**
   * 获取所有日志
   */
  getLogs(): TestStepLog[] {
    return [...this.logs];
  }

  /**
   * 获取日志目录路径
   */
  getLogDir(): string {
    return join(process.cwd(), this.logDir);
  }

  /**
   * 打印实时摘要
   */
  printSummary(): void {
    const totalDuration = Date.now() - this.testStartTime;
    const totalSteps = this.logs.length;
    const passedSteps = this.logs.filter(l => l.status === 'passed').length;
    const failedSteps = this.logs.filter(l => l.status === 'failed').length;
    const totalErrors = this.logs.reduce((sum, l) => sum + l.consoleErrors.length + l.networkIssues.length, 0);

    console.log('\n' + '='.repeat(50));
    console.log('Real-time Summary');
    console.log('='.repeat(50));
    console.log(`Duration: ${(totalDuration / 1000).toFixed(2)}s`);
    console.log(`Steps: ${passedSteps}/${totalSteps} passed`);
    if (failedSteps > 0) {
      console.log(`Failed: ${failedSteps}`);
    }
    console.log(`Errors: ${totalErrors}`);
    console.log('='.repeat(50));
  }

  /**
   * 清空日志
   */
  clearLogs(): void {
    this.logs = [];
    this.consoleLogger.clearErrors();
    this.networkMonitor.clearErrors();
  }
}
