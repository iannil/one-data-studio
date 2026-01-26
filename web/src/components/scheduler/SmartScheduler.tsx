/**
 * 智能任务调度组件
 * 可视化任务管理、资源监控和调度优化
 */

import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Space,
  Typography,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Progress,
  Tooltip,
  Alert,
  Timeline,
  Descriptions,
  Steps,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  ThunderboltOutlined,
  FundOutlined,
  CalendarOutlined,
  RocketOutlined,
  SettingOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EditOutlined,
  WarningOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  optimizeSchedule,
  getResourceDemand,
  getSchedulerStatistics,
  getNextTask,
  completeScheduledTask,
  type SchedulerTask,
  type SchedulerTaskPriority,
  type SchedulerTaskStatus,
  type SchedulerStatistics,
  type ResourceDemandPrediction,
} from '@/services/alldata';
import './SmartScheduler.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface SmartSchedulerProps {
  className?: string;
}

/**
 * 任务优先级颜色
 */
const getPriorityColor = (priority: SchedulerTaskPriority) => {
  const colors: Record<SchedulerTaskPriority, string> = {
    critical: 'red',
    high: 'orange',
    normal: 'blue',
    low: 'default',
  };
  return colors[priority] || 'default';
};

const getPriorityText = (priority: SchedulerTaskPriority) => {
  const texts: Record<SchedulerTaskPriority, string> = {
    critical: '紧急',
    high: '高',
    normal: '普通',
    low: '低',
  };
  return texts[priority] || priority;
};

/**
 * 任务状态颜色
 */
const getStatusColor = (status: SchedulerTaskStatus) => {
  const colors: Record<SchedulerTaskStatus, string> = {
    pending: 'default',
    queued: 'blue',
    running: 'processing',
    completed: 'success',
    failed: 'error',
    cancelled: 'default',
    skipped: 'default',
    retrying: 'warning',
  };
  return colors[status] || 'default';
};

const getStatusText = (status: SchedulerTaskStatus) => {
  const texts: Record<SchedulerTaskStatus, string> = {
    pending: '待调度',
    queued: '已排队',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    skipped: '已跳过',
    retrying: '重试中',
  };
  return texts[status] || status;
};

/**
 * 任务列表标签页
 */
const TasksTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<SchedulerTask | undefined>();
  const [filters, setFilters] = useState<{
    status?: SchedulerTaskStatus;
    priority?: SchedulerTaskPriority;
    task_type?: string;
  }>({});

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['scheduler', 'tasks', filters],
    queryFn: async () => {
      const res = await getScheduledTasks(filters);
      return res.data;
    },
    refetchInterval: 10000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteScheduledTask,
    onSuccess: () => {
      message.success('任务删除成功');
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'tasks'] });
    },
  });

  const handleCreate = () => {
    setEditingTask(undefined);
    setModalVisible(true);
  };

  const handleEdit = (task: SchedulerTask) => {
    setEditingTask(task);
    setModalVisible(true);
  };

  const handleDelete = (taskId: string) => {
    deleteMutation.mutate(taskId);
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: SchedulerTask) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>{record.description}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 80,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: SchedulerTaskPriority) => (
        <Tag color={getPriorityColor(priority)}>{getPriorityText(priority)}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: SchedulerTaskStatus) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '资源需求',
      key: 'resources',
      width: 120,
      render: (_: unknown, record: SchedulerTask) => (
        <Space size="small" wrap>
          {record.resource_requirement.cpu_cores > 0 && (
            <Tooltip title={`CPU: ${record.resource_requirement.cpu_cores}核`}>
              <Tag>CPU: {record.resource_requirement.cpu_cores}</Tag>
            </Tooltip>
          )}
          {record.resource_requirement.gpu_count > 0 && (
            <Tooltip title={`GPU: ${record.resource_requirement.gpu_count}个`}>
              <Tag color="purple">GPU: {record.resource_requirement.gpu_count}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '预计耗时',
      dataIndex: 'estimated_duration_ms',
      key: 'estimated_duration_ms',
      width: 100,
      render: (ms: number) => {
        const minutes = Math.floor(ms / 60000);
        return <Text type="secondary">{minutes}分钟</Text>;
      },
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 80,
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: SchedulerTask) => (
        <Space size="small">
          {record.status === 'pending' && (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartTask(record.task_id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleCompleteTask(record.task_id)}
            >
              完成
            </Button>
          )}
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record.task_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleStartTask = async (taskId: string) => {
    try {
      const res = await getNextTask();
      message.info('任务已启动');
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'tasks'] });
    } catch (e) {
      message.error('启动任务失败');
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      await completeScheduledTask(taskId, { success: true, execution_time_ms: 60000 });
      message.success('任务已完成');
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'tasks'] });
    } catch (e) {
      message.error('完成任务失败');
    }
  };

  return (
    <>
      <Card
        title="任务列表"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建任务
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="状态"
            style={{ width: 120 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, status: value })}
          >
            <Option value="pending">待调度</Option>
            <Option value="queued">已排队</Option>
            <Option value="running">运行中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
          </Select>
          <Select
            placeholder="优先级"
            style={{ width: 100 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, priority: value })}
          >
            <Option value="critical">紧急</Option>
            <Option value="high">高</Option>
            <Option value="normal">普通</Option>
            <Option value="low">低</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={tasksData?.tasks || []}
          rowKey="task_id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <TaskFormModal
        visible={modalVisible}
        task={editingTask}
        onCancel={() => setModalVisible(false)}
        onOk={() => {
          setModalVisible(false);
          queryClient.invalidateQueries({ queryKey: ['scheduler', 'tasks'] });
        }}
      />
    </>
  );
};

