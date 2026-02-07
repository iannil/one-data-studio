/**
 * 报告生成器
 * 生成多种格式的测试报告
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { PageValidationResult } from './interactive-validator';

// ==================== 类型定义 ====================

export interface ReportSummary {
  generatedAt: string;
  duration: number;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  passRate: number;
  byModule: Record<string, ModuleStats>;
  byPageType: Record<string, PageTypeStats>;
}

export interface ModuleStats {
  total: number;
  passed: number;
  failed: number;
  passRate: number;
  avgLoadTime: number;
}

export interface PageTypeStats {
  total: number;
  passed: number;
  failed: number;
}

export interface FullReportData {
  summary: ReportSummary;
  results: PageValidationResult[];
  errors: string[];
  warnings: string[];
}

// ==================== 报告生成器类 ====================

export class ReportGenerator {
  private reportDir: string;
  private reportBaseUrl?: string;

  constructor(reportDir = 'test-results/interactive-reports', reportBaseUrl?: string) {
    this.reportDir = reportDir;
    this.reportBaseUrl = reportBaseUrl;
  }

  /**
   * 确保报告目录存在
   */
  private async ensureDir(): Promise<void> {
    if (!existsSync(this.reportDir)) {
      await mkdir(this.reportDir, { recursive: true });
    }
  }

  /**
   * 生成完整报告
   */
  async generateFullReport(results: PageValidationResult[], duration = 0): Promise<string[]> {
    await this.ensureDir();

    const generatedFiles: string[] = [];

    // 生成 HTML 报告
    const htmlFile = await this.generateHtmlReport(results, duration);
    generatedFiles.push(htmlFile);

    // 生成 Markdown 报告
    const mdFile = await this.generateMarkdownReport(results, duration);
    generatedFiles.push(mdFile);

    // 生成 JSON 报告
    const jsonFile = await this.generateJsonReport(results, duration);
    generatedFiles.push(jsonFile);

    // 生成 CSV 报告
    const csvFile = await this.generateCsvReport(results);
    generatedFiles.push(csvFile);

    return generatedFiles;
  }

  /**
   * 生成 HTML 报告
   */
  async generateHtmlReport(results: PageValidationResult[], duration = 0): Promise<string> {
    const summary = this.generateSummary(results, duration);

    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ONE-DATA-STUDIO 功能验证报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: #f5f5f5;
      color: #333;
      line-height: 1.6;
    }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
      border-radius: 10px;
      margin-bottom: 30px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header h1 { font-size: 28px; margin-bottom: 10px; }
    .header .meta { opacity: 0.9; font-size: 14px; }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }
    .stat-card {
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      text-align: center;
    }
    .stat-card .value { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
    .stat-card .label { color: #666; font-size: 14px; }
    .stat-card.total .value { color: #667eea; }
    .stat-card.passed .value { color: #52c41a; }
    .stat-card.failed .value { color: #ff4d4f; }
    .stat-card.rate .value { color: #1890ff; }
    .section {
      background: white;
      border-radius: 10px;
      padding: 25px;
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .section-title {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 20px;
      padding-bottom: 10px;
      border-bottom: 2px solid #f0f0f0;
    }
    .module-stats {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 15px;
    }
    .module-stat {
      padding: 15px;
      border-radius: 8px;
      background: #fafafa;
      border-left: 4px solid #667eea;
    }
    .module-stat.passed { border-left-color: #52c41a; }
    .module-stat.failed { border-left-color: #ff4d4f; }
    .module-stat h4 { margin-bottom: 10px; font-size: 16px; }
    .module-stat .info { font-size: 13px; color: #666; }
    .page-list { display: grid; gap: 15px; }
    .page-item {
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      overflow: hidden;
    }
    .page-item.passed { border-color: #b7eb8f; }
    .page-item.failed { border-color: #ffccc7; }
    .page-header {
      padding: 15px 20px;
      background: #fafafa;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }
    .page-item.passed .page-header { background: #f6ffed; }
    .page-item.failed .page-header { background: #fff2f0; }
    .page-title { font-weight: 600; font-size: 15px; }
    .page-badge {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }
    .page-item.passed .page-badge { background: #52c41a; color: white; }
    .page-item.failed .page-badge { background: #ff4d4f; color: white; }
    .page-details {
      padding: 20px;
      display: none;
      border-top: 1px solid #e8e8e8;
    }
    .page-item.expanded .page-details { display: block; }
    .op-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 15px;
    }
    .op-item {
      padding: 10px;
      border-radius: 6px;
      text-align: center;
      font-size: 13px;
    }
    .op-item.success { background: #f6ffed; color: #52c41a; }
    .op-item.failed { background: #fff2f0; color: #ff4d4f; }
    .op-item.skipped { background: #fafafa; color: #999; }
    .error-list {
      margin-top: 15px;
      padding: 15px;
      background: #fff2f0;
      border-radius: 6px;
      border-left: 4px solid #ff4d4f;
    }
    .error-list li { margin-bottom: 8px; color: #cf1322; }
    .warning-list {
      margin-top: 15px;
      padding: 15px;
      background: #fffbe6;
      border-radius: 6px;
      border-left: 4px solid #faad14;
    }
    .warning-list li { margin-bottom: 8px; color: #d46b08; }
    .screenshot-link {
      display: inline-block;
      margin-top: 10px;
      padding: 8px 16px;
      background: #1890ff;
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-size: 13px;
    }
    .filter-bar {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }
    .filter-btn {
      padding: 8px 16px;
      border: 1px solid #d9d9d9;
      background: white;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.3s;
    }
    .filter-btn:hover { border-color: #1890ff; color: #1890ff; }
    .filter-btn.active { background: #1890ff; color: white; border-color: #1890ff; }
    .progress-bar {
      height: 8px;
      background: #f0f0f0;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 5px;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #52c41a, #1890ff);
      transition: width 0.3s;
    }
    @media (max-width: 768px) {
      .summary { grid-template-columns: repeat(2, 1fr); }
      .header h1 { font-size: 22px; }
      .stat-card .value { font-size: 28px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>ONE-DATA-STUDIO 功能验证报告</h1>
      <div class="meta">
        <span>生成时间: ${summary.generatedAt}</span>
        <span style="margin: 0 15px;">|</span>
        <span>总耗时: ${(summary.duration / 1000).toFixed(2)}s</span>
      </div>
    </div>

    <div class="summary">
      <div class="stat-card total">
        <div class="value">${summary.total}</div>
        <div class="label">总页面数</div>
      </div>
      <div class="stat-card passed">
        <div class="value">${summary.passed}</div>
        <div class="label">通过</div>
      </div>
      <div class="stat-card failed">
        <div class="value">${summary.failed}</div>
        <div class="label">失败</div>
      </div>
      <div class="stat-card rate">
        <div class="value">${summary.passRate.toFixed(1)}%</div>
        <div class="label">通过率</div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">模块统计</div>
      <div class="module-stats">
        ${Object.entries(summary.byModule).map(([module, stats]) => `
          <div class="module-stat ${stats.failed === 0 ? 'passed' : 'failed'}">
            <h4>${this.getModuleName(module)}</h4>
            <div class="info">
              通过: ${stats.passed}/${stats.total} (${stats.passRate.toFixed(1)}%)<br>
              平均加载时间: ${stats.avgLoadTime}ms
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${stats.passRate}%"></div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        页面详情
        <div class="filter-bar" style="margin-top: 15px;">
          <button class="filter-btn active" onclick="filterPages('all')">全部</button>
          <button class="filter-btn" onclick="filterPages('passed')">通过</button>
          <button class="filter-btn" onclick="filterPages('failed')">失败</button>
        </div>
      </div>
      <div class="page-list">
        ${results.map((result, index) => this.renderPageItem(result, index)).join('\n')}
      </div>
    </div>
  </div>

  <script>
    function togglePage(index) {
      const item = document.querySelector('.page-item[data-index="' + index + '"]');
      item.classList.toggle('expanded');
    }

    function filterPages(type) {
      const items = document.querySelectorAll('.page-item');
      const buttons = document.querySelectorAll('.filter-btn');

      buttons.forEach(btn => btn.classList.remove('active'));
      event.target.classList.add('active');

      items.forEach(item => {
        if (type === 'all') {
          item.style.display = '';
        } else if (type === 'passed') {
          item.style.display = item.classList.contains('passed') ? '' : 'none';
        } else if (type === 'failed') {
          item.style.display = item.classList.contains('failed') ? '' : 'none';
        }
      });
    }
  </script>
</body>
</html>`;

    const filePath = join(this.reportDir, 'report.html');
    await writeFile(filePath, html, 'utf-8');
    return filePath;
  }

  /**
   * 渲染单个页面项的 HTML
   */
  private renderPageItem(result: PageValidationResult, index: number): string {
    const passed = this.isPagePassed(result);
    const hasErrors = result.errors.length > 0;
    const hasWarnings = result.warnings.length > 0;

    return `
      <div class="page-item ${passed ? 'passed' : 'failed'}" data-index="${index}">
        <div class="page-header" onclick="togglePage(${index})">
          <div>
            <span class="page-title">${result.pageName}</span>
            <span style="color: #999; font-size: 13px; margin-left: 10px;">${result.route}</span>
          </div>
          <span class="page-badge">${passed ? 'PASSED' : 'FAILED'}</span>
        </div>
        <div class="page-details">
          <div style="margin-bottom: 15px;">
            <strong>模块:</strong> ${this.getModuleName(result.module)}<br>
            <strong>加载时间:</strong> ${result.pageLoad.loadTime}ms<br>
            <strong>验证时间:</strong> ${result.validatedAt}
          </div>

          <div class="op-grid">
            <div class="op-item ${result.operations.create?.success ? 'success' : result.operations.create ? 'failed' : 'skipped'}">
              创建: ${result.operations.create?.success ? '✓' : result.operations.create ? '✗' : '-'}
            </div>
            <div class="op-item ${result.operations.read?.success ? 'success' : result.operations.read ? 'failed' : 'skipped'}">
              读取: ${result.operations.read?.success ? '✓' : result.operations.read ? '✗' : '-'}
            </div>
            <div class="op-item ${result.operations.update?.success ? 'success' : result.operations.update ? 'failed' : 'skipped'}">
              更新: ${result.operations.update?.success ? '✓' : result.operations.update ? '✗' : '-'}
            </div>
            <div class="op-item ${result.operations.delete?.success ? 'success' : result.operations.delete ? 'failed' : 'skipped'}">
              删除: ${result.operations.delete?.success ? '✓' : result.operations.delete ? '✗' : '-'}
            </div>
          </div>

          ${hasErrors ? `
            <div class="error-list">
              <strong>错误:</strong>
              <ul>${result.errors.map(e => `<li>${e}</li>`).join('')}</ul>
            </div>
          ` : ''}

          ${hasWarnings ? `
            <div class="warning-list">
              <strong>警告:</strong>
              <ul>${result.warnings.map(w => `<li>${w}</li>`).join('')}</ul>
            </div>
          ` : ''}

          ${result.screenshotPath ? `
            <a href="${result.screenshotPath}" target="_blank" class="screenshot-link">查看截图</a>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * 生成 Markdown 报告
   */
  async generateMarkdownReport(results: PageValidationResult[], duration = 0): Promise<string> {
    const summary = this.generateSummary(results, duration);

    const markdown = `# ONE-DATA-STUDIO 功能验证报告

> 生成时间: ${summary.generatedAt}
> 总耗时: ${(summary.duration / 1000).toFixed(2)}s

## 汇总统计

| 指标 | 数值 |
|------|------|
| 总页面数 | ${summary.total} |
| 通过 | ${summary.passed} |
| 失败 | ${summary.failed} |
| 跳过 | ${summary.skipped} |
| **通过率** | **${summary.passRate.toFixed(1)}%** |

## 模块统计

| 模块 | 总数 | 通过 | 失败 | 通过率 | 平均加载时间 |
|------|------|------|------|--------|--------------|
${Object.entries(summary.byModule).map(([module, stats]) => {
  const moduleName = this.getModuleName(module);
  return `| ${moduleName} | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.passRate.toFixed(1)}% | ${stats.avgLoadTime}ms |`;
}).join('\n')}

## 详细结果

${results.map(result => this.renderMarkdownPage(result)).join('\n\n---\n\n')}

## 错误汇总

${this.collectAllErrors(results).length > 0 ? `
${this.collectAllErrors(results).map(error => `- **${error.page}:** ${error.message}`).join('\n')}
` : '*无错误*'}

## 警告汇总

${this.collectAllWarnings(results).length > 0 ? `
${this.collectAllWarnings(results).map(warning => `- **${warning.page}:** ${warning.message}`).join('\n')}
` : '*无警告*'}
`;

    const filePath = join(this.reportDir, 'report.md');
    await writeFile(filePath, markdown, 'utf-8');
    return filePath;
  }

  /**
   * 渲染单个页面的 Markdown
   */
  private renderMarkdownPage(result: PageValidationResult): string {
    const passed = this.isPagePassed(result);
    const status = passed ? '✅ PASSED' : '❌ FAILED';

    let md = `### ${result.pageName} ${status}\n\n`;
    md += `- **路由:** \`${result.route}\`\n`;
    md += `- **模块:** ${this.getModuleName(result.module)}\n`;
    md += `- **加载时间:** ${result.pageLoad.loadTime}ms\n`;
    md += `- **验证时间:** ${result.validatedAt}\n\n`;

    // 操作结果
    md += '#### 操作结果\n\n';
    md += '| 操作 | 状态 | 耗时 |\n';
    md += '|------|------|------|\n';

    const ops = [
      { name: '创建', op: result.operations.create },
      { name: '读取', op: result.operations.read },
      { name: '更新', op: result.operations.update },
      { name: '删除', op: result.operations.delete },
    ];

    for (const { name, op } of ops) {
      if (op) {
        const opStatus = op.success ? '✅ 成功' : '❌ 失败';
        const opTime = `${op.duration}ms`;
        md += `| ${name} | ${opStatus} | ${opTime} |\n`;
      } else {
        md += `| ${name} | ⏭️ 跳过 | - |\n`;
      }
    }

    // 错误
    if (result.errors.length > 0) {
      md += '\n#### 错误\n\n';
      for (const error of result.errors) {
        md += `- ${error}\n`;
      }
    }

    // 警告
    if (result.warnings.length > 0) {
      md += '\n#### 警告\n\n';
      for (const warning of result.warnings) {
        md += `- ${warning}\n`;
      }
    }

    // 截图
    if (result.screenshotPath) {
      md += `\n#### 截图\n\n`;
      md += `![${result.pageName}](${result.screenshotPath})\n`;
    }

    return md;
  }

  /**
   * 生成 JSON 报告
   */
  async generateJsonReport(results: PageValidationResult[], duration = 0): Promise<string> {
    const data: FullReportData = {
      summary: this.generateSummary(results, duration),
      results,
      errors: this.collectAllErrors(results).map(e => `${e.page}: ${e.message}`),
      warnings: this.collectAllWarnings(results).map(w => `${w.page}: ${w.message}`),
    };

    const filePath = join(this.reportDir, 'report.json');
    await writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
    return filePath;
  }

  /**
   * 生成 CSV 报告
   */
  async generateCsvReport(results: PageValidationResult[]): Promise<string> {
    const headers = [
      'Page Name',
      'Route',
      'Module',
      'Status',
      'Load Time (ms)',
      'Create Status',
      'Read Status',
      'Update Status',
      'Delete Status',
      'Errors',
      'Warnings',
    ];

    const rows = results.map(result => [
      result.pageName,
      result.route,
      result.module,
      this.isPagePassed(result) ? 'PASSED' : 'FAILED',
      result.pageLoad.loadTime,
      result.operations.create?.success ? 'PASSED' : result.operations.create ? 'FAILED' : 'SKIPPED',
      result.operations.read?.success ? 'PASSED' : result.operations.read ? 'FAILED' : 'SKIPPED',
      result.operations.update?.success ? 'PASSED' : result.operations.update ? 'FAILED' : 'SKIPPED',
      result.operations.delete?.success ? 'PASSED' : result.operations.delete ? 'FAILED' : 'SKIPPED',
      result.errors.join('; '),
      result.warnings.join('; '),
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    const filePath = join(this.reportDir, 'report.csv');
    await writeFile(filePath, csv, 'utf-8');
    return filePath;
  }

  /**
   * 生成汇总统计
   */
  private generateSummary(results: PageValidationResult[], duration: number): ReportSummary {
    const summary: ReportSummary = {
      generatedAt: new Date().toISOString(),
      duration,
      total: results.length,
      passed: 0,
      failed: 0,
      skipped: 0,
      passRate: 0,
      byModule: {},
      byPageType: {},
    };

    for (const result of results) {
      // 模块统计
      if (!summary.byModule[result.module]) {
        summary.byModule[result.module] = {
          total: 0,
          passed: 0,
          failed: 0,
          passRate: 0,
          avgLoadTime: 0,
        };
      }
      const moduleStats = summary.byModule[result.module];
      moduleStats.total++;
      moduleStats.avgLoadTime += result.pageLoad.loadTime;

      // 判断页面是否通过
      if (this.isPagePassed(result)) {
        summary.passed++;
        moduleStats.passed++;
      } else {
        summary.failed++;
        moduleStats.failed++;
      }
    }

    // 计算通过率和平均加载时间
    summary.passRate = summary.total > 0 ? (summary.passed / summary.total) * 100 : 0;

    for (const module in summary.byModule) {
      const stats = summary.byModule[module];
      stats.passRate = stats.total > 0 ? (stats.passed / stats.total) * 100 : 0;
      stats.avgLoadTime = stats.total > 0 ? Math.round(stats.avgLoadTime / stats.total) : 0;
    }

    return summary;
  }

  /**
   * 判断页面是否通过
   */
  private isPagePassed(result: PageValidationResult): boolean {
    if (!result.pageLoad.success) return false;

    // 检查是否有错误
    if (result.errors.length > 0) return false;

    // 检查配置的操作是否都成功
    const ops = Object.values(result.operations).filter(op => op !== undefined);
    if (ops.length === 0) return true; // 没有配置操作，仅页面加载成功就算通过

    return ops.every(op => op.success);
  }

  /**
   * 收集所有错误
   */
  private collectAllErrors(results: PageValidationResult[]): Array<{ page: string; message: string }> {
    const errors: Array<{ page: string; message: string }> = [];

    for (const result of results) {
      for (const error of result.errors) {
        errors.push({ page: result.pageName, message: error });
      }
    }

    return errors;
  }

  /**
   * 收集所有警告
   */
  private collectAllWarnings(results: PageValidationResult[]): Array<{ page: string; message: string }> {
    const warnings: Array<{ page: string; message: string }> = [];

    for (const result of results) {
      for (const warning of result.warnings) {
        warnings.push({ page: result.pageName, message: warning });
      }
    }

    return warnings;
  }

  /**
   * 获取模块名称
   */
  private getModuleName(module: string): string {
    const names: Record<string, string> = {
      auth: '基础认证',
      data: 'DataOps 数据治理',
      model: 'MLOps 模型管理',
      agent: 'LLMOps Agent 平台',
      workflow: '工作流管理',
      metadata: '元数据管理',
      admin: '管理后台',
      portal: '门户模块',
      common: '通用模块',
    };
    return names[module] || module;
  }
}
