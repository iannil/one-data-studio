import { useState } from 'react';
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
  Descriptions,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  LaptopOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import model from '@/services/model';
import type { Notebook, NotebookImage } from '@/services/model';

const { Option } = Select;
const { TextArea } = Input;

function NotebooksPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(null);

  const [form] = Form.useForm();

  // 获取 Notebook 列表
  const { data: notebooksData, isLoading: isLoadingList } = useQuery({
    queryKey: ['notebooks', page, pageSize, statusFilter],
    queryFn: () =>
      model.getNotebooks({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  // 获取 Notebook 镜像列表
  const { data: imagesData } = useQuery({
    queryKey: ['notebook-images'],
    queryFn: () => model.getNotebookImages(),
  });

  // 创建 Notebook
  const createMutation = useMutation({
    mutationFn: model.createNotebook,
    onSuccess: () => {
      message.success('Notebook 创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    },
    onError: () => {
      message.error('Notebook 创建失败');
    },
  });

  // 启动 Notebook
  const startMutation = useMutation({
    mutationFn: model.startNotebook,
    onSuccess: () => {
      message.success('Notebook 启动成功');
      queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    },
    onError: () => {
      message.error('Notebook 启动失败');
    },
  });

  // 停止 Notebook
  const stopMutation = useMutation({
    mutationFn: model.stopNotebook,
    onSuccess: () => {
      message.success('Notebook 已停止');
      queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    },
    onError: () => {
      message.error('Notebook 停止失败');
    },
  });

  // 删除 Notebook
  const deleteMutation = useMutation({
    mutationFn: model.deleteNotebook,
    onSuccess: () => {
      message.success('Notebook 删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    },
    onError: () => {
      message.error('Notebook 删除失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'green',
      stopped: 'default',
      starting: 'blue',
      stopping: 'orange',
      error: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      running: '运行中',
      stopped: '已停止',
      starting: '启动中',
      stopping: '停止中',
      error: '错误',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Notebook) => (
        <a
          onClick={() => {
            setSelectedNotebook(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '镜像',
      dataIndex: 'image',
      key: 'image',
      render: (image: string) => <Tag>{image}</Tag>,
    },
    {
      title: '工作空间',
      dataIndex: 'workspace',
      key: 'workspace',
      render: (workspace: string) => workspace || 'default',
    },
    {
      title: '资源',
      key: 'resources',
      render: (_: unknown, record: Notebook) => (
        <Space size="small">
          <Tag>CPU: {record.resources.cpu}</Tag>
          <Tag>内存: {record.resources.memory}</Tag>
          {record.resources.gpu && <Tag color="blue">GPU: {record.resources.gpu}</Tag>}
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
      title: '最后活跃',
      dataIndex: 'last_active',
      key: 'last_active',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
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
      render: (_: unknown, record: Notebook) => (
        <Space>
          {record.status === 'running' ? (
            <>
              <Button
                type="text"
                icon={<LaptopOutlined />}
                onClick={() => window.open(record.url, '_blank')}
                title="打开 JupyterLab"
              >
                打开
              </Button>
              <Popconfirm
                title="确定要停止这个 Notebook 吗？"
                onConfirm={() => stopMutation.mutate(record.notebook_id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="text" danger icon={<StopOutlined />} />
              </Popconfirm>
            </>
          ) : (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.notebook_id)}
              loading={startMutation.isPending}
              title="启动"
            >
              启动
            </Button>
          )}
          <Popconfirm
            title="确定要删除这个 Notebook 吗？"
            onConfirm={() => deleteMutation.mutate(record.notebook_id)}
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
      createMutation.mutate({
        ...values,
        resources: {
          cpu: `${values.cpu}核`,
          memory: `${values.memory}Gi`,
          gpu: values.gpu ? `${values.gpu}卡` : undefined,
        },
      });
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="Notebook 开发环境"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            创建 Notebook
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 150 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="running">运行中</Option>
            <Option value="stopped">已停止</Option>
            <Option value="starting">启动中</Option>
            <Option value="error">错误</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={notebooksData?.data?.notebooks || []}
          rowKey="notebook_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: notebooksData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建 Notebook 模态框 */}
      <Modal
        title="创建 Notebook"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入 Notebook 名称' }]}
          >
            <Input placeholder="请输入 Notebook 名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="镜像"
            name="image"
            rules={[{ required: true, message: '请选择镜像' }]}
            initialValue="python:3.10"
          >
            <Select placeholder="请选择镜像">
              {imagesData?.data?.images?.map((img: NotebookImage) => (
                <Option key={img.name} value={img.name}>
                  {img.display_name} {img.python_version && `(${img.python_version})`}
                </Option>
              ))}
              <Option value="python:3.10">Python 3.10</Option>
              <Option value="python:3.11">Python 3.11</Option>
              <Option value="python:3.10-tensorflow">Python 3.10 + TensorFlow</Option>
              <Option value="python:3.10-pytorch">Python 3.10 + PyTorch</Option>
            </Select>
          </Form.Item>
          <Form.Item label="工作空间" name="workspace">
            <Input placeholder="默认工作空间" />
          </Form.Item>
          <Form.Item label="CPU 配置" name="cpu" rules={[{ required: true }]} initialValue={2}>
            <InputNumber min={1} max={32} style={{ width: '100%' }} addonAfter="核" />
          </Form.Item>
          <Form.Item label="内存配置" name="memory" rules={[{ required: true }]} initialValue={8}>
            <InputNumber min={1} max={128} style={{ width: '100%' }} addonAfter="Gi" />
          </Form.Item>
          <Form.Item label="GPU 配置" name="gpu">
            <InputNumber min={0} max={8} style={{ width: '100%' }} addonAfter="卡" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Notebook 详情抽屉 */}
      <Drawer
        title="Notebook 详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedNotebook(null);
        }}
        width={600}
      >
        {selectedNotebook && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="名称" span={2}>
                {selectedNotebook.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedNotebook.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedNotebook.status)}>
                  {getStatusText(selectedNotebook.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="镜像">
                <Tag>{selectedNotebook.image}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="工作空间" span={2}>
                {selectedNotebook.workspace || 'default'}
              </Descriptions.Item>
              <Descriptions.Item label="CPU">
                {selectedNotebook.resources.cpu}
              </Descriptions.Item>
              <Descriptions.Item label="内存">
                {selectedNotebook.resources.memory}
              </Descriptions.Item>
              {selectedNotebook.resources.gpu && (
                <Descriptions.Item label="GPU" span={2}>
                  <Tag color="blue">{selectedNotebook.resources.gpu}</Tag>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedNotebook.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedNotebook.last_active && (
                <Descriptions.Item label="最后活跃" span={2}>
                  {dayjs(selectedNotebook.last_active).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
            </Descriptions>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                {selectedNotebook.status === 'running' && (
                  <Button
                    type="primary"
                    icon={<ApiOutlined />}
                    onClick={() => window.open(selectedNotebook.url, '_blank')}
                  >
                    打开 JupyterLab
                  </Button>
                )}
                {selectedNotebook.status === 'running' ? (
                  <Popconfirm
                    title="确定要停止这个 Notebook 吗？"
                    onConfirm={() => stopMutation.mutate(selectedNotebook.notebook_id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button danger icon={<StopOutlined />}>
                      停止
                    </Button>
                  </Popconfirm>
                ) : (
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => startMutation.mutate(selectedNotebook.notebook_id)}
                    loading={startMutation.isPending}
                  >
                    启动
                  </Button>
                )}
                <Popconfirm
                  title="确定要删除这个 Notebook 吗？"
                  onConfirm={() => deleteMutation.mutate(selectedNotebook.notebook_id)}
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

export default NotebooksPage;
