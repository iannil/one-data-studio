/**
 * 思考节点组件
 */

import { Handle, Position, NodeProps } from 'reactflow';
import { BulbOutlined } from '@ant-design/icons';

export default function ThinkNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-yellow-500 shadow-lg' : 'border-yellow-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-yellow-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center">
          <BulbOutlined className="text-yellow-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '思考'}</div>
          <div className="text-xs text-gray-500">Think</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-yellow-50 p-2 rounded mt-2">
          <div>模型: {data.config.model || 'gpt-4o-mini'}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-yellow-500" />
    </div>
  );
}
