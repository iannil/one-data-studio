/**
 * Kafka 流式数据采集页面
 * 支持 Kafka 消费者管理、实时消息预览和指标监控
 */

import { useState, useEffect } from 'react';
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
  Tooltip,
  Switch,
  Tabs,
  Descriptions,
  Timeline,
  Empty,
  Spin,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  LineChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import './KafkaStreamingPage.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface KafkaConsumer {
  consumer_id: string;
  status: string;
  messages_consumed: number;
  messages_processed: number;
  messages_failed: number;
  bytes_consumed: number;
  last_offset: Record<string, number>;
  current_lag: Record<string, number>;
  last_message_time: string;
  connection_time: string;
  error_message?: string;
  avg_processing_time_ms: number;
}

interface KafkaMessage {
  topic: string;
  partition: number;
  offset: number;
  key: string | null;
  value: unknown;
  timestamp: number;
  processed: boolean;
  error?: string;
}

interface ConsumerConfig {
  bootstrap_servers: string;
  group_id: string;
  topics: string[];
  auto_offset_reset: string;
  enable_auto_commit: boolean;
  max_poll_records: number;
}

const STATUS_COLORS: Record<string, string> = {
  idle: 'default',
  connecting: 'processing',
  connected: 'blue',
  consuming: 'success',
  paused: 'warning',
  error: 'error',
  stopped: 'default',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  idle: <ClockCircleOutlined />,
  connecting: <LoadingOutlined />,
  connected: <CheckCircleOutlined />,
  consuming: <ThunderboltOutlined />,
  paused: <PauseCircleOutlined />,
  error: <CloseCircleOutlined />,
  stopped: <StopOutlined />,
};

/**
 * Kafka 消费者列表组件
 */
const KafkaConsumerList: React.FC<{
  onCreate: () => void;
  onRefresh: () => void;
}> = ({ onCreate, onRefresh }) => {
  const queryClient = useQueryClient();
  const [selectedConsumerId, setSelectedConsumerId] = useState<string | null>(null);

  const { data: consumersData, isLoading, refetch } = useQuery({
    queryKey: ['kafka', 'consumers'],
    queryFn: async () => {
      const res = await fetch('/api/v1/streaming/kafka/consumers', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    refetchInterval: 5000, // 每5秒自动刷新
  });

  const startMutation = useMutation({
    mutationFn: async (consumerId: string) => {
      const res = await fetch(`/api/v1/streaming/kafka/consumers/${consumerId}/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('消费者启动成功');
      queryClient.invalidateQueries({ queryKey: ['kafka', 'consumers'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: async (consumerId: string) => {
      const res = await fetch(`/api/v1/streaming/kafka/consumers/${consumerId}/pause`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('消费者已暂停');
      refetch();
    },
  });

  const resumeMutation = useMutation({
    mutationFn: async (consumerId: string) => {
      const res = await fetch(`/api/v1/streaming/kafka/consumers/${consumerId}/resume`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('消费者已恢复');
      refetch();
    },
  });

  const stopMutation = useMutation({
    mutationFn: async (consumerId: string) => {
      const res = await fetch(`/api/v1/streaming/kafka/consumers/${consumerId}/stop`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('消费者已停止');
      refetch();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (consumerId: string) => {
      const res = await fetch(`/api/v1/streaming/kafka/consumers/${consumerId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return res.json();
    },
    onSuccess: () => {
      message.success('消费者已删除');
      queryClient.invalidateQueries({ queryKey: ['kafka', 'consumers'] });
    },
  });

  const consumers = consumersData?.data?.consumers || [];

  const columns = [
    {
      title: 'Consumer ID',
      dataIndex: 'consumer_id',
      key: 'consumer_id',
      width: 200,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || 'default'} icon={STATUS_ICONS[status]}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '已消费',
      dataIndex: 'messages_consumed',
      key: 'messages_consumed',
      width: 100,
      render: (count: number) => <Text strong>{count.toLocaleString()}</Text>,
    },
    {
      title: '已处理',
      dataIndex: 'messages_processed',
      key: 'messages_processed',
      width: 100,
      render: (count: number) => <Text type="success">{count.toLocaleString()}</Text>,
    },
    {
      title: '失败',
      dataIndex: 'messages_failed',
      key: 'messages_failed',
      width: 80,
      render: (count: number) => count > 0 ? <Text type="danger">{count}</Text> : '-',
    },
    {
      title: '平均处理时间',
      dataIndex: 'avg_processing_time_ms',
      key: 'avg_processing_time_ms',
      width: 120,
      render: (ms: number) => `${ms.toFixed(2)} ms`,
    },
    {
      title: '连接时间',
      dataIndex: 'connection_time',
      key: 'connection_time',
      width: 160,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: unknown, record: KafkaConsumer) => (
        <Space size="small">
          {record.status === 'idle' || record.status === 'stopped' ? (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.consumer_id)}
            >
              启动
            </Button>
          ) : record.status === 'consuming' ? (
            <>
              <Button
                size="small"
                icon={<PauseCircleOutlined />}
                onClick={() => pauseMutation.mutate(record.consumer_id)}
              />
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => stopMutation.mutate(record.consumer_id)}
              />
            </>
          ) : record.status === 'paused' ? (
            <Button
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => resumeMutation.mutate(record.consumer_id)}
            >
              恢复
            </Button>
          ) : null}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setSelectedConsumerId(record.consumer_id)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <DatabaseOutlined />
          <span>Kafka 消费者列表</span>
          <Badge count={consumers.length} />
        </Space>
      }
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>
            创建消费者
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={consumers}
        rowKey="consumer_id"
        loading={isLoading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 1200 }}
        rowSelection={{
          type: 'checkbox',
          selectedRowKeys: selectedConsumerId ? [selectedConsumerId] : [],
          onChange: (keys) => setSelectedConsumerId(keys[0] as string || null),
        }}
      />
    </Card>
  );
};

