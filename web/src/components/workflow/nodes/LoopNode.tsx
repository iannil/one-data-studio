/**
 * 循环节点组件
 */

import { Handle, Position, NodeProps } from 'reactflow';
import { SyncOutlined } from '@ant-design/icons';

export default function LoopNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-cyan-500 shadow-lg' : 'border-cyan-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-cyan-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-cyan-100 flex items-center justify-center">
          <SyncOutlined spin={false} className="text-cyan-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '循环'}</div>
          <div className="text-xs text-gray-500">Loop</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-cyan-50 p-2 rounded mt-2">
          <div>次数: {data.config.loop_over || 1}</div>
          <div>最大: {data.config.max_iterations || 10}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-cyan-500" />
    </div>
  );
}
