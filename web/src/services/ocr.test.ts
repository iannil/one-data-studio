/**
 * OCR service API 测试
 * 测试 OCR 服务 API 客户端
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { ocrApi } from './ocr';
import { apiClient } from './api';

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;
const mockPut = apiClient.put as ReturnType<typeof vi.fn>;
const mockDelete = apiClient.delete as ReturnType<typeof vi.fn>;

describe('OCR Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== OCR 任务管理 ====================

  describe('OCR Task Management', () => {
    it('should create OCR task', () => {
      const formData = new FormData();
      formData.append('file', new Blob(['test'], { type: 'application/pdf' }), 'test.pdf');

      const params = {
        extraction_type: 'invoice',
        template_id: 'template-123',
        tenant_id: 'tenant-123',
        user_id: 'user-123',
      };

      ocrApi.createTask(formData, params);

      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/ocr/tasks?'),
        formData,
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })
      );
    });

    it('should create OCR task with minimal params', () => {
      const formData = new FormData();
      formData.append('file', new Blob(['test']));

      ocrApi.createTask(formData);

      expect(mockPost).toHaveBeenCalled();
    });

    it('should get OCR tasks', () => {
      const params = { status: 'completed', page: 1, page_size: 20 };
      ocrApi.getTasks(params);

      expect(mockGet).toHaveBeenCalledWith('/api/v1/ocr/tasks', { params });
    });

    it('should get OCR task by id', () => {
      const taskId = 'task-123';
      ocrApi.getTask(taskId);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}`);
    });

    it('should get OCR task result', () => {
      const taskId = 'task-123';
      ocrApi.getTaskResult(taskId);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}/result`);
    });

    it('should verify OCR task', () => {
      const taskId = 'task-123';
      const data = {
        corrections: { field1: 'corrected value' },
        verified_by: 'user-123',
      };
      ocrApi.verifyTask(taskId, data);

      expect(mockPost).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}/verify`, data);
    });

    it('should delete OCR task', () => {
      const taskId = 'task-123';
      ocrApi.deleteTask(taskId);

      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}`);
    });

    it('should get enhanced task result', () => {
      const taskId = 'task-123';
      const params = { include_validation: true, include_layout: true };
      ocrApi.getEnhancedTaskResult(taskId, params);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}/result/enhanced`, {
        params,
      });
    });
  });

  // ==================== 批量任务 ====================

  describe('Batch Tasks', () => {
    it('should create batch tasks', () => {
      const files = [new File(['test1'], 'test1.pdf'), new File(['test2'], 'test2.pdf')];
      const params = { extraction_type: 'invoice' };

      ocrApi.createBatchTasks(files, params);

      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/ocr/tasks/batch?'),
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 120000,
        })
      );
    });
  });

  // ==================== 文档类型检测 ====================

  describe('Document Type Detection', () => {
    it('should detect document type', () => {
      const file = new File(['test'], 'test.pdf');

      ocrApi.detectDocumentType(file);

      expect(mockPost).toHaveBeenCalledWith(
        '/api/v1/ocr/detect-type',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })
      );
    });
  });

  // ==================== 模板管理 ====================

  describe('Template Management', () => {
    it('should create template', () => {
      const templateData = {
        name: 'Invoice Template',
        description: 'Standard invoice extraction template',
        template_type: 'invoice',
        category: 'finance',
        extraction_rules: { fields: ['amount', 'date', 'vendor'] },
      };

      ocrApi.createTemplate(templateData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/ocr/templates', templateData);
    });

    it('should get templates', () => {
      const params = { template_type: 'invoice', is_active: true };
      ocrApi.getTemplates(params);

      expect(mockGet).toHaveBeenCalledWith('/api/v1/ocr/templates', { params });
    });

    it('should get template by id', () => {
      const templateId = 'template-123';
      ocrApi.getTemplate(templateId);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/templates/${templateId}`);
    });

    it('should update template', () => {
      const templateId = 'template-123';
      const updateData = { name: 'Updated Template' };

      ocrApi.updateTemplate(templateId, updateData);

      expect(mockPut).toHaveBeenCalledWith(`/api/v1/ocr/templates/${templateId}`, updateData);
    });

    it('should delete template', () => {
      const templateId = 'template-123';
      ocrApi.deleteTemplate(templateId);

      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/ocr/templates/${templateId}`);
    });

    it('should preview template', () => {
      const templateId = 'template-123';
      ocrApi.previewTemplate(templateId);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/templates/${templateId}/preview`);
    });

    it('should preview with template', () => {
      const file = new File(['test'], 'test.pdf');
      const templateConfig = { fields: ['amount', 'date'] };

      ocrApi.previewWithTemplate(file, templateConfig);

      expect(mockPost).toHaveBeenCalledWith(
        '/api/v1/ocr/templates/preview',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })
      );
    });

    it('should get document types', () => {
      ocrApi.getDocumentTypes();

      expect(mockGet).toHaveBeenCalledWith('/api/v1/ocr/templates/types');
    });

    it('should load default templates', () => {
      const params = { tenant_id: 'tenant-123' };
      ocrApi.loadDefaultTemplates(params);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/ocr/templates/load-defaults', undefined, {
        params,
      });
    });
  });

  // ==================== 边界情况 ====================

  describe('Edge Cases', () => {
    it('should handle create task without optional params', () => {
      const formData = new FormData();
      formData.append('file', new Blob(['test']));

      ocrApi.createTask(formData);

      expect(mockPost).toHaveBeenCalled();
    });

    it('should handle get tasks without filters', () => {
      ocrApi.getTasks();

      expect(mockGet).toHaveBeenCalledWith('/api/v1/ocr/tasks', { params: undefined });
    });

    it('should handle verify with only status', () => {
      const taskId = 'task-123';
      ocrApi.verifyTask(taskId, { verified_by: 'user-123' });

      expect(mockPost).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}/verify`, {
        corrections: undefined,
        verified_by: 'user-123',
      });
    });

    it('should handle get enhanced result without params', () => {
      const taskId = 'task-123';
      ocrApi.getEnhancedTaskResult(taskId);

      expect(mockGet).toHaveBeenCalledWith(`/api/v1/ocr/tasks/${taskId}/result/enhanced`, {
        params: undefined,
      });
    });

    it('should handle create batch tasks without params', () => {
      const files = [new File(['test'], 'test.pdf')];

      ocrApi.createBatchTasks(files);

      expect(mockPost).toHaveBeenCalled();
    });

    it('should handle update template with partial data', () => {
      const templateId = 'template-123';
      ocrApi.updateTemplate(templateId, { is_active: false });

      expect(mockPut).toHaveBeenCalledWith(`/api/v1/ocr/templates/${templateId}`, {
        is_active: false,
      });
    });
  });
});
