import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Select,
  Typography,
  Alert,
} from 'antd';
import {
  ClusterOutlined,
  FireOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import model from '@/services/model';

const { Title, Text } = Typography;
const { Option } = Select;

function ResourcesPage() {
  const [poolFilter, setPoolFilter] = useState<string>('all');

  // 获取资源概览
  const { data: overviewData, isLoading: overviewLoading } = useQuery({
    queryKey: ['resource-overview'],
    queryFn: () => model.getResourceOverview(),
    refetchInterval: 10000, // 每 10 秒刷新
  });

  // 获取 GPU 资源
  const { data: gpuData, isLoading: gpuLoading } = useQuery({
    queryKey: ['gpu-resources'],
    queryFn: () => model.getGPUResources(),
    refetchInterval: 10000,
  });

  // 获取资源池
  const { data: poolsData, isLoading: poolsLoading } = useQuery({
    queryKey: ['resource-pools'],
    queryFn: () => model.getResourcePools(),
    refetchInterval: 10000,
  });

  const overview = overviewData?.data;
  const gpus = gpuData?.data?.gpus || [];
  const pools = poolsData?.data?.pools || [];

  // GPU 表格列
  const gpuColumns: any[] = [
    {
      title: 'GPU ID',
      dataIndex: 'gpu_id',
      key: 'gpu_id',
    },
    {
      title: '类型',
      dataIndex: 'gpu_type',
      key: 'gpu_type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          available: 'green',
          in_use: 'blue',
          maintenance: 'red',
        };
        const texts: Record<string, string> = {
          available: '可用',
          in_use: '使用中',
          maintenance: '维护中',
        };
        return <Tag color={colors[status]}>{texts[status] || status}</Tag>;
      },
    },
    {
      title: '利用率',
      dataIndex: 'utilization',
      key: 'utilization',
      render: (utilization?: number) => {
        if (utilization === undefined) return '-';
        const percent = Math.round(utilization);
        let color = 'green';
        if (percent > 80) color = 'red';
        else if (percent > 50) color = 'orange';
        return <Progress percent={percent} size="small" strokeColor={color} />;
      },
    },
    {
      title: '显存',
      key: 'memory',
      render: (_: unknown, record: { memory_used?: number; memory_total?: number }) => {
        if (record.memory_total === undefined) return '-';
        const used = record.memory_used || 0;
        const percent = Math.round((used / record.memory_total) * 100);
        return (
          <div>
            <Progress
              percent={percent}
              size="small"
              format={() => `${(used / 1024).toFixed(1)}GB / ${(record.memory_total! / 1024).toFixed(1)}GB`}
            />
          </div>
        );
      },
    },
    {
      title: '温度',
      dataIndex: 'temperature',
      key: 'temperature',
      render: (temp?: number) => {
        if (temp === undefined) return '-';
        let color = 'green';
        if (temp > 80) color = 'red';
        else if (temp > 60) color = 'orange';
        return <Text style={{ color }}> {temp}°C</Text>;
      },
    },
    {
      title: '运行任务',
      key: 'jobs',
      render: (_: unknown, record: { jobs?: Array<{ job_name: string }> }) => {
        if (!record.jobs || record.jobs.length === 0) return '-';
        return (
          <Space direction="vertical" size="small">
            {record.jobs.map((job, idx) => (
              <Tag key={idx}>{job.job_name}</Tag>
            ))}
          </Space>
        );
      },
    },
  ];

  // 资源池表格列
  const poolColumns: any[] = [
    {
      title: '资源池',
      dataIndex: 'pool_name',
      key: 'pool_name',
    },
    {
      title: '类型',
      dataIndex: 'pool_type',
      key: 'pool_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          cpu: 'blue',
          gpu: 'green',
          mixed: 'orange',
        };
        const texts: Record<string, string> = {
          cpu: 'CPU',
          gpu: 'GPU',
          mixed: '混合',
        };
        return <Tag color={colors[type]}>{texts[type] || type}</Tag>;
      },
    },
    {
      title: '总资源',
      key: 'total',
      render: (_: unknown, record: { total_resources: { cpu: number; memory: string; gpu?: number } }) => (
        <Space>
          <Tag>{record.total_resources.cpu} 核</Tag>
          <Tag>{record.total_resources.memory}</Tag>
          {record.total_resources.gpu !== undefined && <Tag color="blue">{record.total_resources.gpu} GPU</Tag>}
        </Space>
      ),
    },
    {
      title: '已用资源',
      key: 'used',
      render: (_: unknown, record: { used_resources: { cpu: number; memory: string; gpu?: number } }) => (
        <Space>
          <Tag>{record.used_resources.cpu} 核</Tag>
          <Tag>{record.used_resources.memory}</Tag>
          {record.used_resources.gpu !== undefined && <Tag color="blue">{record.used_resources.gpu} GPU</Tag>}
        </Space>
      ),
    },
    {
      title: '可用资源',
      key: 'available',
      render: (_: unknown, record: { available_resources: { cpu: number; memory: string; gpu?: number } }) => (
        <Space>
          <Tag color="green">{record.available_resources.cpu} 核</Tag>
          <Tag color="green">{record.available_resources.memory}</Tag>
          {record.available_resources.gpu !== undefined && (
            <Tag color="green">{record.available_resources.gpu} GPU</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '运行任务',
      dataIndex: 'running_jobs',
      key: 'running_jobs',
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '排队任务',
      dataIndex: 'queued_jobs',
      key: 'queued_jobs',
      render: (count: number) => (count > 0 ? <Tag color="orange">{count}</Tag> : <Tag>0</Tag>),
    },
  ];

  const filteredPools = pools.filter((pool) => {
    if (poolFilter === 'all') return true;
    return pool.pool_type === poolFilter;
  });

  const gpuUtilizationPercent = overview?.total_gpu
    ? Math.round((overview.used_gpu / overview.total_gpu) * 100)
    : 0;

  const cpuUtilizationPercent = overview?.total_cpu
    ? Math.round((overview.used_cpu / overview.total_cpu) * 100)
    : 0;

  return (
    <div style={{ padding: '24px' }}>
      <Title level={3}>资源管理</Title>

      {/* 资源概览卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card loading={overviewLoading}>
            <Statistic
              title="GPU 使用情况"
              value={`${overview?.used_gpu || 0} / ${overview?.total_gpu || 0}`}
              prefix={<ClusterOutlined />}
            />
            <Progress
              percent={gpuUtilizationPercent}
              strokeColor={gpuUtilizationPercent > 80 ? '#ff4d4f' : '#1677ff'}
              style={{ marginTop: 16 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={overviewLoading}>
            <Statistic
              title="CPU 使用情况"
              value={`${overview?.used_cpu || 0} / ${overview?.total_cpu || 0}`}
              prefix={<ThunderboltOutlined />}
              suffix="核"
            />
            <Progress
              percent={cpuUtilizationPercent}
              strokeColor={cpuUtilizationPercent > 80 ? '#ff4d4f' : '#1677ff'}
              style={{ marginTop: 16 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={overviewLoading}>
            <Statistic
              title="运行中任务"
              value={overview?.running_jobs || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={overviewLoading}>
            <Statistic
              title="排队中任务"
              value={overview?.queued_jobs || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: (overview?.queued_jobs || 0) > 0 ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      {/* GPU 资源 */}
      <Card
        title={<Space><ClusterOutlined /> GPU 资源</Space>}
        style={{ marginBottom: 24 }}
      >
        {gpus.length === 0 && !gpuLoading ? (
          <Alert message="暂无 GPU 资源" type="info" showIcon />
        ) : (
          <Table
            columns={gpuColumns}
            dataSource={gpus}
            rowKey="gpu_id"
            loading={gpuLoading}
            pagination={false}
            size="small"
          />
        )}
      </Card>

      {/* 资源池 */}
      <Card
        title={<Space><FireOutlined /> 资源池</Space>}
        extra={
          <Select
            value={poolFilter}
            onChange={setPoolFilter}
            style={{ width: 120 }}
          >
            <Option value="all">全部</Option>
            <Option value="cpu">CPU</Option>
            <Option value="gpu">GPU</Option>
            <Option value="mixed">混合</Option>
          </Select>
        }
      >
        <Table
          columns={poolColumns}
          dataSource={filteredPools}
          rowKey="pool_name"
          loading={poolsLoading}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}

export default ResourcesPage;
