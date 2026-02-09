/**
 * Test State Tracker for Playwright E2E Tests
 *
 * 功能：
 * - 跟踪测试创建的资源
 * - 记录测试阶段结果
 * - 生成测试报告
 */

import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { logger } from './logger';
import { join } from 'path';

export interface TestResource {
  type: string;
  id: string;
  name: string;
  createdAt: string;
  metadata?: Record<string, any>;
}

export interface PhaseResult {
  phase: string;
  errors: any[];
  networkIssues: any[];
  duration: number;
  status: 'passed' | 'failed' | 'skipped';
}

export class TestStateTracker {
  private resources: TestResource[] = [];
  private phaseResults: PhaseResult[] = [];
  private phaseStartTime: number = 0;
  private currentPhase: string = '';
  private testStartTime: number = Date.now();

  /**
   * 开始一个新的测试阶段
   */
  startPhase(phaseName: string): void {
    this.currentPhase = phaseName;
    this.phaseStartTime = Date.now();
    logger.info(`\n========== [START] ${phaseName} ==========`);
  }

  /**
   * 结束当前阶段并记录结果
   */
  endPhase(errors: any[] = [], networkIssues: any[] = [], status: 'passed' | 'failed' | 'skipped' = 'passed'): void {
    const duration = Date.now() - this.phaseStartTime;

    this.phaseResults.push({
      phase: this.currentPhase,
      errors,
      networkIssues,
      duration,
      status,
    });

    const icon = status === 'passed' ? '✓' : status === 'failed' ? '✗' : '○';
    logger.info(`${icon} [END] ${this.currentPhase} (${duration}ms)`);

    this.currentPhase = '';
  }

  /**
   * 跟踪创建的资源
   */
  trackResource(type: string, id: string, name: string, metadata?: Record<string, any>): void {
    this.resources.push({
      type,
      id,
      name,
      createdAt: new Date().toISOString(),
      metadata,
    });

    logger.info(`  + Tracked resource: [${type}] ${name} (ID: ${id})`);
  }

  /**
   * 按类型获取资源
   */
  getResourcesByType(type: string): TestResource[] {
    return this.resources.filter(r => r.type === type);
  }

  /**
   * 获取所有资源
   */
  getAllResources(): TestResource[] {
    return [...this.resources];
  }

  /**
   * 获取阶段结果
   */
  getPhaseResults(): PhaseResult[] {
    return [...this.phaseResults];
  }

  /**
   * 获取当前阶段名称
   */
  getCurrentPhase(): string {
    return this.currentPhase;
  }

  /**
   * 生成测试报告
   */
  getReport(): string {
    const totalDuration = Date.now() - this.testStartTime;
    const lines = [
      '='.repeat(70),
      'Persistent E2E Test Report',
      '='.repeat(70),
      `Test Time: ${new Date().toISOString()}`,
      `Total Duration: ${(totalDuration / 1000).toFixed(2)}s`,
      '',
      'Resources Created:',
      ...this.resources.map(r =>
        `  - [${r.type}] ${r.name} (ID: ${r.id})${r.metadata ? ` - ${JSON.stringify(r.metadata)}` : ''}`
      ),
      '',
      'Phase Results:',
      ...this.phaseResults.map(pr => {
        const icon = pr.status === 'passed' ? '✓' : pr.status === 'failed' ? '✗' : '○';
        return `  ${icon} ${pr.phase}: ${pr.duration}ms - ${pr.errors.length} console errors, ${pr.networkIssues.length} network issues`;
      }),
      '',
      'Summary:',
      `  Total Resources: ${this.resources.length}`,
      `  Total Phases: ${this.phaseResults.length}`,
      `  Passed Phases: ${this.phaseResults.filter(p => p.status === 'passed').length}`,
      `  Failed Phases: ${this.phaseResults.filter(p => p.status === 'failed').length}`,
      `  Total Errors: ${this.phaseResults.reduce((sum, p) => sum + p.errors.length, 0)}`,
      `  Total Network Issues: ${this.phaseResults.reduce((sum, p) => sum + p.networkIssues.length, 0)}`,
      '',
      '='.repeat(70),
    ];

    return lines.join('\n');
  }

  /**
   * 保存报告到文件
   */
  async saveReport(filePath?: string): Promise<void> {
    const dir = join(process.cwd(), 'test-results');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const reportPath = filePath || join(dir, 'persistent-test-report.txt');
    const { writeFile } = await import('fs/promises');
    await writeFile(reportPath, this.getReport(), 'utf-8');
    logger.info(`\n📄 Test report saved: ${reportPath}`);
  }

  /**
   * 保存JSON格式的状态文件
   */
  async saveState(filePath?: string): Promise<void> {
    const dir = join(process.cwd(), 'test-results');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    const statePath = filePath || join(dir, 'persistent-test-state.json');
    const { writeFile } = await import('fs/promises');

    const state = {
      testTime: new Date().toISOString(),
      totalDuration: Date.now() - this.testStartTime,
      resources: this.resources,
      phaseResults: this.phaseResults,
    };

    await writeFile(statePath, JSON.stringify(state, null, 2), 'utf-8');
    logger.info(`📊 Test state saved: ${statePath}`);
  }

  /**
   * 清空状态
   */
  clear(): void {
    this.resources = [];
    this.phaseResults = [];
    this.currentPhase = '';
    this.testStartTime = Date.now();
  }

  /**
   * 打印摘要到控制台
   */
  printSummary(): void {
    logger.info('\n' + '='.repeat(50));
    logger.info('Test Summary');
    logger.info('='.repeat(50));
    logger.info(`Resources Created: ${this.resources.length}`);
    logger.info(`Phases Completed: ${this.phaseResults.length}`);
    logger.info('');

    if (this.resources.length > 0) {
      logger.info('Resources by Type:');
      const byType: Record<string, number> = {};
      for (const r of this.resources) {
        byType[r.type] = (byType[r.type] || 0) + 1;
      }
      for (const [type, count] of Object.entries(byType)) {
        logger.info(`  - ${type}: ${count}`);
      }
    }

    logger.info('');
    logger.info('='.repeat(50));
  }
}
