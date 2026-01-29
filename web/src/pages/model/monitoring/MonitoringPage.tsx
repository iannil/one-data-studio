import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Button,
  Select,
  Alert,
  Modal,
  Form,
  Input,
  InputNumber,
  message,
  Tabs,
  Badge,
  List,
  Switch,
  Radio,
} from 'antd';
import {
  WarningOutlined,
  BellOutlined,
  SettingOutlined,
  ReloadOutlined,
  DotChartOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import model from '@/services/model';
import type {
  MonitoringAlertRule,
  AlertNotification,
  MetricPeriod,
  AlertSeverity,
} from '@/services/model';
import MetricChart from '@/components/MetricChart';

const { Option } = Select;

const severityColors: Record<AlertSeverity, string> = {
  info: 'blue',
  warning: 'orange',
  error: 'red',
  critical: 'purple',
};

function MonitoringPage() {
  const queryClient = useQueryClient();
  const [, setPeriod] = useState<MetricPeriod>('1h');
  const [activeTab, setActiveTab] = useState('overview');

  // Modal states
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [isDashboardModalOpen, setIsDashboardModalOpen] = useState(false);

  const [ruleForm] = Form.useForm();
  const [dashboardForm] = Form.useForm();

  // 获取指标概览
  const { data: overviewData } = useQuery({
    queryKey: ['metricsOverview'],
    queryFn: model.getMetricsOverview,
    refetchInterval: 30000,
  });

  // 获取系统指标
  const { data: systemMetricsData } = useQuery({
    queryKey: ['systemMetrics'],
    queryFn: model.getSystemMetrics,
    refetchInterval: 5000,
  });

  // 获取告警规则
  const { data: alertRulesData, isLoading: isLoadingRules } = useQuery({
    queryKey: ['alertRules'],
    queryFn: () => model.getAlertRules(),
  });

  // 获取告警通知
  const { data: alertNotificationsData, isLoading: isLoadingNotifications } = useQuery({
    queryKey: ['alertNotifications'],
    queryFn: () => model.getAlertNotifications(),
    refetchInterval: 10000,
  });

  // 获取仪表板列表
  const { data: dashboardsData } = useQuery({
    queryKey: ['dashboards'],
    queryFn: () => model.getDashboards(),
    enabled: activeTab === 'dashboards',
  });

  // 获取训练任务列表
  const { data: trainingJobsData } = useQuery({
    queryKey: ['trainingJobs'],
    queryFn: () => model.getTrainingJobs({ page: 1, page_size: 10 }),
  });

  // Mutations
  const createRuleMutation = useMutation({
    mutationFn: model.createAlertRule,
    onSuccess: () => {
      message.success('告警规则创建成功');
      setIsRuleModalOpen(false);
      ruleForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: model.deleteAlertRule,
    onSuccess: () => {
      message.success('告警规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });

  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => model.toggleAlertRule(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });

  const acknowledgeNotificationMutation = useMutation({
    mutationFn: model.acknowledgeAlertNotification,
    onSuccess: () => {
      message.success('告警已确认');
      queryClient.invalidateQueries({ queryKey: ['alertNotifications'] });
    },
  });

  const resolveNotificationMutation = useMutation({
    mutationFn: model.resolveAlertNotification,
    onSuccess: () => {
      message.success('告警已解决');
      queryClient.invalidateQueries({ queryKey: ['alertNotifications'] });
    },
  });

  const createDashboardMutation = useMutation({
    mutationFn: model.createDashboard,
    onSuccess: () => {
      message.success('仪表板创建成功');
      setIsDashboardModalOpen(false);
      dashboardForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['dashboards'] });
    },
  });

  // 告警规则表格列
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '指标类型',
      dataIndex: 'metric_type',
      key: 'metric_type',
      width: 120,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '条件',
      key: 'condition',
      width: 120,
      render: (_: unknown, record: MonitoringAlertRule) => (
        <span>
          {record.condition} {record.threshold}
        </span>
      ),
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: AlertSeverity) => (
        <Tag color={severityColors[severity]}>{severity}</Tag>
      ),
    },
    {
      title: '目标类型',
      dataIndex: 'target_type',
      key: 'target_type',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record: MonitoringAlertRule) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleRuleMutation.mutate({ id: record.rule_id, enabled: checked })}
          disabled={toggleRuleMutation.isPending}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: MonitoringAlertRule) => (
        <Button
          type="link"
          danger
          onClick={() => deleteRuleMutation.mutate(record.rule_id)}
        >
          删除
        </Button>
      ),
    },
  ];

  // 告警通知表格列
  const notificationColumns = [
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: AlertSeverity) => (
        <Tag color={severityColors[severity]}>{severity}</Tag>
      ),
    },
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '告警信息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '当前值',
      dataIndex: 'metric_value',
      key: 'metric_value',
      width: 100,
      render: (val: number) => val.toFixed(2),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          active: { text: '活跃', color: 'error' },
          acknowledged: { text: '已确认', color: 'warning' },
          resolved: { text: '已解决', color: 'success' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: AlertNotification) => (
        <Space>
          {record.status === 'active' && (
            <Button
              type="link"
              size="small"
              onClick={() => acknowledgeNotificationMutation.mutate(record.notification_id)}
            >
              确认
            </Button>
          )}
          {record.status === 'acknowledged' && (
            <Button
              type="link"
              size="small"
              onClick={() => resolveNotificationMutation.mutate(record.notification_id)}
            >
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 模拟历史指标数据
  const generateMockMetrics = (baseValue: number, variance: number) => {
    const now = Date.now();
    return Array.from({ length: 24 }, (_, i) => ({
      timestamp: new Date(now - (23 - i) * 5 * 60 * 1000).toISOString(),
      value: baseValue + (Math.random() - 0.5) * variance,
    }));
  };

  const mockLossMetrics = generateMockMetrics(0.5, 0.3);
  const mockAccuracyMetrics = generateMockMetrics(85, 10);
  const mockGpuMetrics = generateMockMetrics(75, 30);
  const mockMemoryMetrics = generateMockMetrics(60, 20);

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="监控与告警"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries()}>
              刷新
            </Button>
            <Button icon={<SettingOutlined />} onClick={() => setIsRuleModalOpen(true)}>
              配置告警
            </Button>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: (
                <span>
                  <DashboardOutlined />
                  概览
                </span>
              ),
              children: (
                <div>
                  {/* 统计卡片 */}
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="活跃训练任务"
                          value={overviewData?.data?.active_jobs || 0}
                          prefix={<DotChartOutlined />}
                          valueStyle={{ color: '#1677ff' }}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="活跃服务"
                          value={overviewData?.data?.active_services || 0}
                          prefix={<ThunderboltOutlined />}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="GPU 使用率"
                          value={overviewData?.data?.avg_gpu_utilization?.toFixed(1) || 0}
                          suffix="%"
                          prefix={<DatabaseOutlined />}
                          valueStyle={{ color: '#faad14' }}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="活跃告警"
                          value={overviewData?.data?.active_alerts || 0}
                          prefix={<WarningOutlined />}
                          valueStyle={{
                            color: (overviewData?.data?.active_alerts || 0) > 0 ? '#ff4d4f' : '#52c41a',
                          }}
                        />
                        {(overviewData?.data?.critical_alerts || 0) > 0 && (
                          <Badge count={`${overviewData?.data?.critical_alerts} 严重`} style={{ backgroundColor: '#ff4d4f', marginTop: 8 }} />
                        )}
                      </Card>
                    </Col>
                  </Row>

                  {/* 实时指标图表 */}
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={12}>
                      <MetricChart
                        title="训练 Loss"
                        data={mockLossMetrics}
                        color="#ff4d4f"
                        height={200}
                        onPeriodChange={(value) => setPeriod(value as MetricPeriod)}
                      />
                    </Col>
                    <Col span={12}>
                      <MetricChart
                        title="训练 Accuracy"
                        data={mockAccuracyMetrics}
                        color="#52c41a"
                        unit="%"
                        height={200}
                        onPeriodChange={(value) => setPeriod(value as MetricPeriod)}
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <MetricChart
                        title="GPU 使用率"
                        data={mockGpuMetrics}
                        color="#faad14"
                        unit="%"
                        height={200}
                        onPeriodChange={(value) => setPeriod(value as MetricPeriod)}
                      />
                    </Col>
                    <Col span={12}>
                      <MetricChart
                        title="内存使用率"
                        data={mockMemoryMetrics}
                        color="#1677ff"
                        unit="%"
                        height={200}
                        onPeriodChange={(value) => setPeriod(value as MetricPeriod)}
                      />
                    </Col>
                  </Row>

                  {/* 系统资源状态 */}
                  {systemMetricsData?.data && (
                    <Card title="系统资源状态" style={{ marginTop: 16 }}>
                      <Row gutter={16}>
                        <Col span={6}>
                          <div style={{ marginBottom: 16 }}>
                            <div style={{ marginBottom: 8, color: '#666' }}>CPU 使用率</div>
                            <Progress
                              percent={systemMetricsData.data.cpu.usage_percent}
                              status={systemMetricsData.data.cpu.usage_percent > 80 ? 'exception' : 'normal'}
                            />
                          </div>
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 16 }}>
                            <div style={{ marginBottom: 8, color: '#666' }}>内存使用率</div>
                            <Progress
                              percent={systemMetricsData.data.memory.usage_percent}
                              status={systemMetricsData.data.memory.usage_percent > 80 ? 'exception' : 'normal'}
                            />
                            <div style={{ fontSize: 12, color: '#999' }}>
                              {systemMetricsData.data.memory.used_gb.toFixed(1)} / {systemMetricsData.data.memory.total_gb.toFixed(1)} GB
                            </div>
                          </div>
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 16 }}>
                            <div style={{ marginBottom: 8, color: '#666' }}>磁盘使用率</div>
                            <Progress
                              percent={systemMetricsData.data.disk.usage_percent}
                              status={systemMetricsData.data.disk.usage_percent > 80 ? 'exception' : 'normal'}
                            />
                            <div style={{ fontSize: 12, color: '#999' }}>
                              {systemMetricsData.data.disk.used_gb.toFixed(1)} / {systemMetricsData.data.disk.total_gb.toFixed(1)} GB
                            </div>
                          </div>
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 16 }}>
                            <div style={{ marginBottom: 8, color: '#666' }}>网络</div>
                            <Space direction="vertical" size={4}>
                              <div style={{ fontSize: 12 }}>
                                入站: {systemMetricsData.data.network.inbound_mbps.toFixed(1)} Mbps
                              </div>
                              <div style={{ fontSize: 12 }}>
                                出站: {systemMetricsData.data.network.outbound_mbps.toFixed(1)} Mbps
                              </div>
                            </Space>
                          </div>
                        </Col>
                      </Row>

                      {/* GPU 列表 */}
                      {systemMetricsData.data.gpu && systemMetricsData.data.gpu.length > 0 && (
                        <div style={{ marginTop: 24 }}>
                          <h4>GPU 状态</h4>
                          <Row gutter={16}>
                            {systemMetricsData.data.gpu.map((gpu, index) => (
                              <Col span={8} key={index} style={{ marginBottom: 16 }}>
                                <Card size="small">
                                  <div style={{ marginBottom: 8 }}>
                                    <strong>{gpu.name}</strong>
                                  </div>
                                  <Progress
                                    percent={gpu.utilization_percent}
                                    size="small"
                                    status={gpu.utilization_percent > 90 ? 'exception' : 'normal'}
                                  />
                                  <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                                    显存: {gpu.memory_used_mb} / {gpu.memory_total_mb} MB
                                    {gpu.temperature_c && (
                                      <span style={{ marginLeft: 16 }}>
                                        温度: {gpu.temperature_c}°C
                                      </span>
                                    )}
                                  </div>
                                </Card>
                              </Col>
                            ))}
                          </Row>
                        </div>
                      )}
                    </Card>
                  )}
                </div>
              ),
            },
            {
              key: 'alerts',
              label: (
                <span>
                  <BellOutlined />
                  告警
                </span>
              ),
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={12}>
                      <Card title="告警规则" size="small">
                        <div style={{ marginBottom: 8 }}>
                          <Button type="primary" size="small" onClick={() => setIsRuleModalOpen(true)}>
                            新建规则
                          </Button>
                        </div>
                        <Table
                          size="small"
                          columns={ruleColumns}
                          dataSource={alertRulesData?.data?.rules || []}
                          rowKey="rule_id"
                          loading={isLoadingRules}
                          pagination={false}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="活跃告警" size="small">
                        {alertNotificationsData?.data?.notifications.filter(
                          (n) => n.status === 'active'
                        ).length === 0 ? (
                          <Alert
                            message="暂无活跃告警"
                            type="success"
                            showIcon
                          />
                        ) : (
                          <List
                            size="small"
                            dataSource={alertNotificationsData?.data?.notifications.filter(
                              (n) => n.status === 'active'
                            ) || []}
                            renderItem={(item) => (
                              <List.Item>
                                <Space>
                                  <Tag color={severityColors[item.severity]}>{item.severity}</Tag>
                                  <span>{item.message}</span>
                                  <Button
                                    type="link"
                                    size="small"
                                    onClick={() => acknowledgeNotificationMutation.mutate(item.notification_id)}
                                  >
                                    确认
                                  </Button>
                                </Space>
                              </List.Item>
                            )}
                          />
                        )}
                      </Card>
                    </Col>
                  </Row>

                  <Card title="告警历史" size="small">
                    <Table
                      size="small"
                      columns={notificationColumns}
                      dataSource={alertNotificationsData?.data?.notifications || []}
                      rowKey="notification_id"
                      loading={isLoadingNotifications}
                      pagination={{ pageSize: 10 }}
                    />
                  </Card>
                </div>
              ),
            },
            {
              key: 'dashboards',
              label: (
                <span>
                  <DashboardOutlined />
                  仪表板
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsDashboardModalOpen(true)}>
                      创建仪表板
                    </Button>
                  </div>
                  <Row gutter={16}>
                    {dashboardsData?.data?.dashboards.map((dashboard) => (
                      <Col span={8} key={dashboard.dashboard_id} style={{ marginBottom: 16 }}>
                        <Card
                          title={dashboard.name}
                          size="small"
                          extra={<Tag>{dashboard.is_public ? '公开' : '私有'}</Tag>}
                          hoverable
                        >
                          <p style={{ color: '#666', marginBottom: 16 }}>
                            {dashboard.description || '暂无描述'}
                          </p>
                          <Space>
                            <span style={{ fontSize: 12, color: '#999' }}>
                              {dashboard.panels?.length || 0} 个面板
                            </span>
                            <Button type="link" size="small">
                              查看
                            </Button>
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </div>
              ),
            },
            {
              key: 'jobs',
              label: '训练任务监控',
              children: (
                <div>
                  <Alert
                    message="选择一个训练任务查看实时监控指标"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Table
                    columns={[
                      { title: '任务名称', dataIndex: 'name', key: 'name' },
                      { title: '模型', dataIndex: 'model_name', key: 'model_name' },
                      { title: '框架', dataIndex: 'framework', key: 'framework' },
                      {
                        title: '状态',
                        dataIndex: 'status',
                        key: 'status',
                        render: (status: string) => {
                          const statusMap: Record<string, { text: string; color: string }> = {
                            pending: { text: '等待中', color: 'default' },
                            running: { text: '运行中', color: 'processing' },
                            completed: { text: '已完成', color: 'success' },
                            failed: { text: '失败', color: 'error' },
                          };
                          const config = statusMap[status] || { text: status, color: 'default' };
                          return <Tag color={config.color}>{config.text}</Tag>;
                        },
                      },
                      {
                        title: '操作',
                        key: 'actions',
                        render: (_: unknown, _record: unknown) => (
                          <Button type="link" onClick={() => {}}>
                            查看监控
                          </Button>
                        ),
                      },
                    ]}
                    dataSource={trainingJobsData?.data?.jobs || []}
                    rowKey="job_id"
                    pagination={{ pageSize: 10 }}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 创建告警规则模态框 */}
      <Modal
        title="创建告警规则"
        open={isRuleModalOpen}
        onCancel={() => {
          setIsRuleModalOpen(false);
          ruleForm.resetFields();
        }}
        onOk={() => ruleForm.validateFields().then((values) => createRuleMutation.mutate(values))}
        confirmLoading={createRuleMutation.isPending}
        width={600}
      >
        <Form form={ruleForm} layout="vertical">
          <Form.Item label="规则名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="指标类型" name="metric_type" rules={[{ required: true }]}>
                <Select placeholder="选择指标类型">
                  <Option value="loss">Loss</Option>
                  <Option value="accuracy">Accuracy</Option>
                  <Option value="gpu_utilization">GPU 使用率</Option>
                  <Option value="memory_usage">内存使用率</Option>
                  <Option value="cpu_usage">CPU 使用率</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="目标类型" name="target_type" rules={[{ required: true }]}>
                <Select placeholder="选择目标类型">
                  <Option value="training">训练任务</Option>
                  <Option value="serving">模型服务</Option>
                  <Option value="resource">系统资源</Option>
                  <Option value="all">全部</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="条件" name="condition" rules={[{ required: true }]}>
                <Select placeholder="选择条件">
                  <Option value="greater_than">大于</Option>
                  <Option value="less_than">小于</Option>
                  <Option value="equal_to">等于</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="阈值" name="threshold" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} placeholder="输入阈值" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="严重级别" name="severity" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value="info">信息</Radio>
              <Radio value="warning">警告</Radio>
              <Radio value="error">错误</Radio>
              <Radio value="critical">严重</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="冷却时间（分钟）" name="cooldown_minutes" initialValue={5}>
            <InputNumber min={1} max={1440} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建仪表板模态框 */}
      <Modal
        title="创建仪表板"
        open={isDashboardModalOpen}
        onCancel={() => {
          setIsDashboardModalOpen(false);
          dashboardForm.resetFields();
        }}
        onOk={() => dashboardForm.validateFields().then((values) => createDashboardMutation.mutate(values))}
        confirmLoading={createDashboardMutation.isPending}
        width={500}
      >
        <Form form={dashboardForm} layout="vertical">
          <Form.Item label="仪表板名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="请输入仪表板名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="刷新间隔（秒）" name="refresh_interval" initialValue={30}>
            <InputNumber min={10} max={600} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="公开" name="is_public" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default MonitoringPage;
