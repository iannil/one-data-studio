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
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import bisheng, { type WorkflowSchedule, type CreateScheduleRequest, type Workflow } from '@/services/bisheng';

const { Option } = Select;
const { TextArea } = Input;

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
  const [selectedSchedule, setSelectedSchedule] = useState<WorkflowSchedule | null>(null);
  const [scheduleType, setScheduleType] = useState<CreateScheduleRequest['type']>('cron');
  const [enabledOnly, setEnabledOnly] = useState(false);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // 获取工作流列表（用于选择）
  const { data: workflowsData } = useQuery({
    queryKey: ['workflows'],
    queryFn: bisheng.getWorkflows,
  });

  // 获取调度列表
  const { data: schedulesData, isLoading } = useQuery({
    queryKey: ['schedules', enabledOnly],
    queryFn: () => bisheng.listAllSchedules({ enabled: enabledOnly || undefined }),
  });

  // 创建调度
  const createMutation = useMutation({
    mutationFn: ({ workflowId, data }: { workflowId: string; data: CreateScheduleRequest }) =>
      bisheng.createSchedule(workflowId, data),
    onSuccess: () => {
      message.success('调度创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
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
      await bisheng.deleteSchedule(scheduleId);
      return bisheng.createSchedule(workflowId, data);
    },
    onSuccess: () => {
      message.success('调度更新成功');
      setIsEditModalOpen(false);
      setSelectedSchedule(null);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
      message.error(`调度更新失败: ${error.message || '未知错误'}`);
    },
  });

  // 删除调度
  const deleteMutation = useMutation({
    mutationFn: bisheng.deleteSchedule,
    onSuccess: () => {
      message.success('调度删除成功');
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
      message.error(`调度删除失败: ${error.message || '未知错误'}`);
    },
  });

  // 触发调度
  const triggerMutation = useMutation({
    mutationFn: bisheng.triggerSchedule,
    onSuccess: (data) => {
      message.success(`调度已触发，执行ID: ${data.data?.execution_id || '-'}`);
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
      message.error(`触发调度失败: ${error.message || '未知错误'}`);
    },
  });

  // 切换启用状态（通过更新实现）
  const toggleEnabledMutation = useMutation({
    mutationFn: async ({ schedule, enabled }: { schedule: WorkflowSchedule; enabled: boolean }) => {
      await bisheng.deleteSchedule(schedule.schedule_id);
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
      return bisheng.createSchedule(schedule.workflow_id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error: any) => {
      message.error(`切换状态失败: ${error.message || '未知错误'}`);
    },
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
      width: 200,
      render: (_: unknown, record: WorkflowSchedule) => (
        <Space>
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
    </div>
  );
}

export default SchedulesPage;
