import { useState } from 'react';
import {
  Card,
  Button,
  Tag,
  Space,
  Alert,
  Spin,
  Descriptions,
  Progress,
  Empty,
  List,
  Modal,
  Typography,
  Steps,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  SafetyOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  RobotOutlined,
  ScanOutlined,
  FileProtectOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sensitivityAI } from '@/services/data';

const { Text } = Typography;

interface SensitivityScanPanelProps {
  datasetId?: string;
  tableName?: string;
  databaseName?: string;
  columns?: Array<{ name: string; type: string; description?: string }>;
  onMaskingApply?: (rule: any) => void;
  visible?: boolean;
  onClose?: () => void;
}

function AISensitivityScanPanel({
  datasetId,
  tableName,
  databaseName,
  columns = [],
  onMaskingApply,
  visible = true,
  onClose,
}: SensitivityScanPanelProps) {
  const queryClient = useQueryClient();

  // 状态管理
  const [currentStep, setCurrentStep] = useState<number>(0);

  // AI 敏感数据扫描 - 直接返回结果
  const { data: scanResult, isLoading: isScanning } = useQuery({
    queryKey: ['sensitivityScan', datasetId, tableName, columns],
    queryFn: () =>
      sensitivityAI.scan({
        dataset_id: datasetId || '',
        table_name: tableName || '',
        columns,
      }),
    enabled: currentStep === 1,
  });

  // 处理开始扫描
  const handleStartScan = () => {
    if (!datasetId && !tableName) {
      Modal.warning({
        title: '缺少信息',
        content: '请先选择要扫描的数据集或表',
      });
      return;
    }
    setCurrentStep(1);
  };

  // 扫描结果数据
  const scanResultData = scanResult?.data?.data;
  const scanProgress = scanResultData ? 100 : 0;

  const steps = [
    {
      title: '准备扫描',
      description: '确认扫描目标',
      icon: <ScanOutlined />,
    },
    {
      title: 'AI 扫描中',
      description: '分析列敏感度',
      icon: <RobotOutlined />,
    },
    {
      title: '查看结果',
      description: '配置脱敏规则',
      icon: <FileProtectOutlined />,
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <SafetyOutlined />
          <span>AI 敏感数据扫描</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1200}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        currentStep === 0 && (
          <Button
            key="scan"
            type="primary"
            icon={<ScanOutlined />}
            onClick={handleStartScan}
            loading={isScanning}
            disabled={!datasetId && !tableName}
          >
            开始扫描
          </Button>
        ),
        currentStep === 1 && (
          <Button
            key="refresh"
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['sensitivityScanResult'] })}
          >
            刷新状态
          </Button>
        ),
        currentStep === 2 && (
          <Button
            key="close"
            onClick={onClose}
          >
            完成
          </Button>
        ),
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 提示信息 */}
        <Alert
          message="AI 助手将自动识别表中的敏感数据"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>基于列名、数据类型、样例值智能识别敏感信息</li>
              <li>支持个人身份、财务、健康、联系方式等多种敏感类型</li>
              <li>提供一键应用脱敏规则功能</li>
            </ul>
          }
          type="info"
          showIcon
        />

        {/* 扫描目标信息 */}
        {(datasetId || tableName) && (
          <Descriptions size="small" column={3} bordered>
            {datasetId && <Descriptions.Item label="数据集ID">{datasetId}</Descriptions.Item>}
            {databaseName && <Descriptions.Item label="数据库">{databaseName}</Descriptions.Item>}
            {tableName && <Descriptions.Item label="表名">{tableName}</Descriptions.Item>}
            <Descriptions.Item label="列数量">{columns.length}</Descriptions.Item>
          </Descriptions>
        )}

        {/* 步骤指示器 */}
        <Card size="small">
          <Steps
            current={currentStep}
            items={steps.map((step, idx) => ({
              ...step,
              status: idx < currentStep ? 'finish' : undefined,
            }))}
          />
        </Card>

        {/* Step 0: 准备扫描 */}
        {currentStep === 0 && (
          <Card title="扫描配置" extra={<Tag color="blue">准备中</Tag>}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong>扫描范围</Text>
                <div style={{ marginTop: 8 }}>
                  <Space wrap>
                    {columns.map((col) => (
                      <Tag key={col.name}>{col.name}</Tag>
                    ))}
                  </Space>
                </div>
              </div>
              <Alert
                message="扫描说明"
                description="AI 将分析每列的数据特征，包括列名、数据类型、样例值，判断是否包含敏感信息。扫描过程可能需要一些时间，请耐心等待。"
                type="info"
              />
            </Space>
          </Card>
        )}

        {/* Step 1: 扫描中 */}
        {currentStep === 1 && (
          <Card title="扫描进度" extra={<Tag color="processing">扫描中</Tag>}>
            {scanResultData ? (
              <Empty
                description="扫描完成"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => setCurrentStep(2)}
                >
                  查看结果
                </Button>
              </Empty>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} align="center">
                <Progress
                  type="circle"
                  percent={scanProgress}
                  status="active"
                  size={120}
                />
                <Text type="secondary">
                  {isScanning ? 'AI 正在分析数据...' : '扫描完成'}
                </Text>
              </Space>
            )}
          </Card>
        )}

        {/* Step 2: 扫描结果 */}
        {currentStep === 2 && scanResultData && (
          <>
            {/* 扫描摘要 */}
            <Row gutter={16}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="扫描列数"
                    value={scanResultData.columns_scanned || 0}
                    prefix={<ScanOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="敏感列数"
                    value={scanResultData.sensitive_found || 0}
                    valueStyle={{ color: '#cf1322' }}
                    prefix={<WarningOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="敏感率"
                    value={scanResultData.columns_scanned > 0
                      ? ((scanResultData.sensitive_found || 0) / scanResultData.columns_scanned * 100).toFixed(1)
                      : '0.0'}
                    suffix="%"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 敏感数据分类统计 */}
            {scanResultData.breakdown && (
              <Card title="敏感数据分类" size="small">
                <Row gutter={16}>
                  {Object.entries(scanResultData.breakdown).map(([type, count]) => (
                    <Col span={6} key={type}>
                      <Card size="small">
                        <Statistic
                          title={type.toUpperCase()}
                          value={count as number}
                          valueStyle={{ fontSize: 20, color: count > 0 ? '#cf1322' : '#999' }}
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            )}

            {/* AI 建议 */}
            <Card title="AI 安全建议" size="small">
              <List
                size="small"
                dataSource={[
                  '建议对敏感字段启用数据脱敏',
                  '定期审查敏感数据访问权限',
                  '对敏感数据操作进行审计日志记录',
                ]}
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
          </>
        )}
      </Space>
    </Modal>
  );
}

export default AISensitivityScanPanel;
