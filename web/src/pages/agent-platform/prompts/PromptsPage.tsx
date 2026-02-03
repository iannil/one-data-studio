import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import agentService from '@/services/agent-service';
import type { PromptTemplate } from '@/services/agent-service';

const { Option } = Select;
const { TextArea } = Input;

function PromptsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [testResult, setTestResult] = useState<{ result: string; usage?: { prompt_tokens: number; completion_tokens: number } } | null>(null);

  const [form] = Form.useForm();
  const [testForm] = Form.useForm();

  // 获取 Prompt 模板列表
  const { data: templatesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['prompt-templates', page, pageSize, categoryFilter],
    queryFn: () =>
      agentService.getPromptTemplates({
        page,
        page_size: pageSize,
        category: categoryFilter || undefined,
      }),
  });

  // 创建模板
  const createMutation = useMutation({
    mutationFn: agentService.createPromptTemplate,
    onSuccess: () => {
      message.success('Prompt 模板创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: () => {
      message.error('Prompt 模板创建失败');
    },
  });

  // 更新模板
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof agentService.updatePromptTemplate>[1] }) =>
      agentService.updatePromptTemplate(id, data),
    onSuccess: () => {
      message.success('Prompt 模板更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: () => {
      message.error('Prompt 模板更新失败');
    },
  });

  // 删除模板
  const deleteMutation = useMutation({
    mutationFn: agentService.deletePromptTemplate,
    onSuccess: () => {
      message.success('Prompt 模板删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: () => {
      message.error('Prompt 模板删除失败');
    },
  });

  // 测试模板
  const testMutation = useMutation({
    mutationFn: agentService.testPromptTemplate,
    onSuccess: (result) => {
      setTestResult(result.data);
    },
    onError: () => {
      message.error('测试失败');
    },
  });

  // 提取变量
  const extractVariables = (content: string): string[] => {
    const regex = /\{\{([^}]+)\}\}/g;
    const variables: string[] = [];
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (!variables.includes(match[1])) {
        variables.push(match[1]);
      }
    }
    return variables;
  };

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const variables = extractVariables(values.content);
      createMutation.mutate({
        ...values,
        variables,
      });
    });
  };

  const handleUpdate = () => {
    form.validateFields().then((values) => {
      const variables = extractVariables(values.content);
      updateMutation.mutate({
        id: selectedTemplate!.template_id,
        data: {
          ...values,
          variables,
        },
      });
    });
  };

  const handleTest = () => {
    testForm.validateFields().then((values) => {
      testMutation.mutate({
        content: selectedTemplate!.content,
        variables: values.variables,
        model: values.model,
      });
    });
  };

  const renderVariables = (variables: string[]) => {
    if (!variables || variables.length === 0) return '-';
    return (
      <Space size="small" wrap>
        {variables.map((v) => (
          <Tag key={v} color="blue">
            {'{{'} {v} {'}}'}
          </Tag>
        ))}
      </Space>
    );
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: PromptTemplate) => (
        <a
          onClick={() => {
            setSelectedTemplate(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (category ? <Tag color="purple">{category}</Tag> : '-'),
    },
    {
      title: '变量',
      dataIndex: 'variables',
      key: 'variables',
      render: (variables: string[]) => renderVariables(variables),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <>
          {tags?.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
          {tags?.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
      ),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 120,
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
      render: (_: unknown, record: PromptTemplate) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedTemplate(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={() => {
              setSelectedTemplate(record);
              // 预填充变量表单
              const initialValues: Record<string, string> = {};
              record.variables.forEach((v) => {
                initialValues[v] = '';
              });
              testForm.setFieldsValue({
                variables: initialValues,
                model: 'gpt-4',
              });
              setTestResult(null);
              setIsTestModalOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedTemplate(record);
              form.setFieldsValue(record);
              setIsEditModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个模板吗？"
            onConfirm={() => deleteMutation.mutate(record.template_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 生成变量表单
  const renderVariableFields = (variables?: string[]) => {
    if (!variables || variables.length === 0) return <div style={{ textAlign: 'center', padding: '20px' }}>模板中没有变量</div>;

    return (
      <Card size="small" title="变量值" style={{ marginTop: 16 }}>
        <Form.Item label="模型" name="model" initialValue="gpt-4">
          <Select>
            <Option value="gpt-4">GPT-4</Option>
            <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
            <Option value="claude-3-opus">Claude 3 Opus</Option>
            <Option value="claude-3-sonnet">Claude 3 Sonnet</Option>
          </Select>
        </Form.Item>
        {variables.map((v) => (
          <Form.Item key={v} label={v} name={['variables', v]} rules={[{ required: true, message: `请输入 ${v}` }]}>
            <Input placeholder={`请输入 ${v} 的值`} />
          </Form.Item>
        ))}
      </Card>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="Prompt 模板管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建模板
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="分类筛选"
            allowClear
            style={{ width: 150 }}
            onChange={setCategoryFilter}
            value={categoryFilter || undefined}
          >
            <Option value="chat">对话</Option>
            <Option value="agent">Agent</Option>
            <Option value="rag">RAG</Option>
            <Option value="code">代码生成</Option>
            <Option value="summary">摘要</Option>
            <Option value="translation">翻译</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={templatesData?.data?.templates || []}
          rowKey="template_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: templatesData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建模板模态框 */}
      <Modal
        title="新建 Prompt 模板"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="分类"
            name="category"
          >
            <Select placeholder="选择分类" allowClear>
              <Option value="chat">对话</Option>
              <Option value="agent">Agent</Option>
              <Option value="rag">RAG</Option>
              <Option value="code">代码生成</Option>
              <Option value="summary">摘要</Option>
              <Option value="translation">翻译</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="模板内容"
            name="content"
            rules={[{ required: true, message: '请输入模板内容' }]}
            extra="使用 {{变量名}} 来定义变量"
          >
            <TextArea
              rows={10}
              placeholder="例如：你是一个 {{role}}，请帮我 {{task}}。输入内容如下：{{input}}"
            />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑模板模态框 */}
      <Modal
        title="编辑 Prompt 模板"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="分类"
            name="category"
          >
            <Select placeholder="选择分类" allowClear>
              <Option value="chat">对话</Option>
              <Option value="agent">Agent</Option>
              <Option value="rag">RAG</Option>
              <Option value="code">代码生成</Option>
              <Option value="summary">摘要</Option>
              <Option value="translation">翻译</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="模板内容"
            name="content"
            rules={[{ required: true, message: '请输入模板内容' }]}
          >
            <TextArea rows={10} />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 模板详情抽屉 */}
      <Drawer
        title="Prompt 模板详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedTemplate(null);
        }}
        width={700}
      >
        {selectedTemplate && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="名称" span={2}>
                {selectedTemplate.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedTemplate.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="分类">
                {selectedTemplate.category ? <Tag color="purple">{selectedTemplate.category}</Tag> : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建者">
                {selectedTemplate.created_by || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="变量" span={2}>
                {renderVariables(selectedTemplate.variables)}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedTemplate.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedTemplate.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24 }}>
              <Card size="small" title="模板内容" extra={
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => {
                    navigator.clipboard.writeText(selectedTemplate.content);
                    message.success('已复制到剪贴板');
                  }}
                >
                  复制
                </Button>
              }>
              <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                {selectedTemplate.content}
              </pre>
              </Card>
            </div>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<PlayCircleOutlined />}
                  onClick={() => {
                    const initialValues: Record<string, string> = {};
                    selectedTemplate.variables.forEach((v) => {
                      initialValues[v] = '';
                    });
                    testForm.setFieldsValue({
                      variables: initialValues,
                      model: 'gpt-4',
                    });
                    setTestResult(null);
                    setIsTestModalOpen(true);
                  }}
                >
                  测试模板
                </Button>
                <Button
                  icon={<EditOutlined />}
                  onClick={() => {
                    form.setFieldsValue(selectedTemplate);
                    setIsDetailDrawerOpen(false);
                    setIsEditModalOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Popconfirm
                  title="确定要删除这个模板吗？"
                  onConfirm={() => deleteMutation.mutate(selectedTemplate.template_id)}
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

      {/* 测试模板模态框 */}
      <Modal
        title="测试 Prompt 模板"
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
          {renderVariableFields(selectedTemplate?.variables)}
        </Form>
        {testResult && (
          <Alert
            style={{ marginTop: 16 }}
            type="success"
            message="测试结果"
            description={
              <div>
                <div style={{ marginBottom: 8 }}>
                  {testResult.usage && (
                    <Tag>Token: {testResult.usage.prompt_tokens + testResult.usage.completion_tokens}</Tag>
                  )}
                </div>
                <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto' }}>
                  {testResult.result}
                </pre>
              </div>
            }
          />
        )}
      </Modal>
    </div>
  );
}

export default PromptsPage;
