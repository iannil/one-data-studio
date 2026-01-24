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
  InputNumber,
  message,
  Popconfirm,
  Card,
  Tabs,
  Drawer,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type {
  StandardLibrary,
  DataElement,
  CreateDataElementRequest,
} from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

const dataTypes = [
  { value: 'string', label: '字符串' },
  { value: 'integer', label: '整数' },
  { value: 'float', label: '浮点数' },
  { value: 'boolean', label: '布尔' },
  { value: 'date', label: '日期' },
  { value: 'datetime', label: '日期时间' },
  { value: 'decimal', label: '小数' },
];

function StandardsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('elements');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Modals
  const [isLibraryModalOpen, setIsLibraryModalOpen] = useState(false);
  const [isElementModalOpen, setIsElementModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);

  // Selected items
  const [selectedElement, setSelectedElement] = useState<DataElement | null>(null);

  const [libraryForm] = Form.useForm();
  const [elementForm] = Form.useForm();

  // Queries
  const { data: elementsData, isLoading: isLoadingElements } = useQuery({
    queryKey: ['data-elements', page, pageSize],
    queryFn: () => alldata.getDataElements({ page, page_size: pageSize }),
  });

  const { data: librariesData } = useQuery({
    queryKey: ['standard-libraries'],
    queryFn: () => alldata.getStandardLibraries(),
  });

  const { data: documentsData } = useQuery({
    queryKey: ['standard-documents'],
    queryFn: () => alldata.getStandardDocuments(),
  });

  const { data: mappingsData } = useQuery({
    queryKey: ['standard-mappings'],
    queryFn: () => alldata.getStandardMappings(),
  });

  // Mutations
  const createElementMutation = useMutation({
    mutationFn: alldata.createDataElement,
    onSuccess: () => {
      message.success('数据元创建成功');
      setIsElementModalOpen(false);
      elementForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['data-elements'] });
    },
    onError: () => {
      message.error('数据元创建失败');
    },
  });

  const updateElementMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateDataElementRequest> }) =>
      alldata.updateDataElement(id, data),
    onSuccess: () => {
      message.success('数据元更新成功');
      setIsElementModalOpen(false);
      elementForm.resetFields();
      setSelectedElement(null);
      queryClient.invalidateQueries({ queryKey: ['data-elements'] });
    },
    onError: () => {
      message.error('数据元更新失败');
    },
  });

  const deleteElementMutation = useMutation({
    mutationFn: alldata.deleteDataElement,
    onSuccess: () => {
      message.success('数据元删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['data-elements'] });
    },
    onError: () => {
      message.error('数据元删除失败');
    },
  });

  const createLibraryMutation = useMutation({
    mutationFn: alldata.createStandardLibrary,
    onSuccess: () => {
      message.success('词根库创建成功');
      setIsLibraryModalOpen(false);
      libraryForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['standard-libraries'] });
    },
    onError: () => {
      message.error('词根库创建失败');
    },
  });

  const deleteLibraryMutation = useMutation({
    mutationFn: alldata.deleteStandardLibrary,
    onSuccess: () => {
      message.success('词根库删除成功');
      queryClient.invalidateQueries({ queryKey: ['standard-libraries'] });
    },
    onError: () => {
      message.error('词根库删除失败');
    },
  });

  const getDataTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      string: 'blue',
      integer: 'green',
      float: 'cyan',
      boolean: 'purple',
      date: 'orange',
      datetime: 'orange',
      decimal: 'geekblue',
    };
    return colors[type] || 'default';
  };

  const elementColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DataElement) => (
        <a onClick={() => { setSelectedElement(record); setIsDetailDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <Tag color="blue">{code}</Tag>,
    },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
      render: (type: string) => <Tag color={getDataTypeColor(type)}>{type}</Tag>,
    },
    {
      title: '长度',
      dataIndex: 'length',
      key: 'length',
      render: (len?: number) => len || '-',
    },
    {
      title: '精度',
      key: 'precision',
      render: (_: unknown, record: DataElement) => record.precision ? `${record.precision},${record.scale}` : '-',
    },
    {
      title: '标准值',
      dataIndex: 'standard_value',
      key: 'standard_value',
      render: (val?: string) => val ? <Tag>{val}</Tag> : '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags?: string[]) => (
        <>
          {tags?.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
          {tags && tags.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
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
      width: 150,
      render: (_: unknown, record: DataElement) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedElement(record);
              elementForm.setFieldsValue(record);
              setIsElementModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个数据元吗？"
            onConfirm={() => deleteElementMutation.mutate(record.element_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const libraryColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (cat?: string) => cat || '-',
    },
    {
      title: '词根数量',
      dataIndex: 'word_count',
      key: 'word_count',
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: StandardLibrary) => (
        <Space>
          <Popconfirm
            title="确定要删除这个词根库吗？"
            onConfirm={() => deleteLibraryMutation.mutate(record.library_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const documentColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (v: string) => <Tag>v{v}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const labels: Record<string, string> = {
          dictionary: '数据字典',
          rule: '规则文档',
          spec: '规范文档',
          manual: '手册文档',
        };
        return labels[type] || type;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          published: 'green',
          draft: 'default',
          deprecated: 'orange',
        };
        const labels: Record<string, string> = {
          published: '已发布',
          draft: '草稿',
          deprecated: '已废弃',
        };
        return <Tag color={colors[status]}>{labels[status]}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
  ];

  const handleCreateElement = () => {
    elementForm.validateFields().then((values) => {
      createElementMutation.mutate(values);
    });
  };

  const handleUpdateElement = () => {
    elementForm.validateFields().then((values) => {
      updateElementMutation.mutate({
        id: selectedElement!.element_id,
        data: values,
      });
    });
  };

  const handleCreateLibrary = () => {
    libraryForm.validateFields().then((values) => {
      createLibraryMutation.mutate(values);
    });
  };

  const tabItems = [
    {
      key: 'elements',
      label: (
        <span>
          <UnorderedListOutlined />
          数据元
        </span>
      ),
      children: (
        <Card
          title="数据元管理"
          extra={
            <Space>
              <Button
                icon={<AppstoreOutlined />}
                onClick={() => setIsLibraryModalOpen(true)}
              >
                词根库
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsElementModalOpen(true)}>
                新建数据元
              </Button>
            </Space>
          }
        >
          <Table
            columns={elementColumns}
            dataSource={elementsData?.data?.elements || []}
            rowKey="element_id"
            loading={isLoadingElements}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: elementsData?.data?.total || 0,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (newPage, newPageSize) => {
                setPage(newPage);
                setPageSize(newPageSize || 10);
              },
            }}
          />
        </Card>
      ),
    },
    {
      key: 'libraries',
      label: (
        <span>
          <AppstoreOutlined />
          词根库
        </span>
      ),
      children: (
        <Card
          title="词根库"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsLibraryModalOpen(true)}>
              新建词根库
            </Button>
          }
        >
          <Table
            columns={libraryColumns}
            dataSource={librariesData?.data?.libraries || []}
            rowKey="library_id"
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'documents',
      label: (
        <span>
          <FileTextOutlined />
          标准文档
        </span>
      ),
      children: (
        <Card
          title="标准文档"
          extra={
            <Button type="primary" icon={<PlusOutlined />} disabled>
              上传文档（即将推出）
            </Button>
          }
        >
          <Table
            columns={documentColumns}
            dataSource={documentsData?.data?.documents || []}
            rowKey="doc_id"
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'mappings',
      label: (
        <span>
          <UnorderedListOutlined />
          标准映射
        </span>
      ),
      children: (
        <Card
          title="字段标准映射"
          extra={
            <Button type="primary" icon={<PlusOutlined />} disabled>
              新建映射（即将推出）
            </Button>
          }
        >
          <Table
            columns={[
              { title: '名称', dataIndex: 'name', key: 'name' },
              { title: '源表', dataIndex: 'source_table', key: 'source_table' },
              { title: '源字段', dataIndex: 'source_column', key: 'source_column' },
              { title: '目标数据元', dataIndex: 'target_element_name', key: 'target_element_name' },
              {
                title: '状态',
                dataIndex: 'status',
                key: 'status',
                render: (status: string) => (
                  <Tag color={status === 'active' ? 'green' : 'default'}>
                    {status === 'active' ? '启用' : '禁用'}
                  </Tag>
                ),
              },
            ]}
            dataSource={mappingsData?.data?.mappings || []}
            rowKey="mapping_id"
            pagination={false}
          />
        </Card>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      {/* 词根库模态框 */}
      <Modal
        title="新建词根库"
        open={isLibraryModalOpen}
        onOk={handleCreateLibrary}
        onCancel={() => {
          setIsLibraryModalOpen(false);
          libraryForm.resetFields();
        }}
        confirmLoading={createLibraryMutation.isPending}
      >
        <Form form={libraryForm} layout="vertical">
          <Form.Item
            label="词根库名称"
            name="name"
            rules={[{ required: true, message: '请输入词根库名称' }]}
          >
            <Input placeholder="请输入词根库名称" />
          </Form.Item>
          <Form.Item label="分类" name="category">
            <Input placeholder="请输入分类" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据元模态框 */}
      <Modal
        title={selectedElement ? '编辑数据元' : '新建数据元'}
        open={isElementModalOpen}
        onOk={selectedElement ? handleUpdateElement : handleCreateElement}
        onCancel={() => {
          setIsElementModalOpen(false);
          elementForm.resetFields();
          setSelectedElement(null);
        }}
        confirmLoading={createElementMutation.isPending || updateElementMutation.isPending}
        width={600}
      >
        <Form form={elementForm} layout="vertical">
          <Form.Item
            label="数据元名称"
            name="name"
            rules={[{ required: true, message: '请输入数据元名称' }]}
          >
            <Input placeholder="请输入数据元名称" />
          </Form.Item>
          <Form.Item
            label="数据元代码"
            name="code"
            rules={[{ required: true, message: '请输入数据元代码' }]}
          >
            <Input placeholder="请输入数据元代码" />
          </Form.Item>
          <Form.Item
            label="数据类型"
            name="data_type"
            rules={[{ required: true, message: '请选择数据类型' }]}
          >
            <Select placeholder="请选择数据类型">
              {dataTypes.map((type) => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="长度" name="length">
            <InputNumber min={1} style={{ width: '100%' }} placeholder="最大长度" />
          </Form.Item>
          <Form.Item label="精度" name="precision">
            <InputNumber min={1} style={{ width: '100%' }} placeholder="精度" />
          </Form.Item>
          <Form.Item label="小数位数" name="scale">
            <InputNumber min={0} style={{ width: '100%' }} placeholder="小数位数" />
          </Form.Item>
          <Form.Item label="标准值" name="standard_value">
            <Input placeholder="请输入标准值" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="词根库" name="library_id">
            <Select placeholder="请选择词根库" allowClear>
              {librariesData?.data?.libraries.map((lib) => (
                <Option key={lib.library_id} value={lib.library_id}>
                  {lib.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据元详情抽屉 */}
      <Drawer
        title="数据元详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedElement(null);
        }}
        width={600}
      >
        {selectedElement && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="名称" span={2}>
              {selectedElement.name}
            </Descriptions.Item>
            <Descriptions.Item label="代码">
              <Tag color="blue">{selectedElement.code}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="数据类型">
              <Tag color={getDataTypeColor(selectedElement.data_type)}>
                {selectedElement.data_type}
              </Tag>
            </Descriptions.Item>
            {selectedElement.length && (
              <Descriptions.Item label="长度">{selectedElement.length}</Descriptions.Item>
            )}
            {selectedElement.precision && (
              <Descriptions.Item label="精度">
                {selectedElement.precision},{selectedElement.scale}
              </Descriptions.Item>
            )}
            {selectedElement.standard_value && (
              <Descriptions.Item label="标准值" span={2}>
                <Tag>{selectedElement.standard_value}</Tag>
              </Descriptions.Item>
            )}
            {selectedElement.description && (
              <Descriptions.Item label="描述" span={2}>
                {selectedElement.description}
              </Descriptions.Item>
            )}
            {selectedElement.tags && selectedElement.tags.length > 0 && (
              <Descriptions.Item label="标签" span={2}>
                {selectedElement.tags.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="创建者">
              {selectedElement.created_by}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(selectedElement.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}

export default StandardsPage;
