import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Space,
  Button,
  Alert,
  Spin,
  Empty,
  List,
  Descriptions,
  Tooltip,
  Modal,
  Typography,
  Timeline,
} from 'antd';
import {
  TrophyOutlined,
  StarOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assetsAI } from '@/services/alldata';
import React from 'react';

const { Text } = Typography;

interface AIAssetValuePanelProps {
  assetId?: string;
  assetName?: string;
  onRefresh?: () => void;
  visible?: boolean;
  onClose?: () => void;
}

interface ValueScoreBreakdown {
  usage_score: number;
  business_score: number;
  quality_score: number;
  governance_score: number;
  overall_score: number;
}

interface AssetValueAssessmentResponse {
  asset_id: string;
  asset_name: string;
  score_breakdown: ValueScoreBreakdown;
  value_level: 'S' | 'A' | 'B' | 'C';
  level_name: string;
  details: {
    usage: Record<string, unknown>;
    business: Record<string, unknown>;
    quality: Record<string, unknown>;
    governance: Record<string, unknown>;
  };
  recommendations: string[];
}

// 价值等级配置
const VALUE_LEVEL_CONFIG = {
  S: { level: 'S', name: '战略级', color: '#f5222d', minScore: 80, icon: <TrophyOutlined /> },
  A: { level: 'A', name: '核心级', color: '#fa8c16', minScore: 60, icon: <StarOutlined /> },
  B: { level: 'B', name: '重要级', color: '#52c41a', minScore: 40, icon: <LineChartOutlined /> },
  C: { level: 'C', name: '基础级', color: '#1890ff', minScore: 0, icon: <InfoCircleOutlined /> },
};

