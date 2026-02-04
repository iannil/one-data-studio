import { useMemo } from 'react';
import { Card, Space, Select, Button, Tooltip } from 'antd';
import {
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  DotChartOutlined,
  TableOutlined,
  ThunderboltFilled,
  SwapOutlined,
} from '@ant-design/icons';
import type { Text2SqlResponse } from '@/services/agent-service';

const { Option } = Select;

// 图表类型配置
const CHART_TYPES = {
  line: {
    name: '折线图',
    icon: <LineChartOutlined />,
    category: 'trend',
  },
  area: {
    name: '面积图',
    icon: <AreaChartIcon />,
    category: 'trend',
  },
  column: {
    name: '柱状图',
    icon: <BarChartOutlined />,
    category: 'comparison',
  },
  bar: {
    name: '条形图',
    icon: <BarChartIcon />,
    category: 'comparison',
  },
  pie: {
    name: '饼图',
    icon: <PieChartOutlined />,
    category: 'proportion',
  },
  donut: {
    name: '环形图',
    icon: <DonutChartIcon />,
    category: 'proportion',
  },
  scatter: {
    name: '散点图',
    icon: <DotChartOutlined />,
    category: 'distribution',
  },
  table: {
    name: '表格',
    icon: <TableOutlined />,
    category: 'tabular',
  },
};

// 图表类型分组
const CHART_TYPE_GROUPS = [
  { label: '趋势分析', value: 'trend' },
  { label: '数据对比', value: 'comparison' },
  { label: '占比分析', value: 'proportion' },
  { label: '分布分析', value: 'distribution' },
  { label: '表格展示', value: 'tabular' },
];

interface SmartChartProps {
  data: {
    columns: string[];
    rows: Record<string, unknown>[];
  };
  chartRecommendation?: {
    chart_type: string;
    chart_name: string;
    confidence: number;
    reason: string;
    config?: Record<string, unknown>;
  };
  height?: number;
  onChartTypeChange?: (type: string) => void;
}

