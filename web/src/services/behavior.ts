/**
 * 行为服务API客户端
 */

import { apiClient } from './api';
import type { ApiResponse } from './api';

export interface BehaviorAnomaly {
  id: string;
  tenant_id: string;
  user_id: string;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  detected_at: string;
  status: 'open' | 'investigated' | 'resolved' | 'false_positive';
  rule_id?: string;
  rule_name?: string;
  investigated_by?: string;
  investigated_at?: string;
  investigation_notes?: string;
  actions_taken?: Array<{ action: string; performed_by: string; performed_at: string }>;
  behavior_data?: Record<string, unknown>;
}

export interface UserProfile {
  id: string;
  tenant_id: string;
  user_id: string;
  username?: string;
  email?: string;
  department?: string;
  position?: string;
  activity_level: 'high' | 'medium' | 'low' | 'inactive';
  last_active_at?: string;
  login_frequency?: number;
  avg_session_duration?: number;
  preferred_modules?: string[];
  preferred_time_ranges?: Array<{
    range: string;
    count: number;
    percentage: number;
  }>;
  common_actions?: Array<{
    action: string;
    type: string;
    count: number;
  }>;
  total_sessions: number;
  total_page_views: number;
  total_actions: number;
  avg_daily_usage: number;
  segment_tags?: string[];
  risk_score?: number;
}

export interface StatisticsOverview {
  period_days: number;
  total_behaviors: number;
  unique_users: number;
  total_sessions: number;
  behavior_types: Array<{
    type: string;
    count: number;
  }>;
  open_anomalies: number;
}

export interface ActiveUser {
  user_id: string;
  session_count: number;
  page_views: number;
  last_active: string;
}

export interface Segment {
  tag: string;
  count: number;
}

const BEHAVIOR_BASE_URL = process.env.REACT_APP_BEHAVIOR_API_URL || '/api/v1';

export const behaviorApi = {
  // ==================== 行为采集 ====================

  /**
   * 记录页面浏览
   */
  trackPageView: (data: {
    user_id: string;
    tenant_id?: string;
    session_id?: string;
    page_url: string;
    page_title?: string;
    referrer?: string;
    load_time?: number;
  }) => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/behaviors/page-view`, data);
  },

  /**
   * 记录点击事件
   */
  trackClick: (data: {
    user_id: string;
    tenant_id?: string;
    session_id?: string;
    element_type: string;
    element_id?: string;
    element_text?: string;
    page_url: string;
  }) => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/behaviors/click`, data);
  },

  /**
   * 记录通用行为
   */
  trackBehavior: (data: {
    user_id: string;
    tenant_id?: string;
    behavior_type: string;
    action?: string;
    page_url?: string;
    metadata?: Record<string, unknown>;
  }) => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/behaviors/track`, data);
  },

  // ==================== 用户画像 ====================

  /**
   * 获取用户画像
   */
  getUserProfile: (userId: string, refresh?: boolean) => {
    return apiClient.get<ApiResponse<UserProfile>>(`${BEHAVIOR_BASE_URL}/profiles/user/${userId}`, {
      params: { refresh }
    });
  },

  /**
   * 刷新用户画像
   */
  refreshUserProfile: (userId: string, userInfo?: Record<string, unknown>) => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/profiles/user/${userId}/refresh`, {
      user_info: userInfo,
    });
  },

  /**
   * 获取分群标签列表
   */
  getSegments: () => {
    return apiClient.get<ApiResponse<Segment[]>>(`${BEHAVIOR_BASE_URL}/profiles/segments`);
  },

  /**
   * 根据分群获取用户
   */
  getProfilesBySegment: (segmentTag: string) => {
    return apiClient.get(`${BEHAVIOR_BASE_URL}/profiles/segment/${segmentTag}`);
  },

  /**
   * 获取相似用户
   */
  getSimilarUsers: (userId: string, limit?: number) => {
    return apiClient.get(`${BEHAVIOR_BASE_URL}/profiles/user/${userId}/similar`, {
      params: { limit }
    });
  },

  // ==================== 活跃度分析 ====================

  /**
   * 获取用户活跃度
   */
  getUserActivity: (userId: string, days?: number) => {
    return apiClient.get(`${BEHAVIOR_BASE_URL}/profiles/activity/user/${userId}`, {
      params: { days }
    });
  },

  /**
   * 获取活跃用户列表
   */
  getActiveUsers: (params?: { days?: number }) => {
    return apiClient.get(`${BEHAVIOR_BASE_URL}/profiles/activity/users`, {
      params
    });
  },

  /**
   * 获取统计概览
   */
  getStatisticsOverview: (params?: { days?: number }) => {
    return apiClient.get<ApiResponse<StatisticsOverview>>(`${BEHAVIOR_BASE_URL}/audit/statistics/overview`, {
      params
    });
  },

  // ==================== 异常检测 ====================

  /**
   * 获取异常列表
   */
  getAnomalies: (params?: {
    severity?: string;
    status?: string;
    user_id?: string;
  }) => {
    return apiClient.get<ApiResponse<{ anomalies: BehaviorAnomaly[]; total: number }>>(
      `${BEHAVIOR_BASE_URL}/audit/anomalies`,
      { params }
    );
  },

  /**
   * 更新异常状态
   */
  updateAnomalyStatus: (
    anomalyId: string,
    status: string,
    investigatedBy?: string,
    notes?: string
  ) => {
    return apiClient.put(`${BEHAVIOR_BASE_URL}/audit/anomalies/${anomalyId}/status`, {
      status,
      investigated_by: investigatedBy,
      notes,
    });
  },

  /**
   * 运行异常检测
   */
  runDetection: (detectionType?: 'all' | 'login' | 'permission' | 'behavior' | 'data') => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/audit/detect`, {
      detection_type: detectionType || 'all',
    });
  },

  // ==================== 审计日志 ====================

  /**
   * 获取审计日志
   */
  getAuditLog: (params?: {
    user_id?: string;
    behavior_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) => {
    return apiClient.get<ApiResponse<{
      total: number;
      page: number;
      page_size: number;
      behaviors: Array<{
        id: number;
        user_id: string;
        behavior_type: string;
        action?: string;
        target_type?: string;
        page_url?: string;
        occurred_at: string;
        ip_address?: string;
        device_type?: string;
      }>;
    }>>(`${BEHAVIOR_BASE_URL}/audit/audit-log`, { params });
  },

  // ==================== 规则管理 ====================

  /**
   * 获取规则列表
   */
  getRules: (params?: {
    rule_type?: string;
    is_active?: boolean;
  }) => {
    return apiClient.get(`${BEHAVIOR_BASE_URL}/audit/rules`, { params });
  },

  /**
   * 创建规则
   */
  createRule: (data: {
    name: string;
    tenant_id?: string;
    description?: string;
    rule_type: string;
    conditions: Record<string, unknown>;
    actions: Record<string, unknown>;
  }) => {
    return apiClient.post(`${BEHAVIOR_BASE_URL}/audit/rules`, data);
  },
};
