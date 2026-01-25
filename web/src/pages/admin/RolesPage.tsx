import { useState, useEffect, useCallback } from 'react';
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
  Checkbox,
  Divider,
  Row,
  Col,
  Typography,
  Spin,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  SyncOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import admin from '../../services/admin';

const { Option } = Select;
const { Title, Text } = Typography;

// Types
interface Permission {
  id: string;
  name: string;
  code: string;
  resource: string;
  operation: string;
  category?: string;
  is_system?: boolean;
}

interface Role {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  role_type: 'system' | 'custom';
  is_system: boolean;
  is_active: boolean;
  priority: number;
  parent_role_id?: string;
  permissions?: Permission[];
  user_count?: number;
  created_at?: string;
  updated_at?: string;
}

// API functions
const fetchRoles = async (): Promise<{ roles: Role[]; total: number }> => {
  const response = await fetch('/api/v1/roles');
  if (!response.ok) throw new Error('Failed to fetch roles');
  const data = await response.json();
  return { roles: data.data?.roles || [], total: data.data?.total || 0 };
};

const fetchPermissions = async (): Promise<Permission[]> => {
  const response = await fetch('/api/v1/permissions');
  if (!response.ok) throw new Error('Failed to fetch permissions');
  const data = await response.json();
  return data.data?.permissions || [];
};

const createRole = async (role: Partial<Role> & { permission_ids?: string[] }): Promise<Role> => {
  const response = await fetch('/api/v1/roles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(role),
  });
  if (!response.ok) throw new Error('Failed to create role');
  const data = await response.json();
  return data.data;
};

