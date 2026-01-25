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
  InputNumber,
  message,
  Drawer,
  Descriptions,
  Alert,
  Divider,
  Row,
  Col,
  Transfer,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  TeamOutlined,
  UserAddOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

// API functions
const fetchGroups = async (params: {
  page: number;
  page_size: number;
  type?: string;
  search?: string;
}) => {
  const searchParams = new URLSearchParams();
  searchParams.set('page', params.page.toString());
  searchParams.set('page_size', params.page_size.toString());
  if (params.type) searchParams.set('type', params.type);
  if (params.search) searchParams.set('search', params.search);

  const response = await fetch(`/api/v1/groups?${searchParams.toString()}`);
  if (!response.ok) throw new Error('Failed to fetch groups');
  const data = await response.json();
  return data.data;
};

const fetchGroupDetail = async (groupId: string) => {
  const response = await fetch(`/api/v1/groups/${groupId}?include_members=true`);
  if (!response.ok) throw new Error('Failed to fetch group detail');
  const data = await response.json();
  return data.data;
};

const fetchUsers = async () => {
  const response = await fetch('/api/v1/users?page=1&page_size=1000');
  if (!response.ok) throw new Error('Failed to fetch users');
  const data = await response.json();
  return data.data?.users || [];
};

const createGroup = async (groupData: any) => {
  const response = await fetch('/api/v1/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(groupData),
  });
  if (!response.ok) throw new Error('Failed to create group');
  const data = await response.json();
  return data.data;
};

