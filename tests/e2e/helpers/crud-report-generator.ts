/**
 * CRUD 验收报告生成器
 *
 * 功能：
 * - 生成 Markdown 格式验收报告
 * - 包含验收概览（通过/失败/跳过统计）
 * - 每个模块的详细结果
 * - 网络请求记录
 * - 截图链接
 *
 * @description P0 核心功能 CRUD 验收专用
 */

import { writeFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join, relative } from 'path';
import { NetworkRequest, CrudOperationResult } from './crud-network-monitor';

// ==================== 类型定义 ====================

export type CrudOperation = 'create' | 'read' | 'update' | 'delete';

export interface CrudTestResult {
  /** 模块名称 */
  moduleName: string;
  /** 页面路由 */
  route: string;
  /** API 前缀 */
  apiPrefix: string;
  /** 优先级 */
  priority: 'P0' | 'P1' | 'P2';
  /** 操作结果 */
  operations: {
    create?: OperationTestResult;
    read?: OperationTestResult;
    update?: OperationTestResult;
    delete?: OperationTestResult;
  };
  /** 所有网络请求 */
  networkRequests: NetworkRequest[];
  /** 测试开始时间 */
  startTime: number;
  /** 测试结束时间 */
  endTime: number;
}

export interface OperationTestResult {
  /** 操作类型 */
  operation: CrudOperation;
  /** 测试状态 */
  status: 'passed' | 'failed' | 'skipped';
  /** 网络请求验证结果 */
  networkResult?: CrudOperationResult;
  /** 截图路径 */
  screenshotPath?: string;
  /** 错误信息 */
  error?: string;
  /** 耗时(ms) */
  duration: number;
  /** 时间戳 */
  timestamp: string;
}

export interface CrudReportSummary {
  /** 生成时间 */
  generatedAt: string;
  /** 测试环境 */
  environment: {
    frontendUrl: string;
    backendUrl: string;
  };
  /** 总耗时 */
  totalDuration: number;
  /** 统计 */
  statistics: {
    totalOperations: number;
    passed: number;
    failed: number;
    skipped: number;
    passRate: number;
  };
  /** 按模块统计 */
  byModule: Record<string, {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
  }>;
  /** 按操作统计 */
  byOperation: Record<CrudOperation, {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
  }>;
}

export interface FullCrudReport {
  summary: CrudReportSummary;
  results: CrudTestResult[];
}

// ==================== 报告生成器类 ====================

export class CrudReportGenerator {
  private reportDir: string;
  private results: CrudTestResult[] = [];
  private frontendUrl: string;
  private backendUrl: string;
  private testStartTime: number;

  constructor(options: {
    reportDir?: string;
    frontendUrl?: string;
    backendUrl?: string;
  } = {}) {
    this.reportDir = options.reportDir || 'test-results/crud';
    this.frontendUrl = options.frontendUrl || 'http://localhost:3000';
    this.backendUrl = options.backendUrl || 'http://localhost:5000';
    this.testStartTime = Date.now();
  }

  /**
   * 添加测试结果
   */
  addResult(result: CrudTestResult): void {
    this.results.push(result);
  }

  /**
   * 生成摘要
   */
  private generateSummary(): CrudReportSummary {
    const now = new Date();
    const totalDuration = Date.now() - this.testStartTime;

    // 初始化统计
    const statistics = {
      totalOperations: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      passRate: 0,
    };

    const byModule: Record<string, {
      total: number;
      passed: number;
      failed: number;
      skipped: number;
    }> = {};

    const byOperation: Record<CrudOperation, {
      total: number;
      passed: number;
      failed: number;
      skipped: number;
    }> = {
      create: { total: 0, passed: 0, failed: 0, skipped: 0 },
      read: { total: 0, passed: 0, failed: 0, skipped: 0 },
      update: { total: 0, passed: 0, failed: 0, skipped: 0 },
      delete: { total: 0, passed: 0, failed: 0, skipped: 0 },
    };

    // 计算统计
    for (const result of this.results) {
      const moduleName = result.moduleName;

      if (!byModule[moduleName]) {
        byModule[moduleName] = { total: 0, passed: 0, failed: 0, skipped: 0 };
      }

      for (const [op, opResult] of Object.entries(result.operations)) {
        if (!opResult) continue;

        const operation = op as CrudOperation;

        statistics.totalOperations++;
        byModule[moduleName].total++;
        byOperation[operation].total++;

        switch (opResult.status) {
          case 'passed':
            statistics.passed++;
            byModule[moduleName].passed++;
            byOperation[operation].passed++;
            break;
          case 'failed':
            statistics.failed++;
            byModule[moduleName].failed++;
            byOperation[operation].failed++;
            break;
          case 'skipped':
            statistics.skipped++;
            byModule[moduleName].skipped++;
            byOperation[operation].skipped++;
            break;
        }
      }
    }

    statistics.passRate = statistics.totalOperations > 0
      ? Math.round((statistics.passed / statistics.totalOperations) * 100 * 10) / 10
      : 0;

    return {
      generatedAt: now.toISOString(),
      environment: {
        frontendUrl: this.frontendUrl,
        backendUrl: this.backendUrl,
      },
      totalDuration,
      statistics,
      byModule,
      byOperation,
    };
  }

