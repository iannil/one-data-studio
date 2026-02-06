/**
 * Query Hooks 测试
 * 测试 React Query 自定义 Hooks
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    request: vi.fn(),
  },
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    request: vi.fn(),
  },
}));

vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  const queryClient = {
    invalidateQueries: vi.fn(),
  };
  return {
    ...actual,
    useQuery: vi.fn(),
    useMutation: vi.fn(),
    useQueryClient: vi.fn(() => queryClient),
    QueryClient: actual.QueryClient,
  };
});

describe('Query Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 导出检查 ====================

  describe('Exports', () => {
    it('should export useApiQuery', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useApiQuery).toBeDefined();
    });

    it('should export useApiMutation', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useApiMutation).toBeDefined();
    });

    it('should export useApiPost', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useApiPost).toBeDefined();
    });

    it('should export useApiPut', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useApiPut).toBeDefined();
    });

    it('should export useApiDelete', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useApiDelete).toBeDefined();
    });

    it('should export dataset hooks', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useDatasets).toBeDefined();
      expect(hooks.useDataset).toBeDefined();
      expect(hooks.useCreateDataset).toBeDefined();
      expect(hooks.useUpdateDataset).toBeDefined();
      expect(hooks.useDeleteDataset).toBeDefined();
    });

    it('should export workflow hooks', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useWorkflows).toBeDefined();
      expect(hooks.useWorkflow).toBeDefined();
      expect(hooks.useCreateWorkflow).toBeDefined();
      expect(hooks.useUpdateWorkflow).toBeDefined();
      expect(hooks.useDeleteWorkflow).toBeDefined();
    });

    it('should export document hooks', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useDocuments).toBeDefined();
      expect(hooks.useUploadDocument).toBeDefined();
      expect(hooks.useDeleteDocument).toBeDefined();
    });

    it('should export agent template hooks', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useAgentTemplates).toBeDefined();
      expect(hooks.useCreateAgentTemplate).toBeDefined();
      expect(hooks.useUpdateAgentTemplate).toBeDefined();
      expect(hooks.useDeleteAgentTemplate).toBeDefined();
    });

    it('should export model hooks', async () => {
      const hooks = await import('./queryHooks');
      expect(hooks.useModels).toBeDefined();
    });

    it('should export default object with all hooks', async () => {
      const hooks = await import('./queryHooks');
      const defaultExport = hooks.default;

      expect(defaultExport).toBeDefined();
      expect(defaultExport.useDatasets).toBeDefined();
      expect(defaultExport.useWorkflows).toBeDefined();
      expect(defaultExport.useDocuments).toBeDefined();
    });
  });
});
