import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Drawer,
  Descriptions,
  Avatar,
  Switch,
  Divider,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  LockOutlined,
  UnlockOutlined,
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  SyncOutlined,
} from '@ant-design/icons';

const { Option } = Select;
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

// Mock API functions (to be replaced with actual API calls)
const mockUsers = [
  {
    user_id: '1',
    username: 'admin',
    email: 'admin@example.com',
    full_name: '系统管理员',
    phone: '13800138000',
    role: 'admin',
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    last_login: '2024-01-24T10:00:00Z',
  },
  {
    user_id: '2',
    username: 'developer',
    email: 'developer@example.com',
    full_name: '开发工程师',
    phone: '13800138001',
    role: 'developer',
    status: 'active',
    created_at: '2024-01-05T00:00:00Z',
    last_login: '2024-01-24T09:00:00Z',
  },
  {
    user_id: '3',
    username: 'analyst',
    email: 'analyst@example.com',
    full_name: '数据分析师',
    phone: '13800138002',
    role: 'analyst',
    status: 'active',
    created_at: '2024-01-10T00:00:00Z',
    last_login: '2024-01-23T15:00:00Z',
  },
];

const getUsers = async () => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { users: mockUsers, total: mockUsers.length } };
};

const createUser = async (data: any) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { user: { ...data, user_id: Date.now().toString(), created_at: new Date().toISOString() } } };
};

const updateUser = async (userId: string, data: any) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { user: { ...data, user_id: userId } } };
};

const deleteUser = async (_userId: string) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { success: true } };
};

const resetPassword = async (_userId: string) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { success: true, new_password: 'NewPass123!' } };
};

interface User {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  phone?: string;
  role: string;
  status: string;
  created_at: string;
  last_login?: string;
}

function UsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Queries
  const { data: usersData, isLoading: isLoadingList } = useQuery({
    queryKey: ['users', page, pageSize, roleFilter, statusFilter],
    queryFn: () =>
      getUsers().then((res) => {
        let users = res.data.users;
                        if (roleFilter) users = users.filter((u) => u.role === roleFilter);
                        if (statusFilter) users = users.filter((u) => u.status === statusFilter);
                        return { data: { users: users.slice((page - 1) * pageSize, page * pageSize), total: users.length } };
                      }),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      message.success('用户创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('用户创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: any }) => updateUser(userId, data),
    onSuccess: () => {
      message.success('用户更新成功');
      setIsEditModalOpen(false);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('用户更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      message.success('用户删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('用户删除失败');
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: (data) => {
      Modal.success({
        title: '密码重置成功',
        content: `新密码: ${data.data.new_password}`,
      });
    },
    onError: () => {
      message.error('密码重置失败');
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: string }) =>
      updateUser(userId, { status }),
    onSuccess: () => {
      message.success('用户状态更新成功');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('用户状态更新失败');
    },
  });

  const getRoleColor = (role: string) => {
    const colors: Record<string, string> = {
      admin: 'red',
      developer: 'blue',
      analyst: 'green',
      viewer: 'default',
    };
    return colors[role] || 'default';
  };

  const getRoleText = (role: string) => {
    const texts: Record<string, string> = {
      admin: '管理员',
      developer: '开发者',
      analyst: '分析师',
      viewer: '访客',
    };
    return texts[role] || role;
  };

  const getStatusColor = (status: string) => {
    return status === 'active' ? 'success' : 'default';
  };

  const getStatusText = (status: string) => {
    return status === 'active' ? '正常' : '停用';
  };

  const columns = [
    {
      title: '用户',
      key: 'user',
      render: (_: unknown, record: User) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div>{record.full_name}</div>
            <div style={{ fontSize: 12, color: '#999' }}>@{record.username}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '手机',
      dataIndex: 'phone',
      key: 'phone',
      render: (phone?: string) => phone || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={getRoleColor(role)}>{getRoleText(role)}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date?: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: User) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => { setSelectedUser(record); setIsDetailDrawerOpen(true); }}
          />
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedUser(record);
              editForm.setFieldsValue(record);
              setIsEditModalOpen(true);
            }}
          />
          <Switch
            size="small"
            checked={record.status === 'active'}
            onChange={(checked) => {
              toggleStatusMutation.mutate({
                userId: record.user_id,
                status: checked ? 'active' : 'inactive',
              });
            }}
          />
        </Space>
      ),
    },
  ];

  const roles = [
    { value: 'admin', label: '管理员' },
    { value: 'developer', label: '开发者' },
    { value: 'analyst', label: '分析师' },
    { value: 'viewer', label: '访客' },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  const handleUpdate = () => {
    editForm.validateFields().then((values) => {
      if (selectedUser) {
        updateMutation.mutate({ userId: selectedUser.user_id, data: values });
      }
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="用户管理"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['users'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建用户
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="角色筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setRoleFilter}
            value={roleFilter || undefined}
          >
            {roles.map((role) => (
              <Option key={role.value} value={role.value}>
                {role.label}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="active">正常</Option>
            <Option value="inactive">停用</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={usersData?.data?.users || []}
          rowKey="user_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: usersData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建用户模态框 */}
      <Modal
        title="新建用户"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="username"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { pattern: /^[a-zA-Z0-9_]{3,20}$/, message: '用户名只能包含字母、数字、下划线，长度3-20' },
                ]}
              >
                <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="姓名"
                name="full_name"
                rules={[{ required: true, message: '请输入姓名' }]}
              >
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="手机号"
                name="phone"
                rules={[
                  { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' },
                ]}
              >
                <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="密码"
                name="password"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8位' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="角色"
                name="role"
                rules={[{ required: true, message: '请选择角色' }]}
                initialValue="viewer"
              >
                <Select>
                  {roles.map((role) => (
                    <Option key={role.value} value={role.value}>
                      {role.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 编辑用户模态框 */}
      <Modal
        title="编辑用户"
        open={isEditModalOpen}
        onCancel={() => {
          setIsEditModalOpen(false);
          editForm.resetFields();
        }}
        onOk={handleUpdate}
        confirmLoading={updateMutation.isPending}
        width={600}
      >
        <Form form={editForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="姓名"
                name="full_name"
                rules={[{ required: true, message: '请输入姓名' }]}
              >
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="手机号"
                name="phone"
                rules={[
                  { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' },
                ]}
              >
                <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="角色"
                name="role"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select>
                  {roles.map((role) => (
                    <Option key={role.value} value={role.value}>
                      {role.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 用户详情抽屉 */}
      <Drawer
        title="用户详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedUser(null);
        }}
        width={600}
      >
        {selectedUser && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <Avatar size={80} icon={<UserOutlined />} style={{ marginBottom: 16 }} />
              <h3>{selectedUser.full_name}</h3>
              <p style={{ color: '#999' }}>@{selectedUser.username}</p>
            </div>

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="用户ID">{selectedUser.user_id}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
              <Descriptions.Item label="手机号">{selectedUser.phone || '-'}</Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag color={getRoleColor(selectedUser.role)}>{getRoleText(selectedUser.role)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedUser.status)}>{getStatusText(selectedUser.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedUser.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {selectedUser.last_login
                  ? dayjs(selectedUser.last_login).format('YYYY-MM-DD HH:mm:ss')
                  : '从未登录'}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<UnlockOutlined />}
                onClick={() => resetPasswordMutation.mutate(selectedUser.user_id)}
              >
                重置密码
              </Button>
              {selectedUser.username !== 'admin' && (
                <Button
                  block
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    Modal.confirm({
                      title: '确认删除',
                      content: `确定要删除用户 ${selectedUser.full_name} 吗？`,
                      onOk: () => deleteMutation.mutate(selectedUser.user_id),
                    });
                  }}
                >
                  删除用户
                </Button>
              )}
            </Space>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default UsersPage;
