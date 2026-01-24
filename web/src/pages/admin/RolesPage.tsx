import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormGroup,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Security as SecurityIcon,
  Person as PersonIcon,
  Shield as ShieldIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

// Types
interface Permission {
  id: string;
  name: string;
  displayName: string;
  resource: string;
  operation: string;
  scope: string;
  isSystem: boolean;
}

interface Role {
  id: string;
  name: string;
  displayName: string;
  description: string;
  roleType: 'system' | 'custom';
  tenantId: string | null;
  parentRoleId: string | null;
  isActive: boolean;
  isSystem: boolean;
  priority: number;
  permissions: Permission[];
  createdAt: string;
  updatedAt: string;
}

// Available resources and operations
const RESOURCES = [
  { value: 'dataset', label: 'Dataset' },
  { value: 'workflow', label: 'Workflow' },
  { value: 'chat', label: 'Chat' },
  { value: 'model', label: 'Model' },
  { value: 'user', label: 'User' },
  { value: 'system', label: 'System' },
  { value: 'role', label: 'Role' },
];

const OPERATIONS = [
  { value: 'create', label: 'Create' },
  { value: 'read', label: 'Read' },
  { value: 'update', label: 'Update' },
  { value: 'delete', label: 'Delete' },
  { value: 'execute', label: 'Execute' },
  { value: 'manage', label: 'Manage' },
];

