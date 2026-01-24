import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Drawer,
  Progress,
  Alert,
  Divider,
  Descriptions,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  DeleteOutlined,
  EditOutlined,
  DownloadOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import cube from '@/services/cube';
import type { LLMFineTuningJob, CreateFineTuningJobRequest, FineTuningDataset } from '@/services/cube';

const { Option } = Select;
const { TextArea } = Input;

function LLMTuningPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<LLMFineTuningJob | null>(null);

  const [form] = Form.useForm();

  // Queries
  const { data: jobsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['llm-tuning-jobs', page, pageSize, statusFilter],
    queryFn: () =>
      cube.getFineTuningJobs({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const { data: datasetsData } = useQuery({
    queryKey: ['finetuning-datasets'],
    queryFn: () => cube.getFineTuningDatasets(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: cube.createFineTuningJob,
    onSuccess: () => {
      message.success('微调任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['llm-tuning-jobs'] });
    },
    onError: () => {
      message.error('微调任务创建失败');
    },
  });

  const startMutation = useMutation({
    mutationFn: cube.startFineTuningJob,
    onSuccess: () => {
      message.success('微调任务已启动');
      queryClient.invalidateQueries({ queryKey: ['llm-tuning-jobs'] });
    },
    onError: () => {
      message.error('启动微调任务失败');
    },
  });

  const stopMutation = useMutation({
    mutationFn: cube.stopFineTuningJob,
    onSuccess: () => {
      message.success('微调任务已停止');
      queryClient.invalidateQueries({ queryKey: ['llm-tuning-jobs'] });
    },
    onError: () => {
      message.error('停止微调任务失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: cube.deleteFineTuningJob,
    onSuccess: () => {
      message.success('微调任务删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['llm-tuning-jobs'] });
    },
    onError: () => {
      message.error('微调任务删除失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      cancelled: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '待运行',
      running: '训练中',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: LLMFineTuningJob) => (
        <a onClick={() => { setSelectedJob(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '基础模型',
      dataIndex: 'base_model',
      key: 'base_model',
      render: (model: string) => <Tag color="blue">{model}</Tag>,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      render: (method: string) => {
        const colors: Record<string, string> = {
          full: 'red',
          lora: 'green',
          qlora: 'orange',
          p_tuning: 'purple',
        };
        return <Tag color={colors[method] || 'default'}>{method.toUpperCase()}</Tag>;
      },
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
      render: (_: unknown, record: LLMFineTuningJob) => {
        let percent = 0;
        if (record.status === 'completed') percent = 100;
        else if (record.status === 'running') percent = 50;
        return (
          <Progress
            percent={percent}
            size="small"
            status={record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'}
          />
        );
      },
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
      render: (_: unknown, record: LLMFineTuningJob) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.job_id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => stopMutation.mutate(record.job_id)}
            >
              停止
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => {/* 导出模型 */}}
            >
              导出
            </Button>
          )}
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => { setSelectedJob(record); setIsDetailDrawerOpen(true); }}
          />
        </Space>
      ),
    },
  ];

  const methods = [
    { value: 'lora', label: 'LoRA - 低秩适配' },
    { value: 'qlora', label: 'QLoRA - 量化 LoRA' },
    { value: 'full', label: '全量微调' },
    { value: 'p_tuning', label: 'P-Tuning' },
  ];

  const baseModels = [
    { value: 'llama-2-7b', label: 'LLaMA 2 7B' },
    { value: 'llama-2-13b', label: 'LLaMA 2 13B' },
    { value: 'llama-2-70b', label: 'LLaMA 2 70B' },
    { value: 'baichuan-7b', label: 'Baichuan 7B' },
    { value: 'baichuan-13b', label: 'Baichuan 13B' },
    { value: 'chatglm-6b', label: 'ChatGLM 6B' },
    { value: 'qwen-7b', label: 'Qwen 7B' },
    { value: 'qwen-14b', label: 'Qwen 14B' },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const loraConfig = values.method === 'lora' || values.method === 'qlora'
        ? {
            lora_config: {
              r: values.lora_r,
              lora_alpha: values.lora_alpha,
              target_modules: ['q_proj', 'v_proj'],
              lora_dropout: values.lora_dropout,
            },
          }
        : {};

      const data: CreateFineTuningJobRequest = {
        name: values.job_name,
        base_model: values.base_model,
        method: values.method,
        dataset_id: values.dataset_id,
        config: {
          learning_rate: values.learning_rate,
          batch_size: values.batch_size,
          num_epochs: values.num_epochs,
          ...loraConfig,
        },
        resources: {
          gpu_type: 'A100',
          gpu_count: 1,
          cpu: '4',
          memory: '16Gi',
        },
      };
      createMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="LLM 微调"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['llm-tuning-jobs'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建微调任务
            </Button>
          </Space>
        }
      >
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Statistic title="总任务数" value={jobsData?.data?.total || 0} />
          </Col>
          <Col span={6}>
            <Statistic
              title="运行中"
              value={jobsData?.data?.jobs?.filter((j) => j.status === 'running').length || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已完成"
              value={jobsData?.data?.jobs?.filter((j) => j.status === 'completed').length || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="失败"
              value={jobsData?.data?.jobs?.filter((j) => j.status === 'failed').length || 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="pending">待运行</Option>
            <Option value="running">训练中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
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

      {/* 创建微调任务模态框 */}
      <Modal
        title="新建微调任务"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="任务名称"
            name="job_name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>

          <Divider orientation="left">模型配置</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="基础模型"
                name="base_model"
                rules={[{ required: true, message: '请选择基础模型' }]}
              >
                <Select placeholder="选择基础模型">
                  {baseModels.map((model) => (
                    <Option key={model.value} value={model.value}>
                      {model.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="微调方法"
                name="method"
                rules={[{ required: true, message: '请选择微调方法' }]}
                initialValue="lora"
              >
                <Select placeholder="选择微调方法">
                  {methods.map((m) => (
                    <Option key={m.value} value={m.value}>
                      {m.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="训练数据集"
            name="dataset_id"
            rules={[{ required: true, message: '请选择训练数据集' }]}
          >
            <Select placeholder="选择数据集">
              {datasetsData?.data?.datasets?.map((dataset: FineTuningDataset) => (
                <Option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.name} ({dataset.total_samples} 条)
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Divider orientation="left">超参数配置</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="学习率"
                name="learning_rate"
                initialValue={0.0002}
              >
                <InputNumber
                  min={0.00001}
                  max={0.01}
                  step={0.00001}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="批次大小"
                name="batch_size"
                initialValue={4}
              >
                <InputNumber min={1} max={128} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="训练轮数"
                name="num_epochs"
                initialValue={3}
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="LoRA 秩"
                name="lora_r"
                initialValue={8}
              >
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="LoRA Alpha"
                name="lora_alpha"
                initialValue={32}
              >
                <InputNumber min={1} max={512} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="LoRA Dropout"
                name="lora_dropout"
                initialValue={0.1}
              >
                <InputNumber min={0} max={0.5} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Alert
            message="提示"
            description="微调任务将占用 GPU 资源，请确保集群有足够的资源。LoRA 微调相比全量微调需要更少的资源。"
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 任务详情抽屉 */}
      <Drawer
        title="微调任务详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedJob(null);
        }}
        width={800}
      >
        {selectedJob && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="任务ID" span={2}>
                {selectedJob.job_id}
              </Descriptions.Item>
              <Descriptions.Item label="任务名称" span={2}>
                {selectedJob.name}
              </Descriptions.Item>
              <Descriptions.Item label="基础模型">
                <Tag color="blue">{selectedJob.base_model}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="微调方法">
                <Tag>{selectedJob.method.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedJob.status)}>{getStatusText(selectedJob.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedJob.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedJob.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedJob.started_at && (
                <Descriptions.Item label="开始时间" span={2}>
                  {dayjs(selectedJob.started_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              {selectedJob.completed_at && (
                <Descriptions.Item label="完成时间" span={2}>
                  {dayjs(selectedJob.completed_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedJob.status === 'running' && (
              <Card title="训练进度" size="small" style={{ marginTop: 16 }}>
                <Progress percent={50} status="active" />
                <p style={{ marginTop: 8, textAlign: 'center', color: '#666' }}>
                  训练进行中...
                </p>
              </Card>
            )}

            {selectedJob.config && (
              <Card title="超参数配置" size="small" style={{ marginTop: 16 }}>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(selectedJob.config, null, 2)}
                </pre>
              </Card>
            )}

            {selectedJob.status === 'completed' && selectedJob.output_path && (
              <Card title="模型输出" size="small" style={{ marginTop: 16 }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="输出模型路径">
                    {selectedJob.output_path}
                  </Descriptions.Item>
                </Descriptions>
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  style={{ marginTop: 16 }}
                  onClick={() => {/* 部署模型 */}}
                >
                  部署为服务
                </Button>
              </Card>
            )}

            {selectedJob.error && (
              <Alert
                message="错误信息"
                description={selectedJob.error}
                type="error"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default LLMTuningPage;
