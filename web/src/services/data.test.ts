/**
 * Alldata Service 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as data from './alldata';
import { apiClient } from './api';

// Mock apiClient
vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Alldata Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============= Dataset API =============
  describe('Dataset API', () => {
    it('getDatasets should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { datasets: [], total: 0, page: 1, page_size: 10 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { status: 'active', page: 1, page_size: 10 };
      const result = await data.getDatasets(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getDatasets should call correct endpoint without params', async () => {
      const mockResponse = { code: 0, data: { datasets: [], total: 0, page: 1, page_size: 10 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDatasets();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('getDataset should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { dataset_id: 'ds-123', name: 'Test Dataset' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDataset('ds-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets/ds-123');
      expect(result).toEqual(mockResponse);
    });

    it('createDataset should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { dataset_id: 'ds-new', name: 'New Dataset', status: 'active', created_at: '2024-01-01' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateDatasetRequest = {
        name: 'New Dataset',
        description: 'Test dataset',
        storage_type: 'minio',
        storage_path: '/data/test',
        format: 'parquet',
      };
      const result = await data.createDataset(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/datasets', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateDataset should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { dataset_id: 'ds-123', name: 'Updated Dataset' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateDatasetRequest = { name: 'Updated Dataset', tags: ['updated'] };
      const result = await data.updateDataset('ds-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/datasets/ds-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteDataset should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteDataset('ds-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/datasets/ds-123');
      expect(result).toEqual(mockResponse);
    });

    it('getUploadUrl should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { upload_url: 'https://s3.example.com/upload', file_id: 'file-123', expires_at: '2024-01-01T01:00:00Z' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.UploadUrlRequest = { file_name: 'data.csv', file_size: 1024, content_type: 'text/csv' };
      const result = await data.getUploadUrl('ds-123', request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/datasets/ds-123/upload-url', request);
      expect(result).toEqual(mockResponse);
    });

    it('getDatasetPreview should call correct endpoint with limit', async () => {
      const mockResponse = { code: 0, data: { columns: ['id', 'name'], rows: [], total_rows: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDatasetPreview('ds-123', 50);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets/ds-123/preview', { params: { limit: 50 } });
      expect(result).toEqual(mockResponse);
    });

    it('getDatasetPreview should call correct endpoint without limit', async () => {
      const mockResponse = { code: 0, data: { columns: [], rows: [], total_rows: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDatasetPreview('ds-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets/ds-123/preview', { params: { limit: undefined } });
      expect(result).toEqual(mockResponse);
    });

    it('getDatasetVersions should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { versions: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDatasetVersions('ds-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasets/ds-123/versions');
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Metadata API =============
  describe('Metadata API', () => {
    it('getDatabases should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { databases: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDatabases();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metadata/databases');
      expect(result).toEqual(mockResponse);
    });

    it('getTables should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { tables: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getTables('my_database');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metadata/databases/my_database/tables');
      expect(result).toEqual(mockResponse);
    });

    it('getTableDetail should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { table_name: 'users', columns: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getTableDetail('my_database', 'users');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metadata/databases/my_database/tables/users');
      expect(result).toEqual(mockResponse);
    });

    it('searchTables should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { results: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.searchTables('user', 20);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metadata/tables/search', { query: 'user', limit: 20 });
      expect(result).toEqual(mockResponse);
    });

    it('searchTables should use default limit', async () => {
      const mockResponse = { code: 0, data: { results: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.searchTables('order');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metadata/tables/search', { query: 'order', limit: 10 });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Query API =============
  describe('Query API', () => {
    it('executeQuery should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { query_id: 'q-123', status: 'completed', rows: [], columns: [], row_count: 0, execution_time_ms: 100 } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.QueryExecuteRequest = { database: 'my_db', sql: 'SELECT * FROM users', timeout_seconds: 30 };
      const result = await data.executeQuery(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/query/execute', request);
      expect(result).toEqual(mockResponse);
    });

    it('validateSql should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { valid: true, estimated_rows: 100 } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.QueryValidateRequest = { database: 'my_db', sql: 'SELECT * FROM users' };
      const result = await data.validateSql(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/query/validate', request);
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= DataSource API =============
  describe('DataSource API', () => {
    it('getDataSources should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { sources: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { type: 'mysql' as const, status: 'connected', page: 1 };
      const result = await data.getDataSources(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasources', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getDataSource should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { source_id: 'src-123', name: 'MySQL Prod' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDataSource('src-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/datasources/src-123');
      expect(result).toEqual(mockResponse);
    });

    it('createDataSource should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { source_id: 'src-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateDataSourceRequest = {
        name: 'MySQL Prod',
        type: 'mysql',
        connection: { host: 'localhost', port: 3306, username: 'root' },
      };
      const result = await data.createDataSource(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/datasources', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateDataSource should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { source_id: 'src-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateDataSourceRequest = { name: 'MySQL Prod Updated' };
      const result = await data.updateDataSource('src-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/datasources/src-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteDataSource should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteDataSource('src-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/datasources/src-123');
      expect(result).toEqual(mockResponse);
    });

    it('testDataSource should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { success: true, message: 'Connected', latency_ms: 50 } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.TestConnectionRequest = {
        type: 'mysql',
        connection: { host: 'localhost', port: 3306, username: 'root' },
      };
      const result = await data.testDataSource(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/datasources/test', request);
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= ETL API =============
  describe('ETL API', () => {
    it('getETLTasks should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { tasks: [], total: 0, page: 1, page_size: 10 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { status: 'running' as const, type: 'batch' as const };
      const result = await data.getETLTasks(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/etl/tasks', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getETLTask should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { task_id: 'etl-123', name: 'Daily Sync' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getETLTask('etl-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123');
      expect(result).toEqual(mockResponse);
    });

    it('createETLTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { task_id: 'etl-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateETLTaskRequest = {
        name: 'Daily Sync',
        type: 'batch',
        source: { type: 'database', source_id: 'src-123' },
        target: { type: 'dataset', target_id: 'ds-123' },
      };
      const result = await data.createETLTask(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/etl/tasks', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateETLTask should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { task_id: 'etl-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateETLTaskRequest = { name: 'Updated Sync' };
      const result = await data.updateETLTask('etl-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteETLTask should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteETLTask('etl-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123');
      expect(result).toEqual(mockResponse);
    });

    it('startETLTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-123' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.startETLTask('etl-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopETLTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.stopETLTask('etl-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123/stop');
      expect(result).toEqual(mockResponse);
    });

    it('getETLTaskLogs should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { logs: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getETLTaskLogs('etl-123', 'exec-456', 50);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/etl/tasks/etl-123/logs', { params: { execution_id: 'exec-456', limit: 50 } });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Quality API =============
  describe('Quality API', () => {
    it('getQualityRules should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { rules: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { table_name: 'users', dimension: 'completeness' as const };
      const result = await data.getQualityRules(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/rules', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getQualityRule should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-123', name: 'Not Null Check' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getQualityRule('rule-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/rules/rule-123');
      expect(result).toEqual(mockResponse);
    });

    it('createQualityRule should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateQualityRuleRequest = {
        name: 'Email Format Check',
        dimension: 'validity',
        rule_type: 'regex_check',
        table_name: 'users',
        column_name: 'email',
        config: { regex_pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$' },
        severity: 'high',
      };
      const result = await data.createQualityRule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/rules', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateQualityRule should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateQualityRuleRequest = { severity: 'critical', enabled: true };
      const result = await data.updateQualityRule('rule-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/quality/rules/rule-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteQualityRule should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteQualityRule('rule-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/quality/rules/rule-123');
      expect(result).toEqual(mockResponse);
    });

    it('getQualityResults should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { results: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { table_name: 'users', status: 'failed' };
      const result = await data.getQualityResults(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/results', { params });
      expect(result).toEqual(mockResponse);
    });

    it('runQualityCheck should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { check_id: 'check-123', status: 'running' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.runQualityCheck(['rule-1', 'rule-2']);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/checks/run', { rule_ids: ['rule-1', 'rule-2'] });
      expect(result).toEqual(mockResponse);
    });

    it('getQualityReports should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { reports: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getQualityReports({ table_name: 'users' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/reports', { params: { table_name: 'users' } });
      expect(result).toEqual(mockResponse);
    });

    it('getQualityReport should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { report_id: 'report-123' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getQualityReport('report-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/reports/report-123');
      expect(result).toEqual(mockResponse);
    });

    it('getQualityTasks should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { tasks: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getQualityTasks({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/tasks', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('createQualityTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { task_id: 'task-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateQualityTaskRequest = {
        name: 'Daily Check',
        rules: ['rule-1', 'rule-2'],
        tables: ['users', 'orders'],
        alert_enabled: true,
      };
      const result = await data.createQualityTask(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/tasks', request);
      expect(result).toEqual(mockResponse);
    });

    it('startQualityTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.startQualityTask('task-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/tasks/task-123/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopQualityTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.stopQualityTask('task-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/tasks/task-123/stop');
      expect(result).toEqual(mockResponse);
    });

    it('getQualityAlerts should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { alerts: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getQualityAlerts({ severity: 'high', status: 'active' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/alerts', { params: { severity: 'high', status: 'active' } });
      expect(result).toEqual(mockResponse);
    });

    it('acknowledgeAlert should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.acknowledgeAlert('alert-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/alerts/alert-123/acknowledge');
      expect(result).toEqual(mockResponse);
    });

    it('resolveAlert should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.resolveAlert('alert-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/quality/alerts/alert-123/resolve');
      expect(result).toEqual(mockResponse);
    });

    it('getAlertConfig should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { channels: ['email'], alert_on_severity: ['high', 'critical'] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getAlertConfig();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/alerts/config');
      expect(result).toEqual(mockResponse);
    });

    it('updateAlertConfig should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { channels: ['email', 'webhook'] } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const config: data.AlertConfig = { channels: ['email', 'webhook'], alert_on_severity: ['high', 'critical'] };
      const result = await data.updateAlertConfig(config);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/quality/alerts/config', config);
      expect(result).toEqual(mockResponse);
    });

    it('getQualityTrend should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { trend_points: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { table_name: 'users', period: 'daily' };
      const result = await data.getQualityTrend(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/quality/trends', { params });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Lineage API =============
  describe('Lineage API', () => {
    it('getTableLineage should call correct endpoint with default depth', async () => {
      const mockResponse = { code: 0, data: { nodes: [], edges: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getTableLineage('users');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/table', { params: { table_name: 'users', depth: 2 } });
      expect(result).toEqual(mockResponse);
    });

    it('getTableLineage should call correct endpoint with custom depth', async () => {
      const mockResponse = { code: 0, data: { nodes: [], edges: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getTableLineage('users', 5);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/table', { params: { table_name: 'users', depth: 5 } });
      expect(result).toEqual(mockResponse);
    });

    it('getColumnLineage should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { column: 'user_id', source_columns: [], target_columns: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getColumnLineage('users', 'user_id');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/column', { params: { table_name: 'users', column_name: 'user_id' } });
      expect(result).toEqual(mockResponse);
    });

    it('getImpactAnalysis should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { table_name: 'users', impact_level: 'high', upstream_count: 5, downstream_count: 10 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getImpactAnalysis('users');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/impact', { params: { table_name: 'users' } });
      expect(result).toEqual(mockResponse);
    });

    it('searchLineage should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { results: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.searchLineage('order', 'table');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/search', { params: { query: 'order', type: 'table' } });
      expect(result).toEqual(mockResponse);
    });

    it('getETLLineage should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { nodes: [], edges: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getETLLineage('etl-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/etl/etl-123');
      expect(result).toEqual(mockResponse);
    });

    it('getLineagePath should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { path: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getLineagePath('source_table', 'target_table');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lineage/path', { params: { source: 'source_table', target: 'target_table' } });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Feature Store API =============
  describe('Feature Store API', () => {
    it('getFeatures should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { features: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { feature_group: 'user_features', status: 'active' };
      const result = await data.getFeatures(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/features', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getFeature should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { feature_id: 'feat-123', name: 'user_age' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeature('feat-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/features/feat-123');
      expect(result).toEqual(mockResponse);
    });

    it('createFeature should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { feature_id: 'feat-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateFeatureRequest = {
        name: 'user_age',
        feature_group: 'user_features',
        data_type: 'integer',
        value_type: 'continuous',
        source_table: 'users',
        source_column: 'birth_date',
        transform_sql: 'DATEDIFF(CURDATE(), birth_date) / 365',
      };
      const result = await data.createFeature(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/features', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateFeature should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { feature_id: 'feat-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateFeatureRequest = { status: 'deprecated' };
      const result = await data.updateFeature('feat-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/features/feat-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteFeature should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteFeature('feat-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/features/feat-123');
      expect(result).toEqual(mockResponse);
    });

    it('getFeatureVersions should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { versions: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeatureVersions('feat-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/features/feat-123/versions');
      expect(result).toEqual(mockResponse);
    });

    it('getFeatureGroups should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { groups: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeatureGroups({ status: 'active' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feature-groups', { params: { status: 'active' } });
      expect(result).toEqual(mockResponse);
    });

    it('getFeatureGroup should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { group_id: 'fg-123', name: 'User Features' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeatureGroup('fg-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feature-groups/fg-123');
      expect(result).toEqual(mockResponse);
    });

    it('createFeatureGroup should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { group_id: 'fg-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateFeatureGroupRequest = {
        name: 'User Features',
        source_table: 'users',
        join_keys: ['user_id'],
      };
      const result = await data.createFeatureGroup(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/feature-groups', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteFeatureGroup should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteFeatureGroup('fg-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/feature-groups/fg-123');
      expect(result).toEqual(mockResponse);
    });

    it('getFeatureSets should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { sets: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeatureSets({ page: 1, page_size: 10 });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feature-sets', { params: { page: 1, page_size: 10 } });
      expect(result).toEqual(mockResponse);
    });

    it('createFeatureSet should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { set_id: 'fs-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'Training Set',
        feature_groups: [{ group_id: 'fg-123' }],
        labels: ['is_churned'],
      };
      const result = await data.createFeatureSet(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/feature-sets', request);
      expect(result).toEqual(mockResponse);
    });

    it('getFeatureServices should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { services: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFeatureServices({ status: 'running' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feature-services', { params: { status: 'running' } });
      expect(result).toEqual(mockResponse);
    });

    it('createFeatureService should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-new', endpoint: '/api/features/v1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { name: 'User Feature Service', feature_set_id: 'fs-123' };
      const result = await data.createFeatureService(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/feature-services', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteFeatureService should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteFeatureService('svc-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/feature-services/svc-123');
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Standards API =============
  describe('Standards API', () => {
    it('getStandardLibraries should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { libraries: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getStandardLibraries({ category: 'domain' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/standards/libraries', { params: { category: 'domain' } });
      expect(result).toEqual(mockResponse);
    });

    it('createStandardLibrary should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { library_id: 'lib-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateStandardLibraryRequest = { name: 'Domain Terms', category: 'domain' };
      const result = await data.createStandardLibrary(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/standards/libraries', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteStandardLibrary should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteStandardLibrary('lib-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/standards/libraries/lib-123');
      expect(result).toEqual(mockResponse);
    });

    it('getDataElements should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { elements: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDataElements({ library_id: 'lib-123', search: 'email' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/standards/elements', { params: { library_id: 'lib-123', search: 'email' } });
      expect(result).toEqual(mockResponse);
    });

    it('createDataElement should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { element_id: 'elem-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateDataElementRequest = {
        name: 'Email Address',
        code: 'EMAIL',
        data_type: 'string',
        length: 255,
      };
      const result = await data.createDataElement(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/standards/elements', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteDataElement should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteDataElement('elem-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/standards/elements/elem-123');
      expect(result).toEqual(mockResponse);
    });

    it('getStandardDocuments should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { documents: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getStandardDocuments({ type: 'dictionary', status: 'published' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/standards/documents', { params: { type: 'dictionary', status: 'published' } });
      expect(result).toEqual(mockResponse);
    });

    it('createStandardDocument should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { doc_id: 'doc-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateStandardDocumentRequest = {
        name: 'Data Dictionary',
        version: '1.0',
        type: 'dictionary',
      };
      const result = await data.createStandardDocument(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/standards/documents', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteStandardDocument should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteStandardDocument('doc-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/standards/documents/doc-123');
      expect(result).toEqual(mockResponse);
    });

    it('getStandardMappings should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { mappings: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getStandardMappings({ source_table: 'users' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/standards/mappings', { params: { source_table: 'users' } });
      expect(result).toEqual(mockResponse);
    });

    it('createStandardMapping should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { mapping_id: 'map-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'Email Mapping',
        source_table: 'users',
        source_column: 'email',
        target_element_id: 'elem-123',
      };
      const result = await data.createStandardMapping(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/standards/mappings', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteStandardMapping should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteStandardMapping('map-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/standards/mappings/map-123');
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Asset API =============
  describe('Asset API', () => {
    it('getDataAssets should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { assets: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { type: 'table', search: 'user' };
      const result = await data.getDataAssets(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/assets', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getDataAsset should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { asset_id: 'asset-123' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDataAsset('asset-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/assets/asset-123');
      expect(result).toEqual(mockResponse);
    });

    it('getAssetTree should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { nodes: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getAssetTree();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/assets/tree');
      expect(result).toEqual(mockResponse);
    });

    it('createAssetInventory should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { task_id: 'inv-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = { name: 'Full Inventory', scope: ['database1', 'database2'] };
      const result = await data.createAssetInventory(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/assets/inventory', request);
      expect(result).toEqual(mockResponse);
    });

    it('getAssetInventories should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { tasks: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getAssetInventories({ status: 'completed' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/assets/inventory', { params: { status: 'completed' } });
      expect(result).toEqual(mockResponse);
    });

    it('updateAssetTags should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const result = await data.updateAssetTags('asset-123', ['important', 'pii']);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/assets/asset-123/tags', { tags: ['important', 'pii'] });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Data Service API =============
  describe('Data Service API', () => {
    it('getDataServices should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { services: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { type: 'rest', status: 'published' };
      const result = await data.getDataServices(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/services', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getDataService should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-123', name: 'User API' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getDataService('svc-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/services/svc-123');
      expect(result).toEqual(mockResponse);
    });

    it('createDataService should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-new', endpoint: '/api/users' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateDataServiceRequest = {
        name: 'User API',
        type: 'rest',
        source_type: 'table',
        source_config: { database: 'main', table: 'users' },
      };
      const result = await data.createDataService(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/services', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateDataService should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { name: 'Updated User API' };
      const result = await data.updateDataService('svc-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/services/svc-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteDataService should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteDataService('svc-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/services/svc-123');
      expect(result).toEqual(mockResponse);
    });

    it('publishDataService should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { endpoint: '/api/users/v1' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.publishDataService('svc-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/services/svc-123/publish');
      expect(result).toEqual(mockResponse);
    });

    it('unpublishDataService should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.unpublishDataService('svc-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/services/svc-123/unpublish');
      expect(result).toEqual(mockResponse);
    });

    it('getServiceApiKeys should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { api_keys: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getServiceApiKeys('svc-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/services/svc-123/api-keys');
      expect(result).toEqual(mockResponse);
    });

    it('createServiceApiKey should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { key_id: 'key-new', key: 'sk-xxx' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.createServiceApiKey('svc-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/services/svc-123/api-keys');
      expect(result).toEqual(mockResponse);
    });

    it('deleteServiceApiKey should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteServiceApiKey('svc-123', 'key-456');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/services/svc-123/api-keys/key-456');
      expect(result).toEqual(mockResponse);
    });

    it('getDataServiceStatistics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { service_id: 'svc-123', total_calls: 1000 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { period_start: '2024-01-01', period_end: '2024-01-31' };
      const result = await data.getDataServiceStatistics('svc-123', params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/services/svc-123/statistics', { params });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= BI Report API =============
  describe('BI Report API', () => {
    it('getReports should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { reports: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { type: 'dashboard', status: 'published' };
      const result = await data.getReports(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/bi/reports', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getReport should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { dashboard_id: 'report-123', name: 'Sales Dashboard' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getReport('report-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/bi/reports/report-123');
      expect(result).toEqual(mockResponse);
    });

    it('createReport should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { report_id: 'report-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateReportRequest = {
        name: 'Sales Dashboard',
        type: 'dashboard',
        dataset_id: 'ds-123',
      };
      const result = await data.createReport(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/bi/reports', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateReport should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { report_id: 'report-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { name: 'Updated Dashboard' };
      const result = await data.updateReport('report-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/bi/reports/report-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteReport should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteReport('report-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/bi/reports/report-123');
      expect(result).toEqual(mockResponse);
    });

    it('getReportData should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { data: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getReportData('report-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/bi/reports/report-123/data');
      expect(result).toEqual(mockResponse);
    });

    it('executeReportQuery should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rows: [], columns: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const config = { dataset_id: 'ds-123', dimensions: ['date'], metrics: ['revenue'] };
      const result = await data.executeReportQuery(config);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/bi/query', config);
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Streaming API =============
  describe('Streaming API', () => {
    it('getFlinkJobs should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { jobs: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { status: 'running', type: 'sql' };
      const result = await data.getFlinkJobs(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/streaming/jobs', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getFlinkJob should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { job_id: 'flink-123', name: 'Realtime ETL' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFlinkJob('flink-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123');
      expect(result).toEqual(mockResponse);
    });

    it('createFlinkJob should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'flink-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateFlinkJobRequest = {
        name: 'Realtime ETL',
        type: 'sql',
        parallelism: 4,
        checkpoint_interval: 60000,
        source_config: { type: 'kafka', config: { topic: 'events' } },
        sink_config: { type: 'jdbc', config: { table: 'events_sink' } },
        sql: 'SELECT * FROM events',
      };
      const result = await data.createFlinkJob(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/streaming/jobs', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateFlinkJob should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'flink-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { parallelism: 8 };
      const result = await data.updateFlinkJob('flink-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteFlinkJob should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteFlinkJob('flink-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123');
      expect(result).toEqual(mockResponse);
    });

    it('startFlinkJob should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.startFlinkJob('flink-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopFlinkJob should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.stopFlinkJob('flink-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123/stop');
      expect(result).toEqual(mockResponse);
    });

    it('getFlinkJobStatistics should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { job_id: 'flink-123', metrics: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFlinkJobStatistics('flink-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123/statistics');
      expect(result).toEqual(mockResponse);
    });

    it('getFlinkJobLogs should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { logs: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getFlinkJobLogs('flink-123', { limit: 100, offset: 0 });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/streaming/jobs/flink-123/logs', { params: { limit: 100, offset: 0 } });
      expect(result).toEqual(mockResponse);
    });

    it('validateFlinkSql should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { valid: true } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.validateFlinkSql('SELECT * FROM events');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/streaming/validate-sql', { sql: 'SELECT * FROM events' });
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Offline Workflow API =============
  describe('Offline Workflow API', () => {
    it('getOfflineWorkflows should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { workflows: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { status: 'active' };
      const result = await data.getOfflineWorkflows(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/offline/workflows', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getOfflineWorkflow should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { workflow_id: 'wf-123', name: 'Daily Batch' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getOfflineWorkflow('wf-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/offline/workflows/wf-123');
      expect(result).toEqual(mockResponse);
    });

    it('createOfflineWorkflow should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { workflow_id: 'wf-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateOfflineWorkflowRequest = {
        name: 'Daily Batch',
        nodes: [{ node_id: 'n1', name: 'Extract', type: 'sql', config: {}, position: { x: 0, y: 0 } }],
        edges: [],
      };
      const result = await data.createOfflineWorkflow(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/offline/workflows', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateOfflineWorkflow should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { workflow_id: 'wf-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { name: 'Updated Batch' };
      const result = await data.updateOfflineWorkflow('wf-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/offline/workflows/wf-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteOfflineWorkflow should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteOfflineWorkflow('wf-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/offline/workflows/wf-123');
      expect(result).toEqual(mockResponse);
    });

    it('executeOfflineWorkflow should post to correct endpoint with variables', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const variables = { date: '2024-01-01' };
      const result = await data.executeOfflineWorkflow('wf-123', variables);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/offline/workflows/wf-123/execute', { variables });
      expect(result).toEqual(mockResponse);
    });

    it('getWorkflowExecutions should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { executions: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getWorkflowExecutions('wf-123', { status: 'success' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/offline/workflows/wf-123/executions', { params: { status: 'success' } });
      expect(result).toEqual(mockResponse);
    });

    it('getWorkflowExecution should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-123' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getWorkflowExecution('exec-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/offline/executions/exec-123');
      expect(result).toEqual(mockResponse);
    });

    it('cancelWorkflowExecution should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.cancelWorkflowExecution('exec-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/offline/executions/exec-123/cancel');
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Monitoring API =============
  describe('Monitoring API', () => {
    it('getTaskMetrics should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { metrics: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { task_type: 'etl', status: 'failed' };
      const result = await data.getTaskMetrics(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/tasks', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getMonitoringOverview should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { total_tasks: 100, running_tasks: 10 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getMonitoringOverview();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/overview');
      expect(result).toEqual(mockResponse);
    });

    it('getAlertRules should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { rules: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { enabled: true, severity: 'critical' };
      const result = await data.getAlertRules(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/alert-rules', { params });
      expect(result).toEqual(mockResponse);
    });

    it('createAlertRule should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request = {
        name: 'High Error Rate',
        metric: 'error_rate',
        condition: 'greater_than' as const,
        threshold: 0.1,
        severity: 'critical' as const,
        notification_channels: ['email'],
      };
      const result = await data.createAlertRule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/monitoring/alert-rules', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateAlertRule should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { rule_id: 'rule-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request = { enabled: false, threshold: 0.2 };
      const result = await data.updateAlertRule('rule-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/monitoring/alert-rules/rule-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteAlertRule should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteAlertRule('rule-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/monitoring/alert-rules/rule-123');
      expect(result).toEqual(mockResponse);
    });

    it('getAlerts should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { alerts: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { severity: 'critical', status: 'active' };
      const result = await data.getAlerts(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/monitoring/alerts', { params });
      expect(result).toEqual(mockResponse);
    });

    it('acknowledgeMonitoringAlert should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.acknowledgeMonitoringAlert('alert-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/monitoring/alerts/alert-123/acknowledge');
      expect(result).toEqual(mockResponse);
    });

    it('resolveMonitoringAlert should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.resolveMonitoringAlert('alert-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/monitoring/alerts/alert-123/resolve');
      expect(result).toEqual(mockResponse);
    });
  });

  // ============= Metrics API =============
  describe('Metrics API', () => {
    it('getMetrics should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { metrics: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { category: 'business' as const, status: 'active' };
      const result = await data.getMetrics(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getMetric should call correct endpoint with id', async () => {
      const mockResponse = { code: 0, data: { metric_id: 'm-123', name: 'DAU' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getMetric('m-123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics/m-123');
      expect(result).toEqual(mockResponse);
    });

    it('createMetric should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { metric_id: 'm-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateMetricRequest = {
        name: 'Daily Active Users',
        code: 'dau',
        category: 'business',
        value_type: 'absolute',
        source_table: 'user_events',
        aggregation: 'count',
      };
      const result = await data.createMetric(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics', request);
      expect(result).toEqual(mockResponse);
    });

    it('updateMetric should put to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { metric_id: 'm-123' } };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const request: data.UpdateMetricRequest = { status: 'deprecated' };
      const result = await data.updateMetric('m-123', request);

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/metrics/m-123', request);
      expect(result).toEqual(mockResponse);
    });

    it('deleteMetric should delete correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await data.deleteMetric('m-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/metrics/m-123');
      expect(result).toEqual(mockResponse);
    });

    it('batchDeleteMetrics should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.batchDeleteMetrics(['m-1', 'm-2', 'm-3']);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/batch-delete', { metric_ids: ['m-1', 'm-2', 'm-3'] });
      expect(result).toEqual(mockResponse);
    });

    it('getMetricValue should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { metric_id: 'm-123', value: 1000 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const dimensions = { region: 'us-west' };
      const result = await data.getMetricValue('m-123', dimensions);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics/m-123/value', { params: dimensions });
      expect(result).toEqual(mockResponse);
    });

    it('getMetricValues should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { values: [] } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const metricIds = ['m-1', 'm-2'];
      const dimensions = { region: 'us-west' };
      const result = await data.getMetricValues(metricIds, dimensions);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/values/batch', { metric_ids: metricIds, dimensions });
      expect(result).toEqual(mockResponse);
    });

    it('getMetricTrend should call correct endpoint with params', async () => {
      const mockResponse = { code: 0, data: { metric_id: 'm-123', data_points: [] } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { start_time: '2024-01-01', end_time: '2024-01-31', period: 'daily' };
      const result = await data.getMetricTrend('m-123', params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics/m-123/trend', { params });
      expect(result).toEqual(mockResponse);
    });

    it('getMetricCalculationTasks should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { tasks: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const params = { status: 'running' as const };
      const result = await data.getMetricCalculationTasks(params);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics/calculation-tasks', { params });
      expect(result).toEqual(mockResponse);
    });

    it('createMetricCalculationTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { task_id: 'task-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const request: data.CreateMetricCalculationTaskRequest = {
        name: 'Daily Metric Calculation',
        metric_ids: ['m-1', 'm-2'],
      };
      const result = await data.createMetricCalculationTask(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/calculation-tasks', request);
      expect(result).toEqual(mockResponse);
    });

    it('startMetricCalculationTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { execution_id: 'exec-new' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.startMetricCalculationTask('task-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/calculation-tasks/task-123/start');
      expect(result).toEqual(mockResponse);
    });

    it('stopMetricCalculationTask should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: null };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await data.stopMetricCalculationTask('task-123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/calculation-tasks/task-123/stop');
      expect(result).toEqual(mockResponse);
    });

    it('calculateMetric should post to correct endpoint', async () => {
      const mockResponse = { code: 0, data: { value: 1000, timestamp: '2024-01-01T00:00:00Z' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const params = { start_time: '2024-01-01', end_time: '2024-01-31' };
      const result = await data.calculateMetric('m-123', params);

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/metrics/m-123/calculate', params);
      expect(result).toEqual(mockResponse);
    });

    it('getMetricCategories should call correct endpoint', async () => {
      const mockResponse = { code: 0, data: { categories: [], total: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await data.getMetricCategories();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/metrics/categories/stats');
      expect(result).toEqual(mockResponse);
    });
  });
});
