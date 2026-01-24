import { useEffect, useRef, useState } from 'react';
import { Card, Select, Spin, Tag, Space, Button } from 'antd';
import {
  ReloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
} from '@ant-design/icons';
import type { LineageGraph as LineageGraphType, LineageNode } from '@/services/alldata';

const { Option } = Select;

interface LineageGraphProps {
  graph: LineageGraphType | null;
  loading?: boolean;
  onNodeClick?: (node: LineageNode) => void;
  onRefresh?: () => void;
  height?: number;
}

const NODE_COLORS: Record<string, string> = {
  table: '#1677ff',
  view: '#52c41a',
  column: '#faad14',
  etl_task: '#722ed1',
  dataset: '#eb2f96',
};

const NODE_SHAPES: Record<string, string> = {
  table: 'rect',
  view: 'rect',
  column: 'circle',
  etl_task: 'diamond',
  dataset: 'rect',
};

function LineageGraph({ graph, loading, onNodeClick, onRefresh, height = 500 }: LineageGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 50, y: 50 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [layout, setLayout] = useState<'hierarchical' | 'force' | 'circular'>('hierarchical');
  const [dragging, setDragging] = useState(false);

  // 计算节点布局
  const calculateLayout = (g: LineageGraphType, canvasWidth: number, canvasHeight: number) => {
    const nodes = [...g.nodes];
    const nodePositions = new Map<string, { x: number; y: number }>();

    if (layout === 'hierarchical') {
      // 分层布局 - 按照边的方向分层
      const levels = new Map<string, number>();
      const visited = new Set<string>();

      // 找到所有根节点（没有上游的节点）
      const targets = new Set(g.edges.map((e) => e.target));
      const rootNodes = nodes.filter((n) => !targets.has(n.id));

      // BFS 计算层级
      let queue = rootNodes.map((n) => ({ id: n.id, level: 0 }));
      while (queue.length > 0) {
        const { id, level } = queue.shift()!;
        levels.set(id, level);
        visited.add(id);

        // 找到所有从该节点出发的边
        const outgoingEdges = g.edges.filter((e) => e.source === id);
        for (const edge of outgoingEdges) {
          if (!visited.has(edge.target)) {
            queue.push({ id: edge.target, level: level + 1 });
          }
        }
      }

      // 未访问的节点放到最后一层
      for (const node of nodes) {
        if (!levels.has(node.id)) {
          levels.set(node.id, 0);
        }
      }

      // 按层级分组
      const levelGroups = new Map<number, string[]>();
      for (const [id, level] of levels) {
        if (!levelGroups.has(level)) {
          levelGroups.set(level, []);
        }
        levelGroups.get(level)!.push(id);
      }

      // 计算位置
      const maxLevel = Math.max(...Array.from(levels.values()));
      const levelHeight = (canvasHeight - 100) / (maxLevel + 1);

      for (const [level, nodeIds] of levelGroups) {
        const y = 50 + level * levelHeight;
        const levelWidth = canvasWidth / (nodeIds.length + 1);
        nodeIds.forEach((nodeId, index) => {
          nodePositions.set(nodeId, {
            x: levelWidth * (index + 1),
            y,
          });
        });
      }
    } else if (layout === 'circular') {
      // 圆形布局
      const centerX = canvasWidth / 2;
      const centerY = canvasHeight / 2;
      const radius = Math.min(canvasWidth, canvasHeight) / 2 - 60;

      nodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / nodes.length;
        nodePositions.set(node.id, {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        });
      });
    } else {
      // 力导向布局（简化版）
      const centerX = canvasWidth / 2;
      const centerY = canvasHeight / 2;
      nodes.forEach((node, index) => {
        const angle = Math.random() * 2 * Math.PI;
        const dist = 50 + Math.random() * 100;
        nodePositions.set(node.id, {
          x: centerX + dist * Math.cos(angle),
          y: centerY + dist * Math.sin(angle),
        });
      });
    }

    return nodePositions;
  };

  useEffect(() => {
    if (!graph || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置 canvas 尺寸
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // 清空画布
    ctx.clearRect(0, 0, rect.width, rect.height);

    if (!graph.nodes.length) {
      ctx.fillStyle = '#999';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('暂无血缘数据', rect.width / 2, rect.height / 2);
      return;
    }

    const nodePositions = calculateLayout(graph, rect.width, rect.height);

    // 绘制边
    graph.edges.forEach((edge) => {
      const source = nodePositions.get(edge.source);
      const target = nodePositions.get(edge.target);
      if (!source || !target) return;

      ctx.beginPath();
      ctx.moveTo(source.x + offset.x, source.y + offset.y);
      ctx.lineTo(target.x + offset.x, target.y + offset.y);

      // 设置边的样式
      const isHighlighted = hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode);
      ctx.strokeStyle = isHighlighted ? '#1677ff' : '#d9d9d9';
      ctx.lineWidth = isHighlighted ? 2 : 1;
      ctx.stroke();

      // 绘制箭头
      const angle = Math.atan2(target.y - source.y, target.x - source.x);
      const arrowLength = 10;
      ctx.beginPath();
      ctx.moveTo(target.x + offset.x, target.y + offset.y);
      ctx.lineTo(
        target.x + offset.x - arrowLength * Math.cos(angle - Math.PI / 6),
        target.y + offset.y - arrowLength * Math.sin(angle - Math.PI / 6)
      );
      ctx.moveTo(target.x + offset.x, target.y + offset.y);
      ctx.lineTo(
        target.x + offset.x - arrowLength * Math.cos(angle + Math.PI / 6),
        target.y + offset.y - arrowLength * Math.sin(angle + Math.PI / 6)
      );
      ctx.stroke();
    });

    // 绘制节点
    graph.nodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;

      const x = pos.x + offset.x;
      const y = pos.y + offset.y;
      const isHovered = hoveredNode === node.id;
      const isConnected = hoveredNode && graph.edges.some(
        (e) => (e.source === hoveredNode && e.target === node.id) ||
               (e.target === hoveredNode && e.source === node.id)
      );

      // 设置节点样式
      const alpha = (hoveredNode && !isHovered && !isConnected) ? 0.3 : 1;
      ctx.globalAlpha = alpha;

      const color = NODE_COLORS[node.type] || '#666';
      const size = isHovered ? 8 : 6;

      if (NODE_SHAPES[node.type] === 'circle') {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        if (isHovered) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      } else if (NODE_SHAPES[node.type] === 'diamond') {
        ctx.beginPath();
        ctx.moveTo(x, y - size);
        ctx.lineTo(x + size, y);
        ctx.lineTo(x, y + size);
        ctx.lineTo(x - size, y);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
      } else {
        ctx.fillStyle = color;
        ctx.fillRect(x - size, y - size / 2, size * 2, size);
      }

      ctx.globalAlpha = 1;

      // 绘制标签
      ctx.fillStyle = '#333';
      ctx.font = isHovered ? 'bold 12px sans-serif' : '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, x, y + size + 14);
    });
  }, [graph, scale, offset, hoveredNode, layout]);

  // 鼠标位置检测
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graph || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const nodePositions = calculateLayout(graph, rect.width, rect.height);

    for (const [nodeId, pos] of nodePositions) {
      const nodeX = pos.x + offset.x;
      const nodeY = pos.y + offset.y;
      const dist = Math.sqrt((x - nodeX) ** 2 + (y - nodeY) ** 2);
      if (dist < 15) {
        setHoveredNode(nodeId);
        canvas.style.cursor = 'pointer';
        return;
      }
    }

    setHoveredNode(null);
    canvas.style.cursor = dragging ? 'grabbing' : 'grab';
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!hoveredNode) {
      setDragging(true);
    }
  };

  const handleMouseUp = () => {
    setDragging(false);
  };

  const handleMouseLeave = () => {
    setDragging(false);
    setHoveredNode(null);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hoveredNode && onNodeClick && graph) {
      const node = graph.nodes.find((n) => n.id === hoveredNode);
      if (node) {
        onNodeClick(node);
      }
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((prev) => Math.max(0.5, Math.min(2, prev + delta)));
  };

  const handleZoomIn = () => setScale((prev) => Math.min(2, prev + 0.1));
  const handleZoomOut = () => setScale((prev) => Math.max(0.5, prev - 0.1));
  const handleReset = () => {
    setScale(1);
    setOffset({ x: 50, y: 50 });
  };

  // 图例
  const legend = [
    { type: 'table', label: '表', color: NODE_COLORS.table },
    { type: 'view', label: '视图', color: NODE_COLORS.view },
    { type: 'column', label: '字段', color: NODE_COLORS.column },
    { type: 'etl_task', label: 'ETL 任务', color: NODE_COLORS.etl_task },
    { type: 'dataset', label: '数据集', color: NODE_COLORS.dataset },
  ];

  return (
    <Card
      title="血缘关系图"
      extra={
        <Space>
          <Select value={layout} onChange={setLayout} style={{ width: 120 }}>
            <Option value="hierarchical">分层布局</Option>
            <Option value="circular">环形布局</Option>
            <Option value="force">力导向布局</Option>
          </Select>
          <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} disabled={scale <= 0.5} />
          <Button onClick={handleReset}>{Math.round(scale * 100)}%</Button>
          <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} disabled={scale >= 2} />
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading} />
          <Button icon={<ExpandOutlined />} onClick={() => {}}>
            全屏
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <div style={{ position: 'relative' }}>
          <canvas
            ref={canvasRef}
            style={{
              width: '100%',
              height: `${height}px`,
              border: '1px solid #f0f0f0',
              borderRadius: '8px',
              cursor: 'grab',
            }}
            onMouseMove={handleMouseMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            onClick={handleCanvasClick}
            onWheel={handleWheel}
          />

          {/* 图例 */}
          <div style={{ position: 'absolute', bottom: 16, right: 16, background: 'rgba(255,255,255,0.9)', padding: '8px 12px', borderRadius: '6px', border: '1px solid #f0f0f0' }}>
            <Space direction="vertical" size={4}>
              {legend.map((item) => (
                <Space key={item.type} size={8}>
                  <div style={{ width: 12, height: 12, background: item.color, borderRadius: '2px' }} />
                  <span style={{ fontSize: 12 }}>{item.label}</span>
                </Space>
              ))}
            </Space>
          </div>
        </div>

        {/* 节点信息提示 */}
        {hoveredNode && graph && (
          <div style={{ marginTop: 16 }}>
            {(() => {
              const node = graph.nodes.find((n) => n.id === hoveredNode);
              if (!node) return null;
              return (
                <Space>
                  <Tag color={NODE_COLORS[node.type]}>{node.type}</Tag>
                  <span>
                    <strong>{node.name}</strong>
                    {node.database && <span style={{ color: '#999' }}> ({node.database})</span>}
                  </span>
                </Space>
              );
            })()}
          </div>
        )}
      </Spin>
    </Card>
  );
}

export default LineageGraph;
