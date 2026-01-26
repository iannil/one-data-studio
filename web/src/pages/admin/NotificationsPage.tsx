/**
 * 统一通知管理页面
 * 管理通知模板、发送通知、查看发送记录
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
  Badge,
  Tooltip,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SendOutlined,
  ReloadOutlined,
  MailOutlined,
  MessageOutlined,
  BellOutlined,
  WechatOutlined,
  DingdingOutlined,
  ApiOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;

// 通知渠道配置
const CHANNEL_OPTIONS = [
  { value: 'email', label: '邮件', icon: <MailOutlined /> },
  { value: 'sms', label: '短信', icon: <MessageOutlined /> },
  { value: 'dingtalk', label: '钉钉', icon: <DingdingOutlined /> },
  { value: 'wechat_work', label: '企业微信', icon: <WechatOutlined /> },
  { value: 'feishu', label: '飞书', icon: <MessageOutlined /> },
  { value: 'webhook', label: 'Webhook', icon: <ApiOutlined /> },
  { value: 'in_app', label: '站内信', icon: <BellOutlined /> },
];

// 事件类型配置
const EVENT_TYPE_OPTIONS = [
  { value: 'alert', label: '告警通知' },
  { value: 'task_complete', label: '任务完成' },
  { value: 'approval', label: '审批通知' },
  { value: 'system', label: '系统通知' },
  { value: 'user', label: '用户通知' },
  { value: 'data_quality', label: '数据质量' },
  { value: 'etl_status', label: 'ETL状态' },
];

// 类型定义
interface NotificationTemplate {
  id: string;
  name: string;
  description?: string;
  event_type: string;
  channel: string;
  subject_template?: string;
  body_template?: string;
  variables?: Array<{ name: string; type: string; required: boolean; description?: string }>;
  is_enabled: boolean;
  is_default: boolean;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

interface NotificationLog {
  id: string;
  channel: string;
  template_id?: string;
  subject?: string;
  content?: string;
  recipient_type?: string;
  recipient_id?: string;
  recipient_address?: string;
  status: string;
  send_at?: string;
  delivered_at?: string;
  error_message?: string;
  error_code?: string;
  retry_count: number;
  event_type?: string;
  created_at?: string;
}

interface NotificationStats {
  total: number;
  sent_count: number;
  failed_count: number;
  pending_count: number;
  success_rate: number;
  channel_distribution: Record<string, number>;
}

const NotificationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('templates');
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [stats, setStats] = useState<NotificationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [templateModalVisible, setTemplateModalVisible] = useState(false);
  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null);
  const [templateForm] = Form.useForm();
  const [sendForm] = Form.useForm();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  // 获取模板列表
  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/notification-templates');
      const data = await response.json();
      if (data.code === 0) {
        setTemplates(data.data.templates);
        setPagination(prev => ({ ...prev, total: data.data.total }));
      } else {
        message.error(data.message || '获取模板列表失败');
      }
    } catch (error) {
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 获取发送日志
  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/notification-logs?page=${pagination.current}&page_size=${pagination.pageSize}`);
      const data = await response.json();
      if (data.code === 0) {
        setLogs(data.data.logs);
        setPagination(prev => ({ ...prev, total: data.data.total }));
      } else {
        message.error(data.message || '获取日志列表失败');
      }
    } catch (error) {
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 获取统计数据
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/notification-logs/statistics');
      const data = await response.json();
      if (data.code === 0) {
        setStats(data.data);
      }
    } catch (error) {
      console.error('获取统计数据失败', error);
    }
  };

  useEffect(() => {
    fetchTemplates();
    fetchStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
  }, [activeTab, pagination.current, pagination.pageSize]);

  // 创建/更新模板
  const handleSaveTemplate = async (values: any) => {
    try {
      const url = editingTemplate
        ? `/api/v1/notification-templates/${editingTemplate.id}`
        : '/api/v1/notification-templates';
      const method = editingTemplate ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success(editingTemplate ? '更新成功' : '创建成功');
        setTemplateModalVisible(false);
        templateForm.resetFields();
        setEditingTemplate(null);
        fetchTemplates();
      } else {
        message.error(data.message || '操作失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 删除模板
  const handleDeleteTemplate = async (templateId: string) => {
    try {
      const response = await fetch(`/api/v1/notification-templates/${templateId}`, {
        method: 'DELETE',
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success('删除成功');
        fetchTemplates();
      } else {
        message.error(data.message || '删除失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 发送通知
  const handleSendNotification = async (values: any) => {
    try {
      const response = await fetch('/api/v1/notifications/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...values,
          recipients: values.recipients.split(',').map((r: string) => r.trim()),
        }),
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success(`发送完成：成功 ${data.data.success_count}/${data.data.total}`);
        setSendModalVisible(false);
        sendForm.resetFields();
        fetchLogs();
        fetchStats();
      } else {
        message.error(data.message || '发送失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 重试发送
  const handleRetry = async (logId: string) => {
    try {
      const response = await fetch(`/api/v1/notification-logs/${logId}/retry`, {
        method: 'POST',
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success(data.data.success ? '重试成功' : '重试失败');
        fetchLogs();
        fetchStats();
      } else {
        message.error(data.message || '重试失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 模板表格列
  const templateColumns: ColumnsType<NotificationTemplate> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: '事件类型',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type) => {
        const option = EVENT_TYPE_OPTIONS.find(o => o.value === type);
        return <Tag>{option?.label || type}</Tag>;
      },
    },
    {
      title: '渠道',
      dataIndex: 'channel',
      key: 'channel',
      render: (channel) => {
        const option = CHANNEL_OPTIONS.find(o => o.value === channel);
        return (
          <Space>
            {option?.icon}
            {option?.label || channel}
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? '启用' : '禁用'} />
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingTemplate(record);
              templateForm.setFieldsValue(record);
              setTemplateModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此模板吗？"
            onConfirm={() => handleDeleteTemplate(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 日志表格列
  const logColumns: ColumnsType<NotificationLog> = [
    {
      title: '接收方',
      dataIndex: 'recipient_address',
      key: 'recipient_address',
      ellipsis: true,
    },
    {
      title: '渠道',
      dataIndex: 'channel',
      key: 'channel',
      render: (channel) => {
        const option = CHANNEL_OPTIONS.find(o => o.value === channel);
        return (
          <Space>
            {option?.icon}
            {option?.label || channel}
          </Space>
        );
      },
    },
    {
      title: '标题',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig: Record<string, { color: string; text: string }> = {
          pending: { color: 'default', text: '待发送' },
          sending: { color: 'processing', text: '发送中' },
          sent: { color: 'success', text: '已发送' },
          delivered: { color: 'success', text: '已送达' },
          failed: { color: 'error', text: '失败' },
        };
        const config = statusConfig[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 80,
    },
    {
      title: '发送时间',
      dataIndex: 'send_at',
      key: 'send_at',
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (error) => error ? (
        <Tooltip title={error}>
          <Text type="danger" ellipsis>{error}</Text>
        </Tooltip>
      ) : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'failed' && record.retry_count < 3 && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetry(record.id)}
            >
              重试
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <BellOutlined style={{ marginRight: 8 }} />
            统一通知管理
          </Title>
          <Space>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => setSendModalVisible(true)}
            >
              发送通知
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingTemplate(null);
                templateForm.resetFields();
                setTemplateModalVisible(true);
              }}
            >
              新建模板
            </Button>
          </Space>
        </div>

        {/* 统计卡片 */}
        {stats && (
          <>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="总发送量" value={stats.total} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="发送成功"
                    value={stats.sent_count}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="发送失败"
                    value={stats.failed_count}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="成功率"
                    value={stats.success_rate}
                    suffix="%"
                    precision={2}
                  />
                </Card>
              </Col>
            </Row>
            <Divider />
          </>
        )}

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="通知模板" key="templates">
            <Table
              columns={templateColumns}
              dataSource={templates}
              rowKey="id"
              loading={loading}
              pagination={{
                ...pagination,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
              }}
            />
          </TabPane>
          <TabPane tab={<span><HistoryOutlined /> 发送记录</span>} key="logs">
            <Table
              columns={logColumns}
              dataSource={logs}
              rowKey="id"
              loading={loading}
              pagination={{
                ...pagination,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 模板编辑弹窗 */}
      <Modal
        title={editingTemplate ? '编辑通知模板' : '新建通知模板'}
        open={templateModalVisible}
        onCancel={() => {
          setTemplateModalVisible(false);
          setEditingTemplate(null);
          templateForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={templateForm}
          layout="vertical"
          onFinish={handleSaveTemplate}
          initialValues={{ is_enabled: true, is_default: false }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="模板名称"
                rules={[{ required: true, message: '请输入模板名称' }]}
              >
                <Input placeholder="请输入模板名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="event_type"
                label="事件类型"
                rules={[{ required: true, message: '请选择事件类型' }]}
              >
                <Select placeholder="请选择事件类型" options={EVENT_TYPE_OPTIONS} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="channel"
                label="通知渠道"
                rules={[{ required: true, message: '请选择通知渠道' }]}
              >
                <Select
                  placeholder="请选择通知渠道"
                  options={CHANNEL_OPTIONS.map(o => ({ value: o.value, label: <Space>{o.icon}{o.label}</Space> }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_enabled" label="启用状态" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_default" label="默认模板" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="模板描述">
            <TextArea rows={2} placeholder="请输入模板描述" />
          </Form.Item>
          <Form.Item name="subject_template" label="标题模板">
            <Input placeholder="支持变量: {{variable_name}}" />
          </Form.Item>
          <Form.Item
            name="body_template"
            label="内容模板"
            rules={[{ required: true, message: '请输入内容模板' }]}
          >
            <TextArea rows={6} placeholder="支持变量: {{variable_name}}" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => {
                setTemplateModalVisible(false);
                setEditingTemplate(null);
                templateForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 发送通知弹窗 */}
      <Modal
        title="发送通知"
        open={sendModalVisible}
        onCancel={() => {
          setSendModalVisible(false);
          sendForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={sendForm} layout="vertical" onFinish={handleSendNotification}>
          <Form.Item
            name="channel"
            label="通知渠道"
            rules={[{ required: true, message: '请选择通知渠道' }]}
          >
            <Select
              placeholder="请选择通知渠道"
              options={CHANNEL_OPTIONS.map(o => ({ value: o.value, label: <Space>{o.icon}{o.label}</Space> }))}
            />
          </Form.Item>
          <Form.Item
            name="recipients"
            label="接收方"
            rules={[{ required: true, message: '请输入接收方' }]}
            extra="多个接收方用逗号分隔"
          >
            <Input placeholder="请输入接收方地址（邮箱/手机号/Webhook地址）" />
          </Form.Item>
          <Form.Item name="template_id" label="使用模板">
            <Select
              placeholder="选择模板（可选）"
              allowClear
              options={templates
                .filter(t => t.is_enabled)
                .map(t => ({ value: t.id, label: `${t.name} (${t.event_type})` }))}
            />
          </Form.Item>
          <Form.Item name="subject" label="通知标题">
            <Input placeholder="请输入通知标题" />
          </Form.Item>
          <Form.Item
            name="content"
            label="通知内容"
            rules={[{ required: true, message: '请输入通知内容' }]}
          >
            <TextArea rows={4} placeholder="请输入通知内容" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SendOutlined />}>
                发送
              </Button>
              <Button onClick={() => {
                setSendModalVisible(false);
                sendForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default NotificationsPage;
