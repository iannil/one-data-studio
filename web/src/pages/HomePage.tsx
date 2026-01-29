import { useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Typography,
  Spin,
  List,
  Badge,
  Button,
  Tag,
  Empty,
  message,
  Tabs,
  Avatar,
  Tooltip,
  Modal,
} from 'antd';
import {
  DatabaseOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  TableOutlined,
  UserOutlined,
  ExperimentOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  AlertOutlined,
  NotificationOutlined,
  FileTextOutlined,
  RightOutlined,
  CheckOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  getPortalDashboard,
  markNotificationRead,
  markAllNotificationsRead,
  completeTodo,
  startTodo,
  UserNotification,
  UserTodo,
  Announcement,
  PortalDashboard,
} from '../services/admin';

const { Title, Paragraph, Text } = Typography;

// Types
interface StatsOverview {
  users: { total: number; active: number };
  datasets: { total: number; recent: number };
  models: { total: number; deployed: number };
  workflows: { total: number; running: number };
  experiments: { total: number; completed: number };
  api_calls: { today: number; total: number };
  storage: { used_gb: number; total_gb: number };
  compute: { gpu_hours_today: number; cpu_hours_today: number };
}

// API function
const fetchStatsOverview = async (): Promise<StatsOverview> => {
  const response = await fetch('/api/v1/stats/overview');
  if (!response.ok) throw new Error('Failed to fetch stats');
  const data = await response.json();
  return data.data;
};

// Helper functions
const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    case 'warning':
      return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
    case 'error':
    case 'alert':
      return <AlertOutlined style={{ color: '#ff4d4f' }} />;
    case 'task':
      return <FileTextOutlined style={{ color: '#1677ff' }} />;
    case 'approval':
      return <CheckCircleOutlined style={{ color: '#722ed1' }} />;
    default:
      return <NotificationOutlined style={{ color: '#1677ff' }} />;
  }
};

const getPriorityTag = (priority: string) => {
  const config: Record<string, { color: string; text: string }> = {
    urgent: { color: 'red', text: '紧急' },
    high: { color: 'orange', text: '高' },
    medium: { color: 'blue', text: '中' },
    low: { color: 'default', text: '低' },
  };
  const { color, text } = config[priority] || config.medium;
  return <Tag color={color}>{text}</Tag>;
};

const getTodoStatusTag = (status: string, isOverdue: boolean) => {
  if (isOverdue && status === 'pending') {
    return <Tag color="error">已逾期</Tag>;
  }
  const config: Record<string, { color: string; text: string }> = {
    pending: { color: 'default', text: '待处理' },
    in_progress: { color: 'processing', text: '进行中' },
    completed: { color: 'success', text: '已完成' },
    cancelled: { color: 'default', text: '已取消' },
    expired: { color: 'error', text: '已过期' },
  };
  const { color, text } = config[status] || config.pending;
  return <Tag color={color}>{text}</Tag>;
};

const getAnnouncementTag = (type: string) => {
  const config: Record<string, { color: string; text: string }> = {
    info: { color: 'blue', text: '通知' },
    update: { color: 'green', text: '更新' },
    maintenance: { color: 'orange', text: '维护' },
    warning: { color: 'gold', text: '警告' },
    urgent: { color: 'red', text: '紧急' },
  };
  const { color, text } = config[type] || config.info;
  return <Tag color={color}>{text}</Tag>;
};

