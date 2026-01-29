/**
 * 智能预警推送组件
 * 支持 AI 异常检测、预警规则配置、多通道推送、预警订阅管理
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Space,
  Select,
  Input,
  Alert,
  Tag,
  Progress,
  Descriptions,
  Modal,
  Tooltip,
  Statistic,
  Row,
  Col,
  List,
  Empty,
  Spin,
  message,
  Tabs,
  Badge,
  Switch,
  Form,
  InputNumber,
  Divider,
  Steps,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SendOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
  MailOutlined,
  WechatOutlined,
  DingdingOutlined,
  MobileOutlined,
  ApiOutlined,
  RadarChartOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  detectAnomalies,
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  getAlertChannels,
  addAlertChannel,
  updateAlertChannel,
  removeAlertChannel,
  testAlertChannel,
  getAlertHistory,
  getAlertStatistics,
  getAlertSubscriptions,
  createAlertSubscription,
  updateAlertSubscription,
  deleteAlertSubscription,
  getAvailableAlertTypes,
} from '@/services/data';
import type {
  AnomalyDetectionResult,
  AlertRule,
  AlertChannel,
  AlertHistoryItem,
  AlertStatistics,
  AlertSubscription,
  AlertType,
} from '@/services/data';
import './SmartAlerts.css';

// 通道配置接口
interface AlertChannelConfig {
  channel_type: AlertChannel;
  name: string;
  enabled: boolean;
  config?: Record<string, unknown>;
  last_used?: string;
}

const { TextArea } = Input;
const { Option } = Select;
const { Step } = Steps;

interface SmartAlertsProps {
  tenantId?: string;
}

export const SmartAlerts: React.FC<SmartAlertsProps> = ({ tenantId = 'default' }) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('detection');
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [channelModalVisible, setChannelModalVisible] = useState(false);
  const [subscriptionModalVisible, setSubscriptionModalVisible] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AlertRule | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<AlertChannelConfig | null>(null);
  const [selectedSubscription, setSelectedSubscription] = useState<AlertSubscription | null>(null);

  const [form] = Form.useForm();
  const [channelForm] = Form.useForm();
  const [subscriptionForm] = Form.useForm();

  // 获取预警统计
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['alert-statistics'],
    queryFn: () => getAlertStatistics(30),
  });

  // 获取预警规则
  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => getAlertRules(),
  });

  // 获取预警通道
  const { data: channelsData, isLoading: channelsLoading } = useQuery({
    queryKey: ['alert-channels'],
    queryFn: () => getAlertChannels(true),
  });

  // 获取预警历史
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['alert-history'],
    queryFn: () => getAlertHistory({ limit: 20 }),
  });

  // 获取用户订阅
  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['alert-subscriptions'],
    queryFn: () => getAlertSubscriptions(),
  });

  // 获取可订阅的预警类型
  const { data: alertTypesData } = useQuery({
    queryKey: ['alert-types'],
    queryFn: () => getAvailableAlertTypes(),
  });

  // 异常检测
  const detectMutation = useMutation({
    mutationFn: (params: { detection_types?: string[]; time_window_hours?: number }) =>
      detectAnomalies(params),
    onSuccess: (data) => {
      const result = data?.data;
      if (result) {
        message.success(`检测完成，发现 ${result.total_anomalies} 个异常`);
      }
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '异常检测失败');
    },
  });

  // 创建预警规则
  const createRuleMutation = useMutation({
    mutationFn: createAlertRule,
    onSuccess: () => {
      message.success('规则创建成功');
      setRuleModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建失败');
    },
  });

  // 更新预警规则
  const updateRuleMutation = useMutation({
    mutationFn: ({ ruleId, updates }: { ruleId: string; updates: Partial<AlertRule> }) =>
      updateAlertRule(ruleId, updates),
    onSuccess: () => {
      message.success('规则更新成功');
      setRuleModalVisible(false);
      setSelectedRule(null);
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '更新失败');
    },
  });

  // 删除预警规则
  const deleteRuleMutation = useMutation({
    mutationFn: deleteAlertRule,
    onSuccess: () => {
      message.success('规则删除成功');
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败');
    },
  });

  // 测试预警通道
  const testChannelMutation = useMutation({
    mutationFn: (channelType: string) => testAlertChannel(channelType),
    onSuccess: () => {
      message.success('通道测试成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '测试失败');
    },
  });

  // 创建订阅
  const createSubscriptionMutation = useMutation({
    mutationFn: createAlertSubscription,
    onSuccess: () => {
      message.success('订阅创建成功');
      setSubscriptionModalVisible(false);
      subscriptionForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['alert-subscriptions'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建失败');
    },
  });

  // 删除订阅
  const deleteSubscriptionMutation = useMutation({
    mutationFn: deleteAlertSubscription,
    onSuccess: () => {
      message.success('订阅删除成功');
      queryClient.invalidateQueries({ queryKey: ['alert-subscriptions'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败');
    },
  });

  const stats = statsData?.data;
  const rules = rulesData?.data?.rules || [];
  const channels = (channelsData?.data?.channels || []) as unknown as AlertChannelConfig[];
  const history = historyData?.data?.history || [];
  const subscriptions = subscriptionsData?.data?.subscriptions || [];
  const alertTypes = alertTypesData?.data?.types || [];

  const handleDetectAnomalies = () => {
    detectMutation.mutate({ time_window_hours: 24 });
  };

  const handleCreateRule = () => {
    setSelectedRule(null);
    form.resetFields();
    setRuleModalVisible(true);
  };

  const handleEditRule = (rule: AlertRule) => {
    setSelectedRule(rule);
    form.setFieldsValue(rule);
    setRuleModalVisible(true);
  };

  const handleDeleteRule = (ruleId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条预警规则吗？',
      onOk: () => deleteRuleMutation.mutate(ruleId),
    });
  };

  const handleRuleSubmit = (values: any) => {
    if (selectedRule) {
      updateRuleMutation.mutate({
        ruleId: selectedRule.rule_id,
        updates: values,
      });
    } else {
      createRuleMutation.mutate(values);
    }
  };

  const handleTestChannel = (channelType: string) => {
    testChannelMutation.mutate(channelType);
  };

  const handleToggleChannel = (channel: AlertChannelConfig) => {
    updateChannel(channel.channel_type, { enabled: !channel.enabled });
  };

  const updateChannel = (channelType: string, updates: Partial<AlertChannelConfig>) => {
    // Simplified - in production would call the API
    const updatedChannels = channels.map((c) =>
      c.channel_type === channelType ? { ...c, ...updates } : c
    );
    queryClient.setQueryData(['alert-channels'], { data: { channels: updatedChannels, total: updatedChannels.length } });
    message.success('通道更新成功');
  };

  const handleCreateSubscription = () => {
    setSelectedSubscription(null);
    subscriptionForm.resetFields();
    setSubscriptionModalVisible(true);
  };

  const handleDeleteSubscription = (subscriptionId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要取消这个订阅吗？',
      onOk: () => deleteSubscriptionMutation.mutate(subscriptionId),
    });
  };

  const handleSubscriptionSubmit = (values: any) => {
    createSubscriptionMutation.mutate(values);
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: '#ff4d4f',
      error: '#ff4d4f',
      warning: '#faad14',
      info: '#1677ff',
    };
    return colors[severity] || '#999';
  };

  const getSeverityTag = (severity: string) => {
    const tags: Record<string, string> = {
      critical: 'error',
      error: 'error',
      warning: 'warning',
      info: 'processing',
    };
    return tags[severity] || 'default';
  };

  const getChannelIcon = (channelType: string) => {
    const icons: Record<string, React.ReactNode> = {
      email: <MailOutlined />,
      sms: <MobileOutlined />,
      webhook: <ApiOutlined />,
      wechat: <WechatOutlined style={{ color: '#00D768' }} />,
      dingtalk: <DingdingOutlined style={{ color: '#0089FF' }} />,
    };
    return icons[channelType] || <BellOutlined />;
  };

  const getChannelTypeText = (channelType: string) => {
    const texts: Record<string, string> = {
      email: '邮件',
      sms: '短信',
      webhook: 'Webhook',
      wechat: '企业微信',
      dingtalk: '钉钉',
    };
    return texts[channelType] || channelType;
  };

  // 规则列表表格列
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: AlertRule) => (
        <Space>
          <span>{text}</span>
          {record.enabled ? (
            <Badge status="success" text="启用" />
          ) : (
            <Badge status="default" text="禁用" />
          )}
        </Space>
      ),
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityTag(severity)}>{severity}</Tag>
      ),
    },
    {
      title: '推送通道',
      dataIndex: 'channels',
      key: 'channels',
      render: (channels: string[]) => (
        <Space size={4}>
          {channels.map((c) => (
            <Tooltip key={c} title={getChannelTypeText(c)}>
              {getChannelIcon(c)}
            </Tooltip>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: AlertRule) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRule(record)}
          />
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteRule(record.rule_id)}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="smart-alerts">
      <Card
        title={
          <Space>
            <BellOutlined />
            <span>智能预警推送</span>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 异常检测标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <RadarChartOutlined />
                <span>异常检测</span>
              </Space>
            }
            key="detection"
          >
            {/* 统计概览 */}
            {stats && (
              <Card size="small" title="预警概览" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="总预警数"
                      value={stats.total_alerts}
                      prefix={<ExclamationCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="严重告警"
                      value={stats.by_severity.critical || 0}
                      valueStyle={{ color: '#ff4d4f' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="警告告警"
                      value={stats.by_severity.warning || 0}
                      valueStyle={{ color: '#faad14' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="信息告警"
                      value={stats.by_severity.info || 0}
                      valueStyle={{ color: '#1677ff' }}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 检测控制 */}
            <Card size="small" title="AI 异常检测" style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  message="智能异常检测"
                  description="AI 将自动分析数据质量指标、任务执行状态、数据量变化等，检测潜在异常模式"
                  type="info"
                  showIcon
                  icon={<RobotOutlined />}
                />
                <Space>
                  <Button
                    type="primary"
                    icon={<ThunderboltOutlined />}
                    loading={detectMutation.isPending}
                    onClick={handleDetectAnomalies}
                  >
                    开始检测
                  </Button>
                  <Select
                    placeholder="检测类型"
                    style={{ width: 200 }}
                    mode="multiple"
                    defaultValue={["data_quality_spike", "task_failure_pattern"]}
                  >
                    <Option value="data_quality_spike">数据质量突增</Option>
                    <Option value="task_failure_pattern">任务失败模式</Option>
                    <Option value="data_drift">数据漂移</Option>
                    <Option value="volume_anomaly">数据量异常</Option>
                  </Select>
                  <Select placeholder="时间窗口" style={{ width: 120 }} defaultValue={24}>
                    <Option value={1}>1 小时</Option>
                    <Option value={6}>6 小时</Option>
                    <Option value={24}>24 小时</Option>
                    <Option value={72}>3 天</Option>
                    <Option value={168}>7 天</Option>
                  </Select>
                </Space>
              </Space>
            </Card>

            {/* 预警历史 */}
            <Card size="small" title="最近预警">
              {historyLoading ? (
                <Spin />
              ) : history.length > 0 ? (
                <List
                  dataSource={history}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button type="link" size="small">
                          查看详情
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          item.severity === 'critical' || item.severity === 'error' ? (
                            <CloseCircleOutlined style={{ fontSize: 24, color: getSeverityColor(item.severity) }} />
                          ) : (
                            <WarningOutlined style={{ fontSize: 24, color: getSeverityColor(item.severity) }} />
                          )
                        }
                        title={
                          <Space>
                            <span>{item.title}</span>
                            <Tag color={getSeverityTag(item.severity)}>{item.severity}</Tag>
                          </Space>
                        }
                        description={
                          <Space>
                            <ClockCircleOutlined />
                            <span>{item.created_at}</span>
                            <span>·</span>
                            <span>{item.description}</span>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无预警历史" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Tabs.TabPane>

          {/* 预警规则标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <SettingOutlined />
                <span>预警规则</span>
                <Badge count={rules.length} />
              </Space>
            }
            key="rules"
          >
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRule}>
                新建规则
              </Button>
            </div>

            {rulesLoading ? (
              <Spin />
            ) : rules.length > 0 ? (
              <Table
                columns={ruleColumns}
                dataSource={rules}
                rowKey="rule_id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无预警规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>

          {/* 预警通道标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <SendOutlined />
                <span>推送通道</span>
              </Space>
            }
            key="channels"
          >
            <Row gutter={16}>
              {channels.map((channel) => (
                <Col span={12} key={channel.channel_type}>
                  <Card
                    size="small"
                    title={
                      <Space>
                        {getChannelIcon(channel.channel_type)}
                        <span>{channel.name}</span>
                      </Space>
                    }
                    extra={
                      <Switch
                        size="small"
                        checked={channel.enabled}
                        onChange={() => handleToggleChannel(channel)}
                      />
                    }
                    style={{ marginBottom: 16 }}
                  >
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="通道类型">
                        {getChannelTypeText(channel.channel_type)}
                      </Descriptions.Item>
                      <Descriptions.Item label="状态">
                        {channel.enabled ? (
                          <Tag color="success">已启用</Tag>
                        ) : (
                          <Tag>已禁用</Tag>
                        )}
                      </Descriptions.Item>
                      {channel.last_used && (
                        <Descriptions.Item label="最后使用">
                          {channel.last_used}
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                    <div style={{ marginTop: 8, textAlign: 'right' }}>
                      <Button
                        size="small"
                        onClick={() => handleTestChannel(channel.channel_type)}
                        loading={testChannelMutation.isPending}
                      >
                        发送测试
                      </Button>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </Tabs.TabPane>

          {/* 预警订阅标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <MailOutlined />
                <span>我的订阅</span>
              </Space>
            }
            key="subscriptions"
          >
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSubscription}>
                新建订阅
              </Button>
            </div>

            {subscriptionsLoading ? (
              <Spin />
            ) : subscriptions.length > 0 ? (
              <List
                dataSource={subscriptions}
                renderItem={(subscription) => (
                  <List.Item
                    actions={[
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDeleteSubscription(subscription.subscription_id)}
                      >
                        取消订阅
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<MailOutlined style={{ fontSize: 24 }} />}
                      title={
                        <Space>
                          <span>预警订阅</span>
                          {subscription.enabled !== false && <Badge status="success" />}
                        </Space>
                      }
                      description={
                        <Space wrap>
                          {subscription.alert_types.map((type) => (
                            <Tag key={type}>{type}</Tag>
                          ))}
                          <span>·</span>
                          {subscription.severity_filter.map((sev) => (
                            <Tag key={sev} color={getSeverityTag(sev)}>{sev}</Tag>
                          ))}
                          <span>·</span>
                          {subscription.channels.map((ch) => (
                            <Tooltip key={ch} title={getChannelTypeText(ch)}>
                              {getChannelIcon(ch)}
                            </Tooltip>
                          ))}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无订阅" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 规则编辑弹窗 */}
      <Modal
        title={selectedRule ? '编辑预警规则' : '新建预警规则'}
        open={ruleModalVisible}
        onCancel={() => setRuleModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRuleSubmit}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如：数据质量阈值监控" />
          </Form.Item>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <TextArea rows={2} placeholder="描述该规则的用途" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="rule_type"
                label="规则类型"
                rules={[{ required: true, message: '请选择规则类型' }]}
              >
                <Select placeholder="选择类型">
                  <Option value="threshold">阈值监控</Option>
                  <Option value="task_failure">任务失败</Option>
                  <Option value="sla_breach">SLA违约</Option>
                  <Option value="custom">自定义</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="severity"
                label="严重程度"
                rules={[{ required: true, message: '请选择严重程度' }]}
              >
                <Select placeholder="选择程度">
                  <Option value="info">信息</Option>
                  <Option value="warning">警告</Option>
                  <Option value="error">错误</Option>
                  <Option value="critical">紧急</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="channels"
            label="推送通道"
            rules={[{ required: true, message: '请选择推送通道' }]}
            initialValue={['email']}
          >
            <Select mode="multiple" placeholder="选择通道">
              {channels.map((c) => (
                <Option key={c.channel_type} value={c.channel_type}>
                  {c.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="enabled"
            label="启用状态"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 订阅创建弹窗 */}
      <Modal
        title="新建预警订阅"
        open={subscriptionModalVisible}
        onCancel={() => setSubscriptionModalVisible(false)}
        onOk={() => subscriptionForm.submit()}
        width={600}
      >
        <Form
          form={subscriptionForm}
          layout="vertical"
          onFinish={handleSubscriptionSubmit}
        >
          <Form.Item
            name="alert_types"
            label="预警类型"
            rules={[{ required: true, message: '请选择预警类型' }]}
          >
            <Select mode="multiple" placeholder="选择关注的预警类型">
              {alertTypes.map((type) => (
                <Option key={type.type} value={type.type}>
                  {type.name} - {type.description}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="severity_filter"
            label="严重程度过滤"
            rules={[{ required: true, message: '请选择严重程度' }]}
            initialValue={['error', 'critical']}
          >
            <Select mode="multiple" placeholder="选择关注的严重程度">
              <Option value="critical">紧急</Option>
              <Option value="error">错误</Option>
              <Option value="warning">警告</Option>
              <Option value="info">信息</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="channels"
            label="接收通道"
            rules={[{ required: true, message: '请选择接收通道' }]}
            initialValue={['email']}
          >
            <Select mode="multiple" placeholder="选择接收通道">
              {channels.map((c) => (
                <Option key={c.channel_type} value={c.channel_type}>
                  {c.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SmartAlerts;
