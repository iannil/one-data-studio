/**
 * OCR模板管理器组件
 * 用于管理文档提取模板
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Table,
  Space,
  Card,
  Tabs,
  message,
  Popconfirm,
  Tag,
  Row,
  Col,
  Alert,
  Spin,
  Tooltip,
  Empty,
  Upload
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  EyeOutlined,
  DownloadOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import type { OCRTemplate } from '@/services/data';
import { ocrService } from '@/services/data';
import './TemplateManager.css';

const { TextArea } = Input;
const { Option } = Select;

interface TemplateManagerProps {
  visible: boolean;
  onClose: () => void;
  onSave?: (template: OCRTemplate) => void;
}

const DOCUMENT_TYPES = [
  { value: 'invoice', label: '发票' },
  { value: 'contract', label: '合同' },
  { value: 'purchase_order', label: '采购订单' },
  { value: 'delivery_note', label: '送货单' },
  { value: 'quotation', label: '报价单' },
  { value: 'receipt', label: '收据' },
  { value: 'report', label: '报告' },
  { value: 'general', label: '通用文档' }
];

const CATEGORIES = [
  { value: 'financial', label: '财务' },
  { value: 'legal', label: '法律' },
  { value: 'procurement', label: '采购' },
  { value: 'logistics', label: '物流' },
  { value: 'sales', label: '销售' },
  { value: 'business', label: '业务' }
];

export const TemplateManager: React.FC<TemplateManagerProps> = ({
  visible,
  onClose,
  onSave
}) => {
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<OCRTemplate[]>([]);
  const [activeTab, setActiveTab] = useState('list');
  const [editingTemplate, setEditingTemplate] = useState<OCRTemplate | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible) {
      loadTemplates();
    }
  }, [visible]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await ocrService.listTemplates();
      setTemplates(response.data || []);
    } catch (error) {
      message.error('加载模板失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingTemplate({
      id: '',
      tenant_id: '',
      name: '',
      description: '',
      template_type: 'general',
      category: 'business',
      is_active: true,
      is_public: false,
      version: 1,
      extraction_rules: { fields: [] },
      usage_count: 0,
      success_rate: 0,
      created_at: '',
      updated_at: ''
    });
    form.resetFields();
    setActiveTab('editor');
  };

  const handleEdit = (template: OCRTemplate) => {
    setEditingTemplate(template);
    form.setFieldsValue(template);
    setActiveTab('editor');
  };

  const handleDelete = async (id: string) => {
    try {
      await ocrService.deleteTemplate(id);
      message.success('模板删除成功');
      loadTemplates();
    } catch (error) {
      message.error('模板删除失败');
    }
  };

  const handleDuplicate = async (template: OCRTemplate) => {
    const newOCRTemplate = {
      ...template,
      id: '',
      name: `${template.name} (副本)`,
      created_at: '',
      updated_at: ''
    };
    setEditingTemplate(newOCRTemplate);
    form.setFieldsValue(newOCRTemplate);
    setActiveTab('editor');
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      if (editingTemplate?.id) {
        await ocrService.updateTemplate(editingTemplate.id, values);
        message.success('模板更新成功');
      } else {
        await ocrService.createTemplate(values);
        message.success('模板创建成功');
      }

      if (onSave) {
        onSave(values);
      }

      loadTemplates();
      setActiveTab('list');
      setEditingTemplate(null);
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleLoadDefaults = async () => {
    try {
      await ocrService.loadDefaultTemplates();
      message.success('默认模板加载成功');
      loadTemplates();
    } catch (error) {
      message.error('加载默认模板失败');
    }
  };

  const handleExportOCRTemplate = (template: OCRTemplate) => {
    const dataStr = JSON.stringify(template, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `template_${template.template_type}_${template.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: OCRTemplate) => (
        <Space>
          {record.is_public && <Tag color="blue">公共</Tag>}
          {name}
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => {
        const docType = DOCUMENT_TYPES.find(t => t.value === type);
        return docType?.label || type;
      }
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 100,
      render: (rate: number) => `${rate}%`
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: OCRTemplate) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleDuplicate(record)}
            />
          </Tooltip>
          <Tooltip title="导出">
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleExportOCRTemplate(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个模板吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      )
    }
  ];

  const renderOCRTemplateList = () => (
    <div className="template-list">
      <div className="template-list-header">
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建模板
          </Button>
          <Button
            icon={<UploadOutlined />}
            onClick={handleLoadDefaults}
          >
            加载默认模板
          </Button>
        </Space>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : (
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      )}
    </div>
  );

  const renderOCRTemplateEditor = () => (
    <div className="template-editor">
      <Card
        title={editingTemplate?.id ? '编辑模板' : '新建模板'}
        extra={
          <Space>
            <Button onClick={() => setActiveTab('list')}>
              返回列表
            </Button>
            <Button type="primary" onClick={handleSave}>
              保存模板
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={editingTemplate || undefined}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="模板名称"
                name="name"
                rules={[{ required: true, message: '请输入模板名称' }]}
              >
                <Input placeholder="请输入模板名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="文档类型"
                name="type"
                rules={[{ required: true, message: '请选择文档类型' }]}
              >
                <Select placeholder="请选择文档类型">
                  {DOCUMENT_TYPES.map(type => (
                    <Option key={type.value} value={type.value}>
                      {type.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="分类"
                name="category"
                rules={[{ required: true, message: '请选择分类' }]}
              >
                <Select placeholder="请选择分类">
                  {CATEGORIES.map(cat => (
                    <Option key={cat.value} value={cat.value}>
                      {cat.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="状态"
                name="is_active"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="请输入模板描述" />
          </Form.Item>

          <Form.Item label="提取规则配置" name="extraction_rules">
            <TextArea
              rows={10}
              placeholder="请输入JSON格式的提取规则配置"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      </Card>

      <Card title="字段配置" style={{ marginTop: 16 }}>
        <Alert
          message="提示"
          description="在提取规则中定义需要提取的字段，包括字段名称、键名、是否必填等属性。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <p style={{ color: '#999' }}>
          示例配置：
          <pre style={{ background: '#f5f5f5', padding: 8 }}>
{`{
  "fields": [
    { "name": "发票号码", "key": "invoice_number", "required": true },
    { "name": "开票日期", "key": "invoice_date", "required": true }
  ]
}`}
          </pre>
        </p>
      </Card>
    </div>
  );

  return (
    <Modal
      title="模板管理"
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
      destroyOnClose
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="模板列表" key="list">
          {renderOCRTemplateList()}
        </Tabs.TabPane>
        <Tabs.TabPane
          tab={editingTemplate?.id ? '编辑模板' : '新建模板'}
          key="editor"
        >
          {renderOCRTemplateEditor()}
        </Tabs.TabPane>
      </Tabs>
    </Modal>
  );
};

export default TemplateManager;
