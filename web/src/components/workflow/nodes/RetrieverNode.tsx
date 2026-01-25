/**
 * 检索节点组件
 */

import { Handle, Position, NodeProps } from 'reactflow';
import { SearchOutlined } from '@ant-design/icons';

export default function RetrieverNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-teal-500 shadow-lg' : 'border-teal-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-teal-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
          <SearchOutlined className="text-teal-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '检索'}</div>
          <div className="text-xs text-gray-500">Retriever</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-teal-50 p-2 rounded mt-2">
          <div>集合: {data.config.collection || 'default'}</div>
          <div>Top-K: {data.config.top_k || 5}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-teal-500" />
    </div>
  );
}
