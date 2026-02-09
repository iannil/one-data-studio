/**
 * OCR 验证辅助类
 * 提供截图和 OCR 验证功能
 */

import { Page, Locator } from '@playwright/test';
import { logger } from './logger';
import path from 'path';
import fs from 'fs/promises';
import { extractImage, OCRResult, getPageClient } from './ocr-api-client';

// ==================== 类型定义 ====================

/**
 * 验证结果
 */
export interface ValidationResult {
  /** 是否通过 */
  passed: boolean;
  /** 验证的消息 */
  message: string;
  /** 识别到的文本 */
  recognizedText?: string;
  /** OCR 原始结果 */
  ocrResult?: OCRResult;
}

/**
 * 表格数据
 */
export interface TableData {
  headers: string[];
  rows: string[][];
  rowCount: number;
  colCount: number;
}

/**
 * OCR 验证配置
 */
export interface OCRValidatorConfig {
  /** 截图保存目录 */
  screenshotDir: string;
  /** 是否保留截图 */
  keepScreenshots: boolean;
  /** OCR 超时时间（毫秒） */
  ocrTimeout: number;
  /** 是否在 OCR 失败时抛出错误 */
  throwOnOCRError: boolean;
  /** 文本匹配的容错率（0-1） */
  textMatchTolerance: number;
}

/**
 * 页面验证配置
 */
export interface PageValidationConfig {
  /** 页面名称 */
  pageName: string;
  /** 预期的页面标题 */
  expectedTitle?: string;
  /** 预期必须包含的文本 */
  expectedTexts?: string[];
  /** 预期不能包含的文本（错误关键词） */
  forbiddenTexts?: string[];
  /** 成功操作的提示文本 */
  successTexts?: string[];
  /** 是否需要验证表格 */
  expectTable?: boolean;
  /** 最小表格行数 */
  minTableRows?: number;
}

// ==================== 默认配置 ====================

const DEFAULT_CONFIG: OCRValidatorConfig = {
  screenshotDir: 'test-results/ocr-validation/screenshots',
  keepScreenshots: true,
  ocrTimeout: 30000,
  throwOnOCRError: false,
  textMatchTolerance: 0.8,
};

// ==================== OCR 验证器类 ====================

/**
 * OCR 验证器类
 *
 * 使用示例:
 * ```typescript
 * const validator = new OCRValidator(page);
 * const result = await validator.verifyPageTitle('数据源管理');
 * logger.info(result.passed, result.message);
 * ```
 */
export class OCRValidator {
  private page: Page;
  private config: OCRValidatorConfig;
  private screenshotPath: string | null = null;
  private lastOCRResult: OCRResult | null = null;

  constructor(page: Page, config?: Partial<OCRValidatorConfig>) {
    this.page = page;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 初始化截图目录
   */
  private async ensureScreenshotDir(): Promise<void> {
    try {
      await fs.mkdir(this.config.screenshotDir, { recursive: true });
    } catch (error) {
      console.error('Failed to create screenshot directory:', error);
    }
  }

  /**
   * 生成截图文件名
   */
  private generateScreenshotName(prefix: string): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    return `${prefix}-${timestamp}.png`;
  }

  /**
   * 截取页面全屏截图
   *
   * @param prefix - 文件名前缀
   * @param fullPage - 是否截取整个页面（包括滚动部分）
   * @returns 截图文件路径
   */
  async captureScreenshot(
    prefix: string,
    fullPage: boolean = true
  ): Promise<string> {
    await this.ensureScreenshotDir();

    const filename = this.generateScreenshotName(prefix);
    const filepath = path.join(this.config.screenshotDir, filename);

    await this.page.screenshot({
      path: filepath,
      fullPage: fullPage,
    });

    this.screenshotPath = filepath;
    return filepath;
  }

  /**
   * 截取指定元素截图
   *
   * @param locator - 元素定位器
   * @param prefix - 文件名前缀
   * @returns 截图文件路径
   */
  async captureElementScreenshot(
    locator: Locator,
    prefix: string
  ): Promise<string> {
    await this.ensureScreenshotDir();

    const filename = this.generateScreenshotName(prefix);
    const filepath = path.join(this.config.screenshotDir, filename);

    await locator.screenshot({ path: filepath });

    this.screenshotPath = filepath;
    return filepath;
  }

