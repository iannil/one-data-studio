import { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Switch,
  Tooltip,
  Statistic,
  Row,
  Col,
  Progress,
  Descriptions,
  List,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  ThunderboltOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
  SettingOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import bisheng, { type WorkflowSchedule, type CreateScheduleRequest, type Workflow, type ScheduleRetryConfig } from '@/services/agent-service';

const { Option } = Select;

// 获取调度类型标签
const getScheduleTypeTag = (type: WorkflowSchedule['schedule_type']) => {
  const config = {
    cron: { color: 'blue', text: 'Cron', icon: <CalendarOutlined /> },
    interval: { color: 'green', text: '间隔', icon: <ClockCircleOutlined /> },
    event: { color: 'purple', text: '事件', icon: <ThunderboltOutlined /> },
  };
  const cfg = config[type] || { color: 'default', text: type, icon: null };
  return (
    <Tag color={cfg.color} icon={cfg.icon}>
      {cfg.text}
    </Tag>
  );
};

// 格式化调度配置显示
const formatScheduleConfig = (schedule: WorkflowSchedule): string => {
  switch (schedule.schedule_type) {
    case 'cron':
      return schedule.cron_expression || '-';
    case 'interval':
      return schedule.interval_seconds ? `每 ${schedule.interval_seconds} 秒` : '-';
    case 'event':
      return schedule.event_trigger || '-';
    default:
      return '-';
  }
};

// 计算相对时间
const getRelativeTime = (date?: string): string => {
  if (!date) return '-';
  const d = dayjs(date);
  const now = dayjs();
  if (d.isBefore(now)) {
    return d.format('YYYY-MM-DD HH:mm');
  }
  const diff = d.diff(now, 'minute');
  if (diff < 60) return `${diff} 分钟后`;
  const diffHours = d.diff(now, 'hour');
  if (diffHours < 24) return `${diffHours} 小时后`;
  return d.format('YYYY-MM-DD HH:mm');
};

function SchedulesPage() {
  const queryClient = useQueryClient();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isRetryConfigModalOpen, setIsRetryConfigModalOpen] = useState(false);
  const [isStatisticsModalOpen, setIsStatisticsModalOpen] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<WorkflowSchedule | null>(null);
  const [scheduleType, setScheduleType] = useState<CreateScheduleRequest['type']>('cron');
  const [enabledOnly, setEnabledOnly] = useState(false);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [retryConfigForm] = Form.useForm();

  // 获取工作流列表（用于选择）
  const { data: workflowsData } = useQuery({
    queryKey: ['workflows'],
    queryFn: agentService.getWorkflows,
  });

  // 获取调度列表
  const { data: schedulesData, isLoading } = useQuery({
    queryKey: ['schedules', enabledOnly],
    queryFn: () => agentService.listAllSchedules({ enabled: enabledOnly || undefined }),
  });

  // 创建调度
  const createMutation = useMutation({
    mutationFn: ({ workflowId, data }: { workflowId: string; data: CreateScheduleRequest }) =>
      agentService.createSchedule(workflowId, data),
    onSuccess: () => {
      message.success('调度创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`调度创建失败: ${error.message || '未知错误'}`);
    },
  });

  // 更新调度（通过删除重建实现）
  const updateMutation = useMutation({
    mutationFn: async ({
      scheduleId,
      workflowId,
      data,
    }: {
      scheduleId: string;
      workflowId: string;
      data: CreateScheduleRequest;
    }) => {
      await agentService.deleteSchedule(scheduleId);
      return agentService.createSchedule(workflowId, data);
    },
    onSuccess: () => {
      message.success('调度更新成功');
      setIsEditModalOpen(false);
      setSelectedSchedule(null);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`调度更新失败: ${error.message || '未知错误'}`);
    },
  });

  // 删除调度
  const deleteMutation = useMutation({
    mutationFn: agentService.deleteSchedule,
    onSuccess: () => {
      message.success('调度删除成功');
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`调度删除失败: ${error.message || '未知错误'}`);
    },
  });

  // 触发调度
  const triggerMutation = useMutation({
    mutationFn: agentService.triggerSchedule,
    onSuccess: (data) => {
      message.success(`调度已触发，执行ID: ${data.data?.execution_id || '-'}`);
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`触发调度失败: ${error.message || '未知错误'}`);
    },
  });

  // 切换启用状态（通过更新实现）
  const toggleEnabledMutation = useMutation({
    mutationFn: async ({ schedule, enabled }: { schedule: WorkflowSchedule; enabled: boolean }) => {
      await agentService.deleteSchedule(schedule.schedule_id);
      const data: CreateScheduleRequest = {
        type: schedule.schedule_type,
        enabled,
      };
      if (schedule.schedule_type === 'cron') {
        data.cron_expression = schedule.cron_expression;
      } else if (schedule.schedule_type === 'interval') {
        data.interval_seconds = schedule.interval_seconds;
      } else if (schedule.schedule_type === 'event') {
        data.event_trigger = schedule.event_trigger;
      }
      return agentService.createSchedule(schedule.workflow_id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`切换状态失败: ${error.message || '未知错误'}`);
    },
  });

  // P4: 暂停调度
  const pauseMutation = useMutation({
    mutationFn: agentService.pauseSchedule,
    onSuccess: () => {
      message.success('调度已暂停');
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`暂停失败: ${error.message || '未知错误'}`);
    },
  });

  // P4: 恢复调度
  const resumeMutation = useMutation({
    mutationFn: agentService.resumeSchedule,
    onSuccess: () => {
      message.success('调度已恢复');
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`恢复失败: ${error.message || '未知错误'}`);
    },
  });

  // P4: 更新重试配置
  const updateRetryConfigMutation = useMutation({
    mutationFn: ({ scheduleId, config }: { scheduleId: string; config: Partial<ScheduleRetryConfig> }) =>
      agentService.updateScheduleRetryConfig(scheduleId, config),
    onSuccess: () => {
      message.success('重试配置已更新');
      setIsRetryConfigModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: Error) => {
      message.error(`更新失败: ${error.message || '未知错误'}`);
    },
  });

  // P4: 获取统计信息
  const { data: statisticsData, refetch: refetchStatistics } = useQuery({
    queryKey: ['schedule-statistics', selectedSchedule?.schedule_id],
    queryFn: () => agentService.getScheduleStatistics(selectedSchedule!.schedule_id),
    enabled: isStatisticsModalOpen && !!selectedSchedule,
  });

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateScheduleRequest = {
        type: scheduleType,
        enabled: values.enabled ?? true,
      };

      if (scheduleType === 'cron') {
        data.cron_expression = values.cron_expression;
      } else if (scheduleType === 'interval') {
        data.interval_seconds = values.interval_seconds;
      } else if (scheduleType === 'event') {
        data.event_trigger = values.event_trigger;
      }

      createMutation.mutate({
        workflowId: values.workflow_id,
        data,
      });
    });
  };

  const handleEdit = () => {
    editForm.validateFields().then((values) => {
      if (!selectedSchedule) return;

      const data: CreateScheduleRequest = {
        type: selectedSchedule.schedule_type,
        enabled: values.enabled ?? selectedSchedule.enabled,
      };

      if (selectedSchedule.schedule_type === 'cron') {
        data.cron_expression = values.cron_expression;
      } else if (selectedSchedule.schedule_type === 'interval') {
        data.interval_seconds = values.interval_seconds;
      } else if (selectedSchedule.schedule_type === 'event') {
        data.event_trigger = values.event_trigger;
      }

      updateMutation.mutate({
        scheduleId: selectedSchedule.schedule_id,
        workflowId: selectedSchedule.workflow_id,
        data,
      });
    });
  };

  const openEditModal = (schedule: WorkflowSchedule) => {
    setSelectedSchedule(schedule);
    editForm.setFieldsValue({
      enabled: schedule.enabled,
      cron_expression: schedule.cron_expression,
      interval_seconds: schedule.interval_seconds,
      event_trigger: schedule.event_trigger,
    });
    setIsEditModalOpen(true);
  };

  // P4: 打开重试配置模态框
  const openRetryConfigModal = (schedule: WorkflowSchedule) => {
    setSelectedSchedule(schedule);
    retryConfigForm.setFieldsValue({
      max_retries: schedule.max_retries,
      retry_delay_seconds: schedule.retry_delay_seconds,
      retry_backoff_base: schedule.retry_backoff_base,
      timeout_seconds: schedule.timeout_seconds,
    });
    setIsRetryConfigModalOpen(true);
  };

  // P4: 打开统计信息模态框
  const openStatisticsModal = (schedule: WorkflowSchedule) => {
    setSelectedSchedule(schedule);
    setIsStatisticsModalOpen(true);
  };

  // P4: 处理重试配置更新
  const handleUpdateRetryConfig = () => {
    retryConfigForm.validateFields().then((values) => {
      if (!selectedSchedule) return;
      updateRetryConfigMutation.mutate({
        scheduleId: selectedSchedule.schedule_id,
        config: values,
      });
    });
  };

  const getWorkflowName = (workflowId: string): string => {
    const workflow = workflowsData?.data?.workflows?.find((w) => w.workflow_id === workflowId);
    return workflow?.name || workflowId;
  };

  const columns = [
    {
      title: '工作流',
      dataIndex: 'workflow_id',
      key: 'workflow_id',
      render: (workflowId: string) => {
        const name = getWorkflowName(workflowId);
        return <span style={{ fontWeight: 500 }}>{name}</span>;
      },
    },
    {
      title: '调度类型',
      dataIndex: 'schedule_type',
      key: 'schedule_type',
      width: 100,
      render: (type: WorkflowSchedule['schedule_type']) => getScheduleTypeTag(type),
    },
    {
      title: '调度配置',
      key: 'config',
      render: (_: unknown, record: WorkflowSchedule) => (
        <code style={{ fontSize: '12px', background: '#f5f5f5', padding: '2px 6px', borderRadius: '3px' }}>
          {formatScheduleConfig(record)}
        </code>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record: WorkflowSchedule) => (
        <Switch
          checked={enabled}
          size="small"
          loading={toggleEnabledMutation.isPending}
          onChange={(checked) =>
            toggleEnabledMutation.mutate({ schedule: record, enabled: checked })
          }
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '下次运行',
      dataIndex: 'next_run_at',
      key: 'next_run_at',
      width: 160,
      render: (date: string) => (
        <Tooltip title={date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'}>
          <span>{getRelativeTime(date)}</span>
        </Tooltip>
      ),
    },
    {
      title: '上次运行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 320,
      render: (_: unknown, record: WorkflowSchedule) => (
        <Space>
          {/* P4: 暂停/恢复按钮 */}
          {record.paused ? (
            <Tooltip title="恢复调度">
              <Button
                type="text"
                icon={<CaretRightOutlined />}
                onClick={() => resumeMutation.mutate(record.schedule_id)}
                loading={resumeMutation.isPending}
              />
            </Tooltip>
          ) : (
            <Tooltip title="暂停调度">
              <Button
                type="text"
                icon={<PauseCircleOutlined />}
                onClick={() => pauseMutation.mutate(record.schedule_id)}
                loading={pauseMutation.isPending}
              />
            </Tooltip>
          )}
          <Tooltip title="手动触发">
            <Popconfirm
              title="确定要立即触发这个调度吗？"
              onConfirm={() => triggerMutation.mutate(record.schedule_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" icon={<PlayCircleOutlined />} />
            </Popconfirm>
          </Tooltip>
          {/* P4: 统计按钮 */}
          <Tooltip title="执行统计">
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => openStatisticsModal(record)}
            />
          </Tooltip>
          {/* P4: 重试配置按钮 */}
          <Tooltip title="重试配置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => openRetryConfigModal(record)}
            />
          </Tooltip>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
            title="编辑"
          />
          <Popconfirm
            title="确定要删除这个调度吗？"
            onConfirm={() => deleteMutation.mutate(record.schedule_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} title="删除" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const workflowOptions = workflowsData?.data?.workflows || [];

  // Cron 表达式预设
  const cronPresets = [
    { label: '每分钟', value: '* * * * *' },
    { label: '每5分钟', value: '*/5 * * * *' },
    { label: '每30分钟', value: '*/30 * * * *' },
    { label: '每小时', value: '0 * * * *' },
    { label: '每天 0:00', value: '0 0 * * *' },
    { label: '每周一 0:00', value: '0 0 * * 1' },
    { label: '每月1号 0:00', value: '0 0 1 * *' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <ClockCircleOutlined />
            <span>调度管理</span>
          </Space>
        }
        extra={
          <Space>
            <Switch
              checked={enabledOnly}
              onChange={setEnabledOnly}
              checkedChildren="仅启用"
              unCheckedChildren="全部"
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建调度
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={schedulesData?.data?.schedules || []}
          rowKey="schedule_id"
          loading={isLoading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            defaultPageSize: 10,
          }}
        />
      </Card>

      {/* 创建调度模态框 */}
      <Modal
        title="新建调度"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setScheduleType('cron');
        }}
        confirmLoading={createMutation.isPending}
        width={600}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="工作流"
            name="workflow_id"
            rules={[{ required: true, message: '请选择工作流' }]}
          >
            <Select placeholder="请选择要调度的工作流" showSearch optionFilterProp="children">
              {workflowOptions.map((wf: Workflow) => (
                <Option key={wf.workflow_id} value={wf.workflow_id}>
                  {wf.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="调度类型"
            name="type"
            initialValue="cron"
            rules={[{ required: true, message: '请选择调度类型' }]}
          >
            <Select
              placeholder="请选择调度类型"
              onChange={(value) => setScheduleType(value)}
            >
              <Option value="cron">
                <Space>
                  <CalendarOutlined /> Cron 表达式
                </Space>
              </Option>
              <Option value="interval">
                <Space>
                  <ClockCircleOutlined /> 固定间隔
                </Space>
              </Option>
              <Option value="event">
                <Space>
                  <ThunderboltOutlined /> 事件触发
                </Space>
              </Option>
            </Select>
          </Form.Item>

          {scheduleType === 'cron' && (
            <Form.Item
              label="Cron 表达式"
              name="cron_expression"
              rules={[{ required: true, message: '请输入 Cron 表达式' }]}
              extra="格式: 分 时 日 月 周，例如: 0 0 * * * (每天0点)"
            >
              <Select
                placeholder="选择预设或输入自定义 Cron 表达式"
                mode="tags"
                options={cronPresets}
                maxTagCount={1}
              />
            </Form.Item>
          )}

          {scheduleType === 'interval' && (
            <Form.Item
              label="间隔秒数"
              name="interval_seconds"
              rules={[{ required: true, message: '请输入间隔秒数' }]}
            >
              <Input
                type="number"
                placeholder="请输入间隔秒数，例如: 60 (每分钟)"
                min={1}
              />
            </Form.Item>
          )}

          {scheduleType === 'event' && (
            <Form.Item
              label="事件触发器"
              name="event_trigger"
              rules={[{ required: true, message: '请输入事件触发器' }]}
              extra="例如: file_uploaded, data_updated 等"
            >
              <Input placeholder="请输入事件触发器名称" />
            </Form.Item>
          )}

          <Form.Item
            label="启用状态"
            name="enabled"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑调度模态框 */}
      <Modal
        title="编辑调度"
        open={isEditModalOpen}
        onOk={handleEdit}
        onCancel={() => {
          setIsEditModalOpen(false);
          setSelectedSchedule(null);
          editForm.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        {selectedSchedule && (
          <Form form={editForm} layout="vertical">
            <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '6px' }}>
              <p style={{ margin: 0 }}>
                <strong>工作流：</strong>
                {getWorkflowName(selectedSchedule.workflow_id)}
              </p>
              <p style={{ margin: '4px 0 0 0' }}>
                <strong>类型：</strong>
                {getScheduleTypeTag(selectedSchedule.schedule_type)}
              </p>
            </div>

            {selectedSchedule.schedule_type === 'cron' && (
              <Form.Item
                label="Cron 表达式"
                name="cron_expression"
                rules={[{ required: true, message: '请输入 Cron 表达式' }]}
              >
                <Select
                  placeholder="选择预设或输入自定义 Cron 表达式"
                  mode="tags"
                  options={cronPresets}
                  maxTagCount={1}
                />
              </Form.Item>
            )}

            {selectedSchedule.schedule_type === 'interval' && (
              <Form.Item
                label="间隔秒数"
                name="interval_seconds"
                rules={[{ required: true, message: '请输入间隔秒数' }]}
              >
                <Input type="number" placeholder="请输入间隔秒数" min={1} />
              </Form.Item>
            )}

            {selectedSchedule.schedule_type === 'event' && (
              <Form.Item
                label="事件触发器"
                name="event_trigger"
                rules={[{ required: true, message: '请输入事件触发器' }]}
              >
                <Input placeholder="请输入事件触发器名称" />
              </Form.Item>
            )}

            <Form.Item
              label="启用状态"
              name="enabled"
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* P4: 重试配置模态框 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>重试与超时配置</span>
          </Space>
        }
        open={isRetryConfigModalOpen}
        onOk={handleUpdateRetryConfig}
        onCancel={() => {
          setIsRetryConfigModalOpen(false);
          setSelectedSchedule(null);
          retryConfigForm.resetFields();
        }}
        confirmLoading={updateRetryConfigMutation.isPending}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        {selectedSchedule && (
          <Form form={retryConfigForm} layout="vertical">
            <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '6px' }}>
              <p style={{ margin: 0 }}>
                <strong>工作流：</strong>
                {getWorkflowName(selectedSchedule.workflow_id)}
              </p>
            </div>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="最大重试次数"
                  name="max_retries"
                  rules={[{ required: true, message: '请输入最大重试次数' }]}
                  extra="失败后自动重试的次数（0-10）"
                >
                  <Input type="number" min={0} max={10} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="重试延迟（秒）"
                  name="retry_delay_seconds"
                  rules={[{ required: true, message: '请输入重试延迟' }]}
                  extra="首次重试前的等待时间"
                >
                  <Input type="number" min={0} max={3600} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="退避基数"
                  name="retry_backoff_base"
                  rules={[{ required: true, message: '请输入退避基数' }]}
                  extra="指数退避的基数（建议2-3）"
                >
                  <Input type="number" min={1} max={10} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="超时时间（秒）"
                  name="timeout_seconds"
                  rules={[{ required: true, message: '请输入超时时间' }]}
                  extra="单次执行的最大时长"
                >
                  <Input type="number" min={60} max={86400} />
                </Form.Item>
              </Col>
            </Row>

            <div style={{ padding: '12px', background: '#e6f7ff', borderRadius: '6px', border: '1px solid #91d5ff' }}>
              <p style={{ margin: 0, fontSize: '12px', color: '#0050b3' }}>
                <strong>指数退避说明：</strong>第 N 次重试的延迟时间为 {retryConfigForm.getFieldValue('retry_delay_seconds') || 60} × {retryConfigForm.getFieldValue('retry_backoff_base') || 2}<sup>N</sup> 秒
              </p>
            </div>
          </Form>
        )}
      </Modal>

      {/* P4: 执行统计模态框 */}
      <Modal
        title={
          <Space>
            <BarChartOutlined />
            <span>执行统计</span>
          </Space>
        }
        open={isStatisticsModalOpen}
        onCancel={() => {
          setIsStatisticsModalOpen(false);
          setSelectedSchedule(null);
        }}
        footer={[
          <Button key="refresh" icon={<HistoryOutlined />} onClick={() => refetchStatistics()}>
            刷新
          </Button>,
          <Button key="close" type="primary" onClick={() => setIsStatisticsModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {selectedSchedule && statisticsData?.data && (
          <div>
            <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '6px' }}>
              <p style={{ margin: 0 }}>
                <strong>工作流：</strong>
                {getWorkflowName(selectedSchedule.workflow_id)}
              </p>
              <p style={{ margin: '4px 0 0 0' }}>
                <strong>类型：</strong>
                {getScheduleTypeTag(selectedSchedule.schedule_type)}
              </p>
            </div>

            <Row gutter={16} style={{ marginBottom: '24px' }}>
              <Col span={6}>
                <Statistic
                  title="总执行次数"
                  value={statisticsData.data.total_executions}
                  prefix={<HistoryOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="成功次数"
                  value={statisticsData.data.successful_executions}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="失败次数"
                  value={statisticsData.data.failed_executions}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="成功率"
                  value={statisticsData.data.success_rate}
                  suffix="%"
                  valueStyle={{ color: statisticsData.data.success_rate >= 80 ? '#52c41a' : statisticsData.data.success_rate >= 50 ? '#faad14' : '#ff4d4f' }}
                />
              </Col>
            </Row>

            <Descriptions title="性能指标" bordered size="small" column={2} style={{ marginBottom: '16px' }}>
              <Descriptions.Item label="平均执行时间">
                {statisticsData.data.average_execution_time_ms
                  ? `${(statisticsData.data.average_execution_time_ms / 1000).toFixed(2)} 秒`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="最后执行状态">
                {statisticsData.data.last_execution_status ? (
                  <Tag color={
                    statisticsData.data.last_execution_status === 'completed' ? 'success' :
                    statisticsData.data.last_execution_status === 'failed' ? 'error' :
                    statisticsData.data.last_execution_status === 'running' ? 'processing' : 'default'
                  }>
                    {statisticsData.data.last_execution_status === 'completed' ? '成功' :
                     statisticsData.data.last_execution_status === 'failed' ? '失败' :
                     statisticsData.data.last_execution_status === 'running' ? '运行中' :
                     statisticsData.data.last_execution_status}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="最后执行时间" span={2}>
                {statisticsData.data.last_execution_at
                  ? dayjs(statisticsData.data.last_execution_at).format('YYYY-MM-DD HH:mm:ss')
                  : '-'}
              </Descriptions.Item>
            </Descriptions>

            {statisticsData.data.success_rate > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                  成功率
                </div>
                <Progress
                  percent={Math.round(statisticsData.data.success_rate)}
                  status={statisticsData.data.success_rate >= 80 ? 'success' : statisticsData.data.success_rate >= 50 ? 'normal' : 'exception'}
                  strokeColor={{
                    '0%': '#ff4d4f',
                    '50%': '#faad14',
                    '80%': '#52c41a',
                  }}
                />
              </div>
            )}

            {statisticsData.data.recent_executions && statisticsData.data.recent_executions.length > 0 && (
              <div>
                <div style={{ marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                  最近执行记录
                </div>
                <List
                  size="small"
                  bordered
                  dataSource={statisticsData.data.recent_executions.slice(0, 5)}
                  renderItem={(item: typeof statisticsData.data.recent_executions[0]) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          item.status === 'completed' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                          item.status === 'failed' ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> :
                          item.status === 'running' ? <HistoryOutlined style={{ color: '#1890ff' }} /> :
                          <ClockCircleOutlined />
                        }
                        title={
                          <Space>
                            <span>{item.execution_id}</span>
                            <Tag color={
                              item.status === 'completed' ? 'success' :
                              item.status === 'failed' ? 'error' :
                              item.status === 'running' ? 'processing' : 'default'
                            }>
                              {item.status === 'completed' ? '成功' :
                               item.status === 'failed' ? '失败' :
                               item.status === 'running' ? '运行中' : item.status}
                            </Tag>
                          </Space>
                        }
                        description={
                          <Space>
                            {item.started_at && <span>开始: {dayjs(item.started_at).format('MM-DD HH:mm')}</span>}
                            {item.duration_ms && <span>耗时: {(item.duration_ms / 1000).toFixed(2)}s</span>}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default SchedulesPage;
