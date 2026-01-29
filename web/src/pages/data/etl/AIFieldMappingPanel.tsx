import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Alert,
  Spin,
  Empty,
  List,
  Tooltip,
  Modal,
  Progress,
  Segmented,
  Descriptions,
  Typography,
  Select,
} from 'antd';
import {
  PartitionOutlined,
  CheckCircleOutlined,
  SwapOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { etlAI } from '@/services/data';

const { Text } = Typography;

interface FieldMappingPanelProps {
  sourceFields?: Array<{ name: string; type: string; description?: string }>;
  targetFields?: Array<{ name: string; type: string; description?: string }>;
  sourceTable?: string;
  targetTable?: string;
  onMappingApply?: (mappings: any[]) => void;
  visible?: boolean;
  onClose?: () => void;
}

interface FieldMapping {
  source_field: string;
  target_field: string;
  confidence: number;
  mapping_type: string;
  transformation: string;
  source_type: string;
  target_type: string;
  needs_conversion: boolean;
}

interface Transformation {
  source_field: string;
  target_field: string;
  source_type: string;
  target_type: string;
  needs_conversion: boolean;
  sql?: string;
  description: string;
}

function AIFieldMappingPanel({
  sourceFields = [],
  targetFields = [],
  sourceTable,
  targetTable,
  onMappingApply,
  visible = true,
  onClose,
}: FieldMappingPanelProps) {
  const queryClient = useQueryClient();

  // 状态管理
  const [mappingMode, setMappingMode] = useState<'auto' | 'manual'>('auto');
  const [selectedMappings, setSelectedMappings] = useState<FieldMapping[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [manualSourceField, setManualSourceField] = useState<string>('');
  const [manualTargetField, setManualTargetField] = useState<string>('');

  // AI 字段映射推荐
  const { data: aiMappingData, isLoading: isLoadingMapping } = useQuery({
    queryKey: ['etlAIFieldMapping', sourceFields, targetFields],
    queryFn: () =>
      etlAI.suggestFieldMapping({
        source_fields: sourceFields,
        target_fields: targetFields,
      }),
    enabled: mappingMode === 'auto' && sourceFields.length > 0 && targetFields.length > 0,
  });

  // 获取转换建议
  const { data: transformData, isLoading: isLoadingTransform } = useQuery({
    queryKey: ['etlAITransformation', sourceFields, targetFields],
    queryFn: () =>
      etlAI.suggestTransformation({
        source_columns: sourceFields,
        target_columns: targetFields,
      }),
    });

  // 丰富 API 返回的映射数据，补充类型信息
  const enrichedMappings = useMemo((): FieldMapping[] => {
    const apiMappings = aiMappingData?.data?.data?.mappings || [];
    return apiMappings.map((m): FieldMapping => {
      const sourceField = sourceFields.find((f) => f.name === m.source_field);
      const targetField = targetFields.find((f) => f.name === m.target_field);
      return {
        ...m,
        source_type: sourceField?.type || 'varchar',
        target_type: targetField?.type || 'varchar',
        needs_conversion: sourceField?.type !== targetField?.type,
      };
    });
  }, [aiMappingData?.data?.data?.mappings, sourceFields, targetFields]);

  // 应用映射
  const applyMappingMutation = useMutation({
    mutationFn: async (mappings: FieldMapping[]) => {
      // 这里可以调用实际的 API 保存映射
      console.log('Applying mappings:', mappings);
      return { success: true };
    },
    onSuccess: () => {
      if (onMappingApply) {
        const mappingsToApply = selectedMappings.length > 0 ? selectedMappings : enrichedMappings;
        onMappingApply(mappingsToApply);
      }
      queryClient.invalidateQueries({ queryKey: ['fieldMappings'] });
    },
  });

  // 处理 AI 映射
  const handleGenerateMapping = () => {
    setIsGenerating(true);
    // 触发查询
    setTimeout(() => setIsGenerating(false), 500);
  };

  // 处理映射选择
  const handleMappingToggle = (sourceField: string, targetField: string) => {
    const exists = selectedMappings.find(
      (m) => m.source_field === sourceField && m.target_field === targetField
    );
    if (exists) {
      setSelectedMappings((prev) => prev.filter((m) => m !== exists));
    } else {
      // 从 AI 结果或手动添加
      const aiMapping = aiMappingData?.data?.data?.mappings?.find(
        (m: FieldMapping) => m.source_field === sourceField && m.target_field === targetField
      );
      const manualMapping: FieldMapping = {
        source_field: sourceField,
        target_field: targetField,
        confidence: aiMapping?.confidence || 0.5,
        mapping_type: aiMapping?.mapping_type || 'manual',
        transformation: aiMapping?.transformation || '',
        source_type: sourceFields.find((f) => f.name === sourceField)?.type || 'varchar',
        target_type: targetFields.find((f) => f.name === targetField)?.type || 'varchar',
        needs_conversion: sourceFields.find((f) => f.name === sourceField)?.type !==
                     targetFields.find((f) => f.name === targetField)?.type,
      };
      setSelectedMappings((prev) => [...prev, manualMapping]);
    }
  };

  // 获取映射类型颜色
  const getMappingTypeColor = (type: string) => {
    switch (type) {
      case 'exact':
        return 'green';
      case 'fuzzy':
        return 'blue';
      case 'semantic':
        return 'purple';
      case 'manual':
        return 'default';
      default:
        return 'default';
    }
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'green';
    if (confidence >= 0.7) return 'blue';
    if (confidence >= 0.5) return 'orange';
    return 'default';
  };

  // 表格列定义
  const mappingColumns = [
    {
      title: '源字段',
      dataIndex: 'source_field',
      key: 'source_field',
      render: (text: string, record: FieldMapping) => (
        <Space direction="vertical" size={0}>
          <Text>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.source_type}
          </Text>
        </Space>
      ),
    },
    {
      title: '目标字段',
      dataIndex: 'target_field',
      key: 'target_field',
      render: (text: string, record: FieldMapping) => (
        <Space direction="vertical" size={0}>
          <Text>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.target_type}
          </Text>
        </Space>
      ),
    },
    {
      title: '映射类型',
      dataIndex: 'mapping_type',
      key: 'mapping_type',
      render: (type: string) => <Tag color={getMappingTypeColor(type)}>{type}</Tag>,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (value: number) => (
        <Progress
          type="circle"
          percent={value * 100}
          width={50}
          strokeColor={getConfidenceColor(value)}
          format={(percent) => `${percent.toFixed(0)}%`}
        />
      ),
    },
    {
      title: '转换',
      dataIndex: 'needs_conversion',
      key: 'needs_conversion',
      render: (needsConversion: boolean, record: FieldMapping) => (
        <Space>
          {needsConversion ? (
            <Tag color="orange">需要转换</Tag>
          ) : (
            <Tag color="green">直接映射</Tag>
          )}
          {record.transformation && (
            <Tooltip title={record.transformation}>
              <Tag color="blue">转换</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: FieldMapping) => (
        <Button
          type="link"
          size="small"
          danger
          onClick={() => {
            setSelectedMappings((prev) => prev.filter((m) => m !== record));
          }}
        >
          移除
        </Button>
      ),
    },
  ];

  // 未映射的源字段
  const unmappedSourceFields = sourceFields.filter(
    (f) =>
      !aiMappingData?.data?.data?.mappings?.some((m) => m.source_field === f.name) &&
      !selectedMappings.some((m) => m.source_field === f.name)
  );

  // 未映射的目标字段
  const unmappedTargetFields = targetFields.filter(
    (f) =>
      !aiMappingData?.data?.data?.mappings?.some((m) => m.target_field === f.name) &&
      !selectedMappings.some((m) => m.target_field === f.name)
  );

  // 映射统计
  const displayMappings: FieldMapping[] = mappingMode === 'auto'
    ? enrichedMappings
    : selectedMappings;

  return (
    <Modal
      title={
        <Space>
          <PartitionOutlined />
          <span>AI 字段映射助手</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="apply"
          type="primary"
          disabled={displayMappings.length === 0}
          onClick={() => applyMappingMutation.mutate(displayMappings)}
          loading={applyMappingMutation.isPending}
        >
          应用映射 ({displayMappings.length})
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 提示信息 */}
        <Alert
          message="AI 助手将基于字段名称、数据类型自动推荐映射关系"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>完全匹配：字段名相同的直接映射</li>
              <li>模糊匹配：名称相似的智能推断映射</li>
              <li>语义匹配：基于业务语义的映射推荐</li>
            </ul>
          }
          type="info"
          showIcon
        />

        {/* 源表和目标表信息 */}
        {(sourceTable || targetTable) && (
          <Descriptions size="small" column={2} bordered>
            {sourceTable && <Descriptions.Item label="源表">{sourceTable}</Descriptions.Item>}
            {targetTable && <Descriptions.Item label="目标表">{targetTable}</Descriptions.Item>}
            <Descriptions.Item label="源字段数">{sourceFields.length}</Descriptions.Item>
            <Descriptions.Item label="目标字段数">{targetFields.length}</Descriptions.Item>
          </Descriptions>
        )}

        {/* 模式切换 */}
        <Card
          extra={
            <Segmented
              options={[
                { label: 'AI 自动推荐', value: 'auto' },
                { label: '手动配置', value: 'manual' },
              ]}
              value={mappingMode}
              onChange={(value) => {
                setMappingMode(value as 'auto' | 'manual');
                setSelectedMappings([]);
              }}
            />
          }
        >
          {/* AI 自动推荐模式 */}
          {mappingMode === 'auto' && (
            <div>
              {isLoadingMapping ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin tip="AI 正在分析字段关系..." />
                </div>
              ) : aiMappingData?.data?.data?.mappings &&
                aiMappingData.data.data.mappings.length > 0 ? (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Text strong>
                        AI 推荐了 {aiMappingData.data.data.mappings.length} 个字段映射
                      </Text>
                      <Text type="secondary">
                        (覆盖率: {(aiMappingData.data.data.coverage * 100).toFixed(1)}%)
                      </Text>
                    </Space>
                  </div>
                  <Table
                    columns={mappingColumns}
                    dataSource={aiMappingData.data.data.mappings}
                    rowKey={(record, idx) => `${record.source_field}-${idx}`}
                    pagination={false}
                    size="small"
                  />
                </>
              ) : (
                <Empty
                  description="无法生成映射推荐，请检查字段配置"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}

              {/* 未映射字段提示 */}
              {(unmappedSourceFields.length > 0 || unmappedTargetFields.length > 0) && (
                <Alert
                  message="部分字段未映射"
                  description={
                    <div>
                      {unmappedSourceFields.length > 0 && (
                        <div>
                          未映射源字段: {unmappedSourceFields.map((f) => f.name).join(', ')}
                        </div>
                      )}
                      {unmappedTargetFields.length > 0 && (
                        <div>
                          未映射目标字段: {unmappedTargetFields.map((f) => f.name).join(', ')}
                        </div>
                      )}
                    </div>
                  }
                  type="warning"
                />
              )}
            </div>
          )}

          {/* 手动配置模式 */}
          {mappingMode === 'manual' && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Alert
                  message="手动配置映射关系"
                  description="选择源字段和目标字段后，点击下方添加按钮创建映射"
                  type="info"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <Text strong>添加新映射</Text>
                <div style={{ marginTop: 8 }}>
                  <Space>
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择源字段"
                      options={sourceFields.map((f) => ({
                        label: `${f.name} (${f.type})`,
                        value: f.name,
                      }))}
                      onChange={(value) => setManualSourceField(value as string)}
                    />
                    <SwapOutlined />
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择目标字段"
                      options={targetFields.map((f) => ({
                        label: `${f.name} (${f.type})`,
                        value: f.name,
                      }))}
                      onChange={(value) => setManualTargetField(value as string)}
                    />
                    <Button type="primary" icon={<CheckCircleOutlined />}>
                      添加
                    </Button>
                  </Space>
                </div>
              </div>

              {selectedMappings.length > 0 ? (
                <Table
                  columns={mappingColumns}
                  dataSource={selectedMappings}
                  rowKey={(record, idx) => `manual-${idx}`}
                  pagination={false}
                  size="small"
                />
              ) : (
                <Empty description="暂无映射配置" />
              )}
            </div>
          )}
        </Card>

        {/* 转换建议 */}
        {transformData?.data?.data?.transformations &&
          transformData.data.data.transformations.length > 0 && (
          <Card title="数据转换建议" size="small">
            <List
              size="small"
              dataSource={transformData.data.data.transformations}
              renderItem={(item: Transformation) => (
                <List.Item>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <div>
                      <Text strong>{item.source_field}</Text>
                      <Text type="secondary"> → </Text>
                      <Text strong>{item.target_field}</Text>
                    </div>
                    <div>
                      <Tag color={item.needs_conversion ? 'orange' : 'green'}>
                        {item.description}
                      </Tag>
                      {item.sql && (
                        <Text code style={{ marginLeft: 8 }}>
                          {item.sql}
                        </Text>
                      )}
                    </div>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        )}
      </Space>
    </Modal>
  );
}

export default AIFieldMappingPanel;
