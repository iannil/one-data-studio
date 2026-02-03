import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Input,
  Modal,
  Form,
  Select,
  InputNumber,
  message,
  Descriptions,
  List,
  Progress,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TeamOutlined,
  UserOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import admin from '@/services/admin';

const { Option } = Select;
const { TextArea } = Input;

interface UserSegment {
  segment_id: string;
  segment_name: string;
  segment_type: string;
  description: string;
  criteria: Record<string, unknown>;
  characteristics?: {
    avg_activity: number;
    avg_login_days: number;
    common_tags: Record<string, number>;
    common_modules: Record<string, number>;
    user_count: number;
  };
  user_count: number;
  strategy: string;
  is_system: boolean;
  last_rebuilt_at: string;
}

function UserSegmentsPage() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState<UserSegment | null>(null);
  const [form] = Form.useForm();

  // 获取分群列表
  const { data: segmentsData, isLoading } = useQuery({
    queryKey: ['user-segments'],
    queryFn: () => admin.getUserSegments({ include_users: true }),
  });

  const segments = segmentsData?.data?.segments || [];

  // 重建分群
  const rebuildMutation = useMutation({
    mutationFn: admin.rebuildUserSegments,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-segments'] });
      message.success(`分群重建完成，处理了 ${data.data?.segmented_users || 0} 个用户`);
    },
  });

  const createMutation = useMutation({
    mutationFn: admin.createUserSegment,
    onSuccess: () => {
      message.success('分群创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['user-segments'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (segmentId: string) => admin.deleteUserSegment(segmentId),
    onSuccess: () => {
      message.success('分群已删除');
      queryClient.invalidateQueries({ queryKey: ['user-segments'] });
    },
  });

  const getSegmentTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      active: 'green',
      exploratory: 'blue',
      conservative: 'default',
      power: 'purple',
      new: 'cyan',
      churned: 'red',
    };
    return colors[type] || 'default';
  };

  const getSegmentTypeName = (type: string) => {
    const names: Record<string, string> = {
      active: '活跃用户',
      exploratory: '探索型',
      conservative: '保守型',
      power: '专家用户',
      new: '新用户',
      churned: '流失用户',
    };
    return names[type] || type;
  };

  const columns = [
    {
      title: '分群名称',
      dataIndex: 'segment_name',
      key: 'segment_name',
      render: (name: string, record: UserSegment) => (
        <Space>
          <TeamOutlined />
          <div>
            <div>{name}</div>
            {record.is_system && <Tag>系统预置</Tag>}
          </div>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'segment_type',
      key: 'segment_type',
      render: (type: string) => (
        <Tag color={getSegmentTypeColor(type)}>{getSegmentTypeName(type)}</Tag>
      ),
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      sorter: true,
      render: (count: number) => <strong>{count}</strong>,
    },
    {
      title: '特征',
      key: 'characteristics',
      render: (_: unknown, record: UserSegment) => {
        const chars = record.characteristics;
        return chars ? (
          <Space direction="vertical" size="small">
            <span>平均活跃度: <strong>{chars.avg_activity}</strong></span>
            <span>平均登录天数: <strong>{chars.avg_login_days}</strong></span>
          </Space>
        ) : '-';
      },
    },
    {
      title: '最后重建',
      dataIndex: 'last_rebuilt_at',
      key: 'last_rebuilt_at',
      render: (date: string) => (date ? dayjs(date).fromNow() : '从未'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserSegment) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setSelectedSegment(record);
              setIsDetailModalOpen(true);
            }}
          >
            查看
          </Button>
          {!record.is_system && (
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除分群"${record.segment_name}"吗？`,
                  onOk: () => deleteMutation.mutate(record.segment_id),
                });
              }}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总分群数"
              value={segments.length}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已分群用户"
              value={segments.reduce((sum, s) => sum + (s.user_count || 0), 0)}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最大分群"
              value={Math.max(...segments.map((s) => s.user_count || 0), 0)}
              suffix="用户"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均用户数"
              value={
                segments.length > 0
                  ? Math.round(
                      segments.reduce((sum, s) => sum + (s.user_count || 0), 0) / segments.length
                    )
                  : 0
              }
              suffix="用户/分群"
            />
          </Card>
        </Col>
      </Row>

      {/* 分群列表 */}
      <Card
        title="用户分群"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => rebuildMutation.mutate()}
              loading={rebuildMutation.isPending}
            >
              重建分群
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateModalOpen(true)}
            >
              创建分群
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns as any}
          dataSource={segments}
          rowKey="segment_id"
          loading={isLoading}
          pagination={false}
        />
      </Card>

      {/* 创建分群弹窗 */}
      <Modal
        title="创建自定义分群"
        open={isCreateModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item
            label="分群名称"
            name="segment_name"
            rules={[{ required: true, message: '请输入分群名称' }]}
          >
            <Input placeholder="例如：高价值用户" />
          </Form.Item>

          <Form.Item
            label="分群类型"
            name="segment_type"
            rules={[{ required: true, message: '请选择分群类型' }]}
          >
            <Select placeholder="选择类型">
              <Option value="custom">自定义</Option>
              <Option value="active">活跃用户</Option>
              <Option value="value">高价值用户</Option>
            </Select>
          </Form.Item>

          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="描述该分群的特征" />
          </Form.Item>

          <Form.Item label="活跃度分数范围">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item name={['criteria', 'activity_score_min']} noStyle>
                <InputNumber placeholder="最小值" min={0} max={100} style={{ width: '50%' }} />
              </Form.Item>
              <Form.Item name={['criteria', 'activity_score_max']} noStyle>
                <InputNumber placeholder="最大值" min={0} max={100} style={{ width: '50%' }} />
              </Form.Item>
            </Space.Compact>
          </Form.Item>

          <Form.Item label="最少登录天数" name={['criteria', 'login_days_min']}>
            <InputNumber placeholder="例如：7" min={0} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="运营策略建议" name="strategy">
            <TextArea rows={3} placeholder="针对该分群的运营策略" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 分群详情弹窗 */}
      <Modal
        title="分群详情"
        open={isDetailModalOpen}
        onCancel={() => {
          setIsDetailModalOpen(false);
          setSelectedSegment(null);
        }}
        footer={null}
        width={800}
      >
        {selectedSegment && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="分群名称" span={2}>
                {selectedSegment.segment_name}
              </Descriptions.Item>
              <Descriptions.Item label="分群类型">
                <Tag color={getSegmentTypeColor(selectedSegment.segment_type)}>
                  {getSegmentTypeName(selectedSegment.segment_type)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="用户数">
                {selectedSegment.user_count}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedSegment.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="最后重建" span={2}>
                {selectedSegment.last_rebuilt_at
                  ? dayjs(selectedSegment.last_rebuilt_at).format('YYYY-MM-DD HH:mm')
                  : '从未'}
              </Descriptions.Item>
            </Descriptions>

            {selectedSegment.characteristics && (
              <>
                <div style={{ marginTop: 24 }}>
                  <h4>分群特征</h4>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="平均活跃度"
                          value={selectedSegment.characteristics.avg_activity}
                          precision={1}
                          suffix="/ 100"
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="平均登录天数"
                          value={selectedSegment.characteristics.avg_login_days}
                          precision={1}
                          suffix="天"
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small">
                        <Statistic
                          title="用户数"
                          value={selectedSegment.characteristics.user_count}
                          suffix="人"
                        />
                      </Card>
                    </Col>
                  </Row>
                </div>

                {selectedSegment.characteristics.common_tags && (
                  <div style={{ marginTop: 16 }}>
                    <h4>常见标签</h4>
                    <Space wrap>
                      {Object.entries(selectedSegment.characteristics.common_tags).map(([tag, count]) => (
                        <Tag key={tag} color="blue">
                          {tag}: {count}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}

                {selectedSegment.characteristics.common_modules && (
                  <div style={{ marginTop: 16 }}>
                    <h4>常用模块</h4>
                    <List
                      size="small"
                      dataSource={Object.entries(selectedSegment.characteristics.common_modules)}
                      renderItem={([module, count]) => (
                        <List.Item>
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <span>{module}</span>
                            <Progress
                              percent={Math.round((count as number) / selectedSegment.user_count * 100)}
                              size="small"
                              style={{ width: 150 }}
                            />
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>
                )}
              </>
            )}

            {selectedSegment.strategy && (
              <div style={{ marginTop: 16 }}>
                <h4>运营策略</h4>
                <p>{selectedSegment.strategy}</p>
              </div>
            )}

            {selectedSegment.criteria && Object.keys(selectedSegment.criteria).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4>分群规则</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(selectedSegment.criteria, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default UserSegmentsPage;
