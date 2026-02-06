/**
 * Superset service API 测试
 * 测试 Superset BI 集成 API 客户端
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { supersetApi } from './superset';
import { apiClient } from './api';

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;

describe('Superset Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 健康检查 ====================

  describe('Health Check', () => {
    it('should get health status', () => {
      supersetApi.getHealth();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/superset/health');
    });
  });

  // ==================== Guest Token ====================

  describe('Guest Token', () => {
    it('should create guest token with resources and user', () => {
      const tokenRequest = {
        resources: [
          { type: 'dashboard', id: '123' },
          { type: 'chart', id: '456' },
        ],
        user: {
          username: 'testuser',
          first_name: 'Test',
          last_name: 'User',
        },
      };
      supersetApi.createGuestToken(tokenRequest);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/guest-token', tokenRequest);
    });

    it('should create guest token with minimal data', () => {
      const tokenRequest = {
        resources: [{ type: 'dashboard', id: '123' }],
      };
      supersetApi.createGuestToken(tokenRequest);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/guest-token', tokenRequest);
    });

    it('should create guest token with RLS', () => {
      const tokenRequest = {
        resources: [{ type: 'dashboard', id: '123' }],
        rls: [
          { dataset: 1, clause: 'region="west"' },
          { dataset: 2, clause: 'status="active"' },
        ],
      };
      supersetApi.createGuestToken(tokenRequest);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/guest-token', tokenRequest);
    });
  });

  // ==================== 仪表板管理 ====================

  describe('Dashboards', () => {
    it('should list dashboards', () => {
      supersetApi.listDashboards();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/superset/dashboards');
    });

    it('should sync dashboard', () => {
      const syncData = {
        dashboard_id: 'bi-dashboard-123',
        chart_map: {
          'chart-1': 10,
          'chart-2': 20,
        },
      };
      supersetApi.syncDashboard(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/dashboards/sync', syncData);
    });
  });

  // ==================== 图表管理 ====================

  describe('Charts', () => {
    it('should list charts without dataset filter', () => {
      supersetApi.listCharts();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/superset/charts', {
        params: { dataset_id: undefined },
      });
    });

    it('should list charts with dataset filter', () => {
      const datasetId = 42;
      supersetApi.listCharts(datasetId);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/superset/charts', {
        params: { dataset_id: datasetId },
      });
    });
  });

  // ==================== BI 同步 ====================

  describe('BI Sync', () => {
    it('should sync BI to Superset with database config', () => {
      const syncData = {
        database_config: {
          name: 'sales_db',
          host: 'localhost',
          port: 5432,
          username: 'admin',
          password: 'secret',
          database: 'sales_dw',
        },
        dashboard_ids: ['dash-1', 'dash-2'],
      };
      supersetApi.syncBIToSuperset(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/sync/bi', syncData);
    });

    it('should sync BI to Superset with minimal config', () => {
      const syncData = {
        dashboard_ids: ['dash-1'],
      };
      supersetApi.syncBIToSuperset(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/sync/bi', syncData);
    });

    it('should sync BI to Superset with only dashboard_ids', () => {
      const syncData = {
        dashboard_ids: ['dash-1', 'dash-2', 'dash-3'],
      };
      supersetApi.syncBIToSuperset(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/sync/bi', syncData);
    });

    it('should sync BI to Superset with only database config', () => {
      const syncData = {
        database_config: {
          host: 'db.example.com',
          port: 3306,
        },
      };
      supersetApi.syncBIToSuperset(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/sync/bi', syncData);
    });
  });

  // ==================== 边界情况 ====================

  describe('Edge Cases', () => {
    it('should handle empty resources array', () => {
      const tokenRequest = {
        resources: [],
      };
      supersetApi.createGuestToken(tokenRequest);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/guest-token', tokenRequest);
    });

    it('should handle empty dashboard_ids in sync', () => {
      const syncData = {
        dashboard_ids: [],
      };
      supersetApi.syncBIToSuperset(syncData);

      expect(mockPost).toHaveBeenCalledWith('/api/v1/superset/sync/bi', syncData);
    });

    it('should handle undefined dataset_id for charts', () => {
      supersetApi.listCharts(undefined);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/superset/charts', {
        params: { dataset_id: undefined },
      });
    });
  });

  // ==================== 默认导出 ====================

  describe('Default Export', () => {
    it('should export supersetApi as default', () => {
      expect(supersetApi).toBeDefined();
      expect(supersetApi.getHealth).toBeDefined();
      expect(supersetApi.createGuestToken).toBeDefined();
      expect(supersetApi.listDashboards).toBeDefined();
      expect(supersetApi.listCharts).toBeDefined();
      expect(supersetApi.syncDashboard).toBeDefined();
      expect(supersetApi.syncBIToSuperset).toBeDefined();
    });
  });
});
