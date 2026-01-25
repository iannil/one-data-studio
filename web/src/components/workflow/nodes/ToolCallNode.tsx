/**
 * 工具调用节点组件
 */

import { Handle, Position, NodeProps } from 'reactflow';
import { ToolOutlined } from '@ant-design/icons';

export default function ToolCallNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-indigo-500 shadow-lg' : 'border-indigo-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-indigo-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
          <ToolOutlined className="text-indigo-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '工具调用'}</div>
          <div className="text-xs text-gray-500">Tool Call</div>
        </div>
      </div>

      {data.config?.tool_name && (
        <div className="text-xs text-gray-600 bg-indigo-50 p-2 rounded mt-2">
          <div className="truncate" title={data.config.tool_name}>
            {data.config.tool_name}
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-indigo-500" />
    </div>
  );
}
