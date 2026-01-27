/**
 * 文档预览组件
 * 支持PDF渲染、提取字段高亮、签名/印章区域标注、多页导航
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Table,
  Tag,
  Space,
  Button,
  Row,
  Col,
  Card,
  Descriptions,
  Alert,
  Progress,
  Badge,
  Tooltip,
  Empty,
  Spin,
  Statistic
} from 'antd';
import {
  FileTextOutlined,
  TableOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  StampOutlined,
  EditOutlined,
  SaveOutlined,
  DownloadOutlined,
  CheckSquareOutlined,
  CloseSquareOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons';
import type { EnhancedOCRResult } from '@/services/ocr';
import './DocumentViewer.css';

const { TabPane } = Tabs;

interface DocumentViewerProps {
  visible: boolean;
  onClose: () => void;
  result: EnhancedOCRResult | null;
  loading?: boolean;
  onSave?: (data: Record<string, any>) => void;
}

const SIGNATURE_LABELS: Record<string, string> = {
  party_a_signature: '甲方签字',
  party_b_signature: '乙方签字',
  principal_signature: '委托方签字',
  agent_signature: '受托方签字',
  legal_rep_signature: '法定代表人签字',
  authorized_rep_signature: '授权代表签字',
  payee_signature: '收款人签字',
  payer_signature: '付款人签字',
  handler_signature: '经办人签字',
  auditor_signature: '审核人签字'
};

const SEAL_LABELS: Record<string, string> = {
  official_seal: '公章',
  contract_seal: '合同章',
  finance_seal: '财务专用章',
  legal_rep_seal: '法人章',
  invoice_seal: '发票专用章',
  company_seal: '收款单位盖章'
};

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  visible,
  onClose,
  result,
  loading = false,
  onSave
}) => {
  const [editableData, setEditableData] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState('structured');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (result?.structured_data) {
      setEditableData(result.structured_data);
    }
  }, [result]);

  const handleFieldChange = (key: string, value: any) => {
    setEditableData(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    if (onSave) {
      onSave(editableData);
      setHasChanges(false);
    }
  };

  const getValidationIcon = (valid: boolean) => {
    if (valid) return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
  };

  const renderStructuredData = () => {
    if (!result || Object.keys(result.structured_data || {}).length === 0) {
      return <Empty description="未提取到结构化数据" />;
    }

    const data = editableData;
    const entries = Object.entries(data);

    return (
      <div className="structured-data-view">
        {hasChanges && (
          <Alert
            message="您有未保存的修改"
            type="warning"
            action={
              <Button size="small" type="primary" onClick={handleSave}>
                保存修改
              </Button>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        <Descriptions bordered size="small" column={2}>
          {entries.map(([key, value]) => {
            const isComplex = typeof value === 'object' && value !== null;
            const displayValue = isComplex ? JSON.stringify(value) : String(value ?? '');

            return (
              <Descriptions.Item
                key={key}
                label={
                  <Space>
                    <span>{key}</span>
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        const newValue = prompt(`修改 ${key}:`, displayValue);
                        if (newValue !== null) {
                          handleFieldChange(key, newValue);
                        }
                      }}
                    />
                  </Space>
                }
              >
                <Tooltip title={displayValue}>
                  <span
                    style={{
                      display: 'inline-block',
                      maxWidth: 200,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {displayValue || '-'}
                  </span>
                </Tooltip>
              </Descriptions.Item>
            );
          })}
        </Descriptions>
      </div>
    );
  };

  const renderTables = () => {
    if (!result || result.tables.length === 0) {
      return <Empty description="未识别到表格" />;
    }

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {result.tables.map((table, index) => (
          <Card
            key={table.id}
            size="small"
            title={`表格 #${index + 1} (第${table.page_number}页)`}
            extra={<Tag color={table.confidence > 0.8 ? 'success' : 'warning'}>
              置信度: {(table.confidence * 100).toFixed(1)}%
            </Tag>}
          >
            <Table
              columns={table.headers.map((h, i) => ({
                title: h,
                dataIndex: i,
                key: i,
                ellipsis: true
              }))}
              dataSource={table.rows.map((row, i) => ({
                key: i,
                ...row
              }))}
              pagination={false}
              size="small"
              bordered
              scroll={{ x: true }}
            />
          </Card>
        ))}
      </Space>
    );
  };

  const renderValidation = () => {
    if (!result) return null;

    const { cross_field_validation, completeness } = result;

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 跨字段校验结果 */}
        <Card size="small" title="跨字段校验">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {getValidationIcon(cross_field_validation?.valid ?? true)}
              <span>
                {cross_field_validation?.valid ? '校验通过' : '校验失败'}
              </span>
            </div>

            {cross_field_validation?.errors?.map((error, index) => (
              <Alert
                key={`error-${index}`}
                type="error"
                message={error.rule}
                description={
                  <div>
                    <p>{error.description}</p>
                    {error.expected !== undefined && (
                      <p>期望值: {String(error.expected)}</p>
                    )}
                    {error.actual !== undefined && (
                      <p>实际值: {String(error.actual)}</p>
                    )}
                  </div>
                }
              />
            ))}

            {cross_field_validation?.warnings?.map((warning, index) => (
              <Alert
                key={`warning-${index}`}
                type="warning"
                message={warning.rule}
                description={
                  <div>
                    <p>{warning.description}</p>
                    {warning.expected !== undefined && (
                      <p>期望值: {String(warning.expected)}</p>
                    )}
                    {warning.actual !== undefined && (
                      <p>实际值: {String(warning.actual)}</p>
                    )}
                  </div>
                }
              />
            ))}

            {(!cross_field_validation?.errors?.length &&
              !cross_field_validation?.warnings?.length) && (
              <Alert type="success" message="所有校验规则通过" />
            )}
          </Space>
        </Card>

        {/* 完整性检查 */}
        <Card size="small" title="完整性检查">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Progress
                  type="circle"
                  percent={completeness?.completeness_rate || 0}
                  format={percent => `${percent}%`}
                />
              </Col>
              <Col span={12}>
                <Space direction="vertical">
                  <div>
                    {getValidationIcon(completeness?.valid ?? true)}
                    <span>{completeness?.valid ? '完整' : '不完整'}</span>
                  </div>
                  <div>
                    缺少必填字段: {completeness?.missing_required?.length || 0} 个
                  </div>
                </Space>
              </Col>
            </Row>

            {completeness?.missing_required?.map((field, index) => (
              <Tag key={index} color="error">
                {field.name} ({field.key})
              </Tag>
            ))}
          </Space>
        </Card>

        {/* 基础验证问题 */}
        {result.validation_issues?.length > 0 && (
          <Card size="small" title="字段验证问题">
            <Space direction="vertical" style={{ width: '100%' }}>
              {result.validation_issues.map((issue, index) => (
                <Alert
                  key={index}
                  type={issue.severity === 'error' ? 'error' : 'warning'}
                  message={issue.field}
                  description={issue.error}
                />
              ))}
            </Space>
          </Card>
        )}
      </Space>
    );
  };

  const renderLayout = () => {
    if (!result) return null;

    const { layout_info, confidence_score } = result;

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 置信度 */}
        <Card size="small" title="识别置信度">
          <Progress
            percent={Math.round((confidence_score || 0) * 100)}
            status={confidence_score > 0.8 ? 'success' : confidence_score > 0.5 ? 'normal' : 'exception'}
          />
        </Card>

        {/* 签名区域 */}
        <Card
          size="small"
          title={
            <Space>
              <StampOutlined />
              <span>签名区域</span>
              {layout_info?.has_signatures && (
                <Badge count={layout_info.signature_regions?.length || 0} />
              )}
            </Space>
          }
        >
          {layout_info?.signature_regions?.length ? (
            <Space wrap>
              {layout_info.signature_regions.map((region, index) => (
                <Tag key={index} color="blue" icon={<StampOutlined />}>
                  {SIGNATURE_LABELS[region.label] || region.label}
                  {region.page && ` (第${region.page}页)`}
                </Tag>
              ))}
            </Space>
          ) : (
            <Empty description="未检测到签名区域" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        {/* 印章区域 */}
        <Card
          size="small"
          title={
            <Space>
              <StampOutlined />
              <span>印章区域</span>
              {layout_info?.has_seals && (
                <Badge count={layout_info.seal_regions?.length || 0} />
              )}
            </Space>
          }
        >
          {layout_info?.seal_regions?.length ? (
            <Space wrap>
              {layout_info.seal_regions.map((region, index) => (
                <Tag key={index} color="red" icon={<StampOutlined />}>
                  {SEAL_LABELS[region.label] || region.label}
                  {region.page && ` (第${region.page}页)`}
                </Tag>
              ))}
            </Space>
          ) : (
            <Empty description="未检测到印章区域" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Space>
    );
  };

  const renderRawText = () => {
    if (!result?.raw_text) {
      return <Empty description="无文本内容" />;
    }

    return (
      <div
        style={{
          maxHeight: 400,
          overflow: 'auto',
          padding: 12,
          background: '#f5f5f5',
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          fontSize: 12
        }}
      >
        {result.raw_text}
      </div>
    );
  };

  return (
    <Modal
      title="识别结果详情"
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="export"
          icon={<DownloadOutlined />}
          onClick={() => {
            if (result) {
              const data = {
                ...result,
                structured_data: editableData
              };
              const blob = new Blob([JSON.stringify(data, null, 2)], {
                type: 'application/json'
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `ocr_result_${result.task_id}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }
          }}
        >
          导出JSON
        </Button>,
        hasChanges && (
          <Button key="save" type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            保存修改
          </Button>
        )
      ]}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>加载中...</p>
        </div>
      ) : result ? (
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <span>
                <FileTextOutlined />
                结构化数据
              </span>
            }
            key="structured"
          >
            {renderStructuredData()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <TableOutlined />
                表格 ({result.tables.length})
              </span>
            }
            key="tables"
          >
            {renderTables()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <CheckCircleOutlined />
                校验结果
                {(!result.cross_field_validation?.valid ||
                  result.validation_issues?.length > 0) && (
                  <Badge dot style={{ marginLeft: 8 }} />
                )}
              </span>
            }
            key="validation"
          >
            {renderValidation()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <StampOutlined />
                布局分析
                {(result.layout_info?.has_signatures || result.layout_info?.has_seals) && (
                  <Badge dot style={{ marginLeft: 8 }} />
                )}
              </span>
            }
            key="layout"
          >
            {renderLayout()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <InfoCircleOutlined />
                原始文本
              </span>
            }
            key="raw"
          >
            {renderRawText()}
          </TabPane>
        </Tabs>
      ) : (
        <Empty description="暂无数据" />
      )}
    </Modal>
  );
};

export default DocumentViewer;
