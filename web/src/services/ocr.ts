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
  structured_data: Record<string, unknown>;
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

export interface EnhancedOCRResult {
  task_id: string;
  structured_data: Record<string, unknown>;
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
  cross_field_validation: {
    valid: boolean;
    errors: Array<{
      rule: string;
      description: string;
      expected: unknown;
      actual: unknown;
    }>;
    warnings: Array<{
      rule: string;
      description: string;
      expected: unknown;
      actual: unknown;
    }>;
  };
  layout_info: {
    signature_regions: Array<{
      label: string;
      page: number;
    }>;
    seal_regions: Array<{
      label: string;
      page: number;
    }>;
    has_signatures: boolean;
    has_seals: boolean;
  };
  completeness: {
    valid: boolean;
    missing_required: Array<{
      key: string;
      name: string;
    }>;
    completeness_rate: number;
  };
}

export interface ExtractionTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  template_type: string;
  category?: string;
  extraction_rules: Record<string, unknown>;
  is_active: boolean;
  is_public: boolean;
  version: number;
  usage_count: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentTypeDetection {
  detected_type: string;
  confidence: number;
  suggested_templates: string[];
  metadata: {
    file_name: string;
    file_size: number;
    page_count: number;
    text_length: number;
  };
}

export interface BatchTaskResult {
  batch_id: string;
  total_files: number;
  tasks: string[];
  status: string;
}

export interface DocumentTypeInfo {
  type: string;
  name: string;
  category: string;
  supported_formats: string[];
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
    corrections: Record<string, unknown>;
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
    extraction_rules: Record<string, unknown>;
    ai_prompt_template?: string;
    post_processing?: Record<string, unknown>;
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
  },

  // ==================== 新增API ====================

  /**
   * 批量创建OCR任务
   */
  createBatchTasks: (
    files: File[],
    params?: {
      extraction_type?: string;
      template_id?: string;
      tenant_id?: string;
      user_id?: string;
    }
  ) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const queryParams = new URLSearchParams();
    if (params?.extraction_type) queryParams.append('extraction_type', params.extraction_type);
    if (params?.template_id) queryParams.append('template_id', params.template_id);
    if (params?.tenant_id) queryParams.append('tenant_id', params.tenant_id);
    if (params?.user_id) queryParams.append('user_id', params.user_id);

    return apiClient.post<BatchTaskResult>(
      `${OCR_BASE_URL}/tasks/batch?${queryParams.toString()}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      }
    );
  },

  /**
   * 自动识别文档类型
   */
  detectDocumentType: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post<DocumentTypeDetection>(
      `${OCR_BASE_URL}/detect-type`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      }
    );
  },

  /**
   * 获取增强的OCR任务结果（包含跨字段校验和布局分析）
   */
  getEnhancedTaskResult: (taskId: string, params?: {
    include_validation?: boolean;
    include_layout?: boolean;
  }) => {
    return apiClient.get<EnhancedOCRResult>(
      `${OCR_BASE_URL}/tasks/${taskId}/result/enhanced`,
      { params }
    );
  },

  /**
   * 使用模板预览提取结果
   */
  previewWithTemplate: (file: File, templateConfig: Record<string, unknown>) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('request', JSON.stringify({ template_config: templateConfig }));

    return apiClient.post<{
      extracted_fields: Record<string, unknown>;
      detected_tables: Array<{
        index: number;
        headers: string[];
        rows: string[][];
        row_count: number;
      }>;
      validation_result: Record<string, unknown>;
      confidence_score: number;
    }>(
      `${OCR_BASE_URL}/templates/preview`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      }
    );
  },

  /**
   * 获取支持的文档类型列表
   */
  getDocumentTypes: () => {
    return apiClient.get<{ document_types: DocumentTypeInfo[] }>(`${OCR_BASE_URL}/templates/types`);
  },

  /**
   * 加载默认模板到数据库
   */
  loadDefaultTemplates: (params?: { tenant_id?: string }) => {
    return apiClient.post<{
      message: string;
      templates: Array<{
        name: string;
        type: string;
        action: string;
      }>;
      count: number;
    }>(`${OCR_BASE_URL}/templates/load-defaults`, undefined, { params });
  }
};
