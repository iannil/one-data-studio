/**
 * 用户行为分析看板
 * 展示用户行为统计数据、异常检测、用户画像等
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  Alert,
  Tabs,
  Select,
  DatePicker,
  Button,
  Space,
  Tooltip,
  Badge,
  Timeline,
  Modal,
  Descriptions,
  message,
  Spin
} from 'antd';
import {
  UserOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  SafetyOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { behaviorApi } from '@/services/behavior';

const { TabPane } = Tabs;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface Anomaly {
  id: string;
  user_id: string;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  detected_at: string;
  status: 'open' | 'investigated' | 'resolved' | 'false_positive';
}

interface UserProfile {
  id: string;
  user_id: string;
  username?: string;
  email?: string;
  activity_level: string;
  last_active_at?: string;
  total_sessions: number;
  total_page_views: number;
  segment_tags: string[];
}

interface ActiveUser {
  user_id: string;
  session_count: number;
  page_views: number;
  last_active: string;
}

export const BehaviorDashboard: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState('overview');
  const [days, setDays] = useState(7);
  const [severityFilter, setSeverityFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);
  const [anomalyModalVisible, setAnomalyModalVisible] = useState(false);

  const queryClient = useQueryClient();

  // 获取统计概览
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['behavior-stats', days],
    queryFn: () => behaviorApi.getStatisticsOverview({ days }),
    refetchInterval: 60000, // 每分钟刷新
  });

  // 获取异常列表
  const { data: anomaliesData, isLoading: anomaliesLoading } = useQuery({
    queryKey: ['behavior-anomalies', severityFilter, statusFilter],
    queryFn: () => behaviorApi.getAnomalies({ severity: severityFilter, status: statusFilter }),
    refetchInterval: 30000, // 每30秒刷新
  });

  // 获取活跃用户
  const { data: activeUsersData } = useQuery({
    queryKey: ['behavior-active-users', days],
    queryFn: () => behaviorApi.getActiveUsers({ days }),
    refetchInterval: 60000,
  });

  // 获取用户分群
  const { data: segmentsData } = useQuery({
    queryKey: ['behavior-segments'],
    queryFn: () => behaviorApi.getSegments(),
    refetchInterval: 300000, // 5分钟刷新
  });

  // 异常状态配置
  const severityConfig = {
    critical: { color: 'red', icon: <WarningOutlined />, text: '严重' },
    high: { color: 'orange', icon: <WarningOutlined />, text: '高' },
    medium: { color: 'gold', icon: <ClockCircleOutlined />, text: '中' },
    low: { color: 'blue', icon: <SafetyOutlined />, text: '低' },
  };

  const statusConfig = {
    open: { color: 'red', text: '待处理' },
    investigated: { color: 'orange', text: '调查中' },
    resolved: { color: 'green', text: '已解决' },
    false_positive: { color: 'default', text: '误报' },
  };

  const activeLevelConfig = {
    high: { color: 'success', text: '高' },
    medium: { color: 'processing', text: '中' },
    low: { color: 'warning', text: '低' },
    inactive: { color: 'default', text: '不活跃' },
  };

  // 异常列表表格列
  const anomalyColumns = [
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      render: (userId: string) => (
        <Space>
          <UserOutlined />
          {userId}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'anomaly_type',
      key: 'anomaly_type',
      width: 180,
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          high_frequency_login: '高频登录',
          unusual_time_login: '非常时段登录',
          multi_location_login: '多地登录',
          access_denied: '访问拒绝',
          high_frequency_action: '高频操作',
          suspicious_export: '可疑数据导出',
          unusual_data_access: '异常数据访问',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const config = severityConfig[severity as keyof typeof severityConfig];
        return (
          <Tag color={config?.color} icon={config?.icon}>
            {config?.text}
          </Tag>
        );
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusConfig[status as keyof typeof statusConfig];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      },
    },
    {
      title: '检测时间',
      dataIndex: 'detected_at',
      key: 'detected_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Anomaly) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => {
              setSelectedAnomaly(record);
              setAnomalyModalVisible(true);
            }}
          >
            查看
          </Button>
          {record.status === 'open' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleResolveAnomaly(record.id)}
            >
              处理
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 活跃用户表格列
  const activeUsersColumns = [
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
    },
    {
      title: '会话数',
      dataIndex: 'session_count',
      key: 'session_count',
      sorter: (a: ActiveUser, b: ActiveUser) => a.session_count - b.session_count,
    },
    {
      title: '页面浏览',
      dataIndex: 'page_views',
      key: 'page_views',
      sorter: (a: ActiveUser, b: ActiveUser) => a.page_views - b.page_views,
    },
    {
      title: '最后活跃',
      dataIndex: 'last_active',
      key: 'last_active',
      render: (time: string) => dayjs(time).fromNow(),
    },
  ];

  const handleResolveAnomaly = async (anomalyId: string) => {
    try {
      await behaviorApi.updateAnomalyStatus(anomalyId, 'resolved');
      message.success('异常已标记为已处理');
      queryClient.invalidateQueries({ queryKey: ['behavior-anomalies'] });
    } catch (error) {
      message.error('操作失败');
    }
  };

  return (
    <div className="behavior-dashboard">
      <Card
        title={
          <Space>
            <BarChartOutlined />
            <span>用户行为分析</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries()}
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        实时监控用户行为，检测异常活动，分析用户画像
      </Card>

      <div className="page-content">
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card loading={statsLoading}>
              <Statistic
                title="总行为数"
                value={statsData?.total_behaviors || 0}
                prefix={<EyeOutlined />}
                suffix={`次/${days}天`}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={statsLoading}>
              <Statistic
                title="活跃用户"
                value={statsData?.unique_users || 0}
                prefix={<UserOutlined />}
                suffix={`人/${days}天`}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={statsLoading}>
              <Statistic
                title="总会话数"
                value={statsData?.total_sessions || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={statsLoading}>
              <Statistic
                title="待处理异常"
                value={statsData?.open_anomalies || 0}
                prefix={<WarningOutlined />}
                valueStyle={{ color: (statsData?.open_anomalies || 0) > 0 ? '#ff4d4f' : undefined }}
              />
            </Card>
          </Col>
        </Row>

        <Card>
          <Tabs activeKey={selectedTab} onChange={setSelectedTab}>
            <TabPane tab="行为异常" key="anomalies">
              <Space style={{ marginBottom: 16 }} wrap>
                <Space>
                  <span>严重程度:</span>
                  <Select
                    style={{ width: 120 }}
                    placeholder="全部"
                    value={severityFilter}
                    onChange={setSeverityFilter}
                    allowClear
                  >
                    <Option value="critical">严重</Option>
                    <Option value="high">高</Option>
                    <Option value="medium">中</Option>
                    <Option value="low">低</Option>
                  </Select>
                </Space>
                <Space>
                  <span>状态:</span>
                  <Select
                    style={{ width: 120 }}
                    placeholder="全部"
                    value={statusFilter}
                    onChange={setStatusFilter}
                    allowClear
                  >
                    <Option value="open">待处理</Option>
                    <Option value="investigated">调查中</Option>
                    <Option value="resolved">已解决</Option>
                    <Option value="false_positive">误报</Option>
                  </Select>
                </Space>
                <Space>
                  <span>统计周期:</span>
                  <Select value={days} onChange={setDays} style={{ width: 100 }}>
                    <Option value={1}>近1天</Option>
                    <Option value={7}>近7天</Option>
                    <Option value={30}>近30天</Option>
                  </Select>
                </Space>
              </Space>

              {anomaliesData?.anomalies && anomaliesData.anomalies.length > 0 && (
                <Alert
                  message="发现异常行为"
                  description={`检测到 ${anomaliesData.anomalies.length} 条异常记录，请及时处理`}
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              <Table
                columns={anomalyColumns}
                dataSource={anomaliesData?.anomalies || []}
                rowKey="id"
                loading={anomaliesLoading}
                pagination={{
                  pageSize: 20,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                scroll={{ x: 1000 }}
              />
            </TabPane>

            <TabPane tab="活跃用户" key="users">
              <Space style={{ marginBottom: 16 }}>
                <span>统计周期:</span>
                <Select value={days} onChange={setDays} style={{ width: 100 }}>
                  <Option value={1}>近1天</Option>
                  <Option value={7}>近7天</Option>
                  <Option value={30}>近30天</Option>
                </Select>
              </Space>

              <Table
                columns={activeUsersColumns}
                dataSource={activeUsersData?.users || []}
                rowKey="user_id"
                pagination={{
                  pageSize: 20,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
              />
            </TabPane>

            <TabPane tab="用户分群" key="segments">
              <Row gutter={16}>
                {segmentsData?.segments?.map((segment: any) => (
                  <Col span={6} key={segment.tag}>
                    <Card size="small">
                      <Statistic
                        title={segment.tag}
                        value={segment.count}
                        suffix="人"
                        valueStyle={{ fontSize: 24 }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>

              <div style={{ marginTop: 24 }}>
                <h4>分群说明</h4>
                <ul>
                  <li><Tag>power_user</Tag> - 高频用户，活跃度高</li>
                  <li><Tag>dormant_user</Tag> - 沉睡用户，长期未活跃</li>
                  <li><Tag>daily_user</Tag> - 每日活跃用户</li>
                  <li><Tag>data_analyst</Tag> - 数据分析师，偏好数据模块</li>
                  <li><Tag>admin_user</Tag> - 管理员用户</li>
                  <li><Tag>heavy_user</Tag> - 重度用户，使用时长长</li>
                </ul>
              </div>
            </TabPane>

            <TabPane tab="行为分布" key="distribution">
              <Spin spinning={statsLoading}>
                {statsData?.behavior_types && (
                  <div>
                    <h4>行为类型分布</h4>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      {statsData.behavior_types.map((bt: any) => (
                        <div key={bt.type}>
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <span>{bt.type}</span>
                            <span>{bt.count.toLocaleString()}</span>
                          </Space>
                          <Progress
                            percent={Math.round((bt.count / statsData.total_behaviors) * 100)}
                            showInfo={false}
                          />
                        </div>
                      ))}
                    </Space>
                  </div>
                )}
              </Spin>
            </TabPane>
          </Tabs>
        </Card>
      </div>

      {/* 异常详情弹窗 */}
      <Modal
        title="异常详情"
        open={anomalyModalVisible}
        onCancel={() => setAnomalyModalVisible(false)}
        width={700}
        footer={[
          <Button key="close" onClick={() => setAnomalyModalVisible(false)}>
            关闭
          </Button>,
          selectedAnomaly?.status === 'open' && (
            <Button
              key="resolve"
              type="primary"
              onClick={() => {
                if (selectedAnomaly) {
                  handleResolveAnomaly(selectedAnomaly.id);
                  setAnomalyModalVisible(false);
                }
              }}
            >
              标记为已处理
            </Button>
          ),
        ]}
      >
        {selectedAnomaly && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="用户ID">
              {selectedAnomaly.user_id}
            </Descriptions.Item>
            <Descriptions.Item label="异常类型">
              {selectedAnomaly.anomaly_type}
            </Descriptions.Item>
            <Descriptions.Item label="严重程度">
              <Tag color={severityConfig[selectedAnomaly.severity]?.color}>
                {severityConfig[selectedAnomaly.severity]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusConfig[selectedAnomaly.status]?.color}>
                {statusConfig[selectedAnomaly.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {selectedAnomaly.description}
            </Descriptions.Item>
            <Descriptions.Item label="检测时间">
              {dayjs(selectedAnomaly.detected_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default BehaviorDashboard;
