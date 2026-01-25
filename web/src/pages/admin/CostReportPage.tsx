/**
 * ONE-DATA-STUDIO Cost Report Page
 * Admin page for viewing token usage and cost analytics.
 * Rewritten with Ant Design components
 */

import { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Row,
  Col,
  Statistic,
  Spin,
  Alert,
  Tabs,
  Typography,
  Progress,
  DatePicker,
} from 'antd';
import {
  DollarOutlined,
  FieldTimeOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  DownloadOutlined,
  RiseOutlined,
  FallOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

const { Option } = Select;
const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Types
interface CostSummary {
  total_cost: number;
  compute_cost: number;
  storage_cost: number;
  network_cost: number;
  api_cost: number;
  period: string;
  trend: string;
}

interface UsageItem {
  resource: string;
  usage: string;
  cost: number;
}

interface TrendItem {
  date: string;
  cost: number;
}

interface ModelCost {
  model: string;
  calls: number;
  tokens: number;
  cost: number;
  avg_cost: number;
}

// API functions
const fetchCostSummary = async (): Promise<CostSummary> => {
  const response = await fetch('/api/v1/cost/summary');
  if (!response.ok) throw new Error('Failed to fetch cost summary');
  const data = await response.json();
  return data.data;
};

const fetchCostUsage = async (): Promise<UsageItem[]> => {
  const response = await fetch('/api/v1/cost/usage');
  if (!response.ok) throw new Error('Failed to fetch cost usage');
  const data = await response.json();
  return data.data?.items || [];
};

const fetchCostTrends = async (): Promise<TrendItem[]> => {
  const response = await fetch('/api/v1/cost/trends');
  if (!response.ok) throw new Error('Failed to fetch cost trends');
  const data = await response.json();
  return data.data?.trends || [];
};

// Helper functions
const formatCurrency = (value: number, currency: string = 'CNY'): string => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value: number): string => {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return value.toFixed(0);
};

