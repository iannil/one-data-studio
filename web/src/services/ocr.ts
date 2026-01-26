/**
 * OCR服务API客户端
 */

import { apiClient } from './api';
import type { ApiResponse } from './api';

export interface OCRTask {
  id: string;
  tenant_id: string;
  user_id: string;
  document_name: string;
  document_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  result_summary?: {
    pages_processed: number;
    tables_found: number;
    text_length: number;
    fields_extracted: number;
    validation_issues: number;
  };
  error_message?: string;
}

export interface OCRResult {
  task_id: string;
  structured_data: Record<string, any>;
  raw_text?: string;
  tables: Array<{
    id: string;
    table_index: number;
    page_number: number;
    headers: string[];
    rows: string[][];
    confidence: number;
  }>;
  confidence_score: number;
  validation_issues: Array<{
    field: string;
    error: string;
    severity: 'error' | 'warning';
  }>;
}

export interface ExtractionTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  template_type: string;
  category?: string;
  extraction_rules: Record<string, any>;
  is_active: boolean;
  is_public: boolean;
  version: number;
  usage_count: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

const OCR_BASE_URL = process.env.REACT_APP_OCR_API_URL || '/api/v1/ocr';

export const ocrApi = {
  /**
   * 创建OCR任务
   */
  createTask: (
    file: FormData,
    params?: {
      extraction_type?: string;
      template_id?: string;
      tenant_id?: string;
      user_id?: string;
    }
  ) => {
    const queryParams = new URLSearchParams();
    if (params?.extraction_type) queryParams.append('extraction_type', params.extraction_type);
    if (params?.template_id) queryParams.append('template_id', params.template_id);
    if (params?.tenant_id) queryParams.append('tenant_id', params.tenant_id);
    if (params?.user_id) queryParams.append('user_id', params.user_id);

    return apiClient.post<OCRTask>(
      `${OCR_BASE_URL}/tasks?${queryParams.toString()}`,
      file,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 60000 // 上传超时时间
      }
    );
  },

  /**
   * 获取OCR任务列表
   */
  getTasks: (params?: {
    status?: string;
    extraction_type?: string;
    page?: number;
    page_size?: number;
  }) => {
    return apiClient.get<{
      total: number;
      tasks: OCRTask[];
    }>(`${OCR_BASE_URL}/tasks`, { params });
  },

  /**
   * 获取OCR任务详情
   */
  getTask: (taskId: string) => {
    return apiClient.get<OCRTask>(`${OCR_BASE_URL}/tasks/${taskId}`);
  },

  /**
   * 获取OCR任务结果
   */
  getTaskResult: (taskId: string) => {
    return apiClient.get<OCRResult>(`${OCR_BASE_URL}/tasks/${taskId}/result`);
  },

  /**
   * 验证和校正OCR结果
   */
  verifyTask: (taskId: string, data: {
    corrections: Record<string, any>;
    verified_by: string;
  }) => {
    return apiClient.post(`${OCR_BASE_URL}/tasks/${taskId}/verify`, data);
  },

  /**
   * 删除OCR任务
   */
  deleteTask: (taskId: string) => {
    return apiClient.delete(`${OCR_BASE_URL}/tasks/${taskId}`);
  },

  // ==================== 模板管理 ====================

  /**
   * 创建提取模板
   */
  createTemplate: (data: {
    name: string;
    description?: string;
    template_type: string;
    category?: string;
    extraction_rules: Record<string, any>;
    ai_prompt_template?: string;
    post_processing?: Record<string, any>;
  }) => {
    return apiClient.post<ExtractionTemplate>(`${OCR_BASE_URL}/templates`, data);
  },

  /**
   * 获取模板列表
   */
  getTemplates: (params?: {
    template_type?: string;
    category?: string;
    is_active?: boolean;
    include_public?: boolean;
  }) => {
    return apiClient.get<ExtractionTemplate[]>(`${OCR_BASE_URL}/templates`, { params });
  },

  /**
   * 获取模板详情
   */
  getTemplate: (templateId: string) => {
    return apiClient.get<ExtractionTemplate>(`${OCR_BASE_URL}/templates/${templateId}`);
  },

  /**
   * 更新模板
   */
  updateTemplate: (templateId: string, data: Partial<ExtractionTemplate>) => {
    return apiClient.put<ExtractionTemplate>(`${OCR_BASE_URL}/templates/${templateId}`, data);
  },

  /**
   * 删除模板
   */
  deleteTemplate: (templateId: string) => {
    return apiClient.delete(`${OCR_BASE_URL}/templates/${templateId}`);
  },

  /**
   * 预览模板配置
   */
  previewTemplate: (templateId: string) => {
    return apiClient.get(`${OCR_BASE_URL}/templates/${templateId}/preview`);
  }
};
