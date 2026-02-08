import { useState, useEffect, useRef } from 'react';
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
import dataService from '@/services/data';
import type { DataSource, CreateDataSourceRequest, DataSourceType } from '@/services/data';

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
  const [isTestPasswordModalOpen, setIsTestPasswordModalOpen] = useState(false);
  const [selectedDataSource, setSelectedDataSource] = useState<DataSource | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);
  const [loadingEditSource, setLoadingEditSource] = useState<string | null>(null);
  const [testPasswordForm] = Form.useForm();

  // 创建表单和编辑表单使用不同的实例
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  // 用于存储编辑数据
  const [editFormData, setEditFormData] = useState<DataSource | null>(null);

  // 当 editFormData 更新时，设置表单值
  useEffect(() => {
    if (editFormData) {
      const formValues = {
        name: editFormData.name,
        description: editFormData.description,
        type: editFormData.type,
        host: editFormData.connection?.host || '',
        port: editFormData.connection?.port || 3306,
        username: editFormData.connection?.username || '',
        password: '',
        database: editFormData.connection?.database || '',
        schema: editFormData.connection?.schema || '',
        tags: editFormData.tags || [],
      };
      console.log('=== useEffect: editFormData updated, setting form values ===');
      console.log('formValues:', formValues);
      // 使用 setTimeout 确保在 Modal 完全打开后再设置值
      setTimeout(() => {
        console.log('=== Calling setFieldsValue ===');
        editForm.setFieldsValue(formValues);
        // 验证设置是否成功
        setTimeout(() => {
          const currentValues = editForm.getFieldsValue();
          console.log('=== Current form values ===', currentValues);
        }, 50);
      }, 100);
    }
  }, [editFormData, isEditModalOpen, editForm]);

  // 模态框关闭时清空编辑数据
  const handleEditModalClose = () => {
    setIsEditModalOpen(false);
    setEditFormData(null);
    editForm.resetFields();
    setTestResult(null);
  };

  // 获取数据源列表
  const { data: sourcesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['datasources', page, pageSize, typeFilter, statusFilter],
    queryFn: () =>
      dataService.getDataSources({
        page,
        page_size: pageSize,
        type: typeFilter as DataSourceType || undefined,
        status: statusFilter || undefined,
      }),
  });

  // 创建数据源
  const createMutation = useMutation({
    mutationFn: dataService.createDataSource,
    onSuccess: async (response, variables) => {
      message.success('数据源创建成功');
      setIsCreateModalOpen(false);

      // 创建后自动测试连接以更新状态
      const sourceId = response.data?.source_id || response.data?.source_id;
      if (sourceId && variables.connection.password) {
        try {
          // 使用新的 testSavedDataSource 方法，后端会自动更新状态
          const testResult = await dataService.testSavedDataSource(sourceId, variables.connection.password);

          if (testResult.data.success) {
            message.success('连接测试成功，数据源状态已更新');
          } else {
            message.warning(`数据源已创建，但连接测试失败: ${testResult.data.message}`);
          }
        } catch (error) {
          console.warn('自动连接测试失败:', error);
        }
      }

      createForm.resetFields();
      setTestResult(null);
      await queryClient.invalidateQueries({ queryKey: ['datasources'] });
    },
    onError: () => {
      message.error('数据源创建失败');
    },
  });

  // 更新数据源
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof dataService.updateDataSource>[1] }) =>
      dataService.updateDataSource(id, data),
    onSuccess: async (_, variables) => {
      message.success('数据源更新成功');
      setIsEditModalOpen(false);
      setEditFormData(null);

      // 如果提供了密码，更新后自动测试连接
      if (variables.data.connection?.password && selectedDataSource) {
        try {
          // 使用新的 testSavedDataSource 方法，后端会自动更新状态
          const testResult = await dataService.testSavedDataSource(
            variables.id,
            variables.data.connection.password
          );

          if (testResult.data.success) {
            message.success('连接测试成功，数据源状态已更新');
          } else {
            message.warning(`数据源已更新，但连接测试失败: ${testResult.data.message}`);
          }
        } catch (error) {
          console.warn('自动连接测试失败:', error);
        }
      }

      setTestResult(null);
      await queryClient.invalidateQueries({ queryKey: ['datasources'] });
    },
    onError: () => {
      message.error('数据源更新失败');
    },
  });

  // 删除数据源
  const deleteMutation = useMutation({
    mutationFn: dataService.deleteDataSource,
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
      // 根据哪个模态框打开来选择表单
      const activeForm = isEditModalOpen ? editForm : createForm;
      const values = await activeForm.validateFields();
      setTestingConnection(true);
      setTestResult(null);

      const result = await dataService.testDataSource({
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

  // 测试已保存数据源的连接 - 打开密码输入模态框
  const handleTestSavedConnection = (record: DataSource) => {
    setSelectedDataSource(record);
    testPasswordForm.setFieldsValue({ password: '' });
    setIsTestPasswordModalOpen(true);
  };

  // 执行已保存数据源的连接测试
  const handleExecuteTestConnection = async () => {
    if (!selectedDataSource) return;

    try {
      const password = testPasswordForm.getFieldValue('password');
      if (!password) {
        message.warning('请输入密码');
        return;
      }

      setTestingConnection(true);

      // 使用新的 testSavedDataSource 方法，后端会自动更新状态
      const result = await dataService.testSavedDataSource(selectedDataSource.source_id, password);

      if (result.data.success) {
        message.success('连接测试成功，状态已更新');
      } else {
        message.error(`连接测试失败: ${result.data.message}`);
      }

      // 刷新列表以获取最新状态
      await queryClient.invalidateQueries({ queryKey: ['datasources'] });
      setIsTestPasswordModalOpen(false);
      testPasswordForm.resetFields();
    } catch (error) {
      message.error('连接测试失败，请检查配置');
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
      width: 200,
      render: (_: unknown, record: DataSource) => (
        <Space size="small">
          <Button
            type="text"
            icon={<ApiOutlined />}
            size="small"
            onClick={() => handleTestSavedConnection(record)}
          >
            测试
          </Button>
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
            loading={loadingEditSource === record.source_id}
            onClick={async () => {
              try {
                setLoadingEditSource(record.source_id);
                // 获取完整的数据源详情（包含连接信息）
                const detail = await dataService.getDataSource(record.source_id);
                const fullData = detail.data;
                setSelectedDataSource(fullData);

                // 先设置编辑数据，然后在下一个事件循环中打开模态框
                setEditFormData(fullData);
                // 使用 requestAnimationFrame 确保在下一个事件循环中打开模态框
                requestAnimationFrame(() => {
                  setIsEditModalOpen(true);
                });
              } catch (error) {
                console.error('获取数据源详情失败:', error);
                message.error('获取数据源详情失败');
              } finally {
                setLoadingEditSource(null);
              }
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
    createForm.validateFields().then((values) => {
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
    editForm.validateFields().then((values) => {
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

  const renderConnectionForm = (isEdit = false, formInstance: any = createForm) => (
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
              formInstance.setFieldsValue({ port: config.defaultPort });
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
      <Form.Item label="主机地址" name="host">
        <Input placeholder="请输入主机地址" />
      </Form.Item>
      <Form.Item label="端口" name="port">
        <Input placeholder="请输入端口" />
      </Form.Item>
      <Form.Item label="用户名" name="username">
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
          createForm.resetFields();
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
        <Form form={createForm} layout="vertical">
          {renderConnectionForm(false)}
        </Form>
      </Modal>

      {/* 编辑数据源模态框 */}
      <Modal
        title="编辑数据源"
        open={isEditModalOpen}
        onOk={handleUpdate}
        onCancel={handleEditModalClose}
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
          <Button key="cancel" onClick={handleEditModalClose}>
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
        <Form
          form={editForm}
          layout="vertical"
          name="editForm"
          initialValues={editFormData ? {
            name: editFormData.name,
            description: editFormData.description,
            type: editFormData.type,
            host: editFormData.connection?.host || '',
            port: editFormData.connection?.port || 3306,
            username: editFormData.connection?.username || '',
            password: '',
            database: editFormData.connection?.database || '',
            schema: editFormData.connection?.schema || '',
            tags: editFormData.tags || [],
          } : {}}
        >
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
              disabled
            >
              {dataSourceTypes.map((type) => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="主机地址"
            name="host"
            rules={[{ required: true, message: '请输入主机地址' }]}
          >
            <Input placeholder="请输入主机地址" />
          </Form.Item>
          <Form.Item label="端口" name="port" rules={[{ required: true, message: '请输入端口' }]}>
            <Input placeholder="请输入端口" />
          </Form.Item>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item label="新密码（留空不修改）" name="password">
            <Input.Password placeholder="留空不修改密码" />
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

      {/* 测试连接密码输入模态框 */}
      <Modal
        title="测试连接"
        open={isTestPasswordModalOpen}
        onOk={handleExecuteTestConnection}
        onCancel={() => {
          setIsTestPasswordModalOpen(false);
          testPasswordForm.resetFields();
        }}
        confirmLoading={testingConnection}
        okText="测试连接"
        cancelText="取消"
      >
        <p style={{ marginBottom: 16 }}>
          测试连接到 <strong>{selectedDataSource?.name}</strong> ({selectedDataSource?.connection.host}:{selectedDataSource?.connection.port})
        </p>
        <Form form={testPasswordForm} layout="vertical">
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码以测试连接" onPressEnter={handleExecuteTestConnection} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default DataSourcesPage;
