/**
 * Behavior service API 测试
 * 测试用户行为分析服务 API 客户端
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
  ApiResponse: {},
}));

import { behaviorApi } from './behavior';
import { apiClient } from './api';

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;
const mockPut = apiClient.put as ReturnType<typeof vi.fn>;

describe('Behavior Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== 行为采集 ====================

  describe('Behavior Tracking', () => {
    it('should track page view', () => {
      const data = {
        user_id: 'user-123',
        page_url: '/datasets',
        page_title: 'Datasets Page',
      };
      behaviorApi.trackPageView(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/page-view', data);
    });

    it('should track click event', () => {
      const data = {
        user_id: 'user-123',
        element_type: 'button',
        element_id: 'submit-btn',
        page_url: '/datasets',
      };
      behaviorApi.trackClick(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/click', data);
    });

    it('should track generic behavior', () => {
      const data = {
        user_id: 'user-123',
        behavior_type: 'search',
        action: 'query_datasets',
        metadata: { query: 'sales' },
      };
      behaviorApi.trackBehavior(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/track', data);
    });
  });

  // ==================== 用户画像 ====================

  describe('User Profile', () => {
    it('should get user profile', () => {
      const userId = 'user-123';
      behaviorApi.getUserProfile(userId);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/profiles/user/${userId}`, {
        params: { refresh: undefined },
      });
    });

    it('should get user profile with refresh option', () => {
      const userId = 'user-123';
      behaviorApi.getUserProfile(userId, true);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/profiles/user/${userId}`, {
        params: { refresh: true },
      });
    });

    it('should refresh user profile', () => {
      const userId = 'user-123';
      const userInfo = { department: 'Engineering', position: 'Developer' };
      behaviorApi.refreshUserProfile(userId, userInfo);
      expect(mockPost).toHaveBeenCalledWith(`/api/v1/profiles/user/${userId}/refresh`, {
        user_info: userInfo,
      });
    });

    it('should get segments', () => {
      behaviorApi.getSegments();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/profiles/segments');
    });

    it('should get profiles by segment', () => {
      const segmentTag = 'power-users';
      behaviorApi.getProfilesBySegment(segmentTag);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/profiles/segment/${segmentTag}`);
    });

    it('should get similar users', () => {
      const userId = 'user-123';
      behaviorApi.getSimilarUsers(userId, 10);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/profiles/user/${userId}/similar`, {
        params: { limit: 10 },
      });
    });
  });

  // ==================== 活跃度分析 ====================

  describe('Activity Analysis', () => {
    it('should get user activity', () => {
      const userId = 'user-123';
      behaviorApi.getUserActivity(userId, 30);
      expect(mockGet).toHaveBeenCalledWith(`/api/v1/profiles/activity/user/${userId}`, {
        params: { days: 30 },
      });
    });

    it('should get active users', () => {
      behaviorApi.getActiveUsers({ days: 7 });
      expect(mockGet).toHaveBeenCalledWith('/api/v1/profiles/activity/users', {
        params: { days: 7 },
      });
    });

    it('should get statistics overview', () => {
      behaviorApi.getStatisticsOverview({ days: 30 });
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/statistics/overview', {
        params: { days: 30 },
      });
    });
  });

  // ==================== 异常检测 ====================

  describe('Anomaly Detection', () => {
    it('should get anomalies', () => {
      behaviorApi.getAnomalies({ severity: 'high', status: 'open' });
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/anomalies', {
        params: { severity: 'high', status: 'open' },
      });
    });

    it('should update anomaly status', () => {
      const anomalyId = 'anomaly-123';
      behaviorApi.updateAnomalyStatus(anomalyId, 'investigated', 'admin-123', 'Looking into it');
      expect(mockPut).toHaveBeenCalledWith(`/api/v1/audit/anomalies/${anomalyId}/status`, {
        status: 'investigated',
        investigated_by: 'admin-123',
        notes: 'Looking into it',
      });
    });

    it('should run detection', () => {
      behaviorApi.runDetection('behavior');
      expect(mockPost).toHaveBeenCalledWith('/api/v1/audit/detect', {
        detection_type: 'behavior',
      });
    });

    it('should run detection for all types', () => {
      behaviorApi.runDetection('all');
      expect(mockPost).toHaveBeenCalledWith('/api/v1/audit/detect', {
        detection_type: 'all',
      });
    });
  });

  // ==================== 审计日志 ====================

  describe('Audit Log', () => {
    it('should get audit log', () => {
      const params = {
        user_id: 'user-123',
        behavior_type: 'login',
        page: 1,
        page_size: 20,
      };
      behaviorApi.getAuditLog(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/audit-log', { params });
    });

    it('should get audit log with date range', () => {
      const params = {
        start_date: '2024-01-01',
        end_date: '2024-01-31',
      };
      behaviorApi.getAuditLog(params);
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/audit-log', { params });
    });
  });

  // ==================== 规则管理 ====================

  describe('Rules Management', () => {
    it('should get rules', () => {
      behaviorApi.getRules({ rule_type: 'behavior', is_active: true });
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/rules', {
        params: { rule_type: 'behavior', is_active: true },
      });
    });

    it('should create rule', () => {
      const ruleData = {
        name: 'Suspicious Login Detection',
        tenant_id: 'tenant-123',
        description: 'Detects unusual login patterns',
        rule_type: 'login',
        conditions: { frequency_threshold: 10 },
        actions: { alert: true, block: false },
      };
      behaviorApi.createRule(ruleData);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/audit/rules', ruleData);
    });
  });

  // ==================== 边界情况 ====================

  describe('Edge Cases', () => {
    it('should handle tracking with optional fields', () => {
      const data = {
        user_id: 'user-123',
        page_url: '/test',
      };
      behaviorApi.trackPageView(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/page-view', data);
    });

    it('should handle click tracking with minimal data', () => {
      const data = {
        user_id: 'user-123',
        element_type: 'link',
        page_url: '/test',
      };
      behaviorApi.trackClick(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/click', data);
    });

    it('should handle generic behavior with only required fields', () => {
      const data = {
        user_id: 'user-123',
        behavior_type: 'click',
      };
      behaviorApi.trackBehavior(data);
      expect(mockPost).toHaveBeenCalledWith('/api/v1/behaviors/track', data);
    });

    it('should handle get anomalies without filters', () => {
      behaviorApi.getAnomalies();
      expect(mockGet).toHaveBeenCalledWith('/api/v1/audit/anomalies', { params: undefined });
    });

    it('should handle update anomaly status with minimal params', () => {
      const anomalyId = 'anomaly-123';
      behaviorApi.updateAnomalyStatus(anomalyId, 'resolved');
      expect(mockPut).toHaveBeenCalledWith(`/api/v1/audit/anomalies/${anomalyId}/status`, {
        status: 'resolved',
        investigated_by: undefined,
        notes: undefined,
      });
    });
  });
});