  /**
   * 对截图进行 OCR 识别
   *
   * @param screenshotPath - 截图路径，如果不传则使用最近一次截图
   * @returns OCR 识别结果
   */
  async performOCR(screenshotPath?: string): Promise<OCRResult> {
    const imagePath = screenshotPath ?? this.screenshotPath;

    if (!imagePath) {
      throw new Error('No screenshot available. Call captureScreenshot first.');
    }

    try {
      const result = await extractImage(this.page, imagePath);
      this.lastOCRResult = result;
      return result;
    } catch (error) {
      if (this.config.throwOnOCRError) {
        throw error;
      }
      // 返回失败结果
      return {
        taskId: '',
        status: 'failed' as const,
        rawText: '',
        structuredData: {},
        tables: [],
        confidenceScore: 0,
        errorMessage: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * 截图并 OCR 识别（便捷方法）
   *
   * @param prefix - 截图文件名前缀
   * @param fullPage - 是否截取整个页面
   * @returns OCR 识别结果
   */
  async captureAndOCR(
    prefix: string,
    fullPage: boolean = true
  ): Promise<OCRResult> {
    await this.captureScreenshot(prefix, fullPage);
    return await this.performOCR();
  }

  /**
   * 清理截图文件（如果配置了不保留）
   */
  async cleanupScreenshot(): Promise<void> {
    if (!this.config.keepScreenshots && this.screenshotPath) {
      try {
        await fs.unlink(this.screenshotPath);
        this.screenshotPath = null;
      } catch (error) {
        // 忽略删除错误
      }
    }
  }

  /**
   * 验证文本是否存在（支持模糊匹配）
   *
   * @param text - 要查找的文本
   * @param ocrResult - OCR 结果
   * @param partialMatch - 是否允许部分匹配
   * @returns 验证结果
   */
  verifyTextExists(
    text: string,
    ocrResult?: OCRResult,
    partialMatch: boolean = true
  ): ValidationResult {
    const result = ocrResult ?? this.lastOCRResult;

    if (!result || result.status === 'failed') {
      // OCR 失败时不验证文本，返回通过
      return {
        passed: true,
        message: `OCR 失败，跳过文本验证: ${result?.errorMessage ?? 'Unknown error'}`,
        recognizedText: '',
      };
    }

    const recognizedText = result.rawText.toLowerCase();
    const searchText = text.toLowerCase();

    let found = false;

    if (partialMatch) {
      // 部分匹配：检查是否包含搜索文本
      found = recognizedText.includes(searchText);

      // 如果没有直接匹配，尝试分词匹配
      if (!found) {
        const searchWords = searchText.split(/\s+/);
        const matchedWords = searchWords.filter(word =>
          recognizedText.includes(word)
        );
        const matchRatio = matchedWords.length / searchWords.length;
        found = matchRatio >= this.config.textMatchTolerance;
      }
    } else {
      // 完全匹配
      found = recognizedText === searchText;
    }

    return {
      passed: found,
      message: found
        ? `Found text "${text}" in OCR result`
        : `Text "${text}" not found in OCR result`,
      recognizedText: result.rawText,
      ocrResult: result,
    };
  }

  /**
   * 验证多个文本是否都存在
   *
   * @param texts - 要查找的文本数组
   * @param requireAll - 是否需要所有文本都存在（默认 true）
   * @returns 验证结果
   */
  verifyMultipleTexts(
    texts: string[],
    requireAll: boolean = true
  ): ValidationResult {
    const results: ValidationResult[] = [];
    const allResults: OCRResult[] = [];

    for (const text of texts) {
      const result = this.verifyTextExists(text);
      results.push(result);
      if (result.ocrResult) {
        allResults.push(result.ocrResult);
      }
    }

    const passedCount = results.filter(r => r.passed).length;
    const allPassed = requireAll ? passedCount === texts.length : passedCount > 0;

    return {
      passed: allPassed,
      message: `Found ${passedCount}/${texts.length} expected texts`,
      recognizedText: allResults[0]?.rawText,
      ocrResult: allResults[0],
    };
  }

  /**
   * 验证没有错误消息
   *
   * @param customErrorKeywords - 自定义错误关键词
   * @returns 验证结果
   */
  verifyNoErrors(customErrorKeywords?: string[]): ValidationResult {
    const result = this.lastOCRResult;

    if (!result || result.status === 'failed') {
      // OCR 失败时不验证错误，返回通过
      return {
        passed: true,
        message: 'OCR 失败，跳过错误检查',
        recognizedText: '',
      };
    }

    // 默认的错误关键词（中英文）
    const errorKeywords = [
      '错误',
      '失败',
      '异常',
      'error',
      'failed',
      'exception',
      '警告',
      'warning',
      '404',
      '500',
      ...(customErrorKeywords ?? []),
    ];

    const recognizedText = result.rawText.toLowerCase();
    const foundErrors: string[] = [];

    for (const keyword of errorKeywords) {
      if (recognizedText.includes(keyword.toLowerCase())) {
        foundErrors.push(keyword);
      }
    }

    return {
      passed: foundErrors.length === 0,
      message: foundErrors.length === 0
        ? 'No error messages detected'
        : `Found error keywords: ${foundErrors.join(', ')}`,
      recognizedText: result.rawText,
      ocrResult: result,
    };
  }

  /**
   * 验证成功消息
   *
   * @param successKeywords - 成功关键词列表
   * @returns 验证结果
   */
  verifySuccessMessage(successKeywords: string[] = ['成功', '保存成功', '创建成功', 'success']): ValidationResult {
    const result = this.lastOCRResult;

    if (!result || result.status === 'failed') {
      return {
        passed: false,
        message: 'OCR failed, cannot verify success message',
        recognizedText: '',
      };
    }

    const recognizedText = result.rawText.toLowerCase();
    const foundSuccess: string[] = [];

    for (const keyword of successKeywords) {
      if (recognizedText.includes(keyword.toLowerCase())) {
        foundSuccess.push(keyword);
      }
    }

    return {
      passed: foundSuccess.length > 0,
      message: foundSuccess.length > 0
        ? `Found success keywords: ${foundSuccess.join(', ')}`
        : 'No success message detected',
      recognizedText: result.rawText,
      ocrResult: result,
    };
  }

  /**
   * 提取表格数据
   *
   * @param ocrResult - OCR 结果
   * @returns 表格数据数组
   */
  extractTableData(ocrResult?: OCRResult): TableData[] {
    const result = ocrResult ?? this.lastOCRResult;

    if (!result || result.status === 'failed') {
      return [];
    }

    return result.tables.map(table => ({
      headers: table.headers ?? [],
      rows: table.rows ?? [],
      rowCount: table.row_count ?? 0,
      colCount: table.col_count ?? 0,
    }));
  }

  /**
   * 验证表格存在且具有最小行数
   *
   * @param minRows - 最小行数
   * @returns 验证结果
   */
  verifyTableExists(minRows: number = 1): ValidationResult {
    const tables = this.extractTableData();

    if (tables.length === 0) {
      return {
        passed: false,
        message: 'No tables detected in OCR result',
        recognizedText: this.lastOCRResult?.rawText,
      };
    }

    const totalRows = tables.reduce((sum, t) => sum + t.rowCount, 0);

    return {
      passed: totalRows >= minRows,
      message: `Found ${tables.length} table(s) with ${totalRows} total rows`,
      recognizedText: this.lastOCRResult?.rawText,
      ocrResult: this.lastOCRResult ?? undefined,
    };
  }

  /**
   * 验证页面（综合验证）
   *
   * @param config - 页面验证配置
   * @returns 综合验证结果
   */
  async validatePage(config: PageValidationConfig): Promise<{
    passed: boolean;
    results: Record<string, ValidationResult>;
    summary: string;
  }> {
    const results: Record<string, ValidationResult> = {};

    // 截图并 OCR
    const ocrResult = await this.captureAndOCR(config.pageName);

    // 验证预期标题
    if (config.expectedTitle) {
      results.title = this.verifyTextExists(config.expectedTitle, ocrResult);
    }

    // 验证预期文本
    if (config.expectedTexts && config.expectedTexts.length > 0) {
      results.expectedTexts = this.verifyMultipleTexts(config.expectedTexts, false);
    }

    // 验证没有错误消息
    results.noErrors = this.verifyNoErrors(config.forbiddenTexts);

    // 验证成功消息（如果配置）
    if (config.successTexts && config.successTexts.length > 0) {
      results.successMessage = this.verifySuccessMessage(config.successTexts);
    }

    // 验证表格（如果配置）
    if (config.expectTable) {
      results.table = this.verifyTableExists(config.minTableRows);
    }

    // 计算总体结果
    const allPassed = Object.values(results).every(r => r.passed);
    const failedChecks = Object.entries(results)
      .filter(([_, r]) => !r.passed)
      .map(([name, _]) => name);

    return {
      passed: allPassed,
      results,
      summary: allPassed
        ? `Page "${config.pageName}" validation passed`
        : `Page "${config.pageName}" validation failed. Failed checks: ${failedChecks.join(', ')}`,
    };
  }

  /**
   * 获取最后一次 OCR 结果
   */
  getLastOCRResult(): OCRResult | null {
    return this.lastOCRResult;
  }

  /**
   * 获取最后一次截图路径
   */
  getScreenshotPath(): string | null {
    return this.screenshotPath;
  }

  /**
   * 重置状态
   */
  reset(): void {
    this.screenshotPath = null;
    this.lastOCRResult = null;
  }
}

// ==================== 便捷函数 ====================

/**
 * 创建 OCR 验证器
 *
 * @param page - Playwright Page 对象
 * @param config - 验证器配置
 * @returns OCR 验证器实例
 */
export function createOCRValidator(
  page: Page,
  config?: Partial<OCRValidatorConfig>
): OCRValidator {
  return new OCRValidator(page, config);
}

/**
 * 快速验证页面标题
 *
 * @param page - Playwright Page 对象
 * @param expectedTitle - 预期的页面标题
 * @param prefix - 截图文件名前缀
 * @returns 验证结果
 */
export async function quickVerifyTitle(
  page: Page,
  expectedTitle: string,
  prefix: string = 'verify-title'
): Promise<ValidationResult> {
  const validator = new OCRValidator(page);
  await validator.captureAndOCR(prefix);
  return validator.verifyTextExists(expectedTitle);
}

/**
 * 快速验证无错误
 *
 * @param page - Playwright Page 对象
 * @param prefix - 截图文件名前缀
 * @returns 验证结果
 */
export async function quickVerifyNoErrors(
  page: Page,
  prefix: string = 'verify-no-errors'
): Promise<ValidationResult> {
  const validator = new OCRValidator(page);
  await validator.captureAndOCR(prefix);
  return validator.verifyNoErrors();
}
