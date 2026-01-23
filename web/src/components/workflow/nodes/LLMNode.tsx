/**
 * LLM 节点组件
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { RobotOutlined } from '@ant-design/icons';

export default function LLMNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-blue-500 shadow-lg' : 'border-blue-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-blue-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          <RobotOutlined className="text-blue-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '大模型'}</div>
          <div className="text-xs text-gray-500">LLM</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded mt-2">
          <div>模型: {data.config.model || 'gpt-4o-mini'}</div>
          <div>温度: {data.config.temperature || 0.7}</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-blue-500" />
    </div>
  );
}
