import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Input,
  Select,
  Row,
  Col,
  Statistic,
  Progress,
  Avatar,
  Tooltip,
  Modal,
  Descriptions,
  Divider,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  UserOutlined,
  ThunderboltFilled,
  ClockCircleOutlined,
  BarChartOutlined,
  FireOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import admin from '@/services/admin';

const { Search } = Input;
const { Option } = Select;

interface UserProfile {
  profile_id: string;
  user_id: string;
  username: string;
  activity_score: number;
  segment_id: string;
  segment_name?: string;
  behavior_tags: Array<{ tag: string; score: number }>;
  login_count: number;
  login_days: number;
  query_count: number;
  export_count: number;
  create_count: number;
  is_risk_user: boolean;
  last_login_at: string;
  preference_features?: {
    time_preference?: string;
    preferred_module?: string;
    operation_preference?: {
      query: number;
      create: number;
      export: number;
    };
  };
}

function UserProfilesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchText, setSearchText] = useState('');
  const [segmentFilter, setSegmentFilter] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // 获取用户画像列表
  const { data: profilesData, isLoading } = useQuery({
    queryKey: ['user-profiles', page, pageSize, searchText, segmentFilter],
    queryFn: () =>
      admin.getUserProfiles({
        page,
        page_size: pageSize,
        search: searchText || undefined,
        segment_id: segmentFilter || undefined,
      }),
  });

  // 获取用户分群列表
  const { data: segmentsData } = useQuery({
    queryKey: ['user-segments'],
    queryFn: () => admin.getUserSegments(),
  });

  const segments = segmentsData?.data?.segments || [];

  // 刷新分析
  const refreshMutation = useMutation({
    mutationFn: () => admin.refreshUserProfiles(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-profiles'] });
      Modal.success({
        title: '刷新成功',
        content: '用户画像分析已完成',
      });
    },
  });

  const getActivityLevel = (score: number) => {
    if (score >= 80) return { level: '高', color: 'success' };
    if (score >= 50) return { level: '中', color: 'processing' };
    return { level: '低', color: 'default' };
  };

  const getTagColor = (tagName: string) => {
    const colorMap: Record<string, string> = {
      active: 'green',
      expert: 'blue',
      explorer: 'purple',
      data_consumer: 'cyan',
      data_creator: 'magenta',
      night_owl: 'orange',
      early_bird: 'gold',
      high_risk: 'red',
    };
    return colorMap[tagName] || 'default';
  };

  const getSegmentName = (segmentId: string) => {
    const seg = segments.find((s: { segment_id: string; segment_name: string }) => s.segment_id === segmentId);
    return seg?.segment_name || segmentId;
  };

  const columns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (username: string, record: UserProfile) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div>{username || record.user_id}</div>
            <div style={{ fontSize: 12, color: '#999' }}>{record.user_id}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '活跃度',
      dataIndex: 'activity_score',
      key: 'activity_score',
      sorter: true,
      render: (score: number) => {
        const { level, color } = getActivityLevel(score);
        return (
          <Space>
            <Progress
              type="circle"
              percent={Math.round(score)}
              width={50}
              strokeColor={color === 'success' ? '#52c41a' : color === 'processing' ? '#1677ff' : '#d9d9d9'}
            />
            <Tag color={color}>{level}</Tag>
          </Space>
        );
      },
    },
    {
      title: '行为标签',
      dataIndex: 'behavior_tags',
      key: 'behavior_tags',
      render: (tags: Array<{ tag: string; score: number }>) => (
        <Space wrap size="small">
          {tags.slice(0, 3).map((t) => (
            <Tag key={t.tag} color={getTagColor(t.tag)}>
              {t.tag}
            </Tag>
          ))}
          {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: '分群',
      dataIndex: 'segment_id',
      key: 'segment_id',
      render: (segmentId: string) => {
        const seg = segments.find((s: { segment_id: string; segment_name: string }) => s.segment_id === segmentId);
        return seg ? (
          <Tag color="blue">{seg.segment_name}</Tag>
        ) : null;
      },
    },
    {
      title: '操作统计',
      key: 'stats',
      render: (_: unknown, record: UserProfile) => (
        <Space size="large">
          <Tooltip title="登录次数">
            <span><ClockCircleOutlined /> {record.login_count}</span>
          </Tooltip>
          <Tooltip title="查询次数">
            <span><SearchOutlined /> {record.query_count}</span>
          </Tooltip>
          <Tooltip title="导出次数">
            <span><BarChartOutlined /> {record.export_count}</span>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string) => (date ? dayjs(date).fromNow() : '从未'),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: UserProfile) => (
        <>
          {record.is_risk_user && (
            <Tag color="red" icon={<FireOutlined />}>
              风险用户
            </Tag>
          )}
        </>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserProfile) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedUser(record);
            setIsDetailModalOpen(true);
          }}
        >
          查看详情
        </Button>
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
              title="总用户数"
              value={profilesData?.data?.total || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={profilesData?.data?.active_count || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<ThunderboltFilled />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="风险用户"
              value={profilesData?.data?.risk_count || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<FireOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均活跃度"
              value={profilesData?.data?.avg_activity || 0}
              suffix="分"
              precision={1}
            />
          </Card>
        </Col>
      </Row>

      {/* 用户画像列表 */}
      <Card
        title="用户画像"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refreshMutation.mutate()}
              loading={refreshMutation.isPending}
            >
              刷新分析
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Search
            placeholder="搜索用户名或用户ID"
            allowClear
            style={{ width: 250 }}
            onSearch={setSearchText}
            enterButton
          />
          <Select
            placeholder="筛选分群"
            allowClear
            style={{ width: 150 }}
            onChange={setSegmentFilter}
            value={segmentFilter || undefined}
          >
            {segments.map((seg: { segment_id: string; segment_name: string }) => (
              <Option key={seg.segment_id} value={seg.segment_id}>
                {seg.segment_name}
              </Option>
            ))}
          </Select>
        </Space>

        <Table
          columns={columns as any}
          dataSource={profilesData?.data?.profiles || []}
          rowKey="profile_id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: profilesData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个用户`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 20);
            },
          }}
        />
      </Card>

      {/* 用户详情弹窗 */}
      <Modal
        title="用户画像详情"
        open={isDetailModalOpen}
        onCancel={() => {
          setIsDetailModalOpen(false);
          setSelectedUser(null);
        }}
        footer={null}
        width={800}
      >
        {selectedUser && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="用户ID">{selectedUser.user_id}</Descriptions.Item>
              <Descriptions.Item label="用户名">{selectedUser.username || '-'}</Descriptions.Item>
              <Descriptions.Item label="活跃度分数">
                <Progress
                  percent={Math.round(selectedUser.activity_score)}
                  strokeColor={
                    selectedUser.activity_score >= 80
                      ? '#52c41a'
                      : selectedUser.activity_score >= 50
                      ? '#1677ff'
                      : '#d9d9d9'
                  }
                />
              </Descriptions.Item>
              <Descriptions.Item label="所属分群">{getSegmentName(selectedUser.segment_id)}</Descriptions.Item>
              <Descriptions.Item label="登录次数">{selectedUser.login_count}</Descriptions.Item>
              <Descriptions.Item label="活跃天数">{selectedUser.login_days}</Descriptions.Item>
              <Descriptions.Item label="查询次数">{selectedUser.query_count}</Descriptions.Item>
              <Descriptions.Item label="导出次数">{selectedUser.export_count}</Descriptions.Item>
              <Descriptions.Item label="创建次数">{selectedUser.create_count}</Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {selectedUser.last_login_at ? dayjs(selectedUser.last_login_at).format('YYYY-MM-DD HH:mm') : '从未'}
              </Descriptions.Item>
              <Descriptions.Item label="风险状态">
                {selectedUser.is_risk_user ? (
                  <Tag color="red">风险用户</Tag>
                ) : (
                  <Tag color="green">正常</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">行为标签</Divider>
            <Space wrap>
              {selectedUser.behavior_tags.map((tag) => (
                <Tag key={tag.tag} color={getTagColor(tag.tag)}>
                  {tag.tag} ({Math.round(tag.score * 100)}%)
                </Tag>
              ))}
            </Space>

            {selectedUser.preference_features && (
              <>
                <Divider orientation="left">偏好特征</Divider>
                <Descriptions column={2} size="small">
                  {selectedUser.preference_features.time_preference && (
                    <Descriptions.Item label="时间偏好">
                      <Tag>
                        {selectedUser.preference_features.time_preference === 'day' ? '日间活跃' : '夜间活跃'}
                      </Tag>
                    </Descriptions.Item>
                  )}
                  {selectedUser.preference_features.preferred_module && (
                    <Descriptions.Item label="偏好模块">
                      <Tag color="blue">{selectedUser.preference_features.preferred_module}</Tag>
                    </Descriptions.Item>
                  )}
                  {selectedUser.preference_features.operation_preference && (
                    <>
                      <Descriptions.Item label="查询偏好">
                        {Math.round(selectedUser.preference_features.operation_preference.query * 100)}%
                      </Descriptions.Item>
                      <Descriptions.Item label="创建偏好">
                        {Math.round(selectedUser.preference_features.operation_preference.create * 100)}%
                      </Descriptions.Item>
                    </>
                  )}
                </Descriptions>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default UserProfilesPage;
