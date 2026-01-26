import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Avatar,
  Typography,
  Descriptions,
  Button,
  Space,
  Tag,
  Tabs,
  Table,
  Form,
  Input,
  message,
  Modal,
  Divider,
  Timeline,
  Empty,
  Spin,
  Switch,
  Select,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  LockOutlined,
  HistoryOutlined,
  SettingOutlined,
  EditOutlined,
  KeyOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { useAuth } from '../../contexts/AuthContext';
import { getAuditLogs, AuditLog, AuditLogListParams } from '../../services/admin';

const { Title, Text, Paragraph } = Typography;

// 操作类型中文映射
const actionLabels: Record<string, string> = {
  create: '创建',
  read: '查看',
  update: '更新',
  delete: '删除',
  login: '登录',
  logout: '退出',
  export: '导出',
  import: '导入',
  execute: '执行',
  approve: '审批',
  reject: '拒绝',
};

// 资源类型中文映射
const resourceLabels: Record<string, string> = {
  user: '用户',
  role: '角色',
  group: '用户组',
  dataset: '数据集',
  workflow: '工作流',
  model: '模型',
  experiment: '实验',
  notification: '通知',
  announcement: '公告',
  todo: '待办',
  etl_task: 'ETL任务',
  data_source: '数据源',
  metadata: '元数据',
  quality_rule: '质量规则',
  alert_rule: '预警规则',
  settings: '系统设置',
  system: '系统',
};

// 角色中文映射
const roleLabels: Record<string, { label: string; color: string }> = {
  admin: { label: '管理员', color: 'red' },
  developer: { label: '开发者', color: 'blue' },
  analyst: { label: '分析师', color: 'green' },
  viewer: { label: '访客', color: 'default' },
  user: { label: '用户', color: 'cyan' },
  operator: { label: '运维', color: 'orange' },
};

