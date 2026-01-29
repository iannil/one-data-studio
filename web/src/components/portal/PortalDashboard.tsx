/**
 * 统一门户仪表盘组件
 * 聚合各系统数据，提供统一工作台
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  List,
  Tag,
  Badge,
  Input,
  Button,
  Dropdown,
  Tabs,
  Progress,
  Space,
  Tooltip,
  Typography,
  Alert,
  Divider,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  SearchOutlined,
  BellOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  DashboardOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CheckOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPortalDashboard,
  getQuickLinks,
  getPortalNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
  getPortalTodos,
  completeTodo,
  getSystemStatus,
  type QuickLink,
  type PortalNotification,
  type TodoItem,
  type SystemStatus,
} from '@/services/data';
import './PortalDashboard.css';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

interface PortalDashboardProps {
  userId?: string;
  tenantId?: string;
}

/**
 * 统计卡片小组件
 */
const StatisticWidget: React.FC<{
  title: string;
  icon: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  trend?: number;
  trendDirection?: 'up' | 'down' | 'stable';
}> = ({ title, icon, value, prefix, suffix, trend, trendDirection }) => {
  return (
    <Card className="stat-widget">
      <div className="stat-header">
        <span className="stat-icon">{icon}</span>
        <span className="stat-title">{title}</span>
      </div>
      <Statistic
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ fontSize: '28px', fontWeight: 600 }}
      />
      {trend !== undefined && (
        <div className={`stat-trend ${trendDirection}`}>
          {trendDirection === 'up' ? '↑' : trendDirection === 'down' ? '↓' : '→'} {Math.abs(trend)}%
          <span className="trend-label">vs 上周</span>
        </div>
      )}
    </Card>
  );
};

/**
 * 快捷入口卡片
 */
const QuickLinkCard: React.FC<{ link: QuickLink }> = ({ link }) => {
  return (
    <a
      href={link.url}
      className="quick-link-card"
      target={link.new_window ? '_blank' : undefined}
      rel={link.new_window ? 'noopener noreferrer' : undefined}
    >
      <Badge count={link.badge_count} offset={[-4, 4]}>
        <Card hoverable className="quick-link-inner" bodyStyle={{ padding: '16px' }}>
          <div className="quick-link-icon">{link.icon}</div>
          <div className="quick-link-info">
            <div className="quick-link-title">{link.title}</div>
            <div className="quick-link-desc">{link.description}</div>
          </div>
        </Card>
      </Badge>
    </a>
  );
};

/**
 * 通知中心
 */
