import { useRef, useEffect } from 'react';
import { Card, Select } from 'antd';
import type { MetricDataPoint } from '@/services/model';

const { Option } = Select;

interface MetricChartProps {
  title?: string;
  data: MetricDataPoint[];
  color?: string;
  height?: number;
  showY2?: boolean;
  y2Data?: MetricDataPoint[];
  y2Color?: string;
  unit?: string;
  onPeriodChange?: (period: string) => void;
}

function MetricChart({
  title,
  data,
  color = '#1677ff',
  height = 200,
  showY2 = false,
  y2Data,
  y2Color = '#52c41a',
  unit,
  onPeriodChange,
}: MetricChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !data.length) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置 canvas 尺寸
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const padding = { top: 20, right: 20, bottom: 40, left: 50 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;

    // 清空画布
    ctx.clearRect(0, 0, rect.width, rect.height);

    // 计算数值范围
    const allValues = [...data];
    if (y2Data) allValues.push(...y2Data);

    const minValue = Math.min(...allValues.map((d) => d.value)) * 0.95;
    const maxValue = Math.max(...allValues.map((d) => d.value)) * 1.05;
    const valueRange = maxValue - minValue || 1;

    // 绘制网格线
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();

      // Y 轴标签
      const value = maxValue - (valueRange / 5) * i;
      ctx.fillStyle = '#999';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(value.toFixed(1), padding.left - 10, y);
    }

    // 绘制 X 轴标签
    const xStep = chartWidth / (data.length - 1 || 1);
    const labelStep = Math.ceil(data.length / 6);
    data.forEach((point, index) => {
      if (index % labelStep === 0) {
        const x = padding.left + index * xStep;
        const date = new Date(point.timestamp);
        const label = `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText(label, x, rect.height - 15);
      }
    });

    // 绘制线条
    const drawLine = (points: MetricDataPoint[], lineColor: string) => {
      ctx.beginPath();
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';

      points.forEach((point, index) => {
        const x = padding.left + index * xStep;
        const y = padding.top + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;

        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      ctx.stroke();

      // 绘制区域填充
      if (points.length > 1) {
        ctx.lineTo(padding.left + (points.length - 1) * xStep, padding.top + chartHeight);
        ctx.lineTo(padding.left, padding.top + chartHeight);
        ctx.closePath();
        ctx.fillStyle = `${lineColor}10`;
        ctx.fill();
      }

      // 绘制数据点
      points.forEach((point, index) => {
        const x = padding.left + index * xStep;
        const y = padding.top + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = lineColor;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
      });
    };

    drawLine(data, color);
    if (y2Data && showY2) {
      drawLine(y2Data, y2Color);
    }

    // 绘制单位
    if (unit) {
      ctx.fillStyle = '#999';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(unit, padding.left, padding.top - 10);
    }
  }, [data, color, height, showY2, y2Data, y2Color, unit]);

  if (!data.length) {
    return (
      <Card title={title} size="small">
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          暂无数据
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={title}
      size="small"
      extra={
        onPeriodChange && (
          <Select size="small" defaultValue="1h" onChange={onPeriodChange} style={{ width: 80 }}>
            <Option value="5m">5分钟</Option>
            <Option value="15m">15分钟</Option>
            <Option value="1h">1小时</Option>
            <Option value="6h">6小时</Option>
            <Option value="1d">1天</Option>
          </Select>
        )
      }
    >
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: `${height}px`,
        }}
      />
    </Card>
  );
}

export default MetricChart;