const updateRole = async (roleId: string, updates: Partial<Role> & { permission_ids?: string[] }): Promise<Role> => {
  const response = await fetch(`/api/v1/roles/${roleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update role');
  const data = await response.json();
  return data.data;
};

const deleteRole = async (roleId: string): Promise<void> => {
  const response = await fetch(`/api/v1/roles/${roleId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete role');
};

function RolesPage() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Queries
  const { data: rolesData, isLoading: isLoadingRoles } = useQuery({
    queryKey: ['roles'],
    queryFn: fetchRoles,
  });

  const { data: permissions = [], isLoading: isLoadingPermissions } = useQuery({
    queryKey: ['permissions'],
    queryFn: fetchPermissions,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: createRole,
    onSuccess: () => {
      message.success('角色创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      setSelectedPermissions([]);
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: () => {
      message.error('角色创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ roleId, data }: { roleId: string; data: Partial<Role> & { permission_ids?: string[] } }) =>
      updateRole(roleId, data),
    onSuccess: () => {
      message.success('角色更新成功');
      setIsEditModalOpen(false);
      editForm.resetFields();
      setSelectedPermissions([]);
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: () => {
      message.error('角色更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRole,
    onSuccess: () => {
      message.success('角色删除成功');
      setIsDetailDrawerOpen(false);
      setSelectedRole(null);
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: () => {
      message.error('角色删除失败');
    },
  });

  // Group permissions by resource
  const permissionsByResource = permissions.reduce((acc, perm) => {
    const resource = perm.resource || 'other';
    if (!acc[resource]) {
      acc[resource] = [];
    }
    acc[resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  const getResourceLabel = (resource: string) => {
    const labels: Record<string, string> = {
      user: '用户管理',
      dataset: '数据集',
      model: '模型',
      workflow: '工作流',
      system: '系统设置',
      role: '角色',
      other: '其他',
    };
    return labels[resource] || resource;
  };

  const handleCreate = () => {
    form.validateFields().then((values) => {
      createMutation.mutate({
        ...values,
        permission_ids: selectedPermissions,
      });
    });
  };

  const handleUpdate = () => {
    editForm.validateFields().then((values) => {
      if (selectedRole) {
        updateMutation.mutate({
          roleId: selectedRole.id,
          data: {
            ...values,
            permission_ids: selectedPermissions,
          },
        });
      }
    });
  };

  const handleEdit = (role: Role) => {
    setSelectedRole(role);
    editForm.setFieldsValue({
      display_name: role.display_name,
      description: role.description,
      priority: role.priority,
      is_active: role.is_active,
    });
    setSelectedPermissions(role.permissions?.map(p => p.id) || []);
    setIsEditModalOpen(true);
  };

  const handleDelete = (role: Role) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除角色 "${role.display_name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(role.id),
    });
  };

  const handlePermissionChange = (permId: string, checked: boolean) => {
    if (checked) {
      setSelectedPermissions([...selectedPermissions, permId]);
    } else {
      setSelectedPermissions(selectedPermissions.filter(id => id !== permId));
    }
  };

  const columns = [
    {
      title: '角色名称',
      key: 'name',
      render: (_: unknown, record: Role) => (
        <Space>
          {record.is_system ? (
            <LockOutlined style={{ color: '#1890ff' }} />
          ) : (
            <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
          )}
          <div>
            <div>{record.display_name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>{record.name}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (type: string, record: Role) => (
        <Tag color={record.is_system ? 'blue' : 'default'}>
          {record.is_system ? '系统' : '自定义'}
        </Tag>
      ),
    },
    {
      title: '权限数量',
      key: 'permissions',
      width: 100,
      render: (_: unknown, record: Role) => (
        <Tag>{record.permissions?.length || 0} 个</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a: Role, b: Role) => (a.priority || 0) - (b.priority || 0),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date?: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Role) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {!record.is_system && (
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Permission selection component
  const PermissionSelector = () => (
    <div style={{ maxHeight: 400, overflow: 'auto' }}>
      {Object.entries(permissionsByResource).map(([resource, perms]) => (
        <Card
          key={resource}
          size="small"
          title={getResourceLabel(resource)}
          style={{ marginBottom: 12 }}
          bodyStyle={{ padding: '8px 16px' }}
        >
          <Row gutter={[8, 8]}>
            {perms.map(perm => (
              <Col span={8} key={perm.id}>
                <Checkbox
                  checked={selectedPermissions.includes(perm.id)}
                  onChange={(e) => handlePermissionChange(perm.id, e.target.checked)}
                >
                  {perm.operation}
                </Checkbox>
              </Col>
            ))}
          </Row>
        </Card>
      ))}
    </div>
  );

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>角色管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['roles'] })}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setSelectedPermissions([]);
                form.resetFields();
                setIsCreateModalOpen(true);
              }}
            >
              新建角色
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={rolesData?.roles || []}
          rowKey="id"
          loading={isLoadingRoles}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 创建角色模态框 */}
      <Modal
        title="新建角色"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setSelectedPermissions([]);
        }}
        onOk={handleCreate}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="角色标识"
                name="name"
                rules={[
                  { required: true, message: '请输入角色标识' },
                  { pattern: /^[a-z_]+$/, message: '只能包含小写字母和下划线' },
                ]}
              >
                <Input placeholder="例如: data_analyst" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="显示名称"
                name="display_name"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="例如: 数据分析师" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="角色描述" />
          </Form.Item>
          <Form.Item label="优先级" name="priority" initialValue={0}>
            <Select>
              <Option value={0}>低 (0)</Option>
              <Option value={50}>中 (50)</Option>
              <Option value={100}>高 (100)</Option>
            </Select>
          </Form.Item>
          <Divider>权限配置</Divider>
          {isLoadingPermissions ? <Spin /> : <PermissionSelector />}
        </Form>
      </Modal>

      {/* 编辑角色模态框 */}
      <Modal
        title={`编辑角色: ${selectedRole?.display_name || ''}`}
        open={isEditModalOpen}
        onCancel={() => {
          setIsEditModalOpen(false);
          editForm.resetFields();
          setSelectedPermissions([]);
          setSelectedRole(null);
        }}
        onOk={handleUpdate}
        confirmLoading={updateMutation.isPending}
        width={700}
      >
        {selectedRole?.is_system && (
          <Alert
            message="系统角色的部分属性无法修改"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <Form form={editForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="显示名称"
                name="display_name"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="显示名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="优先级" name="priority">
                <Select>
                  <Option value={0}>低 (0)</Option>
                  <Option value={50}>中 (50)</Option>
                  <Option value={100}>高 (100)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="角色描述" />
          </Form.Item>
          {!selectedRole?.is_system && (
            <>
              <Divider>权限配置</Divider>
              {isLoadingPermissions ? <Spin /> : <PermissionSelector />}
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
}

export default RolesPage;
