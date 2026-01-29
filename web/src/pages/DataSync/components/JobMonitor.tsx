/**
 * 任务监控组件
 * 实时显示 CDC 任务的运行指标
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Select,
  Space,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { cdcApi } from '../services/cdc';

const { Option } = Select;

interface JobMonitorProps {
  className?: string;
}

/**
 * 任务监控组件
 */
const JobMonitor: React.FC<JobMonitorProps> = ({ className }) => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // 获取任务列表
  const { data: jobsData } = useQuery({
    queryKey: ['cdc', 'jobs'],
    queryFn: () => cdcApi.listJobs(),
    refetchInterval: 5000,
  });

  // 获取选中任务的指标
  const { data: metricsData, isLoading } = useQuery({
    queryKey: ['cdc', 'metrics', selectedJobId],
    queryFn: () => cdcApi.getJobMetrics(selectedJobId!),
    refetchInterval: 2000,
    enabled: !!selectedJobId,
  });

  const jobs = jobsData?.data?.jobs || [];
  const metrics = metricsData?.data;

  const runningJobs = jobs.filter((j) => j.status === 'running');

  // 自动选择第一个运行中的任务
  useEffect(() => {
    if (!selectedJobId && runningJobs.length > 0) {
      setSelectedJobId(runningJobs[0].job_id);
    }
  }, [runningJobs, selectedJobId]);

  const renderStatus = (status: string) => {
    if (status === 'running') {
      return (
        <Tag icon={<SyncOutlined spin />} color="processing">
          运行中
        </Tag>
      );
    }
    if (status === 'stopped') {
      return (
        <Tag icon={<CheckCircleOutlined />} color="default">
          已停止
        </Tag>
      );
    }
    if (status === 'error') {
      return (
        <Tag icon={<CloseCircleOutlined />} color="error">
          错误
        </Tag>
      );
    }
    return <Tag>{status}</Tag>;
  };

  const columns = [
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
    },
  ];

  const getMetricsData = () => {
    if (!metrics) return [];

    return [
      {
        key: 'status',
        name: '状态',
        value: renderStatus(metrics.status),
      },
      {
        key: 'records_in',
        name: '输入记录数',
        value: metrics.records_in?.toLocaleString() || '-',
      },
      {
        key: 'records_out',
        name: '输出记录数',
        value: metrics.records_out?.toLocaleString() || '-',
      },
      {
        key: 'bytes_in',
        name: '输入字节数',
        value: metrics.bytes_in ? `${(metrics.bytes_in / 1024 / 1024).toFixed(2)} MB` : '-',
      },
      {
        key: 'bytes_out',
        name: '输出字节数',
        value: metrics.bytes_out ? `${(metrics.bytes_out / 1024 / 1024).toFixed(2)} MB` : '-',
      },
      {
        key: 'lag',
        name: '延迟',
        value: metrics.lag_ms ? `${(metrics.lag_ms / 1000).toFixed(2)} 秒` : '-',
      },
      {
        key: 'last_checkpoint',
        name: '最后 Checkpoint',
        value: metrics.last_checkpoint ? new Date(metrics.last_checkpoint).toLocaleString() : '-',
      },
      {
        key: 'start_time',
        name: '启动时间',
        value: metrics.start_time ? new Date(metrics.start_time).toLocaleString() : '-',
      },
    ];
  };

  return (
    <div className={className}>
      <Row gutter={16}>
        {/* 任务选择 */}
        <Col span={24}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <span>选择任务:</span>
              <Select
                style={{ width: 300 }}
                value={selectedJobId}
                onChange={setSelectedJobId}
                placeholder="选择要监控的任务"
              >
                {jobs.map((job) => (
                  <Option key={job.job_id} value={job.job_id}>
                    {job.job_name} ({renderStatus(job.status)})
                  </Option>
                ))}
              </Select>
            </Space>
          </Card>
        </Col>

        {/* 实时指标 */}
        <Col span={24}>
          <Card
            title={metrics ? `监控: ${jobs.find((j) => j.job_id === selectedJobId)?.job_name}` : '任务监控'}
            loading={isLoading}
          >
            {metrics ? (
              <>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={6}>
                    <Statistic title="状态" valueRender={() => renderStatus(metrics.status)} />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="输入记录"
                      value={metrics.records_in}
                      formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="输出记录"
                      value={metrics.records_out}
                      formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="延迟"
                      value={metrics.lag_ms ? (metrics.lag_ms / 1000).toFixed(2) : '-'}
                      suffix="秒"
                      valueStyle={{
                        color: metrics.lag_ms && metrics.lag_ms > 60000 ? '#ff4d4f' : '#52c41a',
                      }}
                    />
                  </Col>
                </Row>

                <Table
                  columns={columns}
                  dataSource={getMetricsData()}
                  pagination={false}
                  size="small"
                />
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                <SyncOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>请选择要监控的任务</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default JobMonitor;
