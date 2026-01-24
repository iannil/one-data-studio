/**
 * ONE-DATA-STUDIO Workflow Version History Component
 * Sprint 32: Developer Experience Optimization
 *
 * Displays workflow version history with diff comparison and rollback capabilities.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Tooltip,
  Divider,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Stack,
  Badge,
} from '@mui/material';
import {
  History as HistoryIcon,
  Restore as RestoreIcon,
  Compare as CompareIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
  Person as PersonIcon,
  Schedule as ScheduleIcon,
  Code as CodeIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

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
  onVersionSelect?: (version: WorkflowVersion) => void;
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
  const colors: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
    added: 'success',
    removed: 'error',
    modified: 'warning',
    unchanged: 'default',
  };

  const icons: Record<string, React.ReactNode> = {
    added: <AddIcon fontSize="small" />,
    removed: <RemoveIcon fontSize="small" />,
    modified: <EditIcon fontSize="small" />,
  };

  return (
    <Chip
      size="small"
      icon={icons[type] as React.ReactElement}
      label={type}
      color={colors[type] || 'default'}
      sx={{ textTransform: 'capitalize' }}
    />
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
  onVersionSelect,
}) => {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<WorkflowVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersions, setSelectedVersions] = useState<number[]>([]);
  const [diffDialogOpen, setDiffDialogOpen] = useState(false);
  const [diff, setDiff] = useState<WorkflowDiff | null>(null);
  const [textDiff, setTextDiff] = useState<string>('');
  const [diffTab, setDiffTab] = useState(0);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
    } finally {
      setRollbackLoading(false);
      setRollbackTarget(null);
    }
  };

  // Copy hash to clipboard
  const handleCopyHash = async (hash: string) => {
    await navigator.clipboard.writeText(hash);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper elevation={0} sx={{ p: 2 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <HistoryIcon />
          {t('workflow.versionHistory', 'Version History')}
        </Typography>

        {selectedVersions.length === 2 && (
          <Button
            variant="contained"
            startIcon={<CompareIcon />}
            onClick={handleCompare}
            size="small"
          >
            {t('workflow.compare', 'Compare')} v{selectedVersions[0]} ↔ v{selectedVersions[1]}
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <List>
        {versions.map((version, index) => (
          <React.Fragment key={version.id}>
            <ListItem
              sx={{
                bgcolor: selectedVersions.includes(version.version_number)
                  ? 'action.selected'
                  : currentVersion === version.version_number
                  ? 'action.hover'
                  : 'transparent',
                borderRadius: 1,
                cursor: 'pointer',
              }}
              onClick={() => handleVersionSelect(version.version_number)}
            >
              <ListItemIcon>
                <Badge
                  badgeContent={currentVersion === version.version_number ? '✓' : null}
                  color="primary"
                >
                  <Chip
                    label={`v${version.version_number}`}
                    size="small"
                    color={currentVersion === version.version_number ? 'primary' : 'default'}
                  />
                </Badge>
              </ListItemIcon>

              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="body2">
                      {version.comment || `Version ${version.version_number}`}
                    </Typography>
                    <Tooltip title={t('workflow.copyHash', 'Copy hash')}>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyHash(version.content_hash);
                        }}
                      >
                        <CopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Typography variant="caption" color="text.secondary">
                      {version.content_hash}
                    </Typography>
                  </Stack>
                }
                secondary={
                  <Stack direction="row" spacing={2} mt={0.5}>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <PersonIcon fontSize="small" color="action" />
                      <Typography variant="caption">{version.created_by}</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <ScheduleIcon fontSize="small" color="action" />
                      <Tooltip title={formatDate(version.created_at)}>
                        <Typography variant="caption">
                          {formatRelativeTime(version.created_at)}
                        </Typography>
                      </Tooltip>
                    </Box>
                  </Stack>
                }
              />

              <ListItemSecondaryAction>
                {currentVersion !== version.version_number && (
                  <Tooltip title={t('workflow.rollback', 'Rollback to this version')}>
                    <IconButton
                      edge="end"
                      onClick={(e) => {
                        e.stopPropagation();
                        setRollbackTarget(version.version_number);
                        setRollbackDialogOpen(true);
                      }}
                    >
                      <RestoreIcon />
                    </IconButton>
                  </Tooltip>
                )}
              </ListItemSecondaryAction>
            </ListItem>
            {index < versions.length - 1 && <Divider component="li" />}
          </React.Fragment>
        ))}
      </List>

      {versions.length === 0 && (
        <Typography color="text.secondary" textAlign="center" py={4}>
          {t('workflow.noVersions', 'No version history available')}
        </Typography>
      )}

      {/* Diff Dialog */}
      <Dialog
        open={diffDialogOpen}
        onClose={() => setDiffDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {t('workflow.versionComparison', 'Version Comparison')}: v{selectedVersions[0]} → v
          {selectedVersions[1]}
        </DialogTitle>
        <DialogContent>
          {diff && (
            <>
              <Alert severity={diff.has_changes ? 'info' : 'success'} sx={{ mb: 2 }}>
                {diff.summary}
              </Alert>

              <Tabs value={diffTab} onChange={(_, v) => setDiffTab(v)} sx={{ mb: 2 }}>
                <Tab
                  label={
                    <Badge badgeContent={diff.node_changes.length} color="primary">
                      {t('workflow.nodeChanges', 'Node Changes')}
                    </Badge>
                  }
                />
                <Tab
                  label={
                    <Badge badgeContent={diff.edge_changes.length} color="primary">
                      {t('workflow.edgeChanges', 'Edge Changes')}
                    </Badge>
                  }
                />
                <Tab
                  icon={<CodeIcon />}
                  label={t('workflow.rawDiff', 'Raw Diff')}
                />
              </Tabs>

              {diffTab === 0 && (
                <List dense>
                  {diff.node_changes.map((change, i) => (
                    <ListItem key={i}>
                      <ListItemIcon>
                        <ChangeTypeBadge type={change.change_type} />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${change.node_type} (${change.node_id})`}
                        secondary={
                          change.field_changes.length > 0 && (
                            <Stack spacing={0.5} mt={1}>
                              {change.field_changes.map((fc, j) => (
                                <Typography key={j} variant="caption" component="div">
                                  <strong>{fc.field}:</strong>{' '}
                                  <span style={{ color: 'red' }}>
                                    {JSON.stringify(fc.old_value)}
                                  </span>{' '}
                                  →{' '}
                                  <span style={{ color: 'green' }}>
                                    {JSON.stringify(fc.new_value)}
                                  </span>
                                </Typography>
                              ))}
                            </Stack>
                          )
                        }
                      />
                    </ListItem>
                  ))}
                  {diff.node_changes.length === 0 && (
                    <Typography color="text.secondary" textAlign="center" py={2}>
                      {t('workflow.noNodeChanges', 'No node changes')}
                    </Typography>
                  )}
                </List>
              )}

              {diffTab === 1 && (
                <List dense>
                  {diff.edge_changes.map((change, i) => (
                    <ListItem key={i}>
                      <ListItemIcon>
                        <ChangeTypeBadge type={change.change_type} />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${change.source_id} → ${change.target_id}`}
                      />
                    </ListItem>
                  ))}
                  {diff.edge_changes.length === 0 && (
                    <Typography color="text.secondary" textAlign="center" py={2}>
                      {t('workflow.noEdgeChanges', 'No edge changes')}
                    </Typography>
                  )}
                </List>
              )}

              {diffTab === 2 && (
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: 'grey.900',
                    color: 'grey.100',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    whiteSpace: 'pre-wrap',
                    overflow: 'auto',
                    maxHeight: 400,
                  }}
                >
                  {textDiff || 'No differences'}
                </Paper>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDiffDialogOpen(false)}>
            {t('common.close', 'Close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rollback Confirmation Dialog */}
      <Dialog
        open={rollbackDialogOpen}
        onClose={() => setRollbackDialogOpen(false)}
      >
        <DialogTitle>{t('workflow.confirmRollback', 'Confirm Rollback')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t(
              'workflow.rollbackWarning',
              'Are you sure you want to rollback to version {{version}}? This will create a new version with the content from version {{version}}.',
              { version: rollbackTarget }
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRollbackDialogOpen(false)} disabled={rollbackLoading}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleRollback}
            color="primary"
            variant="contained"
            disabled={rollbackLoading}
            startIcon={rollbackLoading ? <CircularProgress size={16} /> : <RestoreIcon />}
          >
            {t('workflow.rollback', 'Rollback')}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default VersionHistory;
