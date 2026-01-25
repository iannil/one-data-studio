/**
 * ONE-DATA-STUDIO Workflow Version History Component
 * Sprint 32: Developer Experience Optimization
 *
 * Displays workflow version history with diff comparison and rollback capabilities.
 */

import { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  List,
  Button,
  Modal,
  Tag,
  Tooltip,
  Spin,
  Alert,
  Tabs,
  Badge,
  Space,
  message,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  DiffOutlined,
  PlusOutlined,
  MinusOutlined,
  EditOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Title } = Typography;
const { TabPane } = Tabs;

// Types
interface WorkflowVersion {
  id: number;
  workflow_id: string;
  version_number: number;
  content_hash: string;
  created_at: string;
  created_by: string;
  comment: string;
  parent_version: number | null;
}

interface NodeChange {
  node_id: string;
  node_type: string;
  change_type: 'added' | 'removed' | 'modified' | 'unchanged';
  old_config?: Record<string, unknown>;
  new_config?: Record<string, unknown>;
  field_changes: Array<{
    field: string;
    old_value: unknown;
    new_value: unknown;
  }>;
}

interface EdgeChange {
  source_id: string;
  target_id: string;
  change_type: 'added' | 'removed' | 'modified';
}

interface WorkflowDiff {
  old_version: number;
  new_version: number;
  timestamp: string;
  node_changes: NodeChange[];
  edge_changes: EdgeChange[];
  metadata_changes: Record<string, { old: unknown; new: unknown }>;
  summary: string;
  has_changes: boolean;
  change_count: number;
}

interface VersionHistoryProps {
  workflowId: string;
  currentVersion?: number;
  onRollback?: (version: number) => void;
}

// API functions (to be connected to actual API)
const api = {
  getVersionHistory: async (workflowId: string): Promise<WorkflowVersion[]> => {
    const response = await fetch(`/api/v1/workflows/${workflowId}/versions`);
    if (!response.ok) throw new Error('Failed to fetch version history');
    return response.json();
  },

  compareVersions: async (
    workflowId: string,
    oldVersion: number,
    newVersion: number
  ): Promise<WorkflowDiff> => {
    const response = await fetch(
      `/api/v1/workflows/${workflowId}/versions/compare?old=${oldVersion}&new=${newVersion}`
    );
    if (!response.ok) throw new Error('Failed to compare versions');
    return response.json();
  },

  rollbackVersion: async (
    workflowId: string,
    targetVersion: number
  ): Promise<WorkflowVersion> => {
    const response = await fetch(
      `/api/v1/workflows/${workflowId}/rollback`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: targetVersion }),
      }
    );
    if (!response.ok) throw new Error('Failed to rollback');
    return response.json();
  },

  getTextDiff: async (
    workflowId: string,
    oldVersion: number,
    newVersion: number
  ): Promise<string> => {
    const response = await fetch(
      `/api/v1/workflows/${workflowId}/versions/diff?old=${oldVersion}&new=${newVersion}`
    );
    if (!response.ok) throw new Error('Failed to get diff');
    return response.text();
  },
};

// Helper components
const ChangeTypeBadge: React.FC<{ type: string }> = ({ type }) => {
  const colors: Record<string, string> = {
    added: 'success',
    removed: 'error',
    modified: 'warning',
    unchanged: 'default',
  };

  const icons: Record<string, React.ReactNode> = {
    added: <PlusOutlined />,
    removed: <MinusOutlined />,
    modified: <EditOutlined />,
  };

  return (
    <Tag icon={icons[type]} color={colors[type] || 'default'}>
      {type}
    </Tag>
  );
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return formatDate(dateString);
};

