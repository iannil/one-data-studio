/**
 * 元数据版本差异对比组件
 * 支持元数据快照管理、版本对比、SQL 生成
 */

import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Space,
  Typography,
  message,
  Popconfirm,
  Row,
  Col,
  Steps,
  Timeline,
  Alert,
  Tooltip,
  Divider,
  Descriptions,
  Empty,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  SwapOutlined,
  CodeOutlined,
  HistoryOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  FileTextOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMetadataSnapshots,
  createMetadataSnapshot,
  deleteMetadataSnapshot,
  compareMetadataSnapshots,
  getMigrationSQL,
  getMetadataVersionHistory,
  type MetadataSnapshot,
  type MetadataComparisonResult,
  type TableDiff,
  type ColumnDiff,
} from '@/services/data';
import './MetadataVersionDiff.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Step } = Steps;

interface MetadataVersionDiffProps {
  className?: string;
  database?: string;
}

/**
 * 差异标记组件
 */
const DiffMarker: React.FC<{ type: 'added' | 'removed' | 'modified' }> = ({ type }) => {
  if (type === 'added') {
    return <Tag color="green" icon={<ArrowDownOutlined />}>新增</Tag>;
  }
  if (type === 'removed') {
    return <Tag color="red" icon={<ArrowUpOutlined />}>删除</Tag>;
  }
  return <Tag color="blue" icon={<MinusOutlined />}>修改</Tag>;
};

/**
 * 表差异详情组件
 */
