import { useState } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  message,
  Tabs,
  Select,
  Space,
  Divider,
  Alert,
  Table,
  Tag,
  Modal,
  Row,
  Col,
} from 'antd';
import {
  SaveOutlined,
  ExperimentOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  MailOutlined,
  CloudServerOutlined,
  SafetyOutlined,
  BgColorsOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import admin from '@/services/admin';
import type { NotificationChannel } from '@/services/admin';

const { Option } = Select;
const { TextArea } = Input;

function SettingsPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('general');

  // 通知渠道相关
  const [isChannelModalOpen, setIsChannelModalOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);
  const [channelForm] = Form.useForm();

  // 获取系统配置
  const { data: settingsData, isLoading: isLoadingSettings } = useQuery({
    queryKey: ['systemSettings'],
    queryFn: admin.getSystemSettings,
  });

  // 获取通知渠道
  const { data: channelsData } = useQuery({
    queryKey: ['notificationChannels'],
    queryFn: admin.getNotificationChannels,
  });

  // 获取通知规则
  const { data: rulesData } = useQuery({
    queryKey: ['notificationRules'],
    queryFn: admin.getNotificationRules,
  });

  // 更新系统配置
  const updateSettingsMutation = useMutation({
    mutationFn: admin.updateSystemSettings,
    onSuccess: () => {
      message.success('系统配置更新成功');
      queryClient.invalidateQueries({ queryKey: ['systemSettings'] });
    },
    onError: () => {
      message.error('系统配置更新失败');
    },
  });

  // 测试邮件
  const testEmailMutation = useMutation({
    mutationFn: admin.sendTestEmail,
    onSuccess: () => {
      message.success('测试邮件发送成功，请检查收件箱');
    },
    onError: () => {
      message.error('测试邮件发送失败');
    },
  });

  // 测试存储连接
  const testStorageMutation = useMutation({
    mutationFn: admin.testStorageConnection,
    onSuccess: (data) => {
      if (data.data.success) {
        message.success(data.data.message);
      } else {
        message.error(data.data.message);
      }
    },
  });

  // 创建通知渠道
  const createChannelMutation = useMutation({
    mutationFn: admin.createNotificationChannel,
    onSuccess: () => {
      message.success('通知渠道创建成功');
      setIsChannelModalOpen(false);
      channelForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['notificationChannels'] });
    },
    onError: () => {
      message.error('通知渠道创建失败');
    },
  });

  // 更新通知渠道
  const updateChannelMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationChannel> }) =>
      admin.updateNotificationChannel(id, data),
    onSuccess: () => {
      message.success('通知渠道更新成功');
      setIsChannelModalOpen(false);
      setEditingChannel(null);
      channelForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['notificationChannels'] });
    },
    onError: () => {
      message.error('通知渠道更新失败');
    },
  });

  // 删除通知渠道
  const deleteChannelMutation = useMutation({
    mutationFn: admin.deleteNotificationChannel,
    onSuccess: () => {
      message.success('通知渠道删除成功');
      queryClient.invalidateQueries({ queryKey: ['notificationChannels'] });
    },
    onError: () => {
      message.error('通知渠道删除失败');
    },
  });

  // 测试通知渠道
  const testChannelMutation = useMutation({
    mutationFn: admin.testNotificationChannel,
    onSuccess: (data) => {
      if (data.data.success) {
        message.success(data.data.message);
      } else {
        message.error(data.data.message);
      }
    },
  });

  const handleSaveSettings = async () => {
    try {
      const values = await form.validateFields();
      updateSettingsMutation.mutate(values);
    } catch {
      // Validation failed
    }
  };

  const handleTestEmail = async () => {
    const email = await form.getFieldValue('email_test_address');
    if (!email) {
      message.warning('请输入测试邮箱地址');
      return;
    }
    testEmailMutation.mutate(email);
  };

  const handleOpenChannelModal = (channel?: NotificationChannel) => {
    if (channel) {
      setEditingChannel(channel);
      channelForm.setFieldsValue(channel);
    } else {
      setEditingChannel(null);
      channelForm.resetFields();
    }
    setIsChannelModalOpen(true);
  };

  const handleSaveChannel = async () => {
    try {
      const values = await channelForm.validateFields();
      if (editingChannel) {
        updateChannelMutation.mutate({ id: editingChannel.id, data: values });
      } else {
        createChannelMutation.mutate(values);
      }
    } catch {
      // Validation failed
    }
  };

  const channelColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          email: { label: '邮件', color: 'blue' },
          webhook: { label: 'Webhook', color: 'purple' },
          dingtalk: { label: '钉钉', color: 'cyan' },
          feishu: { label: '飞书', color: 'green' },
          slack: { label: 'Slack', color: 'orange' },
          wechat: { label: '微信', color: 'green' },
        };
        const info = typeMap[type] || { label: type, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>{enabled ? '已启用' : '已禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: NotificationChannel) => (
        <Space>
          <Button
            type="text"
            icon={<ExperimentOutlined />}
            onClick={() => testChannelMutation.mutate(record.id)}
          >
            测试
          </Button>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleOpenChannelModal(record)}
          />
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => deleteChannelMutation.mutate(record.id)}
          />
        </Space>
      ),
    },
  ];

  const settings = settingsData?.data;

  const generalSettings = (
    <Card>
      <Form
        form={form}
        layout="vertical"
        initialValues={settings}
        onFinish={handleSaveSettings}
      >
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="站点名称" name="site_name" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="时区" name="timezone" rules={[{ required: true }]}>
              <Select>
                <Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Option>
                <Option value="Asia/Tokyo">Asia/Tokyo (UTC+9)</Option>
                <Option value="America/New_York">America/New_York (UTC-5)</Option>
                <Option value="Europe/London">Europe/London (UTC+0)</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="站点描述" name="site_description">
          <TextArea rows={2} />
        </Form.Item>
        <Form.Item label="Logo URL" name="logo_url">
          <Input placeholder="https://example.com/logo.png" />
        </Form.Item>
      </Form>
    </Card>
  );

  const emailSettings = (
    <Card>
      <Form layout="vertical" form={form} initialValues={settings}>
        <Form.Item label="启用邮件服务" name="email_enabled" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="SMTP 服务器" name="email_smtp_host">
          <Input placeholder="smtp.example.com" />
        </Form.Item>
        <Form.Item label="SMTP 端口" name="email_smtp_port">
          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item label="SMTP 用户名" name="email_smtp_user">
          <Input />
        </Form.Item>
        <Form.Item label="发件人地址" name="email_from_address">
          <Input placeholder="noreply@example.com" />
        </Form.Item>
        <Form.Item label="发件人名称" name="email_from_name">
          <Input />
        </Form.Item>
        <Divider />
        <Form.Item label="测试邮件地址" name="email_test_address">
          <Input placeholder="test@example.com" />
        </Form.Item>
        <Button
          icon={<MailOutlined />}
          onClick={handleTestEmail}
          loading={testEmailMutation.isPending}
        >
          发送测试邮件
        </Button>
      </Form>
    </Card>
  );

  const storageSettings = (
    <Card>
      <Form layout="vertical" form={form} initialValues={settings}>
        <Form.Item label="存储类型" name="storage_type">
          <Select>
            <Option value="local">本地存储</Option>
            <Option value="minio">MinIO</Option>
            <Option value="s3">AWS S3</Option>
          </Select>
        </Form.Item>
        <Form.Item label="存储端点" name="storage_endpoint">
          <Input placeholder="http://localhost:9000" />
        </Form.Item>
        <Form.Item label="存储桶" name="storage_bucket">
          <Input placeholder="one-data-studio" />
        </Form.Item>
        <Form.Item label="Access Key" name="storage_access_key">
          <Input.Password />
        </Form.Item>
        <Form.Item label="Region" name="storage_region">
          <Input placeholder="us-east-1" />
        </Form.Item>
        <Divider />
        <Button
          icon={<CloudServerOutlined />}
          onClick={() => testStorageMutation.mutate()}
          loading={testStorageMutation.isPending}
        >
          测试存储连接
        </Button>
      </Form>
    </Card>
  );

  const securitySettings = (
    <Card>
      <Form layout="vertical" form={form} initialValues={settings}>
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="最小密码长度" name="password_min_length">
              <InputNumber min={6} max={32} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="会话超时（分钟）" name="session_timeout_minutes">
              <InputNumber min={5} max={1440} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="最大登录尝试次数" name="max_login_attempts">
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="锁定时长（分钟）" name="lockout_duration_minutes">
              <InputNumber min={1} max={1440} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="密码要求" name="password_require_uppercase" valuePropName="checked">
          <Space>
            <Switch />
            <span>包含大写字母</span>
          </Space>
        </Form.Item>
        <Form.Item label="密码要求" name="password_require_lowercase" valuePropName="checked">
          <Space>
            <Switch />
            <span>包含小写字母</span>
          </Space>
        </Form.Item>
        <Form.Item label="密码要求" name="password_require_number" valuePropName="checked">
          <Space>
            <Switch />
            <span>包含数字</span>
          </Space>
        </Form.Item>
        <Form.Item label="密码要求" name="password_require_special" valuePropName="checked">
          <Space>
            <Switch />
            <span>包含特殊字符</span>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );

  const featuresSettings = (
    <Card>
      <Alert
        message="功能开关"
        description="禁用某个功能后，该功能的所有相关页面和 API 将不可用"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Form layout="vertical" form={form} initialValues={settings}>
        <Form.Item label="Alldata (数据治理)" name={['features_enabled', 'alldata']} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="Cube Studio (MLOps)" name={['features_enabled', 'cube']} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="Bisheng (LLMOps)" name={['features_enabled', 'bisheng']} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="工作流编排" name={['features_enabled', 'workflows']} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Card>
  );

  const notificationTab = (
    <div>
      <Card
        title="通知渠道"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenChannelModal()}>
            添加渠道
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={channelColumns}
          dataSource={channelsData?.data?.channels || []}
          rowKey="id"
          pagination={false}
        />
      </Card>

      <Card title="通知规则">
        <Alert
          message="通知规则用于配置在特定事件发生时，通过哪些渠道发送通知"
          type="info"
          style={{ marginBottom: 16 }}
        />
        <Table
          columns={[
            { title: '名称', dataIndex: 'name', key: 'name' },
            {
              title: '事件',
              dataIndex: 'events',
              key: 'events',
              render: (events: string[]) => events?.map((e) => <Tag key={e}>{e}</Tag>) || '-',
            },
            {
              title: '渠道',
              dataIndex: 'channel_ids',
              key: 'channel_ids',
              render: (ids: string[]) => `${ids?.length || 0} 个渠道`,
            },
            {
              title: '状态',
              dataIndex: 'enabled',
              key: 'enabled',
              render: (enabled: boolean) => <Tag color={enabled ? 'green' : 'red'}>{enabled ? '已启用' : '已禁用'}</Tag>,
            },
          ]}
          dataSource={rulesData?.data?.rules || []}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );

  const tabItems = [
    { key: 'general', label: '通用设置', icon: <BgColorsOutlined />, children: generalSettings },
    { key: 'email', label: '邮件服务', icon: <MailOutlined />, children: emailSettings },
    { key: 'storage', label: '存储配置', icon: <CloudServerOutlined />, children: storageSettings },
    { key: 'security', label: '安全设置', icon: <SafetyOutlined />, children: securitySettings },
    { key: 'features', label: '功能开关', icon: <BgColorsOutlined />, children: featuresSettings },
    { key: 'notification', label: '通知配置', icon: <BgColorsOutlined />, children: notificationTab },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="系统设置"
        extra={
          <Space>
            <Button
              onClick={() => {
                if (settings) {
                  form.setFieldsValue(settings);
                }
              }}
            >
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSaveSettings}
              loading={updateSettingsMutation.isPending || isLoadingSettings}
            >
              保存配置
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* 通知渠道模态框 */}
      <Modal
        title={editingChannel ? '编辑通知渠道' : '添加通知渠道'}
        open={isChannelModalOpen}
        onOk={handleSaveChannel}
        onCancel={() => {
          setIsChannelModalOpen(false);
          setEditingChannel(null);
          channelForm.resetFields();
        }}
        confirmLoading={createChannelMutation.isPending || updateChannelMutation.isPending}
      >
        <Form form={channelForm} layout="vertical">
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="请输入渠道名称" />
          </Form.Item>
          <Form.Item label="类型" name="type" rules={[{ required: true }]}>
            <Select disabled={!!editingChannel}>
              <Option value="email">邮件</Option>
              <Option value="webhook">Webhook</Option>
              <Option value="dingtalk">钉钉</Option>
              <Option value="feishu">飞书</Option>
              <Option value="slack">Slack</Option>
              <Option value="wechat">企业微信</Option>
            </Select>
          </Form.Item>
          <Form.Item label="Webhook URL" name={['config', 'url']}>
            <Input placeholder="https://..." />
          </Form.Item>
          <Form.Item label="Secret" name={['config', 'secret']}>
            <Input.Password placeholder="可选" />
          </Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default SettingsPage;
