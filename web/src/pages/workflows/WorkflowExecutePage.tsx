import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Descriptions,
  Tag,
  Space,
  Alert,
  Tabs,
  Input,
  message,
  Spin,
  Empty,
  Badge,
  Modal,
  Form,
  Select,
  Statistic,
  Row,
  Col,
  Switch,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import agentService, { type WorkflowExecution, type HumanTask } from '@/services/agent-service';
import WorkflowLogViewer from '@/components/WorkflowLogViewer';
// import './WorkflowsPage.less';

dayjs.extend(duration);
dayjs.extend(relativeTime);

const { TextArea } = Input;
const { Option } = Select;

interface FormField {
  name: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'boolean' | 'date';
  label: string;
  required?: boolean;
  options?: string[];
  default?: unknown;
}

interface FormSchema {
  fields: FormField[];
}

function WorkflowExecutePage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [executionId, setExecutionId] = useState<string | null>(null);
  const [inputs, setInputs] = useState('{\n  "query": "测试查询"\n}');
  const [activeTab, setActiveTab] = useState('executions');

  // Human task states
  const [isHumanTaskModalOpen, setIsHumanTaskModalOpen] = useState(false);
  const [currentHumanTask, setCurrentHumanTask] = useState<HumanTask | null>(null);
  const [humanTaskComment, setHumanTaskComment] = useState('');
  const [humanTaskInputData, setHumanTaskInputData] = useState<Record<string, unknown>>({});
  const [humanTaskForm] = Form.useForm();

  // 获取工作流信息
  const { data: workflowData } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => agentService.getWorkflow(workflowId!),
    enabled: !!workflowId,
  });

  // 获取执行历史
  const { data: executionsData, refetch: refetchExecutions } = useQuery({
    queryKey: ['workflowExecutions', workflowId],
    queryFn: () => agentService.getWorkflowExecutions(workflowId!),
    enabled: !!workflowId,
    refetchInterval: (query) => {
      // 如果有运行中的执行，每2秒轮询一次
      const queryData = query.state.data as { data?: { executions?: Array<{ status: string }> } } | undefined;
      const hasRunning = queryData?.data?.executions?.some(
        (e: WorkflowExecution) => e.status === 'running' || e.status === 'pending' || e.status === 'waiting_human'
      );
      return hasRunning ? 2000 : false;
    },
  });

  // 获取当前执行的日志
  const { data: logsData, refetch: refetchLogs } = useQuery({
    queryKey: ['executionLogs', executionId],
    queryFn: () => agentService.getExecutionLogs(executionId!),
    enabled: !!executionId && activeTab === 'logs',
    refetchInterval: (query) => {
      // 如果执行仍在运行，每2秒轮询日志
      const queryData = query.state.data as { data?: { executions?: Array<{ id: string; status: string }> } } | undefined;
      const currentExecution = queryData?.data?.executions?.find(
        (e: WorkflowExecution) => e.id === executionId
      );
      return currentExecution?.status === 'running' || currentExecution?.status === 'waiting_human' ? 2000 : false;
    },
  });

  // 获取待处理的人工任务
  const { data: pendingTasksData, refetch: refetchPendingTasks } = useQuery({
    queryKey: ['pendingHumanTasks', workflowId],
    queryFn: () => agentService.getPendingHumanTasks({ execution_id: workflowId }),
    enabled: !!workflowId && activeTab === 'human-tasks',
  });

  // 获取人工任务统计
  const { data: myTasksStatsData } = useQuery({
    queryKey: ['myTasksStatistics'],
    queryFn: () => agentService.getMyTaskStatistics(),
    enabled: activeTab === 'human-tasks',
  });

  // 提交人工任务结果
  const submitHumanTaskMutation = useMutation({
    mutationFn: (data: {
      taskId: string;
      action: 'approve' | 'reject';
      comment?: string;
      input_data?: Record<string, unknown>;
    }) =>
      agentService.submitHumanTask(data.taskId, {
        approved: data.action === 'approve',
        action: data.action,
        comment: data.comment,
        input_data: data.input_data,
      }),
    onSuccess: () => {
      message.success('人工任务已处理');
      setIsHumanTaskModalOpen(false);
      setCurrentHumanTask(null);
      setHumanTaskComment('');
      setHumanTaskInputData({});
      humanTaskForm.resetFields();
      refetchPendingTasks();
      refetchExecutions();
      queryClient.invalidateQueries({ queryKey: ['myTasksStatistics'] });
    },
    onError: () => {
      message.error('处理人工任务失败');
    },
  });

  // 启动工作流
  const startMutation = useMutation({
    mutationFn: (data?: { inputs?: Record<string, unknown> }) =>
      agentService.startWorkflow(workflowId!, data),
    onSuccess: (result) => {
      message.success('工作流已启动');
      setExecutionId(result.data.execution_id);
      refetchExecutions();
    },
    onError: () => {
      message.error('启动工作流失败');
    },
  });

  // 停止工作流
  const stopMutation = useMutation({
    mutationFn: (executionId: string) =>
      agentService.stopWorkflow(workflowId!, { execution_id: executionId }),
    onSuccess: () => {
      message.success('工作流已停止');
      refetchExecutions();
    },
    onError: () => {
      message.error('停止工作流失败');
    },
  });

  const handleStart = () => {
    try {
      const parsedInputs = JSON.parse(inputs);
      startMutation.mutate({ inputs: parsedInputs });
    } catch {
      message.error('输入数据格式错误，请输入有效的 JSON');
    }
  };

  const handleOpenHumanTask = (task: HumanTask) => {
    setCurrentHumanTask(task);
    setHumanTaskComment('');
    setHumanTaskInputData(task.input_data || {});

    // Pre-fill form with existing input data
    if (task.input_data) {
      humanTaskForm.setFieldsValue(task.input_data);
    }

    setIsHumanTaskModalOpen(true);
  };

  const handleSubmitHumanTask = (action: 'approve' | 'reject') => {
    if (!currentHumanTask) return;

    try {
      const formValues = humanTaskForm.getFieldsValue();
      submitHumanTaskMutation.mutate({
        taskId: currentHumanTask.human_task_id ?? '',
        action,
        comment: humanTaskComment || undefined,
        input_data: { ...humanTaskInputData, ...formValues },
      });
    } catch {
      message.error('表单数据验证失败');
    }
  };

  const renderFormField = (field: FormField) => {
    switch (field.type) {
      case 'textarea':
        return (
          <TextArea
            rows={4}
            placeholder={field.label}
            defaultValue={field.default as string}
          />
        );
      case 'number':
        return (
          <Input type="number" placeholder={field.label} defaultValue={field.default as number} />
        );
      case 'select':
        return (
          <Select placeholder={field.label} defaultValue={field.default as string}>
            {field.options?.map((opt) => (
              <Option key={opt} value={opt}>
                {opt}
              </Option>
            ))}
          </Select>
        );
      case 'boolean':
        return <Switch defaultChecked={field.default as boolean} />;
      case 'date':
        return <Input type="date" defaultValue={field.default as string} />;
      default:
        return (
          <Input placeholder={field.label} defaultValue={field.default as string} />
        );
    }
  };

  const renderFormSchema = (schema: FormSchema | string) => {
    const formSchema = typeof schema === 'string' ? JSON.parse(schema) as FormSchema : schema;

    return (
      <Form form={humanTaskForm} layout="vertical">
        {formSchema.fields.map((field) => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            rules={field.required ? [{ required: true, message: `请输入${field.label}` }] : []}
          >
            {renderFormField(field)}
          </Form.Item>
        ))}
      </Form>
    );
  };

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'orange', icon: <ClockCircleOutlined />, text: '等待中' },
      running: { color: 'blue', icon: <ReloadOutlined spin />, text: '运行中' },
      completed: { color: 'green', icon: <CheckCircleOutlined />, text: '已完成' },
      failed: { color: 'red', icon: <CloseCircleOutlined />, text: '失败' },
      stopped: { color: 'default', icon: <CloseCircleOutlined />, text: '已停止' },
      waiting_human: { color: 'purple', icon: <UserOutlined />, text: '等待人工审批' },
      error: { color: 'red', icon: <CloseCircleOutlined />, text: '错误' },
    };
    const config = statusConfig[status] || { color: 'default', icon: null, text: status };
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  const getHumanTaskStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待处理' },
      approved: { color: 'green', text: '已通过' },
      rejected: { color: 'red', text: '已拒绝' },
      timed_out: { color: 'default', text: '已超时' },
      timeout: { color: 'default', text: '已超时' },
      cancelled: { color: 'default', text: '已取消' },
    };
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getApprovalTypeTag = (type: string) => {
    const typeConfig: Record<string, { color: string; text: string }> = {
      single: { color: 'blue', text: '单人审批' },
      multi: { color: 'purple', text: '多人审批' },
      any: { color: 'cyan', text: '任意一人' },
      sequential: { color: 'green', text: '顺序审批' },
    };
    const config = typeConfig[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const formatDuration = (ms: number) => {
    if (!ms) return '-';
    const d = dayjs.duration(ms);
    if (d.asSeconds() < 60) return `${d.asSeconds().toFixed(2)}秒`;
    if (d.asMinutes() < 60) return `${d.asMinutes().toFixed(1)}分钟`;
    return `${d.asHours().toFixed(2)}小时`;
  };

  const workflow = workflowData?.data;
  const executions = executionsData?.data?.executions || [];
  const logs = logsData?.data?.logs || [];
  const currentExecution = executions.find((e: WorkflowExecution) => e.id === executionId);
  const pendingTasks = pendingTasksData?.data?.tasks || [];
  const myStats = myTasksStatsData?.data;

  const executionColumns = [
    {
      title: '执行 ID',
      dataIndex: 'id',
      key: 'id',
      width: 150,
      render: (id: string) => (
        <a onClick={() => { setExecutionId(id); setActiveTab('logs'); }}>
          {id}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: WorkflowExecution['status']) => getStatusTag(status),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (ms: number) => formatDuration(ms),
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: WorkflowExecution) => (
        <Space>
          {record.status === 'running' || record.status === 'pending' || record.status === 'waiting_human' ? (
            <Button
              type="text"
              size="small"
              danger
              onClick={() => stopMutation.mutate(record.id)}
              loading={stopMutation.isPending}
            >
              停止
            </Button>
          ) : (
            <Button
              type="text"
              size="small"
              onClick={() => {
                setExecutionId(record.id);
                setActiveTab('logs');
                refetchLogs();
              }}
            >
              查看日志
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const humanTaskColumns = [
    {
      title: '任务 ID',
      dataIndex: 'human_task_id',
      key: 'human_task_id',
      width: 150,
      ellipsis: true,
    },
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 150,
    },
    {
      title: '审批类型',
      dataIndex: 'approval_type',
      key: 'approval_type',
      width: 100,
      render: (type: string) => getApprovalTypeTag(type),
    },
    {
      title: '分配给',
      dataIndex: 'assignees',
      key: 'assignees',
      width: 150,
      render: (assignees: string[]) => (
        <Space size={4} wrap>
          {assignees?.slice(0, 2).map((a) => (
            <Tag key={a} color="blue" style={{ margin: 0 }}>
              {a}
            </Tag>
          ))}
          {assignees?.length > 2 && <Tag style={{ margin: 0 }}>+{assignees.length - 2}</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: HumanTask['status']) => getHumanTaskStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => dayjs(date).format('MM-DD HH:mm'),
    },
    {
      title: '超时时间',
      dataIndex: 'timeout_at',
      key: 'timeout_at',
      width: 160,
      render: (date: string) => date ? dayjs(date).format('MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: HumanTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setExecutionId(record.execution_id);
              setActiveTab('logs');
            }}
          >
            查看日志
          </Button>
          {record.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              onClick={() => handleOpenHumanTask(record)}
            >
              处理
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'executions',
      label: `执行历史 (${executions.length})`,
      children: (
        <div className="execution-list">
          {executions.length === 0 ? (
            <Empty description="暂无执行记录" />
          ) : (
            <table className="execution-table">
              <thead>
                <tr>
                  {executionColumns.map((col) => (
                    <th key={col.key} style={{ width: col.width }}>
                      {col.title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {executions.map((execution: WorkflowExecution) => (
                  <tr key={execution.id}>
                    <td>
                      <a onClick={() => { setExecutionId(execution.id); setActiveTab('logs'); }}>
                        {execution.id}
                      </a>
                    </td>
                    <td>{getStatusTag(execution.status)}</td>
                    <td>{formatDuration(execution.duration_ms ?? 0)}</td>
                    <td>{execution.started_at ? dayjs(execution.started_at).format('MM-DD HH:mm:ss') : '-'}</td>
                    <td>{execution.completed_at ? dayjs(execution.completed_at).format('MM-DD HH:mm:ss') : '-'}</td>
                    <td>
                      {execution.status === 'running' || execution.status === 'pending' || execution.status === 'waiting_human' ? (
                        <Button
                          type="text"
                          size="small"
                          danger
                          onClick={() => stopMutation.mutate(execution.id)}
                          loading={stopMutation.isPending}
                        >
                          停止
                        </Button>
                      ) : (
                        <Button
                          type="text"
                          size="small"
                          onClick={() => {
                            setExecutionId(execution.id);
                            setActiveTab('logs');
                            refetchLogs();
                          }}
                        >
                          查看日志
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ),
    },
    {
      key: 'human-tasks',
      label: (
        <span>
          人工任务
          {pendingTasks.length > 0 && (
            <Badge count={pendingTasks.length} style={{ marginLeft: 8 }} />
          )}
        </span>
      ),
      children: (
        <div>
          {myStats && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="待处理"
                    value={myStats.pending_count || 0}
                    prefix={<ClockCircleOutlined />}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="已通过"
                    value={myStats.approved_count || 0}
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="已拒绝"
                    value={myStats.rejected_count || 0}
                    prefix={<CloseCircleOutlined />}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均处理时间"
                    value={myStats.avg_processing_time_minutes || 0}
                    suffix="分钟"
                    precision={1}
                  />
                </Card>
              </Col>
            </Row>
          )}

          <div className="human-task-list">
            {pendingTasks.length === 0 ? (
              <Empty description="暂无待处理的人工任务" />
            ) : (
              <table className="human-task-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                    {humanTaskColumns.map((col) => (
                      <th
                        key={col.key}
                        style={{
                          width: col.width,
                          padding: '12px 8px',
                          textAlign: 'left',
                          background: '#fafafa',
                          fontWeight: 500,
                        }}
                      >
                        {col.title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pendingTasks.map((task: HumanTask) => (
                    <tr key={task.human_task_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '12px 8px' }}>{task.human_task_id}</td>
                      <td style={{ padding: '12px 8px' }}>{task.task_name}</td>
                      <td style={{ padding: '12px 8px' }}>{getApprovalTypeTag(task.approval_type ?? '')}</td>
                      <td style={{ padding: '12px 8px' }}>
                        <Space size={4} wrap>
                          {task.assignees?.slice(0, 2).map((a) => (
                            <Tag key={a} color="blue" style={{ margin: 0 }}>
                              {a}
                            </Tag>
                          ))}
                          {(task.assignees?.length ?? 0) > 2 && <Tag style={{ margin: 0 }}>+{(task.assignees?.length ?? 0) - 2}</Tag>}
                        </Space>
                      </td>
                      <td style={{ padding: '12px 8px' }}>{getHumanTaskStatusTag(task.status)}</td>
                      <td style={{ padding: '12px 8px' }}>{dayjs(task.created_at).format('MM-DD HH:mm')}</td>
                      <td style={{ padding: '12px 8px' }}>{task.timeout_at ? dayjs(task.timeout_at).format('MM-DD HH:mm') : '-'}</td>
                      <td style={{ padding: '12px 8px' }}>
                        <Space>
                          <Button
                            type="link"
                            size="small"
                            icon={<EyeOutlined />}
                            onClick={() => {
                              setExecutionId(task.execution_id);
                              setActiveTab('logs');
                            }}
                          >
                            查看日志
                          </Button>
                          {task.status === 'pending' && (
                            <Button
                              type="primary"
                              size="small"
                              onClick={() => handleOpenHumanTask(task)}
                            >
                              处理
                            </Button>
                          )}
                        </Space>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'logs',
      label: '执行日志',
      children: (
        <>
          {!executionId ? (
            <Empty description="请选择一个执行记录查看日志" />
          ) : (
            <>
              <div style={{ marginBottom: 16 }}>
                <Space>
                  <span>执行 ID:</span>
                  <Tag>{executionId}</Tag>
                  {currentExecution && getStatusTag(currentExecution.status)}
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => refetchLogs()}
                  >
                    刷新
                  </Button>
                </Space>
              </div>
              <WorkflowLogViewer logs={logs} />
            </>
          )}
        </>
      ),
    },
    {
      key: 'input',
      label: '输入配置',
      children: (
        <div>
          <TextArea
            value={inputs}
            onChange={(e) => setInputs(e.target.value)}
            rows={10}
            placeholder='输入 JSON 格式的参数，例如：{\n  "query": "测试问题"\n}'
          />
          <div style={{ marginTop: 16 }}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStart}
              loading={startMutation.isPending}
            >
              启动工作流
            </Button>
          </div>
        </div>
      ),
    },
  ];

  if (!workflow) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/workflows')}
        style={{ marginBottom: 16 }}
      >
        返回工作流列表
      </Button>

      <Card
        title={workflow.name}
        extra={getStatusTag(workflow.status)}
      >
        <Descriptions column={2} size="small">
          <Descriptions.Item label="工作流 ID">{workflow.workflow_id}</Descriptions.Item>
          <Descriptions.Item label="类型">{workflow.type}</Descriptions.Item>
          <Descriptions.Item label="创建者">{workflow.created_by || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(workflow.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {workflow.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card style={{ marginTop: 16 }} title="工作流执行">
        {currentExecution && (currentExecution.status === 'running' || currentExecution.status === 'waiting_human') && (
          <Alert
            message={currentExecution.status === 'waiting_human' ? '工作流等待人工审批' : '工作流正在运行中'}
            description={currentExecution.status === 'waiting_human'
              ? '请在"人工任务"标签页中处理待审批的任务'
              : '执行完成后将自动更新状态'}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {currentExecution && currentExecution.status === 'failed' && (
          <Alert
            message="工作流执行失败"
            description={currentExecution.error}
            type="error"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {currentExecution && currentExecution.status === 'completed' && (
          <Alert
            message="工作流执行完成"
            description={`耗时: ${formatDuration(currentExecution.duration_ms ?? 0)}`}
            type="success"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* 人工任务处理模态框 */}
      <Modal
        title={
          <Space>
            <UserOutlined />
            <span>人工任务: {currentHumanTask?.task_name}</span>
          </Space>
        }
        open={isHumanTaskModalOpen}
        onCancel={() => {
          setIsHumanTaskModalOpen(false);
          setCurrentHumanTask(null);
          setHumanTaskComment('');
          setHumanTaskInputData({});
          humanTaskForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        {currentHumanTask && (
          <div>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="任务 ID">{currentHumanTask.human_task_id}</Descriptions.Item>
              <Descriptions.Item label="审批类型">
                {getApprovalTypeTag(currentHumanTask.approval_type ?? '')}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getHumanTaskStatusTag(currentHumanTask.status)}
              </Descriptions.Item>
              <Descriptions.Item label="分配给">
                <Space size={4} wrap>
                  {currentHumanTask.assignees?.map((a) => (
                    <Tag key={a} color="blue">{a}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              {currentHumanTask.timeout_at && (
                <Descriptions.Item label="超时时间">
                  <Tag color={dayjs().isAfter(dayjs(currentHumanTask.timeout_at)) ? 'red' : 'orange'}>
                    {dayjs(currentHumanTask.timeout_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Tag>
                </Descriptions.Item>
              )}
            </Descriptions>

            {currentHumanTask.description && (
              <Alert
                message="任务说明"
                description={currentHumanTask.description}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {currentHumanTask.input_data && Object.keys(currentHumanTask.input_data).length > 0 && (
              <Card size="small" title="输入数据" style={{ marginBottom: 16 }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {JSON.stringify(currentHumanTask.input_data, null, 2)}
                </pre>
              </Card>
            )}

            {currentHumanTask.form_schema && (
              <Card size="small" title="表单填写" style={{ marginBottom: 16 }}>
                {renderFormSchema(currentHumanTask.form_schema as FormSchema | string)}
              </Card>
            )}

            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>审批意见</div>
              <TextArea
                rows={3}
                value={humanTaskComment}
                onChange={(e) => setHumanTaskComment(e.target.value)}
                placeholder="请输入审批意见（可选）"
              />
            </div>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={() => handleSubmitHumanTask('reject')}
                  loading={submitHumanTaskMutation.isPending}
                >
                  拒绝
                </Button>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={() => handleSubmitHumanTask('approve')}
                  loading={submitHumanTaskMutation.isPending}
                >
                  通过
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default WorkflowExecutePage;
