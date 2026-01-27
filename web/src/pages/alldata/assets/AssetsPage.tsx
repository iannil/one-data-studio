import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Card,
  Tree,
  Input,
  Select,
  Drawer,
  Descriptions,
  Progress,
  Row,
  Col,
  Statistic,
  Tabs,
  Modal,
  Form,
  message,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  FolderOutlined,
  DatabaseOutlined,
  TableOutlined,
  FileOutlined,
  TagsOutlined,
  SafetyOutlined,
  HeatMapOutlined,
  ReloadOutlined,
  PlusOutlined,
  RobotOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { DataAsset, AssetValueLevel } from '@/services/alldata';
import { AssetAISearch } from '@/components/alldata/AssetAISearch';
import { AssetValuePanel } from '@/components/alldata/AssetValuePanel';

const { Option } = Select;

function AssetsPage() {
  const queryClient = useQueryClient();
  const [selectedAsset, setSelectedAsset] = useState<DataAsset | null>(null);
  const [isProfileDrawerOpen, setIsProfileDrawerOpen] = useState(false);
  const [isInventoryModalOpen, setIsInventoryModalOpen] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  const [inventoryForm] = Form.useForm();

  // Queries
  const { data: assetsData, isLoading: isLoadingAssets } = useQuery({
    queryKey: ['data-assets'],
    queryFn: () => alldata.getDataAssets(),
  });

  const { data: inventoriesData } = useQuery({
    queryKey: ['asset-inventories'],
    queryFn: () => alldata.getAssetInventories(),
    refetchInterval: 5000,
  });

  const { data: profileData, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['asset-profile', selectedAsset?.asset_id],
    queryFn: () => alldata.getDataAsset(selectedAsset!.asset_id),
    enabled: !!selectedAsset && isProfileDrawerOpen,
  });

  // Mutations
  const createInventoryMutation = useMutation({
    mutationFn: alldata.createAssetInventory,
    onSuccess: () => {
      message.success('资产盘点任务创建成功');
      setIsInventoryModalOpen(false);
      inventoryForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['asset-inventories'] });
    },
    onError: () => {
      message.error('资产盘点任务创建失败');
    },
  });

  const getSensitivityColor = (level: string) => {
    const colors: Record<string, string> = {
      public: 'green',
      internal: 'blue',
      confidential: 'orange',
      restricted: 'red',
    };
    return colors[level] || 'default';
  };

  const getSensitivityText = (level: string) => {
    const texts: Record<string, string> = {
      public: '公开',
      internal: '内部',
      confidential: '机密',
      restricted: '绝密',
    };
    return texts[level] || level;
  };

  const getIconByType = (type: string) => {
    switch (type) {
      case 'database':
        return <DatabaseOutlined />;
      case 'table':
        return <TableOutlined />;
      case 'column':
        return <FileOutlined />;
      default:
        return <FolderOutlined />;
    }
  };

  // 资产价值等级颜色和描述
  const VALUE_LEVEL_CONFIG: Record<AssetValueLevel, { color: string; label: string; description: string }> = {
    S: { color: '#722ed1', label: 'S级', description: '战略级资产' },
    A: { color: '#1890ff', label: 'A级', description: '核心级资产' },
    B: { color: '#52c41a', label: 'B级', description: '重要级资产' },
    C: { color: '#999', label: 'C级', description: '基础级资产' },
  };

  const getValueLevelTag = (level?: AssetValueLevel) => {
    if (!level) return '-';
    const config = VALUE_LEVEL_CONFIG[level];
    return (
      <Tooltip title={config.description}>
        <Tag color={config.color} style={{ fontWeight: 'bold' }}>
          {level}
        </Tag>
      </Tooltip>
    );
  };

  // Filter assets
  const filteredAssets = assetsData?.data?.assets?.filter((asset) => {
    const matchKeyword = !searchKeyword || asset.name.toLowerCase().includes(searchKeyword.toLowerCase());
    const matchType = !typeFilter || asset.type === typeFilter;
    return matchKeyword && matchType;
  }) || [];

  // Build tree data
  const buildTreeData = (assets: DataAsset[]): any[] => {
    const rootNodes = assets.filter((a) => !a.parent_id);
    return rootNodes.map((node) => buildNode(node, assets));
  };

  const buildNode = (node: DataAsset, allAssets: DataAsset[]): any => {
    const children = allAssets.filter((a) => a.parent_id === node.asset_id);
    return {
      title: node.name,
      key: node.asset_id,
      icon: getIconByType(node.type),
      children: children.length > 0 ? children.map((c) => buildNode(c, allAssets)) : undefined,
      data: node,
    };
  };

  const treeDataFormatted = assetsData?.data?.assets ? buildTreeData(assetsData.data.assets) : [];

  const assetColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DataAsset) => (
        <a onClick={() => { setSelectedAsset(record); setIsProfileDrawerOpen(true); }}>
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '所有者',
      dataIndex: 'owner',
      key: 'owner',
      render: (owner?: string) => owner || '-',
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (dept?: string) => dept || '-',
    },
    {
      title: '敏感级别',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => (
        <Tag color={getSensitivityColor(level)} icon={<SafetyOutlined />}>
          {getSensitivityText(level)}
        </Tag>
      ),
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      render: (score?: number) => {
        if (!score) return '-';
        return <Progress percent={score} size="small" status={score >= 80 ? 'success' : score >= 60 ? 'normal' : 'exception'} />;
      },
    },
    {
      title: '价值等级',
      dataIndex: 'value_level',
      key: 'value_level',
      width: 90,
      render: (level?: AssetValueLevel) => getValueLevelTag(level),
    },
    {
      title: '访问热度',
      dataIndex: 'access_heat',
      key: 'access_heat',
      render: (heat?: number) => {
        if (!heat) return '-';
        const color = heat > 70 ? 'red' : heat > 30 ? 'orange' : 'green';
        return <Tag color={color} icon={<HeatMapOutlined />}>{heat}</Tag>;
      },
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
    },
  ];

  const inventoryColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error',
        };
        const labels: Record<string, string> = {
          pending: '待执行',
          running: '执行中',
          completed: '已完成',
          failed: '失败',
        };
        return <Tag color={colors[status]}>{labels[status]}</Tag>;
      },
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: { total_assets: number; scanned_assets: number }) => {
        if (record.total_assets === 0) return '-';
        const percent = Math.round((record.scanned_assets / record.total_assets) * 100);
        return <Progress percent={percent} size="small" />;
      },
    },
    {
      title: '扫描进度',
      key: 'scan',
      render: (_: unknown, record: { total_assets: number; scanned_assets: number }) => {
        return `${record.scanned_assets}/${record.total_assets}`;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
  ];

  const handleSelectAsset = (_selectedKeys: React.Key[], info: any) => {
    if (info.node.data) {
      setSelectedAsset(info.node.data);
      setIsProfileDrawerOpen(true);
    }
  };

  const handleExpand = (newExpandedKeys: React.Key[]) => {
    setExpandedKeys(newExpandedKeys as string[]);
  };

  const handleCreateInventory = () => {
    inventoryForm.validateFields().then((values) => {
      createInventoryMutation.mutate({
        name: values.name,
        scope: values.scope || [],
      });
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16}>
        {/* 左侧资产树 */}
        <Col span={6}>
          <Card
            title="资产目录"
            size="small"
            extra={
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['asset-tree'] })}
              />
            }
          >
            <Input
              placeholder="搜索资产"
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              style={{ marginBottom: 8 }}
            />
            <Tree
              showIcon
              expandedKeys={expandedKeys}
              onExpand={handleExpand}
              onSelect={handleSelectAsset}
              treeData={treeDataFormatted}
              style={{ fontSize: 13 }}
            />
          </Card>
        </Col>

        {/* 右侧资产列表和盘点 */}
        <Col span={18}>
          <Tabs
            defaultActiveKey="assets"
            items={[
              {
                key: 'assets',
                label: '资产列表',
                children: (
                  <Card
                    title="数据资产"
                    extra={
                      <Space>
                        <Select
                          placeholder="类型筛选"
                          allowClear
                          style={{ width: 120 }}
                          onChange={setTypeFilter}
                          value={typeFilter || undefined}
                        >
                          <Option value="database">数据库</Option>
                          <Option value="table">表</Option>
                          <Option value="column">字段</Option>
                          <Option value="view">视图</Option>
                        </Select>
                        <Button
                          type="primary"
                          icon={<ReloadOutlined />}
                          onClick={() => queryClient.invalidateQueries({ queryKey: ['data-assets'] })}
                        >
                          刷新
                        </Button>
                      </Space>
                    }
                  >
                    <Table
                      columns={assetColumns}
                      dataSource={filteredAssets}
                      rowKey="asset_id"
                      loading={isLoadingAssets}
                      pagination={{
                        pageSize: 20,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 条`,
                      }}
                      size="small"
                    />
                  </Card>
                ),
              },
              {
                key: 'ai-search',
                label: (
                  <Space>
                    <RobotOutlined />
                    <span>AI 智能搜索</span>
                  </Space>
                ),
                children: (
                  <AssetAISearch
                    onResultSelect={(asset) => {
                      setSelectedAsset(asset);
                      setIsProfileDrawerOpen(true);
                    }}
                  />
                ),
              },
              {
                key: 'inventory',
                label: '资产盘点',
                children: (
                  <Card
                    title="资产盘点任务"
                    extra={
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsInventoryModalOpen(true)}>
                        创建盘点任务
                      </Button>
                    }
                  >
                    <Table
                      columns={inventoryColumns}
                      dataSource={inventoriesData?.data?.tasks || []}
                      rowKey="task_id"
                      pagination={false}
                      size="small"
                    />
                  </Card>
                ),
              },
              {
                key: 'value-assessment',
                label: (
                  <Space>
                    <TrophyOutlined />
                    <span>价值评估</span>
                  </Space>
                ),
                children: (
                  <AssetValuePanel
                    onAssetSelect={(assetId) => {
                      const asset = assetsData?.data?.assets?.find(a => a.asset_id === assetId);
                      if (asset) {
                        setSelectedAsset(asset);
                        setIsProfileDrawerOpen(true);
                      }
                    }}
                  />
                ),
              },
            ]}
          />
        </Col>
      </Row>

      {/* 资产画像抽屉 */}
      <Drawer
        title="资产画像"
        open={isProfileDrawerOpen}
        onClose={() => {
          setIsProfileDrawerOpen(false);
          setSelectedAsset(null);
        }}
        width={700}
      >
        {isLoadingProfile ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : profileData?.data ? (
          <div>
            <Descriptions title="基本信息" column={2} bordered size="small">
              <Descriptions.Item label="名称" span={2}>
                {profileData.data.basic_info.name}
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                {profileData.data.basic_info.type}
              </Descriptions.Item>
              <Descriptions.Item label="所有者">
                {profileData.data.basic_info.owner}
              </Descriptions.Item>
              <Descriptions.Item label="部门" span={2}>
                {profileData.data.basic_info.department}
              </Descriptions.Item>
              {selectedAsset?.sensitivity_level && (
                <Descriptions.Item label="敏感级别" span={2}>
                  <Tag color={getSensitivityColor(selectedAsset.sensitivity_level)} icon={<SafetyOutlined />}>
                    {getSensitivityText(selectedAsset.sensitivity_level)}
                  </Tag>
                </Descriptions.Item>
              )}
            </Descriptions>

            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={12}>
                <Card title="数据统计" size="small">
                  <Row gutter={8}>
                    <Col span={12}>
                      <Statistic
                        title="行数"
                        value={profileData.data.statistics.row_count}
                        formatter={(v) => v?.toLocaleString()}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="大小"
                        value={profileData.data.statistics.size_bytes / 1024 / 1024}
                        suffix="MB"
                        precision={2}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                  </Row>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="访问统计" size="small">
                  <Row gutter={8}>
                    <Col span={12}>
                      <Statistic
                        title="访问次数"
                        value={profileData.data.statistics.access_count}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="访问热度"
                        value={profileData.data.statistics.access_heat}
                        suffix="/100"
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                  </Row>
                </Card>
              </Col>
            </Row>

            <Card title="数据质量" size="small" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>完整性</div>
                    <Progress percent={profileData.data.quality.completeness} size="small" />
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>准确性</div>
                    <Progress percent={profileData.data.quality.accuracy} size="small" />
                  </div>
                </Col>
                <Col span={12}>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>一致性</div>
                    <Progress percent={profileData.data.quality.consistency} size="small" />
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>时效性</div>
                    <Progress percent={profileData.data.quality.timeliness} size="small" />
                  </div>
                </Col>
              </Row>
            </Card>

            <Card title="血缘关系" size="small" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="上游依赖"
                    value={profileData.data.lineage.upstream_count}
                    suffix="个"
                    valueStyle={{ fontSize: 14 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="下游影响"
                    value={profileData.data.lineage.downstream_count}
                    suffix="个"
                    valueStyle={{ fontSize: 14 }}
                  />
                </Col>
              </Row>
            </Card>

            {selectedAsset?.tags && (
              <Card title={<><TagsOutlined /> 标签</>} size="small" style={{ marginTop: 16 }}>
                <Space wrap>
                  {selectedAsset.tags.map((tag) => (
                    <Tag key={tag} color="blue">
                      {tag}
                    </Tag>
                  ))}
                </Space>
              </Card>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
        )}
      </Drawer>

      {/* 创建盘点任务模态框 */}
      <Modal
        title="创建资产盘点任务"
        open={isInventoryModalOpen}
        onOk={handleCreateInventory}
        onCancel={() => {
          setIsInventoryModalOpen(false);
          inventoryForm.resetFields();
        }}
        confirmLoading={createInventoryMutation.isPending}
      >
        <Form form={inventoryForm} layout="vertical">
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item label="盘点范围" name="scope">
            <Select mode="tags" placeholder="选择要盘点的数据库或表" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default AssetsPage;
