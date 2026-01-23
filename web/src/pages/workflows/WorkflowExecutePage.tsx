import { useState, useEffect } from 'react';
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
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import bisheng, { type WorkflowExecution, type ExecutionLog } from '@/services/bisheng';
import WorkflowLogViewer from '@/components/WorkflowLogViewer';
import './WorkflowsPage.less';

dayjs.extend(duration);
dayjs.extend(relativeTime);

const { TextArea } = Input;

function WorkflowExecutePage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();

  const [executionId, setExecutionId] = useState<string | null>(null);
  const [inputs, setInputs] = useState('{\n  "query": "测试查询"\n}');
  const [activeTab, setActiveTab] = useState('executions');

  // 获取工作流信息
  const { data: workflowData } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => bisheng.getWorkflow(workflowId!),
    enabled: !!workflowId,
  });

  // 获取执行历史
  const { data: executionsData, refetch: refetchExecutions } = useQuery({
    queryKey: ['workflowExecutions', workflowId],
    queryFn: () => bisheng.getWorkflowExecutions(workflowId!),
    enabled: !!workflowId,
    refetchInterval: (data) => {
      // 如果有运行中的执行，每2秒轮询一次
      const hasRunning = data?.data?.executions?.some(
        (e: WorkflowExecution) => e.status === 'running' || e.status === 'pending'
      );
      return hasRunning ? 2000 : false;
    },
  });

  // 获取当前执行的日志
  const { data: logsData, refetch: refetchLogs } = useQuery({
    queryKey: ['executionLogs', executionId],
    queryFn: () => bisheng.getExecutionLogs(executionId!),
    enabled: !!executionId && activeTab === 'logs',
    refetchInterval: (data) => {
      // 如果执行仍在运行，每2秒轮询日志
      const currentExecution = executionsData?.data?.executions?.find(
        (e: WorkflowExecution) => e.id === executionId
      );
      return currentExecution?.status === 'running' ? 2000 : false;
    },
  });

  // 启动工作流
  const startMutation = useMutation({
    mutationFn: (data?: { inputs?: Record<string, unknown> }) =>
      bisheng.startWorkflow(workflowId!, data),
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
      bisheng.stopWorkflow(workflowId!, { execution_id: executionId }),
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

  const getStatusTag = (status: WorkflowExecution['status']) => {
    const statusConfig = {
      pending: { color: 'orange', icon: <ClockCircleOutlined />, text: '等待中' },
      running: { color: 'blue', icon: <ReloadOutlined spin />, text: '运行中' },
      completed: { color: 'green', icon: <CheckCircleOutlined />, text: '已完成' },
      failed: { color: 'red', icon: <CloseCircleOutlined />, text: '失败' },
      stopped: { color: 'default', icon: <CloseCircleOutlined />, text: '已停止' },
    };
    const config = statusConfig[status] || { color: 'default', icon: null, text: status };
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
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
          {record.status === 'running' || record.status === 'pending' ? (
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
                    <td>{formatDuration(execution.duration_ms)}</td>
                    <td>{execution.started_at ? dayjs(execution.started_at).format('MM-DD HH:mm:ss') : '-'}</td>
                    <td>{execution.completed_at ? dayjs(execution.completed_at).format('MM-DD HH:mm:ss') : '-'}</td>
                    <td>
                      {execution.status === 'running' || execution.status === 'pending' ? (
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
        {currentExecution && currentExecution.status === 'running' && (
          <Alert
            message="工作流正在运行中"
            description="执行完成后将自动更新状态"
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
            description={`耗时: ${formatDuration(currentExecution.duration_ms)}`}
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
    </div>
  );
}

export default WorkflowExecutePage;
