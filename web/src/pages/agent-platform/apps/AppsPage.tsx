import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Row,
  Col,
  Statistic,
  Typography,
  Alert,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  ApiOutlined,
  KeyOutlined,
  BarChartOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import bisheng from '@/services/bisheng';
import type {
  PublishedApp,
  ApiKey,
  AppStatus,
} from '@/services/bisheng';

const { Option } = Select;
const { TextArea } = Input;
const { Text } = Typography;

function AppsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [isApiKeysModalOpen, setIsApiKeysModalOpen] = useState(false);
  const [isStatsModalOpen, setIsStatsModalOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState<PublishedApp | null>(null);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);

  const [form] = Form.useForm();
  const [publishForm] = Form.useForm();

  // 获取应用列表
  const { data: appsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['published-apps', page, pageSize, statusFilter, typeFilter],
    queryFn: () =>
      bisheng.getPublishedApps({
        page,
        page_size: pageSize,
        status: statusFilter as AppStatus || undefined,
        type: typeFilter || undefined,
      }),
  });

  // 创建应用
  const createMutation = useMutation({
    mutationFn: bisheng.createApp,
    onSuccess: () => {
      message.success('应用创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['published-apps'] });
    },
    onError: () => {
      message.error('应用创建失败');
    },
  });

  // 更新应用
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof bisheng.updateApp>[1] }) =>
      bisheng.updateApp(id, data),
    onSuccess: () => {
      message.success('应用更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['published-apps'] });
    },
    onError: () => {
      message.error('应用更新失败');
    },
  });

  // 发布应用
  const publishMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof bisheng.publishApp>[1] }) =>
      bisheng.publishApp(id, data),
    onSuccess: (result) => {
      message.success('应用发布成功');
      setIsPublishModalOpen(false);
      publishForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['published-apps'] });
      setSelectedApp((prev) => prev ? { ...prev, status: 'published' as const, endpoint: result.data.endpoint } : null);
    },
    onError: () => {
      message.error('应用发布失败');
    },
  });

  // 下线应用
  const unpublishMutation = useMutation({
    mutationFn: bisheng.unpublishApp,
    onSuccess: () => {
      message.success('应用已下线');
      queryClient.invalidateQueries({ queryKey: ['published-apps'] });
      setSelectedApp((prev) => prev ? { ...prev, status: 'draft' as const } : null);
    },
    onError: () => {
      message.error('应用下线失败');
    },
  });

  // 删除应用
  const deleteMutation = useMutation({
    mutationFn: bisheng.deleteApp,
    onSuccess: () => {
      message.success('应用删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['published-apps'] });
    },
    onError: () => {
      message.error('应用删除失败');
    },
  });

  // 创建 API Key
  const createKeyMutation = useMutation({
    mutationFn: (appId: string) => bisheng.createApiKey(appId),
    onSuccess: (result) => {
      message.success('API 密钥创建成功');
      setNewApiKey(result.data.key);
      queryClient.invalidateQueries({ queryKey: ['app-api-keys', selectedApp?.app_id] });
    },
    onError: () => {
      message.error('API 密钥创建失败');
    },
  });

  // 删除 API Key
  const deleteKeyMutation = useMutation({
    mutationFn: ({ appId, keyId }: { appId: string; keyId: string }) =>
      bisheng.deleteApiKey(appId, keyId),
    onSuccess: () => {
      message.success('API 密钥删除成功');
      queryClient.invalidateQueries({ queryKey: ['app-api-keys', selectedApp?.app_id] });
    },
    onError: () => {
      message.error('API 密钥删除失败');
    },
  });

  // 获取应用 API Keys
  const { data: apiKeysData } = useQuery({
    queryKey: ['app-api-keys', selectedApp?.app_id],
    queryFn: () => bisheng.getAppApiKeys(selectedApp!.app_id),
    enabled: !!selectedApp && isApiKeysModalOpen,
  });

  // 获取应用统计
  const { data: statsData } = useQuery({
    queryKey: ['app-statistics', selectedApp?.app_id],
    queryFn: () => bisheng.getAppStatistics(selectedApp!.app_id),
    enabled: !!selectedApp && isStatsModalOpen,
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      published: 'green',
      archived: 'orange',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      draft: '草稿',
      published: '已发布',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      chat: 'blue',
      workflow: 'purple',
      agent: 'green',
    };
    return colors[type] || 'default';
  };

  const getTypeText = (type: string) => {
    const texts: Record<string, string> = {
      chat: '对话应用',
      workflow: '工作流',
      agent: 'Agent',
    };
    return texts[type] || type;
  };

  const columns = [
    {
      title: '应用名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: PublishedApp) => (
        <a
          onClick={() => {
            setSelectedApp(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{getTypeText(type)}</Tag>
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
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag>v{version}</Tag>,
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => endpoint ? (
        <a href={endpoint} target="_blank" rel="noopener noreferrer">
          {endpoint}
        </a>
      ) : '-',
    },
    {
      title: 'API 密钥',
      dataIndex: 'api_key_count',
      key: 'api_key_count',
      width: 100,
      render: (count: number) => <Tag>{count} 个</Tag>,
    },
    {
      title: '访问次数',
      dataIndex: 'access_count',
      key: 'access_count',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '最后访问',
      dataIndex: 'last_accessed',
      key: 'last_accessed',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: PublishedApp) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedApp(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          {record.status === 'published' ? (
            <Popconfirm
              title="确定要下线这个应用吗？"
              onConfirm={() => unpublishMutation.mutate(record.app_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<CloseCircleOutlined />} />
            </Popconfirm>
          ) : (
            <Button
              type="text"
              icon={<RocketOutlined />}
              onClick={() => {
                setSelectedApp(record);
                setIsPublishModalOpen(true);
              }}
            />
          )}
          <Popconfirm
            title="确定要删除这个应用吗？"
            onConfirm={() => deleteMutation.mutate(record.app_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
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
    form.validateFields().then((values) => {
      updateMutation.mutate({
        id: selectedApp!.app_id,
        data: values,
      });
    });
  };

  const handlePublish = () => {
    publishForm.validateFields().then((values) => {
      publishMutation.mutate({
        id: selectedApp!.app_id,
        data: values,
      });
    });
  };

  const apiKeysColumns = [
    {
      title: '密钥显示',
      dataIndex: 'key_display',
      key: 'key_display',
      render: (key: string) => <Tag style={{ fontFamily: 'monospace' }}>{key}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '使用次数',
      dataIndex: 'access_count',
      key: 'access_count',
    },
    {
      title: '最后使用',
      dataIndex: 'last_used',
      key: 'last_used',
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>{isActive ? '活跃' : '停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: ApiKey) => (
        <Popconfirm
          title="确定要删除这个密钥吗？"
          onConfirm={() => deleteKeyMutation.mutate({ appId: selectedApp!.app_id, keyId: record.key_id })}
          okText="确定"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="应用发布管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            创建应用
          </Button>
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
            <Option value="draft">草稿</Option>
            <Option value="published">已发布</Option>
            <Option value="archived">已归档</Option>
          </Select>
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setTypeFilter}
            value={typeFilter || undefined}
          >
            <Option value="chat">对话应用</Option>
            <Option value="workflow">工作流</Option>
            <Option value="agent">Agent</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={appsData?.data?.apps || []}
          rowKey="app_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: appsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建应用模态框 */}
      <Modal
        title="创建应用"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="应用名称"
            name="name"
            rules={[{ required: true, message: '请输入应用名称' }]}
          >
            <Input placeholder="请输入应用名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="应用类型"
            name="type"
            rules={[{ required: true, message: '请选择应用类型' }]}
          >
            <Select>
              <Option value="chat">对话应用</Option>
              <Option value="workflow">工作流</Option>
              <Option value="agent">Agent</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑应用模态框 */}
      <Modal
        title="编辑应用"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="应用名称"
            name="name"
            rules={[{ required: true, message: '请输入应用名称' }]}
          >
            <Input placeholder="请输入应用名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 发布应用模态框 */}
      <Modal
        title="发布应用"
        open={isPublishModalOpen}
        onOk={handlePublish}
        onCancel={() => {
          setIsPublishModalOpen(false);
          publishForm.resetFields();
        }}
        confirmLoading={publishMutation.isPending}
      >
        <Form form={publishForm} layout="vertical">
          <Form.Item label="版本号" name="version" initialValue="1.0.0">
            <Input placeholder="例如: 1.0.0" />
          </Form.Item>
          <Form.Item label="更新日志" name="changelog">
            <TextArea rows={3} placeholder="描述本次发布的内容和变更" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 应用详情抽屉 */}
      <Drawer
        title="应用详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedApp(null);
        }}
        width={700}
      >
        {selectedApp && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="应用名称" span={2}>
                {selectedApp.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedApp.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="应用类型">
                <Tag color={getTypeColor(selectedApp.type)}>{getTypeText(selectedApp.type)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedApp.status)}>{getStatusText(selectedApp.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                v{selectedApp.version}
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedApp.created_by}
              </Descriptions.Item>
              {selectedApp.endpoint && (
                <Descriptions.Item label="API 端点" span={2}>
                  <a href={selectedApp.endpoint} target="_blank" rel="noopener noreferrer">
                    {selectedApp.endpoint}
                  </a>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedApp.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedApp.published_at && (
                <Descriptions.Item label="发布时间" span={2}>
                  {dayjs(selectedApp.published_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="标签" span={2}>
                {selectedApp.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={8}>
                <Statistic title="API 密钥" value={selectedApp.api_key_count} prefix={<KeyOutlined />} />
              </Col>
              <Col span={8}>
                <Statistic title="访问次数" value={selectedApp.access_count} prefix={<BarChartOutlined />} />
              </Col>
              <Col span={8}>
                <Statistic
                  title="最后访问"
                  value={selectedApp.last_accessed ? dayjs(selectedApp.last_accessed).fromNow() : '-'}
                  prefix={<ThunderboltOutlined />}
                />
              </Col>
            </Row>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<ApiOutlined />}
                  onClick={() => {
                    setNewApiKey(null);
                    setIsApiKeysModalOpen(true);
                  }}
                >
                  管理 API 密钥
                </Button>
                <Button
                  icon={<BarChartOutlined />}
                  onClick={() => setIsStatsModalOpen(true)}
                >
                  访问统计
                </Button>
                {selectedApp.status !== 'published' && (
                  <Button
                    type="primary"
                    icon={<RocketOutlined />}
                    onClick={() => setIsPublishModalOpen(true)}
                  >
                    发布应用
                  </Button>
                )}
                {selectedApp.status === 'published' && (
                  <Button
                    icon={<EditOutlined />}
                    onClick={() => {
                      form.setFieldsValue(selectedApp);
                      setIsEditModalOpen(true);
                    }}
                  >
                    编辑
                  </Button>
                )}
                <Popconfirm
                  title="确定要删除这个应用吗？"
                  onConfirm={() => deleteMutation.mutate(selectedApp.app_id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* API 密钥管理模态框 */}
      <Modal
        title="API 密钥管理"
        open={isApiKeysModalOpen}
        onCancel={() => {
          setIsApiKeysModalOpen(false);
          setNewApiKey(null);
        }}
        footer={[
          <Button key="close" onClick={() => setIsApiKeysModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {newApiKey && (
          <Alert
            style={{ marginBottom: 16 }}
            type="success"
            message="新 API 密钥已创建"
            description={
              <div>
                <Text copyable={{ text: newApiKey }}>
                  {newApiKey}
                </Text>
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  请立即保存此密钥，关闭后将无法再次查看完整密钥
                </div>
              </div>
            }
            closable
            onClose={() => setNewApiKey(null)}
          />
        )}
        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => createKeyMutation.mutate(selectedApp!.app_id)}
          >
            创建密钥
          </Button>
        </div>
        <Table
          columns={apiKeysColumns}
          dataSource={apiKeysData?.data?.api_keys || []}
          rowKey="key_id"
          loading={!apiKeysData?.data}
          pagination={false}
        />
      </Modal>

      {/* 访问统计模态框 */}
      <Modal
        title="访问统计"
        open={isStatsModalOpen}
        onCancel={() => setIsStatsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsStatsModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {statsData?.data && (
          <Tabs
            items={[
              {
                key: 'overview',
                label: '概览',
                children: (
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title="总访问次数" value={statsData.data.total_access} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="独立用户" value={statsData.data.unique_users} />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="平均延迟"
                        value={statsData.data.avg_latency_ms}
                        suffix="ms"
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="错误率"
                        value={(statsData.data.error_rate * 100).toFixed(2)}
                        suffix="%"
                        valueStyle={{
                          color: statsData.data.error_rate > 0.05 ? '#cf1322' : '#3f8600',
                        }}
                      />
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'endpoints',
                label: '热门端点',
                children: (
                  <Table
                    size="small"
                    columns={[
                      { title: '端点', dataIndex: 'endpoint' },
                      { title: '访问次数', dataIndex: 'count' },
                    ]}
                    dataSource={statsData.data.top_endpoints}
                    pagination={false}
                  />
                ),
              },
              {
                key: 'timeline',
                label: '访问趋势',
                children: (
                  <div style={{ height: 200 }}>
                    {statsData.data.access_by_date.map((item) => (
                      <div key={item.date} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span>{item.date}</span>
                        <Tag>{item.count} 次</Tag>
                      </div>
                    ))}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Modal>
    </div>
  );
}

export default AppsPage;