const TableDiffDetail: React.FC<{
  tableDiff: TableDiff;
}> = ({ tableDiff }) => {
  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case 'added':
        return <ArrowDownOutlined style={{ color: '#52c41a' }} />;
      case 'removed':
        return <ArrowUpOutlined style={{ color: '#ff4d4f' }} />;
      case 'modified':
        return <MinusOutlined style={{ color: '#1677ff' }} />;
      default:
        return null;
    }
  };

  return (
    <Card size="small" className="table-diff-card" style={{ marginBottom: 12 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <FileTextOutlined />
          <Text strong>{tableDiff.table_name}</Text>
          <Text type="secondary">({tableDiff.summary})</Text>
        </Space>

        {/* 新增列 */}
        {tableDiff.added_columns.length > 0 && (
          <div className="diff-section added">
            <Text type="secondary">新增列: </Text>
            <Space wrap>
              {tableDiff.added_columns.map(col => (
                <Tag key={col} color="green">{col}</Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 删除列 */}
        {tableDiff.removed_columns.length > 0 && (
          <div className="diff-section removed">
            <Text type="secondary">删除列: </Text>
            <Space wrap>
              {tableDiff.removed_columns.map(col => (
                <Tag key={col} color="red">{col}</Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 修改的列 */}
        {tableDiff.modified_columns.length > 0 && (
          <div className="diff-section modified">
            <Text type="secondary">修改的列:</Text>
            <div className="modified-columns">
              {tableDiff.modified_columns.map(colDiff => (
                <div key={colDiff.column_name} className="column-change-item">
                  <div className="column-name">
                    <Tag color="blue">{colDiff.column_name}</Tag>
                  </div>
                  <div className="column-changes">
                    {colDiff.changes.map((change, idx) => (
                      <div key={idx} className="field-change">
                        {getChangeIcon(change.change_type)}
                        <Text type="secondary">{change.field_name}: </Text>
                        <Text delete={change.change_type === 'removed'}>
                          {change.old_value || '(空)'}
                        </Text>
                        <ArrowDownOutlined style={{ margin: '0 8px', fontSize: 12 }} />
                        <Text type={change.change_type === 'added' ? 'success' : 'secondary'}>
                          {change.new_value || '(空)'}
                        </Text>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 未变化列 */}
        {tableDiff.unchanged_columns.length > 0 && (
          <div className="diff-section unchanged">
            <Text type="secondary">未变化: </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {tableDiff.unchanged_columns.join(', ')}
            </Text>
          </div>
        )}
      </Space>
    </Card>
  );
};

/**
 * 对比结果组件
 */
const ComparisonResult: React.FC<{
  fromSnapshot: MetadataSnapshot;
  toSnapshot: MetadataSnapshot;
  comparisonResult: MetadataComparisonResult;
}> = ({ fromSnapshot, toSnapshot, comparisonResult }) => {
  const [sqlModalVisible, setSqlModalVisible] = useState(false);
  const [sqlStatements, setSqlStatements] = useState<Record<string, string[]>>({});

  const { data: sqlData, isLoading: sqlLoading } = useQuery({
    queryKey: ['metadata', 'sql', fromSnapshot.snapshot_id, toSnapshot.snapshot_id],
    queryFn: () => getMigrationSQL(fromSnapshot.snapshot_id, toSnapshot.snapshot_id),
    select: (data) => data.data,
    enabled: sqlModalVisible,
  });

  const handleShowSql = () => {
    setSqlModalVisible(true);
    if (sqlData) {
      setSqlStatements(sqlData.sql_statements);
    }
  };

  const { added_tables, removed_tables, modified_tables, table_diffs } = comparisonResult;

  return (
    <div className="comparison-result">
      {/* 概览 */}
      <Card title="对比概览" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <Statistic
              title="新增表"
              value={added_tables.length}
              valueStyle={{ color: '#52c41a' }}
              prefix={<ArrowDownOutlined />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="删除表"
              value={removed_tables.length}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ArrowUpOutlined />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="修改表"
              value={modified_tables.length}
              valueStyle={{ color: '#1677ff' }}
              prefix={<MinusOutlined />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Button
              type="primary"
              icon={<CodeOutlined />}
              onClick={handleShowSql}
            >
              查看 SQL
            </Button>
          </Col>
        </Row>
        <Divider />
        <Text type="secondary">{comparisonResult.summary}</Text>
      </Card>

      {/* 表级差异 */}
      <Card title="表级差异" className="table-diffs-card">
        {added_tables.length > 0 && (
          <div className="diff-section added" style={{ marginBottom: 16 }}>
            <Title level={5}>新增表</Title>
            <Space wrap>
              {added_tables.map(tableName => (
                <Tag key={tableName} color="green" style={{ fontSize: 14, padding: '4px 12px' }}>
                  {tableName}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {removed_tables.length > 0 && (
          <div className="diff-section removed" style={{ marginBottom: 16 }}>
            <Title level={5}>删除表</Title>
            <Space wrap>
              {removed_tables.map(tableName => (
                <Tag key={tableName} color="red" style={{ fontSize: 14, padding: '4px 12px' }}>
                  {tableName}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {modified_tables.length > 0 && (
          <div>
            <Title level={5}>修改表</Title>
            {modified_tables.map(tableName => (
              <TableDiffDetail
                key={tableName}
                tableDiff={table_diffs[tableName]}
              />
            ))}
          </div>
        )}

        {added_tables.length === 0 && removed_tables.length === 0 && modified_tables.length === 0 && (
          <Empty description="两个版本之间没有差异" />
        )}
      </Card>

      {/* SQL 预览模态框 */}
      <Modal
        title="迁移 SQL"
        open={sqlModalVisible}
        onCancel={() => setSqlModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setSqlModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="copy"
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => {
              const allSql = Object.values(sqlStatements).flat().join('\n');
              navigator.clipboard.writeText(allSql);
              message.success('SQL 已复制到剪贴板');
            }}
          >
            复制全部 SQL
          </Button>,
        ]}
        width={800}
      >
        {sqlLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : (
          <div className="sql-preview">
            {Object.entries(sqlStatements).map(([table, statements]) => (
              <div key={table} style={{ marginBottom: 16 }}>
                <Text strong>{table}</Text>
                <pre className="sql-block">
                  <code>{statements.join('\n')}</code>
                </pre>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

/**
 * 创建快照表单
 */
const CreateSnapshotForm: React.FC<{
  visible: boolean;
  database?: string;
  onCancel: () => void;
  onSuccess: () => void;
}> = ({ visible, database, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const { data: databasesData } = useQuery({
    queryKey: ['metadata', 'databases'],
    queryFn: async () => {
      const res = await fetch('/api/v1/metadata/databases');
      return res.json();
    },
    select: (data) => data?.data?.databases || [],
  });

  const createMutation = useMutation({
    mutationFn: (values: { version: string; description?: string; database?: string }) =>
      createMetadataSnapshot({
        version: values.version,
        description: values.description,
        database: values.database || database,
        created_by: 'admin',
      }),
    onSuccess: () => {
      message.success('快照创建成功');
      form.resetFields();
      onSuccess();
    },
    onError: (error: Error) => {
      message.error(`创建失败: ${error.message}`);
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await createMutation.mutateAsync(values);
    } catch (error) {
      // Form validation failed
    }
  };

  return (
    <Modal
      title="创建元数据快照"
      open={visible}
      onCancel={() => {
        form.resetFields();
        onCancel();
      }}
      onOk={handleSubmit}
      confirmLoading={createMutation.isPending}
      okText="创建"
      cancelText="取消"
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ database, version: '', description: '' }}
      >
        <Form.Item
          label="版本号"
          name="version"
          rules={[
            { required: true, message: '请输入版本号' },
            { pattern: /^[a-zA-Z0-9._-]+$/, message: '版本号只能包含字母、数字、点、下划线和连字符' },
          ]}
        >
          <Input placeholder="例如: v1.0.0 或 2024-02-08-initial" />
        </Form.Item>

        <Form.Item
          label="数据库"
          name="database"
          rules={[{ required: !database, message: '请选择数据库' }]}
          extra={database ? `已指定数据库: ${database}` : '留空则快照所有数据库'}
        >
          <Select
            placeholder="选择数据库（可选）"
            allowClear
            options={databasesData?.map((db: { name: string }) => ({
              label: db.name,
              value: db.name,
            }))}
          />
        </Form.Item>

        <Form.Item
          label="描述"
          name="description"
          rules={[{ max: 500, message: '描述不能超过500字符' }]}
        >
          <TextArea
            rows={3}
            placeholder="描述此版本的变更内容，例如：新增用户表、修改订单表结构等"
            maxLength={500}
            showCount
          />
        </Form.Item>

        <Alert
          message="快照说明"
          description="快照将保存当前数据库的表结构信息，用于后续版本对比和迁移 SQL 生成。"
          type="info"
          showIcon
        />
      </Form>
    </Modal>
  );
};

/**
 * 快照列表标签页
 */
const SnapshotsTab: React.FC<{ database?: string }> = ({ database }) => {
  const queryClient = useQueryClient();
  const [compareModalVisible, setCompareModalVisible] = useState(false);
  const [selectedSnapshots, setSelectedSnapshots] = useState<string[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);

  const { data: snapshotsData, isLoading } = useQuery({
    queryKey: ['metadata', 'snapshots', database],
    queryFn: () => getMetadataSnapshots({ database }),
    select: (data) => data.data,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMetadataSnapshot,
    onSuccess: () => {
      message.success('快照删除成功');
      queryClient.invalidateQueries({ queryKey: ['metadata', 'snapshots'] });
    },
  });

  const handleCreateSuccess = () => {
    setCreateModalVisible(false);
    queryClient.invalidateQueries({ queryKey: ['metadata', 'snapshots'] });
    queryClient.invalidateQueries({ queryKey: ['metadata', 'history'] });
  };

  const handleCompare = () => {
    if (selectedSnapshots.length === 2) {
      setCompareModalVisible(true);
    } else {
      message.warning('请选择两个快照进行对比');
    }
  };

  const columns = [
    {
      title: '选择',
      dataIndex: 'snapshot_id',
      key: 'select',
      width: 60,
      render: (id: string) => (
        <input
          type="checkbox"
          checked={selectedSnapshots.includes(id)}
          disabled={!selectedSnapshots.includes(id) && selectedSnapshots.length >= 2}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedSnapshots([...selectedSnapshots, id]);
            } else {
              setSelectedSnapshots(selectedSnapshots.filter(s => s !== id));
            }
          }}
        />
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag color="blue">{version}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '表数量',
      dataIndex: 'snapshot_id',
      key: 'table_count',
      render: (id: string, record: MetadataSnapshot) => Object.keys(record.tables || {}).length,
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
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: MetadataSnapshot) => (
        <Space size="small">
          <Popconfirm
            title="确定删除此快照？"
            onConfirm={() => deleteMutation.mutate(record.snapshot_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title="元数据快照"
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              创建快照
            </Button>
            <Button
              type="primary"
              icon={<SwapOutlined />}
              disabled={selectedSnapshots.length !== 2}
              onClick={handleCompare}
            >
              对比选中快照
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={snapshotsData?.snapshots || []}
          rowKey="snapshot_id"
          loading={isLoading}
          pagination={false}
          rowSelection={undefined}
        />
      </Card>

      <CreateSnapshotForm
        visible={createModalVisible}
        database={database}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={handleCreateSuccess}
      />

      <ComparisonModal
        visible={compareModalVisible}
        fromId={selectedSnapshots[0]}
        toId={selectedSnapshots[1]}
        snapshots={snapshotsData?.snapshots || []}
        onClose={() => {
          setCompareModalVisible(false);
          setSelectedSnapshots([]);
        }}
      />
    </>
  );
};

/**
 * 对比模态框
 */
const ComparisonModal: React.FC<{
  visible: boolean;
  fromId: string;
  toId: string;
  snapshots: MetadataSnapshot[];
  onClose: () => void;
}> = ({ visible, fromId, toId, snapshots, onClose }) => {
  const { data: comparisonResult, isLoading } = useQuery({
    queryKey: ['metadata', 'compare', fromId, toId],
    queryFn: () => compareMetadataSnapshots(fromId, toId),
    select: (data: unknown) => (data as { data?: { data?: MetadataComparisonResult } })?.data?.data || ({} as MetadataComparisonResult),
    enabled: visible && !!fromId && !!toId,
  });

  const fromSnapshot = snapshots.find(s => s.snapshot_id === fromId);
  const toSnapshot = snapshots.find(s => s.snapshot_id === toId);

  return (
    <Modal
      title="版本对比结果"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={900}
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
      ) : comparisonResult && fromSnapshot && toSnapshot ? (
        <ComparisonResult
          fromSnapshot={fromSnapshot}
          toSnapshot={toSnapshot}
          comparisonResult={comparisonResult}
        />
      ) : null}
    </Modal>
  );
};

/**
 * 版本历史标签页
 */
const HistoryTab: React.FC<{ database?: string }> = ({ database }) => {
  const { data: historyData, isLoading } = useQuery({
    queryKey: ['metadata', 'history', database],
    queryFn: () => getMetadataVersionHistory({ database }),
    select: (data) => data.data,
  });

  return (
    <Card title="版本历史">
      <Timeline mode="left">
        {historyData?.history.map((item, idx) => (
          <Timeline.Item
            key={item.snapshot_id}
            dot={idx === 0 ? <CheckCircleOutlined style={{ fontSize: 16 }} /> : undefined}
            color={idx === 0 ? 'green' : 'gray'}
          >
            <Card size="small" className="history-timeline-item">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Tag color="blue">{item.version}</Tag>
                  <Text strong>{item.description || '无描述'}</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {item.table_count} 个表 | {item.created_by} | {new Date(item.created_at).toLocaleString('zh-CN')}
                </Text>
              </Space>
            </Card>
          </Timeline.Item>
        ))}
      </Timeline>
      {(!historyData || historyData.history.length === 0) && (
        <Empty description="暂无版本历史" />
      )}
    </Card>
  );
};

/**
 * 主元数据版本对比组件
 */
const MetadataVersionDiff: React.FC<MetadataVersionDiffProps> = ({ className, database }) => {
  return (
    <div className={`metadata-version-diff ${className || ''}`}>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>元数据版本管理</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="snapshots"
          items={[
            {
              key: 'snapshots',
              label: '快照管理',
              children: <SnapshotsTab database={database} />,
            },
            {
              key: 'history',
              label: '版本历史',
              children: <HistoryTab database={database} />,
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default MetadataVersionDiff;
