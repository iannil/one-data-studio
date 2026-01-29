import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
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
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Progress,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import model from '@/services/model';
import type { TrainingJob, CreateTrainingJobRequest } from '@/services/model';

const { Option } = Select;
const { TextArea } = Input;

function TrainingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);

  const [form] = Form.useForm();

  // 获取训练任务列表
  const { data: jobsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['training-jobs', page, pageSize, statusFilter, projectFilter],
    queryFn: () =>
      model.getTrainingJobs({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        project: projectFilter || undefined,
      }),
  });

  // 创建训练任务
  const createMutation = useMutation({
    mutationFn: model.createTrainingJob,
    onSuccess: () => {
      message.success('训练任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['training-jobs'] });
    },
    onError: () => {
      message.error('训练任务创建失败');
    },
  });

  // 停止训练任务
  const stopMutation = useMutation({
    mutationFn: model.stopTrainingJob,
    onSuccess: () => {
      message.success('训练任务已停止');
      queryClient.invalidateQueries({ queryKey: ['training-jobs'] });
    },
    onError: () => {
      message.error('训练任务停止失败');
    },
  });

  // 删除训练任务
  const deleteMutation = useMutation({
    mutationFn: model.deleteTrainingJob,
    onSuccess: () => {
      message.success('训练任务删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['training-jobs'] });
    },
    onError: () => {
      message.error('训练任务删除失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'blue',
      completed: 'green',
      failed: 'red',
      stopped: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '等待中',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      stopped: '已停止',
    };
    return texts[status] || status;
  };

  const getFrameworkColor = (framework: string) => {
    const colors: Record<string, string> = {
      pytorch: 'orange',
      tensorflow: 'orange',
      sklearn: 'green',
      xgboost: 'red',
    };
    return colors[framework] || 'default';
  };

  const renderProgress = (job: TrainingJob) => {
    if (job.status !== 'running' && job.status !== 'completed') return null;
    if (!job.current_epoch || !job.total_epochs) return null;

    const percent = Math.round((job.current_epoch / job.total_epochs) * 100);
    return <Progress percent={percent} size="small" status={job.status === 'completed' ? 'success' : 'active'} />;
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: TrainingJob) => (
        <a
          onClick={() => {
            setSelectedJob(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '项目',
      dataIndex: 'project',
      key: 'project',
      render: (project: string) => <Tag>{project}</Tag>,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '框架',
      dataIndex: 'framework',
      key: 'framework',
      render: (framework: string) => (
        <Tag color={getFrameworkColor(framework)}>{framework}</Tag>
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
      title: '进度',
      key: 'progress',
      width: 120,
      render: (_: unknown, record: TrainingJob) => renderProgress(record),
    },
    {
      title: '资源',
      key: 'resources',
      render: (_: unknown, record: TrainingJob) => (
        <Space size="small">
          <Tag>CPU: {record.resources.cpu}</Tag>
          <Tag>{record.resources.memory}</Tag>
          {record.resources.gpu && <Tag color="blue">GPU: {record.resources.gpu}</Tag>}
        </Space>
      ),
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
      width: 150,
      render: (_: unknown, record: TrainingJob) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedJob(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          {record.status === 'running' && (
            <Popconfirm
              title="确定要停止这个训练任务吗？"
              onConfirm={() => stopMutation.mutate(record.job_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
          <Popconfirm
            title="确定要删除这个训练任务吗？"
            onConfirm={() => deleteMutation.mutate(record.job_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateTrainingJobRequest = {
        ...values,
        hyperparameters: values.hyperparameters ? JSON.parse(values.hyperparameters) : {},
        resources: {
          cpu: values.cpu || 4,
          memory: values.memory || '8Gi',
          gpu: values.gpu,
          gpu_type: values.gpu_type,
        },
      };
      createMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="训练任务管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            创建训练任务
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
            <Option value="pending">等待中</Option>
            <Option value="running">运行中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
          </Select>
          <Select
            placeholder="项目筛选"
            allowClear
            style={{ width: 150 }}
            onChange={setProjectFilter}
            value={projectFilter || undefined}
          >
            <Option value="image-classification">图像分类</Option>
            <Option value="nlp">自然语言处理</Option>
            <Option value="recommendation">推荐系统</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={jobsData?.data?.jobs || []}
          rowKey="job_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: jobsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建训练任务模态框 */}
      <Modal
        title="创建训练任务"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="任务名称"
                name="name"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="请输入任务名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="项目"
                name="project"
                rules={[{ required: true, message: '请选择项目' }]}
              >
                <Select placeholder="请选择项目">
                  <Option value="image-classification">图像分类</Option>
                  <Option value="nlp">自然语言处理</Option>
                  <Option value="recommendation">推荐系统</Option>
                  <Option value="custom">自定义</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="模型名称"
                name="model_name"
                rules={[{ required: true, message: '请输入模型名称' }]}
              >
                <Input placeholder="例如: resnet50" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="框架"
                name="framework"
                rules={[{ required: true, message: '请选择框架' }]}
              >
                <Select placeholder="请选择框架">
                  <Option value="pytorch">PyTorch</Option>
                  <Option value="tensorflow">TensorFlow</Option>
                  <Option value="sklearn">Scikit-learn</Option>
                  <Option value="xgboost">XGBoost</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="数据集 ID" name="dataset_id">
            <Input placeholder="关联的数据集 ID（可选）" />
          </Form.Item>
          <Form.Item label="超参数 (JSON)" name="hyperparameters">
            <TextArea
              rows={3}
              placeholder='{"learning_rate": 0.001, "batch_size": 32, "epochs": 100}'
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="CPU 核数" name="cpu" initialValue={4}>
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="内存 (Gi)" name="memory" initialValue={8}>
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="GPU 数量" name="gpu">
                <InputNumber min={0} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="GPU 类型" name="gpu_type">
            <Select placeholder="选择 GPU 类型" allowClear>
              <Option value="T4">NVIDIA T4</Option>
              <Option value="V100">NVIDIA V100</Option>
              <Option value="A100">NVIDIA A100</Option>
              <Option value="A10G">NVIDIA A10G</Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="分布式训练" name="distributed" valuePropName="checked">
                <Select placeholder="是否启用分布式">
                  <Option value={false}>否</Option>
                  <Option value={true}>是</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="工作节点数" name="worker_count">
                <InputNumber min={1} max={16} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="输出路径" name="output_uri">
            <Input placeholder="s3://models/output/" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 训练任务详情抽屉 */}
      <Drawer
        title="训练任务详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedJob(null);
        }}
        width={700}
      >
        {selectedJob && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="任务名称" span={2}>
                {selectedJob.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedJob.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedJob.status)}>
                  {getStatusText(selectedJob.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="项目">
                <Tag>{selectedJob.project}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型">
                {selectedJob.model_name}
              </Descriptions.Item>
              <Descriptions.Item label="框架">
                <Tag color={getFrameworkColor(selectedJob.framework)}>{selectedJob.framework}</Tag>
              </Descriptions.Item>
              {selectedJob.current_epoch && selectedJob.total_epochs && (
                <Descriptions.Item label="训练进度" span={2}>
                  <Progress
                    percent={Math.round((selectedJob.current_epoch / selectedJob.total_epochs) * 100)}
                    status={selectedJob.status === 'completed' ? 'success' : 'active'}
                  />
                  <span style={{ marginLeft: 8 }}>
                    {selectedJob.current_epoch} / {selectedJob.total_epochs} epochs
                  </span>
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedJob.metrics && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="实时指标">
                  <Row gutter={16}>
                    {selectedJob.metrics.loss !== undefined && (
                      <Col span={8}>
                        <Statistic title="Loss" value={selectedJob.metrics.loss} precision={6} />
                      </Col>
                    )}
                    {selectedJob.metrics.accuracy !== undefined && (
                      <Col span={8}>
                        <Statistic
                          title="Accuracy"
                          value={selectedJob.metrics.accuracy * 100}
                          precision={2}
                          suffix="%"
                        />
                      </Col>
                    )}
                  </Row>
                </Card>
              </div>
            )}

            <div style={{ marginTop: 16 }}>
              <Card size="small" title="资源配置">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="CPU">{selectedJob.resources.cpu} 核</Descriptions.Item>
                  <Descriptions.Item label="内存">{selectedJob.resources.memory}</Descriptions.Item>
                  {selectedJob.resources.gpu && (
                    <Descriptions.Item label="GPU">
                      {selectedJob.resources.gpu} 卡
                      {selectedJob.resources.gpu_type && ` (${selectedJob.resources.gpu_type})`}
                    </Descriptions.Item>
                  )}
                  {selectedJob.distributed && (
                    <Descriptions.Item label="分布式">
                      {selectedJob.worker_count || 1} 工作节点
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            </div>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => navigate(`/cube/training/${selectedJob.job_id}/logs`)}
                >
                  查看日志
                </Button>
                <Button
                  icon={<ThunderboltOutlined />}
                  onClick={() => navigate(`/cube/training/${selectedJob.job_id}/metrics`)}
                >
                  查看指标
                </Button>
                {selectedJob.status === 'running' && (
                  <Popconfirm
                    title="确定要停止这个训练任务吗？"
                    onConfirm={() => stopMutation.mutate(selectedJob.job_id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button danger icon={<StopOutlined />}>
                      停止
                    </Button>
                  </Popconfirm>
                )}
                <Popconfirm
                  title="确定要删除这个训练任务吗？"
                  onConfirm={() => deleteMutation.mutate(selectedJob.job_id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default TrainingPage;
