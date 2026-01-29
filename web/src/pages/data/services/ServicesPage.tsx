import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Card,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Drawer,
  Descriptions,
  Row,
  Col,
  Statistic,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  KeyOutlined,
  BarChartOutlined,
  RocketOutlined,
  StopOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { DataService, CreateDataServiceRequest, ApiKeyInfo } from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

function ServicesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<DataService | null>(null);

  const [form] = Form.useForm();

  // Queries
  const { data: servicesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['data-services', page, pageSize, typeFilter, statusFilter],
    queryFn: () =>
      alldata.getDataServices({
        page,
        page_size: pageSize,
        type: typeFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  const { data: statisticsData } = useQuery({
    queryKey: ['service-statistics', selectedService?.service_id],
    queryFn: () => alldata.getDataServiceStatistics(selectedService!.service_id),
    enabled: !!selectedService && isDetailDrawerOpen,
  });

  const { data: apiKeysData } = useQuery({
    queryKey: ['service-api-keys', selectedService?.service_id],
    queryFn: () => alldata.getServiceApiKeys(selectedService!.service_id),
    enabled: !!selectedService && isApiKeyModalOpen,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: alldata.createDataService,
    onSuccess: () => {
      message.success('服务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['data-services'] });
    },
    onError: () => {
      message.error('服务创建失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: alldata.deleteDataService,
    onSuccess: () => {
      message.success('服务删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['data-services'] });
    },
    onError: () => {
      message.error('服务删除失败');
    },
  });

  const publishMutation = useMutation({
    mutationFn: alldata.publishDataService,
    onSuccess: () => {
      message.success('服务发布成功');
      queryClient.invalidateQueries({ queryKey: ['data-services'] });
      queryClient.invalidateQueries({ queryKey: ['service-statistics'] });
    },
    onError: () => {
      message.error('服务发布失败');
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: alldata.unpublishDataService,
    onSuccess: () => {
      message.success('服务已下线');
      queryClient.invalidateQueries({ queryKey: ['data-services'] });
    },
    onError: () => {
      message.error('服务下线失败');
    },
  });

  const createApiKeyMutation = useMutation({
    mutationFn: () => alldata.createServiceApiKey(selectedService!.service_id),
    onSuccess: (data) => {
      message.success('API 密钥创建成功');
      queryClient.invalidateQueries({ queryKey: ['service-api-keys'] });
      // Show the key in a modal for copying
      Modal.info({
        title: 'API 密钥已创建',
        content: (
          <div>
            <p>请妥善保存您的 API 密钥，它只会显示一次：</p>
            <Input.TextArea
              value={data.data.key}
              autoSize={{ minRows: 2, maxRows: 4 }}
              readOnly
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
            <Button
              type="primary"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => {
                navigator.clipboard.writeText(data.data.key);
                message.success('已复制到剪贴板');
              }}
              style={{ marginTop: 8 }}
            >
              复制
            </Button>
          </div>
        ),
        okText: '关闭',
      });
    },
    onError: () => {
      message.error('API 密钥创建失败');
    },
  });

  const deleteApiKeyMutation = useMutation({
    mutationFn: (keyId: string) => alldata.deleteServiceApiKey(selectedService!.service_id, keyId),
    onSuccess: () => {
      message.success('API 密钥删除成功');
      queryClient.invalidateQueries({ queryKey: ['service-api-keys'] });
    },
    onError: () => {
      message.error('API 密钥删除失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      published: 'green',
      draft: 'default',
      archived: 'orange',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      published: '已发布',
      draft: '草稿',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DataService) => (
        <a onClick={() => { setSelectedService(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: '数据源类型',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type: string) => {
        const labels: Record<string, string> = {
          table: '表',
          query: '查询',
          dataset: '数据集',
        };
        return labels[type] || type;
      },
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
      title: '调用次数',
      key: 'calls',
      render: (_: unknown, record: DataService) =>
        record.statistics?.total_calls?.toLocaleString() || '-',
    },
    {
      title: 'QPS',
      key: 'qps',
      render: (_: unknown, record: DataService) => record.statistics?.qps || '-',
    },
    {
      title: '错误率',
      key: 'error_rate',
      render: (_: unknown, record: DataService) => {
        const rate = record.statistics?.error_rate;
        if (rate === undefined) return '-';
        const percent = (rate * 100).toFixed(2);
        return <span style={{ color: rate > 0.05 ? 'red' : 'inherit' }}>{percent}%</span>;
      },
    },
    {
      title: 'API 密钥',
      dataIndex: 'api_key_count',
      key: 'api_key_count',
      render: (count: number) => <Tag icon={<KeyOutlined />}>{count}</Tag>,
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
      width: 150,
      render: (_: unknown, record: DataService) => (
        <Space>
          <Button
            type="text"
            icon={<KeyOutlined />}
            onClick={() => { setSelectedService(record); setIsApiKeyModalOpen(true); }}
          />
          <Popconfirm
            title="确定要删除这个服务吗？"
            onConfirm={() => deleteMutation.mutate(record.service_id)}
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
      const data: CreateDataServiceRequest = {
        name: values.name,
        description: values.description,
        type: values.type,
        source_type: values.source_type,
        source_config: {},
      };
      createMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="数据服务管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            创建服务
          </Button>
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
            <Option value="rest">REST</Option>
            <Option value="graphql">GraphQL</Option>
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="published">已发布</Option>
            <Option value="draft">草稿</Option>
            <Option value="archived">已归档</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={servicesData?.data?.services || []}
          rowKey="service_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: servicesData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建服务模态框 */}
      <Modal
        title="创建数据服务"
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
            label="服务名称"
            name="name"
            rules={[{ required: true, message: '请输入服务名称' }]}
          >
            <Input placeholder="请输入服务名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="服务类型"
            name="type"
            rules={[{ required: true, message: '请选择服务类型' }]}
            initialValue="rest"
          >
            <Select>
              <Option value="rest">REST API</Option>
              <Option value="graphql">GraphQL</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="数据源类型"
            name="source_type"
            rules={[{ required: true, message: '请选择数据源类型' }]}
          >
            <Select>
              <Option value="table">数据表</Option>
              <Option value="query">自定义查询</Option>
              <Option value="dataset">数据集</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 服务详情抽屉 */}
      <Drawer
        title="服务详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedService(null);
        }}
        width={800}
      >
        {selectedService && (
          <div>
            <Descriptions title="基本信息" column={2} bordered size="small">
              <Descriptions.Item label="服务名称" span={2}>
                {selectedService.name}
              </Descriptions.Item>
              <Descriptions.Item label="服务ID" span={2}>
                <Input.TextArea
                  value={selectedService.service_id}
                  autoSize={{ minRows: 1, maxRows: 2 }}
                  readOnly
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag>{selectedService.type.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedService.status)}>{getStatusText(selectedService.status)}</Tag>
              </Descriptions.Item>
              {selectedService.endpoint && (
                <Descriptions.Item label="服务端点" span={2}>
                  <Input.TextArea
                    value={selectedService.endpoint}
                    autoSize={{ minRows: 1, maxRows: 2 }}
                    readOnly
                    style={{ fontFamily: 'monospace', fontSize: 12 }}
                  />
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建者">
                {selectedService.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedService.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24, textAlign: 'center' }}>
              {selectedService.status === 'published' ? (
                <Button
                  danger
                  icon={<StopOutlined />}
                  loading={unpublishMutation.isPending}
                  onClick={() => unpublishMutation.mutate(selectedService.service_id)}
                >
                  下线服务
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  loading={publishMutation.isPending}
                  onClick={() => publishMutation.mutate(selectedService.service_id)}
                >
                  发布服务
                </Button>
              )}
            </div>

            {statisticsData?.data && selectedService.status === 'published' && (
              <Card title={<><BarChartOutlined /> 调用统计</>} size="small" style={{ marginTop: 24 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="总调用次数"
                      value={statisticsData.data.total_calls}
                      formatter={(v) => v?.toLocaleString()}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="成功调用"
                      value={statisticsData.data.success_calls}
                      formatter={(v) => v?.toLocaleString()}
                      valueStyle={{ fontSize: 14, color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="失败调用"
                      value={statisticsData.data.error_calls}
                      formatter={(v) => v?.toLocaleString()}
                      valueStyle={{ fontSize: 14, color: '#ff4d4f' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="当前 QPS"
                      value={statisticsData.data.qps}
                      precision={2}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                </Row>
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <div>
                      <div style={{ fontSize: 12, color: '#999' }}>平均延迟</div>
                      <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                        {statisticsData.data.avg_latency_ms?.toFixed(2)} ms
                      </div>
                    </div>
                  </Col>
                  <Col span={8}>
                    <div>
                      <div style={{ fontSize: 12, color: '#999' }}>P95 延迟</div>
                      <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                        {statisticsData.data.p95_latency_ms?.toFixed(2)} ms
                      </div>
                    </div>
                  </Col>
                  <Col span={8}>
                    <div>
                      <div style={{ fontSize: 12, color: '#999' }}>P99 延迟</div>
                      <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                        {statisticsData.data.p99_latency_ms?.toFixed(2)} ms
                      </div>
                    </div>
                  </Col>
                </Row>
                {statisticsData.data.total_calls > 0 && statisticsData.data.error_calls > 0 && (
                  <Alert
                    style={{ marginTop: 16 }}
                    type="warning"
                    message={`错误率: ${((statisticsData.data.error_calls / statisticsData.data.total_calls) * 100).toFixed(2)}%`}
                  />
                )}
              </Card>
            )}
          </div>
        )}
      </Drawer>

      {/* API 密钥管理模态框 */}
      <Modal
        title="API 密钥管理"
        open={isApiKeyModalOpen}
        onCancel={() => {
          setIsApiKeyModalOpen(false);
          setSelectedService(null);
        }}
        footer={[
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            loading={createApiKeyMutation.isPending}
            onClick={() => createApiKeyMutation.mutate()}
          >
            创建密钥
          </Button>,
          <Button key="close" onClick={() => setIsApiKeyModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedService && (
          <div>
            <Alert
              message="提示"
              description="创建的 API 密钥只会显示一次，请妥善保存。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table
              columns={[
                {
                  title: '密钥',
                  dataIndex: 'key_display',
                  key: 'key_display',
                  render: (key: string) => (
                    <code style={{ fontSize: 12 }}>{key}</code>
                  ),
                },
                {
                  title: '状态',
                  dataIndex: 'is_active',
                  key: 'is_active',
                  render: (active: boolean) => (
                    <Tag color={active ? 'green' : 'red'}>
                      {active ? '启用' : '禁用'}
                    </Tag>
                  ),
                },
                {
                  title: '访问次数',
                  dataIndex: 'access_count',
                  key: 'access_count',
                },
                {
                  title: '操作',
                  key: 'actions',
                  render: (_: unknown, record: ApiKeyInfo) => (
                    <Popconfirm
                      title="确定要删除这个密钥吗？"
                      onConfirm={() => deleteApiKeyMutation.mutate(record.key_id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button type="link" danger size="small">
                        删除
                      </Button>
                    </Popconfirm>
                  ),
                },
              ]}
              dataSource={apiKeysData?.data?.api_keys || []}
              rowKey="key_id"
              pagination={false}
              size="small"
            />
          </div>
        )}
      </Modal>
    </div>
  );
}

export default ServicesPage;
