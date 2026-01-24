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

// Mock API functions (to be replaced with actual API calls)
const mockGroups = [
  {
    group_id: '1',
    group_name: '默认组',
    description: '系统默认用户组',
    max_qps: 100,
    max_tokens_per_day: 1000000,
    user_count: 5,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    group_id: '2',
    group_name: 'VIP 用户组',
    description: 'VIP 级别用户组，享受更高配额',
    max_qps: 1000,
    max_tokens_per_day: 10000000,
    user_count: 10,
    status: 'active',
    created_at: '2024-01-05T00:00:00Z',
  },
];

const mockUsers = [
  { user_id: '1', username: 'admin', full_name: '系统管理员' },
  { user_id: '2', username: 'developer', full_name: '开发工程师' },
  { user_id: '3', username: 'analyst', full_name: '数据分析师' },
];

const getGroups = async () => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { groups: mockGroups, total: mockGroups.length } };
};

// Placeholder for future use
// const getGroupMembers = async (groupId: string) => {
//   await new Promise((resolve) => setTimeout(resolve, 300));
//   return { data: { members: mockUsers.slice(0, groupId === '1' ? 2 : 1) } };
// };

const createGroup = async (data: any) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { group: { ...data, group_id: Date.now().toString(), created_at: new Date().toISOString() } } };
};

const updateGroup = async (_groupId: string, data: any) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { group: { ...data, group_id: _groupId } } };
};

const deleteGroup = async (_groupId: string) => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return { data: { success: true } };
};

interface UserGroup {
  group_id: string;
  group_name: string;
  description: string;
  max_qps: number;
  max_tokens_per_day: number;
  user_count: number;
  status: string;
  created_at: string;
}

function GroupsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<UserGroup | null>(null);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Queries
  const { data: groupsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['user-groups', page, pageSize, statusFilter],
    queryFn: () =>
      getGroups().then((res) => {
        let groups = res.data.groups;
                        if (statusFilter) groups = groups.filter((g) => g.status === statusFilter);
                        return { data: { groups: groups.slice((page - 1) * pageSize, page * pageSize), total: groups.length } };
                      }),
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

  const getStatusColor = (status: string) => {
    return status === 'active' ? 'success' : 'default';
  };

  const getStatusText = (status: string) => {
    return status === 'active' ? '正常' : '停用';
  };

  const columns = [
    {
      title: '组名称',
      dataIndex: 'group_name',
      key: 'group_name',
      render: (name: string, record: UserGroup) => (
        <a onClick={() => { setSelectedGroup(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'QPS 限制',
      dataIndex: 'max_qps',
      key: 'max_qps',
      render: (qps: number) => (
        <Tag color="blue"><ThunderboltOutlined /> {qps.toLocaleString()}</Tag>
      ),
    },
    {
      title: '日 Token 限制',
      dataIndex: 'max_tokens_per_day',
      key: 'max_tokens_per_day',
      render: (tokens: number) => `${(tokens / 10000).toFixed(0)} 万`,
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count: number) => (
        <Tag><TeamOutlined /> {count}</Tag>
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
              editForm.setFieldsValue(record);
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
        updateMutation.mutate({ groupId: selectedGroup.group_id, data: values });
      }
    });
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
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Select.Option value="active">正常</Select.Option>
            <Select.Option value="inactive">停用</Select.Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={groupsData?.data?.groups || []}
          rowKey="group_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: groupsData?.data?.total || 0,
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
          <Form.Item
            label="组名称"
            name="group_name"
            rules={[{ required: true, message: '请输入组名称' }]}
          >
            <Input placeholder="请输入组名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>

          <Divider orientation="left">流量控制</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="QPS 限制"
                name="max_qps"
                rules={[{ required: true, message: '请输入 QPS 限制' }]}
                initialValue={100}
              >
                <InputNumber
                  min={1}
                  max={10000}
                  style={{ width: '100%' }}
                  addonAfter="次/秒"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="日 Token 限制"
                name="max_tokens_per_day"
                rules={[{ required: true, message: '请输入 Token 限制' }]}
                initialValue={1000000}
              >
                <InputNumber
                  min={10000}
                  max={100000000}
                  step={10000}
                  style={{ width: '100%' }}
                  addonAfter="Token"
                />
              </Form.Item>
            </Col>
          </Row>

          <Alert
            message="提示"
            description="流量控制设置将应用于该组所有用户。设置后，该组用户的 API 调用将受到限制。"
            type="info"
            showIcon
          />
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
            label="组名称"
            name="group_name"
            rules={[{ required: true, message: '请输入组名称' }]}
          >
            <Input placeholder="请输入组名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>

          <Divider orientation="left">流量控制</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="QPS 限制"
                name="max_qps"
                rules={[{ required: true, message: '请输入 QPS 限制' }]}
              >
                <InputNumber
                  min={1}
                  max={10000}
                  style={{ width: '100%' }}
                  addonAfter="次/秒"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="日 Token 限制"
                name="max_tokens_per_day"
                rules={[{ required: true, message: '请输入 Token 限制' }]}
              >
                <InputNumber
                  min={10000}
                  max={100000000}
                  step={10000}
                  style={{ width: '100%' }}
                  addonAfter="Token"
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 成员管理模态框 */}
      <Modal
        title={`成员管理 - ${selectedGroup?.group_name}`}
        open={isMemberModalOpen}
        onCancel={() => setIsMemberModalOpen(false)}
        onOk={() => {
          message.success('成员更新成功');
          setIsMemberModalOpen(false);
        }}
        width={600}
      >
        <Alert
          message="成员管理"
          description="拖动用户在不同列表之间移动，添加或移除组成员。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Transfer
          dataSource={mockUsers.map((u) => ({ ...u, key: u.user_id }))}
          targetKeys={selectedGroup?.group_id === '1' ? ['1', '2'] : ['3']}
          render={(item) => `${item.full_name} (@${item.username})`}
          titles={['所有用户', '组成员']}
          onChange={(keys) => {
            console.log('Selected keys:', keys);
          }}
        />
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
              message={selectedGroup.group_name}
              description={selectedGroup.description}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="组ID">{selectedGroup.group_id}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedGroup.status)}>{getStatusText(selectedGroup.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="QPS 限制">
                <Tag color="blue"><ThunderboltOutlined /> {selectedGroup.max_qps.toLocaleString()} 次/秒</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="日 Token 限制">
                {(selectedGroup.max_tokens_per_day / 10000).toFixed(0)} 万 Token
              </Descriptions.Item>
              <Descriptions.Item label="用户数">
                <Tag><TeamOutlined /> {selectedGroup.user_count} 人</Tag>
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
                onClick={() => setIsMemberModalOpen(true)}
              >
                管理成员
              </Button>
              {selectedGroup.group_name !== '默认组' && (
                <Button
                  block
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    Modal.confirm({
                      title: '确认删除',
                      content: `确定要删除用户组 ${selectedGroup.group_name} 吗？`,
                      onOk: () => deleteMutation.mutate(selectedGroup.group_id),
                    });
                  }}
                >
                  删除用户组
                </Button>
              )}
            </Space>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default GroupsPage;
