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
  Tabs,
  Statistic,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  LineChartOutlined,
  FundOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type {
  Metric,
  CreateMetricRequest,
  MetricCategory,
  MetricAggregation,
  MetricValueType,
  MetricCalculationTask,
} from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

const categoryOptions: Array<{ value: MetricCategory; label: string; color: string }> = [
  { value: 'business', label: '业务指标', color: 'blue' },
  { value: 'technical', label: '技术指标', color: 'green' },
  { value: 'quality', label: '质量指标', color: 'orange' },
];

const valueTypeOptions: Array<{ value: MetricValueType; label: string }> = [
  { value: 'absolute', label: '绝对值' },
  { value: 'percentage', label: '百分比' },
  { value: 'rate', label: '比率' },
  { value: 'duration', label: '时长' },
];

const aggregationOptions: Array<{ value: MetricAggregation; label: string }> = [
  { value: 'sum', label: '求和' },
  { value: 'avg', label: '平均' },
  { value: 'min', label: '最小值' },
  { value: 'max', label: '最大值' },
  { value: 'count', label: '计数' },
  { value: 'distinct', label: '去重计数' },
];

function MetricsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [activeTab, setActiveTab] = useState('metrics');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isTrendModalOpen, setIsTrendModalOpen] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<Metric | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const [form] = Form.useForm();

  // 获取指标列表
  const { data: metricsData, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ['metrics', page, pageSize, categoryFilter, statusFilter],
    queryFn: () =>
      alldata.getMetrics({
        page,
        page_size: pageSize,
        category: categoryFilter as MetricCategory || undefined,
        status: statusFilter || undefined,
      }),
  });

  // 获取指标分类统计
  const { data: categoriesData } = useQuery({
    queryKey: ['metricCategories'],
    queryFn: alldata.getMetricCategories,
  });

  // 获取指标趋势数据
  const { data: trendData, isLoading: isLoadingTrend } = useQuery({
    queryKey: ['metricTrend', selectedMetric?.metric_id],
    queryFn: () =>
      alldata.getMetricTrend(selectedMetric!.metric_id, {
        start_time: dayjs().subtract(30, 'day').format('YYYY-MM-DD'),
        end_time: dayjs().format('YYYY-MM-DD'),
      }),
    enabled: isTrendModalOpen && selectedMetric !== null,
  });

  // 获取计算任务列表
  const { data: tasksData, isLoading: isLoadingTasks } = useQuery({
    queryKey: ['metricCalculationTasks'],
    queryFn: () => alldata.getMetricCalculationTasks({ page: 1, page_size: 50 }),
    enabled: activeTab === 'tasks',
  });

  // 创建指标
  const createMutation = useMutation({
    mutationFn: alldata.createMetric,
    onSuccess: () => {
      message.success('指标创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['metricCategories'] });
    },
    onError: () => {
      message.error('指标创建失败');
    },
  });

  // 更新指标
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof alldata.updateMetric>[1] }) =>
      alldata.updateMetric(id, data),
    onSuccess: () => {
      message.success('指标更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
    onError: () => {
      message.error('指标更新失败');
    },
  });

  // 删除指标
  const deleteMutation = useMutation({
    mutationFn: alldata.deleteMetric,
    onSuccess: () => {
      message.success('指标删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['metricCategories'] });
    },
    onError: () => {
      message.error('指标删除失败');
    },
  });

  // 批量删除指标
  const batchDeleteMutation = useMutation({
    mutationFn: alldata.batchDeleteMetrics,
    onSuccess: () => {
      message.success('批量删除成功');
      setSelectedRowKeys([]);
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['metricCategories'] });
    },
    onError: () => {
      message.error('批量删除失败');
    },
  });

  // 启动计算任务
  const startTaskMutation = useMutation({
    mutationFn: alldata.startMetricCalculationTask,
    onSuccess: () => {
      message.success('计算任务已启动');
      queryClient.invalidateQueries({ queryKey: ['metricCalculationTasks'] });
    },
    onError: () => {
      message.error('启动任务失败');
    },
  });

  // 停止计算任务
  const stopTaskMutation = useMutation({
    mutationFn: alldata.stopMetricCalculationTask,
    onSuccess: () => {
      message.success('计算任务已停止');
      queryClient.invalidateQueries({ queryKey: ['metricCalculationTasks'] });
    },
    onError: () => {
      message.error('停止任务失败');
    },
  });

  const getCategoryColor = (category: MetricCategory) => {
    return categoryOptions.find((c) => c.value === category)?.color || 'default';
  };

  const getCategoryLabel = (category: MetricCategory) => {
    return categoryOptions.find((c) => c.value === category)?.label || category;
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'green',
      deprecated: 'red',
      draft: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      active: '已激活',
      deprecated: '已废弃',
      draft: '草稿',
    };
    return texts[status] || status;
  };

  const getTaskStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'blue',
      completed: 'green',
      failed: 'red',
    };
    return colors[status] || 'default';
  };

  const metricColumns = [
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Metric) => (
        <a
          onClick={() => {
            setSelectedMetric(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '指标编码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <Tag color="purple">{code}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: MetricCategory) => <Tag color={getCategoryColor(category)}>{getCategoryLabel(category)}</Tag>,
    },
    {
      title: '值类型',
      dataIndex: 'value_type',
      key: 'value_type',
      render: (type: MetricValueType) => valueTypeOptions.find((t) => t.value === type)?.label || type,
    },
    {
      title: '聚合方式',
      dataIndex: 'aggregation',
      key: 'aggregation',
      render: (agg: MetricAggregation) => aggregationOptions.find((a) => a.value === agg)?.label || agg,
    },
    {
      title: '来源表',
      dataIndex: 'source_table',
      key: 'source_table',
    },
    {
      title: '负责人',
      dataIndex: 'owner',
      key: 'owner',
      render: (owner: string) => owner || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
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
      width: 150,
      render: (_: unknown, record: Metric) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedMetric(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedMetric(record);
              form.setFieldsValue(record);
              setIsEditModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个指标吗？"
            onConfirm={() => deleteMutation.mutate(record.metric_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '指标数量',
      dataIndex: 'metric_ids',
      key: 'metric_ids',
      render: (ids: string[]) => ids.length,
    },
    {
      title: '调度类型',
      dataIndex: ['schedule', 'type'],
      key: 'schedule_type',
      render: (type: string) => {
        const texts: Record<string, string> = {
          cron: 'Cron 表达式',
          interval: '间隔执行',
          once: '单次执行',
        };
        return texts[type] || '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={getTaskStatusColor(status)}>{status}</Tag>,
    },
    {
      title: '最后运行',
      dataIndex: 'last_run',
      key: 'last_run',
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '成功率',
      key: 'success_rate',
      render: (_: unknown, record: MetricCalculationTask) => {
        if (!record.statistics || record.statistics.total_runs === 0) return '-';
        const rate = (record.statistics.success_runs / record.statistics.total_runs) * 100;
        return <Progress percent={Math.round(rate)} size="small" />;
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: MetricCalculationTask) => (
        <Space>
          {record.status !== 'running' ? (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => startTaskMutation.mutate(record.task_id)}
            >
              启动
            </Button>
          ) : (
            <Button
              type="text"
              danger
              onClick={() => stopTaskMutation.mutate(record.task_id)}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateMetricRequest = {
        name: values.name,
        code: values.code,
        description: values.description,
        category: values.category,
        value_type: values.value_type,
        unit: values.unit,
        formula: values.formula,
        source_table: values.source_table,
        source_column: values.source_column,
        dimensions: values.dimensions,
        aggregation: values.aggregation,
        tags: values.tags,
        owner: values.owner,
        department: values.department,
      };
      createMutation.mutate(data);
    });
  };

  const handleUpdate = () => {
    form.validateFields().then((values) => {
      updateMutation.mutate({
        id: selectedMetric!.metric_id,
        data: {
          name: values.name,
          description: values.description,
          formula: values.formula,
          source_table: values.source_table,
          source_column: values.source_column,
          dimensions: values.dimensions,
          aggregation: values.aggregation,
          tags: values.tags,
          owner: values.owner,
          department: values.department,
          status: values.status,
        },
      });
    });
  };

  const renderMetricForm = (isEdit = false) => (
    <>
      <Form.Item label="指标名称" name="name" rules={[{ required: true, message: '请输入指标名称' }]}>
        <Input placeholder="请输入指标名称" disabled={isEdit} />
      </Form.Item>
      <Form.Item label="指标编码" name="code" rules={[{ required: true, message: '请输入指标编码' }]}>
        <Input placeholder="如: daily_active_users" disabled={isEdit} />
      </Form.Item>
      <Form.Item label="描述" name="description">
        <TextArea rows={2} placeholder="请输入指标描述" />
      </Form.Item>
      <Form.Item label="分类" name="category" rules={[{ required: true, message: '请选择分类' }]}>
        <Select placeholder="请选择分类">
          {categoryOptions.map((cat) => (
            <Option key={cat.value} value={cat.value}>
              {cat.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="值类型" name="value_type" rules={[{ required: true, message: '请选择值类型' }]}>
        <Select placeholder="请选择值类型">
          {valueTypeOptions.map((type) => (
            <Option key={type.value} value={type.value}>
              {type.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="聚合方式" name="aggregation" rules={[{ required: true, message: '请选择聚合方式' }]}>
        <Select placeholder="请选择聚合方式">
          {aggregationOptions.map((agg) => (
            <Option key={agg.value} value={agg.value}>
              {agg.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="单位" name="unit">
        <Input placeholder="如: 元、次、%" />
      </Form.Item>
      <Form.Item label="数据来源表" name="source_table" rules={[{ required: true, message: '请输入数据来源表' }]}>
        <Input placeholder="如: user_events" />
      </Form.Item>
      <Form.Item label="数据来源字段" name="source_column">
        <Input placeholder="如: user_id" />
      </Form.Item>
      <Form.Item label="维度" name="dimensions">
        <Select mode="tags" placeholder="选择或输入维度字段，如: date, region" />
      </Form.Item>
      <Form.Item label="计算公式" name="formula">
        <TextArea rows={3} placeholder="可选：输入 SQL 计算公式" />
      </Form.Item>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="负责人" name="owner">
            <Input placeholder="请输入负责人" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="部门" name="department">
            <Input placeholder="请输入部门" />
          </Form.Item>
        </Col>
      </Row>
      {isEdit && (
        <Form.Item label="状态" name="status">
          <Select>
            <Option value="active">已激活</Option>
            <Option value="draft">草稿</Option>
            <Option value="deprecated">已废弃</Option>
          </Select>
        </Form.Item>
      )}
      <Form.Item label="标签" name="tags">
        <Select mode="tags" placeholder="输入标签后按回车" />
      </Form.Item>
    </>
  );

  const tabItems = [
    {
      key: 'metrics',
      label: '指标管理',
      children: (
        <Card
          title="指标管理"
          extra={
            <Space>
              {selectedRowKeys.length > 0 && (
                <Popconfirm
                  title={`确定要删除选中的 ${selectedRowKeys.length} 个指标吗？`}
                  onConfirm={() => batchDeleteMutation.mutate(selectedRowKeys as string[])}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger>批量删除</Button>
                </Popconfirm>
              )}
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                新建指标
              </Button>
            </Space>
          }
        >
          <Space style={{ marginBottom: 16 }} size="middle">
            <Select
              placeholder="分类筛选"
              allowClear
              style={{ width: 150 }}
              onChange={setCategoryFilter}
              value={categoryFilter || undefined}
            >
              {categoryOptions.map((cat) => (
                <Option key={cat.value} value={cat.value}>
                  {cat.label}
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
              <Option value="active">已激活</Option>
              <Option value="draft">草稿</Option>
              <Option value="deprecated">已废弃</Option>
            </Select>
          </Space>

          <Table
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            columns={metricColumns}
            dataSource={metricsData?.data?.metrics || []}
            rowKey="metric_id"
            loading={isLoadingMetrics}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: metricsData?.data?.total || 0,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (newPage, newPageSize) => {
                setPage(newPage);
                setPageSize(newPageSize || 10);
              },
            }}
          />
        </Card>
      ),
    },
    {
      key: 'tasks',
      label: '计算任务',
      children: (
        <Card title="指标计算任务">
          <Table
            columns={taskColumns}
            dataSource={tasksData?.data?.tasks || []}
            rowKey="task_id"
            loading={isLoadingTasks}
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'overview',
      label: '概览',
      children: (
        <Card title="指标概览">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="总指标数"
                value={categoriesData?.data?.total || 0}
                prefix={<FundOutlined />}
              />
            </Col>
            {categoriesData?.data?.categories.map((cat) => (
              <Col span={6} key={cat.category}>
                <Card size="small">
                  <Statistic
                    title={getCategoryLabel(cat.category)}
                    value={cat.count}
                    valueStyle={{ color: getCategoryColor(cat.category) }}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      {/* 创建指标模态框 */}
      <Modal
        title="新建指标"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          {renderMetricForm(false)}
        </Form>
      </Modal>

      {/* 编辑指标模态框 */}
      <Modal
        title="编辑指标"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          {renderMetricForm(true)}
        </Form>
      </Modal>

      {/* 指标详情抽屉 */}
      <Drawer
        title="指标详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedMetric(null);
        }}
        width={600}
      >
        {selectedMetric && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="指标名称" span={2}>
                {selectedMetric.name}
              </Descriptions.Item>
              <Descriptions.Item label="指标编码">
                <Tag color="purple">{selectedMetric.code}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="分类">
                <Tag color={getCategoryColor(selectedMetric.category)}>
                  {getCategoryLabel(selectedMetric.category)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="值类型">
                {valueTypeOptions.find((t) => t.value === selectedMetric.value_type)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="聚合方式">
                {aggregationOptions.find((a) => a.value === selectedMetric.aggregation)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="单位" span={2}>
                {selectedMetric.unit || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="来源表" span={2}>
                {selectedMetric.source_table}
                {selectedMetric.source_column && `.${selectedMetric.source_column}`}
              </Descriptions.Item>
              {selectedMetric.dimensions && selectedMetric.dimensions.length > 0 && (
                <Descriptions.Item label="维度" span={2}>
                  {selectedMetric.dimensions.map((d) => (
                    <Tag key={d}>{d}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {selectedMetric.formula && (
                <Descriptions.Item label="计算公式" span={2}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{selectedMetric.formula}</pre>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="负责人">
                {selectedMetric.owner || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="部门">
                {selectedMetric.department || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedMetric.status)}>
                  {getStatusText(selectedMetric.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedMetric.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedMetric.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedMetric.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24 }}>
              <Space>
                <Button
                  icon={<LineChartOutlined />}
                  onClick={() => setIsTrendModalOpen(true)}
                >
                  查看趋势
                </Button>
                <Button
                  icon={<PlayCircleOutlined />}
                  onClick={() => {
                    // 手动计算
                    alldata.calculateMetric(selectedMetric.metric_id).then(() => {
                      message.success('计算已启动');
                    });
                  }}
                >
                  立即计算
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* 趋势图表模态框 */}
      <Modal
        title={
          <span>
            <LineChartOutlined style={{ marginRight: 8 }} />
            {selectedMetric?.name} - 趋势图表
          </span>
        }
        open={isTrendModalOpen}
        onCancel={() => setIsTrendModalOpen(false)}
        footer={null}
        width={900}
      >
        {isLoadingTrend ? (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>加载中...</div>
        ) : trendData?.data?.data_points && trendData.data.data_points.length > 0 ? (
          <div>
            <div style={{ height: 300, display: 'flex', alignItems: 'flex-end', gap: 8, padding: '20px 0' }}>
              {trendData.data.data_points.map((point, index) => {
                const maxValue = Math.max(...trendData.data.data_points.map(p => p.value || 0));
                const height = maxValue > 0 ? ((point.value || 0) / maxValue) * 100 : 0;
                return (
                  <div
                    key={index}
                    style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                    }}
                  >
                    <div
                      style={{
                        width: '80%',
                        height: `${height}%`,
                        minHeight: 4,
                        background: '#1677ff',
                        borderRadius: '4px 4px 0 0',
                        transition: 'height 0.3s ease',
                      }}
                    />
                    <span style={{ fontSize: 10, marginTop: 4 }}>
                      {dayjs(point.timestamp).format('MM-DD')}
                    </span>
                  </div>
                );
              })}
            </div>
            <div style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              <Space size="large">
                <span>时间范围: 近30天</span>
                <span>数据点: {trendData.data.data_points.length} 个</span>
                <span>
                  最新值: {trendData.data.data_points[trendData.data.data_points.length - 1]?.value || '-'}
                </span>
              </Space>
            </div>
          </div>
        ) : (
          <div style={{ padding: '40px 0', textAlign: 'center', color: '#999' }}>
            暂无趋势数据，请先执行指标计算
          </div>
        )}
      </Modal>
    </div>
  );
}

export default MetricsPage;
