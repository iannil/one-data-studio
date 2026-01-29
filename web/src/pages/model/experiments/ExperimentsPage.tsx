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
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  LineChartOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import model from '@/services/model';
import type { Experiment } from '@/services/model';

dayjs.extend(duration);

const { Option } = Select;
const { TextArea } = Input;

function ExperimentsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);

  const [form] = Form.useForm();

  // 获取实验列表
  const { data: experimentsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['experiments', page, pageSize, statusFilter, projectFilter],
    queryFn: () =>
      model.getExperiments({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        project: projectFilter || undefined,
      }),
  });

  // 创建实验
  const createMutation = useMutation({
    mutationFn: model.createExperiment,
    onSuccess: () => {
      message.success('实验创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
    onError: () => {
      message.error('实验创建失败');
    },
  });

  // 停止实验
  const stopMutation = useMutation({
    mutationFn: model.stopExperiment,
    onSuccess: () => {
      message.success('实验已停止');
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
    onError: () => {
      message.error('实验停止失败');
    },
  });

  // 删除实验
  const deleteMutation = useMutation({
    mutationFn: model.deleteExperiment,
    onSuccess: () => {
      message.success('实验删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
    onError: () => {
      message.error('实验删除失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'blue',
      completed: 'green',
      failed: 'red',
      stopped: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      stopped: '已停止',
    };
    return texts[status] || status;
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    return dayjs.duration(seconds, 'seconds').humanize();
  };

  const renderMetrics = (metrics?: Record<string, number>) => {
    if (!metrics || Object.keys(metrics).length === 0) return '-';
    return (
      <Space size="small" wrap>
        {Object.entries(metrics).slice(0, 3).map(([key, value]) => (
          <Tag key={key}>
            {key}: {typeof value === 'number' ? value.toFixed(4) : value}
          </Tag>
        ))}
        {Object.keys(metrics).length > 3 && <Tag>+{Object.keys(metrics).length - 3}</Tag>}
      </Space>
    );
  };

  const columns = [
    {
      title: '实验名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Experiment) => (
        <a
          onClick={() => {
            setSelectedExperiment(record);
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
      render: (_: unknown, record: Experiment) => renderMetrics(record.metrics),
    },
    {
      title: '时长',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration: number) => formatDuration(duration),
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
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: Experiment) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedExperiment(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          {record.status === 'running' && (
            <Popconfirm
              title="确定要停止这个实验吗？"
              onConfirm={() => stopMutation.mutate(record.experiment_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
          <Popconfirm
            title="确定要删除这个实验吗？"
            onConfirm={() => deleteMutation.mutate(record.experiment_id)}
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
      createMutation.mutate(values);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="实验管理"
        extra={
          <Space>
            <Button
              icon={<LineChartOutlined />}
              onClick={() => navigate('/model/experiments/compare')}
            >
              对比实验
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              创建实验
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
            <Option value="running">运行中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
            <Option value="stopped">已停止</Option>
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
          dataSource={experimentsData?.data?.experiments || []}
          rowKey="experiment_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: experimentsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建实验模态框 */}
      <Modal
        title="创建实验"
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
            label="实验名称"
            name="name"
            rules={[{ required: true, message: '请输入实验名称' }]}
          >
            <Input placeholder="请输入实验名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
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
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 实验详情抽屉 */}
      <Drawer
        title="实验详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedExperiment(null);
        }}
        width={700}
      >
        {selectedExperiment && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="实验名称" span={2}>
                {selectedExperiment.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedExperiment.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="项目">
                <Tag>{selectedExperiment.project}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedExperiment.status)}>
                  {getStatusText(selectedExperiment.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedExperiment.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="时长">
                {formatDuration(selectedExperiment.duration)}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间" span={2}>
                {dayjs(selectedExperiment.start_time).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedExperiment.end_time && (
                <Descriptions.Item label="结束时间" span={2}>
                  {dayjs(selectedExperiment.end_time).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="标签" span={2}>
                {selectedExperiment.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {selectedExperiment.metrics && Object.keys(selectedExperiment.metrics).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h3>指标</h3>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {Object.entries(selectedExperiment.metrics).map(([key, value]) => (
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

            {selectedExperiment.parameters && Object.keys(selectedExperiment.parameters).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h3>超参数</h3>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {Object.entries(selectedExperiment.parameters).map(([key, value]) => (
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
                  icon={<LineChartOutlined />}
                  onClick={() => navigate(`/model/experiments/${selectedExperiment.experiment_id}`)}
                >
                  查看详情
                </Button>
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => navigate(`/model/experiments/${selectedExperiment.experiment_id}/logs`)}
                >
                  查看日志
                </Button>
                {selectedExperiment.status === 'running' && (
                  <Popconfirm
                    title="确定要停止这个实验吗？"
                    onConfirm={() => stopMutation.mutate(selectedExperiment.experiment_id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button danger icon={<StopOutlined />}>
                      停止
                    </Button>
                  </Popconfirm>
                )}
                <Popconfirm
                  title="确定要删除这个实验吗？"
                  onConfirm={() => deleteMutation.mutate(selectedExperiment.experiment_id)}
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

export default ExperimentsPage;
