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
  DownloadOutlined,
  ReloadOutlined,
  ScanOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  FileWordOutlined,
  TableOutlined,
  CopyOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { ocrApi } from '@/services/ocr';

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
  { value: 'report', label: '报告' },
  { value: 'table', label: '表格' },
  { value: 'general', label: '通用文档' }
];

export const OCRPage: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [extractionType, setExtractionType] = useState<string>('general');
  const [templateId, setTemplateId] = useState<string | undefined>();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [resultModalVisible, setResultModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

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

  // 获取任务结果
  const { data: resultData, isLoading: resultLoading } = useQuery({
    queryKey: ['ocr-result', selectedTaskId],
    queryFn: () => ocrApi.getTaskResult(selectedTaskId!),
    enabled: !!selectedTaskId && resultModalVisible
  });

  // 上传处理
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return await ocrApi.createTask(formData, {
        extraction_type: extractionType,
        template_id: templateId
      });
    },
    onSuccess: () => {
      message.success('文档上传成功，正在识别...');
      setFileList([]);
      setActiveTab('tasks');
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

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

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
                    onChange={setExtractionType}
                  >
                    {DOCUMENT_TYPES.map(type => (
                      <Option key={type.value} value={type.value}>
                        {type.label}
                      </Option>
                    ))}
                  </Select>
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

      {/* 结果详情弹窗 */}
      <Modal
        title="识别结果"
        open={resultModalVisible}
        onCancel={() => setResultModalVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setResultModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="export"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => {
              if (resultData) {
                handleDownload(
                  JSON.stringify(resultData.structured_data, null, 2),
                  `ocr_result_${selectedTaskId}.json`
                );
              }
            }}
          >
            导出JSON
          </Button>
        ]}
      >
        {resultLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>加载中...</p>
          </div>
        ) : resultData ? (
          <Tabs defaultActiveKey="structured">
            <TabPane tab="结构化数据" key="structured">
              <Descriptions bordered size="small" column={1}>
                {Object.entries(resultData.structured_data || {}).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
              {Object.keys(resultData.structured_data || {}).length === 0 && (
                <Empty description="未提取到结构化数据" />
              )}
            </TabPane>

            <TabPane tab={`表格 (${resultData.tables.length})`} key="tables">
              {resultData.tables.map((table, index) => (
                <div key={table.id} style={{ marginBottom: 24 }}>
                  <Text strong>表格 #{index + 1} (第{table.page_number}页)</Text>
                  <Table
                    style={{ marginTop: 8 }}
                    columns={table.headers.map((h, i) => ({
                      title: h,
                      dataIndex: i,
                      key: i
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
                </div>
              ))}
              {resultData.tables.length === 0 && (
                <Empty description="未识别到表格" />
              )}
            </TabPane>

            <TabPane tab="原始文本" key="raw">
              <div
                style={{
                  maxHeight: 400,
                  overflow: 'auto',
                  padding: 12,
                  background: '#f5f5f5',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace'
                }}
              >
                {resultData.raw_text || '无文本内容'}
              </div>
              {resultData.raw_text && (
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => handleCopyText(resultData.raw_text!)}
                  style={{ marginTop: 8 }}
                >
                  复制文本
                </Button>
              )}
            </TabPane>

            {resultData.validation_issues.length > 0 && (
              <TabPane tab={`验证问题 (${resultData.validation_issues.length})`} key="validation">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {resultData.validation_issues.map((issue, index) => (
                    <Alert
                      key={index}
                      type={issue.severity === 'error' ? 'error' : 'warning'}
                      message={issue.field}
                      description={issue.error}
                    />
                  ))}
                </Space>
              </TabPane>
            )}
          </Tabs>
        ) : null}
      </Modal>
    </div>
  );
};

export default OCRPage;
