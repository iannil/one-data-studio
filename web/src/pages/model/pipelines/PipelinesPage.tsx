import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Drawer,
  Tag,
  Divider,
  Alert,
  Table,
  Tabs,
  Descriptions,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  FolderOpenOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import model from '@/services/model';
import type {
  Pipeline,
  CreatePipelineRequest,
  PipelineExecution,
  PipelineNode,
  PipelineEdge,
} from '@/services/model';

const { Option } = Select;
const { TextArea } = Input;

function PipelinesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isExecutionDrawerOpen, setIsExecutionDrawerOpen] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);

  const [form] = Form.useForm();
  const [nodes, setNodes] = useState<PipelineNode[]>([]);
  const [edges, setEdges] = useState<PipelineEdge[]>([]);

  // Queries
  const { data: pipelinesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['pipelines', page, pageSize, statusFilter],
    queryFn: () =>
      model.getPipelines({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const { data: templatesData } = useQuery({
    queryKey: ['pipeline-templates'],
    queryFn: () => model.getPipelineTemplates(),
  });

  const { data: executionsData, isLoading: isLoadingExecutions } = useQuery({
    queryKey: ['pipeline-executions', selectedPipeline?.pipeline_id],
    queryFn: () =>
      model.getPipelineExecutions(selectedPipeline!.pipeline_id),
    enabled: !!selectedPipeline && isExecutionDrawerOpen,
    refetchInterval: 5000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: model.createPipeline,
    onSuccess: () => {
      message.success('Pipeline 创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      setNodes([]);
      setEdges([]);
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
    onError: () => {
      message.error('Pipeline 创建失败');
    },
  });

  const stopExecutionMutation = useMutation({
    mutationFn: model.stopPipelineExecution,
    onSuccess: () => {
      message.success('执行已停止');
      queryClient.invalidateQueries({ queryKey: ['pipeline-executions'] });
    },
    onError: () => {
      message.error('停止执行失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'green',
      paused: 'orange',
      draft: 'default',
      archived: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      active: '活跃',
      paused: '暂停',
      draft: '草稿',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: 'Pipeline 名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Pipeline) => (
        <a onClick={() => { setSelectedPipeline(record); setIsDetailDrawerOpen(true); }}>
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
      render: (_: unknown, record: Pipeline) => record.nodes.length,
    },
    {
      title: '边数',
      key: 'edges',
      render: (_: unknown, record: Pipeline) => record.edges.length,
    },
    {
      title: '调度',
      key: 'schedule',
      render: (_: unknown, record: Pipeline) =>
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
  ];

  // 添加节点
  const handleAddNode = () => {
    const newNode: PipelineNode = {
      node_id: `node_${Date.now()}`,
      name: `节点 ${nodes.length + 1}`,
      type: 'process',
      config: { parameters: {} },
      position: { x: Math.random() * 600, y: Math.random() * 400 },
    };
    setNodes([...nodes, newNode]);
  };

  // 渲染 Pipeline DAG
  const renderDAG = (pipeline: Pipeline) => {
    const nodePositions: Record<string, { x: number; y: number }> = {};
    pipeline.nodes.forEach((node) => {
      nodePositions[node.node_id] = node.position;
    });

    const nodeTypeColors: Record<string, string> = {
      data: 'blue',
      process: 'green',
      model: 'orange',
      evaluate: 'purple',
      deploy: 'red',
      custom: 'cyan',
    };

    return (
      <div style={{ position: 'relative', height: 400, background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
        {pipeline.edges.map((edge) => {
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
              <line
                x1={sourcePos.x + 80}
                y1={sourcePos.y + 25}
                x2={targetPos.x + 80}
                y2={targetPos.y + 25}
                stroke="#999"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
              />
            </svg>
          );
        })}
        {pipeline.nodes.map((node) => {
          const pos = nodePositions[node.node_id] || { x: 0, y: 0 };
          const color = nodeTypeColors[node.type] || 'gray';
          return (
            <div
              key={node.node_id}
              style={{
                position: 'absolute',
                left: pos.x,
                top: pos.y,
                minWidth: 120,
                background: 'white',
                border: `2px solid ${color}`,
                borderRadius: 8,
                padding: '12px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{node.name}</div>
              <Tag color={color}>{node.type}</Tag>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="Pipeline 编排"
        extra={
          <Space>
            <Button
              icon={<FolderOpenOutlined />}
              onClick={() => setIsTemplateModalOpen(true)}
            >
              模板
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['pipelines'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建 Pipeline
            </Button>
          </Space>
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
            <Option value="active">活跃</Option>
            <Option value="paused">暂停</Option>
            <Option value="draft">草稿</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={pipelinesData?.data?.pipelines || []}
          rowKey="pipeline_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: pipelinesData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* Pipeline 详情抽屉 */}
      <Drawer
        title="Pipeline 详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedPipeline(null);
        }}
        width={1000}
      >
        {selectedPipeline && (
          <Tabs
            defaultActiveKey="dag"
            items={[
              {
                key: 'dag',
                label: 'DAG 视图',
                children: (
                  <div>
                    <Alert
                      message="Pipeline DAG 预览"
                      description="这是 Pipeline 的可视化展示，展示节点之间的依赖关系"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    {renderDAG(selectedPipeline)}

                    <Divider />

                    <div style={{ marginTop: 24, textAlign: 'center' }}>
                      <Space>
                        <Button
                          type="primary"
                          icon={<PlayCircleOutlined />}
                          onClick={() => {
                            setIsDetailDrawerOpen(false);
                            setIsExecutionDrawerOpen(true);
                          }}
                        >
                          执行 Pipeline
                        </Button>
                      </Space>
                    </div>
                  </div>
                ),
              },
              {
                key: 'config',
                label: '配置',
                children: (
                  <Card title="Pipeline 配置" size="small">
                    <Descriptions column={1} bordered size="small">
                      <Descriptions.Item label="Pipeline ID">{selectedPipeline.pipeline_id}</Descriptions.Item>
                      <Descriptions.Item label="名称">{selectedPipeline.name}</Descriptions.Item>
                      <Descriptions.Item label="状态">
                        <Tag color={getStatusColor(selectedPipeline.status)}>{getStatusText(selectedPipeline.status)}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="描述">
                        {selectedPipeline.description || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="调度">
                        {selectedPipeline.schedule ? (
                          <Tag color="blue">
                            {selectedPipeline.schedule.type === 'cron' ? 'Cron' : '事件'}: {selectedPipeline.schedule.expression}
                          </Tag>
                        ) : (
                          '手动执行'
                        )}
                      </Descriptions.Item>
                      <Descriptions.Item label="创建者">{selectedPipeline.created_by}</Descriptions.Item>
                      <Descriptions.Item label="创建时间">
                        {dayjs(selectedPipeline.created_at).format('YYYY-MM-DD HH:mm:ss')}
                      </Descriptions.Item>
                    </Descriptions>

                    {selectedPipeline.variables && Object.keys(selectedPipeline.variables).length > 0 && (
                      <Card title="变量" size="small" style={{ marginTop: 16 }}>
                        <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                          {JSON.stringify(selectedPipeline.variables, null, 2)}
                        </pre>
                      </Card>
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
                        { title: '名称', dataIndex: 'name', key: 'name' },
                        { title: '类型', dataIndex: 'type', key: 'type', render: (type: string) => <Tag>{type}</Tag> },
                        {
                          title: '配置',
                          key: 'config',
                          render: (_: unknown, node: PipelineNode) => {
                            const paramCount = Object.keys(node.config.parameters || {}).length;
                            return (
                              <span style={{ fontSize: 11 }}>
                                {paramCount > 0 ? `${paramCount} 个参数` : '-'}
                              </span>
                            );
                          },
                        },
                      ]}
                      dataSource={selectedPipeline.nodes}
                      rowKey="node_id"
                      pagination={false}
                      size="small"
                    />
                  </Card>
                ),
              },
            ]}
          />
        )}
      </Drawer>

      {/* 执行历史抽屉 */}
      <Drawer
        title="执行历史"
        open={isExecutionDrawerOpen}
        onClose={() => setIsExecutionDrawerOpen(false)}
        width={800}
      >
        {selectedPipeline && (
          <div>
            <Alert
              message={`${selectedPipeline.name} 的执行记录`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table
              columns={[
                {
                  title: '执行 ID',
                  dataIndex: 'execution_id',
                  key: 'execution_id',
                  ellipsis: true,
                  render: (id: string) => <code style={{ fontSize: 11 }}>{id.slice(0, 12)}...</code>,
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  key: 'status',
                  width: 100,
                  render: (status: string) => {
                    const colors: Record<string, string> = {
                      running: 'processing',
                      completed: 'success',
                      failed: 'error',
                      cancelled: 'default',
                    };
                    const texts: Record<string, string> = {
                      running: '运行中',
                      completed: '成功',
                      failed: '失败',
                      cancelled: '已取消',
                    };
                    return (
                      <Tag
                        color={colors[status]}
                        icon={status === 'running' ? <ClockCircleOutlined spin /> : undefined}
                      >
                        {texts[status]}
                      </Tag>
                    );
                  },
                },
                {
                  title: '进度',
                  key: 'progress',
                  render: (_: unknown, record: PipelineExecution) => {
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
                  render: (_: unknown, record: PipelineExecution) =>
                    record.duration_ms ? `${(record.duration_ms / 1000).toFixed(1)}s` : '-',
                },
                {
                  title: '操作',
                  key: 'actions',
                  render: (_: unknown, record: PipelineExecution) => (
                    <Space>
                      {record.status === 'running' && (
                        <Button
                          type="link"
                          size="small"
                          danger
                          onClick={() => stopExecutionMutation.mutate(record.execution_id)}
                        >
                          停止
                        </Button>
                      )}
                      <Button
                        type="link"
                        size="small"
                        onClick={() => {
                          // Show execution details
                        }}
                      >
                        详情
                      </Button>
                    </Space>
                  ),
                },
              ]}
              dataSource={executionsData?.data?.executions || []}
              rowKey="execution_id"
              loading={isLoadingExecutions}
              pagination={false}
            />
          </div>
        )}
      </Drawer>

      {/* 创建 Pipeline 模态框 */}
      <Modal
        title="创建 Pipeline"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setNodes([]);
          setEdges([]);
        }}
        onOk={() => {
          form.validateFields().then((values) => {
            const data: CreatePipelineRequest = {
              name: values.name,
              description: values.description,
              nodes,
              edges,
              schedule: values.schedule_type ? {
                type: values.schedule_type,
                expression: values.cron_expression,
              } : undefined,
            };
            createMutation.mutate(data);
          });
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Pipeline 名称"
            name="name"
            rules={[{ required: true, message: '请输入 Pipeline 名称' }]}
          >
            <Input placeholder="请输入 Pipeline 名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="调度类型" name="schedule_type">
                <Select placeholder="选择调度类型" allowClear>
                  <Option value="cron">Cron 表达式</Option>
                  <Option value="interval">间隔</Option>
                  <Option value="manual">手动</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Cron 表达式" name="cron_expression">
                <Input placeholder="0 0 * * * ?" disabled={form.getFieldValue('schedule_type') !== 'cron'} />
              </Form.Item>
            </Col>
          </Row>
          <Divider>节点管理</Divider>
          <div style={{ marginBottom: 16, textAlign: 'center' }}>
            <Button icon={<PlusOutlined />} onClick={handleAddNode}>
              添加节点
            </Button>
            <span style={{ margin: '0 16px', color: '#999' }}>共 {nodes.length} 个节点</span>
          </div>
          {nodes.map((node, index) => (
            <Card
              key={node.node_id}
              size="small"
              style={{ marginBottom: 8 }}
              extra={
                <Button
                  type="link"
                  size="small"
                  danger
                  onClick={() => {
                    setNodes(nodes.filter((n) => n.node_id !== node.node_id));
                  }}
                >
                  删除
                </Button>
              }
            >
              <Input
                value={node.name}
                onChange={(e) => {
                  const newNodes = [...nodes];
                  newNodes[index].name = e.target.value;
                  setNodes(newNodes);
                }}
                placeholder="节点名称"
                style={{ marginBottom: 8 }}
              />
              <Select
                value={node.type}
                onChange={(value) => {
                  const newNodes = [...nodes];
                  newNodes[index].type = value as PipelineNode['type'];
                  setNodes(newNodes);
                }}
                style={{ width: '100%', marginBottom: 8 }}
              >
                <Option value="data">数据源</Option>
                <Option value="process">处理</Option>
                <Option value="model">模型</Option>
                <Option value="evaluate">评估</Option>
                <Option value="deploy">部署</Option>
              </Select>
            </Card>
          ))}
        </Form>
      </Modal>

      {/* Pipeline 模板模态框 */}
      <Modal
        title="Pipeline 模板"
        open={isTemplateModalOpen}
        onCancel={() => setIsTemplateModalOpen(false)}
        footer={[
          <Button onClick={() => setIsTemplateModalOpen(false)}>关闭</Button>,
        ]}
        width={600}
      >
        <Card title="可用的模板" size="small">
          <Table
            columns={[
              { title: '名称', dataIndex: 'name', key: 'name' },
              { title: '分类', dataIndex: 'category', key: 'category' },
              { title: '节点数', dataIndex: 'nodes', key: 'nodes', render: (_, r: any) => r.nodes.length },
              { title: '描述', dataIndex: 'description', key: 'description', render: (desc?: string) => desc || '-' },
            ]}
            dataSource={templatesData?.data?.templates || []}
            rowKey="template_id"
            pagination={false}
            size="small"
          />
        </Card>
      </Modal>
    </div>
  );
}

export default PipelinesPage;
