/**
 * 元数据服务 API
 */

import api from './api';

export interface MetadataTable {
  table_id: string;
  table_name: string;
  schema_name?: string;
  description?: string;
  table_type: string;
  row_count?: number;
  column_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface MetadataColumn {
  column_id: string;
  column_name: string;
  table_id: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  description?: string;
}

export interface MetadataRelation {
  relation_id: string;
  source_table_id: string;
  source_column_id: string;
  target_table_id: string;
  target_column_id: string;
  relation_type: 'one_to_one' | 'one_to_many' | 'many_to_many';
}

export interface MetadataGraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    data: unknown;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    data: unknown;
  }>;
}

/**
 * 元数据 API
 */
export const metadataApi = {
  /**
   * 获取元数据表列表
   */
  getTables: async (params?: { page?: number; page_size?: number; keyword?: string }) => {
    return api.get('/data/metadata/tables', { params });
  },

  /**
   * 获取表详情
   */
  getTableDetail: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}`);
  },

  /**
   * 获取表的列信息
   */
  getTableColumns: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}/columns`);
  },

  /**
   * 获取表的关系
   */
  getTableRelations: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}/relations`);
  },

  /**
   * 获取元数据图谱数据
   */
  getGraphData: async (params?: { center_table_id?: string; depth?: number }) => {
    return api.get('/data/metadata/graph', { params });
  },

  /**
   * 搜索表
   */
  searchTables: async (keyword: string) => {
    return api.get('/data/metadata/search', { params: { keyword } });
  },

  /**
   * 获取数据血缘
   */
  getLineage: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}/lineage`);
  },

  /**
   * 获取 OpenMetadata 集成状态
   */
  getOpenMetadataStatus: async () => {
    return api.get('/data/openmetadata/status');
  },

  /**
   * 触发 OpenMetadata 元数据同步
   */
  syncToOpenMetadata: async (params?: { database_name?: string; table_names?: string[] }) => {
    return api.post('/data/openmetadata/sync', params || {});
  },

  /**
   * 通过 OpenMetadata 获取增强血缘
   */
  getOpenMetadataLineage: async (params: {
    database: string;
    table: string;
    upstream_depth?: number;
    downstream_depth?: number;
  }) => {
    return api.get('/data/openmetadata/lineage', { params });
  },

  /**
   * 通过 OpenMetadata 搜索元数据
   */
  searchOpenMetadata: async (params: { q: string; limit?: number; offset?: number }) => {
    return api.get('/data/openmetadata/search', { params });
  },

  /**
   * 获取元数据图谱 (带节点类型过滤)
   */
  getMetadataGraph: async (params?: { node_types?: string; center_table_id?: string; depth?: number }) => {
    return api.get('/data/metadata/graph', { params });
  },

  /**
   * 获取图谱统计信息
   */
  getGraphStatistics: async () => {
    return api.get('/data/metadata/graph/statistics');
  },

  /**
   * 获取表的血缘图谱
   */
  getTableLineageGraph: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}/lineage/graph`);
  },

  /**
   * 获取列关系图
   */
  getColumnRelationGraph: async (tableId: string) => {
    return api.get(`/data/metadata/tables/${tableId}/columns/relations`);
  },

  /**
   * 搜索元数据节点
   */
  searchMetadataNodes: async (params: { keyword: string; node_types?: string; limit?: number }) => {
    return api.get('/data/metadata/graph/search', { params });
  },
};

export default metadataApi;
