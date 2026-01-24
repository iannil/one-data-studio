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
  Upload,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  UploadOutlined,
  DownloadOutlined,
  RocketOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import bisheng from '@/services/bisheng';
import type { SFTTask, CreateSFTTaskRequest, SFTDataset } from '@/services/bisheng';

const { Option } = Select;
const { TextArea } = Input;
const { Dragger } = Upload;

function SFTPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDatasetModalOpen, setIsDatasetModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<SFTTask | null>(null);

  const [form] = Form.useForm();
  const [datasetForm] = Form.useForm();

  // Queries
  const { data: tasksData, isLoading: isLoadingList } = useQuery({
    queryKey: ['sft-tasks', page, pageSize, statusFilter],
    queryFn: () =>
      bisheng.getSFTTasks({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  const { data: datasetsData } = useQuery({
    queryKey: ['sft-datasets'],
    queryFn: () => bisheng.getSFTDatasets(),
  });

  // Mutations
  const createTaskMutation = useMutation({
    mutationFn: bisheng.createSFTTask,
    onSuccess: () => {
      message.success('SFT 任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['sft-tasks'] });
    },
    onError: () => {
      message.error('SFT 任务创建失败');
    },
  });

  const startMutation = useMutation({
    mutationFn: bisheng.startSFTTask,
    onSuccess: () => {
      message.success('SFT 任务已启动');
      queryClient.invalidateQueries({ queryKey: ['sft-tasks'] });
    },
    onError: () => {
      message.error('启动 SFT 任务失败');
    },
  });

  const stopMutation = useMutation({
    mutationFn: bisheng.stopSFTTask,
    onSuccess: () => {
      message.success('SFT 任务已停止');
      queryClient.invalidateQueries({ queryKey: ['sft-tasks'] });
    },
    onError: () => {
      message.error('停止 SFT 任务失败');
    },
  });

  const createDatasetMutation = useMutation({
    mutationFn: bisheng.createSFTTask,
    onSuccess: () => {
      message.success('SFT 任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['sft-tasks'] });
    },
    onError: () => {
      message.error('SFT 任务创建失败');
    },
  });

  const exportMutation = useMutation({
    mutationFn: ({ taskId, format }: { taskId: string; format: 'pytorch' | 'safetensors' | 'gguf' }) =>
      bisheng.exportSFTModel(taskId, format),
    onSuccess: () => {
      message.success('模型导出成功');
    },
    onError: () => {
      message.error('模型导出失败');
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
      render: (name: string, record: SFTTask) => (
        <a onClick={() => { setSelectedTask(record); setIsDetailDrawerOpen(true); }}>
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
      title: '训练方法',
      dataIndex: 'method',
      key: 'method',
      render: (method: string) => <Tag>{method}</Tag>,
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
      render: (_: unknown, record: SFTTask) => {
        // 根据状态显示进度
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
      render: (_: unknown, record: SFTTask) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.task_id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => stopMutation.mutate(record.task_id)}
            >
              停止
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => exportMutation.mutate({ taskId: record.task_id, format: 'safetensors' })}
            >
              导出
            </Button>
          )}
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => { setSelectedTask(record); setIsDetailDrawerOpen(true); }}
          />
        </Space>
      ),
    },
  ];

  const baseModels = [
    { value: 'llama-2-7b-chat', label: 'LLaMA 2 7B Chat' },
    { value: 'llama-2-13b-chat', label: 'LLaMA 2 13B Chat' },
    { value: 'chatglm3-6b', label: 'ChatGLM3 6B' },
    { value: 'baichuan2-7b-chat', label: 'Baichuan2 7B Chat' },
    { value: 'qwen-14b-chat', label: 'Qwen 14B Chat' },
    { value: 'yi-34b-chat', label: 'Yi 34B Chat' },
  ];

  const trainingMethods = [
    { value: 'sft', label: '全量微调' },
    { value: 'lora', label: 'LoRA' },
    { value: 'qlora', label: 'QLoRA' },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateSFTTaskRequest = {
        name: values.name,
        base_model: values.base_model,
        method: values.method,
        dataset_id: values.dataset_id,
        config: {
          learning_rate: values.learning_rate,
          batch_size: values.batch_size,
          num_epochs: values.num_epochs,
          lora_r: values.lora_r,
          lora_alpha: values.lora_alpha,
          max_steps: values.max_steps,
        },
        resources: {
          gpu_type: values.gpu_type || 'A100',
          gpu_count: values.gpu_count || 1,
          cpu: values.cpu || '4',
          memory: values.memory || '16Gi',
        },
      };
      createTaskMutation.mutate(data);
    });
  };

  const handleCreateDataset = () => {
    datasetForm.validateFields().then((_values) => {
      // Dataset creation is handled via file upload
      message.info('数据集上传功能即将推出');
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="SFT 监督微调"
        extra={
          <Space>
            <Button icon={<UploadOutlined />} onClick={() => setIsDatasetModalOpen(true)}>
              上传数据集
            </Button>
            <Button icon={<SyncOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['sft-tasks'] })}>
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
            <Statistic title="总任务数" value={tasksData?.data?.total || 0} />
          </Col>
          <Col span={6}>
            <Statistic
              title="运行中"
              value={tasksData?.data?.tasks?.filter((t) => t.status === 'running').length || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已完成"
              value={tasksData?.data?.tasks?.filter((t) => t.status === 'completed').length || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="可用数据集"
              value={datasetsData?.data?.datasets?.length || 0}
              valueStyle={{ color: '#722ed1' }}
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

      {/* 创建微调任务模态框 */}
      <Modal
        title="新建 SFT 微调任务"
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
                label="训练方法"
                name="method"
                rules={[{ required: true, message: '请选择训练方法' }]}
                initialValue="lora"
              >
                <Select placeholder="选择训练方法">
                  {trainingMethods.map((m) => (
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
              {datasetsData?.data?.datasets?.map((dataset: SFTDataset) => (
                <Option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.name} ({dataset.sample_count} 条)
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
                label="最大长度"
                name="max_length"
                initialValue={512}
              >
                <InputNumber min={128} max={4096} step={128} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Alert
            message="提示"
            description="SFT 微调需要带标注的对话数据，格式为 JSONL。每条数据包含 instruction、input、output 字段。"
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 上传数据集模态框 */}
      <Modal
        title="创建训练数据集"
        open={isDatasetModalOpen}
        onCancel={() => {
          setIsDatasetModalOpen(false);
          datasetForm.resetFields();
        }}
        onOk={handleCreateDataset}
        confirmLoading={createDatasetMutation.isPending}
        width={600}
      >
        <Form form={datasetForm} layout="vertical">
          <Form.Item
            label="数据集名称"
            name="name"
            rules={[{ required: true, message: '请输入数据集名称' }]}
          >
            <Input placeholder="请输入数据集名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>

          <Alert
            message="数据格式要求"
            description={
              <div>
                <p>支持 JSONL 格式，每行一条数据：</p>
                <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                  {JSON.stringify({ instruction: "问题", input: "", output: "答案" }, null, 2)}
                </pre>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="数据文件"
            name="file_path"
            rules={[{ required: true, message: '请上传数据文件' }]}
          >
            <Dragger
              accept=".jsonl,.json"
              customRequest={({ onSuccess }) => {
                setTimeout(() => {
                  onSuccess?.('ok');
                }, 1000);
              }}
              onChange={(info) => {
                if (info.file.status === 'done') {
                  form.setFieldValue('file_path', '/path/to/' + info.file.name);
                }
              }}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">支持 .jsonl 或 .json 格式</p>
            </Dragger>
          </Form.Item>
        </Form>
      </Modal>

      {/* 任务详情抽屉 */}
      <Drawer
        title="SFT 任务详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedTask(null);
        }}
        width={800}
      >
        {selectedTask && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="任务ID" span={2}>
                {selectedTask.task_id}
              </Descriptions.Item>
              <Descriptions.Item label="任务名称" span={2}>
                {selectedTask.name}
              </Descriptions.Item>
              <Descriptions.Item label="基础模型">
                <Tag color="blue">{selectedTask.base_model}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="训练方法">
                <Tag>{selectedTask.method}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedTask.status)}>{getStatusText(selectedTask.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedTask.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedTask.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedTask.started_at && (
                <Descriptions.Item label="开始时间" span={2}>
                  {dayjs(selectedTask.started_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              {selectedTask.completed_at && (
                <Descriptions.Item label="完成时间" span={2}>
                  {dayjs(selectedTask.completed_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedTask.status === 'running' && (
              <Card title="训练进度" size="small" style={{ marginTop: 16 }}>
                <Progress
                  percent={50}
                  status="active"
                />
                <p style={{ marginTop: 8, textAlign: 'center', color: '#666' }}>
                  训练进行中...
                </p>
              </Card>
            )}

            {selectedTask.config && (
              <Card title="训练配置" size="small" style={{ marginTop: 16 }}>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(selectedTask.config, null, 2)}
                </pre>
              </Card>
            )}

            {selectedTask.status === 'completed' && selectedTask.output_model_path && (
              <Card title="微调后模型" size="small" style={{ marginTop: 16 }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="模型路径">
                    {selectedTask.output_model_path}
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
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default SFTPage;
