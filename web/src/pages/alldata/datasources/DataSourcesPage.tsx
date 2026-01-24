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
  Drawer,
  Descriptions,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { DataSource, CreateDataSourceRequest, DataSourceType } from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

const dataSourceTypes: Array<{ value: DataSourceType; label: string; defaultPort: number }> = [
  { value: 'mysql', label: 'MySQL', defaultPort: 3306 },
  { value: 'postgresql', label: 'PostgreSQL', defaultPort: 5432 },
  { value: 'oracle', label: 'Oracle', defaultPort: 1521 },
  { value: 'sqlserver', label: 'SQL Server', defaultPort: 1433 },
  { value: 'hive', label: 'Hive', defaultPort: 10000 },
  { value: 'mongodb', label: 'MongoDB', defaultPort: 27017 },
  { value: 'redis', label: 'Redis', defaultPort: 6379 },
  { value: 'elasticsearch', label: 'Elasticsearch', defaultPort: 9200 },
];

function DataSourcesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedDataSource, setSelectedDataSource] = useState<DataSource | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);

  const [form] = Form.useForm();

  // 获取数据源列表
  const { data: sourcesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['datasources', page, pageSize, typeFilter, statusFilter],
    queryFn: () =>
      alldata.getDataSources({
        page,
        page_size: pageSize,
        type: typeFilter as DataSourceType || undefined,
        status: statusFilter || undefined,
      }),
  });

  // 创建数据源
  const createMutation = useMutation({
    mutationFn: alldata.createDataSource,
    onSuccess: () => {
      message.success('数据源创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      setTestResult(null);
      queryClient.invalidateQueries({ queryKey: ['datasources'] });
    },
    onError: () => {
      message.error('数据源创建失败');
    },
  });

  // 更新数据源
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof alldata.updateDataSource>[1] }) =>
      alldata.updateDataSource(id, data),
    onSuccess: () => {
      message.success('数据源更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      setTestResult(null);
      queryClient.invalidateQueries({ queryKey: ['datasources'] });
    },
    onError: () => {
      message.error('数据源更新失败');
    },
  });

  // 删除数据源
  const deleteMutation = useMutation({
    mutationFn: alldata.deleteDataSource,
    onSuccess: () => {
      message.success('数据源删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['datasources'] });
    },
    onError: () => {
      message.error('数据源删除失败');
    },
  });

  // 测试连接
  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields();
      setTestingConnection(true);
      setTestResult(null);

      const result = await alldata.testDataSource({
        type: values.type,
        connection: {
          host: values.host,
          port: values.port,
          username: values.username,
          password: values.password,
          database: values.database,
          schema: values.schema,
        },
      });

      setTestResult({
        success: result.data.success,
        message: result.data.message,
        latency: result.data.latency_ms,
      });

      if (result.data.success) {
        message.success('连接测试成功');
      } else {
        message.error(`连接测试失败: ${result.data.message}`);
      }
    } catch (error) {
      setTestResult({ success: false, message: '连接测试失败，请检查配置' });
    } finally {
      setTestingConnection(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      connected: 'green',
      disconnected: 'default',
      error: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      connected: '已连接',
      disconnected: '未连接',
      error: '错误',
    };
    return texts[status] || status;
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      mysql: 'blue',
      postgresql: 'cyan',
      oracle: 'orange',
      sqlserver: 'purple',
      hive: 'yellow',
      mongodb: 'green',
      redis: 'red',
      elasticsearch: 'geekblue',
    };
    return colors[type] || 'default';
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DataSource) => (
        <a
          onClick={() => {
            setSelectedDataSource(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color={getTypeColor(type)}>{type}</Tag>,
    },
    {
      title: '主机',
      dataIndex: ['connection', 'host'],
      key: 'host',
    },
    {
      title: '端口',
      dataIndex: ['connection', 'port'],
      key: 'port',
    },
    {
      title: '数据库',
      dataIndex: ['connection', 'database'],
      key: 'database',
      render: (db: string) => db || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={status === 'connected' ? <CheckCircleOutlined /> : undefined}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '表数量',
      dataIndex: ['metadata', 'tables_count'],
      key: 'tables_count',
      render: (count?: number) => (count !== undefined ? count.toLocaleString() : '-'),
    },
    {
      title: '最后连接',
      dataIndex: 'last_connected',
      key: 'last_connected',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: DataSource) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedDataSource(record);
              setIsDetailDrawerOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedDataSource(record);
              form.setFieldsValue({
                ...record,
                password: '', // 不显示密码
              });
              setIsEditModalOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个数据源吗？"
            onConfirm={() => deleteMutation.mutate(record.source_id)}
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
      const data: CreateDataSourceRequest = {
        name: values.name,
        description: values.description,
        type: values.type,
        connection: {
          host: values.host,
          port: values.port,
          username: values.username,
          password: values.password,
          database: values.database,
          schema: values.schema,
        },
        tags: values.tags,
      };
      createMutation.mutate(data);
    });
  };

  const handleUpdate = () => {
    form.validateFields().then((values) => {
      updateMutation.mutate({
        id: selectedDataSource!.source_id,
        data: {
          name: values.name,
          description: values.description,
          connection: {
            host: values.host,
            port: values.port,
            username: values.username,
            password: values.password || undefined,
            database: values.database,
            schema: values.schema,
          },
          tags: values.tags,
        },
      });
    });
  };

  const renderConnectionForm = (isEdit = false) => (
    <>
      <Form.Item
        label="数据源名称"
        name="name"
        rules={[{ required: true, message: '请输入数据源名称' }]}
      >
        <Input placeholder="请输入数据源名称" />
      </Form.Item>
      <Form.Item label="描述" name="description">
        <TextArea rows={2} placeholder="请输入描述" />
      </Form.Item>
      <Form.Item
        label="数据库类型"
        name="type"
        rules={[{ required: true, message: '请选择数据库类型' }]}
      >
        <Select
          placeholder="请选择数据库类型"
          disabled={isEdit}
          onChange={(value) => {
            const config = dataSourceTypes.find((t) => t.value === value);
            if (config) {
              form.setFieldsValue({ port: config.defaultPort });
            }
          }}
        >
          {dataSourceTypes.map((type) => (
            <Option key={type.value} value={type.value}>
              {type.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="主机地址" name="host" rules={[{ required: true, message: '请输入主机地址' }]}>
        <Input placeholder="例如: localhost 或 192.168.1.100" />
      </Form.Item>
      <Form.Item label="端口" name="port" rules={[{ required: true, message: '请输入端口' }]}>
        <InputNumber min={1} max={65535} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
        <Input placeholder="请输入用户名" />
      </Form.Item>
      <Form.Item label={isEdit ? '新密码（留空不修改）' : '密码'} name="password" rules={!isEdit ? [{ required: true, message: '请输入密码' }] : []}>
        <Input.Password placeholder={isEdit ? '留空不修改密码' : '请输入密码'} />
      </Form.Item>
      <Form.Item label="数据库" name="database">
        <Input placeholder="请输入数据库名称" />
      </Form.Item>
      <Form.Item label="Schema" name="schema">
        <Input placeholder="请输入 Schema（可选）" />
      </Form.Item>
      <Form.Item label="标签" name="tags">
        <Select mode="tags" placeholder="输入标签后按回车" />
      </Form.Item>
    </>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="数据源管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建数据源
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 150 }}
            onChange={setTypeFilter}
            value={typeFilter || undefined}
          >
            {dataSourceTypes.map((type) => (
              <Option key={type.value} value={type.value}>
                {type.label}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="connected">已连接</Option>
            <Option value="disconnected">未连接</Option>
            <Option value="error">错误</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={sourcesData?.data?.sources || []}
          rowKey="source_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: sourcesData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建数据源模态框 */}
      <Modal
        title="新建数据源"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setTestResult(null);
        }}
        confirmLoading={createMutation.isPending}
        width={600}
        footer={[
          <Button
            key="test"
            icon={<ApiOutlined />}
            loading={testingConnection}
            onClick={handleTestConnection}
          >
            测试连接
          </Button>,
          <Button key="cancel" onClick={() => setIsCreateModalOpen(false)}>
            取消
          </Button>,
          <Button key="submit" type="primary" loading={createMutation.isPending} onClick={handleCreate}>
            创建
          </Button>,
        ]}
      >
        {testResult && (
          <Alert
            style={{ marginBottom: 16 }}
            type={testResult.success ? 'success' : 'error'}
            message={testResult.message}
            description={testResult.latency !== undefined ? `延迟: ${testResult.latency}ms` : undefined}
            showIcon
            closable
            onClose={() => setTestResult(null)}
          />
        )}
        <Form form={form} layout="vertical">
          {renderConnectionForm(false)}
        </Form>
      </Modal>

      {/* 编辑数据源模态框 */}
      <Modal
        title="编辑数据源"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
          setTestResult(null);
        }}
        confirmLoading={updateMutation.isPending}
        width={600}
        footer={[
          <Button
            key="test"
            icon={<ApiOutlined />}
            loading={testingConnection}
            onClick={handleTestConnection}
          >
            测试连接
          </Button>,
          <Button key="cancel" onClick={() => setIsEditModalOpen(false)}>
            取消
          </Button>,
          <Button key="submit" type="primary" loading={updateMutation.isPending} onClick={handleUpdate}>
            保存
          </Button>,
        ]}
      >
        {testResult && (
          <Alert
            style={{ marginBottom: 16 }}
            type={testResult.success ? 'success' : 'error'}
            message={testResult.message}
            showIcon
            closable
            onClose={() => setTestResult(null)}
          />
        )}
        <Form form={form} layout="vertical">
          {renderConnectionForm(true)}
        </Form>
      </Modal>

      {/* 数据源详情抽屉 */}
      <Drawer
        title="数据源详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedDataSource(null);
        }}
        width={600}
      >
        {selectedDataSource && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="名称" span={2}>
                {selectedDataSource.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedDataSource.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag color={getTypeColor(selectedDataSource.type)}>{selectedDataSource.type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedDataSource.status)} icon={selectedDataSource.status === 'connected' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
                  {getStatusText(selectedDataSource.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="主机" span={2}>
                {selectedDataSource.connection.host}:{selectedDataSource.connection.port}
              </Descriptions.Item>
              <Descriptions.Item label="用户名">
                {selectedDataSource.connection.username}
              </Descriptions.Item>
              <Descriptions.Item label="数据库">
                {selectedDataSource.connection.database || '-'}
              </Descriptions.Item>
              {selectedDataSource.connection.schema && (
                <Descriptions.Item label="Schema" span={2}>
                  {selectedDataSource.connection.schema}
                </Descriptions.Item>
              )}
              {selectedDataSource.metadata && (
                <>
                  {selectedDataSource.metadata.version && (
                    <Descriptions.Item label="版本">
                      {selectedDataSource.metadata.version}
                    </Descriptions.Item>
                  )}
                  {selectedDataSource.metadata.tables_count !== undefined && (
                    <Descriptions.Item label="表数量">
                      {selectedDataSource.metadata.tables_count.toLocaleString()}
                    </Descriptions.Item>
                  )}
                </>
              )}
              <Descriptions.Item label="创建者">
                {selectedDataSource.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedDataSource.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
              {selectedDataSource.last_connected && (
                <Descriptions.Item label="最后连接" span={2}>
                  {dayjs(selectedDataSource.last_connected).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="标签" span={2}>
                {selectedDataSource.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {selectedDataSource.last_error && (
              <Alert
                style={{ marginTop: 16 }}
                type="error"
                message="连接错误"
                description={selectedDataSource.last_error}
              />
            )}

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<DatabaseOutlined />}
                  onClick={() => {
                    // 跳转到元数据页面
                    window.location.href = `/metadata?source=${selectedDataSource.source_id}`;
                  }}
                >
                  浏览元数据
                </Button>
                <Popconfirm
                  title="确定要删除这个数据源吗？"
                  onConfirm={() => deleteMutation.mutate(selectedDataSource.source_id)}
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

export default DataSourcesPage;
