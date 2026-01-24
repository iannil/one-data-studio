import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Input,
  Tag,
  Space,
  Modal,
  Form,
  Select,
  message,
  Popconfirm,
  Card,
  Descriptions,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { Dataset, ColumnSchema } from '@/services/alldata';

const { Search } = Input;
const { Option } = Select;

function DatasetsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const [form] = Form.useForm();

  // 获取数据集列表
  const { data: datasetsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['datasets', page, pageSize, statusFilter],
    queryFn: () =>
      alldata.getDatasets({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      }),
    enabled: !id,
  });

  // 获取数据集详情
  const { data: datasetDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => alldata.getDataset(id!),
    enabled: !!id,
  });

  // 如果 URL 中有 id，自动打开详情抽屉
  useEffect(() => {
    if (id && datasetDetail?.data) {
      setSelectedDataset(datasetDetail.data);
      setIsDetailDrawerOpen(true);
    }
  }, [id, datasetDetail]);

  // 创建数据集
  const createMutation = useMutation({
    mutationFn: alldata.createDataset,
    onSuccess: () => {
      message.success('数据集创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: () => {
      message.error('数据集创建失败');
    },
  });

  // 更新数据集
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Dataset> }) =>
      alldata.updateDataset(id, data),
    onSuccess: () => {
      message.success('数据集更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['dataset', selectedDataset?.dataset_id] });
    },
  });

  // 删除数据集
  const deleteMutation = useMutation({
    mutationFn: alldata.deleteDataset,
    onSuccess: () => {
      message.success('数据集删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Dataset) => (
        <a
          onClick={() => {
            setSelectedDataset(record);
            setIsDetailDrawerOpen(true);
            navigate(`/datasets/${record.dataset_id}`, { replace: true });
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
      title: '格式',
      dataIndex: 'format',
      key: 'format',
      width: 100,
      render: (format: string) => <Tag>{format.toUpperCase()}</Tag>,
    },
    {
      title: '存储路径',
      dataIndex: 'storage_path',
      key: 'storage_path',
      ellipsis: true,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <>
          {tags?.map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
        </>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const color = status === 'active' ? 'green' : 'default';
        return <Tag color={color}>{status}</Tag>;
      },
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
      render: (_: unknown, record: Dataset) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedDataset(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedDataset(record);
              form.setFieldsValue(record);
              setIsEditModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个数据集吗？"
            onConfirm={() => deleteMutation.mutate(record.dataset_id)}
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
      createMutation.mutate({
        ...values,
        storage_type: 's3',
        schema: {
          columns: [],
        },
      });
    });
  };

  const handleUpdate = () => {
    form.validateFields().then((values) => {
      updateMutation.mutate({
        id: selectedDataset?.dataset_id!,
        data: values,
      });
    });
  };

  const renderSchemaTable = (columns?: ColumnSchema[]) => {
    if (!columns || columns.length === 0) return <div style={{ textAlign: 'center', padding: '20px' }}>暂无 Schema</div>;

    return (
      <Table
        size="small"
        dataSource={columns}
        rowKey="name"
        pagination={false}
        columns={[
          { title: '列名', dataIndex: 'name', key: 'name' },
          { title: '类型', dataIndex: 'type', key: 'type' },
          { title: '描述', dataIndex: 'description', key: 'description', render: (desc) => desc || '-' },
          {
            title: '可空',
            dataIndex: 'nullable',
            key: 'nullable',
            width: 80,
            render: (val) => (val ? '是' : '否'),
          },
        ]}
      />
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="数据集管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建数据集
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Search
            placeholder="搜索数据集名称"
            allowClear
            style={{ width: 300 }}
            onSearch={setSearchText}
          />
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 150 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="active">活跃</Option>
            <Option value="archived">已归档</Option>
            <Option value="processing">处理中</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={datasetsData?.data?.datasets || []}
          rowKey="dataset_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: datasetsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建数据集模态框 */}
      <Modal
        title="新建数据集"
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
            label="数据集名称"
            name="name"
            rules={[{ required: true, message: '请输入数据集名称' }]}
          >
            <Input placeholder="请输入数据集名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="存储路径"
            name="storage_path"
            rules={[{ required: true, message: '请输入存储路径' }]}
          >
            <Input placeholder="s3://bucket/path/" />
          </Form.Item>
          <Form.Item
            label="格式"
            name="format"
            rules={[{ required: true, message: '请选择格式' }]}
          >
            <Select placeholder="请选择格式">
              <Option value="csv">CSV</Option>
              <Option value="json">JSON</Option>
              <Option value="parquet">Parquet</Option>
              <Option value="excel">Excel</Option>
            </Select>
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑数据集模态框 */}
      <Modal
        title="编辑数据集"
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
            label="数据集名称"
            name="name"
            rules={[{ required: true, message: '请输入数据集名称' }]}
          >
            <Input placeholder="请输入数据集名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据集详情抽屉 */}
      <Drawer
        title="数据集详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedDataset(null);
          navigate('/datasets', { replace: true });
        }}
        width={700}
      >
        {selectedDataset && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="名称" span={2}>
                {selectedDataset.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedDataset.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="格式">
                <Tag>{selectedDataset.format.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={selectedDataset.status === 'active' ? 'green' : 'default'}>
                  {selectedDataset.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="存储类型" span={2}>
                {selectedDataset.storage_type}
              </Descriptions.Item>
              <Descriptions.Item label="存储路径" span={2}>
                {selectedDataset.storage_path}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedDataset.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {selectedDataset.updated_at
                  ? dayjs(selectedDataset.updated_at).format('YYYY-MM-DD HH:mm')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedDataset.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {selectedDataset.statistics && (
              <div style={{ marginTop: 24 }}>
                <h3>统计信息</h3>
                <Descriptions column={2} bordered>
                  <Descriptions.Item label="行数">
                    {selectedDataset.statistics.row_count.toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="大小">
                    {(selectedDataset.statistics.size_bytes / 1024 / 1024).toFixed(2)} MB
                  </Descriptions.Item>
                </Descriptions>
              </div>
            )}

            {selectedDataset.schema && (
              <div style={{ marginTop: 24 }}>
                <h3>Schema</h3>
                {renderSchemaTable(selectedDataset.schema.columns)}
              </div>
            )}

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button icon={<UploadOutlined />} onClick={() => setUploadModalOpen(true)}>
                  上传文件
                </Button>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => {
                    form.setFieldsValue(selectedDataset);
                    setIsEditModalOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Popconfirm
                  title="确定要删除这个数据集吗？"
                  onConfirm={() => deleteMutation.mutate(selectedDataset.dataset_id)}
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
    </div>
  );
}

export default DatasetsPage;
