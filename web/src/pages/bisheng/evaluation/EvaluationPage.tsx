import { useState } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Drawer,
  Tabs,
  Row,
  Col,
  Card,
  Alert,
  Descriptions,
  Divider,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  BarChartOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import bisheng from '@/services/bisheng';
import type {
  EvaluationTask,
  CreateEvaluationTaskRequest,
  EvaluationResult,
  ComparisonReport,
} from '@/services/bisheng';

const { Option } = Select;
const { TextArea } = Input;

function EvaluationPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isResultDrawerOpen, setIsResultDrawerOpen] = useState(false);
  const [isDatasetModalOpen, setIsDatasetModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<EvaluationTask | null>(null);
  const [selectedResults, setSelectedResults] = useState<EvaluationResult[]>([]);
  const [comparisonReport, setComparisonReport] = useState<ComparisonReport | null>(null);

  const [form] = Form.useForm();

  // Queries
  const { data: tasksData, isLoading: isLoadingList } = useQuery({
    queryKey: ['evaluation-tasks', page, pageSize, statusFilter],
    queryFn: () =>
      bisheng.getEvaluationTasks({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const { data: datasetsData } = useQuery({
    queryKey: ['evaluation-datasets'],
    queryFn: () => bisheng.getEvaluationDatasets(),
  });

  // Mutations
  const createTaskMutation = useMutation({
    mutationFn: bisheng.createEvaluationTask,
    onSuccess: () => {
      message.success('评估任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['evaluation-tasks'] });
    },
    onError: () => {
      message.error('评估任务创建失败');
    },
  });

  const startTaskMutation = useMutation({
    mutationFn: bisheng.startEvaluationTask,
    onSuccess: () => {
      message.success('评估任务已启动');
      queryClient.invalidateQueries({ queryKey: ['evaluation-tasks'] });
    },
    onError: () => {
      message.error('启动评估任务失败');
    },
  });

  const stopTaskMutation = useMutation({
    mutationFn: bisheng.stopEvaluationTask,
    onSuccess: () => {
      message.success('评估任务已停止');
      queryClient.invalidateQueries({ queryKey: ['evaluation-tasks'] });
    },
    onError: () => {
      message.error('停止评估任务失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '待运行',
      running: '评估中',
      completed: '已完成',
      failed: '失败',
    };
    return texts[status] || status;
  };

  const getMetricColor = (metric: string) => {
    const colors: Record<string, string> = {
      accuracy: 'blue',
      f1: 'green',
      precision: 'orange',
      recall: 'purple',
      bleu: 'cyan',
      rouge: 'red',
      cosine_similarity: 'geekblue',
      response_time: 'gold',
    };
    return colors[metric] || 'default';
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: EvaluationTask) => (
        <a onClick={() => { setSelectedTask(record); setIsResultDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '模型数量',
      key: 'models',
      render: (_: unknown, record: EvaluationTask) => record.model_configs.length,
    },
    {
      title: '评估指标',
      key: 'metrics',
      render: (_: unknown, record: EvaluationTask) => (
        <Space wrap>
          {record.metrics.map((m) => (
            <Tag key={m} color={getMetricColor(m)}>{m}</Tag>
          ))}
        </Space>
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
      width: 180,
      render: (_: unknown, record: EvaluationTask) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => startTaskMutation.mutate(record.task_id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              danger
              icon={<CloseOutlined />}
              onClick={() => stopTaskMutation.mutate(record.task_id)}
            >
              停止
            </Button>
          )}
          {(record.status === 'completed' || record.status === 'failed') && (
            <Button
              icon={<BarChartOutlined />}
              onClick={() => {
                setSelectedTask(record);
                bisheng.getEvaluationResults(record.task_id).then((res) => {
                  setSelectedResults(res.data.results);
                });
              }}
            >
              查看结果
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const availableMetrics = [
    { value: 'accuracy', label: '准确率 (Accuracy)' },
    { value: 'f1', label: 'F1 Score' },
    { value: 'precision', label: '精确率 (Precision)' },
    { value: 'recall', label: '召回率 (Recall)' },
    { value: 'bleu', label: 'BLEU' },
    { value: 'rouge', label: 'ROUGE' },
    { value: 'cosine_similarity', label: '余弦相似度' },
    { value: 'response_time', label: '响应时间' },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateEvaluationTaskRequest = {
        name: values.name,
        description: values.description,
        model_configs: values.models,
        dataset_id: values.dataset_id,
        metrics: values.metrics,
      };
      createTaskMutation.mutate(data);
    });
  };

  const renderResultsTable = (results: EvaluationResult[]) => {
    const columns = [
      {
        title: '模型名称',
        dataIndex: 'model_name',
        key: 'model_name',
        render: (name: string) => <Tag color="blue">{name}</Tag>,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => (
          <Tag
            color={status === 'completed' ? 'success' : 'error'}
            >
            {status === 'completed' ? '成功' : '失败'}
          </Tag>
        ),
      },
      {
        title: '评估样本数',
        dataIndex: 'samples_evaluated',
        key: 'samples_evaluated',
        render: (num: number) => num.toLocaleString(),
      },
      ];
      if (selectedTask) {
        columns.splice(3, 0, {
          title: '平均响应时间',
          dataIndex: 'avg_response_time_ms',
          key: 'avg_response_time_ms',
          render: (ms?: number) => ms ? `${ms.toFixed(2)}ms` : '-',
        });
      }

      // 添加指标列
      if (selectedTask) {
        const metricKeys = selectedTask.metrics;
        metricKeys.forEach((metric) => {
          columns.push({
            title: metric.toUpperCase(),
            dataIndex: 'metrics',
            key: metric,
            render: (val: any) => val?.[metric]?.toFixed(4) || '-',
          });
        });
      }

      return (
        <Table
          columns={columns}
          dataSource={results}
          rowKey="result_id"
          pagination={false}
          size="small"
        />
      );
    };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="模型评估"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建评估任务
          </Button>
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
            <Option value="pending">待运行</Option>
            <Option value="running">评估中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={tasksData?.data?.tasks || []}
          rowKey="task_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: tasksData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建评估任务模态框 */}
      <Modal
        title="新建评估任务"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        confirmLoading={createTaskMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>

          <Divider orientation="left">模型配置</Divider>

          <Form.List
            name="models"
            initialValue={[{ model_name: '', endpoint: '', api_key: '' }]}
          >
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card
                    key={field.key}
                    size="small"
                    style={{ marginBottom: 8 }}
                    extra={
                      <Button
                        type="text"
                        danger
                        icon={<CloseOutlined />}
                        onClick={() => remove(field.name)}
                      >
                        移除
                      </Button>
                    }
                  >
                    <Row gutter={8}>
                      <Col span={12}>
                        <Form.Item
                          label="模型名称"
                          name={[field.name, 'model_name']}
                          rules={[{ required: true, message: '请输入模型名称' }]}
                        >
                          <Input placeholder="模型显示名称" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          label="端点"
                          name={[field.name, 'endpoint']}
                          rules={[{ required: true, message: '请输入端点' }]}
                        >
                          <Input placeholder="http://localhost:8000" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={8}>
                      <Col span={24}>
                        <Form.Item label="API Key (可选)" name={[field.name, 'api_key']}>
                          <Input.Password placeholder="sk-..." />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add()}>
                  添加模型
                </Button>
              </>
            )}
          </Form.List>

          <Divider orientation="left">数据集与指标</Divider>

          <Form.Item
            label="评估数据集"
            name="dataset_id"
            rules={[{ required: true, message: '请选择评估数据集' }]}
          >
            <Select placeholder="选择数据集">
              {datasetsData?.data?.datasets?.map((dataset) => (
                <Option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.name} ({dataset.sample_count} 条)
                </Option>
              ))}
            </Select>
            <Button
              type="link"
              onClick={() => {
                setIsCreateModalOpen(false);
                setIsDatasetModalOpen(true);
              }}
            >
              创建数据集
            </Button>
          </Form.Item>

          <Form.Item
            label="评估指标"
            name="metrics"
            rules={[{ required: true, message: '请选择评估指标' }]}
          >
            <Select mode="multiple" placeholder="选择评估指标">
              {availableMetrics.map((m) => (
                <Option key={m.value} value={m.value}>
                  {m.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 评估结果抽屉 */}
      <Drawer
        title="评估结果"
        open={isResultDrawerOpen}
        onClose={() => {
          setIsResultDrawerOpen(false);
          setSelectedTask(null);
          setSelectedResults([]);
          setComparisonReport(null);
        }}
        width={900}
      >
        {selectedTask && (
          <div>
            <Alert
              message={selectedTask.name}
              type={selectedTask.status === 'failed' ? 'error' : selectedTask.status === 'completed' ? 'success' : 'info'}
              description={
                selectedTask.status === 'running'
                  ? '评估任务正在运行中'
                  : selectedTask.status === 'completed'
                  ? '评估任务已完成，点击查看结果'
                  : selectedTask.status === 'failed'
                  ? '评估任务失败'
                  : ''
              }
              showIcon
              style={{ marginBottom: 16 }}
            />

            {selectedTask.status === 'completed' && (
              <div>
                <Tabs
                  defaultActiveKey="table"
                  items={[
                    {
                      key: 'table',
                      label: '结果表格',
                      children: (
                        <div>
                          {selectedResults.length > 0 ? (
                            renderResultsTable(selectedResults)
                          ) : (
                            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                              暂无结果数据，请启动评估任务或稍后查看
                            </div>
                          )}
                        </div>
                      ),
                    },
                    {
                      key: 'compare',
                      label: '模型对比',
                      children: (
                        <div>
                          {comparisonReport ? (
                            <>
                              <Card title="对比分析" size="small">
                                <Descriptions column={1} bordered size="small">
                                  <Descriptions.Item label="胜出模型">
                                    <Tag color="green" style={{ fontSize: 16 }}>
                                      {comparisonReport.winner}
                                    </Tag>
                                  </Descriptions.Item>
                                  {Object.entries(comparisonReport.comparison).map(([metric, info]) => (
                                    <Descriptions.Item label={metric.toUpperCase()} key={metric}>
                                      {info.best_model} 优于其他模型 {info.difference?.toFixed(4)} 个百分点
                                    </Descriptions.Item>
                                  ))}
                                </Descriptions>
                              </Card>

                              <Card title="详细指标对比" size="small" style={{ marginTop: 16 }}>
                                <Table
                                  columns={[
                                    { title: '指标', dataIndex: 'metric', key: 'metric' },
                                    ...comparisonReport.models.map((model) => ({
                                      title: model.model_name,
                                      dataIndex: ['metrics', model.model_name] as any,
                                      render: (val: number) => val?.toFixed(4) || '-',
                                    })),
                                  ]}
                                  dataSource={Object.keys(comparisonReport.comparison).map((metric) => ({
                                    key: metric,
                                    metric: metric.toUpperCase(),
                                  }))}
                                  rowKey="metric"
                                  pagination={false}
                                  size="small"
                                />
                              </Card>
                            </>
                          ) : (
                            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                              暂无对比数据，请重新生成报告
                            </div>
                          )}
                        </div>
                      ),
                    },
                  ]}
                />
              </div>
            )}
          </div>
        )}
      </Drawer>

      {/* 上传数据集模态框 */}
      <Modal
        title="创建评估数据集"
        open={isDatasetModalOpen}
        onCancel={() => setIsDatasetModalOpen(false)}
        footer={null}
        width={600}
      >
        <Alert
          message="数据集格式"
          description="支持 JSONL 格式的问答对数据，每行包含 question、answer 字段"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Alert
          message="示例数据"
          description={
            <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 8, borderRadius: 4, overflow: 'auto' }}>
              {JSON.stringify([
                { "question": "什么是机器学习?", "answer": "机器学习是..." },
                { "question": "深度学习和机器学习的区别?", "answer": "区别在于..." },
              ], null, 2)}
            </pre>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <p style={{ color: '#666', marginBottom: 16 }}>
          要创建评估数据集，请先上传 JSONL 格式文件。
        </p>
        <Button
          type="primary"
          block
          icon={<UploadOutlined />}
          onClick={() => {
            setIsDatasetModalOpen(false);
            setIsCreateModalOpen(true);
          }}
        >
          在创建任务中上传
        </Button>
      </Modal>
    </div>
  );
}

export default EvaluationPage;
