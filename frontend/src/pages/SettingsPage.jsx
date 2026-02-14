import { useEffect, useState, useCallback } from 'react';
import { categoryAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { Plus, Pencil, Trash2, Tag, FolderKanban, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editCat, setEditCat] = useState(null);
  const [form, setForm] = useState({ name: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const loadCategories = useCallback(async () => {
    try {
      const res = await categoryAPI.listAll();
      setCategories(res.data.categories);
    } catch (err) {
      console.error('Failed to load categories:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCategories(); }, [loadCategories]);

  const resetForm = () => { setForm({ name: '', description: '' }); setEditCat(null); };

  const openCreate = () => { resetForm(); setShowDialog(true); };

  const openEdit = (cat) => {
    setEditCat(cat);
    setForm({ name: cat.name, description: cat.description || '' });
    setShowDialog(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error('Category name is required');
      return;
    }
    setSaving(true);
    try {
      if (editCat) {
        await categoryAPI.update(editCat.id, { name: form.name.trim(), description: form.description.trim() || null });
        toast.success('Category updated');
      } else {
        await categoryAPI.create({ name: form.name.trim(), description: form.description.trim() || null });
        toast.success('Category created');
      }
      setShowDialog(false);
      resetForm();
      loadCategories();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save category');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await categoryAPI.delete(deleteTarget.id);
      toast.success('Category deleted');
      setDeleteTarget(null);
      loadCategories();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete category');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-slate-100 rounded w-40" />
          <div className="h-64 bg-slate-100 rounded-lg" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8" data-testid="settings-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Settings
          </h1>
          <p className="text-muted-foreground mt-1">Manage categories and platform settings</p>
        </div>

        <Separator />

        {/* Categories Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-medium tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Categories
              </h2>
              <p className="text-sm text-muted-foreground mt-1">Manage project categories. Categories used by projects cannot be deleted.</p>
            </div>
            <Button
              onClick={openCreate}
              className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
              data-testid="add-category-btn"
            >
              <Plus className="w-4 h-4 mr-2" /> Add Category
            </Button>
          </div>

          {/* Categories Table */}
          <Card className="border border-border bg-white shadow-sm">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="categories-table">
                  <thead>
                    <tr className="border-b border-border bg-slate-50/80">
                      <th className="text-left px-5 py-3 table-header">Name</th>
                      <th className="text-left px-5 py-3 table-header">Description</th>
                      <th className="text-left px-5 py-3 table-header">Status</th>
                      <th className="text-left px-5 py-3 table-header">Projects</th>
                      <th className="text-right px-5 py-3 table-header">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {categories.map((cat) => {
                      const inUse = cat.project_count > 0;
                      return (
                        <tr key={cat.id} className="border-b border-border/50 hover:bg-slate-50/50 transition-colors" data-testid={`category-row-${cat.id}`}>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <Tag className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                              <span className="font-medium text-foreground">{cat.name}</span>
                            </div>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground text-sm max-w-xs truncate">
                            {cat.description || '—'}
                          </td>
                          <td className="px-5 py-4">
                            <Badge className={cat.is_active ? 'status-active' : 'status-disabled'}>
                              {cat.is_active ? 'active' : 'inactive'}
                            </Badge>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-1.5">
                              <FolderKanban className="w-3.5 h-3.5 text-muted-foreground" />
                              <span className="font-mono text-sm" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                                {cat.project_count}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEdit(cat)}
                                data-testid={`edit-category-${cat.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className={inUse ? 'text-muted-foreground cursor-not-allowed opacity-40' : 'text-destructive hover:text-destructive'}
                                        disabled={inUse}
                                        onClick={() => !inUse && setDeleteTarget(cat)}
                                        data-testid={`delete-category-${cat.id}`}
                                      >
                                        <Trash2 className="w-4 h-4" />
                                      </Button>
                                    </span>
                                  </TooltipTrigger>
                                  {inUse && (
                                    <TooltipContent>
                                      <p>Cannot delete: used by {cat.project_count} project(s)</p>
                                    </TooltipContent>
                                  )}
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {categories.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-5 py-10 text-center text-muted-foreground">
                          No categories found. Add one to get started.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
          <DialogContent data-testid="category-dialog">
            <DialogHeader>
              <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                {editCat ? 'Edit Category' : 'New Category'}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="label-caps">Category Name</Label>
                <Input
                  placeholder="e.g. E-Commerce"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  data-testid="category-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Description (optional)</Label>
                <Input
                  placeholder="Brief description of this category"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  data-testid="category-description-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>Cancel</Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                className="bg-[#0F172A] hover:bg-[#1E293B] text-white"
                data-testid="save-category-btn"
              >
                {saving ? 'Saving...' : editCat ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
          <DialogContent data-testid="delete-category-dialog">
            <DialogHeader>
              <DialogTitle>Delete Category</DialogTitle>
            </DialogHeader>
            <div className="flex gap-3 py-2">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete <strong>"{deleteTarget?.name}"</strong>? This action cannot be undone.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleting}
                data-testid="confirm-delete-category-btn"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