function AIAssetValuePanel({
  assetId,
  assetName,
  onRefresh,
  visible = true,
  onClose,
}: AIAssetValuePanelProps) {
  const queryClient = useQueryClient();

  // AI 价值评估
  const { data: assessmentData, isLoading, refetch } = useQuery({
    queryKey: ['assetsAIValueAssess', assetId],
    queryFn: () => assetsAI.assessValue({ asset_id: assetId || '' }),
    enabled: !!assetId && visible,
  });

  // 刷新评估
  const refreshMutation = useMutation({
    mutationFn: () => refetch(),
    onSuccess: () => {
      if (onRefresh) onRefresh();
    },
  });

  // 获取当前价值等级配置
  const getCurrentLevelConfig = (score: number) => {
    const level = Object.entries(VALUE_LEVEL_CONFIG).find(
      ([_, config]) => score >= config.minScore
    );
    return level ? VALUE_LEVEL_CONFIG[level[0]] : VALUE_LEVEL_CONFIG.C;
  };

  // 计算雷达图数据
  const getRadarData = (breakdown: ValueScoreBreakdown) => {
    return [
      { name: '使用度', value: breakdown.usage_score, fullMark: 100 },
      { name: '业务度', value: breakdown.business_score, fullMark: 100 },
      { name: '质量度', value: breakdown.quality_score, fullMark: 100 },
      { name: '治理度', value: breakdown.governance_score, fullMark: 100 },
    ];
  };

  // 获取评分颜色
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#1890ff';
    if (score >= 40) return '#fa8c16';
    return '#ff4d4f';
  };

  const assessment = assessmentData?.data?.data;
  const levelConfig = assessment
    ? getCurrentLevelConfig(assessment.score_breakdown.overall_score)
    : null;

  return (
    <Modal
      title={
        <Space>
          <TrophyOutlined />
          <span>AI 资产价值评估</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="refresh"
          icon={<RiseOutlined />}
          onClick={() => refreshMutation.mutate()}
          loading={refreshMutation.isPending}
        >
          刷新评估
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 提示信息 */}
        <Alert
          message="AI 助手将基于多个维度综合评估资产价值"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>使用度：基于访问量、活跃用户、下游依赖</li>
              <li>业务度：基于 SLA 级别、业务域重要性、核心指标</li>
              <li>质量度：基于完整性、准确性、一致性</li>
              <li>治理度：基于标签完整性、元数据丰富度</li>
            </ul>
          }
          type="info"
          showIcon
        />

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="AI 正在评估资产价值..." />
          </div>
        ) : assessment ? (
          <>
            {/* 价值等级展示 */}
            <Row gutter={16}>
              <Col span={12}>
                <Card>
                  <div style={{ textAlign: 'center', padding: 20 }}>
                    {levelConfig && (
                      <>
                        <div
                          style={{
                            fontSize: 80,
                            color: levelConfig.color,
                            marginBottom: 16,
                          }}
                        >
                          {levelConfig.icon}
                        </div>
                        <div style={{ fontSize: 32, fontWeight: 'bold' }}>
                          {levelConfig.level} 级
                        </div>
                        <div style={{ fontSize: 16, color: '#888' }}>
                          {levelConfig.name}
                        </div>
                      </>
                    )}
                    </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="综合评分" extra={<Tag color="processing">AI评估</Tag>}>
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Statistic
                        title="综合得分"
                        value={assessment.score_breakdown.overall_score}
                        precision={1}
                        suffix="/ 100"
                        valueStyle={{
                          color: getScoreColor(assessment.score_breakdown.overall_score),
                          fontSize: 32,
                        }}
                      />
                    </Col>
                    <Col span={12}>
                      <div>
                        <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>评级标准</div>
                        <div style={{ fontSize: 12 }}>
                          <div>S级: 80+ 分</div>
                          <div>A级: 60-79 分</div>
                          <div>B级: 40-59 分</div>
                          <div>C级: &lt; 40 分</div>
                        </div>
                      </div>
                    </Col>
                  </Row>
                </Card>
              </Col>
            </Row>

            {/* 详细评分 */}
            <Row gutter={16}>
              <Col span={12}>
                <Card title="评分详情">
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>使用度</Text>
                        <Text strong>{assessment.score_breakdown.usage_score.toFixed(1)}</Text>
                      </div>
                      <Progress
                        percent={assessment.score_breakdown.usage_score}
                        strokeColor={getScoreColor(assessment.score_breakdown.usage_score)}
                        size="small"
                      />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>业务度</Text>
                        <Text strong>{assessment.score_breakdown.business_score.toFixed(1)}</Text>
                      </div>
                      <Progress
                        percent={assessment.score_breakdown.business_score}
                        strokeColor={getScoreColor(assessment.score_breakdown.business_score)}
                        size="small"
                      />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>质量度</Text>
                        <Text strong>{assessment.score_breakdown.quality_score.toFixed(1)}</Text>
                      </div>
                      <Progress
                        percent={assessment.score_breakdown.quality_score}
                        strokeColor={getScoreColor(assessment.score_breakdown.quality_score)}
                        size="small"
                      />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>治理度</Text>
                        <Text strong>{assessment.score_breakdown.governance_score.toFixed(1)}</Text>
                      </div>
                      <Progress
                        percent={assessment.score_breakdown.governance_score}
                        strokeColor={getScoreColor(assessment.score_breakdown.governance_score)}
                        size="small"
                      />
                    </div>
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="雷达图分析">
                  <div style={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ flex: 1, height: 250 }}>
                      {React.createElement(require('recharts').RadarChart, {
                        width: 280,
                        height: 250,
                        data: getRadarData(assessment.score_breakdown),
                      },
                      React.createElement(require('recharts').PolarAngleAxis, {
                        dataKey: 'name',
                        tick: { fill: '#888', fontSize: 12 },
                      }),
                      React.createElement(require('recharts').PolarRadiusAxis, {
                        angle: 90,
                        domain: [0, 100],
                        tick: { fill: '#888', fontSize: 12 },
                      }),
                      React.createElement(require('recharts').Radar, {
                        name: '价值评估',
                        dataKey: 'value',
                        stroke: '#1890ff',
                        fill: '#1890ff',
                        fillOpacity: 0.2,
                      })
                      )}
                    </div>
                  </div>
                </Card>
              </Col>
            </Row>

            {/* 优化建议 */}
            {assessment.recommendations && assessment.recommendations.length > 0 && (
              <Card title="优化建议" size="small">
                <List
                  size="small"
                  dataSource={assessment.recommendations}
                  renderItem={(recommendation: string) => (
                    <List.Item>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        <Text>{recommendation}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </>
        ) : (
          <Empty
            description={assetId ? '点击刷新开始评估' : '请先选择资产'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {assetId && (
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={() => refreshMutation.mutate()}
              >
                开始评估
              </Button>
            )}
          </Empty>
        )}
      </Space>
    </Modal>
  );
}

export default AIAssetValuePanel;
