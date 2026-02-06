/**
 * Metadata service API 测试
 * 测试元数据服务 API 客户端
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { metadataApi } from './metadata';
import api from './api';

const mockGet = api.get as ReturnType<typeof vi.fn>;
const mockPost = api.post as ReturnType<typeof vi.fn>;

describe('Metadata Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 基础元数据 API ====================

  describe('Basic Metadata API', () => {
    it('should get tables', () => {
      const params = { page: 1, page_size: 20, keyword: 'sales' };
      metadataApi.getTables(params);

      expect(mockGet).toHaveBeenCalledWith('/data/metadata/tables', { params });
    });

    it('should get tables without params', () => {
      metadataApi.getTables();
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/tables', { params: undefined });
    });

    it('should get table detail', () => {
      const tableId = 'table-123';
      metadataApi.getTableDetail(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}`);
    });

    it('should get table columns', () => {
      const tableId = 'table-123';
      metadataApi.getTableColumns(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}/columns`);
    });

    it('should get table relations', () => {
      const tableId = 'table-123';
      metadataApi.getTableRelations(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}/relations`);
    });
  });

  // ==================== 元数据图谱 API ====================

  describe('Graph Data API', () => {
    it('should get graph data', () => {
      const params = { center_table_id: 'table-123', depth: 2 };
      metadataApi.getGraphData(params);

      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph', { params });
    });

    it('should get graph data without params', () => {
      metadataApi.getGraphData();
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph', { params: undefined });
    });

    it('should get graph statistics', () => {
      metadataApi.getGraphStatistics();
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph/statistics');
    });

    it('should get metadata graph with filters', () => {
      const params = { node_types: 'table,view', center_table_id: 'table-123' };
      metadataApi.getMetadataGraph(params);

      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph', { params });
    });

    it('should get table lineage graph', () => {
      const tableId = 'table-123';
      metadataApi.getTableLineageGraph(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}/lineage/graph`);
    });

    it('should get column relation graph', () => {
      const tableId = 'table-123';
      metadataApi.getColumnRelationGraph(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}/columns/relations`);
    });
  });

  // ==================== 搜索 API ====================

  describe('Search API', () => {
    it('should search tables', () => {
      metadataApi.searchTables('sales');
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/search', { params: { keyword: 'sales' } });
    });

    it('should search metadata nodes', () => {
      const params = { keyword: 'user', node_types: 'table', limit: 10 };
      metadataApi.searchMetadataNodes(params);

      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph/search', { params });
    });
  });

  // ==================== 血缘 API ====================

  describe('Lineage API', () => {
    it('should get lineage', () => {
      const tableId = 'table-123';
      metadataApi.getLineage(tableId);

      expect(mockGet).toHaveBeenCalledWith(`/data/metadata/tables/${tableId}/lineage`);
    });
  });

  // ==================== OpenMetadata 集成 API ====================

  describe('OpenMetadata Integration', () => {
    it('should get OpenMetadata status', () => {
      metadataApi.getOpenMetadataStatus();
      expect(mockGet).toHaveBeenCalledWith('/data/openmetadata/status');
    });

    it('should sync to OpenMetadata', () => {
      const params = { database_name: 'sales_dw', table_names: ['users', 'orders'] };
      metadataApi.syncToOpenMetadata(params);

      expect(mockPost).toHaveBeenCalledWith('/data/openmetadata/sync', params);
    });

    it('should sync to OpenMetadata without params', () => {
      metadataApi.syncToOpenMetadata();
      expect(mockPost).toHaveBeenCalledWith('/data/openmetadata/sync', {});
    });

    it('should get OpenMetadata lineage', () => {
      const params = {
        database: 'sales_dw',
        table: 'users',
        upstream_depth: 2,
        downstream_depth: 1,
      };
      metadataApi.getOpenMetadataLineage(params);

      expect(mockGet).toHaveBeenCalledWith('/data/openmetadata/lineage', { params });
    });

    it('should search OpenMetadata', () => {
      const params = { q: 'users', limit: 10, offset: 0 };
      metadataApi.searchOpenMetadata(params);

      expect(mockGet).toHaveBeenCalledWith('/data/openmetadata/search', { params });
    });

    it('should search OpenMetadata with minimal params', () => {
      const params = { q: 'users' };
      metadataApi.searchOpenMetadata(params);

      expect(mockGet).toHaveBeenCalledWith('/data/openmetadata/search', { params });
    });
  });

  // ==================== 边界情况 ====================

  describe('Edge Cases', () => {
    it('should handle get tables with empty params', () => {
      metadataApi.getTables({});
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/tables', { params: {} });
    });

    it('should handle graph data with only center table', () => {
      const params = { center_table_id: 'table-123' };
      metadataApi.getGraphData(params);
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph', { params });
    });

    it('should handle search nodes with only keyword', () => {
      const params = { keyword: 'test' };
      metadataApi.searchMetadataNodes(params);
      expect(mockGet).toHaveBeenCalledWith('/data/metadata/graph/search', { params });
    });
  });

  // ==================== 默认导出 ====================

  describe('Default Export', () => {
    it('should export metadataApi as default', () => {
      expect(metadataApi).toBeDefined();
      expect(metadataApi.getTables).toBeDefined();
      expect(metadataApi.getTableDetail).toBeDefined();
      expect(metadataApi.getGraphData).toBeDefined();
    });
  });
});