// Stat Card Component
const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
  color?: string;
}> = ({ title, value, subtitle, icon, trend, color = '#1890ff' }) => {
  const isPositiveTrend = trend && trend.startsWith('+');

  return (
    <Card hoverable bodyStyle={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>{title}</Text>
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 28, fontWeight: 600, color }}>{value}</span>
          </div>
          {subtitle && (
            <Text type="secondary" style={{ fontSize: 12 }}>{subtitle}</Text>
          )}
          {trend && (
            <div style={{ marginTop: 8 }}>
              {isPositiveTrend ? (
                <Text type="danger" style={{ fontSize: 12 }}>
                  <RiseOutlined /> {trend} 较上期
                </Text>
              ) : (
                <Text type="success" style={{ fontSize: 12 }}>
                  <FallOutlined /> {trend} 较上期
                </Text>
              )}
            </div>
          )}
        </div>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 8,
            backgroundColor: `${color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: color,
            fontSize: 24,
          }}
        >
          {icon}
        </div>
      </div>
    </Card>
  );
};

// Simple Bar Chart using pure CSS
const SimpleBarChart: React.FC<{ data: TrendItem[] }> = ({ data }) => {
  const maxCost = Math.max(...data.map(d => d.cost));

  return (
    <div style={{ height: 300, padding: '20px 0' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', height: '100%' }}>
        {data.map((item, index) => {
          const height = (item.cost / maxCost) * 100;
          return (
            <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 10, marginBottom: 4 }}>
                {formatCurrency(item.cost)}
              </Text>
              <div
                style={{
                  width: '60%',
                  height: `${height}%`,
                  minHeight: 4,
                  backgroundColor: '#1890ff',
                  borderRadius: '4px 4px 0 0',
                  transition: 'height 0.3s ease',
                }}
              />
              <Text type="secondary" style={{ fontSize: 10, marginTop: 4 }}>
                {dayjs(item.date).format('MM-DD')}
              </Text>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Cost Distribution Component
const CostDistribution: React.FC<{ summary: CostSummary }> = ({ summary }) => {
  const items = [
    { name: '计算资源', value: summary.compute_cost, color: '#1890ff' },
    { name: '存储', value: summary.storage_cost, color: '#52c41a' },
    { name: '网络', value: summary.network_cost, color: '#faad14' },
    { name: 'API 调用', value: summary.api_cost, color: '#722ed1' },
  ];

  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <div>
      {items.map((item, index) => {
        const percent = total > 0 ? (item.value / total) * 100 : 0;
        return (
          <div key={index} style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>{item.name}</Text>
              <Text strong>{formatCurrency(item.value)}</Text>
            </div>
            <Progress
              percent={percent}
              strokeColor={item.color}
              showInfo={false}
              size="small"
            />
          </div>
        );
      })}
    </div>
  );
};

function CostReportPage() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');

  // Queries
  const { data: summary, isLoading: isLoadingSummary } = useQuery({
    queryKey: ['cost-summary', period],
    queryFn: fetchCostSummary,
  });

  const { data: usage = [], isLoading: isLoadingUsage } = useQuery({
    queryKey: ['cost-usage', period],
    queryFn: fetchCostUsage,
  });

  const { data: trends = [], isLoading: isLoadingTrends } = useQuery({
    queryKey: ['cost-trends', period],
    queryFn: fetchCostTrends,
  });

  const isLoading = isLoadingSummary || isLoadingUsage || isLoadingTrends;

  // Mock model data for demonstration
  const modelData: ModelCost[] = [
    { model: 'gpt-4', calls: 1250, tokens: 2500000, cost: 3500.00, avg_cost: 2.80 },
    { model: 'gpt-3.5-turbo', calls: 8500, tokens: 12000000, cost: 1200.00, avg_cost: 0.14 },
    { model: 'claude-3-opus', calls: 450, tokens: 800000, cost: 1800.00, avg_cost: 4.00 },
    { model: 'claude-3-sonnet', calls: 2200, tokens: 3500000, cost: 800.00, avg_cost: 0.36 },
    { model: 'qwen-turbo', calls: 5000, tokens: 8000000, cost: 400.00, avg_cost: 0.08 },
  ];

  const usageColumns = [
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
    },
    {
      title: '用量',
      dataIndex: 'usage',
      key: 'usage',
    },
    {
      title: '费用',
      dataIndex: 'cost',
      key: 'cost',
      render: (cost: number) => formatCurrency(cost),
    },
  ];

  const modelColumns = [
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string) => <Tag color="blue">{model}</Tag>,
    },
    {
      title: '调用次数',
      dataIndex: 'calls',
      key: 'calls',
      render: (calls: number) => formatNumber(calls),
    },
    {
      title: 'Token 消耗',
      dataIndex: 'tokens',
      key: 'tokens',
      render: (tokens: number) => formatNumber(tokens),
    },
    {
      title: '费用',
      dataIndex: 'cost',
      key: 'cost',
      render: (cost: number) => formatCurrency(cost),
      sorter: (a: ModelCost, b: ModelCost) => a.cost - b.cost,
    },
    {
      title: '平均成本/次',
      dataIndex: 'avg_cost',
      key: 'avg_cost',
      render: (cost: number) => formatCurrency(cost),
    },
  ];

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['cost-summary'] });
    queryClient.invalidateQueries({ queryKey: ['cost-usage'] });
    queryClient.invalidateQueries({ queryKey: ['cost-trends'] });
  };

  const handleExport = () => {
    // In a real implementation, this would trigger a download
    console.log('Exporting cost report...');
  };

  const tabItems = [
    {
      key: 'overview',
      label: '概览',
      children: (
        <Row gutter={[24, 24]}>
          {/* Daily Trend Chart */}
          <Col xs={24} lg={16}>
            <Card title="日成本趋势" bodyStyle={{ padding: 24 }}>
              {trends.length > 0 ? (
                <SimpleBarChart data={trends} />
              ) : (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Text type="secondary">暂无数据</Text>
                </div>
              )}
            </Card>
          </Col>

          {/* Cost Distribution */}
          <Col xs={24} lg={8}>
            <Card title="成本分布" bodyStyle={{ padding: 24 }}>
              {summary ? (
                <CostDistribution summary={summary} />
              ) : (
                <Spin />
              )}
            </Card>
          </Col>

          {/* Usage Detail Table */}
          <Col span={24}>
            <Card title="用量明细">
              <Table
                columns={usageColumns}
                dataSource={usage.map((item, index) => ({ ...item, key: index }))}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'by-model',
      label: '按模型',
      children: (
        <Card>
          <Table
            columns={modelColumns}
            dataSource={modelData.map((item, index) => ({ ...item, key: index }))}
            pagination={{
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </Card>
      ),
    },
    {
      key: 'records',
      label: '明细记录',
      children: (
        <Card>
          <Alert
            message="功能开发中"
            description="详细的调用记录功能正在开发中，敬请期待。"
            type="info"
            showIcon
          />
        </Card>
      ),
    },
  ];

  if (isLoading && !summary) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          <DollarOutlined style={{ marginRight: 8 }} />
          成本报告
        </Title>
        <Space>
          <Select value={period} onChange={setPeriod} style={{ width: 120 }}>
            <Option value={7}>近 7 天</Option>
            <Option value={14}>近 14 天</Option>
            <Option value={30}>近 30 天</Option>
            <Option value={90}>近 90 天</Option>
          </Select>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        </Space>
      </div>

      {/* Summary Cards */}
      {summary && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="总费用"
              value={formatCurrency(summary.total_cost)}
              subtitle={summary.period}
              icon={<DollarOutlined />}
              trend={summary.trend}
              color="#1890ff"
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="计算资源"
              value={formatCurrency(summary.compute_cost)}
              icon={<ThunderboltOutlined />}
              color="#52c41a"
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="存储费用"
              value={formatCurrency(summary.storage_cost)}
              icon={<FieldTimeOutlined />}
              color="#faad14"
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="API 调用"
              value={formatCurrency(summary.api_cost)}
              icon={<ApiOutlined />}
              color="#722ed1"
            />
          </Col>
        </Row>
      )}

      {/* Tabs */}
      <Card bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          tabBarStyle={{ padding: '0 24px', marginBottom: 0 }}
        />
      </Card>
    </div>
  );
}

export default CostReportPage;
