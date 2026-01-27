/**
 * 元数据版本回滚组件
 * 支持回滚预览、SQL 生成和执行
 */

import React, { useState } from 'react';
import {
  Card,
  Button,
  Modal,
  Form,
  Select,
  Space,
  Typography,
  Alert,
  Timeline,
  Tag,
  Steps,
  Row,
  Col,
  Statistic,
  Progress,
  Divider,
  List,
  Tooltip,
  message,
  Popconfirm,
  Spin,
  Empty,
  Checkbox,
} from 'antd';
import {
  RollbackOutlined,
  EyeOutlined,
  CodeOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
  HistoryOutlined,
  SwapRightOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import alldata from '@/services/alldata';
import './MetadataVersionRollback.css';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { TextArea } = Form;

interface RollbackAction {
  action: string;
  table?: string;
  column?: string;
  description: string;
  risk: 'low' | 'medium' | 'high';
  change_type?: string;
  from?: string;
  to?: string;
  column_type?: string;
  nullable?: boolean;
  default?: string;
}

interface RollbackPlan {
  version_id: string;
  target_version_id: string;
  table_name: string;
  database_name: string;
  actions: RollbackAction[];
  sql_statements: string[];
  warnings: string[];
  estimated_duration_seconds: number;
  requires_data_backup: boolean;
  is_reversible: boolean;
}

interface RollbackResult {
  success: boolean;
  version_id: string;
  target_version_id: string;
  new_version_id?: string;
  executed_sql: string[];
  error_message?: string;
  rollback_version_id?: string;
}

interface MetadataVersion {
  id: string;
  change_type: string;
  change_summary: string;
  version_number: number;
  created_at: string;
  changed_by: string;
}

interface MetadataVersionRollbackProps {
  tableId: string;
  tableName: string;
  onSuccess?: (result: RollbackResult) => void;
}

const RISK_COLORS = {
  low: { color: '#52c41a', text: '低风险', icon: <CheckCircleOutlined /> },
  medium: { color: '#faad14', text: '中风险', icon: <ExclamationCircleOutlined /> },
  high: { color: '#ff4d4f', text: '高风险', icon: <WarningOutlined /> },
};

const ACTION_ICONS: Record<string, React.ReactNode> = {
  add_column: <Tag color="green">新增列</Tag>,
  drop_column: <Tag color="red">删除列</Tag>,
  modify_column: <Tag color="blue">修改列</Tag>,
  restore_metadata: <Tag color="cyan">恢复元数据</Tag>,
};

/**
 * 风险等级徽章
 */
const RiskBadge: React.FC<{ risk: 'low' | 'medium' | 'high' }> = ({ risk }) => {
  const config = RISK_COLORS[risk];
  return (
    <Tag color={config.color} icon={config.icon}>
      {config.text}
    </Tag>
  );
};

/**
 * 回滚操作列表
 */
const RollbackActionsList: React.FC<{ actions: RollbackAction[] }> = ({ actions }) => {
  const getTypeText = (action: RollbackAction) => {
    if (action.change_type === 'type') {
      return `类型: ${action.from} → ${action.to}`;
    }
    if (action.change_type === 'nullable') {
      return `可空: ${action.from ? '可空' : '不可空'} → ${action.to ? '可空' : '不可空'}`;
    }
    if (action.change_type === 'default') {
      return `默认值: ${action.from || '无'} → ${action.to || '无'}`;
    }
    return null;
  };

  return (
    <List
      dataSource={actions}
      renderItem={(action, idx) => (
        <List.Item key={idx} className="rollback-action-item">
          <List.Item.Meta
            avatar={
              <div className="action-index">
                <Text strong>{idx + 1}</Text>
              </div>
            }
            title={
              <Space>
                {ACTION_ICONS[action.action] || <Tag>{action.action}</Tag>}
                <Text>{action.description}</Text>
                <RiskBadge risk={action.risk} />
              </Space>
            }
            description={
              <Space direction="vertical" style={{ width: '100%' }}>
                {action.column && (
                  <Text type="secondary">列: {action.column}</Text>
                )}
                {action.change_type && (
                  <Text type="secondary">{getTypeText(action)}</Text>
                )}
                {action.column_type && (
                  <Text type="secondary">类型: {action.column_type}</Text>
                )}
              </Space>
            }
          />
        </List.Item>
      )}
    />
  );
};

/**
 * 回滚预览模态框
 */
const RollbackPreviewModal: React.FC<{
  visible: boolean;
  tableId: string;
  versions: MetadataVersion[];
  onClose: () => void;
  onConfirm: (targetVersionId: string, options: any) => void;
  loading: boolean;
}> = ({ visible, tableId, versions, onClose, onConfirm, loading }) => {
  const [form] = Form.useForm();
  const [targetVersionId, setTargetVersionId] = useState<string>('');
  const [currentStep, setCurrentStep] = useState(0);

  const { data: planData, isLoading: planLoading } = useQuery({
    queryKey: ['metadata', 'rollback', 'preview', tableId, targetVersionId],
    queryFn: async () => {
      const res = await alldata.previewRollback(tableId, { target_version_id: targetVersionId });
      return res.data as RollbackPlan;
    },
    enabled: visible && !!targetVersionId,
  });

  const plan = planData as RollbackPlan | undefined;

  const handleSelectVersion = (versionId: string) => {
    setTargetVersionId(versionId);
    setCurrentStep(1);
  };

  const handleExecute = () => {
    const values = form.getFieldsValue();
    onConfirm(targetVersionId, values);
  };

  const steps = [
    {
      title: '选择版本',
      description: '选择要回滚到的目标版本',
    },
    {
      title: '预览变更',
      description: '查看将要执行的操作',
    },
    {
      title: '确认执行',
      description: '确认并执行回滚',
    },
  ];

  const versionOptions = versions
    .sort((a, b) => b.version_number - a.version_number)
    .map(v => ({
      label: (
        <Space>
          <span>v{v.version_number}</span>
          <Text type="secondary">| {v.change_summary}</Text>
        </Space>
      ),
      value: v.id,
    }));

  return (
    <Modal
      title={
        <Space>
          <RollbackOutlined />
          <span>元数据版本回滚</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={
        currentStep === 2 ? (
          <Space>
            <Button onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Popconfirm
              title="确定要执行回滚操作吗？"
              description="此操作将修改元数据，请确认已备份数据"
              onConfirm={handleExecute}
              okText="确认回滚"
              cancelText="取消"
            >
              <Button type="primary" danger loading={loading} icon={<RollbackOutlined />}>
                执行回滚
              </Button>
            </Popconfirm>
          </Space>
        ) : (
          <Space>
            <Button onClick={onClose} disabled={loading}>
              取消
            </Button>
            {currentStep === 1 && (
              <Button onClick={() => setCurrentStep(0)}>
                上一步
              </Button>
            )}
            {currentStep === 1 && plan && (
              <Button type="primary" onClick={() => setCurrentStep(2)}>
                下一步
              </Button>
            )}
            {currentStep === 0 && (
              <Button type="primary" disabled={!targetVersionId} onClick={() => setCurrentStep(1)}>
                下一步
              </Button>
            )}
          </Space>
        )
      }
    >
      <Steps current={currentStep} size="small" style={{ marginBottom: 24 }}>
        {steps.map((step, idx) => (
          <Step key={idx} title={step.title} description={step.description} />
        ))}
      </Steps>

      {/* 步骤1: 选择版本 */}
      {currentStep === 0 && (
        <div className="rollback-step-select-version">
          <Alert
            message="选择要回滚到的目标版本"
            description="系统将恢复该版本的元数据结构，请谨慎选择"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Select
            placeholder="请选择目标版本"
            style={{ width: '100%' }}
            options={versionOptions}
            onChange={handleSelectVersion}
            value={targetVersionId}
            size="large"
          />
        </div>
      )}

      {/* 步骤2: 预览变更 */}
      {currentStep === 1 && (
        <div className="rollback-step-preview">
          {planLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
              <div style={{ marginTop: 16 }}>正在分析变更...</div>
            </div>
          ) : plan ? (
            <>
              {/* 统计概览 */}
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Statistic
                    title="变更操作"
                    value={plan.actions.length}
                    valueStyle={{ color: '#1677ff' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="SQL 语句"
                    value={plan.sql_statements.length}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="警告数量"
                    value={plan.warnings.length}
                    valueStyle={{ color: plan.warnings.length > 0 ? '#faad14' : '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="预计耗时"
                    value={plan.estimated_duration_seconds}
                    suffix="秒"
                    valueStyle={{ color: '#8c8c8c' }}
                  />
                </Col>
              </Row>

              {/* 警告信息 */}
              {plan.warnings.length > 0 && (
                <Alert
                  message="回滚警告"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 16 }}>
                      {plan.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  }
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* 操作列表 */}
              <Card title="将要执行的操作" size="small" style={{ marginBottom: 16 }}>
                <RollbackActionsList actions={plan.actions} />
              </Card>

              {/* SQL 预览 */}
              <Card
                title="SQL 脚本预览"
                size="small"
                extra={
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => {
                      navigator.clipboard.writeText(plan.sql_statements.join('\n'));
                      message.success('SQL 已复制到剪贴板');
                    }}
                  >
                    复制 SQL
                  </Button>
                }
              >
                <pre className="sql-preview-block">
                  <code>{plan.sql_statements.join('\n')}</code>
                </pre>
              </Card>

              {/* 执行选项 */}
              <Divider />
              <Form form={form} layout="vertical">
                <Form.Item
                  name="create_backup"
                  label="创建备份"
                  initialValue={true}
                  valuePropName="checked"
                >
                  <Checkbox>回滚前创建当前版本的备份</Checkbox>
                </Form.Item>
                <Form.Item
                  name="execute_on_database"
                  label="在数据库上执行"
                  valuePropName="checked"
                  extra="注意：启用后将在实际数据库上执行 SQL 操作，默认仅更新元数据"
                >
                  <Checkbox>同时在物理数据库上执行变更（谨慎操作）</Checkbox>
                </Form.Item>
              </Form>
            </>
          ) : (
            <Empty description="无法加载回滚计划" />
          )}
        </div>
      )}

      {/* 步骤3: 确认执行 */}
      {currentStep === 2 && plan && (
        <div className="rollback-step-confirm">
          <Alert
            message="即将执行回滚操作"
            description="请确认以下信息无误后点击执行"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Descriptions size="small" bordered column={1}>
            <Descriptions.Item label="目标版本">
              <Tag color="blue">v{versions.find(v => v.id === targetVersionId)?.version_number}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="变更操作数">
              {plan.actions.length} 项
            </Descriptions.Item>
            <Descriptions.Item label="高风险操作">
              {plan.actions.filter(a => a.risk === 'high').length} 项
            </Descriptions.Item>
            <Descriptions.Item label="是否可逆">
              {plan.is_reversible ? (
                <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
              ) : (
                <Tag color="red" icon={<WarningOutlined />}>否</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>

          {plan.requires_data_backup && (
            <Alert
              message="此回滚操作需要备份数据"
              description="建议先创建数据快照再执行回滚"
              type="error"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </div>
      )}
    </Modal>
  );
};

const Descriptions = ({ children, ...props }: any) => {
  // 简化的 Descriptions 组件
  return <div className="descriptions" {...props}>{children}</div>;
};

const DescriptionsItem = ({ label, children }: any) => {
  return (
    <div className="descriptions-item">
      <div className="label">{label}</div>
      <div className="content">{children}</div>
    </div>
  );
};

/**
 * 版本历史时间轴
 */
const VersionHistoryTimeline: React.FC<{
  tableId: string;
  onRollback: (versionId: string) => void;
}> = ({ tableId, onRollback }) => {
  const { data: versionsData, isLoading } = useQuery({
    queryKey: ['metadata', 'versions', tableId],
    queryFn: async () => {
      const res = await alldata.getMetadataVersions(tableId);
      return res.data as { versions: MetadataVersion[] };
    },
  });

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>;
  }

  const versions = versionsData?.versions || [];

  return (
    <Timeline mode="left">
      {versions.map((version, idx) => (
        <Timeline.Item
          key={version.id}
          dot={idx === 0 ? <CheckCircleOutlined style={{ fontSize: 16, color: '#52c41a' }} /> : undefined}
          color={idx === 0 ? 'green' : 'gray'}
        >
          <Card size="small" className="version-timeline-card">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Tag color="blue">v{version.version_number}</Tag>
                <Tag>{version.change_type}</Tag>
                {idx === 0 && <Tag color="green">当前版本</Tag>}
              </Space>
              <Text>{version.change_summary}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {version.changed_by} | {new Date(version.created_at).toLocaleString('zh-CN')}
              </Text>
              {idx !== 0 && (
                <Button
                  size="small"
                  icon={<RollbackOutlined />}
                  onClick={() => onRollback(version.id)}
                >
                  回滚到此版本
                </Button>
              )}
            </Space>
          </Card>
        </Timeline.Item>
      ))}
    </Timeline>
  );
};

/**
 * 主回滚组件
 */
const MetadataVersionRollback: React.FC<MetadataVersionRollbackProps> = ({
  tableId,
  tableName,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<string>('');

  const { data: versionsData, isLoading: versionsLoading } = useQuery({
    queryKey: ['metadata', 'versions', tableId],
    queryFn: async () => {
      const res = await alldata.getMetadataVersions(tableId);
      return res.data as { versions: MetadataVersion[] };
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: async (params: { targetVersionId: string; options: any }) => {
      const res = await alldata.executeRollback(tableId, {
        target_version_id: params.targetVersionId,
        create_backup: params.options.create_backup !== false,
        execute_on_database: params.options.execute_on_database || false,
      });
      return res.data as RollbackResult;
    },
    onSuccess: (result) => {
      if (result.success) {
        message.success('回滚成功');
        setModalVisible(false);
        queryClient.invalidateQueries({ queryKey: ['metadata', 'versions', tableId] });
        onSuccess?.(result);
      } else {
        message.error(`回滚失败: ${result.error_message}`);
      }
    },
    onError: (err: any) => {
      message.error(`回滚失败: ${err.message}`);
    },
  });

  const handleRollbackClick = (versionId: string) => {
    setSelectedVersionId(versionId);
    setModalVisible(true);
  };

  const handleConfirmRollback = (targetVersionId: string, options: any) => {
    rollbackMutation.mutate({ targetVersionId, options });
  };

  const versions = versionsData?.versions || [];

  return (
    <div className="metadata-version-rollback">
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>版本历史与回滚</span>
            <Text type="secondary">({tableName})</Text>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<RollbackOutlined />}
            onClick={() => setModalVisible(true)}
            disabled={versions.length < 2}
          >
            执行回滚
          </Button>
        }
      >
        {versionsLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : versions.length > 0 ? (
          <VersionHistoryTimeline
            tableId={tableId}
            onRollback={handleRollbackClick}
          />
        ) : (
          <Empty description="暂无版本历史" />
        )}
      </Card>

      <RollbackPreviewModal
        visible={modalVisible}
        tableId={tableId}
        versions={versions}
        onClose={() => {
          setModalVisible(false);
          setSelectedVersionId('');
        }}
        onConfirm={handleConfirmRollback}
        loading={rollbackMutation.isPending}
      />
    </div>
  );
};

export default MetadataVersionRollback;
