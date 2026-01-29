/**
 * 数据服务接口管理组件
 * 支持 API 服务创建、API Key 管理、调用记录追踪、统计分析
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Space,
  Select,
  Input,
  Alert,
  Tag,
  Modal,
  Tooltip,
  Statistic,
  Row,
  Col,
  Descriptions,
  Form,
  message,
  Tabs,
  Badge,
  Switch,
  InputNumber,
  Progress,
  Typography,
  List,
  Empty,
  Spin,
} from 'antd';
import {
  ApiOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  KeyOutlined,
  HistoryOutlined,
  BarChartOutlined,
  CopyOutlined,
  CodeOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listDataServices,
  createDataService,
  updateDataService,
  deleteDataService,
  publishDataService,
  testDataService,
  listAPIKeys,
  createAPIKey,
  deleteAPIKey,
  deactivateAPIKey,
  getAPICallRecords,
  getServiceStatistics,
  getOverallStatistics,
} from '@/services/alldata';
import type {
  APIDataService,
  APIKeyInfo,
  APICallRecord,
  ServiceStatistics,
  OverallStatistics,
} from '@/services/alldata';
import './DataServiceManager.css';

const { Option } = Select;
const { Text, Paragraph, Title } = Typography;

interface DataServiceManagerProps {
  tenantId?: string;
}

export const DataServiceManager: React.FC<DataServiceManagerProps> = ({ tenantId = 'default' }) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('services');
  const [serviceModalVisible, setServiceModalVisible] = useState(false);
  const [apiKeyModalVisible, setApiKeyModalVisible] = useState(false);
  const [selectedService, setSelectedService] = useState<APIDataService | null>(null);
  const [newApiKeySecret, setNewApiKeySecret] = useState<string>('');

  const [form] = Form.useForm();
  const [apiKeyForm] = Form.useForm();

  // 获取数据服务列表
  const { data: servicesData, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
    queryKey: ['data-services'],
    queryFn: () => listDataServices(),
  });

  // 获取 API Keys
  const { data: apiKeysData, isLoading: apiKeysLoading, refetch: refetchApiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => listAPIKeys(),
  });

  // 获取调用记录
  const { data: callRecordsData, isLoading: recordsLoading } = useQuery({
    queryKey: ['api-call-records'],
    queryFn: () => getAPICallRecords({ limit: 50 }),
    enabled: activeTab === 'records',
  });

  // 获取整体统计
  const { data: overallStatsData, isLoading: statsLoading } = useQuery({
    queryKey: ['overall-stats'],
    queryFn: () => getOverallStatistics(24),
    enabled: activeTab === 'statistics',
  });

  // 创建服务
  const createServiceMutation = useMutation({
    mutationFn: createDataService,
    onSuccess: () => {
      message.success('服务创建成功');
      setServiceModalVisible(false);
      form.resetFields();
      refetchServices();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建失败');
    },
  });

  // 更新服务
  const updateServiceMutation = useMutation({
    mutationFn: ({ serviceId, updates }: { serviceId: string; updates: Partial<APIDataService> }) =>
      updateDataService(serviceId, updates),
    onSuccess: () => {
      message.success('服务更新成功');
      setServiceModalVisible(false);
      setSelectedService(null);
      refetchServices();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '更新失败');
    },
  });

  // 删除服务
  const deleteServiceMutation = useMutation({
    mutationFn: deleteDataService,
    onSuccess: () => {
      message.success('服务删除成功');
      refetchServices();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败');
    },
  });

  // 发布服务
  const publishServiceMutation = useMutation({
    mutationFn: publishDataService,
    onSuccess: () => {
      message.success('服务发布成功');
      refetchServices();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '发布失败');
    },
  });

  // 测试服务
  const testServiceMutation = useMutation({
    mutationFn: (serviceId: string) => testDataService(serviceId),
    onSuccess: (data) => {
      const result = data?.data;
      if (result?.success) {
        Modal.info({
          title: '测试成功',
          width: 600,
          content: (
            <div>
              <p>{result.message}</p>
              {result.test_result && (
                <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(result.test_result, null, 2)}
                </pre>
              )}
            </div>
          ),
        });
      } else {
        message.error(result?.message || '测试失败');
      }
    },
  });

  // 创建 API Key
  const createApiKeyMutation = useMutation({
    mutationFn: createAPIKey,
    onSuccess: (data) => {
      const result = data?.data;
      if (result?.key_secret) {
        setNewApiKeySecret(result.key_secret);
        message.success('API Key 创建成功，请妥善保管密钥');
      }
      setApiKeyModalVisible(false);
      apiKeyForm.resetFields();
      refetchApiKeys();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建失败');
    },
  });

  // 删除 API Key
  const deleteApiKeyMutation = useMutation({
    mutationFn: deleteAPIKey,
    onSuccess: () => {
      message.success('API Key 删除成功');
      refetchApiKeys();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败');
    },
  });

  // 停用 API Key
  const deactivateApiKeyMutation = useMutation({
    mutationFn: deactivateAPIKey,
    onSuccess: () => {
      message.success('API Key 已停用');
      refetchApiKeys();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '操作失败');
    },
  });

  const services = servicesData?.data?.services || [];
  const apiKeys = apiKeysData?.data?.keys || [];
  const callRecords = callRecordsData?.data?.records || [];
  const overallStats = overallStatsData?.data;

  const handleCreateService = () => {
    setSelectedService(null);
    form.resetFields();
    setServiceModalVisible(true);
  };

  const handleEditService = (service: APIDataService) => {
    setSelectedService(service);
    form.setFieldsValue(service);
    setServiceModalVisible(true);
  };

  const handleDeleteService = (serviceId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个数据服务吗？',
      onOk: () => deleteServiceMutation.mutate(serviceId),
    });
  };

  const handlePublishService = (serviceId: string) => {
    publishServiceMutation.mutate(serviceId);
  };

  const handleServiceSubmit = (values: any) => {
    if (selectedService) {
      updateServiceMutation.mutate({
        serviceId: selectedService.service_id,
        updates: values,
      });
    } else {
      createServiceMutation.mutate(values);
    }
  };

  const handleTestService = (serviceId: string) => {
    testServiceMutation.mutate(serviceId);
  };

  const handleCreateApiKey = () => {
    apiKeyForm.resetFields();
    setApiKeyModalVisible(true);
  };

  const handleCopyApiKey = (keySecret: string) => {
    navigator.clipboard.writeText(keySecret);
    message.success('已复制到剪贴板');
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      published: 'success',
      archived: 'warning',
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

  const getServiceTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      rest: 'blue',
      graphql: 'purple',
    };
    return colors[type] || 'default';
  };

  // 服务列表表格列
  const serviceColumns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: APIDataService) => (
        <Space>
          <ApiOutlined />
          <span>{text}</span>
          <Tag color={getStatusColor(record.status)}>{getStatusText(record.status)}</Tag>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'service_type',
      key: 'service_type',
      render: (type: string) => <Tag color={getServiceTypeColor(type)}>{type.toUpperCase()}</Tag>,
    },
    {
      title: '数据源',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type: string) => {
        const types: Record<string, string> = {
          table: '表',
          query: '查询',
          dataset: '数据集',
        };
        return types[type] || type;
      },
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      render: (text: string) => <code className="endpoint-code">{text}</code>,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method: string) => <Tag>{method}</Tag>,
    },
    {
      title: '调用次数',
      key: 'calls',
      render: (_: any, record: APIDataService) => {
        const stat = overallStats?.top_services?.find(s => s.service_id === record.service_id);
        return stat?.calls || 0;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: APIDataService) => (
        <Space size="small">
          <Tooltip title="测试">
            <Button
              type="text"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleTestService(record.service_id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditService(record)}
            />
          </Tooltip>
          {record.status === 'draft' && (
            <Tooltip title="发布">
              <Button
                type="text"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handlePublishService(record.service_id)}
              />
            </Tooltip>
          )}
          <Tooltip title="删除">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteService(record.service_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // API Keys 表格列
  const apiKeyColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Key ID',
      dataIndex: 'key_id',
      key: 'key_id',
      render: (text: string) => <code className="key-code">{text}</code>,
    },
    {
      title: '权限范围',
      dataIndex: 'scopes',
      key: 'scopes',
      render: (scopes: string[]) => (
        <Space size={4}>
          {scopes.map(scope => (
            <Tag key={scope} color="blue">{scope}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '最后使用',
      dataIndex: 'last_used',
      key: 'last_used',
      render: (text: string | null) => text ? new Date(text).toLocaleString() : '未使用',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Badge status={isActive ? 'success' : 'default'} text={isActive ? '活跃' : '已停用'} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: APIKeyInfo) => (
        <Space size="small">
          {record.is_active && (
            <Button
              type="text"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => deactivateApiKeyMutation.mutate(record.key_id)}
            >
              停用
            </Button>
          )}
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: '删除后无法恢复，确定要删除这个 API Key 吗？',
                onOk: () => deleteApiKeyMutation.mutate(record.key_id),
              });
            }}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="data-service-manager">
      <Card
        title={
          <Space>
            <ApiOutlined />
            <span>数据服务接口管理</span>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 数据服务标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <ApiOutlined />
                <span>数据服务</span>
                <Badge count={services.length} />
              </Space>
            }
            key="services"
          >
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateService}
              >
                新建服务
              </Button>
            </div>

            {servicesLoading ? (
              <Spin />
            ) : services.length > 0 ? (
              <Table
                columns={serviceColumns}
                dataSource={services}
                rowKey="service_id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无数据服务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>

          {/* API Keys 标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <KeyOutlined />
                <span>API Keys</span>
                <Badge count={apiKeys.length} />
              </Space>
            }
            key="apikeys"
          >
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateApiKey}
              >
                创建 API Key
              </Button>
            </div>

            <Alert
              message="API Key 用于调用已发布的数据服务接口"
              description="请妥善保管您的 API Key，创建后只会显示一次密钥"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            {apiKeysLoading ? (
              <Spin />
            ) : apiKeys.length > 0 ? (
              <Table
                columns={apiKeyColumns}
                dataSource={apiKeys}
                rowKey="key_id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无 API Key" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>

          {/* 调用记录标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <HistoryOutlined />
                <span>调用记录</span>
              </Space>
            }
            key="records"
          >
            {recordsLoading ? (
              <Spin />
            ) : callRecords.length > 0 ? (
              <Table
                columns={[
                  {
                    title: '时间',
                    dataIndex: 'timestamp',
                    key: 'timestamp',
                    render: (text: string) => new Date(text).toLocaleString(),
                    width: 180,
                  },
                  {
                    title: '服务',
                    dataIndex: 'service_id',
                    key: 'service_id',
                    render: (text: string) => {
                      const service = services.find(s => s.service_id === text);
                      return service?.name || text;
                    },
                  },
                  {
                    title: '方法',
                    dataIndex: 'method',
                    key: 'method',
                    width: 60,
                  },
                  {
                    title: '路径',
                    dataIndex: 'path',
                    key: 'path',
                    ellipsis: true,
                  },
                  {
                    title: '状态码',
                    dataIndex: 'status_code',
                    key: 'status_code',
                    width: 80,
                    render: (code: number) => (
                      <Tag color={code >= 200 && code < 300 ? 'success' : code >= 400 ? 'error' : 'warning'}>
                        {code}
                      </Tag>
                    ),
                  },
                  {
                    title: '延迟',
                    dataIndex: 'latency_ms',
                    key: 'latency_ms',
                    width: 100,
                    render: (ms: number) => `${ms} ms`,
                  },
                ]}
                dataSource={callRecords}
                rowKey="call_id"
                pagination={{ pageSize: 20 }}
                size="small"
              />
            ) : (
              <Empty description="暂无调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>

          {/* 统计分析标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <BarChartOutlined />
                <span>统计分析</span>
              </Space>
            }
            key="statistics"
          >
            {statsLoading ? (
              <Spin />
            ) : overallStats ? (
              <>
                {/* 整体统计 */}
                <Card size="small" title="整体概览" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={4}>
                      <Statistic
                        title="总调用次数"
                        value={overallStats.total_calls}
                        prefix={<ApiOutlined />}
                      />
                    </Col>
                    <Col span={4}>
                      <Statistic
                        title="成功率"
                        value={(overallStats.success_rate * 100).toFixed(2)}
                        suffix="%"
                        valueStyle={{ color: overallStats.success_rate >= 0.95 ? '#52c41a' : '#faad14' }}
                      />
                    </Col>
                    <Col span={4}>
                      <Statistic
                        title="活跃服务"
                        value={overallStats.active_services}
                      />
                    </Col>
                    <Col span={4}>
                      <Statistic
                        title="活跃 Keys"
                        value={overallStats.active_keys}
                      />
                    </Col>
                    <Col span={4}>
                      <Statistic
                        title="失败调用"
                        value={overallStats.failed_calls}
                        valueStyle={{ color: overallStats.failed_calls > 0 ? '#ff4d4f' : undefined }}
                      />
                    </Col>
                    <Col span={4}>
                      <Statistic
                        title="QPS"
                        value={overallStats.total_calls / (24 * 3600)}
                        precision={2}
                        suffix="/s"
                      />
                    </Col>
                  </Row>
                </Card>

                {/* 状态码分布 */}
                <Card size="small" title="状态码分布" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    {Object.entries(overallStats.status_codes || {}).map(([code, count]) => (
                      <Col span={4} key={code}>
                        <Statistic
                          title={`HTTP ${code}`}
                          value={count}
                          valueStyle={{
                            color: code.startsWith('2') ? '#52c41a' : code.startsWith('4') ? '#faad14' : '#ff4d4f',
                          }}
                        />
                      </Col>
                    ))}
                  </Row>
                </Card>

                {/* 热门服务 */}
                {overallStats.top_services && overallStats.top_services.length > 0 && (
                  <Card size="small" title="热门服务">
                    <List
                      dataSource={overallStats.top_services}
                      renderItem={(item) => {
                        const service = services.find(s => s.service_id === item.service_id);
                        return (
                          <List.Item>
                            <List.Item.Meta
                              title={service?.name || item.service_id}
                              description={`调用次数: ${item.calls}，失败: ${item.errors}`}
                            />
                            <Progress
                              percent={item.calls > 0 ? ((item.calls - item.errors) / item.calls * 100) : 0}
                              size="small"
                              status={item.errors === 0 ? 'success' : 'exception'}
                              style={{ width: 150 }}
                            />
                          </List.Item>
                        );
                      }}
                    />
                  </Card>
                )}
              </>
            ) : (
              <Empty description="暂无统计数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 创建/编辑服务弹窗 */}
      <Modal
        title={selectedService ? '编辑数据服务' : '新建数据服务'}
        open={serviceModalVisible}
        onCancel={() => setServiceModalVisible(false)}
        onOk={() => form.submit()}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleServiceSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="服务名称"
                rules={[{ required: true, message: '请输入服务名称' }]}
              >
                <Input placeholder="例如：用户数据查询服务" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="service_type"
                label="服务类型"
                rules={[{ required: true, message: '请选择服务类型' }]}
              >
                <Select placeholder="选择类型">
                  <Option value="rest">REST API</Option>
                  <Option value="graphql">GraphQL</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="服务描述"
          >
            <Input.TextArea rows={2} placeholder="描述该服务的用途" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="source_type"
                label="数据源类型"
                rules={[{ required: true, message: '请选择数据源类型' }]}
              >
                <Select placeholder="选择类型">
                  <Option value="table">表</Option>
                  <Option value="query">SQL 查询</Option>
                  <Option value="dataset">数据集</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="method"
                label="HTTP 方法"
                initialValue="GET"
              >
                <Select>
                  <Option value="GET">GET</Option>
                  <Option value="POST">POST</Option>
                  <Option value="PUT">PUT</Option>
                  <Option value="DELETE">DELETE</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="endpoint"
            label="API 端点"
            rules={[{ required: true, message: '请输入 API 端点' }]}
          >
            <Input placeholder="/api/v1/data/users" />
          </Form.Item>

          <Form.Item
            name="rate_limit"
            label="速率限制"
          >
            <InputNumber
              placeholder="每分钟请求数"
              style={{ width: '100%' }}
              addonAfter="次/分钟"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建 API Key 弹窗 */}
      <Modal
        title="创建 API Key"
        open={apiKeyModalVisible}
        onCancel={() => setApiKeyModalVisible(false)}
        onOk={() => apiKeyForm.submit()}
        width={500}
      >
        <Form
          form={apiKeyForm}
          layout="vertical"
          onFinish={(values) => {
            createApiKeyMutation.mutate(values);
          }}
        >
          <Form.Item
            name="name"
            label="Key 名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="例如：生产环境 Key" />
          </Form.Item>

          <Form.Item
            name="scopes"
            label="权限范围"
            rules={[{ required: true, message: '请选择权限' }]}
            initialValue={['read']}
          >
            <Select mode="multiple" placeholder="选择权限">
              <Option value="read">只读</Option>
              <Option value="write">读写</Option>
              <Option value="admin">管理员</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="expires_days"
            label="过期时间"
            initialValue={365}
          >
            <Select>
              <Option value={30}>30 天</Option>
              <Option value={90}>90 天</Option>
              <Option value={180}>180 天</Option>
              <Option value={365}>1 年</Option>
              <Option value={null}>永久有效</Option>
            </Select>
          </Form.Item>
        </Form>

        {newApiKeySecret && (
          <Alert
            message="请妥善保管您的 API Key"
            description={
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text copyable={{ text: newApiKeySecret }}>
                  <code className="api-key-secret">{newApiKeySecret}</code>
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  此密钥只会显示一次，请立即复制保存
                </Text>
              </Space>
            }
            type="warning"
            showIcon
          />
        )}
      </Modal>
    </div>
  );
};

export default DataServiceManager;
