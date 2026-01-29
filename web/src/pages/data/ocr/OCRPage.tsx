/**
 * OCR文档识别页面
 * 支持非结构化文档（PDF、Word、Excel、图片、扫描件）的智能识别
 * 集成新的OCR服务API
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Upload,
  Select,
  Table,
  Tag,
  Progress,
  Space,
  Modal,
  Descriptions,
  message,
  Tabs,
  Tooltip,
  Badge,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  Typography,
  Alert
} from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ScanOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  FileWordOutlined,
  TableOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { DocumentViewer } from '@/components/alldata/DocumentViewer';
import { ocrApi, EnhancedOCRResult } from '@/services/ocr';

const { TabPane } = Tabs;
const { Option } = Select;
const { Dragger } = Upload;
const { Text } = Typography;

interface OCRTask {
  id: string;
  document_name: string;
  document_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  result_summary?: {
    pages_processed: number;
    tables_found: number;
    text_length: number;
    fields_extracted: number;
    validation_issues: number;
  };
  error_message?: string;
}

interface ExtractionResult {
  task_id: string;
  structured_data: Record<string, any>;
  raw_text?: string;
  tables: Array<{
    id: string;
    table_index: number;
    page_number: number;
    headers: string[];
    rows: string[][];
    confidence: number;
  }>;
  confidence_score: number;
  validation_issues: Array<{
    field: string;
    error: string;
    severity: 'error' | 'warning';
  }>;
}

const STATUS_CONFIG = {
  pending: { text: '待处理', color: 'default', icon: null },
  processing: { text: '处理中', color: 'processing', icon: <LoadingOutlined /> },
  completed: { text: '已完成', color: 'success', icon: <CheckCircleOutlined /> },
  failed: { text: '失败', color: 'error', icon: null }
};

const DOCUMENT_TYPES = [
  { value: 'invoice', label: '增值税发票' },
  { value: 'contract', label: '合同' },
  { value: 'purchase_order', label: '采购订单' },
  { value: 'delivery_note', label: '送货单' },
  { value: 'quotation', label: '报价单' },
  { value: 'receipt', label: '收据' },
  { value: 'report', label: '报告' },
  { value: 'table', label: '表格' },
  { value: 'general', label: '通用文档' },
  { value: 'auto', label: '自动识别' }
];

export const OCRPage: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [extractionType, setExtractionType] = useState<string>('auto');
  const [templateId, setTemplateId] = useState<string | undefined>();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [resultModalVisible, setResultModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [enhancedResult, setEnhancedResult] = useState<EnhancedOCRResult | null>(null);
  const [autoDetectedType, setAutoDetectedType] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // 获取任务列表
  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['ocr-tasks', statusFilter],
    queryFn: () => ocrApi.getTasks({ status: statusFilter }),
    refetchInterval: (data) => {
      // 有处理中的任务时，每3秒刷新一次
      const hasProcessing = data?.tasks?.some(
        (t: OCRTask) => t.status === 'processing' || t.status === 'pending'
      );
      return hasProcessing ? 3000 : false;
    }
  });

  // 获取模板列表
  const { data: templatesData } = useQuery({
    queryKey: ['ocr-templates'],
    queryFn: () => ocrApi.getTemplates({ is_active: true })
  });

  // 获取增强任务结果
  const { data: enhancedResultData, isLoading: resultLoading } = useQuery({
    queryKey: ['ocr-enhanced-result', selectedTaskId],
    queryFn: () => ocrApi.getEnhancedTaskResult(selectedTaskId!),
    enabled: !!selectedTaskId && resultModalVisible,
    onSuccess: (data) => {
      setEnhancedResult(data);
    }
  });

  // 上传处理
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);

      let finalExtractionType = extractionType;

      // 如果选择自动识别，先进行类型检测
      if (extractionType === 'auto') {
        try {
          const detectionResult = await ocrApi.detectDocumentType(file);
          finalExtractionType = detectionResult.detected_type;
          setAutoDetectedType(detectionResult.detected_type);
          message.info(`自动识别文档类型: ${getDocumentTypeLabel(detectionResult.detected_type)}`);

          // 如果有建议的模板，使用第一个
          if (detectionResult.suggested_templates.length > 0 && !templateId) {
            setTemplateId(detectionResult.suggested_templates[0]);
          }
        } catch (error) {
          console.error('文档类型识别失败:', error);
          finalExtractionType = 'general';
        }
      }

      formData.append('file', file);
      return await ocrApi.createTask(formData, {
        extraction_type: finalExtractionType,
        template_id: templateId
      });
    },
    onSuccess: () => {
      message.success('文档上传成功，正在识别...');
      setFileList([]);
      setActiveTab('tasks');
      setAutoDetectedType(null);
      queryClient.invalidateQueries({ queryKey: ['ocr-tasks'] });
    },
    onError: (error: any) => {
      message.error(`上传失败: ${error.message || '未知错误'}`);
    }
  });

  // 删除任务
  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => ocrApi.deleteTask(taskId),
    onSuccess: () => {
      message.success('任务已删除');
      queryClient.invalidateQueries({ queryKey: ['ocr-tasks'] });
    }
  });

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    fileList: fileList,
    accept: '.pdf,.jpg,.jpeg,.png,.bmp,.docx,.doc,.xlsx,.xls,.tiff,.webp',
    beforeUpload: (file) => {
      const isValidType = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/bmp',
        'image/tiff',
        'image/webp',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
      ].includes(file.type);

      if (!isValidType) {
        message.error('只支持PDF、图片、Word、Excel格式的文件');
        return Upload.LIST_IGNORE;
      }

      const isLt20M = file.size / 1024 / 1024 < 20;
      if (!isLt20M) {
        message.error('文件大小不能超过20MB');
        return Upload.LIST_IGNORE;
      }

      return false;
    },
    onChange: (info) => {
      setFileList(info.fileList);
    },
    onRemove: () => {
      setFileList([]);
    }
  };

  const handleUpload = () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }
    uploadMutation.mutate(fileList[0].originFileObj as File);
  };

  const handleViewResult = (taskId: string) => {
    setSelectedTaskId(taskId);
    setResultModalVisible(true);
  };

  const handleDelete = (taskId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后任务及所有相关数据将被清除，无法恢复。',
      onOk: () => deleteMutation.mutate(taskId)
    });
  };

  // 任务列表表格列
  const columns = [
    {
      title: '文档名称',
      dataIndex: 'document_name',
      key: 'document_name',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <Space>
          {getFileIcon(text)}
          <Tooltip title={text}>
            <span>{text}</span>
          </Tooltip>
        </Space>
      )
    },
    {
      title: '文档类型',
      dataIndex: 'document_type',
      key: 'document_type',
      width: 100,
      render: (type: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          pdf: { label: 'PDF', color: 'red' },
          image: { label: '图片', color: 'blue' },
          word: { label: 'Word', color: 'geekblue' },
          excel: { label: 'Excel', color: 'green' },
          scanned_pdf: { label: '扫描PDF', color: 'orange' }
        };
        const config = typeMap[type] || { label: type, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string, record: OCRTask) => {
        const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG];
        return (
          <Space>
            {config.icon}
            <Tag color={config.color}>{config.text}</Tag>
            {status === 'processing' && (
              <Progress
                percent={Math.round(record.progress)}
                size="small"
                style={{ width: 60 }}
              />
            )}
          </Space>
        );
      }
    },
    {
      title: '识别结果',
      key: 'result',
      width: 150,
      render: (_: any, record: OCRTask) => {
        if (record.status !== 'completed' || !record.result_summary) {
          return '-';
        }
        return (
          <Space size="small">
            <Tooltip title="处理页数">
              <Tag>{record.result_summary.pages_processed}页</Tag>
            </Tooltip>
            <Tooltip title="发现表格">
              <Tag>{record.result_summary.tables_found}表</Tag>
            </Tooltip>
            <Tooltip title="提取字段">
              <Tag>{record.result_summary.fields_extracted}字段</Tag>
            </Tooltip>
          </Space>
        );
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: OCRTask) => (
        <Space size="small">
          {record.status === 'completed' && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewResult(record.id)}
            >
              查看
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return <FilePdfOutlined style={{ color: '#ff4d4f' }} />;
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || ''))
      return <FileImageOutlined style={{ color: '#1890ff' }} />;
    if (['doc', 'docx'].includes(ext || ''))
      return <FileWordOutlined style={{ color: '#2f54eb' }} />;
    if (['xls', 'xlsx'].includes(ext || ''))
      return <TableOutlined style={{ color: '#52c41a' }} />;
    return <FileTextOutlined style={{ color: '#8c8c8c' }} />;
  };

  const getDocumentTypeLabel = (type: string) => {
    const found = DOCUMENT_TYPES.find(t => t.value === type);
    return found?.label || type;
  };

  const handleSaveResult = (data: Record<string, any>) => {
    // 保存修改后的结果
    if (selectedTaskId) {
      ocrApi.verifyTask(selectedTaskId, {
        corrections: data,
        verified_by: 'current_user'
      }).then(() => {
        message.success('结果已保存');
        queryClient.invalidateQueries({ queryKey: ['ocr-tasks'] });
      });
    }
  };

  // 统计数据
  const stats = {
    total: tasksData?.total || 0,
    pending: tasksData?.tasks?.filter((t: OCRTask) => t.status === 'pending').length || 0,
    processing: tasksData?.tasks?.filter((t: OCRTask) => t.status === 'processing').length || 0,
    completed: tasksData?.tasks?.filter((t: OCRTask) => t.status === 'completed').length || 0,
    failed: tasksData?.tasks?.filter((t: OCRTask) => t.status === 'failed').length || 0
  };

  return (
    <div className="ocr-page">
      <Card
        title={
          <Space>
            <ScanOutlined />
            <span>OCR文档识别</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['ocr-tasks'] })}
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        支持PDF、图片、Word、Excel等格式的智能识别
      </Card>

      <div className="page-content">
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic title="总任务数" value={stats.total} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="处理中"
                value={stats.processing}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已完成"
                value={stats.completed}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="失败"
                value={stats.failed}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>

        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane
              tab={
                <span>
                  上传文档
                  {stats.pending + stats.processing > 0 && (
                    <Badge count={stats.pending + stats.processing} style={{ marginLeft: 8 }} />
                  )}
                </span>
              }
              key="upload"
            >
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Alert
                  message="智能文档识别"
                  description="支持PDF文档识别（含扫描件OCR）、图片文字识别、Word文档解析、Excel表格提取、智能信息抽取（发票、合同、报告等）"
                  type="info"
                  showIcon
                />

                <Space>
                  <Text strong>文档类型:</Text>
                  <Select
                    style={{ width: 200 }}
                    value={extractionType}
                    onChange={(value) => {
                      setExtractionType(value);
                      setAutoDetectedType(null);
                    }}
                  >
                    {DOCUMENT_TYPES.map(type => (
                      <Option key={type.value} value={type.value}>
                        {type.label}
                      </Option>
                    ))}
                  </Select>
                  {autoDetectedType && (
                    <Tag color="blue">自动识别为: {getDocumentTypeLabel(autoDetectedType)}</Tag>
                  )}
                </Space>

                {extractionType !== 'general' && templatesData?.length > 0 && (
                  <Space>
                    <Text strong>提取模板:</Text>
                    <Select
                      style={{ width: 300 }}
                      placeholder="选择模板（可选）"
                      value={templateId}
                      onChange={setTemplateId}
                      allowClear
                    >
                      {templatesData.map((template: any) => (
                        <Option key={template.id} value={template.id}>
                          {template.name} {template.category && <Tag size="small">{template.category}</Tag>}
                        </Option>
                      ))}
                    </Select>
                  </Space>
                )}

                <Dragger {...uploadProps} style={{ padding: '40px' }}>
                  <p className="ant-upload-drag-icon">
                    <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持PDF、JPG、PNG、Word、Excel等格式，单个文件不超过20MB
                  </p>
                </Dragger>

                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  size="large"
                  loading={uploadMutation.isPending}
                  onClick={handleUpload}
                  disabled={fileList.length === 0}
                >
                  开始识别
                </Button>
              </Space>
            </TabPane>

            <TabPane
              tab={
                <span>
                  识别任务
                  <Badge count={stats.pending + stats.processing} style={{ marginLeft: 8 }} />
                </span>
              }
              key="tasks"
            >
              <Space style={{ marginBottom: 16 }}>
                <Text strong>状态筛选:</Text>
                <Select
                  style={{ width: 120 }}
                  placeholder="全部状态"
                  value={statusFilter}
                  onChange={setStatusFilter}
                  allowClear
                >
                  <Option value="pending">待处理</Option>
                  <Option value="processing">处理中</Option>
                  <Option value="completed">已完成</Option>
                  <Option value="failed">失败</Option>
                </Select>
              </Space>

              <Table
                columns={columns}
                dataSource={tasksData?.tasks || []}
                rowKey="id"
                loading={isLoading}
                pagination={{
                  total: tasksData?.total || 0,
                  pageSize: 20,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`
                }}
                scroll={{ x: 1200 }}
              />
            </TabPane>
          </Tabs>
        </Card>
      </div>

      {/* 结果详情弹窗 - 使用新的 DocumentViewer */}
      <DocumentViewer
        visible={resultModalVisible}
        onClose={() => {
          setResultModalVisible(false);
          setEnhancedResult(null);
        }}
        result={enhancedResult}
        loading={resultLoading}
        onSave={handleSaveResult}
      />
    </div>
  );
};

export default OCRPage;
