/**
 * 调度器管理页面
 * 整合 DolphinScheduler 和 Celery 调度能力
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Tabs,
  Button,
  Space,
  Tag,
  message,
  Spin,
  Statistic,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  PlusOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import WorkflowEditor from './components/WorkflowEditor';
import TaskList from './components/TaskList';
import SchedulerMonitor from './components/SchedulerMonitor';
import CreateTaskModal from './components/CreateTaskModal';
import { schedulerApi } from './services/scheduler';

/**
 * 调度器管理页面
 */
const SchedulerPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string>('workflow');
  const [createModalVisible, setCreateModalVisible] = useState(false);

  // 获取统计信息
  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['scheduler', 'stats'],
    queryFn: () => schedulerApi.getStats(),
    refetchInterval: 10000, // 10秒刷新
  });

  // 健康检查
  const { data: healthData, refetch: refetchHealth } = useQuery({
    queryKey: ['scheduler', 'health'],
    queryFn: () => schedulerApi.getHealth(),
    refetchInterval: 30000, // 30秒刷新
  });

  const stats = statsData?.data || {};
  const health = healthData || {};

  // 刷新所有数据
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['scheduler'] });
    refetchStats();
    refetchHealth();
    message.success('刷新成功');
  }, [queryClient, refetchStats, refetchHealth]);

  // 获取资源使用率
  const getResourceUsage = () => {
    const resources = stats?.smart_scheduler?.available_resources || {};
    const total = stats?.smart_scheduler?.total_resources || {};

    if (!total.cpu_cores) return { cpu: 0, memory: 0, gpu: 0 };

    return {
      cpu: Math.round((1 - resources.cpu_cores / total.cpu_cores) * 100),
      memory: Math.round((1 - resources.memory_mb / total.memory_mb) * 100),
      gpu: Math.round((1 - resources.gpu_count / total.gpu_count) * 100),
    };
  };

  const resourceUsage = getResourceUsage();

  const tabs = [
    {
      key: 'workflow',
      label: (
        <span>
          <PlayCircleOutlined />
          工作流编排
        </span>
      ),
      children: <WorkflowEditor />,
    },
    {
      key: 'tasks',
      label: (
        <span>
          <ClockCircleOutlined />
          任务管理
        </span>
      ),
      children: <TaskList />,
    },
    {
      key: 'monitor',
      label: (
        <span>
          <BarChartOutlined />
          监控面板
        </span>
      ),
      children: <SchedulerMonitor />,
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 头部统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="总任务数"
              value={stats?.smart_scheduler?.total_tasks || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="运行中"
              value={stats?.smart_scheduler?.status_counts?.running || 0}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="已完成"
              value={stats?.smart_scheduler?.status_counts?.completed || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="失败"
              value={stats?.smart_scheduler?.status_counts?.failed || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 资源使用率 */}
      <Card title="资源使用率" style={{ marginBottom: 16 }} loading={statsLoading}>
        <Row gutter={16}>
          <Col span={8}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>CPU</span>
                <span>{resourceUsage.cpu}%</span>
              </div>
              <Progress percent={resourceUsage.cpu} status={resourceUsage.cpu > 80 ? 'exception' : 'active'} />
            </div>
          </Col>
          <Col span={8}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>内存</span>
                <span>{resourceUsage.memory}%</span>
              </div>
              <Progress percent={resourceUsage.memory} status={resourceUsage.memory > 80 ? 'exception' : 'active'} />
            </div>
          </Col>
          <Col span={8}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>GPU</span>
                <span>{resourceUsage.gpu}%</span>
              </div>
              <Progress percent={resourceUsage.gpu} status={resourceUsage.gpu > 80 ? 'exception' : 'active'} />
            </div>
          </Col>
        </Row>
      </Card>

      {/* 系统状态 */}
      <Card
        title={
          <Space>
            <span>系统状态</span>
            {health.status === 'healthy' ? (
              <Tag color="success">健康</Tag>
            ) : (
              <Tag color="warning">降级</Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => setCreateModalVisible(true)}
            >
              创建任务
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} />
      </Card>

      {/* 创建任务弹窗 */}
      <CreateTaskModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          handleRefresh();
        }}
      />
    </div>
  );
};

export default SchedulerPage;
