import { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Select,
  Input,
  Tooltip,
  Statistic,
  Row,
  Col,
  Progress,
  Modal,
} from 'antd';
import {
  ReloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  StopOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import bisheng, { type WorkflowExecution, type Workflow } from '@/services/bisheng';
import ExecutionLogsModal from './ExecutionLogsModal';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

dayjs.extend(duration);
dayjs.extend(relativeTime);

const { Search } = Input;

// 获取执行状态配置
const getStatusConfig = (status: WorkflowExecution['status']) => {
  const config = {
    pending: { color: 'default', text: '等待中', icon: <ClockCircleOutlined /> },
    running: { color: 'processing', text: '运行中', icon: <LoadingOutlined /> },
    completed: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
    failed: { color: 'error', text: '失败', icon: <CloseCircleOutlined /> },
    stopped: { color: 'default', text: '已停止', icon: <StopOutlined /> },
    waiting_human: { color: 'warning', text: '等待人工', icon: <ClockCircleOutlined /> },
  };
  return config[status];
};

// 格式化持续时间
const formatDuration = (durationMs?: number): string => {
  if (!durationMs) return '-';
  if (durationMs < 1000) return `${durationMs}ms`;
  if (durationMs < 60000) return `${(durationMs / 1000).toFixed(1)}s`;
  return dayjs.duration(durationMs).humanize();
};

function ExecutionsDashboard() {
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | undefined>();
  const [selectedStatus, setSelectedStatus] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取工作流列表（用于筛选）
  const { data: workflowsData } = useQuery({
    queryKey: ['workflows'],
    queryFn: bisheng.getWorkflows,
  });

  // 获取执行列表
  const { data: executionsData, isLoading, refetch } = useQuery({
    queryKey: ['executions', selectedWorkflowId, selectedStatus],
    queryFn: () =>
      bisheng.listExecutions({
        workflow_id: selectedWorkflowId,
        status: selectedStatus,
        limit: 100,
      }),
    refetchInterval: autoRefresh ? 5000 : false, // 自动刷新5秒
  });

  const executions = executionsData?.data?.executions || [];
  const workflows = workflowsData?.data?.workflows || [];

  const getWorkflowName = (workflowId: string): string => {
    const workflow = workflows.find((w: Workflow) => w.workflow_id === workflowId);
    return workflow?.name || workflowId;
  };

  const getWorkflowType = (workflowId: string): string => {
    const workflow = workflows.find((w: Workflow) => w.workflow_id === workflowId);
    return workflow?.type || 'custom';
  };

  // 根据搜索文本过滤
  const filteredExecutions = executions.filter((exec: WorkflowExecution) => {
    if (!searchText) return true;
    const workflowName = getWorkflowName(exec.workflow_id).toLowerCase();
    const searchLower = searchText.toLowerCase();
    return (
      workflowName.includes(searchLower) ||
      exec.id.toLowerCase().includes(searchLower) ||
      exec.workflow_id.toLowerCase().includes(searchLower)
    );
  });

  // 统计数据
  const stats = {
    total: executions.length,
    running: executions.filter((e: WorkflowExecution) => e.status === 'running').length,
    completed: executions.filter((e: WorkflowExecution) => e.status === 'completed').length,
    failed: executions.filter((e: WorkflowExecution) => e.status === 'failed').length,
  };

  const handleViewLogs = (executionId: string) => {
    setSelectedExecutionId(executionId);
    setLogsModalOpen(true);
  };

  const handleViewDetail = (execution: WorkflowExecution) => {
    setSelectedExecution(execution);
    setDetailModalOpen(true);
  };

  const columns = [
    {
      title: '执行ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Tooltip title={id}>
          <code style={{ fontSize: '12px' }}>{id.slice(0, 8)}...</code>
        </Tooltip>
      ),
    },
    {
      title: '工作流',
      dataIndex: 'workflow_id',
      key: 'workflow_id',
      render: (workflowId: string) => {
        const name = getWorkflowName(workflowId);
        const type = getWorkflowType(workflowId);
        return (
          <Space>
            <span style={{ fontWeight: 500 }}>{name}</span>
            <Tag color={type === 'rag' ? 'blue' : type === 'text2sql' ? 'purple' : 'cyan'}>
              {type.toUpperCase()}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: WorkflowExecution['status']) => {
        const config = getStatusConfig(status);
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
      filters: [
        { text: '等待中', value: 'pending' },
        { text: '运行中', value: 'running' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
        { text: '已停止', value: 'stopped' },
      ],
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (date: string) => (
        <Tooltip title={date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'}>
          <span>{date ? dayjs(date).fromNow() : '-'}</span>
        </Tooltip>
      ),
      sorter: (a: WorkflowExecution, b: WorkflowExecution) =>
        dayjs(a.started_at || 0).unix() - dayjs(b.started_at || 0).unix(),
    },
    {
      title: '持续时间',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (durationMs: number, record: WorkflowExecution) => {
        if (record.status === 'running' && record.started_at) {
          const runningDuration = Date.now() - dayjs(record.started_at).valueOf();
          return <span style={{ color: '#1677ff' }}>{formatDuration(runningDuration)}</span>;
        }
        return <span>{formatDuration(durationMs)}</span>;
      },
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
      render: (error: string) =>
        error ? (
          <Tooltip title={error}>
            <span style={{ color: '#ff4d4f' }}>{error.slice(0, 30)}...</span>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: WorkflowExecution) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="查看日志">
            <Button
              type="text"
              icon={<FileTextOutlined />}
              onClick={() => handleViewLogs(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card>
            <Statistic title="总执行数" value={stats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.running}
              valueStyle={{ color: '#1677ff' }}
              prefix={<LoadingOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failed}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <ClockCircleOutlined />
            <span>执行历史仪表板</span>
            {stats.running > 0 && (
              <Tag color="processing">
                {stats.running} 个运行中
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Select
              placeholder="选择工作流"
              allowClear
              style={{ width: 200 }}
              value={selectedWorkflowId}
              onChange={setSelectedWorkflowId}
              options={workflows.map((wf: Workflow) => ({
                label: wf.name,
                value: wf.workflow_id,
              }))}
            />
            <Select
              placeholder="选择状态"
              allowClear
              style={{ width: 120 }}
              value={selectedStatus}
              onChange={setSelectedStatus}
              options={[
                { label: '等待中', value: 'pending' },
                { label: '运行中', value: 'running' },
                { label: '已完成', value: 'completed' },
                { label: '失败', value: 'failed' },
              ]}
            />
            <Search
              placeholder="搜索工作流或ID"
              allowClear
              style={{ width: 200 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={<ReloadOutlined spin={autoRefresh && stats.running > 0} />}
              onClick={() => {
                setAutoRefresh(!autoRefresh);
                refetch();
              }}
            >
              {autoRefresh ? '自动刷新' : '刷新'}
            </Button>
          </Space>
        }
      >
        {/* 成功率进度条 */}
        {stats.total > 0 && (
          <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span>成功率</span>
              <span>{((stats.completed / stats.total) * 100).toFixed(1)}%</span>
            </div>
            <Progress
              percent={Number(((stats.completed / stats.total) * 100).toFixed(1))}
              success={{
                percent: Number(((stats.completed / stats.total) * 100).toFixed(1)),
              }}
              strokeColor={{
                '0%': '#52c41a',
                '100%': '#52c41a',
              }}
            />
          </div>
        )}

        <Table
          columns={columns}
          dataSource={filteredExecutions}
          rowKey="id"
          loading={isLoading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            defaultPageSize: 20,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          rowClassName={(record) => {
            if (record.status === 'running') return 'row-running';
            if (record.status === 'failed') return 'row-failed';
            return '';
          }}
        />
      </Card>

      {/* 日志查看弹窗 */}
      <ExecutionLogsModal
        executionId={selectedExecutionId}
        open={logsModalOpen}
        onClose={() => {
          setLogsModalOpen(false);
          setSelectedExecutionId(null);
        }}
      />

      {/* 执行详情弹窗 */}
      <Modal
        title="执行详情"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedExecution(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            关闭
          </Button>,
          <Button
            key="logs"
            type="primary"
            icon={<FileTextOutlined />}
            onClick={() => {
              setDetailModalOpen(false);
              handleViewLogs(selectedExecution!.id);
            }}
          >
            查看日志
          </Button>,
        ]}
        width={600}
      >
        {selectedExecution && (
          <div>
            <p>
              <strong>执行ID：</strong>
              <code>{selectedExecution.id}</code>
            </p>
            <p>
              <strong>工作流：</strong>
              {getWorkflowName(selectedExecution.workflow_id)}
            </p>
            <p>
              <strong>状态：</strong>
              {(() => {
                const config = getStatusConfig(selectedExecution.status);
                return (
                  <Tag color={config.color} icon={config.icon}>
                    {config.text}
                  </Tag>
                );
              })()}
            </p>
            <p>
              <strong>开始时间：</strong>
              {selectedExecution.started_at
                ? dayjs(selectedExecution.started_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </p>
            <p>
              <strong>完成时间：</strong>
              {selectedExecution.completed_at
                ? dayjs(selectedExecution.completed_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </p>
            <p>
              <strong>持续时间：</strong>
              {formatDuration(selectedExecution.duration_ms)}
            </p>
            {selectedExecution.error && (
              <p>
                <strong>错误信息：</strong>
                <span style={{ color: '#ff4d4f' }}>{selectedExecution.error}</span>
              </p>
            )}
            {selectedExecution.inputs && Object.keys(selectedExecution.inputs).length > 0 && (
              <div>
                <strong>输入参数：</strong>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: '8px',
                    borderRadius: '4px',
                    marginTop: '8px',
                    fontSize: '12px',
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(selectedExecution.inputs, null, 2)}
                </pre>
              </div>
            )}
            {selectedExecution.outputs !== undefined && selectedExecution.outputs !== null && (
              <div style={{ marginTop: '16px' }}>
                <strong>输出结果：</strong>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: '8px',
                    borderRadius: '4px',
                    marginTop: '8px',
                    fontSize: '12px',
                    overflow: 'auto',
                  }}
                >
                  {typeof selectedExecution.outputs === 'string'
                    ? selectedExecution.outputs
                    : JSON.stringify(selectedExecution.outputs, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      <style>{`
        .row-running {
          background-color: #e6f7ff;
        }
        .row-failed {
          background-color: #fff2f0;
        }
        .row-running:hover,
        .row-failed:hover {
          background-color: #fafafa !important;
        }
      `}</style>
    </div>
  );
}

// 使用 ErrorBoundary 包裹导出组件
function ExecutionsDashboardWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <ExecutionsDashboard />
    </ErrorBoundary>
  );
}

export default ExecutionsDashboardWithErrorBoundary;
