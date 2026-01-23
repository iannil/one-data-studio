/**
 * 输入节点组件
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { InputOutlined } from '@ant-design/icons';

export default function InputNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-emerald-500 shadow-lg' : 'border-emerald-300'}
      `}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
          <InputOutlined className="text-emerald-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '输入'}</div>
          <div className="text-xs text-gray-500">Input</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-emerald-50 p-2 rounded mt-2">
          <div>键名: {data.config.key || 'input'}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-emerald-500" />
    </div>
  );
}
