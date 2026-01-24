/**
 * 输出节点组件
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { UpOutlined } from '@ant-design/icons';

export default function OutputNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-red-500 shadow-lg' : 'border-red-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-red-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
          <UpOutlined className="text-red-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '输出'}</div>
          <div className="text-xs text-gray-500">Output</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-red-50 p-2 rounded mt-2">
          <div>键名: {data.config.output_key || 'result'}</div>
        </div>
      )}
    </div>
  );
}
