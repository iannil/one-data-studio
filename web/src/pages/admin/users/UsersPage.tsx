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

// API functions
const fetchUsers = async (params: {
  page: number;
  page_size: number;
  status?: string;
  department?: string;
  search?: string;
}) => {
  const searchParams = new URLSearchParams();
  searchParams.set('page', params.page.toString());
  searchParams.set('page_size', params.page_size.toString());
  if (params.status) searchParams.set('status', params.status);
  if (params.department) searchParams.set('department', params.department);
  if (params.search) searchParams.set('search', params.search);

  const response = await fetch(`/api/v1/users?${searchParams.toString()}`);
  if (!response.ok) throw new Error('Failed to fetch users');
  const data = await response.json();
  return data.data;
};

const createUser = async (userData: any) => {
  const response = await fetch('/api/v1/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!response.ok) throw new Error('Failed to create user');
  const data = await response.json();
  return data.data;
};

const updateUser = async (userId: string, userData: any) => {
  const response = await fetch(`/api/v1/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!response.ok) throw new Error('Failed to update user');
  const data = await response.json();
  return data.data;
};

const deleteUser = async (userId: string) => {
  const response = await fetch(`/api/v1/users/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete user');
  return true;
};

const resetPassword = async (userId: string) => {
  const response = await fetch(`/api/v1/users/${userId}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error('Failed to reset password');
  const data = await response.json();
  return data.data;
};

const toggleUserStatus = async (userId: string) => {
  const response = await fetch(`/api/v1/users/${userId}/toggle-status`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to toggle status');
  const data = await response.json();
  return data.data;
};

interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  phone?: string;
  department?: string;
  position?: string;
  roles?: { id: string; name: string; display_name: string }[];
  status: string;
  created_at: string;
  last_login_at?: string;
}

function UsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [searchText, setSearchText] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Queries
  const { data: usersData, isLoading: isLoadingList } = useQuery({
    queryKey: ['users', page, pageSize, statusFilter, departmentFilter, searchText],
    queryFn: () => fetchUsers({
      page,
      page_size: pageSize,
      status: statusFilter || undefined,
      department: departmentFilter || undefined,
      search: searchText || undefined,
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
        content: data?.new_password ? `新密码: ${data.new_password}` : '密码已重置',
      });
    },
    onError: () => {
      message.error('密码重置失败');
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: toggleUserStatus,
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
      data_engineer: 'blue',
      ai_developer: 'green',
      user: 'default',
    };
    return colors[role] || 'default';
  };

  const getRoleText = (role: string) => {
    const texts: Record<string, string> = {
      admin: '管理员',
      data_engineer: '数据工程师',
      ai_developer: 'AI 开发者',
      user: '普通用户',
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
            <div>{record.display_name}</div>
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
      key: 'roles',
      render: (_: unknown, record: User) => (
        <Space wrap>
          {record.roles?.map((role) => (
            <Tag key={role.id} color={getRoleColor(role.name)}>
              {role.display_name || getRoleText(role.name)}
            </Tag>
          )) || <Tag>无角色</Tag>}
        </Space>
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
      dataIndex: 'last_login_at',
      key: 'last_login_at',
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
              editForm.setFieldsValue({
                display_name: record.display_name,
                email: record.email,
                phone: record.phone,
                department: record.department,
                position: record.position,
              });
              setIsEditModalOpen(true);
            }}
          />
          <Switch
            size="small"
            checked={record.status === 'active'}
            onChange={() => toggleStatusMutation.mutate(record.id)}
          />
        </Space>
      ),
    },
  ];

  const roles = [
    { value: 'admin', label: '管理员' },
    { value: 'data_engineer', label: '数据工程师' },
    { value: 'ai_developer', label: 'AI 开发者' },
    { value: 'user', label: '普通用户' },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  const handleUpdate = () => {
    editForm.validateFields().then((values) => {
      if (selectedUser) {
        updateMutation.mutate({ userId: selectedUser.id, data: values });
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
          <Input.Search
            placeholder="搜索用户名/邮箱"
            allowClear
            style={{ width: 200 }}
            onSearch={setSearchText}
          />
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
          dataSource={usersData?.users || []}
          rowKey="id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: usersData?.total || 0,
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
                label="显示名称"
                name="display_name"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="请输入显示名称" />
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
                label="部门"
                name="department"
              >
                <Input placeholder="请输入部门" />
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
                label="显示名称"
                name="display_name"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="请输入显示名称" />
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
              <Form.Item label="部门" name="department">
                <Input placeholder="请输入部门" />
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
              <h3>{selectedUser.display_name}</h3>
              <p style={{ color: '#999' }}>@{selectedUser.username}</p>
            </div>

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="用户ID">{selectedUser.id}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
              <Descriptions.Item label="手机号">{selectedUser.phone || '-'}</Descriptions.Item>
              <Descriptions.Item label="部门">{selectedUser.department || '-'}</Descriptions.Item>
              <Descriptions.Item label="角色">
                {selectedUser.roles?.map((role) => (
                  <Tag key={role.id} color={getRoleColor(role.name)}>
                    {role.display_name || getRoleText(role.name)}
                  </Tag>
                )) || <Tag>无角色</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedUser.status)}>{getStatusText(selectedUser.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedUser.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {selectedUser.last_login_at
                  ? dayjs(selectedUser.last_login_at).format('YYYY-MM-DD HH:mm:ss')
                  : '从未登录'}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<UnlockOutlined />}
                onClick={() => resetPasswordMutation.mutate(selectedUser.id)}
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
                      content: `确定要删除用户 ${selectedUser.display_name} 吗？`,
                      onOk: () => deleteMutation.mutate(selectedUser.id),
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
