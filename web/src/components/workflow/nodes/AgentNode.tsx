/**
 * Agent 节点组件
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { ApiOutlined } from '@ant-design/icons';

export default function AgentNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-purple-500 shadow-lg' : 'border-purple-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-purple-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
          <ApiOutlined className="text-purple-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || 'Agent'}</div>
          <div className="text-xs text-gray-500">ReAct Agent</div>
        </div>
      </div>

      {data.config && (
        <div className="text-xs text-gray-600 bg-purple-50 p-2 rounded mt-2">
          <div>类型: {data.config.agent_type || 'react'}</div>
          <div>模型: {data.config.model || 'gpt-4o-mini'}</div>
          <div>迭代: {data.config.max_iterations || 10}次</div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-purple-500" />
    </div>
  );
}
