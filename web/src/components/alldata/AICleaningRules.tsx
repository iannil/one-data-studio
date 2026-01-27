/**
 * AI 辅助数据质量规则配置组件
 * 智能分析数据质量问题并推荐清洗规则
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  List,
  Button,
  Tag,
  Space,
  Alert,
  Descriptions,
  Form,
  Select,
  Input,
  InputNumber,
  Switch,
  Modal,
  Tooltip,
  Progress,
  Empty,
  Spin,
  message,
  Tabs,
  Checkbox,
  Row,
  Col,
} from 'antd';
import {
  RobotOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  StarFilled,
  FilterOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient, { type ApiResponse } from '@/services/api';
import type { CleaningRecommendation } from '@/services/alldata';
import './AICleaningRules.css';

const { Option } = Select;
const { TextArea } = Input;

interface AICleaningRulesProps {
  tableName?: string;
  databaseName?: string;
  onRulesCreated?: (rules: any[]) => void;
}

interface RuleTemplate {
  category: string;
  rule_type: string;
  name: string;
  expression: string;
  severity: string;
  config_template: any;
}

export const AICleaningRules: React.FC<AICleaningRulesProps> = ({
  tableName,
  databaseName,
  onRulesCreated,
}) => {
  const queryClient = useQueryClient();
  const [analyzing, setAnalyzing] = useState(false);
  const [recommendations, setRecommendations] = useState<CleaningRecommendation[]>([]);
  const [selectedRecs, setSelectedRecs] = useState<Set<number>>(new Set());
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('recommend');

  const [form] = Form.useForm();

  // 获取规则模板
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['quality-rule-templates'],
    queryFn: () => apiClient.get<{ templates: RuleTemplate[]; total: number }>('/api/v1/quality/rule-templates'),
  });

  // 分析表质量问题
  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!tableName) {
        throw new Error('请先选择表');
      }

      setAnalyzing(true);
      const response = await apiClient.post<ApiResponse<{
        recommendations: CleaningRecommendation[];
        total_count: number;
      }>>('/api/v1/quality/analyze-table', {
        table_name: tableName,
        database_name: databaseName,
      });
      return response.data.data;
    },
    onSuccess: (data) => {
      setRecommendations(data.recommendations || []);
      setSelectedRecs(new Set());
      message.success(`分析完成，发现 ${data.total_count} 个潜在问题`);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '分析失败');
    },
    onSettled: () => {
      setAnalyzing(false);
    },
  });

  // 创建质量规则
  const createMutation = useMutation({
    mutationFn: async (rules: any[]) => {
      const response = await apiClient.post('/api/v1/quality/rules', {
        rules: rules.map(r => ({
          ...r,
          target_table: tableName,
          target_database: databaseName,
        })),
      });
      return response.data;
    },
    onSuccess: () => {
      message.success('规则创建成功');
      setCreateModalVisible(false);
      setSelectedRecs(new Set());
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      onRulesCreated?.(Array.from(selectedRecs).map(i => recommendations[i]));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建失败');
    },
  });

  const handleAnalyze = () => {
    analyzeMutation.mutate();
  };

  const handleSelectRec = (index: number, checked: boolean) => {
    const newSelected = new Set(selectedRecs);
    if (checked) {
      newSelected.add(index);
    } else {
      newSelected.delete(index);
    }
    setSelectedRecs(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedRecs.size === recommendations.length) {
      setSelectedRecs(new Set());
    } else {
      setSelectedRecs(new Set(recommendations.map((_, i) => i)));
    }
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      critical: 'red',
      high: 'orange',
      medium: 'blue',
      low: 'default',
    };
    return colors[priority] || 'default';
  };

  const getPriorityText = (priority: string) => {
    const texts = {
      critical: '紧急',
      high: '高',
      medium: '中',
      low: '低',
    };
    return texts[priority] || priority;
  };

  const getIssueTypeIcon = (issueType: string) => {
    const icons: Record<string, React.ReactNode> = {
      missing_values: <WarningOutlined style={{ color: '#faad14' }} />,
      duplicate_records: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
      invalid_format: <InfoCircleOutlined style={{ color: '#1677ff' }} />,
      out_of_range: <FileTextOutlined style={{ color: '#52c41a' }} />,
      sensitive_data: <WarningOutlined style={{ color: '#ff4d4f' }} />,
      dirty_data: <FilterOutlined style={{ color: '#8c8c8c' }} />,
    };
    return icons[issueType] || <InfoCircleOutlined />;
  };

  const getIssueTypeText = (issueType: string) => {
    const texts = {
      missing_values: '缺失值',
      duplicate_records: '重复记录',
      invalid_format: '格式无效',
      out_of_range: '超出范围',
      inconsistent_values: '值不一致',
      dirty_data: '脏数据',
      sensitive_data: '敏感数据',
    };
    return texts[issueType] || issueType;
  };

  // 过滤推荐
  const filteredRecommendations = recommendations.filter((rec) => {
    if (selectedCategory !== 'all' && rec.issue_type !== selectedCategory) {
      return false;
    }
    return true;
  });

  // 获取问题类型统计
  const getIssueStats = () => {
    const stats: Record<string, number> = {};
    recommendations.forEach((rec) => {
      stats[rec.issue_type] = (stats[rec.issue_type] || 0) + 1;
    });
    return stats;
  };

  // 处理创建规则
  const handleCreateRules = () => {
    if (selectedRecs.size === 0) {
      message.warning('请至少选择一个推荐规则');
      return;
    }

    const rulesToCreate = Array.from(selectedRecs).map((index) => {
      const rec = recommendations[index];
      return {
        name: rec.rule_name,
        description: rec.issue_description,
        rule_type: rec.rule_type,
        rule_expression: rec.rule_config.rule_expression || rec.rule_config.expression,
        target_table: tableName,
        target_column: rec.rule_config.target_column,
        threshold: rec.rule_config.threshold || 95,
        severity: rec.rule_config.severity || 'warning',
      };
    });

    form.validateFields().then((values) => {
      // 应用用户调整的配置
      const adjustedRules = rulesToCreate.map((rule) => ({
        ...rule,
        ...values,
      }));

      createMutation.mutate(adjustedRules);
    });
  };

  // 渲染推荐项
  const renderRecommendation = (rec: CleaningRecommendation, index: number) => {
    const isSelected = selectedRecs.has(index);

    return (
      <List.Item
        key={index}
        className={isSelected ? 'recommendation-item selected' : 'recommendation-item'}
        onClick={() => handleSelectRec(index, !isSelected)}
      >
        <List.Item.Meta
          avatar={
            <Checkbox
              checked={isSelected}
              onChange={(e) => {
                e.stopPropagation();
                handleSelectRec(index, e.target.checked);
              }}
            />
          }
          title={
            <Space>
              {getIssueTypeIcon(rec.issue_type)}
              <span>{rec.rule_name}</span>
              <Tag color={getPriorityColor(rec.priority)}>
                {getPriorityText(rec.priority)}
              </Tag>
              <Tag>{rec.rule_type}</Tag>
            </Space>
          }
          description={
            <div>
              <div style={{ marginBottom: 8 }}>{rec.issue_description}</div>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="规则类型">{rec.rule_type}</Descriptions.Item>
                <Descriptions.Item label="建议操作">{rec.rule_config.action || '-'}</Descriptions.Item>
                <Descriptions.Item label="阈值">{rec.rule_config.threshold}%</Descriptions.Item>
                <Descriptions.Item label="预期改进">{Math.round(rec.estimated_improvement * 100)}%</Descriptions.Item>
              </Descriptions>
            </div>
          }
        />
        <div className="recommendation-actions">
          <Tooltip title="预览规则配置">
            <Button
              type="text"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                Modal.info({
                  title: '规则配置详情',
                  width: 600,
                  content: (
                    <pre style={{ whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(rec.rule_config, null, 2)}
                    </pre>
                  ),
                });
              }}
            />
          </Tooltip>
        </div>
      </List.Item>
    );
  };

  return (
    <div className="ai-cleaning-rules">
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>AI 智能清洗规则推荐</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<StarFilled />}
              type="primary"
              loading={analyzing}
              onClick={handleAnalyze}
              disabled={!tableName}
            >
              {analyzing ? '分析中...' : '开始分析'}
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 推荐标签页 */}
          <Tabs.TabPane tab="智能推荐" key="recommend">
            {!tableName && (
              <Alert
                message="请先选择要分析的表"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {recommendations.length > 0 && (
              <>
                {/* 统计概览 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Space>
                        <span>共发现 <strong>{recommendations.length}</strong> 个问题</span>
                        <span>|</span>
                        <span>已选择 <strong>{selectedRecs.size}</strong> 个规则</span>
                      </Space>
                    </Col>
                    <Col span={12} style={{ textAlign: 'right' }}>
                      <Space>
                        <Checkbox
                          checked={selectedRecs.size === recommendations.length}
                          indeterminate={selectedRecs.size > 0 && selectedRecs.size < recommendations.length}
                          onChange={handleSelectAll}
                        >
                          全选
                        </Checkbox>
                        <Button
                          type="primary"
                          size="small"
                          icon={<PlusOutlined />}
                          disabled={selectedRecs.size === 0}
                          onClick={() => setCreateModalVisible(true)}
                        >
                          创建规则 ({selectedRecs.size})
                        </Button>
                      </Space>
                    </Col>
                  </Row>
                </Card>

                {/* 过滤器 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space>
                    <span>问题类型:</span>
                    <Select
                      value={selectedCategory}
                      onChange={setSelectedCategory}
                      style={{ width: 120 }}
                    >
                      <Option value="all">全部</Option>
                      <Option value="missing_values">缺失值</Option>
                      <Option value="duplicate_records">重复记录</Option>
                      <Option value="invalid_format">格式无效</Option>
                      <Option value="out_of_range">超出范围</Option>
                      <Option value="inconsistent_values">值不一致</Option>
                      <Option value="dirty_data">脏数据</Option>
                      <Option value="sensitive_data">敏感数据</Option>
                    </Select>
                  </Space>
                </Card>

                {/* 推荐列表 */}
                <List
                  dataSource={filteredRecommendations}
                  renderItem={(_, index) => {
                    // 找到原始索引
                    const originalIndex = recommendations.indexOf(filteredRecommendations[index]);
                    return renderRecommendation(filteredRecommendations[index], originalIndex);
                  }}
                />
              </>
            )}

            {recommendations.length === 0 && tableName && !analyzing && (
              <Empty
                description="点击「开始分析」按钮，AI 将自动检测表中的数据质量问题"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" icon={<StarFilled />} onClick={handleAnalyze}>
                  开始分析
                </Button>
              </Empty>
            )}
          </Tabs.TabPane>

          {/* 规则模板标签页 */}
          <Tabs.TabPane tab="规则模板" key="templates">
            {templatesLoading ? (
              <Spin />
            ) : (
              <List
                dataSource={templatesData?.data?.templates || []}
                renderItem={(template: RuleTemplate) => (
                  <List.Item
                    className="template-item"
                    actions={[
                      <Button
                        type="primary"
                        size="small"
                        onClick={() => {
                          form.setFieldsValue({
                            rule_type: template.rule_type,
                            rule_expression: template.expression,
                            severity: template.severity,
                          });
                          setActiveTab('manual');
                        }}
                      >
                        使用此模板
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <span>{template.name}</span>
                          <Tag color="blue">{template.rule_type}</Tag>
                          <Tag>{template.category}</Tag>
                        </Space>
                      }
                      description={
                        <code style={{ fontSize: 12, background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                          {template.expression}
                        </code>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Tabs.TabPane>

          {/* 手动配置标签页 */}
          <Tabs.TabPane tab="手动配置" key="manual">
            <Form
              form={form}
              layout="vertical"
              onFinish={(values) => {
                createMutation.mutate([values]);
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="规则名称"
                    name="name"
                    rules={[{ required: true, message: '请输入规则名称' }]}
                  >
                    <Input placeholder="例如：用户名非空检查" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="规则类型"
                    name="rule_type"
                    rules={[{ required: true, message: '请选择规则类型' }]}
                  >
                    <Select placeholder="选择规则类型">
                      <Option value="completeness">完整性</Option>
                      <Option value="uniqueness">唯一性</Option>
                      <Option value="validity">有效性</Option>
                      <Option value="accuracy">准确性</Option>
                      <Option value="consistency">一致性</Option>
                      <Option value="timeliness">及时性</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="规则表达式"
                name="rule_expression"
                rules={[{ required: true, message: '请输入规则表达式' }]}
              >
                <TextArea
                  rows={3}
                  placeholder='例如: {column} IS NOT NULL 或 COUNT(*) OVER (PARTITION BY {column}) = 1'
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="目标列"
                    name="target_column"
                  >
                    <Input placeholder="列名" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="通过阈值 (%)"
                    name="threshold"
                    initialValue={95}
                  >
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="严重程度"
                    name="severity"
                    initialValue="warning"
                  >
                    <Select>
                      <Option value="info">信息</Option>
                      <Option value="warning">警告</Option>
                      <Option value="error">错误</Option>
                      <Option value="critical">紧急</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                  创建规则
                </Button>
              </Form.Item>
            </Form>
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 创建规则确认弹窗 */}
      <Modal
        title="确认创建规则"
        open={createModalVisible}
        onOk={handleCreateRules}
        onCancel={() => setCreateModalVisible(false)}
        width={700}
      >
        <Alert
          message={`即将创建 ${selectedRecs.size} 条质量规则`}
          description="请确认规则配置无误后点击确定"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form form={form} layout="vertical">
          <Form.Item label="全局阈值调整 (%)" name="threshold_adjustment">
            <InputNumber min={0} max={100} placeholder="不调整" style={{ width: 200 }} />
          </Form.Item>
        </Form>

        <List
          size="small"
          dataSource={Array.from(selectedRecs).map((i) => recommendations[i])}
          renderItem={(rec) => (
            <List.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <span>{rec.rule_name}</span>
                  <Tag color={getPriorityColor(rec.priority)}>{getPriorityText(rec.priority)}</Tag>
                </Space>
                <div style={{ fontSize: 12, color: '#666' }}>{rec.issue_description}</div>
              </Space>
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default AICleaningRules;