export function SmartChart({
  data,
  chartRecommendation,
  height = 400,
  onChartTypeChange,
}: SmartChartProps) {
  const [selectedChartType, setSelectedChartType] = React.useState(
    chartRecommendation?.chart_type || 'table'
  );
  const [selectedCategory, setSelectedCategory] = React.useState<string | undefined>();

  // 分析数据特征
  const analysis = useMemo(() => {
    const columns = data.columns || [];
    const rows = data.rows || [];
    const rowCount = rows.length;
    const colCount = columns.length;

    // 推断列类型
    const columnTypes = columns.map((col) => {
      const sampleValues = rows.slice(0, 100).map((r) => r[col]);
      const numericCount = sampleValues.filter(
        (v) => typeof v === 'number' && !isNaN(v as number)
      ).length;
      const isNumeric = numericCount / Math.max(sampleValues.length, 1) > 0.8;
      return { name: col, isNumeric };
    });

    const numericColumns = columnTypes.filter((c) => c.isNumeric).map((c) => c.name);
    const categoricalColumns = columnTypes.filter((c) => !c.isNumeric).map((c) => c.name);

    return {
      rowCount,
      colCount,
      numericColumns,
      categoricalColumns,
      columnTypes,
    };
  }, [data]);

  // 获取可用的图表类型
  const availableChartTypes = useMemo(() => {
    const { numericColumns, categoricalColumns } = analysis;

    // 根据数据特征确定可用图表
    const types: string[] = ['table'];

    if (numericColumns.length >= 1 && categoricalColumns.length >= 1) {
      types.push('column', 'bar', 'pie', 'donut');
    }

    if (numericColumns.length >= 1) {
      types.push('line', 'area');
    }

    if (numericColumns.length >= 2) {
      types.push('scatter');
    }

    return types;
  }, [analysis]);

  // 切换图表类型
  const handleChartTypeChange = (type: string) => {
    setSelectedChartType(type);
    onChartTypeChange?.(type);
  };

  // 渲染图表
  const renderChart = () => {
    const { rows, columns } = data;

    if (selectedChartType === 'table') {
      return renderTable(rows, columns);
    }

    if (selectedChartType === 'line' || selectedChartType === 'area') {
      return renderLineChart(rows, columns, selectedChartType === 'area');
    }

    if (selectedChartType === 'column') {
      return renderColumnChart(rows, columns);
    }

    if (selectedChartType === 'bar') {
      return renderBarChart(rows, columns);
    }

    if (selectedChartType === 'pie' || selectedChartType === 'donut') {
      return renderPieChart(rows, columns, selectedChartType === 'donut');
    }

    if (selectedChartType === 'scatter') {
      return renderScatterChart(rows, columns);
    }

    return renderTable(rows, columns);
  };

  // 简单表格渲染
  const renderTable = (rows: Record<string, unknown>[], columns: string[]) => (
    <div style={{ overflow: 'auto', maxHeight: height - 60 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead style={{ position: 'sticky', top: 0, backgroundColor: '#fafafa' }}>
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  borderBottom: '2px solid #e8e8e8',
                  fontWeight: 600,
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((row, i) => (
            <tr
              key={i}
              style={{
                borderBottom: '1px solid #f0f0f0',
                backgroundColor: i % 2 === 0 ? '#fff' : '#fafafa',
              }}
            >
              {columns.map((col) => (
                <td key={col} style={{ padding: '8px 16px' }}>
                  {String(row[col] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && (
        <div style={{ padding: 12, textAlign: 'center', color: '#999' }}>
          仅显示前 100 条记录，共 {rows.length} 条
        </div>
      )}
    </div>
  );

  // 简单柱状图渲染（使用 CSS）
  const renderColumnChart = (rows: Record<string, unknown>[], columns: string[]) => {
    const { numericColumns, categoricalColumns } = analysis;

    if (numericColumns.length === 0 || categoricalColumns.length === 0) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>数据不适合此图表类型</div>;
    }

    const xColumn = categoricalColumns[0];
    const yColumn = numericColumns[0];

    // 限制显示数量
    const displayRows = rows.slice(0, 20);
    const maxValue = Math.max(...displayRows.map((r) => Number(r[yColumn]) || 0), 1);

    return (
      <div style={{ padding: 24, height: height - 60 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, height: '100%' }}>
          {displayRows.map((row, i) => {
            const value = Number(row[yColumn]) || 0;
            const heightPercent = (value / maxValue) * 100;
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  height: '100%',
                  justifyContent: 'flex-end',
                }}
              >
                <Tooltip title={`${row[xColumn]}: ${value}`}>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: 60,
                      height: `${heightPercent}%`,
                      backgroundColor: '#1677ff',
                      borderRadius: '4px 4px 0 0',
                      transition: 'all 0.3s',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#4096ff';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#1677ff';
                    }}
                  />
                </Tooltip>
                <span
                  style={{
                    fontSize: 11,
                    marginTop: 8,
                    textAlign: 'center',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    width: '100%',
                  }}
                >
                  {String(row[xColumn])}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 简单条形图渲染
  const renderBarChart = (rows: Record<string, unknown>[], columns: string[]) => {
    const { numericColumns, categoricalColumns } = analysis;

    if (numericColumns.length === 0 || categoricalColumns.length === 0) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>数据不适合此图表类型</div>;
    }

    const yColumn = categoricalColumns[0];
    const xColumn = numericColumns[0];

    const displayRows = rows.slice(0, 20);
    const maxValue = Math.max(...displayRows.map((r) => Number(r[xColumn]) || 0), 1);

    return (
      <div style={{ padding: 24, height: height - 60, overflowY: 'auto' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {displayRows.map((row, i) => {
            const value = Number(row[xColumn]) || 0;
            const widthPercent = (value / maxValue) * 100;
            return (
              <div key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12 }}>{String(row[yColumn])}</span>
                  <span style={{ fontSize: 12, fontWeight: 'bold' }}>{value}</span>
                </div>
                <div style={{ height: 24, backgroundColor: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${widthPercent}%`,
                      backgroundColor: '#1677ff',
                      transition: 'width 0.5s',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </Space>
      </div>
    );
  };

  // 简单折线图/面积图渲染
  const renderLineChart = (rows: Record<string, unknown>[], columns: string[], isArea: boolean) => {
    const { numericColumns } = analysis;

    if (numericColumns.length === 0) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>数据不适合此图表类型</div>;
    }

    const yColumn = numericColumns[0];
    const xColumn = columns.find((c) => c !== yColumn) || columns[0];

    const displayRows = rows.slice(0, 50);
    const maxValue = Math.max(...displayRows.map((r) => Number(r[yColumn]) || 0), 1);
    const minValue = Math.min(...displayRows.map((r) => Number(r[yColumn]) || 0), 0);
    const range = maxValue - minValue || 1;

    // 生成 SVG 路径
    const points = displayRows.map((row, i) => {
      const x = (i / (displayRows.length - 1 || 1)) * 100;
      const y = 100 - ((Number(row[yColumn]) || 0 - minValue) / range) * 80 - 10;
      return { x, y, value: row[yColumn], label: row[xColumn] };
    });

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    const areaPath = `${pathD} L 100 100 L 0 100 Z`;

    return (
      <div style={{ padding: 24, height: height - 60, position: 'relative' }}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          {isArea && (
            <path
              d={areaPath}
              fill="rgba(22, 119, 255, 0.2)"
              stroke="none"
            />
          )}
          <path
            d={pathD}
            fill="none"
            stroke="#1677ff"
            strokeWidth="0.5"
            vectorEffect="non-scaling-stroke"
          />
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="1.5"
              fill="#1677ff"
              style={{ cursor: 'pointer' }}
              onMouseEnter={(e) => {
                e.currentTarget.setAttribute('r', '2.5');
              }}
              onMouseLeave={(e) => {
                e.currentTarget.setAttribute('r', '1.5');
              }}
            >
              <title>{`${p.label}: ${p.value}`}</title>
            </circle>
          ))}
        </svg>
        {/* X轴标签 */}
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
          {points.filter((_, i) => i % Math.ceil(points.length / 5) === 0).map((p, i) => (
            <span key={i}>{String(p.label)}</span>
          ))}
        </div>
      </div>
    );
  };

  // 简单饼图/环形图渲染
  const renderPieChart = (rows: Record<string, unknown>[], columns: string[], isDonut: boolean) => {
    const { numericColumns, categoricalColumns } = analysis;

    if (numericColumns.length === 0 || categoricalColumns.length === 0) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>数据不适合此图表类型</div>;
    }

    const valueColumn = numericColumns[0];
    const labelColumn = categoricalColumns[0];

    const displayRows = rows.slice(0, 10);
    const total = displayRows.reduce((sum, r) => sum + (Number(r[valueColumn]) || 0), 0);

    let currentAngle = 0;
    const colors = ['#1677ff', '#52c41a', '#faad14', '#722ed1', '#eb2f96', '#13c2c2', '#fa8c16', '#a0d911'];

    const slices = displayRows.map((row, i) => {
      const value = Number(row[valueColumn]) || 0;
      const percentage = total > 0 ? (value / total) * 100 : 0;
      const angle = (percentage / 100) * 360;
      const startAngle = currentAngle;
      currentAngle += angle;
      const endAngle = currentAngle;

      return {
        label: String(row[labelColumn]),
        value,
        percentage,
        startAngle,
        endAngle,
        color: colors[i % colors.length],
      };
    });

    return (
      <div style={{ padding: 24, height: height - 60 }}>
        <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <svg viewBox="-1.2 -1.2 2.4 2.4" style={{ width: Math.min(height, 400), height: Math.min(height, 400) }}>
            {slices.map((slice, i) => {
              const startRad = (slice.startAngle - 90) * Math.PI / 180;
              const endRad = (slice.endAngle - 90) * Math.PI / 180;
              const x1 = Math.cos(startRad);
              const y1 = Math.sin(startRad);
              const x2 = Math.cos(endRad);
              const y2 = Math.sin(endRad);
              const largeArc = slice.percentage > 50 ? 1 : 0;

              const pathData = `M 0 0 L ${x1} ${y1} A 1 1 0 ${largeArc} 1 ${x2} ${y2} Z`;

              return (
                <g key={i}>
                  <path
                    d={pathData}
                    fill={slice.color}
                    stroke="#fff"
                    strokeWidth="0.02"
                    style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.05)';
                      e.currentTarget.style.transformOrigin = 'center';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                    }}
                  >
                    <title>{`${slice.label}: ${slice.value} (${slice.percentage.toFixed(1)}%)`}</title>
                  </path>
                </g>
              );
            })}
            {isDonut && (
              <circle cx="0" cy="0" r="0.6" fill="#fff" />
            )}
          </svg>
        </div>
        {/* 图例 */}
        <div style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', backgroundColor: 'rgba(255,255,255,0.9)', padding: 12, borderRadius: 8 }}>
          <Space direction="vertical" size="small">
            {slices.map((slice, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 12, height: 12, backgroundColor: slice.color, borderRadius: 2 }} />
                <span style={{ fontSize: 12 }}>{slice.label}</span>
                <span style={{ fontSize: 12, fontWeight: 'bold' }}>{slice.percentage.toFixed(1)}%</span>
              </div>
            ))}
          </Space>
        </div>
      </div>
    );
  };

  // 散点图
  const renderScatterChart = (rows: Record<string, unknown>[], columns: string[]) => {
    const { numericColumns } = analysis;

    if (numericColumns.length < 2) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>需要至少两个数值列</div>;
    }

    const xColumn = numericColumns[0];
    const yColumn = numericColumns[1];

    const displayRows = rows.slice(0, 200);
    const xValues = displayRows.map((r) => Number(r[xColumn]) || 0);
    const yValues = displayRows.map((r) => Number(r[yColumn]) || 0);

    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMin = Math.min(...yValues);
    const yMax = Math.max(...yValues);
    const xRange = xMax - xMin || 1;
    const yRange = yMax - yMin || 1;

    return (
      <div style={{ padding: 24, height: height - 60 }}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          {displayRows.map((row, i) => {
            const x = ((Number(row[xColumn]) || 0 - xMin) / xRange) * 90 + 5;
            const y = 100 - ((Number(row[yColumn]) || 0 - yMin) / yRange) * 90 - 5;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="1.5"
                fill="#1677ff"
                opacity="0.7"
                style={{ cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  e.currentTarget.setAttribute('r', '2.5');
                  e.currentTarget.setAttribute('opacity', '1');
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.setAttribute('r', '1.5');
                  e.currentTarget.setAttribute('opacity', '0.7');
                }}
              >
                <title>{`${xColumn}: ${row[xColumn]}, ${yColumn}: ${row[yColumn]}`}</title>
              </circle>
            );
          })}
        </svg>
      </div>
    );
  };

  return (
    <Card
      title={
        <Space>
          {chartRecommendation && (
            <Tooltip title={chartRecommendation.reason}>
              <ThunderboltFilled style={{ color: '#faad14' }} />
            </Tooltip>
          )}
          <span>数据可视化</span>
          {chartRecommendation && (
            <span style={{ fontSize: 12, color: '#999' }}>
              AI 推荐：{chartRecommendation.chart_name} ({(chartRecommendation.confidence * 100).toFixed(0)}%)
            </span>
          )}
        </Space>
      }
      extra={
        <Space>
          <Select
            value={selectedChartType}
            onChange={handleChartTypeChange}
            style={{ width: 150 }}
            placeholder="选择图表类型"
          >
            {availableChartTypes.map((type) => (
              <Option key={type} value={type}>
                <Space size="small">
                  {CHART_TYPES[type as keyof typeof CHART_TYPES]?.icon}
                  {CHART_TYPES[type as keyof typeof CHART_TYPES]?.name}
                </Space>
              </Option>
            ))}
          </Select>
          <Button
            type="text"
            icon={<SwapOutlined />}
            onClick={() => {
              const currentIndex = availableChartTypes.indexOf(selectedChartType);
              const nextIndex = (currentIndex + 1) % availableChartTypes.length;
              handleChartTypeChange(availableChartTypes[nextIndex]);
            }}
            title="切换图表类型"
          />
        </Space>
      }
      styles={{ body: { padding: 0 } }}
    >
      {renderChart()}
    </Card>
  );
}

// 简单的图标组件
function AreaChartIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z" />
    </svg>
  );
}

function BarChartIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <path d="M4 9h4v11H4zm12 4h4v7h-4zm-6-9h4v16h-4z" />
    </svg>
  );
}

function DonutChartIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6z" />
    </svg>
  );
}

// React 导入
import React from 'react';

export default SmartChart;
