/**
 * 调度器监控面板组件
 * 实时显示调度器状态和资源使用情况
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Alert,
  Button,
  Space,
  Tooltip,
  Tabs,
  List,
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { schedulerApi, ResourcePrediction, SmartTask } from '../services/scheduler';

interface SchedulerMonitorProps {
  className?: string;
}

/**
 * 调度器监控面板
 */
const SchedulerMonitor: React.FC<SchedulerMonitorProps> = ({ className }) => {
  const [resourceWindow, setResourceWindow] = useState(60);

  // 获取统计信息
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['scheduler', 'stats'],
    queryFn: () => schedulerApi.getStats(),
    refetchInterval: 5000,
  });

  // 获取健康状态
  const { data: healthData, refetch: refetchHealth } = useQuery({
    queryKey: ['scheduler', 'health'],
    queryFn: () => schedulerApi.getHealth(),
    refetchInterval: 10000,
  });

  // 获取智能任务列表
  const { data: smartTasksData } = useQuery({
    queryKey: ['scheduler', 'smartTasks'],
    queryFn: () => schedulerApi.listSmartTasks({ limit: 100 }),
    refetchInterval: 5000,
  });

  // 优化调度
  const { data: optimizeData, refetch: refetchOptimize } = useQuery({
    queryKey: ['scheduler', 'optimize'],
    queryFn: () => schedulerApi.optimizeSchedule(),
    refetchInterval: 30000,
  });

  // 预测资源需求
  const { data: predictionData, refetch: refetchPrediction } = useQuery({
    queryKey: ['scheduler', 'prediction', resourceWindow],
    queryFn: () => schedulerApi.predictResourceDemand(resourceWindow),
    refetchInterval: 30000,
  });

  const stats = statsData?.data || {};
  const health = healthData || {};
  const smartTasks = smartTasksData?.data?.tasks || [];
  const prediction = predictionData?.data || null;

  const handleRefresh = () => {
    refetchStats();
    refetchHealth();
    refetchOptimize();
    refetchPrediction();
  };

  // 获取资源使用数据
  const getResourceData = () => {
    const total = stats?.smart_scheduler?.total_resources || {};
    const available = stats?.smart_scheduler?.available_resources || {};
    const statusCounts = stats?.smart_scheduler?.status_counts || {};

    return {
      total: {
        cpu: total.cpu_cores || 0,
        memory: Math.round((total.memory_mb || 0) / 1024), // GB
        gpu: total.gpu_count || 0,
      },
      available: {
        cpu: available.cpu_cores || 0,
        memory: Math.round((available.memory_mb || 0) / 1024),
        gpu: available.gpu_count || 0,
      },
      used: {
        cpu: (total.cpu_cores || 0) - (available.cpu_cores || 0),
        memory: Math.round(((total.memory_mb || 0) - (available.memory_mb || 0)) / 1024),
        gpu: (total.gpu_count || 0) - (available.gpu_count || 0),
      },
      usagePercent: {
        cpu: total.cpu_cores ? Math.round(((total.cpu_cores - available.cpu_cores) / total.cpu_cores) * 100) : 0,
        memory: total.memory_mb ? Math.round(((total.memory_mb - available.memory_mb) / total.memory_mb) * 100) : 0,
        gpu: total.gpu_count ? Math.round(((total.gpu_count - available.gpu_count) / total.gpu_count) * 100) : 0,
      },
      tasks: {
        total: stats?.smart_scheduler?.total_tasks || 0,
        pending: statusCounts.pending || 0,
        running: statusCounts.running || 0,
        completed: statusCounts.completed || 0,
        failed: statusCounts.failed || 0,
      },
    };
  };

  const resourceData = getResourceData();

  // 组件健康状态
  const renderHealthStatus = (component: string, isHealthy: boolean) => {
    if (isHealthy) {
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          {component} 正常
        </Tag>
      );
    }
    return (
      <Tag icon={<CloseCircleOutlined />} color="error">
        {component} 异常
      </Tag>
    );
  };

  // 任务表格列
  const taskColumns = [
    {
      title: '任务 ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 150,
      ellipsis: true,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 100,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: string) => {
        const colors: Record<string, string> = {
          critical: 'red',
          high: 'orange',
          normal: 'blue',
          low: 'default',
        };
        return <Tag color={colors[priority]}>{priority}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          pending: { color: 'default', text: '等待' },
          running: { color: 'processing', text: '运行' },
          completed: { color: 'success', text: '完成' },
          failed: { color: 'error', text: '失败' },
        };
        const { color, text } = config[status] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '资源需求',
      key: 'resource',
      width: 150,
      render: (_: any, record: SmartTask) => (
        <Space size={4}>
          <span>CPU: {record.resource_requirement.cpu_cores}</span>
          <span>MEM: {Math.round(record.resource_requirement.memory_mb / 1024)}GB</span>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'overview',
      label: '概览',
      children: (
        <Row gutter={[16, 16]}>
          {/* 资源使用卡片 */}
          <Col span={24}>
            <Card title="资源使用情况" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <div>
                    <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                      <span>CPU 使用</span>
                      <span>
                        {resourceData.used.cpu} / {resourceData.total.cpu} 核心
                      </span>
                    </div>
                    <Progress
                      percent={resourceData.usagePercent.cpu}
                      status={resourceData.usagePercent.cpu > 80 ? 'exception' : 'active'}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div>
                    <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                      <span>内存使用</span>
                      <span>
                        {resourceData.used.memory} / {resourceData.total.memory} GB
                      </span>
                    </div>
                    <Progress
                      percent={resourceData.usagePercent.memory}
                      status={resourceData.usagePercent.memory > 80 ? 'exception' : 'active'}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div>
                    <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                      <span>GPU 使用</span>
                      <span>
                        {resourceData.used.gpu} / {resourceData.total.gpu} 卡
                      </span>
                    </div>
                    <Progress
                      percent={resourceData.usagePercent.gpu}
                      status={resourceData.usagePercent.gpu > 80 ? 'exception' : 'active'}
                    />
                  </div>
                </Col>
              </Row>
            </Card>
          </Col>

          {/* 任务统计 */}
          <Col span={12}>
            <Card title="任务统计" size="small">
              <Row gutter={8}>
                <Col span={6}>
                  <Statistic title="等待中" value={resourceData.tasks.pending} valueStyle={{ color: '#faad14' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="运行中" value={resourceData.tasks.running} valueStyle={{ color: '#1890ff' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="已完成" value={resourceData.tasks.completed} valueStyle={{ color: '#52c41a' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="失败" value={resourceData.tasks.failed} valueStyle={{ color: '#ff4d4f' }} />
                </Col>
              </Row>
            </Card>
          </Col>

          {/* 组件状态 */}
          <Col span={12}>
            <Card title="组件状态" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                {renderHealthStatus('Celery', health?.components?.celery)}
                {renderHealthStatus('DolphinScheduler', health?.components?.dolphinscheduler)}
                {renderHealthStatus('Smart Scheduler', health?.components?.smart_scheduler)}
              </Space>
            </Card>
          </Col>

          {/* 资源预测 */}
          {prediction && (
            <Col span={24}>
              <Card
                title={
                  <Space>
                    <ClockCircleOutlined />
                    <span>资源需求预测 ({resourceWindow} 分钟)</span>
                  </Space>
                }
                size="small"
                extra={
                  <Select
                    value={resourceWindow}
                    onChange={setResourceWindow}
                    style={{ width: 100 }}
                  >
                    <option value={30}>30 分钟</option>
                    <option value={60}>1 小时</option>
                    <option value={120}>2 小时</option>
                    <option value={240}>4 小时</option>
                  </Select>
                }
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Alert
                      message={`预计任务数: ${prediction.predicted_tasks}`}
                      type="info"
                      showIcon
                    />
                  </Col>
                  <Col span={12}>
                    <Alert
                      message={`预计 CPU 使用率: ${prediction.resource_utilization.cpu_percent.toFixed(1)}%`}
                      type={prediction.resource_utilization.cpu_percent > 80 ? 'warning' : 'info'}
                      showIcon
                    />
                  </Col>
                </Row>
                {prediction.recommendations?.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <strong>建议：</strong>
                    <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                      {prediction.recommendations.map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            </Col>
          )}
        </Row>
      ),
    },
    {
      key: 'tasks',
      label: '任务列表',
      children: (
        <Table
          columns={taskColumns}
          dataSource={smartTasks}
          rowKey="task_id"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      ),
    },
    {
      key: 'optimization',
      label: '优化建议',
      children: (
        <div>
          {optimizeData?.data && (
            <Card size="small" style={{ marginBottom: 16 }}>
              <p>优化后的执行顺序：</p>
              <List
                size="small"
                bordered
                dataSource={optimizeData.data.optimized_order || []}
                renderItem={(item: string, index: number) => (
                  <List.Item>
                    <span style={{ marginRight: 16, fontWeight: 'bold' }}>#{index + 1}</span>
                    <span style={{ fontFamily: 'monospace' }}>{item}</span>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className={className}>
      <Card
        title="调度器监控"
        extra={
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        }
      >
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

export default SchedulerMonitor;
