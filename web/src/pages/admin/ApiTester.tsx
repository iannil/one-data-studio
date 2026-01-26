import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Select,
  Tag,
  Space,
  Table,
  Descriptions,
  message,
  Drawer,
  Collapse,
  Badge,
  Statistic,
  Row,
  Col,
  Alert,
  Empty,
} from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import admin from '@/services/admin';

const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;

interface ApiEndpoint {
  endpoint_id: string;
  path: string;
  method: string;
  service: string;
  description: string;
  summary?: string;
  parameters?: Array<{ name: string; type: string; in: string; description: string }>;
  query_params?: Array<{ name: string; type: string; description: string }>;
  body_params?: Array<{ name: string; type: string; description: string }>;
  request_schema?: any;
  requires_auth: boolean;
  call_count: number;
  avg_duration_ms: number;
}

interface ApiTestResult {
  status_code: number;
  status_text: string;
  headers: Record<string, string>;
  body: any;
  duration_ms: number;
  error?: string;
}

function ApiTester() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();

  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [testResult, setTestResult] = useState<ApiTestResult | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // 获取API端点列表
  const { data: endpointsData, isLoading } = useQuery({
    queryKey: ['api-endpoints'],
    queryFn: () => admin.getApiEndpoints(),
  });

  const endpoints = endpointsData?.data?.endpoints || [];

  // 测试API
  const testMutation = useMutation({
    mutationFn: (params: { endpointId: string; data: Parameters<typeof admin.testApi>[1] }) =>
      admin.testApi(params.endpointId, params.data),
    onSuccess: (data) => {
      setTestResult(data.data);
    },
  });

  // API统计
  const { data: statsData } = useQuery({
    queryKey: ['api-stats'],
    queryFn: () => admin.getApiStats(),
  });

  const stats = statsData?.data;

  const methodColors: Record<string, string> = {
    GET: 'green',
    POST: 'blue',
    PUT: 'orange',
    DELETE: 'red',
    PATCH: 'cyan',
  };

  const columns = [
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method: string) => (
        <Tag color={methodColors[method] || 'default'}>{method}</Tag>
      ),
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (path: string) => <code>{path}</code>,
    },
    {
      title: '服务',
      dataIndex: 'service',
      key: 'service',
      render: (service: string) => <Tag>{service}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '性能',
      key: 'performance',
      render: (_: unknown, record: ApiEndpoint) => (
        <Space size="small">
          <span>{record.call_count} 次</span>
          {record.avg_duration_ms > 0 && (
            <span>({record.avg_duration_ms}ms)</span>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: ApiEndpoint) => (
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => {
            setSelectedEndpoint(record);
            setIsDrawerOpen(true);
            // 重置表单
            form.setFieldsValue({
              method: record.method,
              path: record.path,
            });
            setTestResult(null);
          }}
        >
          测试
        </Button>
      ),
    },
  ];

  const handleTest = async () => {
    if (!selectedEndpoint) return;

    const values = await form.validateFields();

    testMutation.mutate({
      endpoint_id: selectedEndpoint.endpoint_id,
      ...values,
    });
  };

  const getStatusIcon = (statusCode: number) => {
    if (statusCode >= 200 && statusCode < 300) {
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    } else if (statusCode >= 400 && statusCode < 500) {
      return <CloseCircleOutlined style={{ color: '#faad14' }} />;
    } else if (statusCode >= 500) {
      return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
    }
    return <ClockCircleOutlined style={{ color: '#999' }} />;
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="API总数"
              value={endpoints.length}
              prefix={<ApiOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日调用"
              value={stats?.total_calls || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="错误率"
              value={stats?.error_rate ? (stats.error_rate * 100).toFixed(2) : 0}
              suffix="%"
              valueStyle={{ color: stats?.error_rate > 0.05 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均响应"
              value={stats?.avg_duration || 0}
              suffix="ms"
            />
          </Card>
        </Col>
      </Row>

      {/* API端点列表 */}
      <Card
        title="API端点"
        extra={
          <Button
            icon={<ApiOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['api-endpoints'] })}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={endpoints}
          rowKey="endpoint_id"
          loading={isLoading}
          pagination={{
            pageSize: 50,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* API测试抽屉 */}
      <Drawer
        title="API 测试"
        placement="right"
        width={800}
        open={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedEndpoint(null);
          setTestResult(null);
        }}
      >
        {selectedEndpoint && (
          <>
            {/* 端点信息 */}
            <Card size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="方法">
                  <Tag color={methodColors[selectedEndpoint.method] || 'default'}>
                    {selectedEndpoint.method}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="路径">
                  <code>{selectedEndpoint.path}</code>
                </Descriptions.Item>
                <Descriptions.Item label="服务" span={2}>
                  <Tag>{selectedEndpoint.service}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="描述" span={2}>
                  {selectedEndpoint.description || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 参数配置 */}
            <Form
              form={form}
              layout="vertical"
              onFinish={handleTest}
              initialValues={{
                method: selectedEndpoint.method,
                path: selectedEndpoint.path,
              }}
            >
              {/* 路径参数 */}
              {selectedEndpoint.parameters && selectedEndpoint.parameters.length > 0 && (
                <Form.Item label="路径参数">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {selectedEndpoint.parameters.map((param) => (
                      <Form.Item
                        key={param.name}
                        name={`path_params.${param.name}`}
                        label={param.name}
                        style={{ marginBottom: 8 }}
                      >
                        <Input placeholder={`请输入${param.description || param.name} (${param.type})`} />
                      </Form.Item>
                    ))}
                  </Space>
                </Form.Item>
              )}

              {/* 查询参数 */}
              {selectedEndpoint.query_params && selectedEndpoint.query_params.length > 0 && (
                <Form.Item label="查询参数">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {selectedEndpoint.query_params.map((param) => (
                      <Form.Item
                        key={param.name}
                        name={`query_params.${param.name}`}
                        label={param.name}
                        style={{ marginBottom: 8 }}
                      >
                        <Input placeholder={`请输入${param.description || param.name} (${param.type})`} />
                      </Form.Item>
                    ))}
                  </Space>
                </Form.Item>
              )}

              {/* 请求体 */}
              {['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && (
                <Form.Item
                  label="请求体 (JSON)"
                  name="request_body"
                >
                  <TextArea
                    rows={6}
                    placeholder='{"key": "value"}'
                    style={{ fontFamily: 'Monaco, monospace' }}
                  />
                </Form.Item>
              )}

              {/* Headers */}
              <Form.Item label="请求头 (JSON)" name="headers">
                <TextArea
                  rows={3}
                  placeholder='{"Authorization": "Bearer token"}'
                  style={{ fontFamily: 'Monaco, monospace' }}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PlayCircleOutlined />}
                  loading={testMutation.isPending}
                >
                  发送请求
                </Button>
              </Form.Item>
            </Form>

            {/* 测试结果 */}
            {testResult && (
              <Card
                title="测试结果"
                size="small"
                style={{ marginTop: 16 }}
                extra={
                  <Badge
                    count={testResult.status_code}
                    status={testResult.status_code >= 400 ? 'error' : 'success'}
                  >
                    {testResult.status_text}
                  </Badge>
                }
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="状态码"
                      value={testResult.status_code}
                      prefix={getStatusIcon(testResult.status_code)}
                      valueStyle={{
                        color:
                          testResult.status_code >= 200 && testResult.status_code < 300
                            ? '#52c41a'
                            : testResult.status_code >= 400 && testResult.status_code < 500
                            ? '#faad14'
                            : '#f5222d',
                      }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="响应时间"
                      value={testResult.duration_ms}
                      suffix="ms"
                    />
                  </Col>
                </Row>

                <Collapse style={{ marginTop: 16 }}>
                  <Panel header="响应头" key="headers">
                    <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                      {Object.entries(testResult.headers || {}).map(([key, value]) => (
                        <div key={key} style={{ marginBottom: 4 }}>
                          <span style={{ fontWeight: 'bold' }}>{key}:</span>{' '}
                          <span style={{ fontFamily: 'monospace' }}>{value}</span>
                        </div>
                      ))}
                    </div>
                  </Panel>
                  <Panel header="响应体" key="body">
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        overflow: 'auto',
                        maxHeight: 400,
                        fontSize: 12,
                      }}
                    >
                      {typeof testResult.body === 'string'
                        ? testResult.body
                        : JSON.stringify(testResult.body, null, 2)}
                    </pre>
                    <Button
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => {
                        const content =
                          typeof testResult.body === 'string'
                            ? testResult.body
                            : JSON.stringify(testResult.body, null, 2);
                        navigator.clipboard.writeText(content);
                        message.success('已复制到剪贴板');
                      }}
                      style={{ marginTop: 8 }}
                    >
                      复制
                    </Button>
                  </Panel>
                </Collapse>
              </Card>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}

export default ApiTester;
