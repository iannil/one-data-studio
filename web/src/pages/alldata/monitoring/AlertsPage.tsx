/**
 * 智能预警推送页面
 * P6.2: 智能预警推送
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
  Badge,
  Tooltip,
  Divider,
  Timeline,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BellOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// 条件类型配置
const CONDITION_TYPES = [
  { value: 'threshold', label: '阈值检测', description: '当指标值超过/低于阈值时触发' },
  { value: 'change_rate', label: '变化率检测', description: '当指标变化率超过阈值时触发' },
  { value: 'anomaly', label: '异常检测', description: '使用AI算法检测指标异常' },
];

// 运算符配置
const OPERATORS = [
  { value: 'gt', label: '大于 (>)' },
  { value: 'gte', label: '大于等于 (>=)' },
  { value: 'lt', label: '小于 (<)' },
  { value: 'lte', label: '小于等于 (<=)' },
  { value: 'eq', label: '等于 (=)' },
  { value: 'neq', label: '不等于 (!=)' },
];

// 严重级别配置
const SEVERITY_OPTIONS = [
  { value: 'info', label: '信息', color: 'blue' },
  { value: 'warning', label: '警告', color: 'orange' },
  { value: 'critical', label: '严重', color: 'red' },
];

// 通知渠道配置
const CHANNEL_OPTIONS = [
  { value: 'email', label: '邮件' },
  { value: 'dingtalk', label: '钉钉' },
  { value: 'wechat_work', label: '企业微信' },
  { value: 'feishu', label: '飞书' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'in_app', label: '站内信' },
];

// 指标类型配置
const METRIC_TYPES = [
  { value: 'etl_task', label: 'ETL任务' },
  { value: 'data_quality', label: '数据质量' },
  { value: 'api_latency', label: 'API延迟' },
  { value: 'data_volume', label: '数据量' },
  { value: 'error_rate', label: '错误率' },
  { value: 'custom', label: '自定义' },
];

// 类型定义
interface MetricAlertRule {
  id: string;
  name: string;
  description?: string;
  metric_id?: string;
  metric_name?: string;
  metric_type?: string;
  condition_type: string;
  condition_config?: any;
  severity: string;
  alert_title_template?: string;
  alert_message_template?: string;
  notification_channels?: string[];
  notification_targets?: string[];
  cooldown_minutes: number;
  last_triggered_at?: string;
  is_enabled: boolean;
  trigger_count: number;
  created_at?: string;
  updated_at?: string;
}

interface Alert {
  id: string;
  rule_id?: string;
  rule_name?: string;
  title: string;
  message?: string;
  severity: string;
  target_type?: string;
  target_id?: string;
  target_name?: string;
  current_value?: number;
  threshold_value?: number;
  status: string;
  triggered_at?: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
}

interface AlertHistory {
  id: string;
  alert_id: string;
  rule_id?: string;
  previous_status?: string;
  new_status: string;
  action: string;
  action_by?: string;
  action_note?: string;
  created_at?: string;
}

interface AlertStats {
  rules: { total: number; enabled: number };
  alerts: { active: number; acknowledged: number; resolved_today: number };
  severity_distribution: Record<string, number>;
}

const AlertsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('rules');
  const [rules, setRules] = useState<MetricAlertRule[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<MetricAlertRule | null>(null);
  const [testingRule, setTestingRule] = useState<MetricAlertRule | null>(null);
  const [ruleForm] = Form.useForm();
  const [testForm] = Form.useForm();
  const [conditionType, setConditionType] = useState('threshold');
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  // 获取规则列表
  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/alerts/metric-rules');
      const data = await response.json();
      if (data.code === 0) {
        setRules(data.data.rules);
        setPagination(prev => ({ ...prev, total: data.data.total }));
      } else {
        message.error(data.message || '获取规则列表失败');
      }
    } catch (error) {
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 获取告警列表
  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/data-monitoring/alerts?page=${pagination.current}&page_size=${pagination.pageSize}`);
      const data = await response.json();
      if (data.code === 0) {
        setAlerts(data.data.alerts);
        setPagination(prev => ({ ...prev, total: data.data.total }));
      } else {
        message.error(data.message || '获取告警列表失败');
      }
    } catch (error) {
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 获取历史记录
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/alerts/history?page=${pagination.current}&page_size=${pagination.pageSize}`);
      const data = await response.json();
      if (data.code === 0) {
        setHistory(data.data.history);
        setPagination(prev => ({ ...prev, total: data.data.total }));
      } else {
        message.error(data.message || '获取历史记录失败');
      }
    } catch (error) {
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 获取统计数据
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/alerts/statistics');
      const data = await response.json();
      if (data.code === 0) {
        setStats(data.data);
      }
    } catch (error) {
      console.error('获取统计数据失败', error);
    }
  };

  useEffect(() => {
    fetchRules();
    fetchStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'alerts') {
      fetchAlerts();
    } else if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, pagination.current, pagination.pageSize]);

  // 创建/更新规则
  const handleSaveRule = async (values: any) => {
    try {
      // 构建条件配置
      let conditionConfig: any = {};
      if (values.condition_type === 'threshold') {
        conditionConfig = {
          operator: values.operator,
          value: values.threshold_value,
        };
      } else if (values.condition_type === 'change_rate') {
        conditionConfig = {
          period: values.period,
          operator: values.change_operator,
          value: values.change_threshold,
        };
      } else if (values.condition_type === 'anomaly') {
        conditionConfig = {
          algorithm: values.algorithm,
          sensitivity: values.sensitivity,
          window: values.window,
        };
      }

      const payload = {
        name: values.name,
        description: values.description,
        metric_id: values.metric_id,
        metric_name: values.metric_name,
        metric_type: values.metric_type,
        condition_type: values.condition_type,
        condition_config: conditionConfig,
        severity: values.severity,
        alert_title_template: values.alert_title_template,
        alert_message_template: values.alert_message_template,
        notification_channels: values.notification_channels,
        notification_targets: values.notification_targets?.split(',').map((s: string) => s.trim()).filter(Boolean),
        cooldown_minutes: values.cooldown_minutes,
        is_enabled: values.is_enabled,
      };

      const url = editingRule
        ? `/api/v1/alerts/metric-rules/${editingRule.id}`
        : '/api/v1/alerts/metric-rules';
      const method = editingRule ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success(editingRule ? '更新成功' : '创建成功');
        setRuleModalVisible(false);
        ruleForm.resetFields();
        setEditingRule(null);
        fetchRules();
        fetchStats();
      } else {
        message.error(data.message || '操作失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 删除规则
  const handleDeleteRule = async (ruleId: string) => {
    try {
      const response = await fetch(`/api/v1/alerts/metric-rules/${ruleId}`, {
        method: 'DELETE',
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success('删除成功');
        fetchRules();
        fetchStats();
      } else {
        message.error(data.message || '删除失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 测试规则
  const handleTestRule = async (values: any) => {
    if (!testingRule) return;

    try {
      const response = await fetch(`/api/v1/alerts/metric-rules/${testingRule.id}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_value: values.test_value }),
      });
      const data = await response.json();

      if (data.code === 0) {
        const result = data.data;
        if (result.should_alert) {
          message.warning(`会触发告警: ${result.message}`);
        } else {
          message.success(`不会触发告警: ${result.message}`);
        }
      } else {
        message.error(data.message || '测试失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 确认告警
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/v1/data-monitoring/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: 'current_user' }),
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success('确认成功');
        fetchAlerts();
        fetchStats();
      } else {
        message.error(data.message || '确认失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 解决告警
  const handleResolveAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/v1/data-monitoring/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: 'current_user' }),
      });
      const data = await response.json();

      if (data.code === 0) {
        message.success('解决成功');
        fetchAlerts();
        fetchStats();
      } else {
        message.error(data.message || '解决失败');
      }
    } catch (error) {
      message.error('网络错误');
    }
  };

  // 规则表格列
  const ruleColumns: ColumnsType<MetricAlertRule> = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          {!record.is_enabled && <Tag color="default">已禁用</Tag>}
        </Space>
      ),
    },
    {
      title: '指标',
      key: 'metric',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.metric_name || record.metric_id || '-'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {METRIC_TYPES.find(t => t.value === record.metric_type)?.label || record.metric_type}
          </Text>
        </Space>
      ),
    },
    {
      title: '条件类型',
      dataIndex: 'condition_type',
      key: 'condition_type',
      render: (type) => {
        const config = CONDITION_TYPES.find(t => t.value === type);
        return <Tag>{config?.label || type}</Tag>;
      },
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => {
        const config = SEVERITY_OPTIONS.find(s => s.value === severity);
        return <Tag color={config?.color}>{config?.label || severity}</Tag>;
      },
    },
    {
      title: '冷却时间',
      dataIndex: 'cooldown_minutes',
      key: 'cooldown_minutes',
      render: (minutes) => `${minutes} 分钟`,
    },
    {
      title: '触发次数',
      dataIndex: 'trigger_count',
      key: 'trigger_count',
    },
    {
      title: '最后触发',
      dataIndex: 'last_triggered_at',
      key: 'last_triggered_at',
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="测试规则">
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                setTestingRule(record);
                setTestModalVisible(true);
              }}
            />
          </Tooltip>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingRule(record);
              setConditionType(record.condition_type);
              const formValues: any = {
                ...record,
                notification_targets: record.notification_targets?.join(', '),
              };
              // 解析条件配置
              const config = record.condition_config || {};
              if (record.condition_type === 'threshold') {
                formValues.operator = config.operator;
                formValues.threshold_value = config.value;
              } else if (record.condition_type === 'change_rate') {
                formValues.period = config.period;
                formValues.change_operator = config.operator;
                formValues.change_threshold = config.value;
              } else if (record.condition_type === 'anomaly') {
                formValues.algorithm = config.algorithm;
                formValues.sensitivity = config.sensitivity;
                formValues.window = config.window;
              }
              ruleForm.setFieldsValue(formValues);
              setRuleModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此规则吗？"
            onConfirm={() => handleDeleteRule(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 告警表格列
  const alertColumns: ColumnsType<Alert> = [
    {
      title: '告警标题',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <Space>
          {record.severity === 'critical' && <AlertOutlined style={{ color: '#ff4d4f' }} />}
          {record.severity === 'warning' && <ExclamationCircleOutlined style={{ color: '#faad14' }} />}
          {record.severity === 'info' && <BellOutlined style={{ color: '#1677ff' }} />}
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '关联规则',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => {
        const config = SEVERITY_OPTIONS.find(s => s.value === severity);
        return <Tag color={config?.color}>{config?.label || severity}</Tag>;
      },
    },
    {
      title: '当前值 / 阈值',
      key: 'values',
      render: (_, record) => (
        <Text>
          {record.current_value ?? '-'} / {record.threshold_value ?? '-'}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
          active: { color: 'error', text: '活跃', icon: <AlertOutlined /> },
          acknowledged: { color: 'warning', text: '已确认', icon: <ClockCircleOutlined /> },
          resolved: { color: 'success', text: '已解决', icon: <CheckCircleOutlined /> },
        };
        const config = statusConfig[status] || { color: 'default', text: status };
        return <Badge status={config.color as any} text={config.text} />;
      },
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'active' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleAcknowledgeAlert(record.id)}
            >
              确认
            </Button>
          )}
          {(record.status === 'active' || record.status === 'acknowledged') && (
            <Button
              type="link"
              size="small"
              onClick={() => handleResolveAlert(record.id)}
            >
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 历史表格列
  const historyColumns: ColumnsType<AlertHistory> = [
    {
      title: '告警ID',
      dataIndex: 'alert_id',
      key: 'alert_id',
      ellipsis: true,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action) => {
        const actionConfig: Record<string, { color: string; text: string }> = {
          triggered: { color: 'red', text: '触发' },
          acknowledged: { color: 'orange', text: '确认' },
          resolved: { color: 'green', text: '解决' },
          escalated: { color: 'purple', text: '升级' },
          reopened: { color: 'blue', text: '重新打开' },
        };
        const config = actionConfig[action] || { color: 'default', text: action };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '状态变更',
      key: 'status_change',
      render: (_, record) => (
        <Text>
          {record.previous_status || '(新建)'} → {record.new_status}
        </Text>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'action_by',
      key: 'action_by',
    },
    {
      title: '备注',
      dataIndex: 'action_note',
      key: 'action_note',
      ellipsis: true,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => time ? new Date(time).toLocaleString() : '-',
    },
  ];

  // 渲染条件配置表单
  const renderConditionForm = () => {
    switch (conditionType) {
      case 'threshold':
        return (
          <>
            <Form.Item
              name="operator"
              label="运算符"
              rules={[{ required: true, message: '请选择运算符' }]}
            >
              <Select placeholder="请选择" options={OPERATORS} />
            </Form.Item>
            <Form.Item
              name="threshold_value"
              label="阈值"
              rules={[{ required: true, message: '请输入阈值' }]}
            >
              <InputNumber style={{ width: '100%' }} placeholder="请输入阈值" />
            </Form.Item>
          </>
        );
      case 'change_rate':
        return (
          <>
            <Form.Item
              name="period"
              label="对比周期"
              rules={[{ required: true, message: '请选择对比周期' }]}
            >
              <Select placeholder="请选择">
                <Select.Option value="1h">1小时</Select.Option>
                <Select.Option value="6h">6小时</Select.Option>
                <Select.Option value="24h">24小时</Select.Option>
                <Select.Option value="7d">7天</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="change_operator"
              label="运算符"
              rules={[{ required: true, message: '请选择运算符' }]}
            >
              <Select placeholder="请选择">
                <Select.Option value="gt">大于</Select.Option>
                <Select.Option value="lt">小于</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="change_threshold"
              label="变化率阈值"
              rules={[{ required: true, message: '请输入变化率阈值' }]}
              extra="如0.2表示20%"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.01}
                placeholder="请输入变化率阈值"
              />
            </Form.Item>
          </>
        );
      case 'anomaly':
        return (
          <>
            <Form.Item
              name="algorithm"
              label="检测算法"
              rules={[{ required: true, message: '请选择检测算法' }]}
            >
              <Select placeholder="请选择">
                <Select.Option value="zscore">Z-Score</Select.Option>
                <Select.Option value="isolation_forest">孤立森林</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="sensitivity"
              label="敏感度"
              rules={[{ required: true, message: '请输入敏感度' }]}
              extra="0.9-0.99之间，越高越敏感"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0.9}
                max={0.99}
                step={0.01}
                placeholder="请输入敏感度"
              />
            </Form.Item>
            <Form.Item
              name="window"
              label="检测窗口"
              rules={[{ required: true, message: '请选择检测窗口' }]}
            >
              <Select placeholder="请选择">
                <Select.Option value="1h">1小时</Select.Option>
                <Select.Option value="6h">6小时</Select.Option>
                <Select.Option value="24h">24小时</Select.Option>
                <Select.Option value="7d">7天</Select.Option>
              </Select>
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <ThunderboltOutlined style={{ marginRight: 8 }} />
            智能预警推送
          </Title>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                fetchRules();
                fetchStats();
              }}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingRule(null);
                setConditionType('threshold');
                ruleForm.resetFields();
                ruleForm.setFieldsValue({
                  condition_type: 'threshold',
                  severity: 'warning',
                  cooldown_minutes: 30,
                  is_enabled: true,
                });
                setRuleModalVisible(true);
              }}
            >
              新建规则
            </Button>
          </Space>
        </div>

        {/* 统计卡片 */}
        {stats && (
          <>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="预警规则" value={stats.rules.total} suffix={`/ ${stats.rules.enabled} 启用`} />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="活跃告警"
                    value={stats.alerts.active}
                    valueStyle={{ color: stats.alerts.active > 0 ? '#ff4d4f' : '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="待处理"
                    value={stats.alerts.acknowledged}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="今日解决"
                    value={stats.alerts.resolved_today}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="严重告警"
                    value={stats.severity_distribution?.critical || 0}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="警告告警"
                    value={stats.severity_distribution?.warning || 0}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
            </Row>
            <Divider />
          </>
        )}

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab="预警规则" key="rules">
            <Table
              columns={ruleColumns}
              dataSource={rules}
              rowKey="id"
              loading={loading}
              pagination={{
                ...pagination,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab={<span><AlertOutlined /> 告警列表</span>} key="alerts">
            <Table
              columns={alertColumns}
              dataSource={alerts}
              rowKey="id"
              loading={loading}
              pagination={{
                ...pagination,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab={<span><HistoryOutlined /> 历史记录</span>} key="history">
            <Table
              columns={historyColumns}
              dataSource={history}
              rowKey="id"
              loading={loading}
              pagination={{
                ...pagination,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
              }}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? '编辑预警规则' : '新建预警规则'}
        open={ruleModalVisible}
        onCancel={() => {
          setRuleModalVisible(false);
          setEditingRule(null);
          ruleForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={ruleForm}
          layout="vertical"
          onFinish={handleSaveRule}
          initialValues={{
            condition_type: 'threshold',
            severity: 'warning',
            cooldown_minutes: 30,
            is_enabled: true,
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="请输入规则名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="metric_type"
                label="指标类型"
              >
                <Select placeholder="请选择指标类型" options={METRIC_TYPES} allowClear />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="metric_id" label="指标ID">
                <Input placeholder="请输入指标ID" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="metric_name" label="指标名称">
                <Input placeholder="请输入指标名称" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="请输入规则描述" />
          </Form.Item>

          <Divider>条件配置</Divider>

          <Form.Item
            name="condition_type"
            label="条件类型"
            rules={[{ required: true, message: '请选择条件类型' }]}
          >
            <Select
              placeholder="请选择条件类型"
              onChange={(value) => setConditionType(value)}
            >
              {CONDITION_TYPES.map(type => (
                <Select.Option key={type.value} value={type.value}>
                  <Space direction="vertical" size={0}>
                    <Text>{type.label}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{type.description}</Text>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {renderConditionForm()}

          <Divider>告警配置</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="severity"
                label="严重级别"
                rules={[{ required: true, message: '请选择严重级别' }]}
              >
                <Select placeholder="请选择">
                  {SEVERITY_OPTIONS.map(opt => (
                    <Select.Option key={opt.value} value={opt.value}>
                      <Tag color={opt.color}>{opt.label}</Tag>
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="cooldown_minutes"
                label="冷却时间（分钟）"
                rules={[{ required: true, message: '请输入冷却时间' }]}
              >
                <InputNumber style={{ width: '100%' }} min={1} placeholder="请输入冷却时间" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="alert_title_template" label="告警标题模板">
            <Input placeholder="支持变量: {{metric_name}}, {{current_value}}, {{threshold_value}}" />
          </Form.Item>
          <Form.Item name="alert_message_template" label="告警内容模板">
            <TextArea rows={3} placeholder="支持变量: {{metric_name}}, {{current_value}}, {{threshold_value}}, {{triggered_at}}" />
          </Form.Item>

          <Divider>通知配置</Divider>

          <Form.Item name="notification_channels" label="通知渠道">
            <Select mode="multiple" placeholder="请选择通知渠道" options={CHANNEL_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="notification_targets"
            label="通知对象"
            extra="多个对象用逗号分隔"
          >
            <Input placeholder="请输入通知对象（用户ID、邮箱等）" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_enabled" label="启用状态" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => {
                setRuleModalVisible(false);
                setEditingRule(null);
                ruleForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 测试规则弹窗 */}
      <Modal
        title="测试预警规则"
        open={testModalVisible}
        onCancel={() => {
          setTestModalVisible(false);
          setTestingRule(null);
          testForm.resetFields();
        }}
        footer={null}
        width={500}
      >
        {testingRule && (
          <>
            <Paragraph>
              <Text strong>规则名称：</Text>{testingRule.name}
            </Paragraph>
            <Paragraph>
              <Text strong>条件类型：</Text>
              {CONDITION_TYPES.find(t => t.value === testingRule.condition_type)?.label}
            </Paragraph>
            <Divider />
            <Form form={testForm} layout="vertical" onFinish={handleTestRule}>
              <Form.Item
                name="test_value"
                label="测试值"
                rules={[{ required: true, message: '请输入测试值' }]}
              >
                <InputNumber style={{ width: '100%' }} placeholder="请输入模拟的指标值" />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />}>
                    执行测试
                  </Button>
                  <Button onClick={() => {
                    setTestModalVisible(false);
                    setTestingRule(null);
                    testForm.resetFields();
                  }}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </div>
  );
};

export default AlertsPage;
