import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  DatePicker,
  Select,
  Button,
  Drawer,
  Descriptions,
  Statistic,
  Row,
  Col,
  Alert,
  Input,
  Modal,
  message,
} from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import admin from '@/services/admin';
import type { AuditLog, AuditActionType, AuditResourceType } from '@/services/admin';

const { RangePicker } = DatePicker;
const { Option } = Select;

function AuditPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [actionFilter, setActionFilter] = useState<string>('');
  const [resourceFilter, setResourceFilter] = useState<string>('');
  const [userFilter, setUserFilter] = useState<string>('');
  const [successFilter, setSuccessFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

  // 获取审计日志列表
  const { data: logsData, isLoading: isLoadingLogs, refetch } = useQuery({
    queryKey: ['auditLogs', page, pageSize, actionFilter, resourceFilter, userFilter, successFilter, dateRange],
    queryFn: () =>
      admin.getAuditLogs({
        page,
        page_size: pageSize,
        action: actionFilter as AuditActionType || undefined,
        resource_type: resourceFilter as AuditResourceType || undefined,
        user_id: userFilter || undefined,
        success: successFilter === 'true' ? true : successFilter === 'false' ? false : undefined,
        start_time: dateRange?.[0]?.format('YYYY-MM-DD HH:mm:ss'),
        end_time: dateRange?.[1]?.format('YYYY-MM-DD HH:mm:ss'),
      }),
  });

  // 获取统计数据
  const { data: statsData } = useQuery({
    queryKey: ['auditLogStatistics', dateRange],
    queryFn: () =>
      admin.getAuditLogStatistics({
        start_time: dateRange?.[0]?.format('YYYY-MM-DD'),
        end_time: dateRange?.[1]?.format('YYYY-MM-DD'),
      }),
  });

  // 获取活跃用户
  const { data: activeUsersData } = useQuery({
    queryKey: ['activeUsers', dateRange],
    queryFn: () =>
      admin.getActiveUsers({
        start_time: dateRange?.[0]?.format('YYYY-MM-DD'),
        end_time: dateRange?.[1]?.format('YYYY-MM-DD'),
      }),
  });

  const getActionColor = (action: AuditActionType) => {
    const colors: Record<string, string> = {
      login: 'green',
      logout: 'default',
      create: 'blue',
      update: 'cyan',
      delete: 'red',
      execute: 'purple',
      export: 'orange',
      import: 'orange',
      start: 'green',
      stop: 'red',
      deploy: 'blue',
      undeploy: 'red',
    };
    return colors[action] || 'default';
  };

  const getResourceColor = (resource: AuditResourceType) => {
    const colors: Record<string, string> = {
      user: 'blue',
      group: 'cyan',
      role: 'purple',
      datasource: 'green',
      dataset: 'green',
      workflow: 'orange',
      experiment: 'pink',
      model: 'red',
      service: 'blue',
      prompt: 'gold',
      knowledge: 'lime',
      metric: 'cyan',
      settings: 'purple',
      system: 'default',
    };
    return colors[resource] || 'default';
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 100,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (action: AuditActionType) => <Tag color={getActionColor(action)}>{action}</Tag>,
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 100,
      render: (type: AuditResourceType) => <Tag color={getResourceColor(type)}>{type}</Tag>,
    },
    {
      title: '资源名称',
      dataIndex: 'resource_name',
      key: 'resource_name',
      ellipsis: true,
      render: (name: string, record: AuditLog) => (
        <a
          onClick={() => {
            setSelectedLog(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name || record.resource_id || '-'}
        </a>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'user_ip',
      key: 'user_ip',
      width: 120,
      render: (ip: string) => ip || '-',
    },
    {
      title: '状态',
      dataIndex: 'success',
      key: 'success',
      width: 80,
      render: (success: boolean) => (
        <Tag
          color={success ? 'green' : 'red'}
          icon={success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        >
          {success ? '成功' : '失败'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 60,
      render: (_: unknown, record: AuditLog) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedLog(record);
            setIsDetailDrawerOpen(true);
          }}
        />
      ),
    },
  ];

  const actionOptions = [
    { value: 'login', label: '登录' },
    { value: 'logout', label: '登出' },
    { value: 'create', label: '创建' },
    { value: 'update', label: '更新' },
    { value: 'delete', label: '删除' },
    { value: 'execute', label: '执行' },
    { value: 'export', label: '导出' },
    { value: 'import', label: '导入' },
    { value: 'start', label: '启动' },
    { value: 'stop', label: '停止' },
    { value: 'deploy', label: '部署' },
    { value: 'undeploy', label: '卸载' },
  ];

  const resourceOptions = [
    { value: 'user', label: '用户' },
    { value: 'group', label: '用户组' },
    { value: 'role', label: '角色' },
    { value: 'datasource', label: '数据源' },
    { value: 'dataset', label: '数据集' },
    { value: 'workflow', label: '工作流' },
    { value: 'experiment', label: '实验' },
    { value: 'model', label: '模型' },
    { value: 'service', label: '服务' },
    { value: 'prompt', label: 'Prompt' },
    { value: 'knowledge', label: '知识库' },
    { value: 'metric', label: '指标' },
    { value: 'settings', label: '系统设置' },
  ];

  const stats = statsData?.data;

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总操作数"
              value={stats?.total_actions || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats?.success_rate || 0}
              suffix="%"
              precision={2}
              valueStyle={{ color: (stats?.success_rate || 0) >= 95 ? '#3f8600' : '#cf1322' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败操作"
              value={(stats?.total_actions ?? 0) - Math.round((stats?.success_rate ?? 0) / 100 * (stats?.total_actions ?? 0))}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={activeUsersData?.data?.users?.length || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="审计日志"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => setIsExportModalOpen(true)}>
              导出
            </Button>
            <Button icon={<SettingOutlined />}>
              保留策略
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <RangePicker
            showTime
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
            placeholder={['开始时间', '结束时间']}
          />
          <Select
            placeholder="操作类型"
            allowClear
            style={{ width: 120 }}
            value={actionFilter || undefined}
            onChange={setActionFilter}
          >
            {actionOptions.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="资源类型"
            allowClear
            style={{ width: 120 }}
            value={resourceFilter || undefined}
            onChange={setResourceFilter}
          >
            {resourceOptions.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="用户 ID"
            allowClear
            style={{ width: 150 }}
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 100 }}
            value={successFilter || undefined}
            onChange={setSuccessFilter}
          >
            <Option value="true">成功</Option>
            <Option value="false">失败</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={logsData?.data?.logs || []}
          rowKey="audit_id"
          loading={isLoadingLogs}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: logsData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 20);
            },
          }}
        />
      </Card>

      {/* 审计日志详情抽屉 */}
      <Drawer
        title="审计日志详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedLog(null);
        }}
        width={600}
      >
        {selectedLog && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="操作时间" span={2}>
                {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="用户">
                {selectedLog.username}
              </Descriptions.Item>
              <Descriptions.Item label="用户 ID">
                {selectedLog.user_id}
              </Descriptions.Item>
              <Descriptions.Item label="操作类型" span={2}>
                <Tag color={getActionColor(selectedLog.action)}>{selectedLog.action}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="资源类型">
                <Tag color={getResourceColor(selectedLog.resource_type)}>
                  {selectedLog.resource_type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="资源 ID">
                {selectedLog.resource_id || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="资源名称" span={2}>
                {selectedLog.resource_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="IP 地址">
                {selectedLog.user_ip || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="User Agent" span={2}>
                {selectedLog.user_agent || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态" span={2}>
                <Tag
                  color={selectedLog.success ? 'green' : 'red'}
                  icon={selectedLog.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                >
                  {selectedLog.success ? '成功' : '失败'}
                </Tag>
              </Descriptions.Item>
              {!selectedLog.success && selectedLog.error_message && (
                <Descriptions.Item label="错误信息" span={2}>
                  <Alert type="error" message={selectedLog.error_message} />
                </Descriptions.Item>
              )}
              {selectedLog.changes && (
                <Descriptions.Item label="变更内容" span={2}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
                    {JSON.stringify(selectedLog.changes, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Drawer>

      {/* 导出模态框 */}
      <Modal
        title="导出审计日志"
        open={isExportModalOpen}
        onCancel={() => setIsExportModalOpen(false)}
        onOk={async () => {
          if (!dateRange) {
            message.warning('请选择时间范围');
            return;
          }
          try {
            const res = await admin.exportAuditLogs({
              start_time: dateRange[0].format('YYYY-MM-DD HH:mm:ss'),
              end_time: dateRange[1].format('YYYY-MM-DD HH:mm:ss'),
              format: 'excel',
            });
            window.open(res.data.download_url, '_blank');
            message.success('导出成功');
            setIsExportModalOpen(false);
          } catch {
            message.error('导出失败');
          }
        }}
      >
        <Alert
          message="导出说明"
          description="请选择时间范围后点击确定，系统将生成导出文件并提供下载。"
          type="info"
          style={{ marginBottom: 16 }}
        />
        <RangePicker
          showTime
          value={dateRange}
          onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
          style={{ width: '100%' }}
          placeholder={['开始时间', '结束时间']}
        />
      </Modal>
    </div>
  );
}

export default AuditPage;