  /**
   * 生成 Markdown 报告
   */
  generateMarkdownReport(): string {
    const summary = this.generateSummary();

    let md = `# P0 核心功能 CRUD 验收报告\n\n`;
    md += `> 验收时间: ${new Date(summary.generatedAt).toLocaleString('zh-CN')}\n`;
    md += `> 验收环境: ${summary.environment.frontendUrl} (前端) + ${summary.environment.backendUrl} (后端)\n`;
    md += `> 总耗时: ${Math.round(summary.totalDuration / 1000)}s\n\n`;

    // ==================== 概览 ====================
    md += `## 概览\n\n`;
    md += `| 指标 | 数值 |\n`;
    md += `|------|------|\n`;
    md += `| 总操作数 | ${summary.statistics.totalOperations} |\n`;
    md += `| 通过 | ${summary.statistics.passed} |\n`;
    md += `| 失败 | ${summary.statistics.failed} |\n`;
    md += `| 跳过 | ${summary.statistics.skipped} |\n`;
    md += `| **通过率** | **${summary.statistics.passRate}%** |\n\n`;

    // ==================== 按操作统计 ====================
    md += `## 按操作统计\n\n`;
    md += `| 操作 | 总数 | 通过 | 失败 | 跳过 |\n`;
    md += `|------|------|------|------|------|\n`;
    for (const [op, stats] of Object.entries(summary.byOperation)) {
      const statusIcon = stats.failed === 0 ? '✅' : '❌';
      md += `| ${statusIcon} ${op.toUpperCase()} | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.skipped} |\n`;
    }
    md += `\n`;

    // ==================== 按模块统计 ====================
    md += `## 按模块统计\n\n`;
    md += `| 模块 | 总数 | 通过 | 失败 | 跳过 |\n`;
    md += `|------|------|------|------|------|\n`;
    for (const [moduleName, stats] of Object.entries(summary.byModule)) {
      const statusIcon = stats.failed === 0 ? '✅' : '❌';
      md += `| ${statusIcon} ${moduleName} | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.skipped} |\n`;
    }
    md += `\n`;

    // ==================== 详细结果 ====================
    md += `## 详细结果\n\n`;

    for (const result of this.results) {
      md += `### ${result.priority}: ${result.moduleName}\n\n`;
      md += `- **路由**: \`${result.route}\`\n`;
      md += `- **API 前缀**: \`${result.apiPrefix}\`\n`;
      md += `- **测试时间**: ${Math.round((result.endTime - result.startTime) / 1000)}s\n\n`;

      md += `| 操作 | 状态 | 网络请求 | 耗时 | 截图 |\n`;
      md += `|------|------|----------|------|------|\n`;

      const operations: CrudOperation[] = ['read', 'create', 'update', 'delete'];
      for (const op of operations) {
        const opResult = result.operations[op];
        if (!opResult) {
          md += `| ${op.toUpperCase()} | ⏭️ 未配置 | - | - | - |\n`;
          continue;
        }

        let statusIcon: string;
        switch (opResult.status) {
          case 'passed':
            statusIcon = '✅';
            break;
          case 'failed':
            statusIcon = '❌';
            break;
          case 'skipped':
            statusIcon = '⏭️';
            break;
        }

        const networkInfo = opResult.networkResult
          ? `${opResult.networkResult.actualMethod || '-'} ${opResult.networkResult.actualStatus || '-'}`
          : '-';

        const screenshotLink = opResult.screenshotPath
          ? `[查看](${relative(this.reportDir, opResult.screenshotPath)})`
          : '-';

        md += `| ${op.toUpperCase()} | ${statusIcon} ${opResult.status} | ${networkInfo} | ${opResult.duration}ms | ${screenshotLink} |\n`;
      }

      md += `\n`;

      // 错误信息
      const errors = Object.values(result.operations)
        .filter(op => op && op.status === 'failed' && op.error);

      if (errors.length > 0) {
        md += `**错误详情:**\n`;
        for (const err of errors) {
          if (err) {
            md += `- ${err.operation}: ${err.error}\n`;
          }
        }
        md += `\n`;
      }
    }

    // ==================== 网络请求汇总 ====================
    md += `## 网络请求汇总\n\n`;
    md += `详细网络请求日志请查看: \`network-requests.json\`\n\n`;

    // 统计所有请求
    const allRequests = this.results.flatMap(r => r.networkRequests);
    const apiRequests = allRequests.filter(r => r.isApiRequest);

    md += `| 指标 | 数值 |\n`;
    md += `|------|------|\n`;
    md += `| 总请求数 | ${allRequests.length} |\n`;
    md += `| API 请求数 | ${apiRequests.length} |\n`;
    md += `| 成功 (2xx) | ${apiRequests.filter(r => r.status >= 200 && r.status < 300).length} |\n`;
    md += `| 错误 (4xx/5xx) | ${apiRequests.filter(r => r.status >= 400).length} |\n\n`;

    // ==================== 失败记录 ====================
    const failedOps = this.results.flatMap(r =>
      Object.values(r.operations)
        .filter(op => op && op.status === 'failed')
        .map(op => ({ module: r.moduleName, ...op }))
    );

    if (failedOps.length > 0) {
      md += `## 失败记录\n\n`;
      for (const op of failedOps) {
        if (op) {
          md += `- **[${op.module}] ${op.operation}**: ${op.error || '未知错误'}\n`;
        }
      }
      md += `\n`;
    }

    // ==================== 验收结论 ====================
    md += `## 验收结论\n\n`;

    if (summary.statistics.failed === 0) {
      md += `✅ **验收通过**: 所有 ${summary.statistics.totalOperations} 项 CRUD 操作均已通过验证。\n`;
    } else {
      md += `❌ **验收未通过**: ${summary.statistics.failed} 项操作失败，需要修复后重新验收。\n\n`;
      md += `### 需要关注的问题:\n`;
      for (const result of this.results) {
        for (const [op, opResult] of Object.entries(result.operations)) {
          if (opResult && opResult.status === 'failed') {
            md += `- [ ] [${result.moduleName}] ${op} 操作失败: ${opResult.error}\n`;
          }
        }
      }
    }

    return md;
  }

