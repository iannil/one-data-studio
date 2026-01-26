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
  Progress,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  ClockCircleOutlined,
  CheckOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  MoreOutlined,
  CalendarOutlined,
  AlertOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  getUserTodos,
  getTodosSummary,
  startTodo,
  completeTodo,
  cancelTodo,
  UserTodo,
  TodoListParams,
} from '../../services/admin';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

// 优先级标签
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

// 状态标签
const getStatusTag = (status: string, isOverdue: boolean) => {
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

// 类型标签
const getTypeTag = (type: string) => {
  const config: Record<string, { color: string; text: string }> = {
    approval: { color: 'purple', text: '审批' },
    task: { color: 'blue', text: '任务' },
    reminder: { color: 'cyan', text: '提醒' },
    alert: { color: 'red', text: '告警' },
    review: { color: 'green', text: '评审' },
  };
  const { color, text } = config[type] || { color: 'default', text: type };
  return <Tag color={color}>{text}</Tag>;
};

function TodosPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedTodo, setSelectedTodo] = useState<UserTodo | null>(null);
  const [activeTab, setActiveTab] = useState<string>('active');
  const [filters, setFilters] = useState<TodoListParams>({
    page: 1,
    page_size: 20,
  });
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  // 获取待办列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['user-todos', filters, activeTab],
    queryFn: async () => {
      const params: TodoListParams = { ...filters };
      if (activeTab === 'active') {
        params.include_completed = false;
      } else if (activeTab === 'completed') {
        params.status = 'completed';
        params.include_completed = true;
      } else if (activeTab !== 'all') {
        params.status = activeTab;
      } else {
        params.include_completed = true;
      }
      const response = await getUserTodos(params);
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
  });

  // 获取统计摘要
  const { data: summaryData } = useQuery({
    queryKey: ['todos-summary'],
    queryFn: async () => {
      const response = await getTodosSummary();
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
  });

  // 开始处理
  const startMutation = useMutation({
    mutationFn: (todoId: string) => startTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-todos'] });
      queryClient.invalidateQueries({ queryKey: ['todos-summary'] });
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已开始处理');
    },
  });

  // 完成待办
  const completeMutation = useMutation({
    mutationFn: (todoId: string) => completeTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-todos'] });
      queryClient.invalidateQueries({ queryKey: ['todos-summary'] });
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已完成');
    },
  });

  // 取消待办
  const cancelMutation = useMutation({
    mutationFn: (todoId: string) => cancelTodo(todoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-todos'] });
      queryClient.invalidateQueries({ queryKey: ['todos-summary'] });
      queryClient.invalidateQueries({ queryKey: ['portal-dashboard'] });
      message.success('已取消');
    },
  });

  const handleTodoClick = (todo: UserTodo) => {
    if (todo.source_url) {
      navigate(todo.source_url);
    } else {
      setSelectedTodo(todo);
    }
  };

  const columns: ColumnsType<UserTodo> = [
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string, record: UserTodo) => getStatusTag(status, record.is_overdue),
    },
    {
      title: '类型',
      dataIndex: 'todo_type',
      width: 80,
      render: (type: string) => getTypeTag(type),
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (title: string, record: UserTodo) => (
        <Space>
          <Text
            strong={record.status === 'pending' || record.status === 'in_progress'}
            style={{ cursor: 'pointer' }}
            onClick={() => handleTodoClick(record)}
          >
            {title}
          </Text>
          {record.is_overdue && record.status === 'pending' && (
            <AlertOutlined style={{ color: '#ff4d4f' }} />
          )}
        </Space>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      render: (priority: string) => getPriorityTag(priority),
    },
    {
      title: '来源',
      dataIndex: 'source_name',
      width: 120,
      render: (sourceName: string) => sourceName || '-',
    },
    {
      title: '截止时间',
      dataIndex: 'due_date',
      width: 120,
      render: (dueDate: string, record: UserTodo) => {
        if (!dueDate) return '-';
        const isOverdue = record.is_overdue && record.status === 'pending';
        return (
          <Text type={isOverdue ? 'danger' : undefined}>
            <CalendarOutlined style={{ marginRight: 4 }} />
            {dueDate.slice(0, 10)}
          </Text>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (time: string) => time?.slice(0, 16) || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: UserTodo) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: '查看详情',
                onClick: () => setSelectedTodo(record),
              },
              record.status === 'pending' && {
                key: 'start',
                icon: <PlayCircleOutlined />,
                label: '开始处理',
                onClick: () => startMutation.mutate(record.id),
              },
              record.status === 'in_progress' && {
                key: 'complete',
                icon: <CheckOutlined />,
                label: '标记完成',
                onClick: () => completeMutation.mutate(record.id),
              },
              (record.status === 'pending' || record.status === 'in_progress') && {
                type: 'divider' as const,
              },
              (record.status === 'pending' || record.status === 'in_progress') && {
                key: 'cancel',
                icon: <StopOutlined />,
                label: '取消',
                danger: true,
                onClick: () => {
                  Modal.confirm({
                    title: '确认取消',
                    content: '确定要取消这个待办事项吗？',
                    onOk: () => cancelMutation.mutate(record.id),
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
    { key: 'active', label: <Badge count={data?.pending_count || 0} offset={[10, 0]}>待处理</Badge> },
    { key: 'in_progress', label: '进行中' },
    { key: 'completed', label: '已完成' },
    { key: 'all', label: '全部' },
  ];

  // 计算完成率
  const totalActive = (summaryData?.by_status?.pending || 0) + (summaryData?.by_status?.in_progress || 0);
  const totalCompleted = summaryData?.by_status?.completed || 0;
  const completionRate = totalActive + totalCompleted > 0
    ? Math.round((totalCompleted / (totalActive + totalCompleted)) * 100)
    : 0;

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="待处理"
              value={summaryData?.by_status?.pending || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="进行中"
              value={summaryData?.by_status?.in_progress || 0}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="已逾期"
              value={summaryData?.overdue_count || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <Text type="secondary">完成率</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: '#52c41a' }}>
                  {completionRate}%
                </div>
              </div>
              <Progress
                type="circle"
                percent={completionRate}
                width={50}
                strokeColor="#52c41a"
              />
            </div>
          </Card>
        </Col>
      </Row>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <ClockCircleOutlined style={{ marginRight: 8 }} />
              待办事项
            </Title>
            <Text type="secondary">
              共 {data?.total || 0} 条待办，{data?.overdue_count || 0} 条已逾期
            </Text>
          </div>
          <Space>
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
            placeholder="搜索待办..."
            allowClear
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            options={[
              { value: 'approval', label: '审批' },
              { value: 'task', label: '任务' },
              { value: 'reminder', label: '提醒' },
              { value: 'alert', label: '告警' },
              { value: 'review', label: '评审' },
            ]}
            onChange={(value) => setFilters({ ...filters, type: value })}
          />
          <Select
            placeholder="优先级"
            allowClear
            style={{ width: 100 }}
            options={[
              { value: 'urgent', label: '紧急' },
              { value: 'high', label: '高' },
              { value: 'medium', label: '中' },
              { value: 'low', label: '低' },
            ]}
            onChange={(value) => setFilters({ ...filters, priority: value })}
          />
        </div>

        <Table
          columns={columns}
          dataSource={data?.todos || []}
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
            emptyText: <Empty description="暂无待办" />,
          }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={
          <Space>
            {selectedTodo && getTypeTag(selectedTodo.todo_type)}
            {selectedTodo?.title}
          </Space>
        }
        open={!!selectedTodo}
        onCancel={() => setSelectedTodo(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedTodo(null)}>
            关闭
          </Button>,
          selectedTodo?.status === 'pending' && (
            <Button
              key="start"
              type="primary"
              onClick={() => {
                if (selectedTodo) {
                  startMutation.mutate(selectedTodo.id);
                  setSelectedTodo(null);
                }
              }}
            >
              开始处理
            </Button>
          ),
          selectedTodo?.status === 'in_progress' && (
            <Button
              key="complete"
              type="primary"
              onClick={() => {
                if (selectedTodo) {
                  completeMutation.mutate(selectedTodo.id);
                  setSelectedTodo(null);
                }
              }}
            >
              标记完成
            </Button>
          ),
          selectedTodo?.source_url && (
            <Button
              key="action"
              type="primary"
              onClick={() => {
                if (selectedTodo?.source_url) {
                  navigate(selectedTodo.source_url);
                  setSelectedTodo(null);
                }
              }}
            >
              前往处理
            </Button>
          ),
        ].filter(Boolean)}
        width={600}
      >
        {selectedTodo && (
          <div style={{ padding: '16px 0' }}>
            <div style={{ marginBottom: 16 }}>
              {getStatusTag(selectedTodo.status, selectedTodo.is_overdue)}
              {getPriorityTag(selectedTodo.priority)}
              <Text type="secondary" style={{ marginLeft: 8 }}>
                创建于 {selectedTodo.created_at?.slice(0, 16)}
              </Text>
            </div>
            {selectedTodo.description && (
              <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                {selectedTodo.description}
              </Paragraph>
            )}
            <div style={{ marginTop: 16 }}>
              {selectedTodo.due_date && (
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    截止时间: {selectedTodo.due_date.slice(0, 16)}
                    {selectedTodo.is_overdue && selectedTodo.status === 'pending' && (
                      <Tag color="error" style={{ marginLeft: 8 }}>已逾期</Tag>
                    )}
                  </Text>
                </div>
              )}
              {selectedTodo.source_name && (
                <div>
                  <Text type="secondary">
                    来源: {selectedTodo.source_name}
                  </Text>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default TodosPage;
