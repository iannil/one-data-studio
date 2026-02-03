/**
 * 统一通知管理组件
 * 管理通知渠道、模板、规则和历史记录
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
  Switch,
  Tag,
  Space,
  Typography,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Progress,
  Alert,
  Divider,
  Upload,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SendOutlined,
  CheckOutlined,
  CloseOutlined,
  ReloadOutlined,
  BellOutlined,
  MailOutlined,
  MessageOutlined,
  ApiOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getNotificationChannels,
  getNotificationTemplates,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate,
  getNotificationRules,
  createNotificationRule,
  updateNotificationRule,
  deleteNotificationRule,
  enableNotificationRule,
  disableNotificationRule,
  sendNotification,
  sendNotificationByTemplate,
  triggerNotificationEvent,
  getNotificationHistory,
  getNotificationStatistics,
  type NotificationTemplate,
  type NotificationRule,
  type NotificationHistoryItem,
  type SendNotificationRequest,
} from '@/services/data';
import './NotificationCenter.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface NotificationCenterProps {
  className?: string;
}

/**
 * 渠道管理标签页
 */
const ChannelsTab: React.FC = () => {
  const { data: channelsData, isLoading } = useQuery({
    queryKey: ['notifications', 'channels'],
    queryFn: async () => {
      const res = await getNotificationChannels();
      return res.data;
    },
  });

  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'email':
        return <MailOutlined />;
      case 'sms':
        return <MessageOutlined />;
      case 'webhook':
        return <ApiOutlined />;
      case 'inapp':
        return <AppstoreOutlined />;
      default:
        return <BellOutlined />;
    }
  };

  const getChannelName = (type: string) => {
    const names: Record<string, string> = {
      email: '邮件通知',
      sms: '短信通知',
      webhook: 'Webhook',
      inapp: '应用内通知',
    };
    return names[type] || type;
  };

  return (
    <Card title="通知渠道" className="channels-card">
      <Alert
        message="渠道管理"
        description="系统已预配置多种通知渠道，可在系统设置中配置 SMTP、短信服务商等信息。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        {channelsData?.channels.map((channel) => (
          <Col key={channel.type} xs={24} sm={12} md={8}>
            <Card
              size="small"
              className={`channel-card ${channel.enabled ? 'enabled' : 'disabled'}`}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <span className="channel-icon">{getChannelIcon(channel.type)}</span>
                  <span className="channel-name">{getChannelName(channel.type)}</span>
                </Space>
                <Tag color={channel.enabled ? 'success' : 'default'}>
                  {channel.enabled ? '已启用' : '已禁用'}
                </Tag>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

/**
 * 模板表单对话框
 */
const TemplateFormModal: React.FC<{
  visible: boolean;
  template?: NotificationTemplate;
  onCancel: () => void;
  onOk: (values: Record<string, unknown>) => void;
  loading?: boolean;
}> = ({ visible, template, onCancel, onOk, loading }) => {
  const [form] = Form.useForm();

  React.useEffect(() => {
    if (visible) {
      if (template) {
        form.setFieldsValue(template);
      } else {
        form.resetFields();
      }
    }
  }, [visible, template, form]);

  return (
    <Modal
      title={template ? '编辑通知模板' : '创建通知模板'}
      open={visible}
      onCancel={onCancel}
      onOk={() => form.validateFields().then(onOk)}
      confirmLoading={loading}
      width={700}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label="模板名称"
          rules={[{ required: true, message: '请输入模板名称' }]}
        >
          <Input placeholder="例如：系统告警通知" />
        </Form.Item>

        <Form.Item
          name="description"
          label="模板描述"
        >
          <Input.TextArea rows={2} placeholder="描述该模板的用途..." />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="type"
              label="通知类型"
              initialValue="info"
            >
              <Select>
                <Option value="info">信息</Option>
                <Option value="success">成功</Option>
                <Option value="warning">警告</Option>
                <Option value="error">错误</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="enabled"
              label="启用状态"
              initialValue={true}
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="subject_template"
          label="主题模板"
          rules={[{ required: true, message: '请输入主题模板' }]}
          extra="使用 {variable_name} 格式插入变量"
        >
          <Input placeholder="例如：【系统告警】{alert_title}" />
        </Form.Item>

        <Form.Item
          name="body_template"
          label="内容模板"
          rules={[{ required: true, message: '请输入内容模板' }]}
        >
          <TextArea
            rows={6}
            placeholder="例如：检测到系统告警：&#10;&#10;告警类型：{alert_type}&#10;告警级别：{severity}"
          />
        </Form.Item>

        <Form.Item
          name="supported_channels"
          label="支持的渠道"
          initialValue={['inapp']}
        >
          <Select mode="multiple" placeholder="选择支持的通知渠道">
            <Option value="email">邮件</Option>
            <Option value="sms">短信</Option>
            <Option value="webhook">Webhook</Option>
            <Option value="inapp">应用内</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="variables"
          label="模板变量"
          extra="输入变量名，用逗号分隔"
        >
          <Input placeholder="例如：alert_title, alert_type, severity, details" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

/**
 * 模板管理标签页
 */
const TemplatesTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | undefined>();

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: async () => {
      const res = await getNotificationTemplates();
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: createNotificationTemplate,
    onSuccess: () => {
      message.success('模板创建成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['notifications', 'templates'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationTemplate> }) =>
      updateNotificationTemplate(id, data),
    onSuccess: () => {
      message.success('模板更新成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['notifications', 'templates'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteNotificationTemplate,
    onSuccess: () => {
      message.success('模板删除成功');
      queryClient.invalidateQueries({ queryKey: ['notifications', 'templates'] });
    },
  });

  const handleCreate = () => {
    setEditingTemplate(undefined);
    setModalVisible(true);
  };

  const handleEdit = (template: NotificationTemplate) => {
    setEditingTemplate(template);
    setModalVisible(true);
  };

  const handleDelete = (templateId: string) => {
    deleteMutation.mutate(templateId);
  };

  const handleSubmit = (values: Record<string, unknown>) => {
    const variablesStr = values.variables as string | undefined;
    const data = {
      ...values,
      variables: variablesStr ? variablesStr.split(',').map((v: string) => v.trim()) : [],
    };

    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.template_id, data });
    } else {
      createMutation.mutate(data as Parameters<typeof createMutation.mutate>[0]);
    }
  };

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: NotificationTemplate) => (
        <Space>
          <span>{name}</span>
          {!record.enabled && <Tag color="default">已禁用</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (type: string) => {
        const colors: Record<string, string> = {
          info: 'blue',
          success: 'green',
          warning: 'orange',
          error: 'red',
        };
        return <Tag color={colors[type]}>{type}</Tag>;
      },
    },
    {
      title: '支持渠道',
      dataIndex: 'supported_channels',
      key: 'supported_channels',
      width: 150,
      render: (channels: string[]) => (
        <Space size={4} wrap>
          {channels.map((ch) => (
            <Tag key={ch} color="default">{ch}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '主题预览',
      dataIndex: 'subject_template',
      key: 'subject_template',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: NotificationTemplate) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此模板？"
            onConfirm={() => handleDelete(record.template_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title="通知模板"
        className="templates-card"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建模板
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={templatesData?.templates || []}
          rowKey="template_id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <TemplateFormModal
        visible={modalVisible}
        template={editingTemplate}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />
    </>
  );
};

/**
 * 规则表单对话框
 */
const RuleFormModal: React.FC<{
  visible: boolean;
  rule?: NotificationRule;
  templates: NotificationTemplate[];
  onCancel: () => void;
  onOk: (values: Record<string, unknown>) => void;
  loading?: boolean;
}> = ({ visible, rule, templates, onCancel, onOk, loading }) => {
  const [form] = Form.useForm();

  React.useEffect(() => {
    if (visible) {
      if (rule) {
        form.setFieldsValue({
          ...rule,
          recipients_str: rule.recipients.join(','),
        });
      } else {
        form.resetFields();
      }
    }
  }, [visible, rule, form]);

  return (
    <Modal
      title={rule ? '编辑通知规则' : '创建通知规则'}
      open={visible}
      onCancel={onCancel}
      onOk={() => form.validateFields().then(onOk)}
      confirmLoading={loading}
      width={700}
    >
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="name"
              label="规则名称"
              rules={[{ required: true, message: '请输入规则名称' }]}
            >
              <Input placeholder="例如：数据质量告警规则" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="enabled"
              label="启用状态"
              initialValue={true}
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="description"
          label="规则描述"
        >
          <Input placeholder="描述该规则的用途..." />
        </Form.Item>

        <Form.Item
          name="event_type"
          label="触发事件类型"
          rules={[{ required: true, message: '请输入事件类型' }]}
          extra="系统事件类型，如 data.quality.issue、task.failed 等"
        >
          <Input placeholder="例如：data.quality.issue" />
        </Form.Item>

        <Form.Item
          name="template_id"
          label="使用模板"
          rules={[{ required: true, message: '请选择通知模板' }]}
        >
          <Select placeholder="选择通知模板">
            {templates.map((tpl) => (
              <Option key={tpl.template_id} value={tpl.template_id}>
                {tpl.name} - {tpl.description}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="channels"
          label="通知渠道"
          rules={[{ required: true, message: '请选择通知渠道' }]}
          initialValue={['inapp']}
        >
          <Select mode="multiple" placeholder="选择通知渠道">
            <Option value="email">邮件</Option>
            <Option value="sms">短信</Option>
            <Option value="webhook">Webhook</Option>
            <Option value="inapp">应用内</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="recipients_str"
          label="接收者"
          rules={[{ required: true, message: '请输入接收者' }]}
          extra="用户ID、邮箱或手机号，用逗号分隔"
        >
          <TextArea rows={2} placeholder="例如：user1@example.com, user2@example.com" />
        </Form.Item>

        <Form.Item
          name="throttle_minutes"
          label="限流间隔（分钟）"
          initialValue={60}
          extra="相同接收者最小发送间隔"
        >
          <Input type="number" min={1} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

/**
 * 规则管理标签页
 */
const RulesTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<NotificationRule | undefined>();

  const { data: templatesData } = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: async () => {
      const res = await getNotificationTemplates();
      return res.data;
    },
  });

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['notifications', 'rules'],
    queryFn: async () => {
      const res = await getNotificationRules();
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: createNotificationRule,
    onSuccess: () => {
      message.success('规则创建成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['notifications', 'rules'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationRule> }) =>
      updateNotificationRule(id, data),
    onSuccess: () => {
      message.success('规则更新成功');
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['notifications', 'rules'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteNotificationRule,
    onSuccess: () => {
      message.success('规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['notifications', 'rules'] });
    },
  });

  const enableMutation = useMutation({
    mutationFn: enableNotificationRule,
    onSuccess: () => {
      message.success('规则已启用');
      queryClient.invalidateQueries({ queryKey: ['notifications', 'rules'] });
    },
  });

  const disableMutation = useMutation({
    mutationFn: disableNotificationRule,
    onSuccess: () => {
      message.success('规则已禁用');
      queryClient.invalidateQueries({ queryKey: ['notifications', 'rules'] });
    },
  });

  const handleCreate = () => {
    setEditingRule(undefined);
    setModalVisible(true);
  };

  const handleEdit = (rule: NotificationRule) => {
    setEditingRule(rule);
    setModalVisible(true);
  };

  const handleDelete = (ruleId: string) => {
    deleteMutation.mutate(ruleId);
  };

  const handleToggle = (rule: NotificationRule) => {
    if (rule.enabled) {
      disableMutation.mutate(rule.rule_id);
    } else {
      enableMutation.mutate(rule.rule_id);
    }
  };

  const handleSubmit = (values: Record<string, unknown>) => {
    const recipientsStr = values.recipients_str as string | undefined;
    const data = {
      ...values,
      recipients: recipientsStr ? recipientsStr.split(',').map((v: string) => v.trim()) : [],
    };

    if (editingRule) {
      updateMutation.mutate({ id: editingRule.rule_id, data });
    } else {
      createMutation.mutate(data as Parameters<typeof createMutation.mutate>[0]);
    }
  };

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: NotificationRule) => (
        <Space>
          <span>{name}</span>
          <Tag color={record.enabled ? 'success' : 'default'}>
            {record.enabled ? '已启用' : '已禁用'}
          </Tag>
        </Space>
      ),
    },
    {
      title: '触发事件',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '使用模板',
      dataIndex: 'template_id',
      key: 'template_id',
    },
    {
      title: '通知渠道',
      dataIndex: 'channels',
      key: 'channels',
      render: (channels: string[]) => (
        <Space size={4} wrap>
          {channels.map((ch) => (
            <Tag key={ch} color="default">{ch}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '接收者',
      dataIndex: 'recipients',
      key: 'recipients',
      ellipsis: true,
      render: (recipients: string[]) => recipients.join(', '),
    },
    {
      title: '限流',
      dataIndex: 'throttle_minutes',
      key: 'throttle_minutes',
      width: 80,
      render: (minutes: number) => `${minutes}分钟`,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: NotificationRule) => (
        <Space size="small">
          <Button
            size="small"
            icon={record.enabled ? <CloseOutlined /> : <CheckOutlined />}
            onClick={() => handleToggle(record)}
          >
            {record.enabled ? '禁用' : '启用'}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此规则？"
            onConfirm={() => handleDelete(record.rule_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title="通知规则"
        className="rules-card"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建规则
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={rulesData?.rules || []}
          rowKey="rule_id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <RuleFormModal
        visible={modalVisible}
        rule={editingRule}
        templates={templatesData?.templates || []}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />
    </>
  );
};

/**
 * 发送通知对话框
 */
const SendNotificationModal: React.FC<{
  visible: boolean;
  onCancel: () => void;
  templates?: NotificationTemplate[];
}> = ({ visible, onCancel, templates }) => {
  const [form] = Form.useForm();
  const [useTemplate, setUseTemplate] = useState(false);

  const sendMutation = useMutation({
    mutationFn: sendNotification,
    onSuccess: () => {
      message.success('通知发送成功');
      onCancel();
      form.resetFields();
    },
  });

  const sendByTemplateMutation = useMutation({
    mutationFn: sendNotificationByTemplate,
    onSuccess: () => {
      message.success('通知发送成功');
      onCancel();
      form.resetFields();
    },
  });

  React.useEffect(() => {
    if (visible) {
      form.resetFields();
      setUseTemplate(false);
    }
  }, [visible, form]);

  const handleOk = () => {
    form.validateFields().then((values) => {
      const data = {
        ...values,
        recipients: values.recipients.split(',').map((v: string) => v.trim()),
      };

      if (useTemplate && values.template_id) {
        sendByTemplateMutation.mutate({
          template_id: values.template_id,
          variables: values.variables || {},
          recipients: data.recipients,
          channels: values.channels,
          action_url: values.action_url,
        });
      } else {
        sendMutation.mutate(data);
      }
    });
  };

  return (
    <Modal
      title="发送通知"
      open={visible}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={sendMutation.isPending || sendByTemplateMutation.isPending}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item>
          <Switch
            checkedChildren="使用模板"
            unCheckedChildren="直接发送"
            checked={useTemplate}
            onChange={setUseTemplate}
          />
        </Form.Item>

        {useTemplate ? (
          <>
            <Form.Item
              name="template_id"
              label="选择模板"
              rules={[{ required: true, message: '请选择模板' }]}
            >
              <Select placeholder="选择通知模板">
                {templates?.map((tpl) => (
                  <Option key={tpl.template_id} value={tpl.template_id}>
                    {tpl.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item label="模板变量（JSON）">
              <Form.Item name="variables" noStyle>
                <TextArea
                  rows={3}
                  placeholder='{"alert_title": "测试告警", "severity": "high"}'
                />
              </Form.Item>
            </Form.Item>
          </>
        ) : (
          <>
            <Form.Item
              name="subject"
              label="通知主题"
              rules={[{ required: !useTemplate, message: '请输入主题' }]}
            >
              <Input placeholder="通知主题" />
            </Form.Item>
            <Form.Item
              name="body"
              label="通知内容"
              rules={[{ required: !useTemplate, message: '请输入内容' }]}
            >
              <TextArea rows={4} placeholder="通知内容" />
            </Form.Item>
          </>
        )}

        <Form.Item
          name="recipients"
          label="接收者"
          rules={[{ required: true, message: '请输入接收者' }]}
          extra="邮箱、手机号或用户ID，用逗号分隔"
        >
          <TextArea rows={2} placeholder="user1@example.com, user2@example.com" />
        </Form.Item>

        <Form.Item
          name="channels"
          label="发送渠道"
          rules={[{ required: true, message: '请选择渠道' }]}
          initialValue={['inapp']}
        >
          <Select mode="multiple" placeholder="选择通知渠道">
            <Option value="email">邮件</Option>
            <Option value="sms">短信</Option>
            <Option value="webhook">Webhook</Option>
            <Option value="inapp">应用内</Option>
          </Select>
        </Form.Item>

        <Form.Item name="action_url" label="操作链接">
          <Input placeholder="https://example.com/action" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

/**
 * 统计标签页
 */
const StatisticsTab: React.FC = () => {
  const { data: statsData, isLoading } = useQuery({
    queryKey: ['notifications', 'statistics'],
    queryFn: async () => {
      const res = await getNotificationStatistics(30);
      return res.data;
    },
    refetchInterval: 60000,
  });

  const { data: historyData } = useQuery({
    queryKey: ['notifications', 'history'],
    queryFn: async () => {
      const res = await getNotificationHistory({ limit: 20 });
      return res.data;
    },
    refetchInterval: 30000,
  });

  const historyColumns = [
    {
      title: '接收者',
      dataIndex: 'recipient',
      key: 'recipient',
      ellipsis: true,
    },
    {
      title: '渠道',
      dataIndex: 'channel',
      key: 'channel',
      render: (channel: string) => <Tag>{channel}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          sent: 'success',
          failed: 'error',
          pending: 'warning',
        };
        const texts: Record<string, string> = {
          sent: '已发送',
          failed: '失败',
          pending: '发送中',
        };
        return <Tag color={colors[status]}>{texts[status]}</Tag>;
      },
    },
    {
      title: '发送时间',
      dataIndex: 'sent_at',
      key: 'sent_at',
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="总通知数"
              value={statsData?.total_notifications || 0}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="发送成功"
              value={statsData?.sent || 0}
              valueStyle={{ color: '#52c41a' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="发送失败"
              value={statsData?.failed || 0}
              valueStyle={{ color: '#ff4d4f' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="成功率"
              value={((statsData?.success_rate || 0) * 100).toFixed(1)}
              suffix="%"
              loading={isLoading}
            />
          </Card>
        </Col>
      </Row>

      {/* 渠道统计 */}
      <Card title="渠道统计">
        <Row gutter={16}>
          {statsData?.by_channel &&
            Object.entries(statsData.by_channel).map(([channel, data]: [string, any]) => (
              <Col key={channel} xs={24} sm={12} md={8}>
                <Card size="small" className="channel-stat-card">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text strong>{channel}</Text>
                      <Text type="secondary">{data.total} 条</Text>
                    </div>
                    <Progress
                      percent={data.total > 0 ? Math.round((data.sent / data.total) * 100) : 0}
                      status={data.failed > 0 ? 'exception' : 'success'}
                      size="small"
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      成功 {data.sent} / 失败 {data.failed}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
        </Row>
      </Card>

      {/* 最近发送记录 */}
      <Card
        title="最近发送记录"
        extra={
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => window.location.reload()}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={historyColumns}
          dataSource={historyData?.history || []}
          rowKey="history_id"
          size="small"
          pagination={false}
        />
      </Card>
    </Space>
  );
};

/**
 * 主通知中心组件
 */
const NotificationCenter: React.FC<NotificationCenterProps> = ({ className }) => {
  const [sendModalVisible, setSendModalVisible] = useState(false);

  const { data: templatesData } = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: async () => {
      const res = await getNotificationTemplates();
      return res.data;
    },
  });

  return (
    <div className={`notification-center ${className || ''}`}>
      <Card
        title={
          <Space>
            <BellOutlined />
            <span>统一通知管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<SendOutlined />} onClick={() => setSendModalVisible(true)}>
            发送通知
          </Button>
        }
      >
        <Tabs
          defaultActiveKey="templates"
          items={[
            {
              key: 'channels',
              label: '通知渠道',
              children: <ChannelsTab />,
            },
            {
              key: 'templates',
              label: '通知模板',
              children: <TemplatesTab />,
            },
            {
              key: 'rules',
              label: '通知规则',
              children: <RulesTab />,
            },
            {
              key: 'statistics',
              label: '统计分析',
              children: <StatisticsTab />,
            },
          ]}
        />
      </Card>

      <SendNotificationModal
        visible={sendModalVisible}
        onCancel={() => setSendModalVisible(false)}
        templates={templatesData?.templates}
      />
    </div>
  );
};

export default NotificationCenter;
