import React, { useState, useCallback } from 'react';
import {
  Card,
  Upload,
  Button,
  Tabs,
  Table,
  Space,
  message,
  Spin,
  Typography,
  Tag,
  Progress,
  Descriptions,
  Alert,
  Select,
  Divider,
  Row,
  Col,
  Statistic,
  Empty,
} from 'antd';
import {
  UploadOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileTextOutlined,
  ScanOutlined,
  TableOutlined,
  DownloadOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import {
  extractDocument,
  ocrImage,
  extractStructuredData,
  getOCRStatus,
  DocumentExtractionData,
  OCRServiceStatus,
  StructuredExtractionResult,
} from '../../../services/alldata';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Dragger } = Upload;

const OCRPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('document');
  const [loading, setLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<OCRServiceStatus | null>(null);
  const [extractionResult, setExtractionResult] = useState<DocumentExtractionData | null>(null);
  const [structuredResult, setStructuredResult] = useState<StructuredExtractionResult | null>(null);
  const [ocrText, setOcrText] = useState<string>('');
  const [ocrConfidence, setOcrConfidence] = useState<number>(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [structuredType, setStructuredType] = useState<'invoice' | 'id_card' | 'contract'>('invoice');

  // 加载服务状态
  const loadServiceStatus = useCallback(async () => {
    try {
      const response = await getOCRStatus();
      if (response.code === 0) {
        setServiceStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to load OCR status:', error);
    }
  }, []);

  React.useEffect(() => {
    loadServiceStatus();
  }, [loadServiceStatus]);

  // 文档提取
  const handleDocumentExtract = async (file: File) => {
    setLoading(true);
    try {
      const response = await extractDocument({
        file,
        extract_tables: true,
        extract_images: false,
        ocr_images: true,
      });
      if (response.code === 0) {
        setExtractionResult(response.data);
        message.success('文档内容提取成功');
      } else {
        message.error(response.message || '提取失败');
      }
    } catch (error) {
      message.error('文档提取失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 图片 OCR
  const handleImageOCR = async (file: File) => {
    setLoading(true);
    try {
      const response = await ocrImage({ file });
      if (response.code === 0) {
        setOcrText(response.data.text);
        setOcrConfidence(response.data.average_confidence);
        message.success('OCR 识别成功');
      } else {
        message.error(response.message || 'OCR 失败');
      }
    } catch (error) {
      message.error('OCR 识别失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 结构化数据提取
  const handleStructuredExtract = async (file: File) => {
    setLoading(true);
    try {
      const response = await extractStructuredData({
        file,
        data_type: structuredType,
      });
      if (response.code === 0) {
        setStructuredResult(response.data);
        message.success('结构化数据提取成功');
      } else {
        message.error(response.message || '提取失败');
      }
    } catch (error) {
      message.error('结构化数据提取失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 上传配置
  const uploadProps: UploadProps = {
    beforeUpload: (file) => {
      setFileList([file]);
      return false;
    },
    fileList,
    onRemove: () => {
      setFileList([]);
      setExtractionResult(null);
      setOcrText('');
      setStructuredResult(null);
    },
    maxCount: 1,
  };

  // 处理提取
  const handleExtract = () => {
    if (fileList.length === 0) {
      message.warning('请先上传文件');
      return;
    }
    const file = fileList[0] as unknown as File;
    if (activeTab === 'document') {
      handleDocumentExtract(file);
    } else if (activeTab === 'image') {
      handleImageOCR(file);
    } else if (activeTab === 'structured') {
      handleStructuredExtract(file);
    }
  };

  // 复制文本
  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  // 下载结果
  const handleDownload = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 获取文件图标
  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return <FilePdfOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />;
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || ''))
      return <FileImageOutlined style={{ fontSize: 48, color: '#1890ff' }} />;
    if (['doc', 'docx'].includes(ext || ''))
      return <FileWordOutlined style={{ fontSize: 48, color: '#2f54eb' }} />;
    return <FileTextOutlined style={{ fontSize: 48, color: '#52c41a' }} />;
  };

  // 渲染表格数据
  const renderTables = () => {
    if (!extractionResult?.tables?.length) return null;

    return (
      <div style={{ marginTop: 16 }}>
        <Title level={5}>
          <TableOutlined /> 提取的表格 ({extractionResult.tables.length})
        </Title>
        {extractionResult.tables.map((table, index) => (
          <Card key={index} size="small" title={`表格 ${index + 1} (第 ${table.page} 页)`} style={{ marginBottom: 16 }}>
            <Table
              dataSource={table.data.map((row, rowIndex) => ({
                key: rowIndex,
                ...row.reduce((acc, cell, cellIndex) => ({ ...acc, [`col${cellIndex}`]: cell }), {}),
              }))}
              columns={table.data[0]?.map((_, colIndex) => ({
                title: `列 ${colIndex + 1}`,
                dataIndex: `col${colIndex}`,
                key: `col${colIndex}`,
              })) || []}
              size="small"
              pagination={false}
              scroll={{ x: true }}
            />
            <div style={{ marginTop: 8 }}>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => handleCopyText(table.markdown)}
              >
                复制为 Markdown
              </Button>
            </div>
          </Card>
        ))}
      </div>
    );
  };

  // 渲染结构化数据
  const renderStructuredData = () => {
    if (!structuredResult?.structured_data) return null;

    const data = structuredResult.structured_data;
    const items = Object.entries(data).map(([key, value]) => ({
      key,
      label: key,
      children: typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value),
    }));

    return (
      <Descriptions
        bordered
        column={2}
        size="small"
        items={items}
      />
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <ScanOutlined /> 非结构化文档 OCR
      </Title>
      <Paragraph type="secondary">
        支持 PDF、图片、Word 等文档的文字识别和内容提取
      </Paragraph>

      {/* 服务状态 */}
      {serviceStatus && (
        <Alert
          message={
            <Space>
              <CheckCircleOutlined style={{ color: serviceStatus.enabled ? '#52c41a' : '#ff4d4f' }} />
              <Text>
                OCR 服务状态: {serviceStatus.enabled ? '可用' : '不可用'}
              </Text>
              <Text type="secondary">
                可用引擎: {Object.entries(serviceStatus.available_engines)
                  .filter(([, v]) => v)
                  .map(([k]) => k)
                  .join(', ') || '无'}
              </Text>
            </Space>
          }
          type={serviceStatus.enabled ? 'success' : 'warning'}
          showIcon={false}
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={24}>
        {/* 左侧：上传和操作 */}
        <Col span={10}>
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              <TabPane tab="文档提取" key="document">
                <Paragraph type="secondary">
                  支持 PDF、Word、文本文件，提取文字内容和表格
                </Paragraph>
              </TabPane>
              <TabPane tab="图片 OCR" key="image">
                <Paragraph type="secondary">
                  识别图片中的文字，支持中英文
                </Paragraph>
              </TabPane>
              <TabPane tab="结构化提取" key="structured">
                <Paragraph type="secondary">
                  从发票、身份证、合同等文档提取结构化信息
                </Paragraph>
                <Select
                  value={structuredType}
                  onChange={setStructuredType}
                  style={{ width: '100%', marginBottom: 16 }}
                  options={[
                    { value: 'invoice', label: '发票信息提取' },
                    { value: 'id_card', label: '身份证信息提取' },
                    { value: 'contract', label: '合同关键信息提取' },
                  ]}
                />
              </TabPane>
            </Tabs>

            <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 PDF、图片（JPG/PNG/BMP）、Word（DOC/DOCX）、文本文件
              </p>
            </Dragger>

            <Button
              type="primary"
              icon={<ScanOutlined />}
              onClick={handleExtract}
              loading={loading}
              block
            >
              开始提取
            </Button>
          </Card>
        </Col>

        {/* 右侧：结果展示 */}
        <Col span={14}>
          <Card title="提取结果" style={{ minHeight: 500 }}>
            <Spin spinning={loading}>
              {/* 文档提取结果 */}
              {activeTab === 'document' && extractionResult && (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Statistic title="字符数" value={extractionResult.char_count} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="页数" value={extractionResult.page_count} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="表格数" value={extractionResult.tables?.length || 0} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="图片数" value={extractionResult.image_count} />
                    </Col>
                  </Row>

                  <Divider orientation="left">提取的文本</Divider>
                  <div style={{ maxHeight: 300, overflow: 'auto', marginBottom: 16 }}>
                    <Paragraph>
                      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {extractionResult.text || '无文本内容'}
                      </pre>
                    </Paragraph>
                  </div>
                  <Space>
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() => handleCopyText(extractionResult.text)}
                    >
                      复制文本
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownload(extractionResult.text, 'extracted_text.txt')}
                    >
                      下载文本
                    </Button>
                  </Space>

                  {renderTables()}

                  {extractionResult.errors?.length > 0 && (
                    <Alert
                      type="warning"
                      message="提取过程中的警告"
                      description={extractionResult.errors.join('\n')}
                      style={{ marginTop: 16 }}
                    />
                  )}
                </div>
              )}

              {/* 图片 OCR 结果 */}
              {activeTab === 'image' && ocrText && (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={12}>
                      <Statistic title="字符数" value={ocrText.length} />
                    </Col>
                    <Col span={12}>
                      <div>
                        <Text type="secondary">识别置信度</Text>
                        <Progress
                          percent={Math.round(ocrConfidence * 100)}
                          status={ocrConfidence > 0.8 ? 'success' : ocrConfidence > 0.5 ? 'normal' : 'exception'}
                        />
                      </div>
                    </Col>
                  </Row>

                  <Divider orientation="left">识别结果</Divider>
                  <div style={{ maxHeight: 400, overflow: 'auto', marginBottom: 16 }}>
                    <Paragraph>
                      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {ocrText}
                      </pre>
                    </Paragraph>
                  </div>
                  <Space>
                    <Button icon={<CopyOutlined />} onClick={() => handleCopyText(ocrText)}>
                      复制文本
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownload(ocrText, 'ocr_result.txt')}
                    >
                      下载文本
                    </Button>
                  </Space>
                </div>
              )}

              {/* 结构化提取结果 */}
              {activeTab === 'structured' && structuredResult && (
                <div>
                  <Tag color="blue" style={{ marginBottom: 16 }}>
                    {structuredResult.data_type === 'invoice' && '发票信息'}
                    {structuredResult.data_type === 'id_card' && '身份证信息'}
                    {structuredResult.data_type === 'contract' && '合同信息'}
                  </Tag>

                  <Divider orientation="left">提取的结构化数据</Divider>
                  {renderStructuredData()}

                  <Divider orientation="left">原始文本摘要</Divider>
                  <Paragraph type="secondary" ellipsis={{ rows: 5, expandable: true }}>
                    {structuredResult.raw_text}
                  </Paragraph>

                  <div style={{ marginTop: 16 }}>
                    <Space>
                      <Button
                        icon={<CopyOutlined />}
                        onClick={() =>
                          handleCopyText(JSON.stringify(structuredResult.structured_data, null, 2))
                        }
                      >
                        复制 JSON
                      </Button>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={() =>
                          handleDownload(
                            JSON.stringify(structuredResult.structured_data, null, 2),
                            `${structuredResult.data_type}_data.json`
                          )
                        }
                      >
                        下载 JSON
                      </Button>
                    </Space>
                  </div>
                </div>
              )}

              {/* 空状态 */}
              {!extractionResult && !ocrText && !structuredResult && (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description='上传文件并点击"开始提取"查看结果'
                />
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default OCRPage;
