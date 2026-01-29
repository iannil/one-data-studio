/**
 * 任务列表组件
 * 显示和管理所有调度任务
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Select,
  Input,
  Modal,
  Form,
  message,
  Tooltip,
  Progress,
} from 'antd';
import {
  ReloadOutlined,
  StopOutlined,
  EyeOutlined,
  SearchOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { schedulerApi, TaskInfo, SmartTask } from '../services/scheduler';

const { Option } = Select;

interface TaskListProps {
  className?: string;
}

/**
 * 任务列表组件
 */
const TaskList: React.FC<TaskListProps> = ({ className }) => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<{
    status?: string;
    engine?: string;
    limit: number;
  }>({
    limit: 50,
  });
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskInfo | SmartTask | null>(null);

  // 获取统一任务列表
  const { data: tasksData, isLoading, refetch } = useQuery({
    queryKey: ['scheduler', 'tasks', filters],
    queryFn: () => schedulerApi.listTasks(filters),
    refetchInterval: 5000,
  });

  // 获取智能调度器任务
  const { data: smartTasksData } = useQuery({
    queryKey: ['scheduler', 'smartTasks', filters],
    queryFn: () => schedulerApi.listSmartTasks(filters),
    refetchInterval: 5000,
  });

  // 取消任务
  const cancelMutation = useMutation({
    mutationFn: ({ taskId, engine }: { taskId: string; engine?: string }) =>
      schedulerApi.cancelTask(taskId, engine),
    onSuccess: () => {
      message.success('任务已取消');
      queryClient.invalidateQueries({ queryKey: ['scheduler'] });
    },
    onError: (error: any) => {
      message.error(`取消失败: ${error.message || '未知错误'}`);
    },
  });

  // 获取任务详情
  const handleViewDetail = useCallback((task: TaskInfo | SmartTask) => {
    setSelectedTask(task);
    setDetailModalVisible(true);
  }, []);

  // 取消任务
  const handleCancel = useCallback(
    (task: TaskInfo | SmartTask) => {
      const taskId = 'task_id' in task ? task.task_id : task.task_id;
      const engine = 'engine' in task ? task.engine : undefined;

      Modal.confirm({
        title: '确认取消',
        content: `确定要取消任务 "${'name' in task ? task.name : taskId}" 吗？`,
        onOk: () => {
          cancelMutation.mutate({ taskId, engine });
        },
      });
    },
    [cancelMutation]
  );

  // 状态标签
  const renderStatus = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      PENDING: { color: 'default', text: '等待中' },
      STARTED: { color: 'processing', text: '运行中' },
      RUNNING: { color: 'processing', text: '运行中' },
      SUCCESS: { color: 'success', text: '成功' },
      COMPLETED: { color: 'success', text: '完成' },
      FAILURE: { color: 'error', text: '失败' },
      FAILED: { color: 'error', text: '失败' },
      RETRY: { color: 'warning', text: '重试中' },
      CANCELLED: { color: 'default', text: '已取消' },
      REVOKED: { color: 'default', text: '已撤销' },
    };

    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 合并任务列表
  const allTasks = [
    ...(tasksData?.data?.tasks || []),
    ...(smartTasksData?.data?.tasks || []),
  ];

  const columns: ColumnsType<any> = [
    {
      title: '任务 ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span style={{ fontFamily: 'monospace' }}>{text.substring(0, 16)}...</span>
        </Tooltip>
      ),
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => text || '-',
    },
    {
      title: '引擎',
      dataIndex: 'engine',
      key: 'engine',
      width: 120,
      render: (engine: string) => {
        const colors: Record<string, string> = {
          celery: 'green',
          dolphinscheduler: 'blue',
          smart: 'purple',
        };
        return <Tag color={colors[engine] || 'default'}>{engine}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: renderStatus,
    },
    {
      title: '进度',
      key: 'progress',
      width: 120,
      render: (_: any, record: any) => {
        if (record.status === 'SUCCESS' || record.status === 'COMPLETED') {
          return <Progress percent={100} size="small" status="success" />;
        }
        if (record.status === 'FAILURE' || record.status === 'FAILED') {
          return <Progress percent={100} size="small" status="exception" />;
        }
        if (record.status === 'STARTED' || record.status === 'RUNNING') {
          return <Progress percent={66} size="small" status="active" />;
        }
        return <Progress percent={0} size="small" />;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_: any, record: TaskInfo | SmartTask) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {(record.status === 'STARTED' ||
            record.status === 'RUNNING' ||
            record.status === 'PENDING') && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleCancel(record)}
            >
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className={className}>
      <Card
        title="任务列表"
        extra={
          <Space>
            <Select
              style={{ width: 120 }}
              placeholder="状态"
              allowClear
              value={filters.status}
              onChange={(value) => setFilters({ ...filters, status: value })}
            >
              <Option value="PENDING">等待中</Option>
              <Option value="RUNNING">运行中</Option>
              <Option value="STARTED">运行中</Option>
              <Option value="SUCCESS">成功</Option>
              <Option value="FAILURE">失败</Option>
            </Select>
            <Select
              style={{ width: 120 }}
              placeholder="引擎"
              allowClear
              value={filters.engine}
              onChange={(value) => setFilters({ ...filters, engine: value })}
            >
              <Option value="celery">Celery</Option>
              <Option value="dolphinscheduler">DolphinScheduler</Option>
              <Option value="smart">智能调度</Option>
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
              loading={isLoading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={allTasks}
          rowKey="task_id"
          loading={isLoading}
          scroll={{ x: 1000 }}
          pagination={{
            pageSize: filters.limit,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 任务详情弹窗 */}
      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedTask && (
          <div>
            <Form layout="vertical">
              <Form.Item label="任务 ID">
                <Input value={selectedTask.task_id} readOnly />
              </Form.Item>
              {'name' in selectedTask && selectedTask.name && (
                <Form.Item label="任务名称">
                  <Input value={selectedTask.name} readOnly />
                </Form.Item>
              )}
              {'engine' in selectedTask && (
                <Form.Item label="调度引擎">
                  <Input value={selectedTask.engine} readOnly />
                </Form.Item>
              )}
              <Form.Item label="状态">
                {renderStatus(selectedTask.status)}
              </Form.Item>
              <Form.Item label="创建时间">
                <Input
                  value={
                    selectedTask.created_at
                      ? new Date(selectedTask.created_at).toLocaleString()
                      : '-'
                  }
                  readOnly
                />
              </Form.Item>
              {'started_at' in selectedTask && selectedTask.started_at && (
                <Form.Item label="开始时间">
                  <Input
                    value={new Date(selectedTask.started_at).toLocaleString()}
                    readOnly
                  />
                </Form.Item>
              )}
              {'completed_at' in selectedTask && selectedTask.completed_at && (
                <Form.Item label="完成时间">
                  <Input
                    value={new Date(selectedTask.completed_at).toLocaleString()}
                    readOnly
                  />
                </Form.Item>
              )}
              {'metrics' in selectedTask && selectedTask.metrics && (
                <>
                  <Form.Item label="执行时长">
                    <Input
                      value={`${Math.round(selectedTask.metrics.execution_time_ms / 1000)} 秒`}
                      readOnly
                    />
                  </Form.Item>
                  <Form.Item label="成功率">
                    <Input value={`${(selectedTask.metrics.success_rate * 100).toFixed(1)}%`} readOnly />
                  </Form.Item>
                </>
              )}
              {'error' in selectedTask && selectedTask.error && (
                <Form.Item label="错误信息">
                  <Input.TextArea
                    rows={4}
                    value={selectedTask.error}
                    readOnly
                    style={{ color: '#ff4d4f' }}
                  />
                </Form.Item>
              )}
            </Form>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TaskList;
