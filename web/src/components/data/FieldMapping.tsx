/**
 * AI 字段转换智能映射组件
 * 智能推荐源表到目标表的字段映射
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  List,
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
  Divider,
  Empty,
  Spin,
  message,
  Tabs,
  Badge,
  Switch,
} from 'antd';
import {
  SwapRightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  CodeOutlined,
  EyeOutlined,
  SyncOutlined,
  RobotOutlined,
  BulbOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  suggestFieldMappings,
  generateTransformationSQL,
  detectMappingConflicts,
  suggestDerivedFields,
  listTablesForMapping,
} from '@/services/data';
import type {
  FieldMappingSuggestion,
  FieldMappingResponse,
  MappingConflict,
  SQLGenerationResponse,
} from '@/services/data';
import './FieldMapping.css';

const { TextArea } = Input;
const { Option } = Select;

interface FieldMappingProps {
  databases?: string[];
  onMappingSaved?: (mappings: FieldMappingSuggestion[]) => void;
}

interface MappingItem extends FieldMappingSuggestion {
  key: string;
  selected?: boolean;
}

export const FieldMapping: React.FC<FieldMappingProps> = ({
  databases = [],
  onMappingSaved,
}) => {
  const [sourceDatabase, setSourceDatabase] = useState<string>('');
  const [targetDatabase, setTargetDatabase] = useState<string>('');
  const [sourceTable, setSourceTable] = useState<string>('');
  const [targetTable, setTargetTable] = useState<string>('');
  const [mappings, setMappings] = useState<MappingItem[]>([]);
  const [selectedMappings, setSelectedMappings] = useState<Set<string>>(new Set());
  const [sqlModalVisible, setSqlModalVisible] = useState(false);
  const [sqlResult, setSqlResult] = useState<SQLGenerationResponse | null>(null);
  const [conflictsModalVisible, setConflictsModalVisible] = useState(false);
  const [conflicts, setConflicts] = useState<MappingConflict[]>([]);
  const [activeTab, setActiveTab] = useState('auto');

  // 获取源表列表
  const { data: sourceTablesData, isLoading: sourceTablesLoading } = useQuery({
    queryKey: ['mapping-tables', sourceDatabase],
    queryFn: () => listTablesForMapping(sourceDatabase),
    enabled: !!sourceDatabase,
  });

  // 获取目标表列表
  const { data: targetTablesData, isLoading: targetTablesLoading } = useQuery({
    queryKey: ['mapping-tables', targetDatabase],
    queryFn: () => listTablesForMapping(targetDatabase),
    enabled: !!targetDatabase,
  });

  // 推荐字段映射
  const suggestMutation = useMutation({
    mutationFn: () =>
      suggestFieldMappings({
        source_table: sourceTable,
        target_table: targetTable,
        source_database: sourceDatabase || undefined,
        target_database: targetDatabase || undefined,
      }),
    onSuccess: (data) => {
      const mappingData = data?.data;
      if (mappingData) {
        const mappingItems = mappingData.suggestions.map((s, index) => ({
          ...s,
          key: `${s.source_field}-${s.target_field}-${index}`,
        }));
        setMappings(mappingItems);
        setSelectedMappings(new Set(mappingItems.map((m) => m.key)));
        message.success(
          `推荐完成：${mappingData.summary.total_suggestions} 个映射，覆盖率 ${(mappingData.summary.source_coverage * 100).toFixed(1)}%`
        );
      }
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '推荐失败');
    },
  });

  // 生成 SQL
  const generateSqlMutation = useMutation({
    mutationFn: (selectedMappingsList: MappingItem[]) =>
      generateTransformationSQL({
        mappings: selectedMappingsList,
        source_table: sourceTable,
        target_table: targetTable,
      }),
    onSuccess: (data) => {
      setSqlResult(data.data);
      setSqlModalVisible(true);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'SQL 生成失败');
    },
  });

  // 检测冲突
  const conflictsMutation = useMutation({
    mutationFn: (selectedMappingsList: MappingItem[]) =>
      detectMappingConflicts({
        mappings: selectedMappingsList,
        target_schema: [], // 简化处理
      }),
    onSuccess: (data) => {
      setConflicts(data.data.conflicts);
      setConflictsModalVisible(true);
    },
  });

  const handleSuggest = () => {
    if (!sourceTable || !targetTable) {
      message.warning('请选择源表和目标表');
      return;
    }
    suggestMutation.mutate();
  };

  const handleToggleMapping = (key: string) => {
    const newSelected = new Set(selectedMappings);
    if (newSelected.has(key)) {
      newSelected.delete(key);
    } else {
      newSelected.add(key);
    }
    setSelectedMappings(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedMappings.size === mappings.length) {
      setSelectedMappings(new Set());
    } else {
      setSelectedMappings(new Set(mappings.map((m) => m.key)));
    }
  };

  const handleGenerateSQL = () => {
    const selectedMappingsList = mappings.filter((m) =>
      selectedMappings.has(m.key)
    );
    if (selectedMappingsList.length === 0) {
      message.warning('请至少选择一个映射');
      return;
    }
    generateSqlMutation.mutate(selectedMappingsList);
  };

  const handleCheckConflicts = () => {
    const selectedMappingsList = mappings.filter((m) =>
      selectedMappings.has(m.key)
    );
    conflictsMutation.mutate(selectedMappingsList);
  };

  const getMappingTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      exact: 'success',
      fuzzy: 'processing',
      semantic: 'warning',
      inferred: 'default',
      derived: 'purple',
    };
    return colors[type] || 'default';
  };

  const getMappingTypeText = (type: string) => {
    const texts: Record<string, string> = {
      exact: '完全匹配',
      fuzzy: '模糊匹配',
      semantic: '语义匹配',
      inferred: '类型推断',
      derived: '派生字段',
    };
    return texts[type] || type;
  };

  const getRiskColor = (risk: string) => {
    const colors: Record<string, string> = {
      low: 'success',
      medium: 'warning',
      high: 'error',
      critical: 'error',
    };
    return colors[risk] || 'default';
  };

  const getRiskText = (risk: string) => {
    const texts: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '严重',
    };
    return texts[risk] || risk;
  };

  const getConversionIcon = (conversion: string) => {
    if (conversion === 'direct') {
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    }
    return <ToolOutlined style={{ color: '#1677ff' }} />;
  };

  const selectedMappingsList = mappings.filter((m) =>
    selectedMappings.has(m.key)
  );

  const mappingSummary = suggestMutation.data?.data?.summary;

  const columns = [
    {
      title: '',
      width: 50,
      render: (_: any, record: MappingItem) => (
        <Switch
          size="small"
          checked={selectedMappings.has(record.key)}
          onChange={() => handleToggleMapping(record.key)}
        />
      ),
    },
    {
      title: '源字段',
      dataIndex: 'source_field',
      key: 'source_field',
      width: 200,
      render: (text: string) => <code className="field-code">{text}</code>,
    },
    {
      title: '',
      width: 50,
      render: () => <SwapRightOutlined style={{ color: '#999' }} />,
    },
    {
      title: '目标字段',
      dataIndex: 'target_field',
      key: 'target_field',
      width: 200,
      render: (text: string) => <code className="field-code">{text}</code>,
    },
    {
      title: '映射类型',
      dataIndex: 'mapping_type',
      key: 'mapping_type',
      width: 100,
      render: (type: string) => (
        <Tag color={getMappingTypeColor(type)}>
          {getMappingTypeText(type)}
        </Tag>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '类型转换',
      key: 'data_type_conversion',
      width: 200,
      render: (_: any, record: MappingItem) => (
        <Space size="small">
          {getConversionIcon(record.data_type_conversion.conversion)}
          <Tooltip
            title={`${record.data_type_conversion.source_type} → ${record.data_type_conversion.target_type}`}
          >
            <Tag color={getRiskColor(record.data_type_conversion.conversion_risk)}>
              {record.data_type_conversion.conversion === 'direct'
                ? '直接映射'
                : '需要转换'}
            </Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '质量得分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 100,
      render: (score: number) => (
        <Badge
          count={score.toFixed(2)}
          style={{
            backgroundColor: score >= 0.8 ? '#52c41a' : score >= 0.6 ? '#faad14' : '#ff4d4f',
          }}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: any, record: MappingItem) => (
        <Space>
          {record.transformation && (
            <Tooltip title="查看转换表达式">
              <Button
                type="text"
                size="small"
                icon={<EyeOutlined />}
                onClick={() =>
                  Modal.info({
                    title: '转换表达式',
                    content: (
                      <pre style={{ whiteSpace: 'pre-wrap' }}>
                        {record.transformation}
                      </pre>
                    ),
                  })
                }
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="field-mapping">
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>AI 字段智能映射</span>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 自动推荐标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <ThunderboltOutlined />
                <span>智能推荐</span>
              </Space>
            }
            key="auto"
          >
            {/* 表选择区域 */}
            <Card size="small" title="选择源表和目标表" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <div className="table-selector">
                    <div className="selector-label">源数据库</div>
                    <Select
                      placeholder="选择源数据库"
                      value={sourceDatabase}
                      onChange={setSourceDatabase}
                      style={{ width: '100%' }}
                    >
                      {databases.map((db) => (
                        <Option key={db} value={db}>
                          {db}
                        </Option>
                      ))}
                    </Select>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="table-selector">
                    <div className="selector-label">源表</div>
                    <Select
                      placeholder="选择源表"
                      value={sourceTable}
                      onChange={setSourceTable}
                      loading={sourceTablesLoading}
                      disabled={!sourceDatabase}
                      style={{ width: '100%' }}
                    >
                      {sourceTablesData?.data?.tables?.map((t) => (
                        <Option key={t.table_name} value={t.table_name}>
                          {t.table_name} ({t.column_count}列)
                        </Option>
                      ))}
                    </Select>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="table-selector">
                    <div className="selector-label">目标数据库</div>
                    <Select
                      placeholder="选择目标数据库"
                      value={targetDatabase}
                      onChange={setTargetDatabase}
                      style={{ width: '100%' }}
                    >
                      {databases.map((db) => (
                        <Option key={db} value={db}>
                          {db}
                        </Option>
                      ))}
                    </Select>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="table-selector">
                    <div className="selector-label">目标表</div>
                    <Select
                      placeholder="选择目标表"
                      value={targetTable}
                      onChange={setTargetTable}
                      loading={targetTablesLoading}
                      disabled={!targetDatabase}
                      style={{ width: '100%' }}
                    >
                      {targetTablesData?.data?.tables?.map((t) => (
                        <Option key={t.table_name} value={t.table_name}>
                          {t.table_name} ({t.column_count}列)
                        </Option>
                      ))}
                    </Select>
                  </div>
                </Col>
              </Row>
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  loading={suggestMutation.isPending}
                  onClick={handleSuggest}
                  disabled={!sourceTable || !targetTable}
                  size="large"
                >
                  开始智能映射
                </Button>
              </div>
            </Card>

            {/* 统计概览 */}
            {mappingSummary && (
              <Card size="small" title="映射概览" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={4}>
                    <Statistic
                      title="推荐数量"
                      value={mappingSummary.total_suggestions}
                      prefix={<BulbOutlined />}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="源表覆盖率"
                      value={(mappingSummary.source_coverage * 100).toFixed(1)}
                      suffix="%"
                      valueStyle={{
                        color:
                          mappingSummary.source_coverage >= 0.8
                            ? '#52c41a'
                            : '#faad14',
                      }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="目标表覆盖率"
                      value={(mappingSummary.target_coverage * 100).toFixed(1)}
                      suffix="%"
                      valueStyle={{
                        color:
                          mappingSummary.target_coverage >= 0.8
                            ? '#52c41a'
                            : '#faad14',
                      }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="平均置信度"
                      value={(mappingSummary.avg_confidence * 100).toFixed(1)}
                      suffix="%"
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="平均质量得分"
                      value={mappingSummary.avg_quality.toFixed(2)}
                      precision={2}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="已选择"
                      value={selectedMappings.size}
                      suffix={`/ ${mappings.length}`}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 映射列表 */}
            {mappings.length > 0 && (
              <Card
                size="small"
                title="字段映射列表"
                extra={
                  <Space>
                    <Button size="small" onClick={handleSelectAll}>
                      {selectedMappings.size === mappings.length ? '取消全选' : '全选'}
                    </Button>
                    <Button
                      size="small"
                      icon={<SyncOutlined />}
                      onClick={handleCheckConflicts}
                    >
                      检测冲突
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<CodeOutlined />}
                      onClick={handleGenerateSQL}
                      disabled={selectedMappings.size === 0}
                    >
                      生成 SQL
                    </Button>
                  </Space>
                }
              >
                <Table
                  columns={columns}
                  dataSource={mappings}
                  pagination={false}
                  size="small"
                  rowClassName={(record) =>
                    selectedMappings.has(record.key) ? 'mapping-row-selected' : ''
                  }
                />
              </Card>
            )}

            {/* 空状态 */}
            {mappings.length === 0 && !suggestMutation.isPending && (
              <Empty
                description="选择源表和目标表，点击「开始智能映射」按钮"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}

            {/* 加载状态 */}
            {suggestMutation.isPending && (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" tip="AI 正在分析字段映射..." />
              </div>
            )}
          </Tabs.TabPane>

          {/* 手动配置标签页 */}
          <Tabs.TabPane
            tab={
              <Space>
                <ToolOutlined />
                <span>手动配置</span>
              </Space>
            }
            key="manual"
          >
            <Alert
              message="手动配置字段映射"
              description="在自动推荐基础上，您可以手动调整映射关系、添加转换规则或创建派生字段。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Empty
              description="手动配置功能开发中"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* SQL 预览弹窗 */}
      <Modal
        title={
          <Space>
            <CodeOutlined />
            <span>转换 SQL 预览</span>
          </Space>
        }
        open={sqlModalVisible}
        onCancel={() => setSqlModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setSqlModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="copy"
            type="primary"
            onClick={() => {
              navigator.clipboard.writeText(sqlResult?.select_sql || '');
              message.success('已复制到剪贴板');
            }}
          >
            复制 SQL
          </Button>,
        ]}
      >
        {sqlResult && (
          <>
            <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="映射数量">
                {selectedMappings.size}
              </Descriptions.Item>
              <Descriptions.Item label="需要转换">
                {sqlResult.conversion_count}
              </Descriptions.Item>
              <Descriptions.Item label="高风险转换">
                <span style={{ color: sqlResult.high_risk_count > 0 ? '#ff4d4f' : 'inherit' }}>
                  {sqlResult.high_risk_count}
                </span>
              </Descriptions.Item>
            </Descriptions>
            <pre className="sql-preview">{sqlResult.select_sql}</pre>
          </>
        )}
      </Modal>

      {/* 冲突检测弹窗 */}
      <Modal
        title={
          <Space>
            <WarningOutlined />
            <span>映射冲突检测</span>
          </Space>
        }
        open={conflictsModalVisible}
        onCancel={() => setConflictsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setConflictsModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {conflicts.length === 0 ? (
          <Alert
            message="未检测到冲突"
            description="当前映射配置没有发现冲突，可以安全使用。"
            type="success"
            showIcon
          />
        ) : (
          <>
            <Alert
              message={`检测到 ${conflicts.length} 个冲突`}
              description="请解决以下冲突后再执行数据转换"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <List
              dataSource={conflicts}
              renderItem={(conflict) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      conflict.severity === 'error' ? (
                        <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                      ) : (
                        <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />
                      )
                    }
                    title={conflict.message}
                    description={
                      <Space>
                        <Tag color={conflict.severity === 'error' ? 'error' : 'warning'}>
                          {conflict.type}
                        </Tag>
                        {conflict.source_fields && (
                          <span>源字段: {conflict.source_fields.join(', ')}</span>
                        )}
                        {conflict.target_field && (
                          <span>目标字段: {conflict.target_field}</span>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </>
        )}
      </Modal>
    </div>
  );
};

export default FieldMapping;
