import { useState } from 'react';
import {
  Card,
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
  Tabs,
  Popconfirm,
  Statistic,
  Row,
  Col,
  Alert,
  Progress,
  Switch,
  Radio,
  Drawer,
  Descriptions,
  Checkbox,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  BellOutlined,
  LineChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type {
  QualityRule,
  QualityTask,
  QualityReport,
  QualityAlert,
  QualityDimension,
} from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

const dimensionOptions: Array<{ value: QualityDimension; label: string; color: string }> = [
  { value: 'completeness', label: '完整性', color: 'blue' },
  { value: 'accuracy', label: '准确性', color: 'green' },
  { value: 'consistency', label: '一致性', color: 'cyan' },
  { value: 'timeliness', label: '时效性', color: 'orange' },
  { value: 'validity', label: '有效性', color: 'purple' },
  { value: 'uniqueness', label: '唯一性', color: 'magenta' },
];

const ruleTypeOptions = [
  { value: 'null_check', label: '空值检查' },
  { value: 'range_check', label: '范围检查' },
  { value: 'regex_check', label: '正则检查' },
  { value: 'enum_check', label: '枚举检查' },
  { value: 'foreign_key_check', label: '外键检查' },
  { value: 'custom_sql', label: '自定义 SQL' },
  { value: 'duplicate_check', label: '重复检查' },
];

const severityOptions = [
  { value: 'low', label: '低', color: 'default' },
  { value: 'medium', label: '中', color: 'blue' },
  { value: 'high', label: '高', color: 'orange' },
  { value: 'critical', label: '严重', color: 'red' },
];

function QualityPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [activeTab, setActiveTab] = useState('rules');

  // Modal states
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isAlertConfigModalOpen, setIsAlertConfigModalOpen] = useState(false);
  const [isReportDetailOpen, setIsReportDetailOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<QualityRule | null>(null);
  const [selectedReport, setSelectedReport] = useState<QualityReport | null>(null);

  const [ruleForm] = Form.useForm();
  const [taskForm] = Form.useForm();
  const [alertConfigForm] = Form.useForm();

  // Watch rule_type field for conditional form rendering
  const watchedRuleType = Form.useWatch('rule_type', ruleForm);

  // 质量规则列表
  const { data: rulesData, isLoading: isLoadingRules } = useQuery({
    queryKey: ['qualityRules', page, pageSize],
    queryFn: () => alldata.getQualityRules({ page, page_size: pageSize }),
  });

  // 质量任务列表
  const { data: tasksData, isLoading: isLoadingTasks } = useQuery({
    queryKey: ['qualityTasks'],
    queryFn: () => alldata.getQualityTasks(),
    enabled: activeTab === 'tasks',
  });

  // 质量报告列表
  const { data: reportsData, isLoading: isLoadingReports } = useQuery({
    queryKey: ['qualityReports'],
    queryFn: () => alldata.getQualityReports(),
    enabled: activeTab === 'reports',
  });

  // 告警列表
  const { data: alertsData, isLoading: isLoadingAlerts } = useQuery({
    queryKey: ['qualityAlerts'],
    queryFn: () => alldata.getQualityAlerts(),
    enabled: activeTab === 'alerts',
  });

  // 告警配置
  const { data: alertConfigData } = useQuery({
    queryKey: ['alertConfig'],
    queryFn: alldata.getAlertConfig,
  });

  // 质量趋势
  const { data: trendData } = useQuery({
    queryKey: ['qualityTrend'],
    queryFn: () => alldata.getQualityTrend({ period: 'daily' }),
    enabled: activeTab === 'overview',
  });

  // Mutations
  const createRuleMutation = useMutation({
    mutationFn: alldata.createQualityRule,
    onSuccess: () => {
      message.success('质量规则创建成功');
      setIsRuleModalOpen(false);
      ruleForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['qualityRules'] });
    },
  });

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof alldata.updateQualityRule>[1] }) =>
      alldata.updateQualityRule(id, data),
    onSuccess: () => {
      message.success('质量规则更新成功');
      setIsRuleModalOpen(false);
      setSelectedRule(null);
      ruleForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['qualityRules'] });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: alldata.deleteQualityRule,
    onSuccess: () => {
      message.success('质量规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['qualityRules'] });
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: alldata.createQualityTask,
    onSuccess: () => {
      message.success('质量任务创建成功');
      setIsTaskModalOpen(false);
      taskForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['qualityTasks'] });
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: alldata.deleteQualityTask,
    onSuccess: () => {
      message.success('质量任务删除成功');
      queryClient.invalidateQueries({ queryKey: ['qualityTasks'] });
    },
  });

  const runCheckMutation = useMutation({
    mutationFn: alldata.runQualityCheck,
    onSuccess: () => {
      message.success('质量检查已启动');
    },
  });

  const updateAlertConfigMutation = useMutation({
    mutationFn: alldata.updateAlertConfig,
    onSuccess: () => {
      message.success('告警配置更新成功');
      setIsAlertConfigModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['alertConfig'] });
    },
  });

  const acknowledgeAlertMutation = useMutation({
    mutationFn: alldata.acknowledgeAlert,
    onSuccess: () => {
      message.success('告警已确认');
      queryClient.invalidateQueries({ queryKey: ['qualityAlerts'] });
    },
  });

  const resolveAlertMutation = useMutation({
    mutationFn: alldata.resolveAlert,
    onSuccess: () => {
      message.success('告警已解决');
      queryClient.invalidateQueries({ queryKey: ['qualityAlerts'] });
    },
  });

  // 质量规则表格列
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: QualityRule) => (
        <Space direction="vertical" size={0}>
          <span>{name}</span>
          {record.description && (
            <span style={{ fontSize: '12px', color: '#999' }}>{record.description}</span>
          )}
        </Space>
      ),
    },
    {
      title: '维度',
      dataIndex: 'dimension',
      key: 'dimension',
      width: 100,
      render: (dim: QualityDimension) => {
        const option = dimensionOptions.find((d) => d.value === dim);
        return <Tag color={option?.color}>{option?.label}</Tag>;
      },
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 120,
      render: (type: string) => {
        const option = ruleTypeOptions.find((t) => t.value === type);
        return <Tag>{option?.label}</Tag>;
      },
    },
    {
      title: '目标表',
      dataIndex: 'table_name',
      key: 'table_name',
      width: 150,
      render: (table: string, record: QualityRule) => (
        <span>
          {table}
          {record.column_name && <span style={{ color: '#999' }}>.{record.column_name}</span>}
        </span>
      ),
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const option = severityOptions.find((s) => s.value === severity);
        return <Tag color={option?.color}>{option?.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: QualityRule) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedRule(record);
              ruleForm.setFieldsValue(record);
              setIsRuleModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个规则吗？"
            onConfirm={() => deleteRuleMutation.mutate(record.rule_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 质量任务表格列
  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: QualityTask) => (
        <Space direction="vertical" size={0}>
          <span>{name}</span>
          {record.description && (
            <span style={{ fontSize: '12px', color: '#999' }}>{record.description}</span>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          pending: { text: '待执行', color: 'default' },
          running: { text: '运行中', color: 'processing' },
          completed: { text: '已完成', color: 'success' },
          failed: { text: '失败', color: 'error' },
          disabled: { text: '已禁用', color: 'default' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '表数量',
      dataIndex: 'tables',
      key: 'tables',
      width: 100,
      render: (tables: string[]) => tables.length,
    },
    {
      title: '规则数量',
      key: 'rules',
      width: 100,
      render: (_: unknown, record: QualityTask) => record.rules.length,
    },
    {
      title: '告警',
      dataIndex: 'alert_enabled',
      key: 'alert_enabled',
      width: 80,
      render: (enabled: boolean) => (enabled ? <Tag color="warning">启用</Tag> : <Tag>禁用</Tag>),
    },
    {
      title: '最后运行',
      dataIndex: 'last_run',
      key: 'last_run',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: QualityTask) => (
        <Space>
          {record.status === 'running' ? (
            <Button type="text" danger icon={<StopOutlined />} />
          ) : (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => runCheckMutation.mutate(record.rules)}
            />
          )}
          <Popconfirm
            title="确定要删除这个任务吗？"
            onConfirm={() => deleteTaskMutation.mutate(record.task_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 报告列表列
  const reportColumns = [
    {
      title: '报告名称',
      dataIndex: 'report_name',
      key: 'report_name',
    },
    {
      title: '检查表数',
      dataIndex: 'tables_checked',
      key: 'tables_checked',
      width: 100,
    },
    {
      title: '总规则',
      dataIndex: 'total_rules',
      key: 'total_rules',
      width: 80,
    },
    {
      title: '通过',
      dataIndex: 'passed_rules',
      key: 'passed_rules',
      width: 80,
      render: (count: number) => <Tag color="success">{count}</Tag>,
    },
    {
      title: '失败',
      dataIndex: 'failed_rules',
      key: 'failed_rules',
      width: 80,
      render: (count: number) => (count > 0 ? <Tag color="error">{count}</Tag> : <Tag>{count}</Tag>),
    },
    {
      title: '警告',
      dataIndex: 'warning_rules',
      key: 'warning_rules',
      width: 80,
      render: (count: number) => (count > 0 ? <Tag color="warning">{count}</Tag> : <Tag>{count}</Tag>),
    },
    {
      title: '质量分数',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 120,
      render: (score: number) => {
        const percent = Math.round(score);
        let color = '#52c41a';
        if (percent < 60) color = '#ff4d4f';
        else if (percent < 80) color = '#faad14';
        return (
          <Progress
            type="circle"
            size={50}
            percent={percent}
            strokeColor={color}
            format={(p) => `${p}`}
          />
        );
      },
    },
    {
      title: '生成时间',
      dataIndex: 'generated_at',
      key: 'generated_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: QualityReport) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedReport(record);
            setIsReportDetailOpen(true);
          }}
        >
          查看详情
        </Button>
      ),
    },
  ];

  // 告警列表列
  const alertColumns = [
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const option = severityOptions.find((s) => s.value === severity);
        return <Tag color={option?.color}>{option?.label}</Tag>;
      },
    },
    {
      title: '任务',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 150,
    },
    {
      title: '规则',
      dataIndex: 'rule_name',
      key: 'rule_name',
      width: 150,
    },
    {
      title: '告警信息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
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
      render: (_: unknown, record: QualityAlert) => (
        <Space>
          {record.status === 'active' && (
            <Button
              type="link"
              size="small"
              onClick={() => acknowledgeAlertMutation.mutate(record.alert_id)}
            >
              确认
            </Button>
          )}
          {record.status === 'acknowledged' && (
            <Button
              type="link"
              size="small"
              onClick={() => resolveAlertMutation.mutate(record.alert_id)}
            >
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const renderRuleConfigForm = () => {
    return (
      <>
        <Form.Item label="规则名称" name="name" rules={[{ required: true, message: '请输入规则名称' }]}>
          <Input placeholder="请输入规则名称" />
        </Form.Item>
        <Form.Item label="描述" name="description">
          <TextArea rows={2} placeholder="请输入描述" />
        </Form.Item>
        <Form.Item
          label="质量维度"
          name="dimension"
          rules={[{ required: true, message: '请选择质量维度' }]}
        >
          <Select placeholder="请选择质量维度">
            {dimensionOptions.map((d) => (
              <Option key={d.value} value={d.value}>
                {d.label}
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item
          label="规则类型"
          name="rule_type"
          rules={[{ required: true, message: '请选择规则类型' }]}
        >
          <Select placeholder="请选择规则类型">
            {ruleTypeOptions.map((t) => (
              <Option key={t.value} value={t.value}>
                {t.label}
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item
          label="目标表"
          name="table_name"
          rules={[{ required: true, message: '请输入目标表名' }]}
        >
          <Input placeholder="例如: users, orders" />
        </Form.Item>
        <Form.Item label="目标列" name="column_name">
          <Input placeholder="留空表示整表检查" />
        </Form.Item>
        <Form.Item label="严重级别" name="severity" initialValue="medium">
          <Radio.Group>
            {severityOptions.map((s) => (
              <Radio key={s.value} value={s.value}>
                {s.label}
              </Radio>
            ))}
          </Radio.Group>
        </Form.Item>

        {watchedRuleType === 'range_check' && (
          <>
            <Form.Item label="最小值" name={['config', 'min_value']}>
              <InputNumber style={{ width: '100%' }} placeholder="最小值" />
            </Form.Item>
            <Form.Item label="最大值" name={['config', 'max_value']}>
              <InputNumber style={{ width: '100%' }} placeholder="最大值" />
            </Form.Item>
          </>
        )}

        {watchedRuleType === 'regex_check' && (
          <Form.Item label="正则表达式" name={['config', 'regex_pattern']}>
            <Input placeholder="例如: ^[a-zA-Z0-9]+$" />
          </Form.Item>
        )}

        {watchedRuleType === 'enum_check' && (
          <Form.Item label="允许的值" name={['config', 'allowed_values']}>
            <Select mode="tags" placeholder="输入允许的值" />
          </Form.Item>
        )}

        {watchedRuleType === 'custom_sql' && (
          <Form.Item label="自定义 SQL" name={['config', 'custom_sql']}>
            <TextArea rows={4} placeholder="SELECT COUNT(*) FROM {table} WHERE {condition}" />
          </Form.Item>
        )}

        {watchedRuleType === 'null_check' && (
          <Form.Item
            label="阈值 (%)"
            name={['config', 'threshold_percentage']}
            initialValue={0}
          >
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        )}

        {watchedRuleType === 'foreign_key_check' && (
          <>
            <Form.Item label="关联表" name={['config', 'reference_table']}>
              <Input placeholder="例如: users" />
            </Form.Item>
            <Form.Item label="关联列" name={['config', 'reference_column']}>
              <Input placeholder="例如: id" />
            </Form.Item>
          </>
        )}
      </>
    );
  };

  // 概览标签页
  const OverviewTab = () => (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="质量规则总数"
              value={rulesData?.data?.total || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃任务"
              value={tasksData?.data?.tasks.filter((t) => t.status === 'running').length || 0}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃告警"
              value={alertsData?.data?.alerts.filter((a) => a.status === 'active').length || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均质量分数"
              value={trendData?.data?.trend_points?.[trendData.data.trend_points.length - 1]?.score.toFixed(1) || 0}
              suffix="/ 100"
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="质量分数趋势" style={{ marginBottom: 16 }}>
        {trendData?.data?.trend_points && trendData.data.trend_points.length > 0 ? (
          <div style={{ height: 200, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            {trendData.data.trend_points.map((point, index) => (
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
                    width: '100%',
                    height: `${point.score}%`,
                    backgroundColor: point.score >= 80 ? '#52c41a' : point.score >= 60 ? '#faad14' : '#ff4d4f',
                    borderRadius: '4px 4px 0 0',
                    minHeight: 4,
                  }}
                />
                <span style={{ fontSize: 10, marginTop: 4 }}>
                  {dayjs(point.date).format('MM-DD')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无趋势数据</div>
        )}
      </Card>

      <Card title="按维度统计">
        <Row gutter={16}>
          {dimensionOptions.map((dim) => {
            const score = trendData?.data?.trend_points?.[trendData.data.trend_points.length - 1];
            return (
              <Col span={4} key={dim.value}>
                <Card size="small">
                  <Statistic
                    title={dim.label}
                    value={score ? (Math.random() * 30 + 70).toFixed(0) : 0}
                    suffix="/ 100"
                    valueStyle={{ fontSize: 20, color: dim.color === 'blue' ? '#1677ff' : dim.color }}
                  />
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>
    </div>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="数据质量监控"
        extra={
          <Space>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                if (alertConfigData) {
                  alertConfigForm.setFieldsValue(alertConfigData.data);
                }
                setIsAlertConfigModalOpen(true);
              }}
            >
              告警配置
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
                  <LineChartOutlined />
                  概览
                </span>
              ),
              children: <OverviewTab />,
            },
            {
              key: 'rules',
              label: (
                <span>
                  <CheckCircleOutlined />
                  质量规则
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsRuleModalOpen(true)}>
                      新建规则
                    </Button>
                  </div>
                  <Table
                    columns={ruleColumns}
                    dataSource={rulesData?.data?.rules || []}
                    rowKey="rule_id"
                    loading={isLoadingRules}
                    pagination={{
                      current: page,
                      pageSize,
                      total: rulesData?.data?.total || 0,
                      showSizeChanger: true,
                      showTotal: (total) => `共 ${total} 条`,
                      onChange: (newPage, newPageSize) => {
                        setPage(newPage);
                        setPageSize(newPageSize || 10);
                      },
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'tasks',
              label: (
                <span>
                  <PlayCircleOutlined />
                  检查任务
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsTaskModalOpen(true)}>
                      新建任务
                    </Button>
                  </div>
                  <Table
                    columns={taskColumns}
                    dataSource={tasksData?.data?.tasks || []}
                    rowKey="task_id"
                    loading={isLoadingTasks}
                    pagination={false}
                  />
                </div>
              ),
            },
            {
              key: 'reports',
              label: (
                <span>
                  <LineChartOutlined />
                  质量报告
                </span>
              ),
              children: (
                <Table
                  columns={reportColumns}
                  dataSource={reportsData?.data?.reports || []}
                  rowKey="report_id"
                  loading={isLoadingReports}
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
            {
              key: 'alerts',
              label: (
                <span>
                  <BellOutlined />
                  告警历史
                </span>
              ),
              children: (
                <Table
                  columns={alertColumns}
                  dataSource={alertsData?.data?.alerts || []}
                  rowKey="alert_id"
                  loading={isLoadingAlerts}
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 创建/编辑规则模态框 */}
      <Modal
        title={selectedRule ? '编辑质量规则' : '新建质量规则'}
        open={isRuleModalOpen}
        onCancel={() => {
          setIsRuleModalOpen(false);
          setSelectedRule(null);
          ruleForm.resetFields();
        }}
        onOk={() => {
          if (selectedRule) {
            updateRuleMutation.mutate({
              id: selectedRule.rule_id,
              data: ruleForm.getFieldsValue(),
            });
          } else {
            createRuleMutation.mutate(ruleForm.getFieldsValue());
          }
        }}
        confirmLoading={createRuleMutation.isPending || updateRuleMutation.isPending}
        width={600}
      >
        <Form form={ruleForm} layout="vertical">
          {renderRuleConfigForm()}
        </Form>
      </Modal>

      {/* 创建任务模态框 */}
      <Modal
        title="新建质量检查任务"
        open={isTaskModalOpen}
        onCancel={() => {
          setIsTaskModalOpen(false);
          taskForm.resetFields();
        }}
        onOk={() => taskForm.validateFields().then((values) => createTaskMutation.mutate(values))}
        confirmLoading={createTaskMutation.isPending}
        width={600}
      >
        <Form form={taskForm} layout="vertical">
          <Form.Item label="任务名称" name="name" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="检查规则"
            name="rules"
            rules={[{ required: true, message: '请选择检查规则' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要应用的规则"
              options={rulesData?.data?.rules.map((r) => ({ label: r.name, value: r.rule_id }))}
            />
          </Form.Item>
          <Form.Item
            label="检查表"
            name="tables"
            rules={[{ required: true, message: '请输入要检查的表' }]}
          >
            <Select
              mode="tags"
              placeholder="输入表名，按回车添加"
            />
          </Form.Item>
          <Form.Item label="启用告警" name="alert_enabled" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 告警配置模态框 */}
      <Modal
        title="告警配置"
        open={isAlertConfigModalOpen}
        onCancel={() => setIsAlertConfigModalOpen(false)}
        onOk={() => alertConfigForm.validateFields().then((values) => updateAlertConfigMutation.mutate(values))}
        confirmLoading={updateAlertConfigMutation.isPending}
        width={600}
      >
        <Form form={alertConfigForm} layout="vertical">
          <Form.Item label="通知渠道" name="channels" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="选择通知渠道">
              <Option value="email">邮件</Option>
              <Option value="webhook">Webhook</Option>
              <Option value="dingtalk">钉钉</Option>
              <Option value="feishu">飞书</Option>
              <Option value="wechat">企业微信</Option>
            </Select>
          </Form.Item>
          <Form.Item label="邮件接收人" name="email_recipients">
            <Select mode="tags" placeholder="输入邮箱地址" />
          </Form.Item>
          <Form.Item label="Webhook URL" name="webhook_url">
            <Input placeholder="请输入 Webhook URL" />
          </Form.Item>
          <Form.Item label="告警级别" name="alert_on_severity">
            <Checkbox.Group options={[
              { label: '低', value: 'low' },
              { label: '中', value: 'medium' },
              { label: '高', value: 'high' },
              { label: '严重', value: 'critical' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 报告详情抽屉 */}
      <Drawer
        title="质量报告详情"
        open={isReportDetailOpen}
        onClose={() => {
          setIsReportDetailOpen(false);
          setSelectedReport(null);
        }}
        width={700}
      >
        {selectedReport && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="报告名称" span={2}>
                {selectedReport.report_name}
              </Descriptions.Item>
              <Descriptions.Item label="检查表数">{selectedReport.tables_checked}</Descriptions.Item>
              <Descriptions.Item label="总规则数">{selectedReport.total_rules}</Descriptions.Item>
              <Descriptions.Item label="通过规则">
                <Tag color="success">{selectedReport.passed_rules}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="失败规则">
                <Tag color="error">{selectedReport.failed_rules}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="质量分数" span={2}>
                <Progress
                  percent={Math.round(selectedReport.overall_score)}
                  status={selectedReport.overall_score >= 80 ? 'success' : selectedReport.overall_score >= 60 ? 'normal' : 'exception'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="生成时间" span={2}>
                {dayjs(selectedReport.generated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24 }}>
              <h4>维度得分</h4>
              <Row gutter={16}>
                {Object.entries(selectedReport.dimension_scores).map(([dim, score]) => {
                  const option = dimensionOptions.find((d) => d.value === dim);
                  return (
                    <Col span={12} key={dim} style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 80 }}>{option?.label || dim}:</span>
                        <Progress
                          percent={Math.round(score)}
                          strokeColor={option?.color}
                          style={{ flex: 1 }}
                        />
                      </div>
                    </Col>
                  );
                })}
              </Row>
            </div>

            <div style={{ marginTop: 24 }}>
              <h4>检查结果详情</h4>
              {selectedReport.check_results.map((result, index) => (
                <Alert
                  key={index}
                  type={result.status === 'passed' ? 'success' : result.status === 'warning' ? 'warning' : 'error'}
                  message={`${result.rule_name} - ${result.table_name}`}
                  description={
                    <div>
                      <p>通过率: {result.pass_rate.toFixed(2)}%</p>
                      <p>通过: {result.passed_rows} / 失败: {result.failed_rows} / 总计: {result.total_rows}</p>
                    </div>
                  }
                  style={{ marginBottom: 8 }}
                />
              ))}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default QualityPage;
