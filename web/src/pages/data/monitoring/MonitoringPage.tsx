import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Select,
  DatePicker,
  Button,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  BellOutlined,
  SettingOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { TaskMetrics, Alert as AlertType } from '@/services/alldata';

const { RangePicker } = DatePicker;
const { Option } = Select;

function MonitoringPage() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs(),
  ]);
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Queries
  const { data: overviewData } = useQuery({
    queryKey: ['monitoring-overview'],
    queryFn: () => alldata.getMonitoringOverview(),
    refetchInterval: 30000,
  });

  const { data: tasksData } = useQuery({
    queryKey: ['task-metrics', taskTypeFilter, statusFilter, dateRange],
    queryFn: () =>
      alldata.getTaskMetrics({
        task_type: taskTypeFilter || undefined,
        status: statusFilter || undefined,
        start_time: dateRange[0].format('YYYY-MM-DD'),
        end_time: dateRange[1].format('YYYY-MM-DD'),
      }),
    refetchInterval: 10000,
  });

  const { data: alertsData } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alldata.getAlerts({ status: 'active', page: 1, page_size: 10 }),
    refetchInterval: 10000,
  });

  const { data: alertRulesData } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => alldata.getAlertRules(),
  });

  const getTaskStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'processing',
      success: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  const getTaskStatusText = (status: string) => {
    const texts: Record<string, string> = {
      running: '运行中',
      success: '成功',
      failed: '失败',
    };
    return texts[status] || status;
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      info: 'blue',
      warning: 'orange',
      error: 'red',
      critical: 'red',
    };
    return colors[severity] || 'default';
  };

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (type: string) => {
        const labels: Record<string, string> = {
          etl: 'ETL',
          quality: '质量检查',
          workflow: '工作流',
        };
        return <Tag>{labels[type] || type}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getTaskStatusColor(status)} icon={status === 'running' ? <ClockCircleOutlined /> : status === 'success' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
          {getTaskStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm:ss'),
    },
    {
      title: '耗时',
      key: 'duration',
      render: (_: unknown, record: TaskMetrics) =>
        record.duration_ms ? `${(record.duration_ms / 1000).toFixed(2)}s` : '-',
    },
    {
      title: '处理数据',
      key: 'data',
      render: (_: unknown, record: TaskMetrics) => {
        if (!record.rows_processed) return '-';
        return `${record.rows_processed.toLocaleString()} 行`;
      },
    },
  ];

  const alertColumns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)} icon={<BellOutlined />}>
          {severity}
        </Tag>
      ),
    },
    {
      title: '告警信息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '规则',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '触发值',
      dataIndex: 'metric_value',
      key: 'metric_value',
      render: (val: number) => val?.toFixed(2) || '-',
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      render: (val: number) => val?.toFixed(2) || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const labels: Record<string, string> = {
          active: '活跃',
          acknowledged: '已确认',
          resolved: '已解决',
        };
        return <Tag>{labels[status] || status}</Tag>;
      },
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm:ss'),
    },
  ];

  const acknowledgeAlert = (alertId: string) => {
    alldata.acknowledgeAlert(alertId).then(() => {
      message.success('告警已确认');
    });
  };

  const resolveAlert = (alertId: string) => {
    alldata.resolveAlert(alertId).then(() => {
      message.success('告警已解决');
    });
  };

  const overview = overviewData?.data;

  return (
    <div style={{ padding: '24px' }}>
      {/* 概览统计 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={overview?.total_tasks || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={overview?.running_tasks || 0}
              prefix={<ReloadOutlined spin />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败任务"
              value={overview?.failed_tasks || 0}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={overview?.success_rate || 0}
              suffix="%"
              precision={1}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 任务监控 */}
        <Col span={16}>
          <Card
            title="任务监控"
            extra={
              <Space>
                <Select
                  placeholder="任务类型"
                  allowClear
                  style={{ width: 120 }}
                  value={taskTypeFilter || undefined}
                  onChange={setTaskTypeFilter}
                >
                  <Option value="etl">ETL 任务</Option>
                  <Option value="quality">质量检查</Option>
                  <Option value="workflow">工作流</Option>
                </Select>
                <Select
                  placeholder="状态"
                  allowClear
                  style={{ width: 100 }}
                  value={statusFilter || undefined}
                  onChange={setStatusFilter}
                >
                  <Option value="running">运行中</Option>
                  <Option value="success">成功</Option>
                  <Option value="failed">失败</Option>
                </Select>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => {
                    if (dates && dates[0] && dates[1]) {
                      setDateRange([dates[0], dates[1]]);
                    }
                  }}
                />
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    // Trigger refetch
                  }}
                />
              </Space>
            }
          >
            <Table
              columns={taskColumns}
              dataSource={tasksData?.data?.metrics || []}
              rowKey="task_id"
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Col>

        {/* 告警列表 */}
        <Col span={8}>
          <Card
            title={<><BellOutlined /> 活跃告警</>}
            extra={<Tag color="red">{alertsData?.data?.alerts.length || 0}</Tag>}
          >
            <Table
              columns={alertColumns}
              dataSource={alertsData?.data?.alerts || []}
              rowKey="alert_id"
              pagination={false}
              size="small"
              expandable={{
                expandedRowRender: (record: AlertType) => (
                  <div style={{ padding: '8px 0' }}>
                    <Space>
                      <Button size="small" onClick={() => acknowledgeAlert(record.alert_id)}>
                        确认
                      </Button>
                      <Button size="small" type="primary" onClick={() => resolveAlert(record.alert_id)}>
                        解决
                      </Button>
                    </Space>
                  </div>
                ),
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 告警规则 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={<><SettingOutlined /> 告警规则</>}
            extra={
              <Button type="primary" icon={<PlusOutlined />}>
                新建规则
              </Button>
            }
          >
            <Table
              columns={[
                { title: '规则名称', dataIndex: 'name', key: 'name' },
                { title: '指标', dataIndex: 'metric', key: 'metric' },
                {
                  title: '条件',
                  dataIndex: 'condition',
                  key: 'condition',
                  render: (cond: string) => {
                    const labels: Record<string, string> = {
                      greater_than: '大于',
                      less_than: '小于',
                      equal_to: '等于',
                    };
                    return labels[cond] || cond;
                  },
                },
                { title: '阈值', dataIndex: 'threshold', key: 'threshold' },
                {
                  title: '级别',
                  dataIndex: 'severity',
                  key: 'severity',
                  render: (severity: string) => <Tag color={getSeverityColor(severity)}>{severity}</Tag>,
                },
                {
                  title: '状态',
                  dataIndex: 'enabled',
                  key: 'enabled',
                  render: (enabled: boolean) => (
                    <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
                  ),
                },
              ]}
              dataSource={alertRulesData?.data?.rules || []}
              rowKey="rule_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default MonitoringPage;
