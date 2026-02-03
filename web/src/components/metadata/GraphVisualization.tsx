/**
 * 元数据图谱可视化组件
 * 使用 Cytoscape.js 渲染元数据关系图和数据血缘
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape, { Core, NodeSingular, ElementDefinition } from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { Button, Card, Col, Row, Select, Space, Tag, Tooltip, Statistic, Spin, Alert } from 'antd';
import {
  ReloadOutlined,
  DownloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  ControlOutlined,
  EyeOutlined,
  FilterOutlined
} from '@ant-design/icons';
import cytoscapeCoseBilkent from 'cytoscape-cose-bilkent';
// @ts-expect-error show method on cytoscape collection cytoscape-navigator doesn't have proper types
import cytoscapeNavigator from 'cytoscape-navigator';

import './GraphVisualization.css';

// 注册扩展
dagre(cytoscape, dagre);
cytoscape.use(cytoscapeCoseBilkent);

interface GraphNode {
  id: string;
  label: string;
  type: 'database' | 'table' | 'column' | 'lineage';
  database_name?: string;
  table_name?: string;
  column_name?: string;
  data_type?: string;
  description?: string;
  is_center?: boolean;
  properties?: Record<string, unknown>;
  relation?: string; // 用于搜索结果
  // Additional properties for impact analysis
  node_type?: string;
  name?: string;
  full_name?: string;
  node_id?: string;
  impact_level?: number | 'low' | 'medium' | 'high' | 'critical';
}

interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  type: string;
  direction?: 'upstream' | 'downstream';
  relation_type?: string;
  properties?: Record<string, unknown>;
}

interface MetadataGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading?: boolean;
  onNodeClick?: (node: GraphNode) => void;
  centerNode?: GraphNode;
  showControls?: boolean;
  height?: string | number;
}

interface GraphStatistics {
  total_nodes?: number;
  total_edges?: number;
  node_types?: Record<string, number>;
}

const LAYOUT_OPTIONS = [
  { value: 'dagre', label: '层次布局' },
  { value: 'cose-bilkent', label: '力导向布局' },
  { value: 'concentric', label: '同心圆布局' },
  { value: 'circle', label: '环形布局' },
  { value: 'grid', label: '网格布局' },
  { value: 'breadthfirst', label: '广度优先' },
];

const NODE_TYPE_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'database', label: '数据库' },
  { value: 'table', label: '表' },
  { value: 'column', label: '列' },
  { value: 'lineage', label: '血缘节点' },
];

const NODE_TYPE_COLORS: Record<string, string> = {
  database: '#ff4d4f',      // 红色
  table: '#1890ff',         // 蓝色
  column: '#52c41a',        // 绿色
  lineage: '#722ed1',       // 紫色
};

const NODE_TYPE_SHAPES: Record<string, string> = {
  database: 'round-rectangle',
  table: 'rectangle',
  column: 'ellipse',
  lineage: 'diamond',
};

export const GraphVisualization: React.FC<MetadataGraphProps> = ({
  nodes,
  edges,
  loading = false,
  onNodeClick,
  centerNode,
  showControls = true,
  height = 600,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const navigatorRef = useRef<any>(null);
  const [selectedLayout, setSelectedLayout] = useState('dagre');
  const [nodeTypeFilter, setNodeTypeFilter] = useState('all');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStatistics>({});

  // 初始化图谱
  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    // 转换数据为 Cytoscape 格式
    const elements: ElementDefinition[] = [
      ...nodes.map(node => ({
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          ...node,
        },
        classes: node.type,
      })),
      ...edges.map(edge => ({
        data: {
          id: `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          ...edge,
        },
        classes: edge.type,
      })),
    ];

    // 创建 Cytoscape 实例
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      // @ts-expect-error show method on cytoscape collection - cytoscape style type incompatibility
      style: getGraphStyle(),
      layout: getLayoutConfig(selectedLayout),
      minZoom: 0.1,
      maxZoom: 3,
      wheelSensitivity: 0.2,
    });

    cyRef.current = cy;

    // 添加导航器
    if (showControls) {
      try {
        // @ts-expect-error show method on cytoscape collection - navigator extension
        cy.navigator({
          zoom: 4,
        });
      } catch (e) {
         
        console.warn('Navigator extension not available:', e);
      }
    }

    // 节点点击事件
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = node.data() as GraphNode;

      setSelectedNode(nodeData);
      onNodeClick?.(nodeData);

      // 高亮选中节点及其邻居
      highlightNeighbors(cy, node);
    });

    // 点击空白处取消选中
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        resetHighlight(cy);
      }
    });

    // 双击节点居中
    cy.on('dbltap', 'node', (evt) => {
      const node = evt.target;
      cy.animate({
        center: {
          eles: node,
        },
        zoom: 1.5,
      }, {
        duration: 500,
      });
    });

    // 统计信息
    updateStatistics(cy);

    // 如果有中心节点，高亮显示
    if (centerNode) {
      highlightPath(cy, centerNode.id);
    }

    return () => {
      cy.destroy();
    };
  }, [nodes, edges, centerNode]);

  // 更新布局
  useEffect(() => {
    if (cyRef.current) {
      cyRef.current.layout(getLayoutConfig(selectedLayout)).run();
    }
  }, [selectedLayout]);

  // 节点类型过滤
  useEffect(() => {
    if (cyRef.current) {
      const cy = cyRef.current;

      if (nodeTypeFilter === 'all') {
        // @ts-expect-error show method on cytoscape collection - show/hide extension methods
        cy.nodes().show();
        // @ts-expect-error show method on cytoscape collection
        cy.edges().show();
      } else {
        cy.nodes().forEach((node) => {
          if (node.data('type') === nodeTypeFilter) {
            // @ts-expect-error show method on cytoscape collection
            node.show();
          } else {
            // @ts-expect-error show method on cytoscape collection
            node.hide();
          }
        });

        // 隐藏没有端点的边
        cy.edges().forEach((edge) => {
          const source = edge.source();
          const target = edge.target();

          if (source.visible() && target.visible()) {
            // @ts-expect-error show method on cytoscape collection
            edge.show();
          } else {
            // @ts-expect-error show method on cytoscape collection
            edge.hide();
          }
        });
      }
    }
  }, [nodeTypeFilter]);

  const updateStatistics = (cy: Core) => {
    const visibleNodes = cy.nodes(':visible').length;
    const visibleEdges = cy.edges(':visible').length;

    const typeCount: Record<string, number> = {};
    cy.nodes(':visible').forEach((node) => {
      const type = node.data('type');
      typeCount[type] = (typeCount[type] || 0) + 1;
    });

    setGraphStats({
      total_nodes: visibleNodes,
      total_edges: visibleEdges,
      node_types: typeCount,
    });
  };

  const highlightNeighbors = (cy: Core, node: NodeSingular) => {
    const neighborhood = node.closedNeighborhood();

    cy.elements().not(neighborhood).addClass('faded');
    // @ts-expect-error show method on cytoscape collection - connectivity extension method
    neighborhood.connectivity().addClass('highlighted');
  };

  const resetHighlight = (cy: Core) => {
    cy.elements().removeClass('faded highlighted');
  };

  const highlightPath = (cy: Core, centerNodeId: string) => {
    // 高亮从中心节点出发的所有路径
    const bfs = cy.elements().bfs({
      root: `#${centerNodeId}`,
      directed: false,
    });

    // @ts-expect-error - SearchFirstResult is not assignable to not() parameter
    cy.elements().not(bfs).addClass('faded');
    // @ts-expect-error - bfs.path() expects different parameters
    bfs.path(bfs, {
      directed: false,
    }).addClass('highlighted');
  };

  // 控制函数
  const handleZoomIn = () => {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  };

  const handleZoomOut = () => {
    cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
  };

  const handleFit = () => {
    cyRef.current?.fit(undefined, 50);
  };

  const handleCenter = () => {
    cyRef.current?.center();
  };

  const handleLayoutChange = (layout: string) => {
    setSelectedLayout(layout);
  };

  const handleExport = () => {
    if (cyRef.current) {
      const png = cyRef.current.png({ full: true, scale: 2 });
      const link = document.createElement('a');
      link.href = png;
      link.download = `metadata-graph-${Date.now()}.png`;
      link.click();
    }
  };

  return (
    <div className="metadata-graph-container">
      {showControls && (
        <Card size="small" className="graph-controls">
          <Space wrap>
            <Space>
              <span>布局:</span>
              <Select
                value={selectedLayout}
                onChange={handleLayoutChange}
                style={{ width: 120 }}
                size="small"
              >
                {LAYOUT_OPTIONS.map(opt => (
                  <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                ))}
              </Select>
            </Space>

            <Space>
              <span>类型:</span>
              <Select
                value={nodeTypeFilter}
                onChange={setNodeTypeFilter}
                style={{ width: 100 }}
                size="small"
              >
                {NODE_TYPE_FILTERS.map(opt => (
                  <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                ))}
              </Select>
            </Space>

            <Button size="small" icon={<ZoomInOutlined />} onClick={handleZoomIn} />
            <Button size="small" icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
            <Button size="small" icon={<ExpandOutlined />} onClick={handleFit}>适配</Button>
            <Button size="small" icon={<ControlOutlined />} onClick={handleCenter}>居中</Button>
            <Button size="small" icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
          </Space>
      </Card>
      )}

      <Row gutter={16}>
        <Col span={showControls ? 18 : 24}>
          <Spin spinning={loading}>
            <div
              ref={containerRef}
              style={{
                height: typeof height === 'number' ? `${height}px` : height,
                border: '1px solid #d9d9d9',
                borderRadius: '4px',
                background: '#fafafa',
              }}
            />
          </Spin>
        </Col>

        {showControls && (
          <Col span={6}>
            <Card size="small" title="统计信息" className="graph-stats">
              <Row gutter={8}>
                <Col span={12}>
                  <Statistic
                    title="节点"
                    value={graphStats.total_nodes || 0}
                    valueStyle={{ fontSize: 16 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="关系"
                    value={graphStats.total_edges || 0}
                    valueStyle={{ fontSize: 16 }}
                  />
                </Col>
              </Row>

              {graphStats.node_types && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ marginBottom: 8, fontSize: 12, fontWeight: 'bold' }}>
                    节点类型
                  </div>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {Object.entries(graphStats.node_types).map(([type, count]) => (
                      <Space key={type} style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Tag color={NODE_TYPE_COLORS[type]}>
                          {getTypeLabel(type)}
                        </Tag>
                        <span>{count}</span>
                      </Space>
                    ))}
                  </Space>
                </div>
              )}

              {selectedNode && (
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
                  <div style={{ marginBottom: 8, fontSize: 12, fontWeight: 'bold' }}>
                    选中节点
                  </div>
                  <div style={{ fontSize: 12 }}>
                    <div><strong>名称:</strong> {selectedNode.label}</div>
                    <div><strong>类型:</strong>
                      <Tag color={NODE_TYPE_COLORS[selectedNode.type]} style={{ marginLeft: 4 }}>
                        {getTypeLabel(selectedNode.type)}
                      </Tag>
                    </div>
                    {selectedNode.database_name && (
                      <div><strong>数据库:</strong> {selectedNode.database_name}</div>
                    )}
                    {selectedNode.table_name && selectedNode.type !== 'table' && (
                      <div><strong>表:</strong> {selectedNode.table_name}</div>
                    )}
                    {selectedNode.data_type && (
                      <div><strong>类型:</strong> {selectedNode.data_type}</div>
                    )}
                    {selectedNode.description && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontWeight: 'bold', marginBottom: 4 }}>描述:</div>
                        <div style={{ color: '#666' }}>{selectedNode.description}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
};

// 辅助函数
function getGraphStyle() {
  return [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'background-color': (ele: NodeSingular) => NODE_TYPE_COLORS[ele.data('type')] || '#999',
        'color': '#fff',
        'text-valign': 'center',
        'text-halign': 'center',
        'width': 'mapData(weight)',
        'height': 'mapData(height)',
        'font-size': 12,
        'border-width': 2,
        'border-color': '#fff',
        'shape': (ele: NodeSingular) => NODE_TYPE_SHAPES[ele.data('type')] || 'ellipse',
        'text-wrap': 'wrap',
        'text-max-width': '80px',
      },
    },
    {
      selector: 'node.faded',
      style: {
        'opacity': 0.2,
      },
    },
    {
      selector: 'node.highlighted',
      style: {
        'border-width': 3,
        'border-color': '#ffd700',
        'background-color': (ele: NodeSingular) => {
          const baseColor = NODE_TYPE_COLORS[ele.data('type')] || '#999';
          return baseColor;
        },
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#ffd700',
      },
    },
    {
      selector: 'node.center',
      style: {
        'border-width': 3,
        'border-color': '#ffd700',
        'background-width': 20,
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#ccc',
        'target-arrow-color': '#ccc',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': 10,
        'text-rotation': 'autorotate',
        'text-margin-y': -10,
      },
    },
    {
      selector: 'edge.highlighted',
      style: {
        'line-color': '#999',
        'width': 3,
        'target-arrow-color': '#999',
      },
    },
    {
      selector: 'edge.faded',
      style: {
        'opacity': 0.1,
      },
    },
    {
      selector: 'edge.hierarchy',
      style: {
        'line-style': 'solid',
        'line-color': '#ddd',
      },
    },
    {
      selector: 'edge.lineage',
      style: {
        'line-style': 'dashed',
        'line-color': '#999',
      },
    },
  ];
}

function getLayoutConfig(layout: string) {
  const configs: Record<string, any> = {
    'dagre': {
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 50,
      rankSep: 80,
    },
    'cose-bilkent': {
      name: 'cose-bilkent',
      idealEdgeLength: 100,
      nodeOverlap: 20,
      refresh: 20,
      fit: true,
      padding: 30,
      randomize: false,
      componentSpacing: 100,
      nodeRepulsion: 400,
    },
    'concentric': {
      name: 'concentric',
      concentric: (node: NodeSingular) => node.degree(),
      minNodeSpacing: 20,
    },
    'circle': {
      name: 'circle',
      fit: true,
      padding: 30,
      avoidOverlap: true,
    },
    'grid': {
      name: 'grid',
      rows: undefined,
      cols: undefined,
    },
    'breadthfirst': {
      name: 'breadthfirst',
      directed: false,
      spacingFactor: 80,
    },
  };

  return configs[layout] || configs['dagre'];
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    database: '数据库',
    table: '表',
    column: '列',
    lineage: '血缘',
  };
  return labels[type] || type;
}

export default GraphVisualization;
