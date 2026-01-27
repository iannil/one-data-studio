import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Table,
  Select,
  Space,
  Button,
  Tooltip,
  Empty,
  Spin,
  Alert,
} from 'antd';
import {
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  StarFilled,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAssetValueReport,
  getAssetValueRanking,
  evaluateAssetValue,
  batchEvaluateAssetValues,
  type AssetValueLevel,
  type AssetValueRanking,
  type AssetValueReport,
} from '@/services/alldata';

const { Option } = Select;

interface AssetValuePanelProps {
  onAssetSelect?: (assetId: string) => void;
}

const VALUE_LEVEL_CONFIG: Record<
  AssetValueLevel,
  { color: string; label: string; description: string }
> = {
  S: { color: '#722ed1', label: 'S级 (战略级)', description: '核心战略资产，需重点保护' },
  A: { color: '#1890ff', label: 'A级 (核心级)', description: '重要业务资产，高价值' },
  B: { color: '#52c41a', label: 'B级 (重要级)', description: '常用业务资产，中等价值' },
  C: { color: '#999', label: 'C级 (基础级)', description: '基础数据资产，待提升' },
};

export function AssetValuePanel({ onAssetSelect }: AssetValuePanelProps) {
  const queryClient = useQueryClient();
  const [levelFilter, setLevelFilter] = useState<AssetValueLevel | undefined>();
  const [typeFilter, setTypeFilter] = useState<string | undefined>();

  // 获取价值报告
  const { data: reportData, isLoading: isLoadingReport } = useQuery({
    queryKey: ['asset-value-report'],
    queryFn: () => getAssetValueReport(),
  });

  // 获取排名列表
  const { data: rankingData, isLoading: isLoadingRanking } = useQuery({
    queryKey: ['asset-value-ranking', levelFilter, typeFilter],
    queryFn: () =>
      getAssetValueRanking({
        limit: 50,
        value_level: levelFilter,
        asset_type: typeFilter,
      }),
  });

  // 批量评估
  const batchEvaluateMutation = useMutation({
    mutationFn: batchEvaluateAssetValues,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-value-report'] });
      queryClient.invalidateQueries({ queryKey: ['asset-value-ranking'] });
    },
  });

  const report = reportData?.data;
  const ranking = rankingData?.data?.ranking || [];

  const renderValueLevelTag = (level: AssetValueLevel) => {
    const config = VALUE_LEVEL_CONFIG[level];
    return (
      <Tooltip title={config.description}>
        <Tag color={config.color} style={{ fontWeight: 'bold' }}>
          {level}
        </Tag>
      </Tooltip>
    );
  };

  const renderTrendIcon = (direction: 'up' | 'down' | 'stable') => {
    switch (direction) {
      case 'up':
        return <RiseOutlined style={{ color: '#52c41a' }} />;
      case 'down':
        return <FallOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <MinusOutlined style={{ color: '#999' }} />;
    }
  };

  const rankingColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      render: (rank: number) => {
        if (rank <= 3) {
          const colors = ['#ffd700', '#c0c0c0', '#cd7f32'];
          return (
            <span style={{ color: colors[rank - 1], fontWeight: 'bold' }}>
              <TrophyOutlined /> {rank}
            </span>
          );
        }
        return rank;
      },
    },
    {
      title: '资产名称',
      dataIndex: 'asset_name',
      key: 'asset_name',
      render: (name: string, record: AssetValueRanking) => (
        <a onClick={() => onAssetSelect?.(record.asset_id)}>{name}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'asset_type',
      key: 'asset_type',
      width: 80,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '价值等级',
      dataIndex: 'value_level',
      key: 'value_level',
      width: 100,
      render: (level: AssetValueLevel) => renderValueLevelTag(level),
    },
    {
      title: '综合评分',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 120,
      render: (score: number) => (
        <Progress
          percent={Math.round(score)}
          size="small"
          status={score >= 80 ? 'success' : score >= 60 ? 'normal' : 'exception'}
          format={(p) => `${p}`}
        />
      ),
    },
    {
      title: '使用',
      dataIndex: 'usage_score',
      key: 'usage_score',
      width: 60,
      render: (score: number) => (
        <Tooltip title="使用频率评分">
          <span>{Math.round(score)}</span>
        </Tooltip>
      ),
    },
    {
      title: '业务',
      dataIndex: 'business_score',
      key: 'business_score',
      width: 60,
      render: (score: number) => (
        <Tooltip title="业务重要度评分">
          <span>{Math.round(score)}</span>
        </Tooltip>
      ),
    },
    {
      title: '质量',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 60,
      render: (score: number) => (
        <Tooltip title="数据质量评分">
          <span>{Math.round(score)}</span>
        </Tooltip>
      ),
    },
    {
      title: '治理',
      dataIndex: 'governance_score',
      key: 'governance_score',
      width: 60,
      render: (score: number) => (
        <Tooltip title="治理成熟度评分">
          <span>{Math.round(score)}</span>
        </Tooltip>
      ),
    },
  ];

  if (isLoadingReport) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: '#999' }}>加载价值报告中...</div>
      </div>
    );
  }

  if (!report) {
    return (
      <Empty description="暂无价值评估数据">
        <Button
          type="primary"
          onClick={() => batchEvaluateMutation.mutate({ asset_ids: [] })}
          loading={batchEvaluateMutation.isPending}
        >
          开始评估
        </Button>
      </Empty>
    );
  }

  return (
    <div>
      {/* 概览统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已评估资产"
              value={report.statistics.total_assets}
              suffix="个"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="平均评分"
              value={report.statistics.average_score}
              precision={1}
              suffix="分"
              valueStyle={{ color: report.statistics.average_score >= 60 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="最高评分"
              value={report.statistics.max_score}
              precision={1}
              suffix="分"
              prefix={<StarFilled style={{ color: '#ffd700' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="最低评分"
              value={report.statistics.min_score}
              precision={1}
              suffix="分"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 价值等级分布 */}
      <Card title="价值等级分布" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          {(['S', 'A', 'B', 'C'] as AssetValueLevel[]).map((level) => {
            const config = VALUE_LEVEL_CONFIG[level];
            const count = report.distribution.counts[level] || 0;
            const percent = report.distribution.percentages[level] || 0;
            return (
              <Col span={6} key={level}>
                <div
                  style={{
                    textAlign: 'center',
                    padding: '16px',
                    background: `${config.color}10`,
                    borderRadius: 8,
                  }}
                >
                  <div
                    style={{
                      fontSize: 32,
                      fontWeight: 'bold',
                      color: config.color,
                    }}
                  >
                    {count}
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Tag color={config.color}>{config.label}</Tag>
                  </div>
                  <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                    占比 {percent.toFixed(1)}%
                  </div>
                </div>
              </Col>
            );
          })}
        </Row>
      </Card>

      {/* 维度平均分 */}
      <Card title="维度评分分析" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#999' }}>使用频率</span>
              <Tooltip title="衡量资产被访问和使用的频率">
                <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
              </Tooltip>
            </div>
            <Progress
              percent={Math.round(report.dimension_averages.usage)}
              size="small"
              strokeColor="#1890ff"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#999' }}>业务重要度</span>
              <Tooltip title="衡量资产对业务的重要程度">
                <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
              </Tooltip>
            </div>
            <Progress
              percent={Math.round(report.dimension_averages.business)}
              size="small"
              strokeColor="#722ed1"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#999' }}>数据质量</span>
              <Tooltip title="衡量数据的完整性、准确性、一致性、时效性">
                <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
              </Tooltip>
            </div>
            <Progress
              percent={Math.round(report.dimension_averages.quality)}
              size="small"
              strokeColor="#52c41a"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#999' }}>治理成熟度</span>
              <Tooltip title="衡量资产的元数据完善程度、血缘关系、质量规则等">
                <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
              </Tooltip>
            </div>
            <Progress
              percent={Math.round(report.dimension_averages.governance)}
              size="small"
              strokeColor="#fa8c16"
            />
          </Col>
        </Row>
      </Card>

      {/* 价值排名 */}
      <Card
        title="资产价值排名"
        size="small"
        extra={
          <Space>
            <Select
              placeholder="价值等级"
              allowClear
              style={{ width: 120 }}
              value={levelFilter}
              onChange={setLevelFilter}
            >
              <Option value="S">S级</Option>
              <Option value="A">A级</Option>
              <Option value="B">B级</Option>
              <Option value="C">C级</Option>
            </Select>
            <Select
              placeholder="资产类型"
              allowClear
              style={{ width: 100 }}
              value={typeFilter}
              onChange={setTypeFilter}
            >
              <Option value="table">表</Option>
              <Option value="database">数据库</Option>
              <Option value="column">字段</Option>
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['asset-value-ranking'] });
              }}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={rankingColumns}
          dataSource={ranking}
          rowKey="asset_id"
          loading={isLoadingRanking}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          size="small"
        />
      </Card>

      {/* 改进建议 */}
      {report.distribution.counts.C > 0 && (
        <Alert
          style={{ marginTop: 16 }}
          message="价值提升建议"
          description={
            <div>
              <p>
                当前有 <strong>{report.distribution.counts.C}</strong>{' '}
                个C级资产，建议重点关注以下方面：
              </p>
              <ul style={{ marginBottom: 0 }}>
                <li>为资产添加业务负责人和详细描述</li>
                <li>建立数据血缘关系，提升可追溯性</li>
                <li>配置数据质量规则，持续监控数据质量</li>
                <li>提升资产曝光度，增加使用频率</li>
              </ul>
            </div>
          }
          type="info"
          showIcon
        />
      )}
    </div>
  );
}

export default AssetValuePanel;
