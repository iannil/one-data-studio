import { useMemo } from 'react';
import { Card, Select, Space, Tooltip, Row, Col, Statistic } from 'antd';
import { HeatMapOutlined } from '@ant-design/icons';

const { Option } = Select;

interface BehaviorHeatmapProps {
  data: Array<{
    hour?: number;
    day?: number;
    count: number;
    user_id?: string;
  }>;
  type?: 'hour-day' | 'user-activity';
  title?: string;
  height?: number;
}

export function BehaviorHeatmap({
  data,
  type = 'hour-day',
  title = '行为热力图',
  height = 300,
}: BehaviorHeatmapProps) {
  // 处理数据
  const heatmapData = useMemo(() => {
    if (type === 'hour-day') {
      // 小时 x 星期几 热力图
      const grid = Array(7)
        .fill(0)
        .map(() => Array(24).fill(0));

      data.forEach((item) => {
        if (item.day !== undefined && item.hour !== undefined) {
          grid[item.day][item.hour] = item.count;
        }
      });

      // 找出最大值用于归一化
      const maxCount = Math.max(...data.map((d) => d.count), 1);

      return { grid, maxCount };
    }
    return { grid: [], maxCount: 1 };
  }, [data, type]);

  const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const getColor = (value: number, max: number) => {
    if (value === 0) return '#f5f5f5';
    const ratio = value / max;
    if (ratio < 0.2) return '#e6f7ff';
    if (ratio < 0.4) return '#bae7ff';
    if (ratio < 0.6) return '#91d5ff';
    if (ratio < 0.8) return '#69c0ff';
    return '#1677ff';
  };

  // 计算统计数据
  const stats = useMemo(() => {
    const totalCount = data.reduce((sum, d) => sum + d.count, 0);
    const maxCount = Math.max(...data.map((d) => d.count), 0);
    const activeSlots = data.filter((d) => d.count > 0).length;

    return {
      total: totalCount,
      max: maxCount,
      activeSlots,
      avgSlots: Math.round(totalCount / Math.max(activeSlots, 1)),
    };
  }, [data]);

  if (type === 'hour-day') {
    const { grid, maxCount } = heatmapData;

    return (
      <Card
        title={
          <Space>
            <HeatMapOutlined />
            {title}
          </Space>
        }
        extra={
          <Space>
            <Statistic value={stats.total} suffix="次操作" valueStyle={{ fontSize: 14 }} />
            <Statistic
              value={stats.activeSlots}
              suffix="活跃时段"
              valueStyle={{ fontSize: 14 }}
            />
          </Space>
        }
        size="small"
      >
        <div style={{ position: 'relative' }}>
          {/* 星期标签 */}
          <div style={{ position: 'absolute', left: -40, top: 0, height: '100%' }}>
            {weekDays.map((day, i) => (
              <div
                key={day}
                style={{
                  height: `${100 / 7}%`,
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: 11,
                  color: '#666',
                }}
              >
                {day}
              </div>
            ))}
          </div>

          {/* 小时标签 */}
          <div style={{ marginLeft: 45, marginBottom: 8 }}>
            {hours.map((h) => (
              <span
                key={h}
                style={{
                  display: 'inline-block',
                  width: `${100 / 24}%`,
                  textAlign: 'center',
                  fontSize: 10,
                  color: '#999',
                }}
              >
                {h}
              </span>
            ))}
          </div>

          {/* 热力图网格 */}
          <div
            style={{
              marginLeft: 45,
              display: 'grid',
              gridTemplateColumns: `repeat(24, 1fr)`,
              gridTemplateRows: `repeat(7, 1fr)`,
              gap: 1,
              background: '#fff',
              borderRadius: 4,
              overflow: 'hidden',
            }}
          >
            {grid.map((row, i) =>
              row.map((count, j) => (
                <Tooltip
                  key={`${i}-${j}`}
                  title={`${weekDays[i]} ${j}:00 - ${j + 1}:00: ${count} 次操作`}
                >
                  <div
                    style={{
                      backgroundColor: getColor(count, maxCount),
                      height: height / 7,
                      minHeight: 24,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 10,
                      color: count > maxCount * 0.5 ? '#fff' : '#666',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.1)';
                      e.currentTarget.style.zIndex = '10';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.zIndex = '1';
                    }}
                  >
                    {count > 0 ? count : ''}
                  </div>
                </Tooltip>
              ))
            )}
          </div>

          {/* 图例 */}
          <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8, marginLeft: 45 }}>
            <span style={{ fontSize: 12, color: '#999' }}>少</span>
            <div style={{ display: 'flex', gap: 2 }}>
              {['#f5f5f5', '#e6f7ff', '#bae7ff', '#91d5ff', '#69c0ff', '#1677ff'].map(
                (color) => (
                  <div
                    key={color}
                    style={{
                      width: 20,
                      height: 12,
                      backgroundColor: color,
                    }}
                  />
                )
              )}
            </div>
            <span style={{ fontSize: 12, color: '#999' }}>多</span>
          </div>
        </div>
      </Card>
    );
  }

  return <Card title={title}>暂无数据</Card>;
}

// 用户活动强度热力图
interface UserActivityHeatmapProps {
  data: Array<{
    user_id: string;
    username: string;
    activity_score: number;
    login_count: number;
    query_count: number;
  }>;
  title?: string;
  maxUsers?: number;
}

export function UserActivityHeatmap({
  data,
  title = '用户活动强度',
  maxUsers = 20,
}: UserActivityHeatmapProps) {
  const displayData = useMemo(() => {
    return data
      .sort((a, b) => b.activity_score - a.activity_score)
      .slice(0, maxUsers);
  }, [data, maxUsers]);

  const maxScore = useMemo(() => {
    return Math.max(...displayData.map((d) => d.activity_score), 1);
  }, [displayData]);

  return (
    <Card title={title} size="small">
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {displayData.map((user) => (
            <div key={user.user_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 12 }}>{user.username || user.user_id}</span>
                <span style={{ fontSize: 12, fontWeight: 'bold' }}>
                  {Math.round(user.activity_score)}
                </span>
              </div>
              <div
                style={{
                  height: 8,
                  backgroundColor: '#f0f0f0',
                  borderRadius: 4,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${(user.activity_score / maxScore) * 100}%`,
                    background: `linear-gradient(90deg, #1677ff, #52c41a)`,
                    borderRadius: 4,
                    transition: 'width 0.3s',
                  }}
                />
              </div>
            </div>
          ))}
        </Space>
      </div>
    </Card>
  );
}

export default BehaviorHeatmap;
