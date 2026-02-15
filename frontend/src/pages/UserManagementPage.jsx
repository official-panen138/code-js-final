import { useEffect, useState, useCallback } from 'react';
import api from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Checkbox } from '../components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { Users, Shield, Plus, Pencil, Trash2, AlertCircle, Check } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';

export default function UserManagementPage() {
  return (
    <Layout>
      <div className="space-y-8" data-testid="user-management-page">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            User Management
          </h1>
          <p className="text-muted-foreground mt-1">Manage users, roles, and menu permissions</p>
        </div>

        <Tabs defaultValue="users" className="space-y-6">
          <TabsList data-testid="user-mgmt-tabs">
            <TabsTrigger value="users" data-testid="users-tab">
              <Users className="w-4 h-4 mr-2" /> Users
            </TabsTrigger>
            <TabsTrigger value="roles" data-testid="roles-tab">
              <Shield className="w-4 h-4 mr-2" /> Roles & Permissions
            </TabsTrigger>
          </TabsList>

          <TabsContent value="users">
            <UsersSection />
          </TabsContent>
          <TabsContent value="roles">
            <RolesSection />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}


/* ─── Users Section ─── */
function UsersSection() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user: currentUser } = useAuth();

  const loadUsers = useCallback(async () => {
    try {
      const res = await api.get('/users');
      setUsers(res.data.users);
      setRoles(res.data.roles);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const updateRole = async (userId, newRole) => {
    try {
      await api.patch(`/users/${userId}`, { role: newRole });
      toast.success('User role updated');
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const toggleActive = async (userId, isActive) => {
    try {
      await api.patch(`/users/${userId}`, { is_active: !isActive });
      toast.success(isActive ? 'User deactivated' : 'User activated');
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update user');
    }
  };

  if (loading) {
    return <div className="animate-pulse h-64 bg-slate-100 rounded-lg" />;
  }

  return (
    <div className="space-y-4" data-testid="users-section">
      <Card className="border border-border bg-white shadow-sm">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="users-table">
              <thead>
                <tr className="border-b border-border bg-slate-50/80">
                  <th className="text-left px-5 py-3 table-header">Email</th>
                  <th className="text-left px-5 py-3 table-header">Role</th>
                  <th className="text-left px-5 py-3 table-header">Status</th>
                  <th className="text-left px-5 py-3 table-header">Created</th>
                  <th className="text-right px-5 py-3 table-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id} className="border-b border-border/50 hover:bg-slate-50/50 transition-colors" data-testid={`user-row-${u.id}`}>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-medium text-slate-600">
                            {u.email[0].toUpperCase()}
                          </div>
                          <span className="font-medium text-foreground">{u.email}</span>
                          {isSelf && <Badge variant="outline" className="text-xs">You</Badge>}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <Select value={u.role} onValueChange={(val) => updateRole(u.id, val)} disabled={isSelf}>
                          <SelectTrigger className="w-32 h-8" data-testid={`role-select-${u.id}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map(r => (
                              <SelectItem key={r.id} value={r.name}>{r.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="px-5 py-4">
                        <Badge className={u.is_active ? 'status-active' : 'status-disabled'}>
                          {u.is_active ? 'active' : 'inactive'}
                        </Badge>
                      </td>
                      <td className="px-5 py-4 text-xs text-muted-foreground">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span>
                                  <Switch
                                    checked={u.is_active}
                                    onCheckedChange={() => toggleActive(u.id, u.is_active)}
                                    disabled={isSelf}
                                    data-testid={`user-toggle-${u.id}`}
                                  />
                                </span>
                              </TooltipTrigger>
                              {isSelf && (
                                <TooltipContent><p>Cannot deactivate yourself</p></TooltipContent>
                              )}
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


/* ─── Roles Section ─── */
function RolesSection() {
  const [roles, setRoles] = useState([]);
  const [menus, setMenus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editRole, setEditRole] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', permissions: [] });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const { refreshUser } = useAuth();

  const loadRoles = useCallback(async () => {
    try {
      const res = await api.get('/roles');
      setRoles(res.data.roles);
      setMenus(res.data.available_menus);
    } catch (err) {
      console.error('Failed to load roles:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadRoles(); }, [loadRoles]);

  const resetForm = () => { setForm({ name: '', description: '', permissions: [] }); setEditRole(null); };

  const openCreate = () => { resetForm(); setShowDialog(true); };

  const openEdit = (role) => {
    setEditRole(role);
    setForm({ name: role.name, description: role.description || '', permissions: [...(role.permissions || [])] });
    setShowDialog(true);
  };

  const togglePermission = (key) => {
    setForm(prev => ({
      ...prev,
      permissions: prev.permissions.includes(key)
        ? prev.permissions.filter(p => p !== key)
        : [...prev.permissions, key]
    }));
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error('Role name is required');
      return;
    }
    setSaving(true);
    try {
      if (editRole) {
        await api.patch(`/roles/${editRole.id}`, {
          name: form.name.trim().toLowerCase(),
          description: form.description.trim() || null,
          permissions: form.permissions,
        });
        toast.success('Role updated');
      } else {
        await api.post('/roles', {
          name: form.name.trim().toLowerCase(),
          description: form.description.trim() || null,
          permissions: form.permissions,
        });
        toast.success('Role created');
      }
      setShowDialog(false);
      resetForm();
      loadRoles();
      refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save role');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/roles/${deleteTarget.id}`);
      toast.success('Role deleted');
      setDeleteTarget(null);
      loadRoles();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete role');
    }
  };

  if (loading) return <div className="animate-pulse h-64 bg-slate-100 rounded-lg" />;

  return (
    <div className="space-y-4" data-testid="roles-section">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Configure which menus and features each role can access. New menus are automatically available here.
        </p>
        <Button
          onClick={openCreate}
          className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
          data-testid="add-role-btn"
        >
          <Plus className="w-4 h-4 mr-2" /> Add Role
        </Button>
      </div>

      {/* Roles Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {roles.map((role) => (
          <Card key={role.id} className="border border-border bg-white shadow-sm" data-testid={`role-card-${role.id}`}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-base font-medium capitalize">{role.name}</CardTitle>
                  {role.is_system && <Badge variant="outline" className="text-xs">System</Badge>}
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(role)} data-testid={`edit-role-${role.id}`}>
                    <Pencil className="w-4 h-4" />
                  </Button>
                  {!role.is_system && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span>
                            <Button
                              variant="ghost" size="sm"
                              className={role.user_count > 0 ? 'text-muted-foreground opacity-40 cursor-not-allowed' : 'text-destructive'}
                              disabled={role.user_count > 0}
                              onClick={() => role.user_count === 0 && setDeleteTarget(role)}
                              data-testid={`delete-role-${role.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </span>
                        </TooltipTrigger>
                        {role.user_count > 0 && (
                          <TooltipContent><p>Assigned to {role.user_count} user(s)</p></TooltipContent>
                        )}
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
              </div>
              {role.description && <p className="text-xs text-muted-foreground mt-1">{role.description}</p>}
              <p className="text-xs text-muted-foreground">{role.user_count} user(s)</p>
            </CardHeader>
            <Separator />
            <CardContent className="pt-3">
              <p className="label-caps mb-2">Menu Access</p>
              <div className="flex flex-wrap gap-1.5">
                {menus.map(m => {
                  const hasAccess = (role.permissions || []).includes(m.key);
                  return (
                    <Badge
                      key={m.key}
                      variant={hasAccess ? 'default' : 'outline'}
                      className={`text-xs ${hasAccess ? 'bg-[#0F172A] text-white' : 'text-muted-foreground opacity-50'}`}
                    >
                      {hasAccess && <Check className="w-3 h-3 mr-1" />}
                      {m.label}
                    </Badge>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create/Edit Role Dialog */}
      <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-md" data-testid="role-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              {editRole ? 'Edit Role' : 'New Role'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 py-2">
            <div className="space-y-2">
              <Label className="label-caps">Role Name</Label>
              <Input
                placeholder="e.g. editor"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                disabled={editRole?.is_system}
                data-testid="role-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Description</Label>
              <Input
                placeholder="Brief description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                data-testid="role-description-input"
              />
            </div>
            <div className="space-y-3">
              <Label className="label-caps">Menu Permissions</Label>
              <div className="space-y-2">
                {menus.map(m => (
                  <div
                    key={m.key}
                    className="flex items-center justify-between px-3 py-2.5 rounded-md border border-border hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => togglePermission(m.key)}
                    data-testid={`perm-toggle-${m.key}`}
                  >
                    <div>
                      <p className="text-sm font-medium">{m.label}</p>
                      <p className="text-xs text-muted-foreground">{m.description}</p>
                    </div>
                    <Checkbox
                      checked={form.permissions.includes(m.key)}
                      onCheckedChange={() => togglePermission(m.key)}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="save-role-btn">
              {saving ? 'Saving...' : editRole ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Role Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <DialogContent data-testid="delete-role-dialog">
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
          </DialogHeader>
          <div className="flex gap-3 py-2">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-sm text-muted-foreground">
              Delete role <strong>"{deleteTarget?.name}"</strong>? This cannot be undone.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} data-testid="confirm-delete-role-btn">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
