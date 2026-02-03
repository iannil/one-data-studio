/**
 * 用户画像查看页面
 * 展示单个用户的详细画像信息
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Descriptions,
  Tag,
  Progress,
  Timeline,
  List,
  Statistic,
  Button,
  Space,
  Select,
  Input,
  Empty,
  Spin
} from 'antd';
import {
  UserOutlined,
  ReloadOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  TrophyOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { behaviorApi } from '@/services/behavior';

const { Search } = Input;
const { Option } = Select;

interface UserProfile {
  id: string;
  user_id: string;
  username?: string;
  email?: string;
  department?: string;
  position?: string;
  activity_level: string;
  last_active_at?: string;
  login_frequency: number;
  avg_session_duration: number;
  preferred_modules?: string[];
  preferred_time_ranges?: Array<{
    range: string;
    count: number;
    percentage: number;
  }>;
  common_actions?: Array<{
    action: string;
    type: string;
    count: number;
  }>;
  total_sessions: number;
  total_page_views: number;
  total_actions: number;
  avg_daily_usage: number;
  segment_tags?: string[];
}

interface UserActivity {
  total_sessions: number;
  total_page_views: number;
  total_actions: number;
  avg_daily_sessions: number;
  avg_daily_duration: number;
  most_active_hour: number;
  most_visited_pages: Array<{
    url: string;
    count: number;
  }>;
  activity_trend: Array<{
    date: string;
    count: number;
  }>;
}

export const ProfileView: React.FC = () => {
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [searchValue, setSearchValue] = useState<string>('');

  const { data: profileData, isLoading: profileLoading, refetch: refetchProfile } = useQuery({
    queryKey: ['behavior-profile', selectedUserId],
    queryFn: () => behaviorApi.getUserProfile(selectedUserId, true),
    enabled: !!selectedUserId,
    select: (data) => data.data.data,
  });

  const { data: activityData } = useQuery({
    queryKey: ['behavior-activity', selectedUserId],
    queryFn: () => behaviorApi.getUserActivity(selectedUserId, 30),
    enabled: !!selectedUserId,
    select: (data) => data.data.data,
  });

  const { data: similarUsers } = useQuery({
    queryKey: ['behavior-similar', selectedUserId],
    queryFn: () => behaviorApi.getSimilarUsers(selectedUserId),
    select: (data) => data.data.data,
    enabled: !!selectedUserId,
  });

  const handleSearch = () => {
    if (searchValue) {
      setSelectedUserId(searchValue);
    }
  };

  const activityLevelConfig: Record<string, { color: string; text: string }> = {
    high: { color: 'success', text: '高活跃' },
    medium: { color: 'processing', text: '中活跃' },
    low: { color: 'warning', text: '低活跃' },
    inactive: { color: 'default', text: '不活跃' },
  };

  return (
    <div className="user-profile-view">
      <Card
        title={
          <Space>
            <UserOutlined />
            <span>用户画像</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        查看用户行为画像和活跃度分析
      </Card>

      <div className="page-content">
        <Card style={{ marginBottom: 16 }}>
          <Space>
            <Search
              placeholder="输入用户ID"
              enterButton={<SearchOutlined />}
              size="large"
              style={{ width: 300 }}
              onSearch={handleSearch}
              onChange={(e) => setSearchValue(e.target.value)}
              value={searchValue}
            />
          </Space>
        </Card>

        {selectedUserId && (
          <Spin spinning={profileLoading}>
            {profileData ? (
              <Row gutter={16}>
                {/* 基础信息 */}
                <Col span={8}>
                  <Card
                    title="基础信息"
                    extra={
                      <Button
                        icon={<ReloadOutlined />}
                        size="small"
                        onClick={() => refetchProfile()}
                      >
                        刷新
                      </Button>
                    }
                  >
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="用户ID">
                        {profileData.user_id}
                      </Descriptions.Item>
                      <Descriptions.Item label="用户名">
                        {profileData.username || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="邮箱">
                        {profileData.email || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="部门">
                        {profileData.department || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="职位">
                        {profileData.position || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="活跃度">
                        <Tag color={activityLevelConfig[profileData.activity_level]?.color}>
                          {activityLevelConfig[profileData.activity_level]?.text}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="最后活跃">
                        {profileData.last_active_at
                          ? new Date(profileData.last_active_at).toLocaleString('zh-CN')
                          : '未知'}
                      </Descriptions.Item>
                    </Descriptions>

                    <div style={{ marginTop: 16 }}>
                      <h4>用户标签</h4>
                      <Space wrap>
                        {profileData.segment_tags?.map((tag: string) => (
                          <Tag key={tag} color="blue">
                            {tag}
                          </Tag>
                        )) || <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无标签" />}
                      </Space>
                    </div>
                  </Card>
                </Col>

                {/* 使用统计 */}
                <Col span={16}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="总会话数"
                          value={profileData.total_sessions}
                          suffix="次"
                          prefix={<TrophyOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="页面浏览"
                          value={profileData.total_page_views}
                          suffix="次"
                          prefix={<EyeOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="操作次数"
                          value={profileData.total_actions}
                          suffix="次"
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="日均使用"
                          value={profileData.avg_daily_usage}
                          suffix="分钟"
                          precision={1}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Card title="行为偏好" style={{ marginTop: 16 }}>
                    <Row gutter={16}>
                      <Col span={12}>
                        <h4>偏好模块</h4>
                        <Space wrap>
                          {profileData.preferred_modules?.map((module: string) => (
                            <Tag key={module} color="geekblue">
                              {module}
                            </Tag>
                          )) || <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                        </Space>
                      </Col>
                      <Col span={12}>
                        <h4>常用操作</h4>
                        <List
                          size="small"
                          dataSource={profileData.common_actions?.slice(0, 5)}
                          renderItem={(item: { action: string; count: number; type?: string }) => (
                            <List.Item>
                              <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                                <span>{item.action}</span>
                                <Tag>{item.count}次</Tag>
                              </Space>
                            </List.Item>
                          )}
                        />
                      </Col>
                    </Row>

                    {profileData.preferred_time_ranges && (
                      <div style={{ marginTop: 16 }}>
                        <h4>活跃时段偏好</h4>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          {profileData.preferred_time_ranges.map((timeRange: { range: string; count: number; percentage: number }) => (
                            <div key={timeRange.range}>
                              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                <span>{timeRange.range}</span>
                                <span>{timeRange.percentage}%</span>
                              </Space>
                              <Progress percent={timeRange.percentage} showInfo={false} />
                            </div>
                          ))}
                        </Space>
                      </div>
                    )}
                  </Card>
                </Col>

                {/* 活动趋势 */}
                <Col span={24} style={{ marginTop: 16 }}>
                  <Card title="活动趋势">
                    <Row gutter={16}>
                      <Col span={12}>
                        <h4>每日活动量</h4>
                        <Timeline
                          mode="left"
                          items={activityData?.activity_trend?.slice(-10).map((item: { date: string; count: number }) => ({
                            label: item.date,
                            children: `${item.count} 次行为`,
                          }))}
                        />
                      </Col>
                      <Col span={12}>
                        <h4>常用页面</h4>
                        <List
                          size="small"
                          dataSource={activityData?.most_visited_pages?.slice(0, 5)}
                          renderItem={(item: { url: string; count: number }) => (
                            <List.Item>
                              <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                                <span style={{ fontSize: 12 }}>{item.url}</span>
                                <Tag>{item.count}次</Tag>
                              </Space>
                            </List.Item>
                          )}
                        />
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 相似用户 */}
                <Col span={24} style={{ marginTop: 16 }}>
                  <Card title="相似用户">
                    <List
                      grid={{ gutter: 16, column: 4 }}
                      dataSource={similarUsers?.similar_users?.slice(0, 8)}
                      renderItem={(item: { username?: string; user_id: string; similarity_score: number }) => (
                        <List.Item>
                          <Card size="small">
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <span>{item.username || item.user_id}</span>
                              <Progress
                                type="circle"
                                percent={Math.round(item.similarity_score * 100)}
                                size={60}
                              />
                            </Space>
                          </Card>
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
              </Row>
            ) : (
              <Card>
                <Empty description="未找到用户画像数据" />
              </Card>
            )}
          </Spin>
        )}

        {!selectedUserId && (
          <Card>
            <Empty
              description="请输入用户ID查看画像"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </Card>
        )}
      </div>
    </div>
  );
};

export default ProfileView;
