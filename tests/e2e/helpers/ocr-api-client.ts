/**
 * OCR 服务 API 客户端
 * 封装 OCR 服务 HTTP 调用，处理文件上传和结果轮询
 *
 * 服务地址: http://localhost:8007
 * API 文档: 见 OCR 服务 README
 */

import { readFile } from 'fs/promises';
import { Page } from '@playwright/test';

// ==================== 类型定义 ====================

/**
 * 任务状态枚举
 */
export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

/**
 * OCR 任务响应
 */
export interface OCRTaskResponse {
  id: string;
  document_name: string;
  document_type: string;
  status: TaskStatus;
  progress: number;
  created_at: string;
  result_summary?: Record<string, unknown>;
  error_message?: string;
}

/**
 * 增强的提取结果响应
 */
export interface EnhancedExtractionResult {
  task_id: string;
  structured_data: Record<string, unknown>;
  raw_text?: string;
  tables: TableData[];
  confidence_score: number;
  validation_issues: ValidationIssue[];
  cross_field_validation: Record<string, unknown>;
  layout_info: LayoutInfo;
  completeness: Record<string, unknown>;
}

/**
 * 表格数据
 */
export interface TableData {
  id: string;
  task_id: string;
  table_index: number;
  page_number: number;
  row_count: number;
  col_count: number;
  headers: string[];
  rows: string[][];
  confidence: number;
}

/**
 * 验证问题
 */
export interface ValidationIssue {
  field?: string;
  issue: string;
  severity: 'error' | 'warning' | 'info';
}

/**
 * 布局信息
 */
export interface LayoutInfo {
  signature_regions: unknown[];
  seal_regions: unknown[];
  has_signatures: boolean;
  has_seals: boolean;
}

/**
 * OCR 识别结果
 */
export interface OCRResult {
  taskId: string;
  status: TaskStatus;
  rawText: string;
  structuredData: Record<string, unknown>;
  tables: TableData[];
  confidenceScore: number;
  errorMessage?: string;
}

/**
 * 客户端配置
 */
export interface OCRClientConfig {
  /** 服务基础 URL */
  baseUrl: string;
  /** 请求超时时间（毫秒） */
  timeout: number;
  /** 轮询间隔（毫秒） */
  pollInterval: number;
  /** 最大轮询次数 */
  maxPollAttempts: number;
}

// ==================== 错误类 ====================

/**
 * OCR 客户端错误基类
 */
export class OCRClientError extends Error {
  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = 'OCRClientError';
  }
}

/**
 * 服务不可用错误
 */
export class ServiceUnavailableError extends OCRClientError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'ServiceUnavailableError';
  }
}

/**
 * 任务处理失败错误
 */
export class TaskFailedError extends OCRClientError {
  constructor(
    public readonly taskId: string,
    message: string,
    cause?: Error
  ) {
    super(message, cause);
    this.name = 'TaskFailedError';
  }
}

/**
 * 请求超时错误
 */
export class TimeoutError extends OCRClientError {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

// ==================== HTTP 辅助函数 ====================

/**
 * Node.js fetch 封装，支持超时和错误处理
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit & { timeout?: number } = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }
    throw error;
  }
}

// ==================== OCR 客户端类 ====================

/**
 * OCR 服务客户端（使用 Node.js fetch API）
 *
 * 使用示例:
 * ```typescript
 * const client = new OCRPageClient(page);
 * const result = await client.extractImage('/path/to/screenshot.png');
 * console.log(result.rawText);
 * ```
 */
export class OCRPageClient {
  private config: OCRClientConfig;
  private page: Page;

  constructor(page: Page, config?: Partial<OCRClientConfig>) {
    this.page = page;
    this.config = {
      baseUrl: config?.baseUrl ?? process.env.OCR_SERVICE_URL ?? 'http://localhost:8007',
      timeout: config?.timeout ?? 300000, // 5 分钟
      pollInterval: config?.pollInterval ?? 1000, // 1 秒
      maxPollAttempts: config?.maxPollAttempts ?? 300, // 5 分钟
    };
  }