const updateGroup = async (groupId: string, groupData: any) => {
  const response = await fetch(`/api/v1/groups/${groupId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(groupData),
  });
  if (!response.ok) throw new Error('Failed to update group');
  const data = await response.json();
  return data.data;
};

const deleteGroup = async (groupId: string) => {
  const response = await fetch(`/api/v1/groups/${groupId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete group');
  return true;
};

const addGroupMembers = async (groupId: string, userIds: string[]) => {
  const response = await fetch(`/api/v1/groups/${groupId}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_ids: userIds }),
  });
  if (!response.ok) throw new Error('Failed to add members');
  const data = await response.json();
  return data.data;
};

const removeGroupMember = async (groupId: string, userId: string) => {
  const response = await fetch(`/api/v1/groups/${groupId}/members/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove member');
  return true;
};

interface UserGroup {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  group_type: string;
  is_active: boolean;
  member_count: number;
  members?: { id: string; username: string; display_name: string }[];
  created_at: string;
  updated_at?: string;
}

interface User {
  id: string;
  username: string;
  display_name: string;
}

function GroupsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<UserGroup | null>(null);
  const [targetKeys, setTargetKeys] = useState<string[]>([]);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Queries
  const { data: groupsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['user-groups', page, pageSize, typeFilter],
    queryFn: () => fetchGroups({
      page,
      page_size: pageSize,
      type: typeFilter || undefined,
    }),
  });

  const { data: allUsers = [], isLoading: isLoadingUsers } = useQuery({
    queryKey: ['all-users'],
    queryFn: fetchUsers,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: () => {
      message.success('用户组创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['user-groups'] });
    },
    onError: () => {
      message.error('用户组创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: any }) => updateGroup(groupId, data),
    onSuccess: () => {
      message.success('用户组更新成功');
      setIsEditModalOpen(false);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['user-groups'] });
    },
    onError: () => {
      message.error('用户组更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteGroup,
    onSuccess: () => {
      message.success('用户组删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['user-groups'] });
    },
    onError: () => {
      message.error('用户组删除失败');
    },
  });

  const addMembersMutation = useMutation({
    mutationFn: ({ groupId, userIds }: { groupId: string; userIds: string[] }) =>
      addGroupMembers(groupId, userIds),
    onSuccess: () => {
      message.success('成员添加成功');
      queryClient.invalidateQueries({ queryKey: ['user-groups'] });
    },
    onError: () => {
      message.error('成员添加失败');
    },
  });

  const getStatusColor = (isActive: boolean) => {
    return isActive ? 'success' : 'default';
  };

  const getStatusText = (isActive: boolean) => {
    return isActive ? '正常' : '停用';
  };

  const getTypeText = (type: string) => {
    const types: Record<string, string> = {
      department: '部门',
      team: '团队',
      project: '项目',
      custom: '自定义',
    };
    return types[type] || type;
  };

  const columns = [
    {
      title: '组名称',
      key: 'name',
      render: (_: unknown, record: UserGroup) => (
        <a onClick={() => { setSelectedGroup(record); setIsDetailDrawerOpen(true); }}>
          {record.display_name || record.name}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc?: string) => desc || '-',
    },
    {
      title: '类型',
      dataIndex: 'group_type',
      key: 'group_type',
      width: 100,
      render: (type: string) => <Tag>{getTypeText(type)}</Tag>,
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      key: 'member_count',
      width: 100,
      render: (count: number) => (
        <Tag><TeamOutlined /> {count}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Tag color={getStatusColor(isActive)}>{getStatusText(isActive)}</Tag>
      ),
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
      width: 200,
      render: (_: unknown, record: UserGroup) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => { setSelectedGroup(record); setIsDetailDrawerOpen(true); }}
          >
            详情
          </Button>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedGroup(record);
              editForm.setFieldsValue({
                display_name: record.display_name,
                description: record.description,
                group_type: record.group_type,
              });
              setIsEditModalOpen(true);
            }}
          >
            编辑
          </Button>
          <Button
            type="text"
            size="small"
            icon={<UserAddOutlined />}
            onClick={() => {
              setSelectedGroup(record);
              setTargetKeys(record.members?.map(m => m.id) || []);
              setIsMemberModalOpen(true);
            }}
          >
            成员
          </Button>
        </Space>
      ),
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  const handleUpdate = () => {
    editForm.validateFields().then((values) => {
      if (selectedGroup) {
        updateMutation.mutate({ groupId: selectedGroup.id, data: values });
      }
    });
  };

  const handleMemberChange = (newTargetKeys: string[]) => {
    setTargetKeys(newTargetKeys);
  };

  const handleMemberSave = () => {
    if (selectedGroup) {
      const currentMembers = selectedGroup.members?.map(m => m.id) || [];
      const newMembers = targetKeys.filter(k => !currentMembers.includes(k));

      if (newMembers.length > 0) {
        addMembersMutation.mutate({
          groupId: selectedGroup.id,
          userIds: newMembers,
        });
      }
      setIsMemberModalOpen(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="用户组管理"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['user-groups'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建用户组
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setTypeFilter}
            value={typeFilter || undefined}
          >
            <Select.Option value="department">部门</Select.Option>
            <Select.Option value="team">团队</Select.Option>
            <Select.Option value="project">项目</Select.Option>
            <Select.Option value="custom">自定义</Select.Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={groupsData?.groups || []}
          rowKey="id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: groupsData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建用户组模态框 */}
      <Modal
        title="新建用户组"
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
                label="组名称"
                name="name"
                rules={[{ required: true, message: '请输入组名称' }]}
              >
                <Input placeholder="请输入组名称（英文标识）" />
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
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="类型"
            name="group_type"
            initialValue="custom"
          >
            <Select>
              <Select.Option value="department">部门</Select.Option>
              <Select.Option value="team">团队</Select.Option>
              <Select.Option value="project">项目</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户组模态框 */}
      <Modal
        title="编辑用户组"
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
          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="请输入显示名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="类型" name="group_type">
            <Select>
              <Select.Option value="department">部门</Select.Option>
              <Select.Option value="team">团队</Select.Option>
              <Select.Option value="project">项目</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 成员管理模态框 */}
      <Modal
        title={`成员管理 - ${selectedGroup?.display_name || selectedGroup?.name}`}
        open={isMemberModalOpen}
        onCancel={() => setIsMemberModalOpen(false)}
        onOk={handleMemberSave}
        confirmLoading={addMembersMutation.isPending}
        width={700}
      >
        <Alert
          message="成员管理"
          description="将用户添加到组成员列表中。移动用户到右侧即可添加为成员。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        {isLoadingUsers ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : (
          <Transfer
            dataSource={allUsers.map((u: User) => ({
              key: u.id,
              title: `${u.display_name} (@${u.username})`,
              ...u,
            }))}
            targetKeys={targetKeys}
            onChange={handleMemberChange}
            render={(item) => item.title}
            titles={['所有用户', '组成员']}
            listStyle={{ width: 280, height: 350 }}
            showSearch
            filterOption={(inputValue, option) =>
              option.username.toLowerCase().includes(inputValue.toLowerCase()) ||
              option.display_name.toLowerCase().includes(inputValue.toLowerCase())
            }
          />
        )}
      </Modal>

      {/* 用户组详情抽屉 */}
      <Drawer
        title="用户组详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedGroup(null);
        }}
        width={600}
      >
        {selectedGroup && (
          <div>
            <Alert
              message={selectedGroup.display_name || selectedGroup.name}
              description={selectedGroup.description || '暂无描述'}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="组ID">{selectedGroup.id}</Descriptions.Item>
              <Descriptions.Item label="组标识">{selectedGroup.name}</Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag>{getTypeText(selectedGroup.group_type)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedGroup.is_active)}>
                  {getStatusText(selectedGroup.is_active)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="成员数">
                <Tag><TeamOutlined /> {selectedGroup.member_count} 人</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedGroup.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<UserAddOutlined />}
                onClick={() => {
                  setTargetKeys(selectedGroup.members?.map(m => m.id) || []);
                  setIsMemberModalOpen(true);
                }}
              >
                管理成员
              </Button>
              <Button
                block
                danger
                icon={<DeleteOutlined />}
                onClick={() => {
                  Modal.confirm({
                    title: '确认删除',
                    content: `确定要删除用户组 "${selectedGroup.display_name || selectedGroup.name}" 吗？`,
                    onOk: () => deleteMutation.mutate(selectedGroup.id),
                  });
                }}
              >
                删除用户组
              </Button>
            </Space>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default GroupsPage;
