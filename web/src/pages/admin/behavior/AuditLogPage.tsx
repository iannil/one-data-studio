/**
 * 行为审计日志页面
 * 展示用户行为审计记录
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  DatePicker,
  Input,
  Select,
  Button,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { behaviorApi } from '@/services/behavior';

const { Search } = Input;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface AuditLog {
  id: number;
  user_id: string;
  behavior_type: string;
  action?: string;
  target_type?: string;
  page_url?: string;
  occurred_at: string;
  ip_address?: string;
  device_type?: string;
}

export const AuditLogPage: React.FC = () => {
  const [filters, setFilters] = useState({
    user_id: '',
    behavior_type: undefined as string | undefined,
    start_date: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
    end_date: dayjs().format('YYYY-MM-DD'),
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
  });

  const { data: auditData, isLoading, refetch } = useQuery({
    queryKey: ['behavior-audit-log', filters, pagination],
    queryFn: () => behaviorApi.getAuditLog({
      user_id: filters.user_id || undefined,
      behavior_type: filters.behavior_type,
      start_date: filters.start_date,
      end_date: filters.end_date,
      page: pagination.current,
      page_size: pagination.pageSize,
    }),
    select: (data) => data.data.data,
  });

  const columns = [
    {
      title: '时间',
      dataIndex: 'occurred_at',
      key: 'occurred_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
    },
    {
      title: '行为类型',
      dataIndex: 'behavior_type',
      key: 'behavior_type',
      width: 120,
      render: (type: string) => {
        const typeConfig: Record<string, { color: string; text: string }> = {
          page_view: { color: 'blue', text: '页面浏览' },
          click: { color: 'cyan', text: '点击' },
          submit: { color: 'green', text: '提交' },
          form_submit: { color: 'lime', text: '表单提交' },
          login: { color: 'gold', text: '登录' },
          logout: { color: 'orange', text: '登出' },
          download: { color: 'purple', text: '下载' },
          export: { color: 'red', text: '导出' },
          data_query: { color: 'geekblue', text: '数据查询' },
          api_call: { color: 'default', text: 'API调用' },
        };
        const config = typeConfig[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      ellipsis: true,
      render: (action: string) => (
        <Tooltip title={action}>
          <span>{action || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '目标类型',
      dataIndex: 'target_type',
      key: 'target_type',
      width: 100,
      render: (type: string) => type || '-',
    },
    {
      title: '页面',
      dataIndex: 'page_url',
      key: 'page_url',
      ellipsis: true,
      render: (url: string) => (
        <Tooltip title={url}>
          <span>{url || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '设备',
      dataIndex: 'device_type',
      key: 'device_type',
      width: 80,
      render: (device: string) => {
        const deviceConfig: Record<string, string> = {
          pc: 'PC',
          mobile: '手机',
          tablet: '平板',
        };
        return deviceConfig[device] || device || '-';
      },
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: (ip: string) => ip || '-',
    },
  ];

  return (
    <div className="audit-log-page">
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>行为审计</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => {
                // 导出功能
              }}
            >
              导出
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
            >
              刷新
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        用户行为审计日志，支持全链路追溯
      </Card>

      <div className="page-content">
        <Card>
          <Space style={{ marginBottom: 16 }} wrap>
            <Search
              placeholder="用户ID"
              allowClear
              style={{ width: 200 }}
              onSearch={(value) => setFilters({ ...filters, user_id: value })}
              enterButton
            />
            <Select
              style={{ width: 150 }}
              placeholder="行为类型"
              allowClear
              value={filters.behavior_type}
              onChange={(value) => setFilters({ ...filters, behavior_type: value })}
            >
              <Option value="page_view">页面浏览</Option>
              <Option value="click">点击</Option>
              <Option value="login">登录</Option>
              <Option value="logout">登出</Option>
              <Option value="export">导出</Option>
              <Option value="data_query">数据查询</Option>
            </Select>
            <RangePicker
              value={[dayjs(filters.start_date), dayjs(filters.end_date)]}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setFilters({
                    ...filters,
                    start_date: dates[0].format('YYYY-MM-DD'),
                    end_date: dates[1].format('YYYY-MM-DD'),
                  });
                }
              }}
            />
          </Space>

          <Table
            columns={columns}
            dataSource={auditData?.behaviors || []}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: auditData?.total || 0,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => {
                setPagination({ current: page, pageSize: pageSize || 50 });
              },
            }}
            scroll={{ x: 1200 }}
          />
        </Card>
      </div>
    </div>
  );
};

export default AuditLogPage;