  /**
   * 获取完整的 API URL
   */
  private getUrl(path: string): string {
    return `${this.config.baseUrl.replace(/\/$/, '')}${path}`;
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetchWithTimeout(this.getUrl('/'), {
        timeout: 5000,
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * 从文件路径读取图片并提取文本
   *
   * @param filePath - 图片文件路径（PNG/JPG等）
   * @param extractionType - 提取类型，默认为 'general'
   * @returns OCR 识别结果
   */
  async extractImage(
    filePath: string,
    extractionType: string = 'general'
  ): Promise<OCRResult> {
    try {
      // 读取文件
      const imageBuffer = await readFile(filePath);

      // 创建任务
      const taskId = await this.createTask(imageBuffer, extractionType);

      // 等待任务完成
      return await this.pollForResult(taskId);
    } catch (error) {
      if (error instanceof OCRClientError) {
        throw error;
      }
      throw new OCRClientError(
        `Failed to extract image: ${error instanceof Error ? error.message : String(error)}`,
        error instanceof Error ? error : undefined
      );
    }
  }

  /**
   * 从 Buffer 提取文本
   *
   * @param buffer - 图片 Buffer
   * @param extractionType - 提取类型
   * @returns OCR 识别结果
   */
  async extractBuffer(
    buffer: Buffer,
    extractionType: string = 'general'
  ): Promise<OCRResult> {
    try {
      const taskId = await this.createTask(buffer, extractionType);
      return await this.pollForResult(taskId);
    } catch (error) {
      if (error instanceof OCRClientError) {
        throw error;
      }
      throw new OCRClientError(
        `Failed to extract buffer: ${error instanceof Error ? error.message : String(error)}`,
        error instanceof Error ? error : undefined
      );
    }
  }

  /**
   * 创建 OCR 任务
   */
  private async createTask(
    buffer: Buffer,
    extractionType: string
  ): Promise<string> {
    // 构建 multipart/form-data
    const formData = new FormData();
    formData.append('file', new Blob([buffer], { type: 'image/png' }), 'screenshot.png');

    // 构建查询参数
    const params = new URLSearchParams({
      extraction_type: extractionType,
      tenant_id: 'e2e-test',
      user_id: 'playwright-test',
    });

    // 发送请求
    const response = await fetchWithTimeout(
      this.getUrl(`/api/v1/ocr/tasks?${params.toString()}`),
      {
        method: 'POST',
        body: formData,
        timeout: this.config.timeout,
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new OCRClientError(
        `Failed to create OCR task: ${response.status} ${errorText}`
      );
    }

    const taskResponse: OCRTaskResponse = await response.json();
    const taskId = taskResponse.id;

    if (!taskId) {
      throw new OCRClientError('No task ID in response');
    }

    return taskId;
  }

  /**
   * 轮询获取任务结果
   */
  private async pollForResult(taskId: string): Promise<OCRResult> {
    let attempts = 0;

    while (attempts < this.config.maxPollAttempts) {
      attempts++;

      try {
        const response = await fetchWithTimeout(
          this.getUrl(`/api/v1/ocr/tasks/${taskId}/result/enhanced`)
        );

        if (response.status === 400) {
          // 任务尚未完成，继续等待
          await this.delay(this.config.pollInterval);
          continue;
        }

        if (response.status === 404) {
          throw new OCRClientError(`Task not found: ${taskId}`);
        }

        if (!response.ok) {
          throw new OCRClientError(
            `Failed to get result: ${response.status}`
          );
        }

        const result: EnhancedExtractionResult = await response.json();

        return {
          taskId: result.task_id,
          status: TaskStatus.COMPLETED,
          rawText: result.raw_text ?? '',
          structuredData: result.structured_data,
          tables: result.tables,
          confidenceScore: result.confidence_score,
        };
      } catch (error) {
        if (error instanceof OCRClientError) {
          throw error;
        }
        // 其他错误，继续重试
        await this.delay(this.config.pollInterval);
      }
    }

    throw new TimeoutError(
      `Timeout waiting for OCR task ${taskId} after ${attempts} attempts`
    );
  }

  /**
   * 获取任务状态
   */
  async getTaskStatus(taskId: string): Promise<OCRTaskResponse> {
    const response = await fetchWithTimeout(
      this.getUrl(`/api/v1/ocr/tasks/${taskId}`)
    );

    if (!response.ok) {
      throw new OCRClientError(`Failed to get task status: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: string): Promise<boolean> {
    const response = await fetchWithTimeout(
      this.getUrl(`/api/v1/ocr/tasks/${taskId}`),
      {
        method: 'DELETE',
      }
    );
    return response.ok;
  }

  /**
   * 延迟指定毫秒
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 批量提取图片
   *
   * @param filePaths - 文件路径数组
   * @param extractionType - 提取类型
   * @returns OCR 识别结果数组
   */
  async extractBatch(
    filePaths: string[],
    extractionType: string = 'general'
  ): Promise<OCRResult[]> {
    const results: OCRResult[] = [];

    for (const filePath of filePaths) {
      try {
        const result = await this.extractImage(filePath, extractionType);
        results.push(result);
      } catch (error) {
        // 添加失败结果
        results.push({
          taskId: '',
          status: TaskStatus.FAILED,
          rawText: '',
          structuredData: {},
          tables: [],
          confidenceScore: 0,
          errorMessage: error instanceof Error ? error.message : String(error),
        });
      }
    }

    return results;
  }
}

// ==================== 便捷函数 ====================

/**
 * 创建 OCR 客户端实例
 */
export function getPageClient(page: Page, config?: Partial<OCRClientConfig>): OCRPageClient {
  return new OCRPageClient(page, config);
}

/**
 * 等待 OCR 服务就绪
 *
 * @param page - Playwright Page 对象
 * @param maxAttempts - 最大尝试次数
 * @param interval - 检查间隔（毫秒）
 */
export async function waitForOCRService(
  page: Page,
  maxAttempts: number = 30,
  interval: number = 2000
): Promise<boolean> {
  const client = getPageClient(page);

  for (let i = 0; i < maxAttempts; i++) {
    if (await client.healthCheck()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  return false;
}

/**
 * 提取图片文本的便捷函数
 *
 * @param page - Playwright Page 对象
 * @param filePath - 图片文件路径
 * @param extractionType - 提取类型
 * @returns OCR 识别结果
 */
export async function extractImage(
  page: Page,
  filePath: string,
  extractionType: string = 'general'
): Promise<OCRResult> {
  const client = getPageClient(page);
  return await client.extractImage(filePath, extractionType);
}