// Main component
export const VersionHistory: React.FC<VersionHistoryProps> = ({
  workflowId,
  currentVersion,
  onRollback,
}) => {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<WorkflowVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersions, setSelectedVersions] = useState<number[]>([]);
  const [diffDialogOpen, setDiffDialogOpen] = useState(false);
  const [diff, setDiff] = useState<WorkflowDiff | null>(null);
  const [textDiff, setTextDiff] = useState<string>('');
  const [diffTab, setDiffTab] = useState('nodes');
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<number | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  // Load version history
  useEffect(() => {
    const loadVersions = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getVersionHistory(workflowId);
        setVersions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load versions');
      } finally {
        setLoading(false);
      }
    };

    loadVersions();
  }, [workflowId]);

  // Handle version selection for comparison
  const handleVersionSelect = (versionNumber: number) => {
    setSelectedVersions((prev) => {
      if (prev.includes(versionNumber)) {
        return prev.filter((v) => v !== versionNumber);
      }
      if (prev.length < 2) {
        return [...prev, versionNumber].sort((a, b) => a - b);
      }
      return [prev[1], versionNumber].sort((a, b) => a - b);
    });
  };

  // Compare selected versions
  const handleCompare = async () => {
    if (selectedVersions.length !== 2) return;

    try {
      setDiffDialogOpen(true);
      const [oldVersion, newVersion] = selectedVersions;

      const [diffData, textDiffData] = await Promise.all([
        api.compareVersions(workflowId, oldVersion, newVersion),
        api.getTextDiff(workflowId, oldVersion, newVersion),
      ]);

      setDiff(diffData);
      setTextDiff(textDiffData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare versions');
      setDiffDialogOpen(false);
    }
  };

  // Handle rollback
  const handleRollback = async () => {
    if (rollbackTarget === null) return;

    try {
      setRollbackLoading(true);
      const newVersion = await api.rollbackVersion(workflowId, rollbackTarget);
      setVersions((prev) => [newVersion, ...prev]);
      setRollbackDialogOpen(false);
      onRollback?.(rollbackTarget);
      message.success(t('workflow.rollbackSuccess', 'Rollback successful'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
      message.error(t('workflow.rollbackFailed', 'Rollback failed'));
    } finally {
      setRollbackLoading(false);
      setRollbackTarget(null);
    }
  };

  // Copy hash to clipboard
  const handleCopyHash = async (hash: string) => {
    await navigator.clipboard.writeText(hash);
    message.success(t('workflow.hashCopied', 'Hash copied'));
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <HistoryOutlined />
          {t('workflow.versionHistory', 'Version History')}
        </Title>

        {selectedVersions.length === 2 && (
          <Button
            type="primary"
            icon={<DiffOutlined />}
            onClick={handleCompare}
            size="small"
          >
            {t('workflow.compare', 'Compare')} v{selectedVersions[0]} ↔ v{selectedVersions[1]}
          </Button>
        )}
      </div>

      {error && (
        <Alert
          type="error"
          message={error}
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <List
        dataSource={versions}
        renderItem={(version) => (
          <List.Item
            style={{
              backgroundColor: selectedVersions.includes(version.version_number)
                ? '#e6f7ff'
                : currentVersion === version.version_number
                ? '#f6ffed'
                : 'transparent',
              borderRadius: 4,
              cursor: 'pointer',
              padding: '12px 16px',
            }}
            onClick={() => handleVersionSelect(version.version_number)}
            actions={[
              currentVersion !== version.version_number && (
                <Tooltip key="rollback" title={t('workflow.rollback', 'Rollback to this version')}>
                  <Button
                    type="text"
                    icon={<RollbackOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      setRollbackTarget(version.version_number);
                      setRollbackDialogOpen(true);
                    }}
                  />
                </Tooltip>
              ),
            ].filter(Boolean)}
          >
            <List.Item.Meta
              avatar={
                <Badge count={currentVersion === version.version_number ? '✓' : null}>
                  <Tag color={currentVersion === version.version_number ? 'blue' : 'default'}>
                    v{version.version_number}
                  </Tag>
                </Badge>
              }
              title={
                <Space>
                  <Text>{version.comment || `Version ${version.version_number}`}</Text>
                  <Tooltip title={t('workflow.copyHash', 'Copy hash')}>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopyHash(version.content_hash);
                      }}
                    />
                  </Tooltip>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {version.content_hash.substring(0, 8)}
                  </Text>
                </Space>
              }
              description={
                <Space>
                  <Space size={4}>
                    <UserOutlined style={{ color: '#999' }} />
                    <Text type="secondary">{version.created_by}</Text>
                  </Space>
                  <Space size={4}>
                    <ClockCircleOutlined style={{ color: '#999' }} />
                    <Tooltip title={formatDate(version.created_at)}>
                      <Text type="secondary">{formatRelativeTime(version.created_at)}</Text>
                    </Tooltip>
                  </Space>
                </Space>
              }
            />
          </List.Item>
        )}
      />

      {versions.length === 0 && (
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 32 }}>
          {t('workflow.noVersions', 'No version history available')}
        </Text>
      )}

      {/* Diff Dialog */}
      <Modal
        title={`${t('workflow.versionComparison', 'Version Comparison')}: v${selectedVersions[0]} → v${selectedVersions[1]}`}
        open={diffDialogOpen}
        onCancel={() => setDiffDialogOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDiffDialogOpen(false)}>
            {t('common.close', 'Close')}
          </Button>,
        ]}
        width={800}
      >
        {diff && (
          <>
            <Alert
              type={diff.has_changes ? 'info' : 'success'}
              message={diff.summary}
              style={{ marginBottom: 16 }}
            />

            <Tabs activeKey={diffTab} onChange={setDiffTab}>
              <TabPane
                tab={
                  <Badge count={diff.node_changes.length}>
                    {t('workflow.nodeChanges', 'Node Changes')}
                  </Badge>
                }
                key="nodes"
              >
                <List
                  size="small"
                  dataSource={diff.node_changes}
                  renderItem={(change, i) => (
                    <List.Item key={i}>
                      <List.Item.Meta
                        avatar={<ChangeTypeBadge type={change.change_type} />}
                        title={`${change.node_type} (${change.node_id})`}
                        description={
                          change.field_changes.length > 0 && (
                            <div style={{ marginTop: 8 }}>
                              {change.field_changes.map((fc, j) => (
                                <div key={j} style={{ fontSize: 12 }}>
                                  <strong>{fc.field}:</strong>{' '}
                                  <span style={{ color: 'red' }}>
                                    {JSON.stringify(fc.old_value)}
                                  </span>{' '}
                                  →{' '}
                                  <span style={{ color: 'green' }}>
                                    {JSON.stringify(fc.new_value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )
                        }
                      />
                    </List.Item>
                  )}
                  locale={{
                    emptyText: t('workflow.noNodeChanges', 'No node changes'),
                  }}
                />
              </TabPane>

              <TabPane
                tab={
                  <Badge count={diff.edge_changes.length}>
                    {t('workflow.edgeChanges', 'Edge Changes')}
                  </Badge>
                }
                key="edges"
              >
                <List
                  size="small"
                  dataSource={diff.edge_changes}
                  renderItem={(change, i) => (
                    <List.Item key={i}>
                      <List.Item.Meta
                        avatar={<ChangeTypeBadge type={change.change_type} />}
                        title={`${change.source_id} → ${change.target_id}`}
                      />
                    </List.Item>
                  )}
                  locale={{
                    emptyText: t('workflow.noEdgeChanges', 'No edge changes'),
                  }}
                />
              </TabPane>

              <TabPane
                tab={
                  <Space>
                    <CodeOutlined />
                    {t('workflow.rawDiff', 'Raw Diff')}
                  </Space>
                }
                key="raw"
              >
                <pre
                  style={{
                    padding: 16,
                    backgroundColor: '#1a1a1a',
                    color: '#e0e0e0',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                    overflow: 'auto',
                    maxHeight: 400,
                    borderRadius: 4,
                  }}
                >
                  {textDiff || 'No differences'}
                </pre>
              </TabPane>
            </Tabs>
          </>
        )}
      </Modal>

      {/* Rollback Confirmation Dialog */}
      <Modal
        title={t('workflow.confirmRollback', 'Confirm Rollback')}
        open={rollbackDialogOpen}
        onCancel={() => setRollbackDialogOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setRollbackDialogOpen(false)} disabled={rollbackLoading}>
            {t('common.cancel', 'Cancel')}
          </Button>,
          <Button
            key="rollback"
            type="primary"
            onClick={handleRollback}
            loading={rollbackLoading}
            icon={<RollbackOutlined />}
          >
            {t('workflow.rollback', 'Rollback')}
          </Button>,
        ]}
      >
        <Text>
          {t(
            'workflow.rollbackWarning',
            `Are you sure you want to rollback to version ${rollbackTarget}? This will create a new version with the content from version ${rollbackTarget}.`
          )}
        </Text>
      </Modal>
    </Card>
  );
};

export default VersionHistory;
