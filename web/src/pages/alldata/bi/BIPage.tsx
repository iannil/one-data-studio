import { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Drawer,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  EyeOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  TableOutlined,
  DashboardOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { Report, CreateReportRequest } from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;

function BIPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [chartData, setChartData] = useState<any>(null); // 真实图表数据

  const [form] = Form.useForm();

  // Queries
  const { data: reportsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['reports', page, pageSize, typeFilter, statusFilter],
    queryFn: () =>
      alldata.getReports({
        page,
        page_size: pageSize,
        type: typeFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: alldata.createReport,
    onSuccess: () => {
      message.success('报表创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: () => {
      message.error('报表创建失败');
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      published: 'green',
      draft: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      published: '已发布',
      draft: '草稿',
    };
    return texts[status] || status;
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'dashboard':
        return <DashboardOutlined />;
      case 'chart':
        return <BarChartOutlined />;
      case 'table':
        return <TableOutlined />;
      default:
        return <FileTextOutlined />;
    }
  };

  const columns = [
    {
      title: '报表名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Report) => (
        <a onClick={async () => {
          setSelectedReport(record);
          setIsDetailDrawerOpen(true);
          // 尝试获取真实图表数据
          const data = await fetchReportChartData(record.report_id);
          setChartData(data);
        }}>
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag icon={getTypeIcon(type)}>{type === 'dashboard' ? '仪表板' : type === 'chart' ? '图表' : '表格'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags?: string[]) => (
        <>
          {tags?.slice(0, 2).map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
          {tags && tags.length > 2 && <Tag>+{tags.length - 2}</Tag>}
        </>
      ),
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
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Report) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={async () => {
              setSelectedReport(record);
              setIsDetailDrawerOpen(true);
              // 尝试获取真实图表数据
              const data = await fetchReportChartData(record.report_id);
              setChartData(data);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedReport(record);
              form.setFieldsValue(record);
              setIsCreateModalOpen(true);
            }}
          />
        </Space>
      ),
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateReportRequest = {
        ...values,
        tags: values.tags || [],
      };
      createMutation.mutate(data);
    });
  };

  // 获取报表图表数据（真实API调用）
  const fetchReportChartData = async (reportId: string) => {
    try {
      const response = await alldata.getReportData(reportId);
      // 类型断言：API返回的data包含chart_data字段
      return (response.data as { chart_data?: any })?.chart_data || null;
    } catch (error) {
      console.warn('Failed to fetch chart data, using demo data:', error);
      return null;
    }
  };

  // 模拟图表数据（仅用于演示，实际生产环境应从API获取真实数据）
  const mockChartData = {
    line: [
      { date: '2024-01', value: 120 },
      { date: '2024-02', value: 200 },
      { date: '2024-03', value: 150 },
      { date: '2024-04', value: 80 },
      { date: '2024-05', value: 70 },
      { date: '2024-06', value: 110 },
    ],
    bar: [
      { category: '数据质量', value: 85 },
      { category: '完整性', value: 92 },
      { category: '准确性', value: 78 },
      { category: '一致性', value: 88 },
      { category: '时效性', value: 95 },
    ],
    pie: [
      { name: 'MySQL', value: 45 },
      { name: 'PostgreSQL', value: 30 },
      { name: 'Oracle', value: 15 },
      { name: '其他', value: 10 },
    ],
  };

  const reportTypes = [
    { value: 'dashboard', label: '仪表板' },
    { value: 'chart', label: '图表' },
    { value: 'table', label: '表格' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16}>
        {/* 报表列表 */}
        <Col span={24}>
          <Card
            title="BI 报表"
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                创建报表
              </Button>
            }
          >
            <Space style={{ marginBottom: 16 }} size="middle">
              <Select
                placeholder="类型筛选"
                allowClear
                style={{ width: 120 }}
                onChange={setTypeFilter}
                value={typeFilter || undefined}
              >
                {reportTypes.map((type) => (
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
                <Option value="published">已发布</Option>
                <Option value="draft">草稿</Option>
              </Select>
            </Space>

            <Table
              columns={columns}
              dataSource={reportsData?.data?.reports || []}
              rowKey="report_id"
              loading={isLoadingList}
              pagination={{
                current: page,
                pageSize: pageSize,
                total: reportsData?.data?.total || 0,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (newPage, newPageSize) => {
                  setPage(newPage);
                  setPageSize(newPageSize || 10);
                },
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 创建报表模态框 */}
      <Modal
        title={selectedReport ? '编辑报表' : '创建报表'}
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setSelectedReport(null);
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="报表名称"
            name="name"
            rules={[{ required: true, message: '请输入报表名称' }]}
          >
            <Input placeholder="请输入报表名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="报表类型"
            name="type"
            rules={[{ required: true, message: '请选择报表类型' }]}
            initialValue="dashboard"
          >
            <Select>
              {reportTypes.map((type) => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="数据集" name="dataset_id">
            <Select placeholder="选择数据集" allowClear>
              <Option value="dataset1">销售数据集</Option>
              <Option value="dataset2">用户行为数据集</Option>
            </Select>
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 报表详情抽屉 */}
      <Drawer
        title="报表详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedReport(null);
          setChartData(null);
        }}
        width={1000}
      >
        {selectedReport && (
          <div>
            <Tabs
              defaultActiveKey="preview"
              items={[
                {
                  key: 'preview',
                  label: '预览',
                  children: (
                    <div>
                      <h3>{selectedReport.name}</h3>
                      {selectedReport.description && (
                        <p style={{ color: '#666', marginBottom: 24 }}>{selectedReport.description}</p>
                      )}
                      <Row gutter={16}>
                        <Col span={12}>
                          <Card
                            title={<><LineChartOutlined /> 趋势分析{chartData ? '' : '（示例）'}</>}
                            size="small"
                            style={{ height: 300 }}
                          >
                            <div style={{ height: 220, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
                              {(chartData?.line || mockChartData.line).map((d) => (
                                <div
                                  key={d.date}
                                  style={{
                                    flex: 1,
                                    height: `${(d.value / 200) * 100}%`,
                                    background: '#1677ff',
                                    borderRadius: '4px 4px 0 0',
                                  }}
                                />
                              ))}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                              {(chartData?.line || mockChartData.line).map((d) => (
                                <span key={d.date} style={{ fontSize: 10 }}>{d.date}</span>
                              ))}
                            </div>
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card
                            title={<><BarChartOutlined /> 数据质量评分{chartData ? '' : '（示例）'}</>}
                            size="small"
                            style={{ height: 300 }}
                          >
                            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, height: 200 }}>
                              {(chartData?.bar || mockChartData.bar).map((d) => (
                                <div
                                  key={d.category}
                                  style={{
                                    flex: 1,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                  }}
                                >
                                  <div
                                    style={{
                                      width: '100%',
                                      height: `${d.value}%`,
                                      background: '#52c41a',
                                      borderRadius: '4px 4px 0 0',
                                    }}
                                  />
                                  <span style={{ fontSize: 10, marginTop: 4 }}>{d.category}</span>
                                  <span style={{ fontSize: 12, fontWeight: 'bold' }}>{d.value}</span>
                                </div>
                              ))}
                            </div>
                          </Card>
                        </Col>
                      </Row>
                      <Row gutter={16} style={{ marginTop: 16 }}>
                        <Col span={12}>
                          <Card
                            title={<><PieChartOutlined /> 数据源分布{chartData ? '' : '（示例）'}</>}
                            size="small"
                            style={{ height: 300 }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
                              {(chartData?.pie || mockChartData.pie).map((d, i) => {
                                const colors = ['#1677ff', '#52c41a', '#faad14', '#722ed1'];
                                return (
                                  <div
                                    key={d.name}
                                    style={{
                                      display: 'flex',
                                      flexDirection: 'column',
                                      alignItems: 'center',
                                    }}
                                  >
                                    <div
                                      style={{
                                        width: 80,
                                        height: 80,
                                        borderRadius: '50%',
                                        background: `conic-gradient(${colors[i]} ${d.value}%, #f0f0f0 ${d.value}%)`,
                                      }}
                                    />
                                    <span style={{ fontSize: 12, marginTop: 8 }}>{d.name}</span>
                                    <span style={{ fontSize: 12, fontWeight: 'bold' }}>{d.value}%</span>
                                  </div>
                                );
                              })}
                            </div>
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card
                            title={<><TableOutlined /> 数据预览{chartData ? '' : '（示例）'}</>}
                            size="small"
                            style={{ height: 300 }}
                          >
                            <Table
                              size="small"
                              columns={[
                                { title: '日期', dataIndex: 'date' },
                                { title: '销售额', dataIndex: 'sales' },
                                { title: '订单数', dataIndex: 'orders' },
                              ]}
                              dataSource={[
                                { date: '2024-01-01', sales: '12,345', orders: '123' },
                                { date: '2024-01-02', sales: '23,456', orders: '234' },
                                { date: '2024-01-03', sales: '34,567', orders: '345' },
                                { date: '2024-01-04', sales: '45,678', orders: '456' },
                              ]}
                              pagination={false}
                            />
                          </Card>
                        </Col>
                      </Row>
                    </div>
                  ),
                },
                {
                  key: 'config',
                  label: '配置',
                  children: (
                    <Card title="报表配置" size="small">
                      <p><strong>报表ID:</strong> {selectedReport.report_id}</p>
                      <p><strong>类型:</strong> {selectedReport.type}</p>
                      <p><strong>数据集:</strong> {selectedReport.dataset_id || '-'}</p>
                      <p><strong>状态:</strong> <Tag color={getStatusColor(selectedReport.status)}>{getStatusText(selectedReport.status)}</Tag></p>
                      <p><strong>创建者:</strong> {selectedReport.created_by}</p>
                      <p><strong>创建时间:</strong> {dayjs(selectedReport.created_at).format('YYYY-MM-DD HH:mm:ss')}</p>
                    </Card>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default BIPage;