/**
 * 任务表单对话框
 */
const TaskFormModal: React.FC<{
  visible: boolean;
  task?: SchedulerTask;
  onCancel: () => void;
  onOk: () => void;
}> = ({ visible, task, onCancel, onOk }) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: createScheduledTask,
    onSuccess: () => {
      message.success('任务创建成功');
      onOk();
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SchedulerTask> }) =>
      updateScheduledTask(id, data),
    onSuccess: () => {
      message.success('任务更新成功');
      onOk();
    },
  });

  React.useEffect(() => {
    if (visible) {
      if (task) {
        form.setFieldsValue(task);
      } else {
        form.resetFields();
      }
    }
  }, [visible, task, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (task) {
        await updateMutation.mutate({ id: task.task_id, data: values });
      } else {
        await createMutation.mutate(values);
      }
    } catch (e) {
      // Form validation error
    }
  };

  return (
    <Modal
      title={task ? '编辑任务' : '创建任务'}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={createMutation.isPending || updateMutation.isPending}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label="任务名称"
          rules={[{ required: true, message: '请输入任务名称' }]}
        >
          <Input placeholder="例如：数据同步任务" />
        </Form.Item>

        <Form.Item
          name="description"
          label="任务描述"
        >
          <TextArea rows={2} placeholder="描述任务的用途..." />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="task_type"
              label="任务类型"
              initialValue="etl"
            >
              <Select>
                <Option value="etl">ETL</Option>
                <Option value="ml">机器学习</Option>
                <Option value="data_quality">数据质量</Option>
                <Option value="notification">通知</Option>
                <Option value="report">报表</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="priority"
              label="优先级"
              initialValue="normal"
            >
              <Select>
                <Option value="critical">紧急</Option>
                <Option value="high">高</Option>
                <Option value="normal">普通</Option>
                <Option value="low">低</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="资源需求">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name={['resource_requirement', 'cpu_cores']} label="CPU核数" initialValue={1}>
                <Input type="number" min={0.1} step={0.1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['resource_requirement', 'memory_mb']} label="内存(MB)" initialValue={512}>
                <Input type="number" min={128} step={128} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['resource_requirement', 'gpu_count']} label="GPU个数" initialValue={0}>
                <Input type="number" min={0} />
              </Form.Item>
            </Col>
          </Row>
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="estimated_duration_ms"
              label="预计耗时(毫秒)"
              initialValue={60000}
            >
              <Input type="number" min={1000} step={1000} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="max_retries" label="最大重试次数" initialValue={3}>
              <Input type="number" min={0} max={10} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
};

/**
 * 资源监控标签页
 */
