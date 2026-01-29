import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Drawer,
  Tabs,
  Divider,
  Alert,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import data from '@/services/data';
import type { OfflineWorkflow, WorkflowExecution } from '@/services/data';

const { Option } = Select;
const { TextArea } = Input;

function OfflinePage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isExecutionModalOpen, setIsExecutionModalOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<OfflineWorkflow | null>(null);

  const [form] = Form.useForm();

  // Queries
  const { data: workflowsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['offline-workflows', page, pageSize, statusFilter],
    queryFn: () =>
      data.getOfflineWorkflows({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const { data: executionsData, isLoading: isLoadingExecutions } = useQuery({
    queryKey: ['workflow-executions', selectedWorkflow?.workflow_id],
    queryFn: () =>
      data.getWorkflowExecutions(selectedWorkflow!.workflow_id),
    enabled: !!selectedWorkflow && isExecutionModalOpen,
    refetchInterval: 5000,
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'green',
      inactive: 'default',
      draft: 'orange',
      running: 'blue',
      success: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      active: '活跃',
      inactive: '停用',
      draft: '草稿',
      running: '运行中',
      success: '成功',
      failed: '失败',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '工作流名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: OfflineWorkflow) => (
        <a onClick={() => { setSelectedWorkflow(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
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
      title: '节点数',
      key: 'nodes',
      render: (_: unknown, record: OfflineWorkflow) => record.nodes.length,
    },
    {
      title: '边数',
      key: 'edges',
      render: (_: unknown, record: OfflineWorkflow) => record.edges.length,
    },
    {
      title: '调度',
      key: 'schedule',
      render: (_: unknown, record: OfflineWorkflow) =>
        record.schedule ? (
          <Tag color="blue">
            {record.schedule.type === 'cron' ? 'Cron' : '事件'}: {record.schedule.expression}
          </Tag>
        ) : (
          <Tag>手动</Tag>
        ),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
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
      width: 200,
      render: (_: unknown, record: OfflineWorkflow) => (
        <Space>
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={() => {
              setSelectedWorkflow(record);
              setIsExecutionModalOpen(true);
            }}
          >
            执行
          </Button>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedWorkflow(record);
              setIsDetailDrawerOpen(true);
            }}
          />
        </Space>
      ),
    },
  ];

  const executionColumns = [
    {
      title: '执行ID',
      dataIndex: 'execution_id',
      key: 'execution_id',
      ellipsis: true,
      render: (id: string) => <code style={{ fontSize: 11 }}>{id.slice(0, 8)}...</code>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors: Record<string, string> = {
          running: 'processing',
          success: 'success',
          failed: 'error',
          cancelled: 'default',
        };
        const texts: Record<string, string> = {
          running: '运行中',
          success: '成功',
          failed: '失败',
          cancelled: '已取消',
        };
        return (
          <Tag
            color={colors[status]}
            icon={
              status === 'running' ? (
                <ClockCircleOutlined spin />
              ) : status === 'success' ? (
                <CheckCircleOutlined />
              ) : status === 'failed' ? (
                <ExclamationCircleOutlined />
              ) : undefined
            }
          >
            {texts[status]}
          </Tag>
        );
      },
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: WorkflowExecution) => {
        const total = record.node_statuses?.length || 0;
        const completed = record.node_statuses?.filter((s) => s.status === 'completed').length || 0;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
        return <Progress percent={percent} size="small" status={record.status === 'failed' ? 'exception' : 'active'} />;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm:ss'),
    },
    {
      title: '耗时',
      key: 'duration',
      render: (_: unknown, record: WorkflowExecution) =>
        record.duration_ms ? `${(record.duration_ms / 1000).toFixed(1)}s` : '-',
    },
    {
      title: '触发者',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
    },
  ];

  // 渲染工作流 DAG
  const renderDAG = (workflow: OfflineWorkflow) => {
    const nodePositions: Record<string, { x: number; y: number }> = {};
    workflow.nodes.forEach((node, index) => {
      const col = index % 3;
      const row = Math.floor(index / 3);
      nodePositions[node.node_id] = { x: col * 200 + 50, y: row * 100 + 50 };
    });

    return (
      <div style={{ position: 'relative', height: 400, background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 4 }}>
        {workflow.nodes.map((node) => {
          const pos = nodePositions[node.node_id] || { x: 0, y: 0 };
          const nodeTypeColors: Record<string, string> = {
            sql: 'blue',
            shell: 'green',
            python: 'orange',
            spark: 'purple',
            data_quality: 'cyan',
          };
          return (
            <div
              key={node.node_id}
              style={{
                position: 'absolute',
                left: pos.x,
                top: pos.y,
                padding: '8px 16px',
                background: 'white',
                border: '2px solid ' + (nodeTypeColors[node.type] || 'gray'),
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                minWidth: 120,
                textAlign: 'center',
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{node.name}</div>
              <Tag color={nodeTypeColors[node.type]}>{node.type}</Tag>
            </div>
          );
        })}
        {workflow.edges.map((edge) => {
          const sourcePos = nodePositions[edge.source] || { x: 0, y: 0 };
          const targetPos = nodePositions[edge.target] || { x: 0, y: 0 };
          return (
            <svg
              key={edge.edge_id}
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            >
              <line
                x1={sourcePos.x + 60}
                y1={sourcePos.y + 30}
                x2={targetPos.x + 60}
                y2={targetPos.y + 30}
                stroke="#999"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
              />
            </svg>
          );
        })}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
          </marker>
        </defs>
      </div>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="离线开发工作流"
        extra={
          <Space>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              onChange={setStatusFilter}
              value={statusFilter || undefined}
            >
              <Option value="active">活跃</Option>
              <Option value="inactive">停用</Option>
              <Option value="draft">草稿</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => {/* refresh */}}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建工作流
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={workflowsData?.data?.workflows || []}
          rowKey="workflow_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: workflowsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 工作流详情抽屉 */}
      <Drawer
        title="工作流详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedWorkflow(null);
        }}
        width={800}
      >
        {selectedWorkflow && (
          <div>
            <Alert
              message="工作流 DAG 预览"
              description="此为工作流的可视化预览，实际执行时节点可能会根据条件跳过"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            {renderDAG(selectedWorkflow)}

            <Divider />

            <Tabs
              defaultActiveKey="info"
              items={[
                {
                  key: 'info',
                  label: '基本信息',
                  children: (
                    <Card title="工作流配置" size="small">
                      <p><strong>名称:</strong> {selectedWorkflow.name}</p>
                      <p><strong>描述:</strong> {selectedWorkflow.description || '-'}</p>
                      <p><strong>状态:</strong> <Tag color={getStatusColor(selectedWorkflow.status)}>{getStatusText(selectedWorkflow.status)}</Tag></p>
                      <p><strong>调度:</strong> {selectedWorkflow.schedule ? `${selectedWorkflow.schedule.type}: ${selectedWorkflow.schedule.expression}` : '手动执行'}</p>
                      <p><strong>创建者:</strong> {selectedWorkflow.created_by}</p>
                      <p><strong>创建时间:</strong> {dayjs(selectedWorkflow.created_at).format('YYYY-MM-DD HH:mm:ss')}</p>
                      {selectedWorkflow.variables && (
                        <div>
                          <strong>变量:</strong>
                          <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                            {JSON.stringify(selectedWorkflow.variables, null, 2)}
                          </pre>
                        </div>
                      )}
                    </Card>
                  ),
                },
                {
                  key: 'nodes',
                  label: '节点列表',
                  children: (
                    <Card title="任务节点" size="small">
                      <Table
                        columns={[
                          { title: '节点名称', dataIndex: 'name', key: 'name' },
                          { title: '类型', dataIndex: 'type', key: 'type', render: (type: string) => <Tag>{type}</Tag> },
                          { title: '位置', key: 'position', render: (_: unknown, node: any) => `(${node.position.x}, ${node.position.y})` },
                        ]}
                        dataSource={selectedWorkflow.nodes}
                        rowKey="node_id"
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  ),
                },
                {
                  key: 'executions',
                  label: '执行历史',
                  children: (
                    <Card
                      title="执行记录"
                      extra={
                        <Button
                          size="small"
                          icon={<ReloadOutlined />}
                          onClick={() => {
                            // refetch
                          }}
                        >
                          刷新
                        </Button>
                      }
                    >
                      <Table
                        columns={executionColumns}
                        dataSource={executionsData?.data?.executions || []}
                        rowKey="execution_id"
                        loading={isLoadingExecutions}
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Drawer>

      {/* 执行工作流模态框 */}
      <Modal
        title="执行工作流"
        open={isExecutionModalOpen}
        onCancel={() => {
          setIsExecutionModalOpen(false);
        }}
        footer={null}
        width={800}
      >
        {selectedWorkflow && (
          <div>
            <Alert
              message={`准备执行工作流: ${selectedWorkflow.name}`}
              description="请确认工作流配置和变量设置"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Form layout="vertical">
              {selectedWorkflow.variables && Object.keys(selectedWorkflow.variables).length > 0 && (
                <Form.Item label="工作流变量">
                  {Object.entries(selectedWorkflow.variables).map(([key, value]) => (
                    <div key={key} style={{ marginBottom: 8 }}>
                      <span style={{ fontWeight: 'bold' }}>{key}:</span>
                      <Input
                        defaultValue={value as string}
                        placeholder={`请输入 ${key}`}
                        style={{ marginLeft: 8 }}
                      />
                    </div>
                  ))}
                </Form.Item>
              )}
              <Form.Item>
                <Space>
                  <Button type="primary" icon={<PlayCircleOutlined />}>
                    开始执行
                  </Button>
                  <Button onClick={() => setIsExecutionModalOpen(false)}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            <Divider />

            <div>
              <h4>工作流预览</h4>
              {renderDAG(selectedWorkflow)}

              <h4 style={{ marginTop: 24 }}>节点列表</h4>
              <Table
                columns={[
                  { title: '名称', dataIndex: 'name', key: 'name' },
                  { title: '类型', dataIndex: 'type', key: 'type' },
                  { title: '描述', dataIndex: 'description', key: 'description', render: (desc?: string) => desc || '-' },
                ]}
                dataSource={selectedWorkflow.nodes}
                rowKey="node_id"
                pagination={false}
                size="small"
              />
            </div>
          </div>
        )}
      </Modal>

      {/* 创建工作流模态框 */}
      <Modal
        title="创建工作流"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Alert
          message="工作流编辑器"
          description="完整的工作流编辑器功能正在开发中，请使用基础配置创建工作流"
          type="info"
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          <Form.Item
            label="工作流名称"
            name="name"
            rules={[{ required: true, message: '请输入工作流名称' }]}
          >
            <Input placeholder="请输入工作流名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="调度类型" name="schedule_type">
            <Select placeholder="选择调度类型" allowClear>
              <Option value="cron">Cron 表达式</Option>
              <Option value="interval">间隔</Option>
              <Option value="manual">手动执行</Option>
            </Select>
          </Form.Item>
          <Form.Item label="Cron 表达式" name="cron_expression">
            <Input placeholder="0 0 * * * ?" />
          </Form.Item>
          <Button type="primary" block>
            创建工作流（简化版）
          </Button>
        </Form>
      </Modal>
    </div>
  );
}

export default OfflinePage;
