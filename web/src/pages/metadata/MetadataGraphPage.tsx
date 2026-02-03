/**
 * 元数据图谱页面
 * 展示元数据关系图、数据血缘图等可视化内容
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Tabs,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Alert,
  Tooltip,
  Descriptions,
  Spin,
  message,
  Breadcrumb,
  Statistic
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  TableOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
  WarningOutlined,
  ClusterOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { GraphVisualization } from '@/components/metadata/GraphVisualization';
import { metadataApi } from '@/services/metadata';

const { TabPane } = Tabs;
const { Search } = Input;
const { Option } = Select;

export const MetadataGraphPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedLayout, setSelectedLayout] = useState('dagre');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('all');

  // 获取完整元数据图谱
  const { data: graphResponse, isLoading: graphLoading, refetch: refetchGraph } = useQuery({
    queryKey: ['metadata-graph', nodeTypeFilter],
    queryFn: () => metadataApi.getMetadataGraph({ node_types: nodeTypeFilter }),
    refetchInterval: 60000,
  });
  const graphData = graphResponse?.data;

  // 获取图谱统计
  const { data: statsResponse } = useQuery({
    queryKey: ['metadata-graph-stats'],
    queryFn: () => metadataApi.getGraphStatistics(),
  });
  const statsData = statsResponse?.data;

  // 获取表的血缘图谱
  const { data: lineageResponse, isLoading: lineageLoading } = useQuery({
    queryKey: ['metadata-lineage', selectedTable],
    queryFn: () => metadataApi.getTableLineageGraph(selectedTable),
    enabled: !!selectedTable && activeTab === 'lineage',
  });
  const lineageData = lineageResponse?.data;

  // 获取列关系图
  const { data: columnResponse, isLoading: columnLoading } = useQuery({
    queryKey: ['metadata-column-relation', selectedTable],
    queryFn: () => metadataApi.getColumnRelationGraph(selectedTable),
    enabled: !!selectedTable && activeTab === 'columns',
  });
  const columnRelationData = columnResponse?.data;

  // 搜索处理
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      return;
    }

    try {
      const response = await metadataApi.searchMetadataNodes({ keyword: searchQuery });
      setSearchResults(response.data?.nodes || []);
    } catch (error) {
      message.error('搜索失败');
    }
  };

  // 处理节点点击
  const handleNodeClick = (node: { type: string; table_name?: string }) => {
    if (node.type === 'table') {
      setSelectedTable(node.table_name);
      setActiveTab('lineage');
    }
  };

  // 获取节点类型颜色
  const getNodeTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      database: 'red',
      table: 'blue',
      column: 'green',
      lineage: 'purple',
    };
    return colors[type] || 'default';
  };

  // 获取关系类型颜色
  const getRelationTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      hierarchy: '#d9d9d9',
      lineage: '#999',
      relation: '#1890ff',
    };
    return colors[type] || '#d9d9d9';
  };

  return (
    <div className="metadata-graph-page">
      <Card
        title={
          <Space>
            <NodeIndexOutlined />
            <span>元数据图谱</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetchGraph()}
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        可视化展示数据血缘关系和元数据依赖
      </Card>

      <div className="page-content">
        {/* 搜索栏 */}
        <Card style={{ marginBottom: 16 }}>
          <Space>
            <Search
              placeholder="搜索数据库、表、列..."
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              style={{ width: 400 }}
              onSearch={handleSearch}
              onChange={(e) => setSearchQuery(e.target.value)}
              value={searchQuery}
            />
            <Select
              style={{ width: 120 }}
              placeholder="筛选类型"
              value={nodeTypeFilter}
              onChange={setNodeTypeFilter}
            >
              <Option value="all">全部类型</Option>
              <Option value="database">数据库</Option>
              <Option value="table">表</Option>
              <Option value="column">列</Option>
            </Select>
          </Space>

          {/* 搜索结果 */}
          {searchResults.length > 0 && (
            <>
              <Alert
                message={`找到 ${searchResults.length} 个匹配的节点`}
                type="info"
                showIcon
                closable
                onClose={() => setSearchResults([])}
                style={{ marginTop: 12 }}
              />

              {/* 搜索结果列表 */}
              <Space wrap style={{ marginTop: 12 }}>
                {searchResults.slice(0, 10).map((node) => (
                  <Tag
                    key={node.id}
                    color={getNodeTypeColor(node.type)}
                    style={{ cursor: 'pointer' }}
                    onClick={() => {
                      if (node.type === 'table') {
                        setSelectedTable(node.table_name || node.label);
                        setActiveTab('lineage');
                      }
                    }}
                  >
                    {node.label}
                    <span style={{ marginLeft: 4, opacity: 0.7 }}>
                      ({getTypeLabel(node.type)})
                    </span>
                  </Tag>
                ))}
                {searchResults.length > 10 && (
                  <Tag>+{searchResults.length - 10} 更多</Tag>
                )}
              </Space>
            </>
          )}
        </Card>

        {/* 图例 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col>
              <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
                <Space>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      backgroundColor: '#ff4d4f',
                      borderRadius: 2,
                      display: 'inline-block'
                    }}
                  />
                  <span>数据库</span>
                </Space>
                <Space>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      backgroundColor: '#1890ff',
                      borderRadius: 2,
                      display: 'inline-block'
                    }}
                  />
                  <span>表</span>
                </Space>
                <Space>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      backgroundColor: '#52c41a',
                      borderRadius: 2,
                      display: 'inline-block'
                    }}
                  />
                  <span>列</span>
                </Space>
                <Space>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      backgroundColor: '#722ed1',
                      borderRadius: 2,
                      display: 'inline-block'
                    }}
                  />
                  <span>血缘节点</span>
                </Space>
              </Space>
            </Col>
            <Col>
              <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
                <Space>
                  <span
                    style={{
                      width: 30,
                      height: 2,
                      backgroundColor: '#d9d9d9',
                      display: 'inline-block'
                    }}
                  />
                  <span>层级关系</span>
                </Space>
                <Space>
                  <span
                    style={{
                      width: 30,
                      height: 2,
                      backgroundColor: '#999',
                      borderStyle: 'dashed',
                      display: 'inline-block'
                    }}
                  />
                  <span>血缘关系</span>
                </Space>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 统计信息 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="数据库"
                value={statsData?.databases || 0}
                prefix={<ClusterOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="表"
                value={statsData?.tables || 0}
                prefix={<TableOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="列"
                value={statsData?.columns || 0}
                suffix="个"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="关系"
                value={graphData?.statistics?.total_edges || 0}
                suffix="条"
              />
            </Card>
          </Col>
        </Row>

        {/* 主内容区域 */}
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab="全量图谱" key="overview">
              <GraphVisualization
                nodes={graphData?.nodes || []}
                edges={graphData?.edges || []}
                loading={graphLoading}
                onNodeClick={handleNodeClick}
                height={600}
              />
            </TabPane>

            <TabPane tab="数据血缘" key="lineage">
              <Space style={{ marginBottom: 16 }}>
                <span>选择表:</span>
                <Select
                  style={{ width: 300 }}
                  placeholder="选择要查看血缘的表"
                  value={selectedTable}
                  onChange={setSelectedTable}
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.label || '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={graphData?.nodes
                    ?.filter((n: { type?: string }) => n.type === 'table')
                    .map((n: { type?: string; table_name?: string; label?: string; database_name?: string }) => ({
                      value: n.table_name,
                      label: n.label,
                      database: n.database_name,
                    })) || []
                  }
                />
              </Space>

              {selectedTable && lineageData && (
                <>
                  {lineageData.error && (
                    <Alert
                      message={lineageData.error}
                      type="warning"
                      showIcon
                      closable
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  {!lineageData.error && lineageData.center_table && (
                    <Alert
                      message={
                        <>
                          <span>表: {lineageData.center_table}</span>
                          <span style={{ marginLeft: 16 }}>
                            上游依赖: {lineageData.statistics?.upstream_count || 0}
                          </span>
                          <span style={{ marginLeft: 16 }}>
                            下游依赖: {lineageData.statistics?.downstream_count || 0}
                          </span>
                        </>
                      }
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  <GraphVisualization
                    nodes={lineageData.nodes || []}
                    edges={lineageData.edges || []}
                    loading={lineageLoading}
                    centerNode={lineageData.nodes?.find((n: { is_center?: boolean }) => n.is_center)}
                    height={600}
                  />
                </>
              )}

              {!selectedTable && (
                <div style={{
                  textAlign: 'center',
                  padding: 60,
                  color: '#999'
                }}>
                  <NodeIndexOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <div>请选择一个表查看其数据血缘</div>
                </div>
              )}
            </TabPane>

            <TabPane tab="列关系" key="columns">
              <Space style={{ marginBottom: 16 }}>
                <span>选择表:</span>
                <Select
                  style={{ width: 300 }}
                  placeholder="选择要查看列关系的表"
                  value={selectedTable}
                  onChange={setSelectedTable}
                  showSearch
                  options={graphData?.nodes
                    ?.filter((n: { type?: string }) => n.type === 'table')
                    .map((n: { type?: string; table_name?: string; label?: string; database_name?: string }) => ({
                      value: n.table_name,
                      label: n.label,
                      database: n.database_name,
                    })) || []
                  }
                />
              </Space>

              {selectedTable && columnRelationData && (
                <>
                  <Alert
                    message={`表 ${selectedTable} 的列关系图`}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <GraphVisualization
                    nodes={columnRelationData.nodes || []}
                    edges={columnRelationData.edges || []}
                    loading={columnLoading}
                    height={500}
                  />
                </>
              )}

              {!selectedTable && (
                <div style={{
                  textAlign: 'center',
                  padding: 60,
                  color: '#999'
                }}>
                  <TableOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <div>请选择一个表查看其列关系</div>
                </div>
              )}
            </TabPane>

            <TabPane tab="影响分析" key="impact">
              <Alert
                message="影响分析"
                description="选择一个节点，查看其修改后对下游的影响范围"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Alert
                message="功能说明"
                description={
                  <ul>
                    <li>分析表或列的修改对下游的影响范围</li>
                    <li>识别潜在的风险点</li>
                    <li>生成影响报告</li>
                  </ul>
                }
                type="info"
              />
            </TabPane>
          </Tabs>
        </Card>
      </div>
    </div>
  );
};

export default MetadataGraphPage;

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    database: '数据库',
    table: '表',
    column: '列',
    lineage: '血缘',
  };
  return labels[type] || type;
}
