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
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  RocketOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import model from '@/services/model';
import type { RegisteredModel, RegisterModelRequest } from '@/services/model';

const { Option } = Select;
const { TextArea } = Input;

function ModelsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [frameworkFilter, setFrameworkFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<RegisteredModel | null>(null);

  const [form] = Form.useForm();

  // 获取注册模型列表
  const { data: modelsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['registered-models', page, pageSize, frameworkFilter, statusFilter],
    queryFn: () =>
      model.getRegisteredModels({
        page,
        page_size: pageSize,
        framework: frameworkFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  // 注册模型
  const registerMutation = useMutation({
    mutationFn: model.registerModel,
    onSuccess: () => {
      message.success('模型注册成功');
      setIsRegisterModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['registered-models'] });
    },
    onError: () => {
      message.error('模型注册失败');
    },
  });

  // 删除模型
  const deleteMutation = useMutation({
    mutationFn: model.deleteRegisteredModel,
    onSuccess: () => {
      message.success('模型删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['registered-models'] });
    },
    onError: () => {
      message.error('模型删除失败');
    },
  });

  // 设置模型阶段
  const setStageMutation = useMutation({
    mutationFn: ({ modelId, version, stage }: { modelId: string; version: string; stage: string }) =>
      model.setModelStage(modelId, version, stage),
    onSuccess: () => {
      message.success('模型状态更新成功');
      queryClient.invalidateQueries({ queryKey: ['registered-models'] });
    },
    onError: () => {
      message.error('模型状态更新失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      production: 'green',
      staging: 'blue',
      archived: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      production: '生产',
      staging: '预发布',
      archived: '已归档',
    };
    return texts[status] || status;
  };

  const getFrameworkColor = (framework: string) => {
    const colors: Record<string, string> = {
      pytorch: 'orange',
      tensorflow: 'orange',
      sklearn: 'green',
      xgboost: 'red',
      onnx: 'blue',
    };
    return colors[framework] || 'default';
  };

  const renderMetrics = (metrics?: Record<string, number>) => {
    if (!metrics || Object.keys(metrics).length === 0) return '-';
    return (
      <Space size="small" wrap>
        {Object.entries(metrics).slice(0, 2).map(([key, value]) => (
          <Tag key={key}>
            {key}: {typeof value === 'number' ? value.toFixed(4) : value}
          </Tag>
        ))}
        {Object.keys(metrics).length > 2 && <Tag>+{Object.keys(metrics).length - 2}</Tag>}
      </Space>
    );
  };

  const columns = [
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: RegisteredModel) => (
        <a
          onClick={() => {
            setSelectedModel(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag>v{version}</Tag>,
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
      title: '指标',
      key: 'metrics',
      render: (_: unknown, record: RegisteredModel) => renderMetrics(record.metrics),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <>
          {tags?.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
          {tags?.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
      ),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 120,
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
      render: (_: unknown, record: RegisteredModel) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedModel(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个模型吗？"
            onConfirm={() => deleteMutation.mutate(record.model_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleRegister = () => {
    form.validateFields().then((values) => {
      const data: RegisterModelRequest = {
        ...values,
        metrics: values.metrics ? JSON.parse(values.metrics) : undefined,
        parameters: values.parameters ? JSON.parse(values.parameters) : undefined,
      };
      registerMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="模型管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsRegisterModalOpen(true)}>
            注册模型
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="框架筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setFrameworkFilter}
            value={frameworkFilter || undefined}
          >
            <Option value="pytorch">PyTorch</Option>
            <Option value="tensorflow">TensorFlow</Option>
            <Option value="sklearn">Scikit-learn</Option>
            <Option value="xgboost">XGBoost</Option>
            <Option value="onnx">ONNX</Option>
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="production">生产</Option>
            <Option value="staging">预发布</Option>
            <Option value="archived">已归档</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={modelsData?.data?.models || []}
          rowKey="model_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: modelsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 注册模型模态框 */}
      <Modal
        title="注册模型"
        open={isRegisterModalOpen}
        onOk={handleRegister}
        onCancel={() => {
          setIsRegisterModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={registerMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="模型名称"
            name="name"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="例如: image-classifier" />
          </Form.Item>
          <Form.Item
            label="版本"
            name="version"
            rules={[{ required: true, message: '请输入版本号' }]}
            initialValue="1.0.0"
          >
            <Input placeholder="例如: 1.0.0" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
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
              <Option value="onnx">ONNX</Option>
              <Option value="other">其他</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="模型路径 (URI)"
            name="uri"
            rules={[{ required: true, message: '请输入模型路径' }]}
          >
            <Input placeholder="s3://models/path 或 /path/to/model" />
          </Form.Item>
          <Form.Item label="实验 ID" name="experiment_id">
            <Input placeholder="关联的实验 ID（可选）" />
          </Form.Item>
          <Form.Item label="指标 (JSON)" name="metrics">
            <TextArea rows={2} placeholder='{"accuracy": 0.95, "f1": 0.93}' />
          </Form.Item>
          <Form.Item label="参数 (JSON)" name="parameters">
            <TextArea rows={2} placeholder='{"learning_rate": 0.001, "epochs": 100}' />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 模型详情抽屉 */}
      <Drawer
        title="模型详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedModel(null);
        }}
        width={700}
      >
        {selectedModel && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="模型名称" span={2}>
                {selectedModel.name}
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                <Tag>v{selectedModel.version}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedModel.status)}>
                  {getStatusText(selectedModel.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="框架">
                <Tag color={getFrameworkColor(selectedModel.framework)}>{selectedModel.framework}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedModel.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="模型路径 (URI)" span={2}>
                {selectedModel.uri}
              </Descriptions.Item>
              {selectedModel.experiment_id && (
                <Descriptions.Item label="实验 ID" span={2}>
                  <Tag>{selectedModel.experiment_id}</Tag>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedModel.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedModel.updated_at && (
                <Descriptions.Item label="更新时间" span={2}>
                  {dayjs(selectedModel.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="标签" span={2}>
                {selectedModel.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {selectedModel.description && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="描述">
                  {selectedModel.description}
                </Card>
              </div>
            )}

            {selectedModel.metrics && Object.keys(selectedModel.metrics).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title={<><TagsOutlined /> 指标</>}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {Object.entries(selectedModel.metrics).map(([key, value]) => (
                      <div key={key} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{key}</span>
                        <span style={{ fontWeight: 'bold' }}>
                          {typeof value === 'number' ? value.toFixed(6) : value}
                        </span>
                      </div>
                    ))}
                  </Space>
                </Card>
              </div>
            )}

            {selectedModel.parameters && Object.keys(selectedModel.parameters).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="超参数">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {Object.entries(selectedModel.parameters).map(([key, value]) => (
                      <div key={key} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{key}</span>
                        <span style={{ fontWeight: 'bold' }}>{String(value)}</span>
                      </div>
                    ))}
                  </Space>
                </Card>
              </div>
            )}

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<RocketOutlined />}
                  onClick={() => navigate(`/model/serving/create?modelId=${selectedModel.model_id}`)}
                >
                  部署服务
                </Button>
                <Select
                  placeholder="设置状态"
                  style={{ width: 120 }}
                  onChange={(stage) => setStageMutation.mutate({
                    modelId: selectedModel.model_id,
                    version: selectedModel.version,
                    stage,
                  })}
                  value={selectedModel.status}
                  loading={setStageMutation.isPending}
                >
                  <Option value="production">生产</Option>
                  <Option value="staging">预发布</Option>
                  <Option value="archived">归档</Option>
                </Select>
                <Popconfirm
                  title="确定要删除这个模型吗？"
                  onConfirm={() => deleteMutation.mutate(selectedModel.model_id)}
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

export default ModelsPage;
