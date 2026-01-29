import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Upload,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  UploadOutlined,
  SearchOutlined,
  SyncOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { UploadFile } from 'antd';
import agentService from '@/services/agent-service';
import type {
  KnowledgeBase,
  KnowledgeDocument,
  RetrievalTestResult,
} from '@/services/agent-service';

const { Option } = Select;
const { TextArea } = Input;
const { Dragger } = Upload;

function KnowledgePage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [testResult, setTestResult] = useState<RetrievalTestResult | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const [form] = Form.useForm();
  const [testForm] = Form.useForm();

  // 获取知识库列表
  const { data: kbData, isLoading: isLoadingList } = useQuery({
    queryKey: ['knowledge-bases', page, pageSize, statusFilter],
    queryFn: () =>
      agentService.getKnowledgeBases({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
  });

  // 获取知识库详情（包含文档列表）
  const { data: kbDetailData } = useQuery({
    queryKey: ['knowledge-base-detail', selectedKB?.kb_id],
    queryFn: () => agentService.getKnowledgeBase(selectedKB!.kb_id),
    enabled: !!selectedKB && isDetailDrawerOpen,
  });

  // 创建知识库
  const createMutation = useMutation({
    mutationFn: agentService.createKnowledgeBase,
    onSuccess: () => {
      message.success('知识库创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
    onError: () => {
      message.error('知识库创建失败');
    },
  });

  // 更新知识库
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof agentService.updateKnowledgeBase>[1] }) =>
      agentService.updateKnowledgeBase(id, data),
    onSuccess: () => {
      message.success('知识库更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
    onError: () => {
      message.error('知识库更新失败');
    },
  });

  // 删除知识库
  const deleteMutation = useMutation({
    mutationFn: agentService.deleteKnowledgeBase,
    onSuccess: () => {
      message.success('知识库删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
    onError: () => {
      message.error('知识库删除失败');
    },
  });

  // 上传文档
  const uploadMutation = useMutation({
    mutationFn: ({ kbId, formData }: { kbId: string; formData: FormData }) =>
      agentService.uploadToKnowledgeBase(kbId, formData),
    onSuccess: () => {
      message.success('文档上传成功');
      setIsUploadModalOpen(false);
      setFileList([]);
      queryClient.invalidateQueries({ queryKey: ['knowledge-base-detail'] });
    },
    onError: () => {
      message.error('文档上传失败');
    },
  });

  // 删除文档
  const deleteDocMutation = useMutation({
    mutationFn: ({ kbId, docId }: { kbId: string; docId: string }) =>
      agentService.deleteKnowledgeDocument(kbId, docId),
    onSuccess: () => {
      message.success('文档删除成功');
      queryClient.invalidateQueries({ queryKey: ['knowledge-base-detail'] });
    },
    onError: () => {
      message.error('文档删除失败');
    },
  });

  // 测试检索
  const testMutation = useMutation({
    mutationFn: ({ kbId, data }: { kbId: string; data: Parameters<typeof agentService.testRetrieval>[1] }) =>
      agentService.testRetrieval(kbId, data),
    onSuccess: (result) => {
      setTestResult(result.data);
    },
    onError: () => {
      message.error('检索测试失败');
    },
  });

  // 重建索引
  const rebuildMutation = useMutation({
    mutationFn: (kbId: string) => agentService.rebuildKnowledgeIndex(kbId),
    onSuccess: () => {
      message.success('索引重建已启动');
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-base-detail'] });
    },
    onError: () => {
      message.error('索引重建失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      ready: 'green',
      indexing: 'blue',
      error: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      ready: '就绪',
      indexing: '索引中',
      error: '错误',
    };
    return texts[status] || status;
  };

  const getDocStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      indexed: 'green',
      failed: 'red',
    };
    return colors[status] || 'default';
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: KnowledgeBase) => (
        <a
          onClick={() => {
            setSelectedKB(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '向量模型',
      dataIndex: 'embedding_model',
      key: 'embedding_model',
      render: (model: string) => <Tag>{model}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={status === 'ready' ? <CheckCircleOutlined /> : status === 'indexing' ? <LoadingOutlined /> : undefined}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '文档数 / 向量数',
      key: 'counts',
      render: (_: unknown, record: KnowledgeBase) => (
        <Space>
          <FileTextOutlined /> {record.document_count}
          <DatabaseOutlined /> {record.vector_count}
        </Space>
      ),
    },
    {
      title: '分块配置',
      key: 'chunking',
      render: (_: unknown, record: KnowledgeBase) => (
        <Tag>{record.chunk_size} / {record.chunk_overlap}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: KnowledgeBase) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedKB(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个知识库吗？"
            onConfirm={() => deleteMutation.mutate(record.kb_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  const handleUpdate = () => {
    form.validateFields().then((values) => {
      updateMutation.mutate({
        id: selectedKB!.kb_id,
        data: values,
      });
    });
  };

  const handleUpload = () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }
    const formData = new FormData();
    fileList.forEach((file) => {
      if (file.originFileObj) {
        formData.append('files', file.originFileObj);
      }
    });

    uploadMutation.mutate({
      kbId: selectedKB!.kb_id,
      formData,
    });
  };

  const handleTest = () => {
    testForm.validateFields().then((values) => {
      testMutation.mutate({
        kbId: selectedKB!.kb_id,
        data: {
          query: values.query,
          top_k: values.top_k,
          score_threshold: values.score_threshold,
          search_type: values.search_type,
        },
      });
    });
  };

  const docColumns = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      ellipsis: true,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag
          color={getDocStatusColor(status)}
          icon={status === 'indexed' ? <CheckCircleOutlined /> : status === 'failed' ? <ExclamationCircleOutlined /> : undefined}
        >
          {status === 'indexed' ? '已索引' : status === 'failed' ? '失败' : '待处理'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: KnowledgeDocument) => (
        <Popconfirm
          title="确定要删除这个文档吗？"
          onConfirm={() => deleteDocMutation.mutate({ kbId: selectedKB!.kb_id, docId: record.doc_id })}
          okText="确定"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="知识库管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            创建知识库
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="ready">就绪</Option>
            <Option value="indexing">索引中</Option>
            <Option value="error">错误</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={kbData?.data?.knowledge_bases || []}
          rowKey="kb_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: kbData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建知识库模态框 */}
      <Modal
        title="创建知识库"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="知识库名称"
            name="name"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="请输入知识库名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="向量模型"
            name="embedding_model"
            initialValue="text-embedding-ada-002"
          >
            <Select>
              <Option value="text-embedding-ada-002">OpenAI Ada-002</Option>
              <Option value="text-embedding-3-small">OpenAI Embedding-3 Small</Option>
              <Option value="bge-large-zh">BGE Large ZH</Option>
              <Option value="m3e-base">M3E Base</Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="分块大小" name="chunk_size" initialValue={500}>
                <InputNumber min={100} max={2000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="重叠大小" name="chunk_overlap" initialValue={50}>
                <InputNumber min={0} max={500} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑知识库模态框 */}
      <Modal
        title="编辑知识库"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="知识库名称"
            name="name"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="请输入知识库名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="向量模型" name="embedding_model">
            <Select>
              <Option value="text-embedding-ada-002">OpenAI Ada-002</Option>
              <Option value="text-embedding-3-small">OpenAI Embedding-3 Small</Option>
              <Option value="bge-large-zh">BGE Large ZH</Option>
              <Option value="m3e-base">M3E Base</Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="分块大小" name="chunk_size">
                <InputNumber min={100} max={2000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="重叠大小" name="chunk_overlap">
                <InputNumber min={0} max={500} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 知识库详情抽屉 */}
      <Drawer
        title="知识库详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedKB(null);
        }}
        width={800}
      >
        {selectedKB && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="名称" span={2}>
                {selectedKB.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedKB.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="向量模型">
                <Tag>{selectedKB.embedding_model}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedKB.status)}>{getStatusText(selectedKB.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="分块配置">
                {selectedKB.chunk_size} / {selectedKB.chunk_overlap}
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedKB.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedKB.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedKB.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {kbDetailData?.data && (
              <Row gutter={16} style={{ marginTop: 24 }}>
                <Col span={8}>
                  <Statistic title="文档数量" value={selectedKB.document_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="向量数量" value={selectedKB.vector_count} />
                </Col>
                <Col span={8}>
                  {selectedKB.status === 'indexing' && (
                    <Button
                      icon={<SyncOutlined />}
                      onClick={() => rebuildMutation.mutate(selectedKB.kb_id)}
                      loading={rebuildMutation.isPending}
                    >
                      重建索引
                    </Button>
                  )}
                </Col>
              </Row>
            )}

            <div style={{ marginTop: 24 }}>
              <Card
                title="文档列表"
                extra={
                  <Button
                    type="primary"
                    icon={<UploadOutlined />}
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    上传文档
                  </Button>
                }
              >
                <Table
                  columns={docColumns}
                  dataSource={kbDetailData?.data?.documents || []}
                  rowKey="doc_id"
                  loading={!kbDetailData?.data}
                  pagination={false}
                  size="small"
                />
              </Card>
            </div>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<SearchOutlined />}
                  onClick={() => {
                    testForm.resetFields();
                    setTestResult(null);
                    setIsTestModalOpen(true);
                  }}
                >
                  测试检索
                </Button>
                <Button
                  icon={<EditOutlined />}
                  onClick={() => {
                    form.setFieldsValue(selectedKB);
                    setIsDetailDrawerOpen(false);
                    setIsEditModalOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Popconfirm
                  title="确定要删除这个知识库吗？"
                  onConfirm={() => deleteMutation.mutate(selectedKB.kb_id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* 上传文档模态框 */}
      <Modal
        title="上传文档"
        open={isUploadModalOpen}
        onCancel={() => {
          setIsUploadModalOpen(false);
          setFileList([]);
        }}
        footer={[
          <Button key="cancel" onClick={() => setIsUploadModalOpen(false)}>
            取消
          </Button>,
          <Button
            key="upload"
            type="primary"
            loading={uploadMutation.isPending}
            onClick={handleUpload}
          >
            上传
          </Button>,
        ]}
      >
        <Dragger
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          beforeUpload={() => false}
          multiple
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p style={{ marginTop: 8 }}>点击或拖拽文件到此区域上传</p>
          <p style={{ color: '#999' }}>支持 TXT, PDF, MD, DOCX 等格式</p>
        </Dragger>
      </Modal>

      {/* 测试检索模态框 */}
      <Modal
        title="测试知识库检索"
        open={isTestModalOpen}
        onCancel={() => setIsTestModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsTestModalOpen(false)}>
            关闭
          </Button>,
          <Button key="test" type="primary" loading={testMutation.isPending} onClick={handleTest}>
            测试
          </Button>,
        ]}
        width={700}
      >
        <Form form={testForm} layout="vertical">
          <Form.Item
            label="查询内容"
            name="query"
            rules={[{ required: true, message: '请输入查询内容' }]}
          >
            <TextArea rows={3} placeholder="请输入要检索的内容" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="返回数量" name="top_k" initialValue={5}>
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="相似度阈值" name="score_threshold" initialValue={0.5}>
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="检索类型" name="search_type" initialValue="vector">
                <Select>
                  <Option value="vector">向量检索</Option>
                  <Option value="hybrid">混合检索</Option>
                  <Option value="keyword">关键词检索</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
        {testResult && (
          <Card size="small" title="检索结果" style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 8 }}>
              <Tag>找到 {testResult.total_results} 条相关结果</Tag>
              <Tag>{testResult.search_type}</Tag>
            </div>
            {testResult.results.map((result, index) => (
              <Card
                key={result.chunk_id}
                size="small"
                style={{ marginBottom: 8 }}
                title={`结果 ${index + 1} (相似度: ${(result.score * 100).toFixed(2)}%)`}
              >
                <p>{result.content}</p>
                <div style={{ fontSize: 12, color: '#999' }}>
                  来源: {result.source.file_name}
                </div>
              </Card>
            ))}
          </Card>
        )}
      </Modal>
    </div>
  );
}

export default KnowledgePage;