  /**
   * 生成 HTML 报告
   */
  generateHtmlReport(): string {
    const summary = this.generateSummary();

    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>P0 核心功能 CRUD 验收报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f7fa;
      color: #333;
      line-height: 1.6;
      padding: 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
      border-radius: 12px;
      margin-bottom: 24px;
    }
    .header h1 { font-size: 24px; margin-bottom: 8px; }
    .header .meta { opacity: 0.9; font-size: 14px; }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stat-card .value { font-size: 32px; font-weight: bold; }
    .stat-card .label { color: #666; font-size: 14px; }
    .stat-card.passed .value { color: #52c41a; }
    .stat-card.failed .value { color: #ff4d4f; }
    .stat-card.rate .value { color: #1890ff; }
    .section {
      background: white;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .section-title {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 2px solid #f0f0f0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #f0f0f0;
    }
    th { background: #fafafa; font-weight: 600; }
    tr:hover { background: #fafafa; }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }
    .badge.passed { background: #f6ffed; color: #52c41a; }
    .badge.failed { background: #fff2f0; color: #ff4d4f; }
    .badge.skipped { background: #fafafa; color: #999; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>P0 核心功能 CRUD 验收报告</h1>
      <div class="meta">
        验收时间: ${new Date(summary.generatedAt).toLocaleString('zh-CN')} |
        总耗时: ${Math.round(summary.totalDuration / 1000)}s
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="value">${summary.statistics.totalOperations}</div>
        <div class="label">总操作数</div>
      </div>
      <div class="stat-card passed">
        <div class="value">${summary.statistics.passed}</div>
        <div class="label">通过</div>
      </div>
      <div class="stat-card failed">
        <div class="value">${summary.statistics.failed}</div>
        <div class="label">失败</div>
      </div>
      <div class="stat-card rate">
        <div class="value">${summary.statistics.passRate}%</div>
        <div class="label">通过率</div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">按模块统计</div>
      <table>
        <thead>
          <tr>
            <th>模块</th>
            <th>总数</th>
            <th>通过</th>
            <th>失败</th>
            <th>跳过</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(summary.byModule).map(([name, stats]) => `
            <tr>
              <td>${name}</td>
              <td>${stats.total}</td>
              <td style="color: #52c41a">${stats.passed}</td>
              <td style="color: #ff4d4f">${stats.failed}</td>
              <td style="color: #999">${stats.skipped}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div class="section">
      <div class="section-title">详细结果</div>
      ${this.results.map(result => `
        <h4 style="margin: 16px 0 8px;">${result.priority}: ${result.moduleName}</h4>
        <p style="color: #666; font-size: 14px; margin-bottom: 8px;">
          路由: <code>${result.route}</code> | API: <code>${result.apiPrefix}</code>
        </p>
        <table>
          <thead>
            <tr>
              <th>操作</th>
              <th>状态</th>
              <th>网络请求</th>
              <th>耗时</th>
            </tr>
          </thead>
          <tbody>
            ${(['read', 'create', 'update', 'delete'] as const).map(op => {
              const opResult = result.operations[op];
              if (!opResult) {
                return `<tr><td>${op.toUpperCase()}</td><td><span class="badge skipped">未配置</span></td><td>-</td><td>-</td></tr>`;
              }
              const networkInfo = opResult.networkResult
                ? `${opResult.networkResult.actualMethod || '-'} ${opResult.networkResult.actualStatus || '-'}`
                : '-';
              return `
                <tr>
                  <td>${op.toUpperCase()}</td>
                  <td><span class="badge ${opResult.status}">${opResult.status}</span></td>
                  <td>${networkInfo}</td>
                  <td>${opResult.duration}ms</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `).join('')}
    </div>
  </div>
</body>
</html>`;

    return html;
  }

  /**
   * 生成 JSON 报告
   */
  generateJsonReport(): string {
    const report: FullCrudReport = {
      summary: this.generateSummary(),
      results: this.results,
    };

    return JSON.stringify(report, null, 2);
  }

  /**
   * 保存所有报告
   */
  async saveReports(): Promise<string[]> {
    if (!existsSync(this.reportDir)) {
      await mkdir(this.reportDir, { recursive: true });
    }

    const savedFiles: string[] = [];

    // Markdown 报告
    const mdPath = join(this.reportDir, 'acceptance-report.md');
    await writeFile(mdPath, this.generateMarkdownReport(), 'utf-8');
    savedFiles.push(mdPath);

    // HTML 报告
    const htmlPath = join(this.reportDir, 'acceptance-report.html');
    await writeFile(htmlPath, this.generateHtmlReport(), 'utf-8');
    savedFiles.push(htmlPath);

    // JSON 报告
    const jsonPath = join(this.reportDir, 'acceptance-report.json');
    await writeFile(jsonPath, this.generateJsonReport(), 'utf-8');
    savedFiles.push(jsonPath);

    return savedFiles;
  }

  /**
   * 获取报告目录
   */
  getReportDir(): string {
    return this.reportDir;
  }

  /**
   * 获取所有结果
   */
  getResults(): CrudTestResult[] {
    return [...this.results];
  }

  /**
   * 清空结果
   */
  clearResults(): void {
    this.results = [];
    this.testStartTime = Date.now();
  }
}

// ==================== 工厂函数 ====================

/**
 * 创建 CRUD 报告生成器
 */
export function createCrudReportGenerator(options?: {
  reportDir?: string;
  frontendUrl?: string;
  backendUrl?: string;
}): CrudReportGenerator {
  return new CrudReportGenerator(options);
}