/**
 * 创建消费者模态框
 */
const CreateConsumerModal: React.FC<{
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [testingConnection, setTestingConnection] = useState(false);

  const { data: connectionResult, mutate: testConnection } = useMutation({
    mutationFn: async (bootstrapServers: string) => {
      setTestingConnection(true);
      const res = await fetch('/api/v1/streaming/kafka/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ bootstrap_servers: bootstrapServers }),
      });
      const data = await res.json();
      setTestingConnection(false);
      return data;
    },
    onSuccess: (data) => {
      if (data.code === 0) {
        message.success('Kafka 连接成功');
      } else {
        message.error(`连接失败: ${data.message}`);
      }
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: ConsumerConfig) => {
      const res = await fetch('/api/v1/streaming/kafka/consumers', {
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
        message.success('消费者创建成功');
        form.resetFields();
        onClose();
        onSuccess();
      } else {
        message.error(`创建失败: ${data.message}`);
      }
    },
  });

  const handleTestConnection = async () => {
    const bootstrapServers = form.getFieldValue('bootstrap_servers');
    if (bootstrapServers) {
      testConnection(bootstrapServers);
    } else {
      message.warning('请先输入 Kafka 服务器地址');
    }
  };

  return (
    <Modal
      title={<Space><PlusOutlined /> 创建 Kafka 消费者</Space>}
      open={visible}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => createMutation.mutate(values)}
        initialValues={{
          auto_offset_reset: 'latest',
          enable_auto_commit: true,
          max_poll_records: 500,
        }}
      >
        <Form.Item
          label="Bootstrap Servers"
          name="bootstrap_servers"
          rules={[{ required: true, message: '请输入 Kafka 服务器地址' }]}
          extra="例如: localhost:9092 或 192.168.1.100:9092,192.168.1.101:9092"
        >
          <Input
            placeholder="localhost:9092"
            addonAfter={
              <Button
                size="small"
                type="link"
                loading={testingConnection}
                onClick={handleTestConnection}
              >
                测试连接
              </Button>
            }
          />
        </Form.Item>

        <Form.Item
          label="Group ID"
          name="group_id"
          rules={[{ required: true, message: '请输入消费者组 ID' }]}
        >
          <Input placeholder="data-consumer-group" />
        </Form.Item>

        <Form.Item
          label="Topics"
          name="topics"
          rules={[{ required: true, message: '请输入订阅的 Topic' }]}
          extra="多个 Topic 用逗号分隔"
        >
          <Select
            mode="tags"
            placeholder="输入 Topic 名称"
            tokenSeparators={[',']}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Offset 重置策略"
              name="auto_offset_reset"
            >
              <Select>
                <Select.Option value="latest">latest (最新)</Select.Option>
                <Select.Option value="earliest">earliest (最早)</Select.Option>
                <Select.Option value="none">none (无)</Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="最大拉取数"
              name="max_poll_records"
            >
              <Input type="number" min={1} max={10000} />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="自动提交"
          name="enable_auto_commit"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

/**
 * 消息预览组件
 */
const MessagePreview: React.FC<{
  consumerId: string;
  visible: boolean;
  onClose: () => void;
}> = ({ consumerId, visible, onClose }) => {
  const [clearAfterFetch, setClearAfterFetch] = useState(false);

  const { data: messagesData, isLoading, refetch } = useQuery({
    queryKey: ['kafka', 'messages', consumerId, clearAfterFetch],
    queryFn: async () => {
      // 获取消费者详情以获取 topics
      const consumerRes = await fetch('/api/v1/streaming/kafka/consumers', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const consumerData = await consumerRes.json();
      const consumer = consumerData.data?.consumers?.find((c: KafkaConsumer) => c.consumer_id === consumerId);

      if (consumer) {
        // 从第一个 topic 获取消息
        const topics = Object.keys(consumer.last_offset || {});
        if (topics.length > 0) {
          const topic = topics[0];
          const res = await fetch(
            `/api/v1/streaming/kafka/topics/${topic}/messages?limit=100&clear=${clearAfterFetch}`,
            {
              headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            }
          );
          return res.json();
        }
      }
      return { data: { messages: [], count: 0 } };
    },
    enabled: visible,
    refetchInterval: 3000,
  });

  const messages = messagesData?.data?.messages || [];

  const formatMessage = (msg: KafkaMessage) => {
    try {
      return typeof msg.value === 'string' ? msg.value : JSON.stringify(msg.value, null, 2);
    } catch {
      return String(msg.value);
    }
  };

  return (
    <Modal
      title={<Space><EyeOutlined /> 消息预览</Space>}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Space key="footer">
          <Switch
            checked={clearAfterFetch}
            onChange={(checked) => setClearAfterFetch(checked)}
            checkedChildren="获取后清空"
            unCheckedChildren="保留消息"
          />
          <Button onClick={() => refetch()}>
            刷新
          </Button>
          <Button type="primary" onClick={onClose}>
            关闭
          </Button>
        </Space>,
      ]}
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : messages.length === 0 ? (
        <Empty description="暂无消息" />
      ) : (
        <div className="kafka-messages-preview">
          {messages.map((msg: KafkaMessage, idx: number) => (
            <div key={idx} className="kafka-message-item">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Tag color="blue">{msg.topic}</Tag>
                  <Text type="secondary">分区: {msg.partition}</Text>
                  <Text type="secondary">偏移: {msg.offset}</Text>
                  {msg.key && <Text code>{msg.key}</Text>}
                  <Tag color={msg.processed ? 'success' : 'default'}>
                    {msg.processed ? '已处理' : '未处理'}
                  </Tag>
                  {msg.error && <Tag color="error">{msg.error}</Tag>}
                </Space>
                <pre className="message-content">
                  <code>{formatMessage(msg)}</code>
                </pre>
              </Space>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
};

/**
 * 主 Kafka 流式数据页面
 */
function KafkaStreamingPage() {
  const queryClient = useQueryClient();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [previewConsumerId, setPreviewConsumerId] = useState<string | null>(null);

  return (
    <div className="kafka-streaming-page">
      <Title level={2}>
        <Space>
          <ThunderboltOutlined />
          Kafka 流式数据采集
        </Space>
      </Title>

      <Tabs
        defaultActiveKey="consumers"
        items={[
          {
            key: 'consumers',
            label: '消费者管理',
            children: (
              <KafkaConsumerList
                onCreate={() => setCreateModalVisible(true)}
                onRefresh={() => queryClient.invalidateQueries({ queryKey: ['kafka'] })}
              />
            ),
          },
          {
            key: 'monitoring',
            label: '实时监控',
            children: (
              <Card title="消费者指标监控">
                <Alert
                  message="实时监控"
                  description="消费者指标每5秒自动刷新"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <KafkaConsumerList
                  onCreate={() => setCreateModalVisible(true)}
                  onRefresh={() => queryClient.invalidateQueries({ queryKey: ['kafka'] })}
                />
              </Card>
            ),
          },
        ]}
      />

      <CreateConsumerModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['kafka', 'consumers'] })}
      />

      {previewConsumerId && (
        <MessagePreview
          consumerId={previewConsumerId}
          visible={!!previewConsumerId}
          onClose={() => setPreviewConsumerId(null)}
        />
      )}
    </div>
  );
}

export default KafkaStreamingPage;
