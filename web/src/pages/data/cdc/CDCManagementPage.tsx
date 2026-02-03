/**
 * CDC 增量数据采集管理页面
 * 支持 MySQL Binlog 和 PostgreSQL WAL 的增量捕获
 */

import { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Input,
  Form,
  Select,
  Space,
  Typography,
  message,
  Modal,
  Tag,
  Statistic,
  Row,
  Col,
  Progress,
  Alert,
  Timeline,
  Empty,
  Spin,
  Badge,
  Tabs,
  Switch,
  InputNumber,
  Tooltip,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  SyncOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import './CDCManagementPage.css';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface CDCTask {
  cdc_id: string;
  source_type: string;
  status: string;
  events_captured: number;
  events_processed: number;
  events_failed: number;
  insert_events: number;
  update_events: number;
  delete_events: number;
  ddl_events: number;
  last_capture_time: string;
  last_position: string;
  current_lag_ms: number;
  error_message?: string;
  throughput_per_second: number;
}

interface CDCEvent {
  event_id: string;
  event_type: string;
  source_type: string;
  table: string;
  database: string;
  timestamp: number;
  data: Record<string, any>;
  old_data: Record<string, any>;
  new_data: Record<string, any>;
  processed: boolean;
  error?: string;
}

const SOURCE_TYPE_OPTIONS = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'Oracle', value: 'oracle' },
  { label: 'MongoDB', value: 'mongodb' },
];

const STATUS_CONFIG = {
  idle: { color: 'default', icon: <ClockCircleOutlined />, text: '空闲' },
  connecting: { color: 'processing', icon: <SyncOutlined spin />, text: '连接中' },
  connected: { color: 'blue', icon: <CheckCircleOutlined />, text: '已连接' },
  running: { color: 'success', icon: <ThunderboltOutlined />, text: '运行中' },
  paused: { color: 'warning', icon: <PauseCircleOutlined />, text: '已暂停' },
  error: { color: 'error', icon: <CloseCircleOutlined />, text: '错误' },
  stopped: { color: 'default', icon: <StopOutlined />, text: '已停止' },
};

const EVENT_TYPE_CONFIG = {
  insert: { color: 'green', label: 'INSERT' },
  update: { color: 'blue', label: 'UPDATE' },
  delete: { color: 'red', label: 'DELETE' },
  ddl: { color: 'orange', label: 'DDL' },
};

/**
 * CDC 任务列表组件
 */
