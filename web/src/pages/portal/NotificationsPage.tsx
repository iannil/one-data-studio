import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Badge,
  Tabs,
  Input,
  Select,
  Modal,
  message,
  Tooltip,
  Empty,
  Dropdown,
} from 'antd';
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
  InboxOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  AlertOutlined,
  FileTextOutlined,
  NotificationOutlined,
  EyeOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  getUserNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  archiveNotification,
  deleteNotification,
  UserNotification,
  NotificationListParams,
} from '../../services/admin';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

// 通知类型图标
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

// 通知类型标签
const getTypeTag = (type: string) => {
  const config: Record<string, { color: string; text: string }> = {
    info: { color: 'blue', text: '信息' },
    success: { color: 'green', text: '成功' },
    warning: { color: 'orange', text: '警告' },
    error: { color: 'red', text: '错误' },
    alert: { color: 'red', text: '告警' },
    task: { color: 'cyan', text: '任务' },
    approval: { color: 'purple', text: '审批' },
    system: { color: 'default', text: '系统' },
  };
  const { color, text } = config[type] || config.info;
  return <Tag color={color}>{text}</Tag>;
};

// 严重级别标签
const getSeverityTag = (severity: string) => {
  const config: Record<string, { color: string; text: string }> = {
    info: { color: 'default', text: '信息' },
    low: { color: 'blue', text: '低' },
    medium: { color: 'orange', text: '中' },
    high: { color: 'red', text: '高' },
    critical: { color: 'magenta', text: '紧急' },
  };
  const { color, text } = config[severity] || config.info;
  return <Tag color={color}>{text}</Tag>;
};

function NotificationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedNotification, setSelectedNotification] = useState<UserNotification | null>(null);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [filters, setFilters] = useState<NotificationListParams>({
    page: 1,
    page_size: 20,
  });
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  // 获取通知列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['user-notifications', filters, activeTab],
    queryFn: async () => {
      const params: NotificationListParams = { ...filters };
      if (activeTab === 'unread') {
        params.is_read = false;
      } else if (activeTab !== 'all') {
        params.category = activeTab;
      }
      const response = await getUserNotifications(params);
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
  });

  // 标记已读
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-notifications'] });
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
    },
  });

  // 全部已读
  const markAllReadMutation = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-notifications'] });
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已标记所有通知为已读');
    },
  });

  // 归档通知
  const archiveMutation = useMutation({
    mutationFn: (notificationId: string) => archiveNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-notifications'] });
      message.success('已归档');
    },
  });

  // 删除通知
  const deleteMutation = useMutation({
    mutationFn: (notificationId: string) => deleteNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-notifications'] });
      message.success('已删除');
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

  const columns: ColumnsType<UserNotification> = [
    {
      title: '状态',
      dataIndex: 'is_read',
      width: 60,
      render: (isRead: boolean) => (
        <Badge status={isRead ? 'default' : 'processing'} />
      ),
    },
    {
      title: '类型',
      dataIndex: 'notification_type',
      width: 100,
      render: (type: string) => getTypeTag(type),
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (title: string, record: UserNotification) => (
        <Space>
          {getNotificationIcon(record.notification_type)}
          <Text
            strong={!record.is_read}
            style={{ cursor: 'pointer' }}
            onClick={() => handleNotificationClick(record)}
          >
            {title}
          </Text>
        </Space>
      ),
    },
    {
      title: '摘要',
      dataIndex: 'summary',
      ellipsis: true,
      width: 200,
      render: (summary: string) => (
        <Text type="secondary">{summary || '-'}</Text>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source_name',
      width: 120,
      render: (sourceName: string) => sourceName || '-',
    },
    {
      title: '级别',
      dataIndex: 'severity',
      width: 80,
      render: (severity: string) => severity ? getSeverityTag(severity) : '-',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 160,
      render: (time: string) => time?.slice(0, 16) || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: UserNotification) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: '查看详情',
                onClick: () => setSelectedNotification(record),
              },
              !record.is_read && {
                key: 'read',
                icon: <CheckOutlined />,
                label: '标记已读',
                onClick: () => markReadMutation.mutate(record.id),
              },
              {
                key: 'archive',
                icon: <InboxOutlined />,
                label: '归档',
                onClick: () => archiveMutation.mutate(record.id),
              },
              {
                type: 'divider' as const,
              },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: '删除',
                danger: true,
                onClick: () => {
                  Modal.confirm({
                    title: '确认删除',
                    content: '确定要删除这条通知吗？',
                    onOk: () => deleteMutation.mutate(record.id),
                  });
                },
              },
            ].filter(Boolean),
          }}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  const tabItems = [
    { key: 'all', label: '全部' },
    { key: 'unread', label: <Badge count={data?.unread_count || 0} offset={[10, 0]}>未读</Badge> },
    { key: 'message', label: '消息' },
    { key: 'alert', label: '告警' },
    { key: 'task', label: '任务' },
    { key: 'announcement', label: '公告' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <BellOutlined style={{ marginRight: 8 }} />
              消息通知
            </Title>
            <Text type="secondary">
              共 {data?.total || 0} 条通知，{data?.unread_count || 0} 条未读
            </Text>
          </div>
          <Space>
            <Button
              icon={<CheckOutlined />}
              onClick={() => markAllReadMutation.mutate()}
              disabled={!data?.unread_count}
            >
              全部已读
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
          </Space>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{ marginBottom: 16 }}
        />

        <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
          <Search
            placeholder="搜索通知..."
            allowClear
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            options={[
              { value: 'info', label: '信息' },
              { value: 'success', label: '成功' },
              { value: 'warning', label: '警告' },
              { value: 'error', label: '错误' },
              { value: 'alert', label: '告警' },
              { value: 'task', label: '任务' },
              { value: 'approval', label: '审批' },
            ]}
            onChange={(value) => setFilters({ ...filters, type: value })}
          />
        </div>

        <Table
          columns={columns}
          dataSource={data?.notifications || []}
          rowKey="id"
          loading={isLoading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
          }}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            total: data?.total || 0,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setFilters({ ...filters, page, page_size: pageSize }),
          }}
          locale={{
            emptyText: <Empty description="暂无通知" />,
          }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={
          <Space>
            {selectedNotification && getNotificationIcon(selectedNotification.notification_type)}
            {selectedNotification?.title}
          </Space>
        }
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
        width={600}
      >
        {selectedNotification && (
          <div style={{ padding: '16px 0' }}>
            <div style={{ marginBottom: 16 }}>
              {getTypeTag(selectedNotification.notification_type)}
              {selectedNotification.severity && getSeverityTag(selectedNotification.severity)}
              <Text type="secondary" style={{ marginLeft: 8 }}>
                {selectedNotification.created_at?.slice(0, 16)}
              </Text>
            </div>
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
              {selectedNotification.content || selectedNotification.summary}
            </Paragraph>
            {selectedNotification.source_name && (
              <div style={{ marginTop: 16 }}>
                <Text type="secondary">
                  来源: {selectedNotification.source_name}
                </Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default NotificationsPage;
