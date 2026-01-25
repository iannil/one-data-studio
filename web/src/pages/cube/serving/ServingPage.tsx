import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Statistic,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ExpandOutlined,
  CloudServerOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import cube from '@/services/cube';
import type { ServingService, CreateServingServiceRequest } from '@/services/cube';

const { Option } = Select;

function ServingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isScaleModalOpen, setIsScaleModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServingService | null>(null);

  const [form] = Form.useForm();
  const [scaleForm] = Form.useForm();

  // 获取服务列表
  const { data: servicesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['serving-services', page, pageSize, statusFilter],
    queryFn: () =>
      cube.getServingServices({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  // 创建服务
  const createMutation = useMutation({
    mutationFn: cube.createServingService,
    onSuccess: () => {
      message.success('服务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['serving-services'] });
    },
    onError: () => {
      message.error('服务创建失败');
    },
  });

  // 启动服务
  const startMutation = useMutation({
    mutationFn: cube.startServingService,
    onSuccess: () => {
      message.success('服务启动成功');
      queryClient.invalidateQueries({ queryKey: ['serving-services'] });
    },
    onError: () => {
      message.error('服务启动失败');
    },
  });

  // 停止服务
  const stopMutation = useMutation({
    mutationFn: cube.stopServingService,
    onSuccess: () => {
      message.success('服务已停止');
      queryClient.invalidateQueries({ queryKey: ['serving-services'] });
    },
    onError: () => {
      message.error('服务停止失败');
    },
  });

  // 删除服务
  const deleteMutation = useMutation({
    mutationFn: cube.deleteServingService,
    onSuccess: () => {
      message.success('服务删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['serving-services'] });
    },
    onError: () => {
      message.error('服务删除失败');
    },
  });

  // 扩缩容
  const scaleMutation = useMutation({
    mutationFn: ({ serviceId, replicas }: { serviceId: string; replicas: number }) =>
      cube.scaleServingService(serviceId, { replicas }),
    onSuccess: () => {
      message.success('扩缩容成功');
      setIsScaleModalOpen(false);
      scaleForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['serving-services'] });
    },
    onError: () => {
      message.error('扩缩容失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'green',
      stopped: 'default',
      starting: 'blue',
      stopping: 'orange',
      error: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      running: '运行中',
      stopped: '已停止',
      starting: '启动中',
      stopping: '停止中',
      error: '错误',
    };
    return texts[status] || status;
  };

  const renderReplicasProgress = (service: ServingService) => {
    if (!service.replicas || service.replicas.total === 0) return null;
    const percent = Math.round((service.replicas.available / service.replicas.total) * 100);
    return (
      <Progress
        percent={percent}
        size="small"
        format={() => `${service.replicas.available}/${service.replicas.total}`}
        status={service.status === 'running' ? 'success' : 'exception'}
      />
    );
  };

  const columns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ServingService) => (
        <a
          onClick={() => {
            setSelectedService(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      render: (name: string, record: ServingService) => (
        <Space>
          <span>{name}</span>
          <Tag>v{record.model_version}</Tag>
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
      title: '副本',
      key: 'replicas',
      width: 120,
      render: (_: unknown, record: ServingService) => renderReplicasProgress(record),
    },
    {
      title: 'QPS / 延迟',
      key: 'metrics',
      render: (_: unknown, record: ServingService) => {
        if (!record.metrics) return '-';
        return (
          <Space size="small">
            <Tag color="blue">{record.metrics.qps.toFixed(1)} QPS</Tag>
            <Tag>{record.metrics.avg_latency_ms.toFixed(1)}ms</Tag>
          </Space>
        );
      },
    },
    {
      title: '错误率',
      dataIndex: ['metrics', 'error_rate'],
      key: 'error_rate',
      width: 100,
      render: (rate?: number) => {
        if (rate === undefined) return '-';
        const color = rate > 0.05 ? 'red' : rate > 0.01 ? 'orange' : 'green';
        return <Tag color={color}>{(rate * 100).toFixed(2)}%</Tag>;
      },
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <a href={endpoint} target="_blank" rel="noopener noreferrer">
          {endpoint}
        </a>
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
      render: (_: unknown, record: ServingService) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedService(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          {record.status === 'stopped' ? (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.service_id)}
              loading={startMutation.isPending}
            />
          ) : record.status === 'running' ? (
            <>
              <Button
                type="text"
                icon={<ExpandOutlined />}
                onClick={() => {
                  setSelectedService(record);
                  scaleForm.setFieldsValue({ replicas: record.replicas.total });
                  setIsScaleModalOpen(true);
                }}
              />
              <Popconfirm
                title="确定要停止这个服务吗？"
                onConfirm={() => stopMutation.mutate(record.service_id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="text" danger icon={<StopOutlined />} />
              </Popconfirm>
            </>
          ) : null}
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
      const data: CreateServingServiceRequest = {
        ...values,
        resources: {
          cpu: `${values.cpu}核`,
          memory: `${values.memory}Gi`,
          gpu: values.gpu ? `${values.gpu}卡` : undefined,
        },
        autoscaling: values.enable_autoscaling
          ? {
              min_replicas: values.min_replicas,
              max_replicas: values.max_replicas,
              target_qps: values.target_qps,
            }
          : undefined,
      };
      createMutation.mutate(data);
    });
  };

  const handleScale = () => {
    scaleForm.validateFields().then((values) => {
      if (selectedService) {
        scaleMutation.mutate({
          serviceId: selectedService.service_id,
          replicas: values.replicas,
        });
      }
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="模型服务管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            部署服务
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
            <Option value="running">运行中</Option>
            <Option value="stopped">已停止</Option>
            <Option value="starting">启动中</Option>
            <Option value="error">错误</Option>
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
        title="部署模型服务"
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
          <Form.Item
            label="模型 ID"
            name="model_id"
            rules={[{ required: true, message: '请输入模型 ID' }]}
          >
            <Input placeholder="请输入已注册模型的 ID" />
          </Form.Item>
          <Form.Item
            label="模型版本"
            name="model_version"
            rules={[{ required: true, message: '请输入模型版本' }]}
          >
            <Input placeholder="例如: 1.0.0" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="副本数" name="replicas" initialValue={1}>
                <InputNumber min={1} max={16} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="CPU (核)" name="cpu" initialValue={2}>
                <InputNumber min={1} max={32} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="内存 (Gi)" name="memory" initialValue={4}>
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="GPU (卡)" name="gpu">
            <InputNumber min={0} max={8} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="启用自动扩缩容" name="enable_autoscaling" valuePropName="checked">
            <Select placeholder="是否启用">
              <Option value={false}>否</Option>
              <Option value={true}>是</Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="最小副本数" name="min_replicas" initialValue={1}>
                <InputNumber min={1} max={16} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="最大副本数" name="max_replicas" initialValue={5}>
                <InputNumber min={1} max={32} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="目标 QPS" name="target_qps">
            <InputNumber min={1} max={10000} style={{ width: '100%' }} placeholder="触发扩容的 QPS 阈值" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 扩缩容模态框 */}
      <Modal
        title="调整副本数"
        open={isScaleModalOpen}
        onOk={handleScale}
        onCancel={() => {
          setIsScaleModalOpen(false);
          scaleForm.resetFields();
        }}
        confirmLoading={scaleMutation.isPending}
      >
        <Form form={scaleForm} layout="vertical">
          <Form.Item
            label="副本数"
            name="replicas"
            rules={[{ required: true, message: '请输入副本数' }]}
          >
            <InputNumber min={1} max={32} style={{ width: '100%' }} />
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
        width={700}
      >
        {selectedService && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="服务名称" span={2}>
                {selectedService.name}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedService.status)}>
                  {getStatusText(selectedService.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型">
                {selectedService.model_name} v{selectedService.model_version}
              </Descriptions.Item>
              <Descriptions.Item label="端点" span={2}>
                <a href={selectedService.endpoint} target="_blank" rel="noopener noreferrer">
                  {selectedService.endpoint}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="副本状态" span={2}>
                <Progress
                  percent={
                    selectedService.replicas.total > 0
                      ? Math.round((selectedService.replicas.available / selectedService.replicas.total) * 100)
                      : 0
                  }
                  format={() => `${selectedService.replicas.available}/${selectedService.replicas.total}`}
                  status={selectedService.status === 'running' ? 'success' : 'exception'}
                />
              </Descriptions.Item>
            </Descriptions>

            {selectedService.metrics && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="服务指标">
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="QPS"
                        value={selectedService.metrics.qps}
                        precision={1}
                        suffix="req/s"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="平均延迟"
                        value={selectedService.metrics.avg_latency_ms}
                        precision={2}
                        suffix="ms"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="错误率"
                        value={selectedService.metrics.error_rate * 100}
                        precision={2}
                        suffix="%"
                        valueStyle={{
                          color:
                            selectedService.metrics.error_rate > 0.05
                              ? '#cf1322'
                              : selectedService.metrics.error_rate > 0.01
                                ? '#faad14'
                                : '#3f8600',
                        }}
                      />
                    </Col>
                  </Row>
                </Card>
              </div>
            )}

            <div style={{ marginTop: 16 }}>
              <Card size="small" title="资源配置">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="CPU">{selectedService.resources.cpu}</Descriptions.Item>
                  <Descriptions.Item label="内存">{selectedService.resources.memory}</Descriptions.Item>
                  {selectedService.resources.gpu && (
                    <Descriptions.Item label="GPU">{selectedService.resources.gpu}</Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            </div>

            {selectedService.autoscaling && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="自动扩缩容">
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="最小副本">{selectedService.autoscaling.min_replicas}</Descriptions.Item>
                    <Descriptions.Item label="最大副本">{selectedService.autoscaling.max_replicas}</Descriptions.Item>
                    {selectedService.autoscaling.target_qps && (
                      <Descriptions.Item label="目标 QPS">{selectedService.autoscaling.target_qps}</Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              </div>
            )}

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<LineChartOutlined />}
                  onClick={() => navigate(`/cube/serving/${selectedService.service_id}/metrics`)}
                >
                  查看指标
                </Button>
                <Button
                  icon={<CloudServerOutlined />}
                  onClick={() => navigate(`/cube/serving/${selectedService.service_id}/logs`)}
                >
                  查看日志
                </Button>
                {selectedService.status === 'running' && (
                  <>
                    <Button
                      icon={<ExpandOutlined />}
                      onClick={() => {
                        scaleForm.setFieldsValue({ replicas: selectedService.replicas.total });
                        setIsScaleModalOpen(true);
                      }}
                    >
                      扩缩容
                    </Button>
                    <Popconfirm
                      title="确定要停止这个服务吗？"
                      onConfirm={() => stopMutation.mutate(selectedService.service_id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button danger icon={<StopOutlined />}>
                        停止
                      </Button>
                    </Popconfirm>
                  </>
                )}
                {selectedService.status === 'stopped' && (
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => startMutation.mutate(selectedService.service_id)}
                    loading={startMutation.isPending}
                  >
                    启动
                  </Button>
                )}
                <Popconfirm
                  title="确定要删除这个服务吗？"
                  onConfirm={() => deleteMutation.mutate(selectedService.service_id)}
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
    </div>
  );
}

export default ServingPage;