const NotificationCenter: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['portal', 'notifications'],
    queryFn: async () => {
      const res = await getPortalNotifications({ limit: 10 });
      return res.data;
    },
    refetchInterval: 60000,
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal', 'notifications'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal', 'notifications'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (notificationId: string) => deleteNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal', 'notifications'] });
    },
  });

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircleOutlined className="notification-icon success" />;
      case 'warning':
        return <WarningOutlined className="notification-icon warning" />;
      case 'error':
        return <CloseCircleOutlined className="notification-icon error" />;
      default:
        return <InfoCircleOutlined className="notification-icon info" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return '#ff4d4f';
      case 'high':
        return '#faad14';
      case 'low':
        return '#8c8c8c';
      default:
        return '#1677ff';
    }
  };

  const handleNotificationClick = (notification: PortalNotification) => {
    if (!notification.read) {
      markReadMutation.mutate(notification.notification_id);
    }
    if (notification.action_url) {
      window.location.href = notification.action_url;
    }
  };

  return (
    <Card
      title={
        <Space>
          <BellOutlined />
          <span>通知中心</span>
          {notifications?.unread_count > 0 && (
            <Badge count={notifications.unread_count} size="small" />
          )}
        </Space>
      }
      extra={
        <Space>
          {notifications?.unread_count > 0 && (
            <Button
              size="small"
              type="link"
              loading={markAllReadMutation.isPending}
              onClick={() => markAllReadMutation.mutate()}
            >
              全部已读
            </Button>
          )}
          <Button size="small" type="link" icon={<ReloadOutlined />} />
        </Space>
      }
      className="notification-center"
      loading={isLoading}
    >
      <List
        dataSource={notifications?.notifications || []}
        renderItem={(notification) => (
          <List.Item
            key={notification.notification_id}
            className={`notification-item ${notification.read ? 'read' : 'unread'}`}
            onClick={() => handleNotificationClick(notification)}
            style={{ cursor: notification.action_url ? 'pointer' : 'default' }}
          >
            <List.Item.Meta
              avatar={getIcon(notification.type)}
              title={
                <Space>
                  <span>{notification.title}</span>
                  {!notification.read && <Badge status="processing" />}
                  <Tag color={getPriorityColor(notification.priority)} style={{ fontSize: '10px' }}>
                    {notification.priority}
                  </Tag>
                  <Tag style={{ fontSize: '10px' }}>{notification.source}</Tag>
                </Space>
              }
              description={
                <div>
                  <Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0 }}>
                    {notification.content}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {new Date(notification.created_at).toLocaleString('zh-CN')}
                  </Text>
                </div>
              }
            />
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                deleteMutation.mutate(notification.notification_id);
              }}
            />
          </List.Item>
        )}
        locale={{ emptyText: '暂无通知' }}
      />
    </Card>
  );
};

/**
 * 待办事项
 */
const TodoList: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: todos, isLoading } = useQuery({
    queryKey: ['portal', 'todos'],
    queryFn: async () => {
      const res = await getPortalTodos({ status: 'pending', limit: 10 });
      return res.data;
    },
    refetchInterval: 60000,
  });

  const completeMutation = useMutation({
    mutationFn: (todoId: string) => completeTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal', 'todos'] });
    },
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'red';
      case 'high':
        return 'orange';
      case 'low':
        return 'default';
      default:
        return 'blue';
    }
  };

  const getSourceIcon = (source: string) => {
    const icons: Record<string, string> = {
      data_api: '📊',
      alldata: '📊', // 兼容旧名称
      quality: '✅',
      model_api: '🤖',
      cube: '🤖', // 兼容旧名称
      agent_api: '⚙️',
      bisheng: '⚙️', // 兼容旧名称
      api: '🔌',
      admin: '⚙️',
    };
    return icons[source] || '📋';
  };

  return (
    <Card
      title={
        <Space>
          <CheckCircleOutlined />
          <span>待办事项</span>
          {todos?.pending_count > 0 && (
            <Badge count={todos.pending_count} size="small" />
          )}
        </Space>
      }
      extra={
        <Button size="small" type="link" icon={<ReloadOutlined />} />
      }
      className="todo-list"
      loading={isLoading}
    >
      <List
        dataSource={todos?.todos || []}
        renderItem={(todo) => (
          <List.Item
            key={todo.todo_id}
            actions={[
              <Button
                key="complete"
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => completeMutation.mutate(todo.todo_id)}
              >
                完成
              </Button>,
            ]}
          >
            <List.Item.Meta
              avatar={<span style={{ fontSize: '24px' }}>{getSourceIcon(todo.source)}</span>}
              title={
                <Space>
                  <a href={todo.action_url}>{todo.title}</a>
                  <Tag color={getPriorityColor(todo.priority)}>{todo.priority}</Tag>
                </Space>
              }
              description={
                <Space direction="vertical" size={0}>
                  <Text type="secondary">{todo.description}</Text>
                  {todo.due_date && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      <ClockCircleOutlined /> 截止: {new Date(todo.due_date).toLocaleString('zh-CN')}
                    </Text>
                  )}
                </Space>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: '暂无待办' }}
      />
    </Card>
  );
};

/**
 * 系统状态监控
 */