// API functions
const api = {
  async getRoles(): Promise<Role[]> {
    const response = await fetch('/api/v1/admin/roles');
    if (!response.ok) throw new Error('Failed to fetch roles');
    const data = await response.json();
    return data.roles || [];
  },

  async getPermissions(): Promise<Permission[]> {
    const response = await fetch('/api/v1/admin/permissions');
    if (!response.ok) throw new Error('Failed to fetch permissions');
    const data = await response.json();
    return data.permissions || [];
  },

  async createRole(role: Partial<Role>): Promise<Role> {
    const response = await fetch('/api/v1/admin/roles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(role),
    });
    if (!response.ok) throw new Error('Failed to create role');
    return response.json();
  },

  async updateRole(roleId: string, updates: Partial<Role>): Promise<Role> {
    const response = await fetch(`/api/v1/admin/roles/${roleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update role');
    return response.json();
  },

  async deleteRole(roleId: string): Promise<void> {
    const response = await fetch(`/api/v1/admin/roles/${roleId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete role');
  },

  async addPermissionToRole(roleId: string, permission: string): Promise<void> {
    const response = await fetch(`/api/v1/admin/roles/${roleId}/permissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ permission }),
    });
    if (!response.ok) throw new Error('Failed to add permission');
  },

  async removePermissionFromRole(roleId: string, permission: string): Promise<void> {
    const response = await fetch(`/api/v1/admin/roles/${roleId}/permissions/${permission}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to remove permission');
  },
};

// Role Dialog Component
interface RoleDialogProps {
  open: boolean;
  role: Role | null;
  roles: Role[];
  permissions: Permission[];
  onClose: () => void;
  onSave: (role: Partial<Role>) => Promise<void>;
}

const RoleDialog: React.FC<RoleDialogProps> = ({
  open,
  role,
  roles,
  permissions,
  onClose,
  onSave,
}) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    name: '',
    displayName: '',
    description: '',
    parentRoleId: '',
    permissions: [] as string[],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (role) {
      setFormData({
        name: role.name,
        displayName: role.displayName,
        description: role.description || '',
        parentRoleId: role.parentRoleId || '',
        permissions: role.permissions.map((p) => `${p.resource}:${p.operation}`),
      });
    } else {
      setFormData({
        name: '',
        displayName: '',
        description: '',
        parentRoleId: '',
        permissions: [],
      });
    }
    setError(null);
  }, [role, open]);

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('Role name is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await onSave({
        ...formData,
        parentRoleId: formData.parentRoleId || null,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save role');
    } finally {
      setSaving(false);
    }
  };

  const handlePermissionToggle = (permission: string) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter((p) => p !== permission)
        : [...prev.permissions, permission],
    }));
  };

  // Group permissions by resource
  const permissionsByResource = permissions.reduce(
    (acc, perm) => {
      if (!acc[perm.resource]) {
        acc[perm.resource] = [];
      }
      acc[perm.resource].push(perm);
      return acc;
    },
    {} as Record<string, Permission[]>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {role ? t('admin.editRole') : t('admin.createRole')}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label={t('admin.roleName')}
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            disabled={role?.isSystem}
            required
            fullWidth
          />

          <TextField
            label={t('admin.displayName')}
            value={formData.displayName}
            onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
            fullWidth
          />

          <TextField
            label={t('admin.description')}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            multiline
            rows={2}
            fullWidth
          />

          <FormControl fullWidth>
            <InputLabel>{t('admin.parentRole')}</InputLabel>
            <Select
              value={formData.parentRoleId}
              onChange={(e) => setFormData({ ...formData, parentRoleId: e.target.value })}
              label={t('admin.parentRole')}
            >
              <MenuItem value="">
                <em>{t('common.none')}</em>
              </MenuItem>
              {roles
                .filter((r) => r.id !== role?.id)
                .map((r) => (
                  <MenuItem key={r.id} value={r.id}>
                    {r.displayName}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>

          <Typography variant="subtitle1" sx={{ mt: 2 }}>
            {t('admin.permissions')}
          </Typography>

          {Object.entries(permissionsByResource).map(([resource, perms]) => (
            <Card key={resource} variant="outlined" sx={{ p: 1 }}>
              <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
                {resource.charAt(0).toUpperCase() + resource.slice(1)}
              </Typography>
              <FormGroup row>
                {perms.map((perm) => {
                  const permKey = `${perm.resource}:${perm.operation}`;
                  return (
                    <FormControlLabel
                      key={perm.id}
                      control={
                        <Checkbox
                          checked={formData.permissions.includes(permKey)}
                          onChange={() => handlePermissionToggle(permKey)}
                          disabled={role?.isSystem}
                        />
                      }
                      label={perm.operation}
                    />
                  );
                })}
              </FormGroup>
            </Card>
          ))}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('common.cancel')}</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || role?.isSystem}
          startIcon={saving ? <CircularProgress size={20} /> : null}
        >
          {t('common.save')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// Main Roles Page Component
const RolesPage: React.FC = () => {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState<Role | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rolesData, permissionsData] = await Promise.all([
        api.getRoles(),
        api.getPermissions(),
      ]);
      setRoles(rolesData);
      setPermissions(permissionsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateRole = () => {
    setEditingRole(null);
    setDialogOpen(true);
  };

  const handleEditRole = (role: Role) => {
    setEditingRole(role);
    setDialogOpen(true);
  };

  const handleDeleteClick = (role: Role) => {
    setRoleToDelete(role);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!roleToDelete) return;

    try {
      await api.deleteRole(roleToDelete.id);
      setRoles((prev) => prev.filter((r) => r.id !== roleToDelete.id));
      setDeleteConfirmOpen(false);
      setRoleToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete role');
    }
  };

  const handleSaveRole = async (roleData: Partial<Role>) => {
    if (editingRole) {
      const updated = await api.updateRole(editingRole.id, roleData);
      setRoles((prev) =>
        prev.map((r) => (r.id === editingRole.id ? updated : r))
      );
    } else {
      const created = await api.createRole(roleData);
      setRoles((prev) => [...prev, created]);
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Typography variant="h5" component="h1">
          <SecurityIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          {t('admin.rolesManagement')}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateRole}
        >
          {t('admin.createRole')}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{t('admin.roleName')}</TableCell>
              <TableCell>{t('admin.type')}</TableCell>
              <TableCell>{t('admin.permissions')}</TableCell>
              <TableCell>{t('admin.status')}</TableCell>
              <TableCell align="right">{t('common.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {roles.map((role) => (
              <TableRow key={role.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {role.isSystem ? (
                      <ShieldIcon color="primary" fontSize="small" />
                    ) : (
                      <PersonIcon color="action" fontSize="small" />
                    )}
                    <Box>
                      <Typography variant="body1">{role.displayName}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {role.name}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={role.roleType}
                    size="small"
                    color={role.isSystem ? 'primary' : 'default'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {role.permissions.slice(0, 3).map((perm) => (
                      <Chip
                        key={perm.id}
                        label={`${perm.resource}:${perm.operation}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                    {role.permissions.length > 3 && (
                      <Tooltip
                        title={role.permissions
                          .slice(3)
                          .map((p) => `${p.resource}:${p.operation}`)
                          .join(', ')}
                      >
                        <Chip
                          label={`+${role.permissions.length - 3}`}
                          size="small"
                        />
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={role.isActive ? t('common.active') : t('common.inactive')}
                    size="small"
                    color={role.isActive ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title={t('common.edit')}>
                    <IconButton
                      onClick={() => handleEditRole(role)}
                      size="small"
                    >
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  {!role.isSystem && (
                    <Tooltip title={t('common.delete')}>
                      <IconButton
                        onClick={() => handleDeleteClick(role)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Role Dialog */}
      <RoleDialog
        open={dialogOpen}
        role={editingRole}
        roles={roles}
        permissions={permissions}
        onClose={() => setDialogOpen(false)}
        onSave={handleSaveRole}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>{t('admin.deleteRole')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t('admin.deleteRoleConfirmation', { name: roleToDelete?.displayName })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            {t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RolesPage;
