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
    data: any;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    data: any;
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
    return api.get('/alldata/metadata/tables', { params });
  },

  /**
   * 获取表详情
   */
  getTableDetail: async (tableId: string) => {
    return api.get(`/alldata/metadata/tables/${tableId}`);
  },

  /**
   * 获取表的列信息
   */
  getTableColumns: async (tableId: string) => {
    return api.get(`/alldata/metadata/tables/${tableId}/columns`);
  },

  /**
   * 获取表的关系
   */
  getTableRelations: async (tableId: string) => {
    return api.get(`/alldata/metadata/tables/${tableId}/relations`);
  },

  /**
   * 获取元数据图谱数据
   */
  getGraphData: async (params?: { center_table_id?: string; depth?: number }) => {
    return api.get('/alldata/metadata/graph', { params });
  },

  /**
   * 搜索表
   */
  searchTables: async (keyword: string) => {
    return api.get('/alldata/metadata/search', { params: { keyword } });
  },

  /**
   * 获取数据血缘
   */
  getLineage: async (tableId: string) => {
    return api.get(`/alldata/metadata/tables/${tableId}/lineage`);
  },
};

export default metadataApi;