function ProfilePage() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [passwordForm] = Form.useForm();
  const [activityParams, setActivityParams] = useState<AuditLogListParams>({
    page: 1,
    page_size: 10,
    user_id: user?.sub,
  });

  // 获取用户活动记录
  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['user-activities', activityParams],
    queryFn: async () => {
      if (!user?.sub) return null;
      const response = await getAuditLogs({
        ...activityParams,
        user_id: user.sub,
      });
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
    enabled: !!user?.sub,
  });

  // 修改密码
  const handleChangePassword = async (values: { oldPassword: string; newPassword: string }) => {
    try {
      // TODO: 实际调用修改密码 API
      message.success('密码修改成功，请重新登录');
      setPasswordModalVisible(false);
      passwordForm.resetFields();
      // 登出让用户重新登录
      setTimeout(() => logout(), 2000);
    } catch (error) {
      message.error('密码修改失败');
    }
  };

  // 活动记录列
  const activityColumns: ColumnsType<AuditLog> = [
    {
      title: '操作',
      dataIndex: 'action',
      width: 80,
      render: (action: string) => (
        <Tag color="blue">{actionLabels[action] || action}</Tag>
      ),
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      width: 100,
      render: (type: string) => resourceLabels[type] || type,
    },
    {
      title: '资源名称',
      dataIndex: 'resource_name',
      ellipsis: true,
      render: (name: string) => name || '-',
    },
    {
      title: '状态',
      dataIndex: 'success',
      width: 80,
      render: (success: boolean) => (
        success ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>成功</Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>失败</Tag>
        )
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      width: 130,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 160,
      render: (time: string) => time?.slice(0, 19).replace('T', ' ') || '-',
    },
  ];

  // 最近活动时间线
  const recentActivities = activityData?.logs?.slice(0, 5) || [];

  // 渲染个人资料
  const renderProfile = () => (
    <Row gutter={[24, 24]}>
      <Col xs={24} md={8}>
        <Card>
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <Avatar
              size={100}
              icon={<UserOutlined />}
              style={{ backgroundColor: '#1677ff', marginBottom: 16 }}
            />
            <Title level={4} style={{ margin: '8px 0' }}>
              {user?.name || user?.preferred_username || '用户'}
            </Title>
            <Text type="secondary">{user?.email || '未设置邮箱'}</Text>
            <Divider />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">角色</Text>
              <div style={{ marginTop: 8 }}>
                {user?.roles?.map((role) => {
                  const roleInfo = roleLabels[role] || { label: role, color: 'default' };
                  return (
                    <Tag key={role} color={roleInfo.color} style={{ marginBottom: 4 }}>
                      {roleInfo.label}
                    </Tag>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>
      </Col>
      <Col xs={24} md={16}>
        <Card
          title={
            <span>
              <UserOutlined style={{ marginRight: 8 }} />
              基本信息
            </span>
          }
          extra={
            <Button icon={<EditOutlined />} disabled>
              编辑
            </Button>
          }
        >
          <Descriptions column={{ xs: 1, sm: 2 }} bordered>
            <Descriptions.Item label="用户名">
              {user?.preferred_username || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="姓名">
              {user?.name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="名">
              {user?.given_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="姓">
              {user?.family_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="邮箱" span={2}>
              <MailOutlined style={{ marginRight: 8 }} />
              {user?.email || '未设置'}
            </Descriptions.Item>
            <Descriptions.Item label="用户ID" span={2}>
              <Text code copyable style={{ fontSize: 12 }}>
                {user?.sub}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          title={
            <span>
              <HistoryOutlined style={{ marginRight: 8 }} />
              最近活动
            </span>
          }
          style={{ marginTop: 16 }}
          extra={
            <Button type="link" onClick={() => setActiveTab('activities')}>
              查看全部
            </Button>
          }
        >
          {recentActivities.length > 0 ? (
            <Timeline
              items={recentActivities.map((activity) => ({
                color: activity.success ? 'green' : 'red',
                children: (
                  <div>
                    <Text strong>{actionLabels[activity.action] || activity.action}</Text>
                    <Text> {resourceLabels[activity.resource_type] || activity.resource_type}</Text>
                    {activity.resource_name && (
                      <Text type="secondary"> - {activity.resource_name}</Text>
                    )}
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {activity.created_at?.slice(0, 19).replace('T', ' ')}
                      </Text>
                    </div>
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty description="暂无活动记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Col>
    </Row>
  );

  // 渲染活动记录
  const renderActivities = () => (
    <Card
      title={
        <span>
          <HistoryOutlined style={{ marginRight: 8 }} />
          活动记录
        </span>
      }
    >
      <Table
        columns={activityColumns}
        dataSource={activityData?.logs || []}
        rowKey="audit_id"
        loading={activityLoading}
        pagination={{
          current: activityParams.page,
          pageSize: activityParams.page_size,
          total: activityData?.total || 0,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) =>
            setActivityParams({ ...activityParams, page, page_size: pageSize }),
        }}
        locale={{
          emptyText: <Empty description="暂无活动记录" />,
        }}
      />
    </Card>
  );

  // 渲染安全设置
  const renderSecurity = () => (
    <Row gutter={[24, 24]}>
      <Col span={24}>
        <Card
          title={
            <span>
              <LockOutlined style={{ marginRight: 8 }} />
              密码管理
            </span>
          }
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <Text strong>登录密码</Text>
              <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 4 }}>
                定期更新密码可以提高账户安全性
              </Paragraph>
            </div>
            <Button
              icon={<KeyOutlined />}
              onClick={() => setPasswordModalVisible(true)}
            >
              修改密码
            </Button>
          </div>
        </Card>
      </Col>
      <Col span={24}>
        <Card
          title={
            <span>
              <SafetyCertificateOutlined style={{ marginRight: 8 }} />
              登录安全
            </span>
          }
        >
          <Descriptions column={1}>
            <Descriptions.Item label="两步验证">
              <Tag color="default">未启用</Tag>
              <Button type="link" size="small" disabled>
                启用
              </Button>
            </Descriptions.Item>
            <Descriptions.Item label="登录设备管理">
              <Button type="link" size="small" disabled>
                查看设备
              </Button>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
      <Col span={24}>
        <Card
          title={
            <span>
              <LogoutOutlined style={{ marginRight: 8 }} />
              账户操作
            </span>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <Text strong>退出登录</Text>
                <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 4 }}>
                  退出当前账户
                </Paragraph>
              </div>
              <Button danger onClick={() => logout()}>
                退出登录
              </Button>
            </div>
          </Space>
        </Card>
      </Col>
    </Row>
  );

  // 渲染偏好设置
  const renderPreferences = () => (
    <Row gutter={[24, 24]}>
      <Col span={24}>
        <Card
          title={
            <span>
              <BellOutlined style={{ marginRight: 8 }} />
              通知设置
            </span>
          }
        >
          <Form layout="horizontal" labelCol={{ span: 6 }} wrapperCol={{ span: 18 }}>
            <Form.Item label="系统通知" valuePropName="checked">
              <Switch defaultChecked />
              <Text type="secondary" style={{ marginLeft: 8 }}>
                接收系统公告和更新通知
              </Text>
            </Form.Item>
            <Form.Item label="任务提醒" valuePropName="checked">
              <Switch defaultChecked />
              <Text type="secondary" style={{ marginLeft: 8 }}>
                接收待办任务和截止日期提醒
              </Text>
            </Form.Item>
            <Form.Item label="告警通知" valuePropName="checked">
              <Switch defaultChecked />
              <Text type="secondary" style={{ marginLeft: 8 }}>
                接收数据质量和预警告警
              </Text>
            </Form.Item>
            <Form.Item label="邮件通知" valuePropName="checked">
              <Switch />
              <Text type="secondary" style={{ marginLeft: 8 }}>
                同时发送邮件通知
              </Text>
            </Form.Item>
          </Form>
        </Card>
      </Col>
      <Col span={24}>
        <Card
          title={
            <span>
              <SettingOutlined style={{ marginRight: 8 }} />
              显示设置
            </span>
          }
        >
          <Form layout="horizontal" labelCol={{ span: 6 }} wrapperCol={{ span: 18 }}>
            <Form.Item label="语言">
              <Select defaultValue="zh-CN" style={{ width: 200 }} disabled>
                <Select.Option value="zh-CN">简体中文</Select.Option>
                <Select.Option value="en-US">English</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item label="时区">
              <Select defaultValue="Asia/Shanghai" style={{ width: 200 }} disabled>
                <Select.Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Select.Option>
                <Select.Option value="UTC">UTC</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item label="每页显示">
              <Select defaultValue={20} style={{ width: 200 }}>
                <Select.Option value={10}>10 条</Select.Option>
                <Select.Option value={20}>20 条</Select.Option>
                <Select.Option value={50}>50 条</Select.Option>
                <Select.Option value={100}>100 条</Select.Option>
              </Select>
            </Form.Item>
          </Form>
        </Card>
      </Col>
    </Row>
  );

  const tabItems = [
    {
      key: 'profile',
      label: (
        <span>
          <UserOutlined />
          个人资料
        </span>
      ),
      children: renderProfile(),
    },
    {
      key: 'activities',
      label: (
        <span>
          <HistoryOutlined />
          活动记录
        </span>
      ),
      children: renderActivities(),
    },
    {
      key: 'security',
      label: (
        <span>
          <SafetyCertificateOutlined />
          安全设置
        </span>
      ),
      children: renderSecurity(),
    },
    {
      key: 'preferences',
      label: (
        <span>
          <SettingOutlined />
          偏好设置
        </span>
      ),
      children: renderPreferences(),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          个人中心
        </Title>
        <Text type="secondary">管理您的个人信息、安全设置和偏好</Text>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false);
          passwordForm.resetFields();
        }}
        footer={null}
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handleChangePassword}
        >
          <Form.Item
            name="oldPassword"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码长度至少8位' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                message: '密码需包含大小写字母和数字',
              },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setPasswordModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                确认修改
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default ProfilePage;