const SystemStatusMonitor: React.FC = () => {
  const { data: statusData, isLoading } = useQuery({
    queryKey: ['portal', 'system-status'],
    queryFn: async () => {
      const res = await getSystemStatus();
      return res.data;
    },
    refetchInterval: 30000,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'down':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'degraded':
        return '降级';
      case 'down':
        return '离线';
      default:
        return '未知';
    }
  };

  return (
    <Card
      title={
        <Space>
          <DashboardOutlined />
          <span>系统状态</span>
          {statusData && (
            <Tag color={getStatusColor(statusData.overall_status)}>
              {getStatusText(statusData.overall_status)}
            </Tag>
          )}
        </Space>
      }
      extra={
        <Button size="small" type="link" icon={<ReloadOutlined />} />
      }
      className="system-status-monitor"
      loading={isLoading}
    >
      <Row gutter={[16, 16]}>
        {statusData?.systems.map((system) => (
          <Col key={system.id} xs={12} sm={6}>
            <div className="system-status-item">
              <div className="system-status-info">
                <div className="system-name">{system.name}</div>
                <Tag color={getStatusColor(system.status)} style={{ margin: '4px 0' }}>
                  {getStatusText(system.status)}
                </Tag>
              </div>
              <Progress
                type="circle"
                size={60}
                percent={Math.round(system.uptime_percent)}
                format={(percent) => `${percent}%`}
                strokeColor={{
                  '0%': system.status === 'healthy' ? '#52c41a' : '#ff4d4f',
                  '100%': system.status === 'healthy' ? '#73d13d' : '#ff7875',
                }}
              />
            </div>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

/**
 * 最近活动列表
 */
const RecentActivities: React.FC<{
  activities: Array<{ id: string; title: string; time: string; source: string; type: string; icon: string }>;
}> = ({ activities }) => {
  return (
    <Card title={<Space><ClockCircleOutlined /><span>最近活动</span></Space>} className="recent-activities">
      <List
        dataSource={activities}
        renderItem={(activity) => (
          <List.Item key={activity.id}>
            <List.Item.Meta
              avatar={<span style={{ fontSize: '20px' }}>{activity.icon}</span>}
              title={
                <Space>
                  <span>{activity.title}</span>
                  <Tag color={activity.type === 'warning' ? 'warning' : activity.type === 'success' ? 'success' : 'default'}>
                    {activity.source}
                  </Tag>
                </Space>
              }
              description={
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {activity.time}
                </Text>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: '暂无活动' }}
      />
    </Card>
  );
};

/**
 * 主门户仪表盘组件
 */
const PortalDashboard: React.FC<PortalDashboardProps> = ({ userId, tenantId }) => {
  const [searchVisible, setSearchVisible] = useState(false);
  const [searchValue, setSearchValue] = useState('');

  // 获取仪表盘数据
  const { data: dashboardData, isLoading: dashboardLoading, refetch: refetchDashboard } = useQuery({
    queryKey: ['portal', 'dashboard'],
    queryFn: async () => {
      const res = await getPortalDashboard();
      return res.data;
    },
    refetchInterval: 60000,
  });

  // 获取快捷入口
  const { data: quickLinksData } = useQuery({
    queryKey: ['portal', 'quick-links'],
    queryFn: async () => {
      const res = await getQuickLinks();
      return res.data;
    },
  });

  const widgetsData = dashboardData?.widgets_data || {};
  const activities = widgetsData.list_recent_activities as Array<{
    id: string;
    title: string;
    time: string;
    source: string;
    type: string;
    icon: string;
  }> || [];

  return (
    <div className="portal-dashboard">
      {/* 顶部栏 */}
      <div className="portal-header">
        <div className="portal-title">
          <DashboardOutlined />
          <Title level={3} style={{ margin: 0 }}>工作台</Title>
        </div>

        <Space size="middle">
          {/* 全局搜索 */}
          <div className={`portal-search ${searchVisible ? 'visible' : ''}`}>
            {searchVisible ? (
              <Search
                placeholder="搜索资产、工作流、模型..."
                allowClear
                autoFocus
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onSearch={(value) => {
                  // 实际项目中跳转到搜索结果页
                  console.log('搜索:', value);
                }}
                onBlur={() => {
                  if (!searchValue) setSearchVisible(false);
                }}
                style={{ width: 300 }}
              />
            ) : (
              <Button
                icon={<SearchOutlined />}
                onClick={() => setSearchVisible(true)}
              >
                搜索...
              </Button>
            )}
          </div>

          {/* 用户菜单 */}
          <Dropdown menu={{ items: [] }} placement="bottomRight">
            <Button type="text" icon={<UserOutlined />}>
              {userId || '用户'}
            </Button>
          </Dropdown>

          <Button type="text" icon={<SettingOutlined />} />
        </Space>
      </div>

      {/* 统计卡片行 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <StatisticWidget
            title="数据资产总数"
            icon="📊"
            value={(widgetsData.stat_total_assets as any)?.value || 0}
            trend={(widgetsData.stat_total_assets as any)?.trend}
            trendDirection={(widgetsData.stat_total_assets as any)?.trend_direction}
          />
        </Col>
        <Col xs={12} sm={6}>
          <StatisticWidget
            title="数据质量评分"
            icon="✅"
            value={(widgetsData.stat_quality_score as any)?.value || 0}
            suffix="分"
            trend={(widgetsData.stat_quality_score as any)?.trend}
            trendDirection={(widgetsData.stat_quality_score as any)?.trend_direction}
          />
        </Col>
        <Col xs={12} sm={6}>
          <StatisticWidget
            title="今日任务"
            icon="📋"
            value={`${(widgetsData.stat_today_tasks as any)?.value || 0} / ${(widgetsData.stat_today_tasks as any)?.total || 0}`}
          />
        </Col>
        <Col xs={12} sm={6}>
          <StatisticWidget
            title="待处理告警"
            icon="🔔"
            value={(widgetsData.stat_alerts as any)?.value || 0}
            suffix={(widgetsData.stat_alerts as any)?.critical ? ` (${(widgetsData.stat_alerts as any).critical} 紧急)` : ''}
          />
        </Col>
      </Row>

      {/* 主要内容区 */}
      <Row gutter={[16, 16]}>
        {/* 左侧栏 */}
        <Col xs={24} lg={16}>
          <Tabs
            defaultActiveKey="overview"
            items={[
              {
                key: 'overview',
                label: '概览',
                children: (
                  <>
                    {/* 快捷入口 */}
                    <Card title="快捷入口" style={{ marginBottom: 16 }}>
                      <Row gutter={[16, 16]}>
                        {quickLinksData?.links.map((link) => (
                          <Col key={link.link_id} xs={12} sm={8} md={6}>
                            <QuickLinkCard link={link} />
                          </Col>
                        ))}
                      </Row>
                    </Card>

                    {/* 最近活动 */}
                    <RecentActivities activities={activities} />
                  </>
                ),
              },
              {
                key: 'data-trend',
                label: '数据趋势',
                children: (
                  <Card title="数据访问趋势">
                    <Alert
                      message="图表功能"
                      description="此处将显示数据访问趋势图表，基于 ECharts 或 Recharts 实现。"
                      type="info"
                      showIcon
                    />
                  </Card>
                ),
              },
              {
                key: 'quality',
                label: '数据质量',
                children: (
                  <Card title="数据质量问题">
                    <Alert
                      message="质量问题列表"
                      description="此处将显示当前数据质量问题列表，支持跳转到质量管理模块。"
                      type="warning"
                      showIcon
                    />
                  </Card>
                ),
              },
            ]}
          />
        </Col>

        {/* 右侧栏 */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            {/* 系统状态 */}
            <SystemStatusMonitor />

            {/* 通知中心 */}
            <NotificationCenter />

            {/* 待办事项 */}
            <TodoList />
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default PortalDashboard;
