import { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Upload,
  Tag,
  Drawer,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UploadProps } from 'antd';
import dayjs from 'dayjs';
import bisheng, { type IndexedDocument } from '@/services/bisheng';

const { Dragger } = Upload;
const { Option } = Select;
const { TextArea } = Input;

function DocumentsPage() {
  const queryClient = useQueryClient();

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isPreviewDrawerOpen, setIsPreviewDrawerOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<IndexedDocument | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<string | undefined>();
  const [uploadForm] = Form.useForm();
  const [fileList, setFileList] = useState<any[]>([]);

  // 获取文档列表
  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['documents', selectedCollection],
    queryFn: () => bisheng.getDocuments({ collection: selectedCollection, limit: 100 }),
  });

  // 上传文档
  const uploadMutation = useMutation({
    mutationFn: bisheng.uploadDocument,
    onSuccess: () => {
      message.success('文档上传成功');
      setIsUploadModalOpen(false);
      setFileList([]);
      uploadForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: any) => {
      message.error(`文档上传失败: ${error.message || '未知错误'}`);
    },
  });

  // 删除文档
  const deleteMutation = useMutation({
    mutationFn: bisheng.deleteDocument,
    onSuccess: () => {
      message.success('文档删除成功');
      setIsPreviewDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: any) => {
      message.error(`文档删除失败: ${error.message || '未知错误'}`);
    },
  });

  const handleUpload = async () => {
    const values = uploadForm.getFieldsValue();

    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    const formData = new FormData();
    formData.append('file', fileList[0].originFileObj);
    if (values.title) {
      formData.append('title', values.title);
    }
    if (values.collection) {
      formData.append('collection', values.collection);
    }

    uploadMutation.mutate(formData);
  };

  const handlePreview = (doc: IndexedDocument) => {
    setSelectedDocument(doc);
    setIsPreviewDrawerOpen(true);
  };

  const handleDelete = (docId: string) => {
    deleteMutation.mutate(docId);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    fileList,
    beforeUpload: (file) => {
      const isValidText = file.type === 'text/plain' ||
                         file.type === 'text/markdown' ||
                         file.type === 'application/json' ||
                         file.name.endsWith('.txt') ||
                         file.name.endsWith('.md') ||
                         file.name.endsWith('.json') ||
                         file.name.endsWith('.html') ||
                         file.name.endsWith('.htm') ||
                         file.name.endsWith('.csv') ||
                         file.name.endsWith('.xml');

      if (!isValidText) {
        message.error('仅支持上传文本文件 (txt, md, json, html, csv, xml)');
        return Upload.LIST_IGNORE;
      }

      const isLt5M = file.size / 1024 / 1024 < 5;
      if (!isLt5M) {
        message.error('文件大小不能超过 5MB');
        return Upload.LIST_IGNORE;
      }

      setFileList([file]);
      return false;
    },
    onRemove: () => {
      setFileList([]);
    },
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      render: (fileName: string, record: IndexedDocument) => (
        <a onClick={() => handlePreview(record)}>{fileName}</a>
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string) => title || '-',
    },
    {
      title: '集合',
      dataIndex: 'collection_name',
      key: 'collection_name',
      width: 120,
      render: (collection: string) => <Tag color="blue">{collection}</Tag>,
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 100,
      render: (count: number) => (
        <Tag color="green">{count} 块</Tag>
      ),
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 120,
      render: (creator: string) => creator || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: IndexedDocument) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
            title="预览"
          >
            预览
          </Button>
          <Popconfirm
            title="确定要删除这个文档吗？"
            description="删除后将从向量数据库中移除，无法恢复"
            onConfirm={() => handleDelete(record.doc_id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" danger icon={<DeleteOutlined />} title="删除">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const collections = documentsData?.data?.collections || [];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>文档管理</span>
          </Space>
        }
        extra={
          <Space>
            <Select
              placeholder="筛选集合"
              style={{ width: 150 }}
              value={selectedCollection}
              onChange={setSelectedCollection}
              allowClear
            >
              {collections.map((c) => (
                <Option key={c} value={c}>
                  {c}
                </Option>
              ))}
            </Select>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setIsUploadModalOpen(true)}
            >
              上传文档
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documentsData?.data?.documents || []}
          rowKey="doc_id"
          loading={isLoading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            defaultPageSize: 20,
          }}
        />
      </Card>

      {/* 上传文档模态框 */}
      <Modal
        title="上传文档"
        open={isUploadModalOpen}
        onOk={handleUpload}
        onCancel={() => {
          setIsUploadModalOpen(false);
          setFileList([]);
          uploadForm.resetFields();
        }}
        confirmLoading={uploadMutation.isPending}
        width={600}
        okText="上传"
        cancelText="取消"
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item label="选择文件" required>
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持文本文件 (txt, md, json, html, csv, xml)，最大 5MB
              </p>
            </Dragger>
          </Form.Item>
          <Form.Item label="文档标题" name="title">
            <Input placeholder="留空则使用文件名" />
          </Form.Item>
          <Form.Item
            label="集合名称"
            name="collection"
            initialValue="default"
          >
            <Select placeholder="选择或输入集合名称">
              {collections.map((c) => (
                <Option key={c} value={c}>
                  {c}
                </Option>
              ))}
              <Option value="default">default</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 文档预览抽屉 */}
      <Drawer
        title="文档预览"
        placement="right"
        width={600}
        open={isPreviewDrawerOpen}
        onClose={() => {
          setIsPreviewDrawerOpen(false);
          setSelectedDocument(null);
        }}
        extra={
          <Space>
            <Popconfirm
              title="确定要删除这个文档吗？"
              description="删除后将从向量数据库中移除，无法恢复"
              onConfirm={() => selectedDocument && handleDelete(selectedDocument.doc_id)}
              okText="确定"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        {selectedDocument && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <p>
                <strong>文件名：</strong>
                {selectedDocument.file_name}
              </p>
              <p>
                <strong>标题：</strong>
                {selectedDocument.title || '-'}
              </p>
              <p>
                <strong>集合：</strong>
                <Tag color="blue">{selectedDocument.collection_name}</Tag>
              </p>
              <p>
                <strong>分块数：</strong>
                <Tag color="green">{selectedDocument.chunk_count} 块</Tag>
              </p>
              <p>
                <strong>创建人：</strong>
                {selectedDocument.created_by || '-'}
              </p>
              <p>
                <strong>创建时间：</strong>
                {dayjs(selectedDocument.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </p>
            </div>
            <div>
              <h4>内容预览</h4>
              <div
                style={{
                  padding: '12px',
                  background: '#f5f5f5',
                  borderRadius: '4px',
                  maxHeight: '400px',
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                }}
              >
                {selectedDocument.content || '(无内容)'}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default DocumentsPage;
