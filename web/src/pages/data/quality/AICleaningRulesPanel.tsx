import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Alert,
  Spin,
  Descriptions,
  Progress,
  Empty,
  List,
  Tooltip,
  Modal,
  Switch,
  Typography,
} from 'antd';
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { qualityAI } from '@/services/data';

const { Text } = Typography;

interface AICleaningRulesPanelProps {
  tableName?: string;
  databaseName?: string;
  columns?: Array<{ name: string; type: string; description?: string }>;
  onRuleApply?: (rule: any) => void;
  visible?: boolean;
  onClose?: () => void;
}

interface CleaningRecommendation {
  issue_type: string;
  issue_description: string;
  rule_type: string;
  rule_name: string;
  rule_config: Record<string, any>;
  priority: string;
  estimated_improvement: number;
}

interface RuleTemplate {
  rule_name: string;
  rule_type: string;
  target_column: string;
  expression: string;
  description: string;
  severity: string;
  priority: number;
}

function AICleaningRulesPanel({
  tableName,
  databaseName,
  columns = [],
  onRuleApply,
  visible = true,
  onClose,
}: AICleaningRulesPanelProps) {
  const queryClient = useQueryClient();

  // 状态管理
  const [activeTab, setActiveTab] = useState<'analyze' | 'templates'>('analyze');
  const [selectedRules, setSelectedRules] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CleaningRecommendation[] | null>(null);

  // AI 分析表质量
  const analyzeMutation = useMutation({
    mutationFn: () =>
      qualityAI.analyzeTable({
        table_name: tableName || '',
        database_name: databaseName,
      }),
    onSuccess: (data) => {
      if (data.data?.data?.recommendations) {
        setAnalysisResult(data.data.data.recommendations);
      }
    },
  });

  // 获取规则模板
  const {
    data: templatesData,
    isLoading: isLoadingTemplates,
    refetch: refetchTemplates,
  } = useQuery({
    queryKey: ['qualityAITemplates', tableName, columns],
    queryFn: () =>
      qualityAI.getRuleTemplates({
        table_name: tableName || '',
        columns,
      }),
    enabled: activeTab === 'templates' && !!tableName && columns.length > 0,
  });

  // 应用规则
  const applyRuleMutation = useMutation({
    mutationFn: async (rule: any) => {
      // 调用创建质量规则 API
      const response = await fetch('/api/v1/quality/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rule_name: rule.rule_name,
          rule_type: rule.rule_type,
          dimension: rule.rule_type,
          target_table: tableName,
          target_column: rule.target_column,
          rule_expression: rule.expression,
          severity: rule.severity,
          threshold: rule.threshold || 80,
          action: rule.action || 'alert',
        }),
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['qualityRules'] });
      if (onRuleApply) {
        onRuleApply(true);
      }
    },
  });

  // 处理 AI 分析
  const handleAnalyze = () => {
    if (!tableName) {
      Modal.warning({
        title: '缺少信息',
        content: '请先选择要分析的表',
      });
      return;
    }
    setIsAnalyzing(true);
    analyzeMutation.mutate(undefined, {
      onSettled: () => setIsAnalyzing(false),
    });
  };

  // 处理规则选择
  const handleRuleToggle = (ruleId: string) => {
    setSelectedRules((prev) =>
      prev.includes(ruleId) ? prev.filter((id) => id !== ruleId) : [...prev, ruleId]
    );
  };

  // 批量应用选中的规则
  const handleApplySelected = async () => {
    if (!analysisResult) return;

    const selectedData = analysisResult.filter((_, idx) =>
      selectedRules.includes(`rule-${idx}`)
    );

    for (const rule of selectedData) {
      try {
        await applyRuleMutation.mutateAsync(rule);
      } catch (error) {
        console.error('Failed to apply rule:', error);
      }
    }

    setSelectedRules([]);
  };

  // 获取优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'red';
      case 'high':
        return 'orange';
      case 'medium':
        return 'blue';
      case 'low':
        return 'default';
      default:
        return 'default';
    }
  };

  // 获取规则类型标签
  const getRuleTypeLabel = (ruleType: string) => {
    const labels: Record<string, string> = {
      completeness: '完整性',
      validity: '有效性',
      consistency: '一致性',
      uniqueness: '唯一性',
      security: '安全性',
      accuracy: '准确性',
    };
    return labels[ruleType] || ruleType;
  };

  // 分析结果表格列定义
  const analysisColumns = [
    {
      title: '选择',
      dataIndex: 'select',
      key: 'select',
      width: 60,
      render: (_: any, _record: CleaningRecommendation, index: number) => (
        <input
          type="checkbox"
          checked={selectedRules.includes(`rule-${index}`)}
          onChange={() => handleRuleToggle(`rule-${index}`)}
        />
      ),
    },
    {
      title: '问题类型',
      dataIndex: 'issue_type',
      key: 'issue_type',
      render: (type: string) => <Tag color="blue">{getRuleTypeLabel(type)}</Tag>,
    },
    {
      title: '问题描述',
      dataIndex: 'issue_description',
      key: 'issue_description',
      ellipsis: true,
    },
    {
      title: '推荐规则',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>{priority.toUpperCase()}</Tag>
      ),
    },
    {
      title: '预期改进',
      dataIndex: 'estimated_improvement',
      key: 'estimated_improvement',
      render: (value: number) => (
        <Progress percent={value * 100} size="small" format={(percent) => `${percent}%`} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: CleaningRecommendation) => (
        <Space size="small">
          <Tooltip title="应用此规则">
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => applyRuleMutation.mutate(record)}
            >
              应用
            </Button>
          </Tooltip>
          <Tooltip title="查看配置">
            <Button type="link" size="small" icon={<InfoCircleOutlined />}>
              详情
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 规则模板表格列定义
  const templateColumns = [
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => <Tag color="cyan">{getRuleTypeLabel(type)}</Tag>,
    },
    {
      title: '目标列',
      dataIndex: 'target_column',
      key: 'target_column',
    },
    {
      title: '规则表达式',
      dataIndex: 'expression',
      key: 'expression',
      ellipsis: true,
      render: (text: string) => (
        <code style={{ fontSize: '12px' }}>{text}</code>
      ),
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap: Record<string, string> = {
          error: 'red',
          warning: 'orange',
          info: 'blue',
        };
        return <Tag color={colorMap[severity] || 'default'}>{severity}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: RuleTemplate) => (
        <Button
          type="link"
          size="small"
          onClick={() => applyRuleMutation.mutate(record)}
        >
          添加
        </Button>
      ),
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <RobotOutlined />
          <span>AI 质量规则助手</span>
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
          onClick={() => {
            if (activeTab === 'templates') {
              refetchTemplates();
            } else {
              handleAnalyze();
            }
          }}
        >
          刷新
        </Button>,
        <Button
          type="primary"
          key="apply-selected"
          disabled={selectedRules.length === 0 || activeTab !== 'analyze'}
          onClick={handleApplySelected}
          loading={applyRuleMutation.isPending}
        >
          应用选中 ({selectedRules.length})
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 提示信息 */}
        <Alert
          message="AI 助手将分析表结构并推荐数据质量规则"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>基于列名、数据类型自动识别潜在质量问题</li>
              <li>推荐适合的校验规则和阈值</li>
              <li>提供一键应用规则到质量监控</li>
            </ul>
          }
          type="info"
          showIcon
        />

        {/* 表信息 */}
        {tableName && (
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="表名">{tableName}</Descriptions.Item>
            {databaseName && (
              <Descriptions.Item label="数据库">{databaseName}</Descriptions.Item>
            )}
            <Descriptions.Item label="列数量">{columns.length}</Descriptions.Item>
          </Descriptions>
        )}

        {/* 标签页 */}
        <Card
          tabList={[
            { key: 'analyze', tab: '智能分析', icon: <ThunderboltOutlined /> },
            { key: 'templates', tab: '规则模板', icon: <CheckCircleOutlined /> },
          ]}
          activeTabKey={activeTab}
          onTabChange={(key) => setActiveTab(key as 'analyze' | 'templates')}
        >
          {/* 分析结果 Tab */}
          {activeTab === 'analyze' && (
            <div>
              {!analysisResult ? (
                <Empty
                  description="点击下方按钮开始 AI 分析"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Button
                    type="primary"
                    icon={<RobotOutlined />}
                    onClick={handleAnalyze}
                    loading={isAnalyzing || analyzeMutation.isPending}
                    disabled={!tableName}
                  >
                    开始 AI 分析
                  </Button>
                </Empty>
              ) : (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Text strong>
                        发现 {analysisResult.length} 个潜在质量问题
                      </Text>
                      <Text type="secondary">
                        ({analysisResult.filter((r) => r.priority === 'critical').length} 个严重,
                        {analysisResult.filter((r) => r.priority === 'high').length} 个高优先级)
                      </Text>
                    </Space>
                  </div>
                  <Table
                    columns={analysisColumns}
                    dataSource={analysisResult}
                    rowKey={(record, idx) => `rule-${idx}`}
                    pagination={false}
                    size="small"
                  />
                </>
              )}
            </div>
          )}

          {/* 规则模板 Tab */}
          {activeTab === 'templates' && (
            <div>
              {isLoadingTemplates ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin tip="AI 正在生成规则模板..." />
                </div>
              ) : templatesData?.data?.data?.rules ? (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>
                      AI 推荐了 {templatesData.data.data.total || templatesData.data.data.rules.length} 条规则模板
                    </Text>
                  </div>
                  <Table
                    columns={templateColumns}
                    dataSource={templatesData.data.data.rules}
                    rowKey="rule_name"
                    pagination={false}
                    size="small"
                  />
                  </>
              ) : (
                <Empty
                  description={
                    !tableName || columns.length === 0
                      ? '请选择表后查看规则模板'
                      : '点击刷新生成规则模板'
                  }
                />
              )}
            </div>
          )}
        </Card>
      </Space>
    </Modal>
  );
}

export default AICleaningRulesPanel;
