/**
 * 工作流编辑页面
 * Phase 7: Sprint 7.3
 *
 * 可视化工作流编辑器，支持：
 * - 拖拽创建节点
 * - 连接节点
 * - 配置节点属性
 * - 保存和运行工作流
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  message,
  Modal,
  Space,
  Dropdown,
  Tooltip,
  Badge,
} from 'antd';
import {
  SaveOutlined,
  PlayCircleOutlined,
  StopOutlined,
  UndoOutlined,
  RedoOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FitScreenOutlined,
  DownloadOutlined,
  UploadOutlined,
  ClearOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

import FlowCanvas, { Node, Edge } from '../../components/workflow/FlowCanvas';
import NodePalette, { nodeTypes } from '../../components/workflow/NodePalette';
import NodeConfigPanel from '../../components/workflow/NodeConfigPanel';
import * as bishengService from '../../services/bisheng';

interface WorkflowDefinition {
  version: string;
  nodes: any[];
  edges: any[];
}

function WorkflowEditorPage() {
  const { workflowId } = useParams();
  const navigate = useNavigate();

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showConfig, setShowConfig] = useState(true);

  // 加载工作流定义
  useEffect(() => {
    if (workflowId && workflowId !== 'new') {
      loadWorkflow(workflowId);
    } else {
      // 新建工作流，添加默认节点
      setNodes([
        {
          id: 'input-1',
          type: 'input',
          position: { x: 100, y: 100 },
          data: { label: '输入', config: { key: 'input' } },
        },
        {
          id: 'output-1',
          type: 'output',
          position: { x: 100, y: 300 },
          data: { label: '输出', config: { output_key: 'result' } },
        },
      ]);
    }
  }, [workflowId]);

  // 加载工作流
  const loadWorkflow = async (id: string) => {
    setLoading(true);
    try {
      const response = await bishengService.getWorkflow(id);
      if (response.code === 0 && response.data) {
        const wf = response.data;
        setWorkflowName(wf.name || '');
        setWorkflowDescription(wf.description || '');

        // 解析工作流定义
        if (wf.definition) {
          let definition: WorkflowDefinition;
          if (typeof wf.definition === 'string') {
            definition = JSON.parse(wf.definition);
          } else {
            definition = wf.definition;
          }

          if (definition.nodes) {
            setNodes(definition.nodes);
          }
          if (definition.edges) {
            setEdges(definition.edges);
          }
        }
      }
    } catch (error) {
      message.error('加载工作流失败');
    } finally {
      setLoading(false);
    }
  };

  // 保存工作流
  const handleSave = async () => {
    setSaving(true);
    try {
      const definition: WorkflowDefinition = {
        version: '1.0',
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          targetHandle: e.targetHandle,
        })),
      };

      const isCreateMode = workflowId === 'new';

      if (isCreateMode) {
        // 创建新工作流
        const response = await bishengService.createWorkflow({
          name: workflowName || '未命名工作流',
          description: workflowDescription,
          type: 'custom',
          definition: JSON.stringify(definition),
        });
        if (response.code === 0) {
          message.success('工作流创建成功');
          setHasChanges(false);
          navigate(`/workflows/${response.data.workflow_id}/edit`, { replace: true });
        }
      } else {
        // 更新现有工作流
        const response = await bishengService.updateWorkflow(workflowId, {
          name: workflowName || '未命名工作流',
          description: workflowDescription,
          type: 'custom',
          definition: JSON.stringify(definition),
        });
        if (response.code === 0) {
          message.success('工作流更新成功');
          setHasChanges(false);
        }
      }
    } catch (error) {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 运行工作流
  const handleRun = async () => {
    if (workflowId === 'new') {
      message.warning('请先保存工作流');
      return;
    }

    try {
      const response = await bishengService.startWorkflow(workflowId, {
        inputs: { query: '测试查询' },
      });
      if (response.code === 0) {
        message.success(`工作流已启动，执行ID: ${response.data.execution_id}`);
        navigate(`/workflows/${workflowId}/executions`);
      }
    } catch (error) {
      message.error('启动失败');
    }
  };

  // 处理节点变化
  const handleNodesChange = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
    setHasChanges(true);
  }, []);

  // 处理边变化
  const handleEdgesChange = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
    setHasChanges(true);
  }, []);

  // 添加节点
  const handleAddNode = useCallback((nodeType: string, config: Record<string, any>) => {
    const newNode: Node = {
      id: `${nodeType}-${Date.now()}`,
      type: nodeType,
      position: { x: Math.random() * 500 + 100, y: Math.random() * 300 + 100 },
      data: {
        label: nodeTypes.find((t) => t.type === nodeType)?.label || nodeType,
        config,
      },
    };
    setNodes((nds) => [...nds, newNode]);
    setHasChanges(true);
  }, []);

  // 更新节点配置
  const handleNodeUpdate = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, config } }
          : node
      )
    );
    setHasChanges(true);
    message.success('节点配置已更新');
  }, []);

  // 导出工作流
  const handleExport = () => {
    const definition = {
      version: '1.0',
      nodes,
      edges,
    };
    const dataStr = JSON.stringify(definition, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName || 'workflow'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 导入工作流
  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const text = await file.text();
        try {
          const definition = JSON.parse(text);
          if (definition.nodes) setNodes(definition.nodes);
          if (definition.edges) setEdges(definition.edges);
          setHasChanges(true);
          message.success('工作流已导入');
        } catch {
          message.error('导入失败：无效的 JSON 文件');
        }
      }
    };
    input.click();
  };

  // 清空画布
  const handleClear = () => {
    Modal.confirm({
      title: '确认清空',
      content: '此操作将清空所有节点和连线，确定继续？',
      onOk: () => {
        setNodes([]);
        setEdges([]);
        setHasChanges(true);
      },
    });
  };

  // 验证工作流
  const handleValidate = () => {
    const errors: string[] = [];

    // 检查是否有输入节点
    const hasInput = nodes.some((n) => n.type === 'input');
    if (!hasInput) {
      errors.push('缺少输入节点');
    }

    // 检查是否有输出节点
    const hasOutput = nodes.some((n) => n.type === 'output');
    if (!hasOutput) {
      errors.push('缺少输出节点');
    }

    // 检查孤立节点
    const connectedNodeIds = new Set<string>();
    edges.forEach((e) => {
      connectedNodeIds.add(e.source);
      connectedNodeIds.add(e.target);
    });
    const isolatedNodes = nodes.filter(
      (n) => !connectedNodeIds.has(n.id) && n.type !== 'input'
    );
    if (isolatedNodes.length > 0) {
      errors.push(`${isolatedNodes.length} 个孤立节点`);
    }

    if (errors.length > 0) {
      Modal.warning({
        title: '工作流验证失败',
        content: (
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        ),
      });
    } else {
      Modal.success({
        title: '工作流验证通过',
        content: '工作流定义有效，可以保存和运行。',
      });
    }
  };

  // 工具栏菜单项
  const viewMenuItems: MenuProps['items'] = [
    {
      key: 'zoom-in',
      label: '放大',
      icon: <ZoomInOutlined />,
    },
    {
      key: 'zoom-out',
      label: '缩小',
      icon: <ZoomOutOutlined />,
    },
    {
      key: 'fit',
      label: '适应屏幕',
      icon: <FitScreenOutlined />,
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span>加载中...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b">
        <Space>
          <Button icon={<UndoOutlined />} disabled>
            撤销
          </Button>
          <Button icon={<RedoOutlined />} disabled>
            重做
          </Button>
          <div className="w-px h-6 bg-gray-300 mx-2" />
          <Badge dot={hasChanges}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存
            </Button>
          </Badge>
          <Button
            icon={<PlayCircleOutlined />}
            onClick={handleRun}
            disabled={workflowId === 'new'}
          >
            运行
          </Button>
        </Space>

        <Space>
          <span className="text-sm text-gray-600">
            {workflowName || '未命名工作流'}
          </span>
          <Badge count={nodes.length} showZero>
            <span className="text-xs text-gray-500">节点</span>
          </Badge>
        </Space>

        <Space>
          <Dropdown menu={{ items: viewMenuItems }}>
            <Button icon={<ZoomInOutlined />}>视图</Button>
          </Dropdown>
          <Button icon={<CheckCircleOutlined />} onClick={handleValidate}>
            验证
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
          <Button icon={<UploadOutlined />} onClick={handleImport}>
            导入
          </Button>
          <Button danger icon={<ClearOutlined />} onClick={handleClear}>
            清空
          </Button>
          <Button onClick={() => setShowConfig(!showConfig)}>
            {showConfig ? '隐藏配置' : '显示配置'}
          </Button>
        </Space>
      </div>

      {/* 主编辑区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 节点面板 */}
        <div className="flex-shrink-0">
          <ReactFlowWrapper>
            <NodePalette onNodeAdd={handleAddNode} />
          </ReactFlowWrapper>
        </div>

        {/* 流程图画布 */}
        <div className="flex-1 bg-gray-100">
          <ReactFlowWrapper>
            <FlowCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onNodeSelect={(node) => setSelectedNode(node)}
            />
          </ReactFlowWrapper>
        </div>

        {/* 配置面板 */}
        {showConfig && (
          <div className="flex-shrink-0">
            <ReactFlowWrapper>
              <NodeConfigPanel
                node={selectedNode}
                onNodeUpdate={handleNodeUpdate}
                onClose={() => setSelectedNode(null)}
              />
            </ReactFlowWrapper>
          </div>
        )}
      </div>
    </div>
  );
}

// 用于包装需要 ReactFlowProvider 的组件
function ReactFlowWrapper({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export default WorkflowEditorPage;