function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedNotification, setSelectedNotification] = useState<UserNotification | null>(null);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<Announcement | null>(null);

  // Fetch platform stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats-overview'],
    queryFn: fetchStatsOverview,
    staleTime: 60000,
  });

  // Fetch portal dashboard data
  const { data: portalData, isLoading: portalLoading } = useQuery({
    queryKey: ['portal-dashboard'],
    queryFn: async () => {
      const response = await getPortalDashboard();
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
    staleTime: 30000,
  });

  // Mark notification as read
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
    },
  });

  // Mark all notifications as read
  const markAllReadMutation = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已标记所有通知为已读');
    },
  });

  // Start todo
  const startTodoMutation = useMutation({
    mutationFn: (todoId: string) => startTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已开始处理');
    },
  });

  // Complete todo
  const completeTodoMutation = useMutation({
    mutationFn: (todoId: string) => completeTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已完成');
    },
  });

  const handleNotificationClick = (notification: UserNotification) => {
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id);
    }
    if (notification.action_url) {
      navigate(notification.action_url);
    } else {
      setSelectedNotification(notification);
    }
  };

  const handleTodoAction = (todo: UserTodo) => {
    if (todo.source_url) {
      navigate(todo.source_url);
    } else if (todo.status === 'pending') {
      startTodoMutation.mutate(todo.id);
    }
  };

  const portalStats = portalData?.stats;
  const isLoading = statsLoading || portalLoading;

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>工作台</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          统一数据 + AI + LLM 融合平台
        </Paragraph>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* Portal Stats Row */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={24} sm={12} md={6}>
              <Card
                hoverable
                onClick={() => navigate('/portal/notifications')}
                style={{ cursor: 'pointer' }}
              >
                <Statistic
                  title="未读通知"
                  value={portalStats?.unread_notifications || 0}
                  prefix={<Badge count={portalStats?.unread_notifications || 0} offset={[10, 0]}><BellOutlined /></Badge>}
                  valueStyle={{ color: portalStats?.unread_notifications ? '#ff4d4f' : '#1677ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card
                hoverable
                onClick={() => navigate('/portal/todos')}
                style={{ cursor: 'pointer' }}
              >
                <Statistic
                  title="待办事项"
                  value={portalStats?.pending_todos || 0}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#faad14' }}
                  suffix={
                    portalStats?.overdue_todos ? (
                      <span style={{ fontSize: 12, color: '#ff4d4f' }}>
                        {portalStats.overdue_todos} 已逾期
                      </span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="今日活动"
                  value={portalStats?.today_activities || 0}
                  prefix={<ExperimentOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="活跃用户"
                  value={stats?.users?.active || 0}
                  prefix={<UserOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                  suffix={`/ ${stats?.users?.total || 0}`}
                />
              </Card>
            </Col>
          </Row>

          {/* Main Content: Notifications, Todos, Announcements */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            {/* Notifications */}
            <Col xs={24} lg={8}>
              <Card
                title={
                  <span>
                    <BellOutlined style={{ marginRight: 8 }} />
                    消息通知
                    {portalStats?.unread_notifications ? (
                      <Badge
                        count={portalStats.unread_notifications}
                        style={{ marginLeft: 8 }}
                      />
                    ) : null}
                  </span>
                }
                extra={
                  <Button
                    type="link"
                    size="small"
                    onClick={() => markAllReadMutation.mutate()}
                    disabled={!portalStats?.unread_notifications}
                  >
                    全部已读
                  </Button>
                }
                styles={{ body: { padding: '12px 0', maxHeight: 400, overflow: 'auto' } }}
              >
                {portalData?.recent_notifications?.length ? (
                  <List
                    dataSource={portalData.recent_notifications}
                    renderItem={(item: UserNotification) => (
                      <List.Item
                        style={{
                          padding: '12px 16px',
                          cursor: 'pointer',
                          backgroundColor: item.is_read ? 'transparent' : '#f6ffed',
                        }}
                        onClick={() => handleNotificationClick(item)}
                      >
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              icon={getNotificationIcon(item.notification_type)}
                              style={{ backgroundColor: 'transparent' }}
                            />
                          }
                          title={
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Text
                                strong={!item.is_read}
                                ellipsis
                                style={{ flex: 1, maxWidth: 180 }}
                              >
                                {item.title}
                              </Text>
                              {!item.is_read && <Badge status="processing" />}
                            </div>
                          }
                          description={
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {item.summary || item.created_at?.slice(0, 16)}
                            </Text>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无通知"
                    style={{ padding: 40 }}
                  />
                )}
                <div style={{ textAlign: 'center', padding: '8px 0', borderTop: '1px solid #f0f0f0' }}>
                  <Button type="link" onClick={() => navigate('/portal/notifications')}>
                    查看全部 <RightOutlined />
                  </Button>
                </div>
              </Card>
            </Col>

            {/* Todos */}
            <Col xs={24} lg={8}>
              <Card
                title={
                  <span>
                    <ClockCircleOutlined style={{ marginRight: 8 }} />
                    待办事项
                    {portalStats?.pending_todos ? (
                      <Badge
                        count={portalStats.pending_todos}
                        style={{ marginLeft: 8, backgroundColor: '#faad14' }}
                      />
                    ) : null}
                  </span>
                }
                extra={
                  portalStats?.overdue_todos ? (
                    <Tag color="error">{portalStats.overdue_todos} 逾期</Tag>
                  ) : null
                }
                styles={{ body: { padding: '12px 0', maxHeight: 400, overflow: 'auto' } }}
              >
                {portalData?.recent_todos?.length ? (
                  <List
                    dataSource={portalData.recent_todos}
                    renderItem={(item: UserTodo) => (
                      <List.Item
                        style={{ padding: '12px 16px' }}
                        actions={[
                          item.status === 'pending' && (
                            <Tooltip title="开始处理">
                              <Button
                                type="text"
                                size="small"
                                icon={<EyeOutlined />}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleTodoAction(item);
                                }}
                              />
                            </Tooltip>
                          ),
                          item.status === 'in_progress' && (
                            <Tooltip title="完成">
                              <Button
                                type="text"
                                size="small"
                                icon={<CheckOutlined />}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  completeTodoMutation.mutate(item.id);
                                }}
                              />
                            </Tooltip>
                          ),
                        ].filter(Boolean)}
                      >
                        <List.Item.Meta
                          title={
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Text ellipsis style={{ flex: 1, maxWidth: 150 }}>
                                {item.title}
                              </Text>
                              {getPriorityTag(item.priority)}
                            </div>
                          }
                          description={
                            <div>
                              {getTodoStatusTag(item.status, item.is_overdue)}
                              {item.due_date && (
                                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                                  截止: {item.due_date.slice(0, 10)}
                                </Text>
                              )}
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无待办"
                    style={{ padding: 40 }}
                  />
                )}
                <div style={{ textAlign: 'center', padding: '8px 0', borderTop: '1px solid #f0f0f0' }}>
                  <Button type="link" onClick={() => navigate('/portal/todos')}>
                    查看全部 <RightOutlined />
                  </Button>
                </div>
              </Card>
            </Col>

            {/* Announcements */}
            <Col xs={24} lg={8}>
              <Card
                title={
                  <span>
                    <NotificationOutlined style={{ marginRight: 8 }} />
                    系统公告
                  </span>
                }
                styles={{ body: { padding: '12px 0', maxHeight: 400, overflow: 'auto' } }}
              >
                {portalData?.active_announcements?.length ? (
                  <List
                    dataSource={portalData.active_announcements}
                    renderItem={(item: Announcement) => (
                      <List.Item
                        style={{ padding: '12px 16px', cursor: 'pointer' }}
                        onClick={() => setSelectedAnnouncement(item)}
                      >
                        <List.Item.Meta
                          title={
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              {item.is_pinned && (
                                <Tag color="red" style={{ marginRight: 0 }}>置顶</Tag>
                              )}
                              {getAnnouncementTag(item.announcement_type)}
                              <Text ellipsis style={{ flex: 1, maxWidth: 120 }}>
                                {item.title}
                              </Text>
                            </div>
                          }
                          description={
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {item.summary || item.created_at?.slice(0, 10)}
                            </Text>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无公告"
                    style={{ padding: 40 }}
                  />
                )}
                <div style={{ textAlign: 'center', padding: '8px 0', borderTop: '1px solid #f0f0f0' }}>
                  <Button type="link" onClick={() => navigate('/portal/announcements')}>
                    查看全部 <RightOutlined />
                  </Button>
                </div>
              </Card>
            </Col>
          </Row>

          {/* Platform Stats */}
          <Title level={4} style={{ marginBottom: '16px' }}>
            平台数据
          </Title>
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="数据集"
                  value={stats?.datasets?.total || 0}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ color: '#1677ff' }}
                  suffix={
                    stats?.datasets?.recent ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>+{stats.datasets.recent} 新增</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="模型"
                  value={stats?.models?.total || 0}
                  prefix={<NodeIndexOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                  suffix={
                    stats?.models?.deployed ? (
                      <span style={{ fontSize: 12, color: '#1677ff' }}>{stats.models.deployed} 已部署</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="工作流"
                  value={stats?.workflows?.total || 0}
                  prefix={<TableOutlined />}
                  valueStyle={{ color: '#faad14' }}
                  suffix={
                    stats?.workflows?.running ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>{stats.workflows.running} 运行中</span>
                    ) : null
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="存储使用"
                  value={stats?.storage?.used_gb?.toFixed(1) || 0}
                  prefix={<CloudServerOutlined />}
                  suffix={`/ ${stats?.storage?.total_gb || 0} GB`}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Quick Start */}
          <Title level={4} style={{ marginBottom: '16px' }}>
            快速开始
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card
                hoverable
                onClick={() => navigate('/datasets')}
                style={{ cursor: 'pointer' }}
              >
                <DatabaseOutlined style={{ fontSize: '32px', color: '#1677ff', marginBottom: '16px' }} />
                <Title level={5}>数据集管理</Title>
                <Paragraph type="secondary">
                  管理数据集、定义 Schema、版本控制、文件上传
                </Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                hoverable
                onClick={() => navigate('/chat')}
                style={{ cursor: 'pointer' }}
              >
                <MessageOutlined style={{ fontSize: '32px', color: '#52c41a', marginBottom: '16px' }} />
                <Title level={5}>AI 聊天</Title>
                <Paragraph type="secondary">
                  与 AI 模型对话、流式输出、参数配置
                </Paragraph>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                hoverable
                onClick={() => navigate('/metadata')}
                style={{ cursor: 'pointer' }}
              >
                <TableOutlined style={{ fontSize: '32px', color: '#faad14', marginBottom: '16px' }} />
                <Title level={5}>元数据浏览</Title>
                <Paragraph type="secondary">
                  浏览数据库和表结构、Text-to-SQL 查询
                </Paragraph>
              </Card>
            </Col>
          </Row>
        </>
      )}

      {/* Notification Detail Modal */}
      <Modal
        title={selectedNotification?.title}
        open={!!selectedNotification}
        onCancel={() => setSelectedNotification(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedNotification(null)}>
            关闭
          </Button>,
          selectedNotification?.action_url && (
            <Button
              key="action"
              type="primary"
              onClick={() => {
                if (selectedNotification?.action_url) {
                  navigate(selectedNotification.action_url);
                  setSelectedNotification(null);
                }
              }}
            >
              {selectedNotification?.action_label || '查看详情'}
            </Button>
          ),
        ].filter(Boolean)}
      >
        <div style={{ padding: '16px 0' }}>
          <div style={{ marginBottom: 16 }}>
            <Tag color={selectedNotification?.notification_type === 'error' ? 'error' : 'blue'}>
              {selectedNotification?.notification_type}
            </Tag>
            <Text type="secondary" style={{ marginLeft: 8 }}>
              {selectedNotification?.created_at?.slice(0, 16)}
            </Text>
          </div>
          <Paragraph>{selectedNotification?.content || selectedNotification?.summary}</Paragraph>
          {selectedNotification?.source_name && (
            <Text type="secondary">
              来源: {selectedNotification.source_name}
            </Text>
          )}
        </div>
      </Modal>

      {/* Announcement Detail Modal */}
      <Modal
        title={selectedAnnouncement?.title}
        open={!!selectedAnnouncement}
        onCancel={() => setSelectedAnnouncement(null)}
        footer={
          <Button onClick={() => setSelectedAnnouncement(null)}>
            关闭
          </Button>
        }
        width={600}
      >
        <div style={{ padding: '16px 0' }}>
          <div style={{ marginBottom: 16 }}>
            {selectedAnnouncement?.is_pinned && (
              <Tag color="red">置顶</Tag>
            )}
            {selectedAnnouncement && getAnnouncementTag(selectedAnnouncement.announcement_type)}
            <Text type="secondary" style={{ marginLeft: 8 }}>
              发布于 {selectedAnnouncement?.publish_at?.slice(0, 10) || selectedAnnouncement?.created_at?.slice(0, 10)}
            </Text>
          </div>
          <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
            {selectedAnnouncement?.content || selectedAnnouncement?.summary}
          </Paragraph>
        </div>
      </Modal>
    </div>
  );
}

export default HomePage;
