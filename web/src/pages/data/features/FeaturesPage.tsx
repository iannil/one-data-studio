import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tabs,
  Popconfirm,
  Row,
  Col,
  Descriptions,
  Badge,
  Drawer,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  FolderOutlined,
  ApiOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import data from '@/services/data';
import type {
  Feature,
  FeatureGroup,
  FeatureSet,
  FeatureService,
} from '@/services/data';

const { Option } = Select;
const { TextArea } = Input;

const dataTypeOptions = [
  { value: 'boolean', label: '布尔值', color: 'blue' },
  { value: 'integer', label: '整数', color: 'green' },
  { value: 'float', label: '浮点数', color: 'cyan' },
  { value: 'string', label: '字符串', color: 'orange' },
  { value: 'array', label: '数组', color: 'purple' },
  { value: 'map', label: '映射', color: 'magenta' },
];

const valueTypeOptions = [
  { value: 'continuous', label: '连续型' },
  { value: 'categorical', label: '分类型' },
  { value: 'ordinal', label: '有序型' },
];

function FeaturesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [activeTab, setActiveTab] = useState('features');

  // Modal states
  const [isFeatureModalOpen, setIsFeatureModalOpen] = useState(false);
  const [isGroupModalOpen, setIsGroupModalOpen] = useState(false);
  const [isSetModalOpen, setIsSetModalOpen] = useState(false);
  const [isServiceModalOpen, setIsServiceModalOpen] = useState(false);
  const [isFeatureDetailOpen, setIsFeatureDetailOpen] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);

  const [featureForm] = Form.useForm();
  const [groupForm] = Form.useForm();
  const [setForm] = Form.useForm();
  const [serviceForm] = Form.useForm();

  // 获取特征列表
  const { data: featuresData, isLoading: isLoadingFeatures } = useQuery({
    queryKey: ['features', page, pageSize],
    queryFn: () => data.getFeatures({ page, page_size: pageSize }),
    enabled: activeTab === 'features',
  });

  // 获取特征组列表
  const { data: groupsData, isLoading: isLoadingGroups } = useQuery({
    queryKey: ['featureGroups'],
    queryFn: () => data.getFeatureGroups(),
    enabled: activeTab === 'features' || activeTab === 'groups',
  });

  // 获取特征集列表
  const { data: setsData, isLoading: isLoadingSets } = useQuery({
    queryKey: ['featureSets'],
    queryFn: () => data.getFeatureSets(),
    enabled: activeTab === 'sets',
  });

  // 获取特征服务列表
  const { data: servicesData, isLoading: isLoadingServices } = useQuery({
    queryKey: ['featureServices'],
    queryFn: () => data.getFeatureServices(),
    enabled: activeTab === 'services',
  });

  // 获取特征版本
  const { data: versionsData } = useQuery({
    queryKey: ['featureVersions', selectedFeature?.feature_id],
    queryFn: () => data.getFeatureVersions(selectedFeature!.feature_id),
    enabled: !!selectedFeature && isFeatureDetailOpen,
  });

  // Mutations
  const createFeatureMutation = useMutation({
    mutationFn: data.createFeature,
    onSuccess: () => {
      message.success('特征创建成功');
      setIsFeatureModalOpen(false);
      featureForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['features'] });
    },
  });

  const deleteFeatureMutation = useMutation({
    mutationFn: data.deleteFeature,
    onSuccess: () => {
      message.success('特征删除成功');
      queryClient.invalidateQueries({ queryKey: ['features'] });
    },
  });

  const createGroupMutation = useMutation({
    mutationFn: data.createFeatureGroup,
    onSuccess: () => {
      message.success('特征组创建成功');
      setIsGroupModalOpen(false);
      groupForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['featureGroups'] });
    },
  });

  const deleteGroupMutation = useMutation({
    mutationFn: data.deleteFeatureGroup,
    onSuccess: () => {
      message.success('特征组删除成功');
      queryClient.invalidateQueries({ queryKey: ['featureGroups'] });
    },
  });

  const createSetMutation = useMutation({
    mutationFn: data.createFeatureSet,
    onSuccess: () => {
      message.success('特征集创建成功');
      setIsSetModalOpen(false);
      setForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['featureSets'] });
    },
  });

  const deleteSetMutation = useMutation({
    mutationFn: (id: string) => data.deleteFeature(id),
    onSuccess: () => {
      message.success('特征集删除成功');
      queryClient.invalidateQueries({ queryKey: ['featureSets'] });
    },
  });

  const createServiceMutation = useMutation({
    mutationFn: data.createFeatureService,
    onSuccess: () => {
      message.success('特征服务创建成功');
      setIsServiceModalOpen(false);
      serviceForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['featureServices'] });
    },
  });

  const deleteServiceMutation = useMutation({
    mutationFn: data.deleteFeatureService,
    onSuccess: () => {
      message.success('特征服务删除成功');
      queryClient.invalidateQueries({ queryKey: ['featureServices'] });
    },
  });

  // 特征表格列
  const featureColumns = [
    {
      title: '特征名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Feature) => (
        <a onClick={() => { setSelectedFeature(record); setIsFeatureDetailOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '特征组',
      dataIndex: 'feature_group',
      key: 'feature_group',
      width: 120,
      render: (group: string) => <Tag>{group}</Tag>,
    },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 100,
      render: (type: string) => {
        const option = dataTypeOptions.find((t) => t.value === type);
        return <Tag color={option?.color}>{option?.label}</Tag>;
      },
    },
    {
      title: '值类型',
      dataIndex: 'value_type',
      key: 'value_type',
      width: 100,
      render: (type: string) => {
        const option = valueTypeOptions.find((t) => t.value === type);
        return <Tag>{option?.label}</Tag>;
      },
    },
    {
      title: '来源',
      key: 'source',
      width: 200,
      render: (_: unknown, record: Feature) => (
        <span style={{ fontSize: 12 }}>
          {record.source_table}.{record.source_column}
        </span>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags: string[]) => (
        <>
          {tags?.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue" style={{ marginBottom: 4 }}>
              {tag}
            </Tag>
          ))}
          {tags?.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (v: number) => <Badge count={`v${v}`} style={{ backgroundColor: '#52c41a' }} />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          active: { text: '活跃', color: 'success' },
          deprecated: { text: '已弃用', color: 'default' },
          draft: { text: '草稿', color: 'warning' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Feature) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedFeature(record);
              setIsFeatureDetailOpen(true);
            }}
          />
          <Popconfirm
            title="确定要删除这个特征吗？"
            onConfirm={() => deleteFeatureMutation.mutate(record.feature_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 特征组表格列
  const groupColumns = [
    {
      title: '组名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span>{name}</span>
      ),
    },
    {
      title: '来源表',
      dataIndex: 'source_table',
      key: 'source_table',
      width: 150,
    },
    {
      title: '关联键',
      dataIndex: 'join_keys',
      key: 'join_keys',
      width: 150,
      render: (keys: string[]) => keys?.map((k) => <Tag key={k}>{k}</Tag>) || '-',
    },
    {
      title: '实体列',
      dataIndex: 'entity_columns',
      key: 'entity_columns',
      width: 150,
      render: (cols: string[]) => cols?.map((c) => <Tag key={c}>{c}</Tag>) || '-',
    },
    {
      title: '特征数量',
      key: 'feature_count',
      width: 100,
      render: (_: unknown, record: FeatureGroup) => record.features?.length || 0,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          active: { text: '活跃', color: 'success' },
          deprecated: { text: '已弃用', color: 'default' },
          draft: { text: '草稿', color: 'warning' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: FeatureGroup) => (
        <Popconfirm
          title="确定要删除这个特征组吗？"
          onConfirm={() => deleteGroupMutation.mutate(record.group_id)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // 特征集表格列
  const setColumns = [
    {
      title: '集合名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '特征组数量',
      key: 'group_count',
      width: 120,
      render: (_: unknown, record: FeatureSet) => record.feature_groups?.length || 0,
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      width: 200,
      render: (labels: string[]) => (
        <>
          {labels?.map((label) => (
            <Tag key={label} color="geekblue">
              {label}
            </Tag>
          ))}
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
      width: 100,
      render: (_: unknown, record: FeatureSet) => (
        <Popconfirm
          title="确定要删除这个特征集吗？"
          onConfirm={() => deleteSetMutation.mutate(record.set_id)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // 特征服务表格列
  const serviceColumns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      width: 300,
      render: (endpoint: string) => (
        <Space>
          <code style={{ fontSize: 12 }}>{endpoint}</code>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => {
              navigator.clipboard.writeText(endpoint);
              message.success('已复制到剪贴板');
            }}
          />
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          running: { text: '运行中', color: 'success' },
          stopped: { text: '已停止', color: 'default' },
          error: { text: '错误', color: 'error' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: 'QPS',
      dataIndex: 'qps',
      key: 'qps',
      width: 100,
      render: (qps: number) => qps.toFixed(1),
    },
    {
      title: '平均延迟',
      dataIndex: 'avg_latency_ms',
      key: 'avg_latency_ms',
      width: 100,
      render: (latency: number) => `${latency.toFixed(1)} ms`,
    },
    {
      title: '特征数量',
      key: 'feature_count',
      width: 100,
      render: (_: unknown, record: FeatureService) => record.features?.length || 0,
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: FeatureService) => (
        <Popconfirm
          title="确定要删除这个服务吗？"
          onConfirm={() => deleteServiceMutation.mutate(record.service_id)}
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
      <Card title="特征存储管理">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'features',
              label: (
                <span>
                  <AppstoreOutlined />
                  特征列表
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsFeatureModalOpen(true)}>
                      注册特征
                    </Button>
                  </div>
                  <Table
                    columns={featureColumns}
                    dataSource={featuresData?.data?.features || []}
                    rowKey="feature_id"
                    loading={isLoadingFeatures}
                    pagination={{
                      current: page,
                      pageSize,
                      total: featuresData?.data?.total || 0,
                      showSizeChanger: true,
                      showTotal: (total) => `共 ${total} 条`,
                      onChange: (newPage, newPageSize) => {
                        setPage(newPage);
                        setPageSize(newPageSize || 10);
                      },
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'groups',
              label: (
                <span>
                  <FolderOutlined />
                  特征组
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsGroupModalOpen(true)}>
                      创建特征组
                    </Button>
                  </div>
                  <Table
                    columns={groupColumns}
                    dataSource={groupsData?.data?.groups || []}
                    rowKey="group_id"
                    loading={isLoadingGroups}
                    pagination={false}
                    expandable={{
                      expandedRowRender: (record) => (
                        <Table
                          size="small"
                          columns={featureColumns.filter((col) => col.key !== 'actions')}
                          dataSource={record.features || []}
                          rowKey="feature_id"
                          pagination={false}
                        />
                      ),
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'sets',
              label: '特征集',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsSetModalOpen(true)}>
                      创建特征集
                    </Button>
                  </div>
                  <Table
                    columns={setColumns}
                    dataSource={setsData?.data?.sets || []}
                    rowKey="set_id"
                    loading={isLoadingSets}
                    pagination={false}
                  />
                </div>
              ),
            },
            {
              key: 'services',
              label: (
                <span>
                  <ApiOutlined />
                  特征服务
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsServiceModalOpen(true)}>
                      发布服务
                    </Button>
                  </div>
                  <Table
                    columns={serviceColumns}
                    dataSource={servicesData?.data?.services || []}
                    rowKey="service_id"
                    loading={isLoadingServices}
                    pagination={false}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 创建特征模态框 */}
      <Modal
        title="注册特征"
        open={isFeatureModalOpen}
        onCancel={() => {
          setIsFeatureModalOpen(false);
          featureForm.resetFields();
        }}
        onOk={() => featureForm.validateFields().then((values) => createFeatureMutation.mutate(values))}
        confirmLoading={createFeatureMutation.isPending}
        width={600}
      >
        <Form form={featureForm} layout="vertical">
          <Form.Item label="特征名称" name="name" rules={[{ required: true, message: '请输入特征名称' }]}>
            <Input placeholder="例如: user_avg_order_amount" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入特征描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="特征组" name="feature_group" rules={[{ required: true, message: '请选择或输入特征组' }]}>
                <Select
                  mode="tags"
                  placeholder="选择或创建特征组"
                  options={groupsData?.data?.groups.map((g) => ({ label: g.name, value: g.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="数据类型" name="data_type" rules={[{ required: true }]}>
                <Select placeholder="选择数据类型">
                  {dataTypeOptions.map((t) => (
                    <Option key={t.value} value={t.value}>
                      {t.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="值类型" name="value_type" rules={[{ required: true }]}>
                <Select placeholder="选择值类型">
                  {valueTypeOptions.map((t) => (
                    <Option key={t.value} value={t.value}>
                      {t.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="标签" name="tags">
                <Select mode="tags" placeholder="输入标签" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="来源表" name="source_table" rules={[{ required: true }]}>
            <Input placeholder="例如: user_features" />
          </Form.Item>
          <Form.Item label="来源列" name="source_column" rules={[{ required: true }]}>
            <Input placeholder="例如: avg_order_amount" />
          </Form.Item>
          <Form.Item label="转换 SQL" name="transform_sql">
            <TextArea rows={3} placeholder="可选的 SQL 转换表达式" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建特征组模态框 */}
      <Modal
        title="创建特征组"
        open={isGroupModalOpen}
        onCancel={() => {
          setIsGroupModalOpen(false);
          groupForm.resetFields();
        }}
        onOk={() => groupForm.validateFields().then((values) => createGroupMutation.mutate(values))}
        confirmLoading={createGroupMutation.isPending}
        width={500}
      >
        <Form form={groupForm} layout="vertical">
          <Form.Item label="组名称" name="name" rules={[{ required: true, message: '请输入组名称' }]}>
            <Input placeholder="例如: user_features" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="来源表" name="source_table" rules={[{ required: true }]}>
            <Input placeholder="例如: user_profile" />
          </Form.Item>
          <Form.Item label="关联键" name="join_keys">
            <Select mode="tags" placeholder="输入关联键，如 user_id" />
          </Form.Item>
          <Form.Item label="实体列" name="entity_columns">
            <Select mode="tags" placeholder="输入实体列，如 user_id" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建特征集模态框 */}
      <Modal
        title="创建特征集"
        open={isSetModalOpen}
        onCancel={() => {
          setIsSetModalOpen(false);
          setForm.resetFields();
        }}
        onOk={() => setForm.validateFields().then((values) => createSetMutation.mutate(values))}
        confirmLoading={createSetMutation.isPending}
        width={500}
      >
        <Form form={setForm} layout="vertical">
          <Form.Item label="集合名称" name="name" rules={[{ required: true, message: '请输入集合名称' }]}>
            <Input placeholder="例如: training_features_v1" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="特征组"
            name="feature_groups"
            rules={[{ required: true, message: '请选择特征组' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要包含的特征组"
              options={groupsData?.data?.groups.map((g) => ({ label: g.name, value: g.group_id }))}
            />
          </Form.Item>
          <Form.Item label="标签" name="labels">
            <Select mode="tags" placeholder="输入标签" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 创建特征服务模态框 */}
      <Modal
        title="发布特征服务"
        open={isServiceModalOpen}
        onCancel={() => {
          setIsServiceModalOpen(false);
          serviceForm.resetFields();
        }}
        onOk={() => serviceForm.validateFields().then((values) => createServiceMutation.mutate(values))}
        confirmLoading={createServiceMutation.isPending}
        width={500}
      >
        <Form form={serviceForm} layout="vertical">
          <Form.Item label="服务名称" name="name" rules={[{ required: true, message: '请输入服务名称' }]}>
            <Input placeholder="例如: user_feature_service" />
          </Form.Item>
          <Form.Item
            label="特征集"
            name="feature_set_id"
            rules={[{ required: true, message: '请选择特征集' }]}
          >
            <Select
              placeholder="选择要发布的特征集"
              options={setsData?.data?.sets.map((s) => ({ label: s.name, value: s.set_id }))}
            />
          </Form.Item>
          <Alert
            message="服务发布后，将提供 REST API 端点供在线推理服务调用"
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 特征详情抽屉 */}
      <Drawer
        title="特征详情"
        open={isFeatureDetailOpen}
        onClose={() => {
          setIsFeatureDetailOpen(false);
          setSelectedFeature(null);
        }}
        width={600}
      >
        {selectedFeature && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="特征名称" span={2}>
                {selectedFeature.name}
              </Descriptions.Item>
              <Descriptions.Item label="特征组">
                <Tag>{selectedFeature.feature_group}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                <Badge count={`v${selectedFeature.version}`} />
              </Descriptions.Item>
              <Descriptions.Item label="数据类型">
                {dataTypeOptions.find((t) => t.value === selectedFeature.data_type)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="值类型">
                {valueTypeOptions.find((t) => t.value === selectedFeature.value_type)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="来源表" span={2}>
                {selectedFeature.source_table}.{selectedFeature.source_column}
              </Descriptions.Item>
              <Descriptions.Item label="状态" span={2}>
                <Tag color={selectedFeature.status === 'active' ? 'success' : 'default'}>
                  {selectedFeature.status === 'active' ? '活跃' : selectedFeature.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedFeature.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
              {selectedFeature.transform_sql && (
                <Descriptions.Item label="转换 SQL" span={2}>
                  <pre style={{ margin: 0, fontSize: 12, background: '#f5f5f5', padding: 8 }}>
                    {selectedFeature.transform_sql}
                  </pre>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建者">
                {selectedFeature.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedFeature.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            </Descriptions>

            {/* 版本历史 */}
            <div style={{ marginTop: 24 }}>
              <h4>版本历史</h4>
              {versionsData?.data?.versions ? (
                <Table
                  size="small"
                  columns={[
                    { title: '版本', dataIndex: 'version', key: 'version', render: (v: number) => `v${v}` },
                    { title: '描述', dataIndex: 'description', key: 'description' },
                    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag>{s}</Tag> },
                    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (d: string) => dayjs(d).format('YYYY-MM-DD') },
                  ]}
                  dataSource={versionsData.data.versions}
                  rowKey="version_id"
                  pagination={false}
                />
              ) : (
                <span style={{ color: '#999' }}>暂无版本历史</span>
              )}
            </div>

            {/* API 调用示例 */}
            <div style={{ marginTop: 24 }}>
              <h4>API 调用示例</h4>
              <Alert
                message={
                  <pre style={{ margin: 0, fontSize: 12 }}>
{`curl -X POST \\
  http://api.example.com/v1/features/${selectedFeature.name} \\
  -H "Content-Type: application/json" \\
  -d '{"entity_id": "12345"}'`}
                  </pre>
                }
                type="info"
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default FeaturesPage;
