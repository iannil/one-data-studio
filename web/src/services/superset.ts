/**
 * Superset API 服务
 */

import request from '@/utils/request';

export interface GuestTokenRequest {
  resources: Array<{
    type: string;
    id: string;
  }>;
  user?: {
    username: string;
    first_name: string;
    last_name: string;
  };
  rls?: Array<{
    dataset: number;
    clause: string;
  }>;
}

export interface GuestTokenResponse {
  token: string;
}

export interface SupersetDashboard {
  id: number;
  dashboard_title: string;
  description: string;
  modified: string;
  url: string;
}

export interface SupersetChart {
  id: number;
  slice_name: string;
  viz_type: string;
  datasource_id: number;
  datasource_name: string;
}

export const supersetApi = {
  /**
   * 健康检查
   */
  getHealth: () =>
    request.get<{ status: string; url: string }>('/api/v1/superset/health'),

  /**
   * 创建 Guest Token
   */
  createGuestToken: (data: GuestTokenRequest) =>
    request.post<{ data: GuestTokenResponse; code: number; msg: string }>(
      '/api/v1/superset/guest-token',
      data
    ),

  /**
   * 列出仪表板
   */
  listDashboards: () =>
    request.get<{ data: { dashboards: SupersetDashboard[]; total: number }; code: number; msg: string }>(
      '/api/v1/superset/dashboards'
    ),

  /**
   * 列出图表
   */
  listCharts: (datasetId?: number) =>
    request.get<{ data: { charts: SupersetChart[]; total: number }; code: number; msg: string }>(
      '/api/v1/superset/charts',
      { params: { dataset_id: datasetId } }
    ),

  /**
   * 同步仪表板到 Superset
   */
  syncDashboard: (data: {
    dashboard_id: string;
    chart_map: Record<string, number>;
  }) =>
    request.post<{ data: { dashboard_id: number }; code: number; msg: string }>(
      '/api/v1/superset/dashboards/sync',
      data
    ),

  /**
   * 批量同步 BI 到 Superset
   */
  syncBIToSuperset: (data: {
    database_config?: {
      name?: string;
      host?: string;
      port?: number;
      username?: string;
      password?: string;
      database?: string;
    };
    dashboard_ids?: string[];
  }) =>
    request.post<{
      data: {
        synced: Array<{
          bi_dashboard_id: string;
          superset_dashboard_id: number;
          charts_count: number;
        }>;
        total: number;
      };
      code: number;
      msg: string;
    }>('/api/v1/superset/sync/bi', data),
};

export default supersetApi;