const CDCTaskList: React.FC<{
  onCreate: () => void;
  onRefresh: () => void;
}> = ({ onCreate, onRefresh }) => {
  const queryClient = useQueryClient();

  const { data: cdcTasksData, isLoading } = useQuery({
    queryKey: ['cdc', 'tasks'],
    queryFn: async () => {
      const res = await fetch('/api/v1/cdc/tasks', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: async (cdcId: string) => {
      const res = await fetch(`/api/v1/cdc/tasks/${cdcId}/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('CDC 任务启动成功');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: async (cdcId: string) => {
      const res = await fetch(`/api/v1/cdc/tasks/${cdcId}/stop`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('CDC 任务已停止');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (cdcId: string) => {
      const res = await fetch(`/api/v1/cdc/tasks/${cdcId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('CDC 任务已删除');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
  });

  const tasks = cdcTasksData?.data?.tasks || [];

  const columns = [
    {
      title: 'CDC ID',
      dataIndex: 'cdc_id',
      key: 'cdc_id',
      width: 150,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '源类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 100,
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.idle;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '捕获事件',
      key: 'events',
      width: 150,
      render: (_: unknown, record: CDCTask) => (
        <Space size={4}>
          <Tooltip title="INSERT">
            <Tag color="green">{record.insert_events}</Tag>
          </Tooltip>
          <Tooltip title="UPDATE">
            <Tag color="blue">{record.update_events}</Tag>
          </Tooltip>
          <Tooltip title="DELETE">
            <Tag color="red">{record.delete_events}</Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '吞吐量',
      dataIndex: 'throughput_per_second',
      key: 'throughput_per_second',
      width: 100,
      render: (value: number) => `${value.toFixed(1)} evt/s`,
    },
    {
      title: '延迟',
      dataIndex: 'current_lag_ms',
      key: 'current_lag_ms',
      width: 100,
      render: (lag: number) => {
        const lagSeconds = lag / 1000;
        let color: 'success' | 'warning' | 'danger' | 'secondary' = 'success';
        if (lagSeconds > 60) color = 'warning';
        if (lagSeconds > 300) color = 'danger';
        return <Text type={color}>{lagSeconds.toFixed(1)}s</Text>;
      },
    },
    {
      title: '最后捕获',
      dataIndex: 'last_capture_time',
      key: 'last_capture_time',
      width: 160,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: CDCTask) => (
        <Space size="small">
          {record.status === 'idle' || record.status === 'stopped' ? (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.cdc_id)}
            >
              启动
            </Button>
          ) : record.status === 'running' ? (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => stopMutation.mutate(record.cdc_id)}
            >
              停止
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <DatabaseOutlined />
          <span>CDC 增量采集任务</span>
          <Badge count={tasks.length} />
        </Space>
      }
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={onRefresh}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>
            创建任务
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="cdc_id"
        loading={isLoading}
        pagination={{ pageSize: 10 }}
        rowClassName={(record) => record.status === 'error' ? 'error-row' : ''}
      />
    </Card>
  );
};

/**
 * 创建 CDC 任务模态框
 */
const CreateCDCTaskModal: React.FC<{
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [testingConnection, setTestingConnection] = useState(false);

  const testConnectionMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      setTestingConnection(true);
      const res = await fetch('/api/v1/cdc/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      setTestingConnection(false);
      return data;
    },
    onSuccess: (data) => {
      if (data.code === 0) {
        message.success('数据库连接成功');
      } else {
        message.error(`连接失败: ${data.message}`);
      }
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      const res = await fetch('/api/v1/cdc/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      return res.json();
    },
    onSuccess: (data) => {
      if (data.code === 0) {
        message.success('CDC 任务创建成功');
        form.resetFields();
        onClose();
        onSuccess();
      } else {
        message.error(`创建失败: ${data.message}`);
      }
    },
  });

  const handleTestConnection = () => {
    form.validateFields(['source_type', 'host', 'port', 'username', 'password', 'database'])
      .then((values) => {
        testConnectionMutation.mutate(values);
      });
  };

  return (
    <Modal
      title={<Space><PlusOutlined /> 创建 CDC 增量采集任务</Space>}
      open={visible}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      width={700}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => createMutation.mutate(values)}
        initialValues={{
          source_type: 'mysql',
          port: 3306,
          batch_size: 1000,
          snapshot_mode: 'initial',
          include_ddl: false,
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="源类型"
              name="source_type"
              rules={[{ required: true }]}
            >
              <Select options={SOURCE_TYPE_OPTIONS} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="CDC ID"
              name="cdc_id"
              rules={[{ required: true }]}
            >
              <Input placeholder="cdc_mysql_users" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="主机地址"
              name="host"
              rules={[{ required: true }]}
            >
              <Input placeholder="localhost" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="端口"
              name="port"
              rules={[{ required: true }]}
            >
              <InputNumber style={{ width: '100%' }} min={1} max={65535} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="用户名"
              name="username"
              rules={[{ required: true }]}
            >
              <Input placeholder="root" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true }]}
            >
              <Input.Password />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="数据库"
          name="database"
          rules={[{ required: true }]}
        >
          <Input placeholder="business_db" />
        </Form.Item>

        <Form.Item
          label="Schema"
          name="schema"
          extra="PostgreSQL 使用，MySQL 可留空"
        >
          <Input placeholder="public" />
        </Form.Item>

        <Form.Item
          label="监听表"
          name="tables"
          extra="留空表示监听所有表，多个表用逗号分隔"
        >
          <Select
            mode="tags"
            placeholder="users,orders,products"
            tokenSeparators={[',']}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              label="批量大小"
              name="batch_size"
            >
              <InputNumber min={1} max={10000} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              label="快照模式"
              name="snapshot_mode"
            >
              <Select>
                <Select.Option value="initial">初始快照</Select.Option>
                <Select.Option value="schema_only">仅结构</Select.Option>
                <Select.Option value="never">从当前开始</Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              label="包含 DDL"
              name="include_ddl"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item>
          <Button
            block
            icon={<DatabaseOutlined />}
            onClick={handleTestConnection}
            loading={testingConnection}
          >
            测试数据库连接
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
};

/**
 * CDC 事件时间轴
 */
const CDCEventTimeline: React.FC<{ cdcId: string }> = ({ cdcId }) => {
  const { data: eventsData, isLoading } = useQuery({
    queryKey: ['cdc', 'events', cdcId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/cdc/tasks/${cdcId}/events?limit=50`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    refetchInterval: 5000,
  });

  const events = eventsData?.data?.events || [];

  return (
    <Card title="变更事件时间轴" size="small">
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <Spin />
        </div>
      ) : events.length === 0 ? (
        <Empty description="暂无变更事件" />
      ) : (
        <Timeline mode="left">
          {events.map((event: CDCEvent, idx: number) => {
            const config = EVENT_TYPE_CONFIG[event.event_type] || EVENT_TYPE_CONFIG.update;
            return (
              <Timeline.Item
                key={event.event_id}
                dot={config.icon}
                color={config.color}
              >
                <Card size="small" className="cdc-event-card">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Tag color={config.color}>{config.label}</Tag>
                      <Text strong>{event.database}.{event.table}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(event.timestamp * 1000).toLocaleString('zh-CN')}
                      </Text>
                    </Space>

                    {event.old_data && Object.keys(event.old_data).length > 0 && (
                      <div>
                        <Text type="secondary">旧值: </Text>
                        <pre className="event-data">{JSON.stringify(event.old_data, null, 2)}</pre>
                      </div>
                    )}

                    {event.new_data && Object.keys(event.new_data).length > 0 && (
                      <div>
                        <Text type="secondary">新值: </Text>
                        <pre className="event-data">{JSON.stringify(event.new_data, null, 2)}</pre>
                      </div>
                    )}
                  </Space>
                </Card>
              </Timeline.Item>
            );
          })}
        </Timeline>
      )}
    </Card>
  );
};

/**
 * CDC 指标面板
 */
const CDCMetricsPanel: React.FC<{ cdcId: string }> = ({ cdcId }) => {
  const { data: metricsData, isLoading } = useQuery({
    queryKey: ['cdc', 'metrics', cdcId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/cdc/tasks/${cdcId}/metrics`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    refetchInterval: 3000,
  });

  const metrics = metricsData?.data?.metrics;

  if (!metrics) {
    return <Card loading={isLoading} />;
  }

  return (
    <Row gutter={16}>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="捕获事件"
            value={metrics.events_captured}
            valueStyle={{ color: '#1677ff' }}
            prefix={<ThunderboltOutlined />}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="已处理"
            value={metrics.events_processed}
            valueStyle={{ color: '#52c41a' }}
            prefix={<CheckCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="失败事件"
            value={metrics.events_failed}
            valueStyle={{ color: metrics.events_failed > 0 ? '#ff4d4f' : '#52c41a' }}
            prefix={<CloseCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card>
          <Statistic
            title="吞吐量"
            value={metrics.throughput_per_second}
            precision={1}
            suffix="evt/s"
          />
        </Card>
      </Col>
    </Row>
  );
};

/**
 * 主 CDC 管理页面
 */
function CDCManagementPage() {
  const queryClient = useQueryClient();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  return (
    <div className="cdc-management-page">
      <Title level={2}>
        <Space>
          <SyncOutlined />
          CDC 增量数据采集
        </Space>
      </Title>

      <Tabs
        defaultActiveKey="tasks"
        items={[
          {
            key: 'tasks',
            label: '采集任务',
            children: (
              <CDCTaskList
                onCreate={() => setCreateModalVisible(true)}
                onRefresh={() => queryClient.invalidateQueries({ queryKey: ['cdc'] })}
              />
            ),
          },
          {
            key: 'monitoring',
            label: '实时监控',
            children: selectedTaskId ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <CDCMetricsPanel cdcId={selectedTaskId} />
                <CDCEventTimeline cdcId={selectedTaskId} />
              </Space>
            ) : (
              <Empty description="请选择一个 CDC 任务查看监控" />
            ),
          },
        ]}
      />

      <CreateCDCTaskModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['cdc'] })}
      />
    </div>
  );
}

export default CDCManagementPage;
