/**
 * 数据同步管理页面
 * 整合 SeaTunnel CDC 和 Kettle ETL 的数据同步功能
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Tabs,
  Button,
  Space,
  Tag,
  message,
  Statistic,
  Row,
  Col,
  Progress,
  Table,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  PlusOutlined,
  SyncOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cdcApi, CDCJob, CDCMetrics } from './services/cdc';
import CreateJobModal from './components/CreateJobModal';
import JobMonitor from './components/JobMonitor';

const { Option } = Select;
const { TextArea } = Input;

/**
 * 数据同步页面
 */
const DataSyncPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string>('cdc');
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<CDCJob | null>(null);

  // 获取 CDC 任务列表
  const { data: jobsData, isLoading: jobsLoading, refetch: refetchJobs } = useQuery({
    queryKey: ['cdc', 'jobs'],
    queryFn: () => cdcApi.listJobs(),
    select: (res) => res.data.data,
    refetchInterval: 5000,
  });

  // 健康检查
  const { data: healthData, refetch: refetchHealth } = useQuery({
    queryKey: ['cdc', 'health'],
    queryFn: () => cdcApi.getHealth(),
    select: (res) => res.data.data,
    refetchInterval: 30000,
  });

  const jobs = jobsData?.jobs || [];
  const defaultHealth = { status: 'unknown', service: 'unknown', url: '' };
  const health = healthData || defaultHealth;

  // 启动任务
  const startMutation = useMutation({
    mutationFn: (jobId: string) => cdcApi.startJob(jobId),
    onSuccess: () => {
      message.success('任务已启动');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误';
      message.error(`启动失败: ${errMsg}`);
    },
  });

  // 停止任务
  const stopMutation = useMutation({
    mutationFn: (jobId: string) => cdcApi.stopJob(jobId),
    onSuccess: () => {
      message.success('任务已停止');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误'; message.error(`停止失败: ${errMsg}`);
    },
  });

  // 删除任务
  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => cdcApi.deleteJob(jobId),
    onSuccess: () => {
      message.success('任务已删除');
      queryClient.invalidateQueries({ queryKey: ['cdc'] });
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误'; message.error(`删除失败: ${errMsg}`);
    },
  });

  const handleStart = (jobId: string) => {
    startMutation.mutate(jobId);
  };

  const handleStop = (jobId: string) => {
    stopMutation.mutate(jobId);
  };

  const handleDelete = (jobId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此任务吗？',
      onOk: () => {
        deleteMutation.mutate(jobId);
      },
    });
  };

  const handleRefresh = () => {
    refetchJobs();
    refetchHealth();
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'job_name',
      key: 'job_name',
      render: (text: string, record: CDCJob) => (
        <Space>
          <span>{text}</span>
          {record.status === 'running' && <SyncOutlined spin style={{ color: '#1890ff' }} />}
        </Space>
      ),
    },
    {
      title: '源类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '目标类型',
      dataIndex: 'sink_type',
      key: 'sink_type',
      width: 120,
      render: (type: string) => <Tag color="green">{type}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          running: { color: 'processing', text: '运行中' },
          stopped: { color: 'default', text: '已停止' },
          created: { color: 'blue', text: '已创建' },
          error: { color: 'error', text: '错误' },
        };
        const { color, text } = config[status] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '输入记录',
      dataIndex: 'records_in',
      key: 'records_in',
      width: 100,
      render: (count: number) => count?.toLocaleString() || '-',
    },
    {
      title: '输出记录',
      dataIndex: 'records_out',
      key: 'records_out',
      width: 100,
      render: (count: number) => count?.toLocaleString() || '-',
    },
    {
      title: '延迟',
      dataIndex: 'lag_ms',
      key: 'lag_ms',
      width: 100,
      render: (lag: number) => {
        if (!lag) return '-';
        const seconds = Math.round(lag / 1000);
        return <span style={{ color: seconds > 60 ? '#ff4d4f' : '#52c41a' }}>{seconds}s</span>;
      },
    },
    {
      title: '启动时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 160,
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: CDCJob) => (
        <Space size="small">
          {record.status === 'running' ? (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStop(record.job_id)}
              loading={stopMutation.isPending}
            >
              停止
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.job_id)}
              loading={startMutation.isPending}
            >
              启动
            </Button>
          )}
          <Button
            type="link"
            size="small"
            onClick={() => setSelectedJob(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(record.job_id)}
            loading={deleteMutation.isPending}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 统计运行中任务
  const runningJobs = jobs.filter((j: CDCJob) => j.status === 'running');
  const totalRecordsIn = jobs.reduce((sum: number, j: CDCJob) => sum + (j.records_in || 0), 0);
  const totalRecordsOut = jobs.reduce((sum: number, j: CDCJob) => sum + (j.records_out || 0), 0);

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 头部统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={jobsLoading}>
            <Statistic
              title="总任务数"
              value={jobs.length}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={jobsLoading}>
            <Statistic
              title="运行中"
              value={runningJobs.length}
              prefix={<SyncOutlined spin={runningJobs.length > 0} />}
              valueStyle={{ color: runningJobs.length > 0 ? '#1890ff' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={jobsLoading}>
            <Statistic
              title="输入记录"
              value={totalRecordsIn}
              formatter={(value) => `${(Number(value) / 1000000).toFixed(2)}M`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={jobsLoading}>
            <Statistic
              title="输出记录"
              value={totalRecordsOut}
              formatter={(value) => `${(Number(value) / 1000000).toFixed(2)}M`}
            />
          </Card>
        </Col>
      </Row>

      {/* 服务状态 */}
      <Card
        title={
          <Space>
            <CloudServerOutlined />
            <span>CDC 服务状态</span>
            <Tag color={health.status === 'healthy' ? 'success' : 'error'}>
              {health.status === 'healthy' ? '正常' : '异常'}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => setCreateModalVisible(true)}
            >
              创建同步任务
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'cdc',
              label: (
                <span>
                  <SyncOutlined />
                  CDC 实时同步
                </span>
              ),
              children: (
                <Table
                  columns={columns}
                  dataSource={jobs}
                  rowKey="job_id"
                  loading={jobsLoading}
                  scroll={{ x: 1200 }}
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
            {
              key: 'etl',
              label: (
                <span>
                  <PlayCircleOutlined />
                  ETL 批处理
                </span>
              ),
              children: (
                <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
                  <PlayCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <p>ETL 批处理任务管理</p>
                  <p>
                    请前往"数据治理 {'>'} ETL 任务"页面管理
                  </p>
                </div>
              ),
            },
            {
              key: 'monitor',
              label: (
                <span>
                  <DatabaseOutlined />
                  任务监控
                </span>
              ),
              children: <JobMonitor />,
            },
          ]}
        />
      </Card>

      {/* 创建任务弹窗 */}
      <CreateJobModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          handleRefresh();
        }}
      />

      {/* 任务详情弹窗 */}
      <Modal
        title="任务详情"
        open={!!selectedJob}
        onCancel={() => setSelectedJob(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedJob(null)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedJob && (
          <Form layout="vertical">
            <Form.Item label="任务 ID">
              <Input value={selectedJob.job_id} readOnly />
            </Form.Item>
            <Form.Item label="任务名称">
              <Input value={selectedJob.job_name} readOnly />
            </Form.Item>
            <Form.Item label="描述">
              <TextArea value={selectedJob.description || ''} readOnly rows={2} />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="源类型">
                  <Input value={selectedJob.source_type} readOnly />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="目标类型">
                  <Input value={selectedJob.sink_type} readOnly />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="状态">
              <Tag
                color={
                  selectedJob.status === 'running'
                    ? 'processing'
                    : selectedJob.status === 'error'
                    ? 'error'
                    : 'default'
                }
              >
                {selectedJob.status}
              </Tag>
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default DataSyncPage;
