import { useState } from 'react';
import {
  Card,
  List,
  Tag,
  Button,
  Space,
  Typography,
  Input,
  Select,
  Modal,
  Empty,
  Divider,
  Avatar,
  Skeleton,
} from 'antd';
import {
  NotificationOutlined,
  SearchOutlined,
  ReloadOutlined,
  PushpinOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  ToolOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  AlertOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { Announcement } from '../../services/admin';
import { getAnnouncements } from '../../services/admin';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

// 公告类型图标
const getAnnouncementIcon = (type: string) => {
  switch (type) {
    case 'info':
      return <InfoCircleOutlined style={{ color: '#1677ff' }} />;
    case 'update':
      return <ToolOutlined style={{ color: '#52c41a' }} />;
    case 'maintenance':
      return <ToolOutlined style={{ color: '#faad14' }} />;
    case 'warning':
      return <WarningOutlined style={{ color: '#faad14' }} />;
    case 'urgent':
      return <AlertOutlined style={{ color: '#ff4d4f' }} />;
    default:
      return <NotificationOutlined style={{ color: '#1677ff' }} />;
  }
};

// 公告类型标签
const getTypeTag = (type: string) => {
  const config: Record<string, { color: string; text: string }> = {
    info: { color: 'blue', text: '通知' },
    update: { color: 'green', text: '更新' },
    maintenance: { color: 'orange', text: '维护' },
    warning: { color: 'gold', text: '警告' },
    urgent: { color: 'red', text: '紧急' },
  };
  const { color, text } = config[type] || config.info;
  return <Tag color={color}>{text}</Tag>;
};

function AnnouncementsPage() {
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<Announcement | null>(null);
  const [searchText, setSearchText] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // 获取公告列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['announcements', page, typeFilter],
    queryFn: async () => {
      const response = await getAnnouncements({
        page,
        page_size: pageSize,
        type: typeFilter,
        active_only: true,
      });
      if (response.code === 0) {
        return response.data;
      }
      throw new Error(response.message);
    },
  });

  // 过滤搜索
  const filteredAnnouncements = data?.announcements?.filter((item) => {
    if (!searchText) return true;
    return (
      item.title.toLowerCase().includes(searchText.toLowerCase()) ||
      item.summary?.toLowerCase().includes(searchText.toLowerCase())
    );
  });

  // 分离置顶和普通公告
  const pinnedAnnouncements = filteredAnnouncements?.filter((a) => a.is_pinned) || [];
  const normalAnnouncements = filteredAnnouncements?.filter((a) => !a.is_pinned) || [];

  const renderAnnouncementItem = (item: Announcement) => (
    <List.Item
      key={item.id}
      style={{
        padding: '16px 24px',
        cursor: 'pointer',
        borderRadius: 8,
        marginBottom: 8,
        backgroundColor: item.is_pinned ? '#fffbe6' : '#fff',
        border: item.is_pinned ? '1px solid #ffe58f' : '1px solid #f0f0f0',
      }}
      onClick={() => setSelectedAnnouncement(item)}
    >
      <List.Item.Meta
        avatar={
          <Avatar
            size={48}
            style={{
              backgroundColor: item.is_pinned ? '#fff7e6' : '#f0f5ff',
            }}
            icon={getAnnouncementIcon(item.announcement_type)}
          />
        }
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {item.is_pinned && (
              <PushpinOutlined style={{ color: '#faad14' }} />
            )}
            <Text strong style={{ fontSize: 16 }}>
              {item.title}
            </Text>
            {getTypeTag(item.announcement_type)}
          </div>
        }
        description={
          <div>
            <Paragraph
              type="secondary"
              ellipsis={{ rows: 2 }}
              style={{ marginBottom: 8 }}
            >
              {item.summary || item.content?.slice(0, 200)}
            </Paragraph>
            <Space size="middle">
              <Text type="secondary" style={{ fontSize: 12 }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                {item.publish_at?.slice(0, 10) || item.created_at?.slice(0, 10)}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <EyeOutlined style={{ marginRight: 4 }} />
                {item.view_count || 0} 次浏览
              </Text>
            </Space>
          </div>
        }
      />
    </List.Item>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <NotificationOutlined style={{ marginRight: 8 }} />
              系统公告
            </Title>
            <Text type="secondary">
              共 {data?.total || 0} 条公告
            </Text>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
          </Space>
        </div>

        <div style={{ marginBottom: 24, display: 'flex', gap: 8 }}>
          <Search
            placeholder="搜索公告..."
            allowClear
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            options={[
              { value: 'info', label: '通知' },
              { value: 'update', label: '更新' },
              { value: 'maintenance', label: '维护' },
              { value: 'warning', label: '警告' },
              { value: 'urgent', label: '紧急' },
            ]}
            value={typeFilter}
            onChange={setTypeFilter}
          />
        </div>

        {isLoading ? (
          <div>
            {[1, 2, 3].map((i) => (
              <Card key={i} style={{ marginBottom: 16 }}>
                <Skeleton active avatar paragraph={{ rows: 2 }} />
              </Card>
            ))}
          </div>
        ) : filteredAnnouncements?.length === 0 ? (
          <Empty description="暂无公告" />
        ) : (
          <>
            {/* 置顶公告 */}
            {pinnedAnnouncements.length > 0 && (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ color: '#faad14' }}>
                    <PushpinOutlined style={{ marginRight: 4 }} />
                    置顶公告
                  </Text>
                </div>
                <List
                  dataSource={pinnedAnnouncements}
                  renderItem={renderAnnouncementItem}
                />
                <Divider />
              </>
            )}

            {/* 普通公告 */}
            {normalAnnouncements.length > 0 && (
              <>
                {pinnedAnnouncements.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>最新公告</Text>
                  </div>
                )}
                <List
                  dataSource={normalAnnouncements}
                  renderItem={renderAnnouncementItem}
                  pagination={{
                    current: page,
                    pageSize: pageSize,
                    total: data?.total || 0,
                    onChange: setPage,
                    showSizeChanger: false,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条`,
                  }}
                />
              </>
            )}
          </>
        )}
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={
          <Space>
            {selectedAnnouncement?.is_pinned && (
              <PushpinOutlined style={{ color: '#faad14' }} />
            )}
            {selectedAnnouncement && getAnnouncementIcon(selectedAnnouncement.announcement_type)}
            {selectedAnnouncement?.title}
          </Space>
        }
        open={!!selectedAnnouncement}
        onCancel={() => setSelectedAnnouncement(null)}
        footer={
          <Button onClick={() => setSelectedAnnouncement(null)}>
            关闭
          </Button>
        }
        width={700}
      >
        {selectedAnnouncement && (
          <div style={{ padding: '16px 0' }}>
            <div style={{ marginBottom: 16 }}>
              {selectedAnnouncement.is_pinned && (
                <Tag color="warning">置顶</Tag>
              )}
              {getTypeTag(selectedAnnouncement.announcement_type)}
              <Text type="secondary" style={{ marginLeft: 8 }}>
                发布于 {selectedAnnouncement.publish_at?.slice(0, 10) || selectedAnnouncement.created_at?.slice(0, 10)}
              </Text>
              <Text type="secondary" style={{ marginLeft: 16 }}>
                <EyeOutlined style={{ marginRight: 4 }} />
                {selectedAnnouncement.view_count || 0} 次浏览
              </Text>
            </div>
            <Divider />
            <div
              style={{
                whiteSpace: 'pre-wrap',
                lineHeight: 1.8,
                fontSize: 14,
              }}
            >
              {selectedAnnouncement.content || selectedAnnouncement.summary}
            </div>
            {(selectedAnnouncement.start_time || selectedAnnouncement.end_time) && (
              <>
                <Divider />
                <div>
                  <Text type="secondary">
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    有效期:
                    {selectedAnnouncement.start_time && ` ${selectedAnnouncement.start_time.slice(0, 10)}`}
                    {selectedAnnouncement.start_time && selectedAnnouncement.end_time && ' ~ '}
                    {selectedAnnouncement.end_time && selectedAnnouncement.end_time.slice(0, 10)}
                  </Text>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default AnnouncementsPage;
