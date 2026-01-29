import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Statistic,
  Row,
  Col,
  Descriptions,
  Drawer,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import data from '@/services/data';
import type { FlinkJob, CreateFlinkJobRequest } from '@/services/data';

const { Option } = Select;
const { TextArea } = Input;

function StreamingPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<FlinkJob | null>(null);
  const [jobLogs, setJobLogs] = useState<string[]>([]);

  const [form] = Form.useForm();

  // Queries
  const { data: jobsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['flink-jobs', page, pageSize, statusFilter, typeFilter],
    queryFn: () =>
      data.getFlinkJobs({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      }),
    });

  // Mutations
  const createMutation = useMutation({
    mutationFn: data.createFlinkJob,
    onSuccess: () => {
      message.success('Flink 作业创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['flink-jobs'] });
    },
    onError: () => {
      message.error('Flink 作业创建失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: data.deleteFlinkJob,
    onSuccess: () => {
      message.success('Flink 作业删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['flink-jobs'] });
    },
    onError: () => {
      message.error('Flink 作业删除失败');
    },
  });

  const startMutation = useMutation({
    mutationFn: data.startFlinkJob,
    onSuccess: () => {
      message.success('Flink 作业启动成功');
      queryClient.invalidateQueries({ queryKey: ['flink-jobs'] });
    },
    onError: () => {
      message.error('Flink 作业启动失败');
    },
  });

  const stopMutation = useMutation({
    mutationFn: data.stopFlinkJob,
    onSuccess: () => {
      message.success('Flink 作业停止成功');
      queryClient.invalidateQueries({ queryKey: ['flink-jobs'] });
    },
    onError: () => {
      message.error('Flink 作业停止失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'green',
      stopped: 'default',
      failed: 'red',
      starting: 'blue',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      running: '运行中',
      stopped: '已停止',
      failed: '失败',
      starting: '启动中',
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '作业名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: FlinkJob) => (
        <a onClick={() => { setSelectedJob(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
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
      title: '并行度',
      dataIndex: 'parallelism',
      key: 'parallelism',
    },
    {
      title: 'Checkpoint',
      dataIndex: 'checkpoint_interval',
      key: 'checkpoint_interval',
      render: (interval: number) => `${interval}s`,
    },
    {
      title: '输入吞吐',
      key: 'in',
      render: (_: unknown, record: FlinkJob) =>
        record.statistics?.records_in ? `${(record.statistics.records_in / 1000).toFixed(1)}k` : '-',
    },
    {
      title: '输出吞吐',
      key: 'out',
      render: (_: unknown, record: FlinkJob) =>
        record.statistics?.records_out ? `${(record.statistics.records_out / 1000).toFixed(1)}k` : '-',
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
      render: (_: unknown, record: FlinkJob) => (
        <Space>
          {record.status === 'stopped' ? (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => startMutation.mutate(record.job_id)}
            >
              启动
            </Button>
          ) : record.status === 'running' ? (
            <Button
              type="text"
              danger
              icon={<StopOutlined />}
              onClick={() => stopMutation.mutate(record.job_id)}
            >
              停止
            </Button>
          ) : null}
          <Button
            type="text"
            icon={<CodeOutlined />}
            onClick={() => {
              setSelectedJob(record);
              data.getFlinkJobLogs(record.job_id, { limit: 100 }).then((res) => {
                setJobLogs(res.data.logs);
                setIsLogModalOpen(true);
              });
            }}
          >
            日志
          </Button>
          <Popconfirm
            title="确定要删除这个作业吗？"
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
      const data: CreateFlinkJobRequest = {
        ...values,
        source_config: { type: values.source_type, config: {} },
        sink_config: { type: values.sink_type, config: {} },
      };
      createMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="Flink 实时计算"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['flink-jobs'] })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
              新建作业
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 100 }}
            onChange={setTypeFilter}
            value={typeFilter || undefined}
          >
            <Option value="sql">SQL</Option>
            <Option value="jar">JAR</Option>
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="running">运行中</Option>
            <Option value="stopped">已停止</Option>
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

      {/* 创建作业模态框 */}
      <Modal
        title="新建 Flink 作业"
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
                label="作业名称"
                name="name"
                rules={[{ required: true, message: '请输入作业名称' }]}
              >
                <Input placeholder="请输入作业名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="作业类型"
                name="type"
                rules={[{ required: true, message: '请选择作业类型' }]}
                initialValue="sql"
              >
                <Select>
                  <Option value="sql">SQL 作业</Option>
                  <Option value="jar">JAR 作业</Option>
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
                label="并行度"
                name="parallelism"
                rules={[{ required: true, message: '请输入并行度' }]}
                initialValue={1}
              >
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Checkpoint 间隔 (秒)"
                name="checkpoint_interval"
                rules={[{ required: true, message: '请输入间隔时间' }]}
                initialValue={60}
              >
                <InputNumber min={1} max={3600} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="源类型"
            name="source_type"
            rules={[{ required: true, message: '请选择源类型' }]}
          >
            <Select>
              <Option value="kafka">Kafka</Option>
              <Option value="mysql">MySQL</Option>
              <Option value="postgresql">PostgreSQL</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="目标类型"
            name="sink_type"
            rules={[{ required: true, message: '请选择目标类型' }]}
          >
            <Select>
              <Option value="kafka">Kafka</Option>
              <Option value="mysql">MySQL</Option>
              <Option value="postgresql">PostgreSQL</Option>
            </Select>
          </Form.Item>
          <Form.Item label="SQL (SQL 作业必填)" name="sql">
            <TextArea rows={6} placeholder="SELECT ... FROM ..." style={{ fontFamily: 'monospace' }} />
          </Form.Item>
          <Form.Item label="JAR URI (JAR 作业必填)" name="jar_uri">
            <Input placeholder="s3://bucket/path/to/job.jar" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 作业详情抽屉 */}
      <Drawer
        title="作业详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedJob(null);
        }}
        width={700}
      >
        {selectedJob && (
          <div>
            <Descriptions title="基本信息" column={2} bordered size="small">
              <Descriptions.Item label="作业名称" span={2}>
                {selectedJob.name}
              </Descriptions.Item>
              <Descriptions.Item label="作业ID" span={2}>
                <Input.TextArea
                  value={selectedJob.job_id}
                  autoSize={{ minRows: 1, maxRows: 2 }}
                  readOnly
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag>{selectedJob.type.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedJob.status)}>{getStatusText(selectedJob.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="并行度">
                {selectedJob.parallelism}
              </Descriptions.Item>
              <Descriptions.Item label="Checkpoint 间隔">
                {selectedJob.checkpoint_interval}s
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedJob.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedJob.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {selectedJob.statistics && (
              <Card title="实时统计" size="small" style={{ marginTop: 16 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="输入吞吐"
                      value={(selectedJob.statistics.records_in / 1000).toFixed(1)}
                      suffix="k/s"
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="输出吞吐"
                      value={(selectedJob.statistics.records_out / 1000).toFixed(1)}
                      suffix="k/s"
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="延迟"
                      value={selectedJob.statistics.lag_ms ? (selectedJob.statistics.lag_ms / 1000).toFixed(2) : '-'}
                      suffix="s"
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="输入字节"
                      value={(selectedJob.statistics.bytes_in / 1024 / 1024).toFixed(2)}
                      suffix="MB"
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {selectedJob.sql && (
              <Card title="SQL 脚本" size="small" style={{ marginTop: 16 }}>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, fontSize: 12 }}>
                  {selectedJob.sql}
                </pre>
              </Card>
            )}
          </div>
        )}
      </Drawer>

      {/* 日志模态框 */}
      <Modal
        title="作业日志"
        open={isLogModalOpen}
        onCancel={() => setIsLogModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsLogModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <pre
          style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: 16,
            borderRadius: 4,
            fontSize: 12,
            maxHeight: 400,
            overflow: 'auto',
          }}
        >
          {jobLogs.join('\n')}
        </pre>
      </Modal>
    </div>
  );
}

export default StreamingPage;