const ResourcesTab: React.FC = () => {
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['scheduler', 'statistics'],
    queryFn: async () => {
      const res = await getSchedulerStatistics();
      return res.data;
    },
    refetchInterval: 5000,
  });

  const [windowMinutes, setWindowMinutes] = useState(60);

  const { data: demandData, isLoading: demandLoading } = useQuery({
    queryKey: ['scheduler', 'resource-demand', windowMinutes],
    queryFn: async () => {
      const res = await getResourceDemand(windowMinutes);
      return res.data;
    },
    refetchInterval: 10000,
  });

  if (statsLoading || !statsData) {
    return <Card>加载中...</Card>;
  }

  const { total_resources, used_resources, available_resources, scheduling_stats } = statsData;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      {/* 总体资源概览 */}
      <Card title="资源概览">
        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <Statistic
              title="CPU"
              value={available_resources.cpu_cores}
              suffix={`/ ${total_resources.cpu_cores} 核`}
              prefix={<FundOutlined />}
            />
            <Progress
              percent={(used_resources.cpu_cores / total_resources.cpu_cores) * 100}
              status={used_resources.cpu_cores / total_resources.cpu_cores > 0.9 ? 'exception' : 'active'}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="内存"
              value={available_resources.memory_mb}
              suffix={`/${total_resources.memory_mb} MB`}
              prefix={<FundOutlined />}
            />
            <Progress
              percent={(used_resources.memory_mb / total_resources.memory_mb) * 100}
              status={used_resources.memory_mb / total_resources.memory_mb > 0.9 ? 'exception' : 'active'}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="GPU"
              value={available_resources.gpu_count}
              suffix={`/ ${total_resources.gpu_count} 个`}
              prefix={<ThunderboltOutlined />}
            />
            <Progress
              percent={(used_resources.gpu_count / total_resources.gpu_count) * 100}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="队列长度"
              value={scheduling_stats.total_scheduled - scheduling_stats.total_completed - scheduling_stats.total_failed}
              prefix={<ClockCircleOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* 资源需求预测 */}
      <Card
        title="资源需求预测"
        extra={
          <Select
            defaultValue="60"
            style={{ width: 120 }}
            onChange={(value) => setWindowMinutes(value)}
          >
            <Option value="30">30分钟</Option>
            <Option value="60">60分钟</Option>
            <Option value="120">2小时</Option>
            <Option value="240">4小时</Option>
          </Select>
        }
      >
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="预计任务数"
              value={demandData?.predicted_tasks || 0}
              loading={demandLoading}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="CPU 需求"
              value={demandData?.resource_demand?.cpu_cores || 0}
              suffix="核"
              loading={demandLoading}
            />
            <Progress
              percent={demandData?.resource_utilization?.cpu_percent || 0}
              strokeColor={demandData?.resource_utilization?.cpu_percent > 90 ? '#ff4d4f' : '#1677ff'}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="内存需求"
              value={demandData?.resource_demand?.memory_mb || 0}
              suffix="MB"
              loading={demandLoading}
            />
            <Progress
              percent={demandData?.resource_utilization?.memory_percent || 0}
              strokeColor={demandData?.resource_utilization?.memory_percent > 90 ? '#ff4d4f' : '#1677ff'}
            />
          </Col>
        </Row>

        {demandData?.recommendations && demandData.recommendations.length > 0 && (
          <Alert
            type="warning"
            message="资源建议"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {demandData.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            }
            style={{ marginTop: 16 }}
          />
        )}
      </Card>
    </Space>
  );
};

/**
 * 统计标签页
 */
const StatisticsTab: React.FC = () => {
  const { data: statsData, isLoading } = useQuery({
    queryKey: ['scheduler', 'statistics'],
    queryFn: async () => {
      const res = await getSchedulerStatistics();
      return res.data;
    },
    refetchInterval: 5000,
  });

  if (isLoading || !statsData) {
    return <Card>加载中...</Card>;
  }

  const { status_counts, scheduling_stats } = statsData;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="总任务数"
            value={statsData.total_tasks}
            prefix={<RocketOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="已完成"
            value={scheduling_stats.total_completed}
            valueStyle={{ color: '#52c41a' }}
            prefix={<CheckCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="失败"
            value={scheduling_stats.total_failed}
            valueStyle={{ color: '#ff4d4f' }}
            prefix={<CloseCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title="重试次数"
            value={scheduling_stats.total_retries}
            prefix={<ReloadOutlined />}
          />
        </Card>
      </Col>

      {/* 状态分布 */}
      <Col span={24}>
        <Card title="任务状态分布">
          <Row gutter={16}>
            {Object.entries(status_counts).map(([status, count]) => (
              <Col key={status} xs={12} sm={8} md={6}>
                <Statistic
                  title={getStatusText(status as SchedulerTaskStatus)}
                  value={count}
                  valueStyle={{ color: getStatusColor(status as SchedulerTaskStatus) === 'error' ? '#ff4d4f' : undefined }}
                />
              </Col>
            ))}
          </Row>
        </Card>
      </Col>
    </Row>
  );
};

/**
 * 主智能调度组件
 */
const SmartScheduler: React.FC<SmartSchedulerProps> = ({ className }) => {
  return (
    <div className={`smart-scheduler ${className || ''}`}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>智能任务调度</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="tasks"
          items={[
            {
              key: 'tasks',
              label: '任务管理',
              children: <TasksTab />,
            },
            {
              key: 'resources',
              label: '资源监控',
              children: <ResourcesTab />,
            },
            {
              key: 'statistics',
              label: '统计分析',
              children: <StatisticsTab />,
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default SmartScheduler;
