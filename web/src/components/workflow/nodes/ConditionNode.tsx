/**
 * 条件分支节点组件
 */

import { Handle, Position, NodeProps } from 'reactflow';
import { BranchesOutlined } from '@ant-design/icons';

export default function ConditionNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white min-w-[180px]
        ${selected ? 'border-amber-500 shadow-lg' : 'border-amber-300'}
      `}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-amber-500" />

      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
          <BranchesOutlined className="text-amber-600" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{data.label || '条件'}</div>
          <div className="text-xs text-gray-500">Condition</div>
        </div>
      </div>

      {data.config?.condition && (
        <div className="text-xs text-gray-600 bg-amber-50 p-2 rounded mt-2">
          <div className="truncate" title={data.config.condition}>
            {data.config.condition}
          </div>
        </div>
      )}

      {/* 两个输出连接点 */}
      <div className="flex justify-between mt-3">
        <div className="flex flex-col items-center">
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className="w-3 h-3 !bg-green-500"
            style={{ left: '25%' }}
          />
          <span className="text-xs text-green-600 mt-1">True</span>
        </div>
        <div className="flex flex-col items-center">
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className="w-3 h-3 !bg-red-500"
            style={{ left: '75%' }}
          />
          <span className="text-xs text-red-600 mt-1">False</span>
        </div>
      </div>
    </div>
  );
}
