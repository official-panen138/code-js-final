import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectAPI, categoryAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, FileCode, Globe, FolderKanban, Search, Filter, X } from 'lucide-react';
import { toast } from 'sonner';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [newProject, setNewProject] = useState({ name: '', category_id: '' });
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      const [projRes, catRes] = await Promise.all([projectAPI.list(), categoryAPI.list()]);
      setProjects(projRes.data.projects);
      setCategories(catRes.data.categories);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!newProject.name.trim()) {
      toast.error('Project name is required');
      return;
    }
    if (!newProject.category_id) {
      toast.error('Please select a category');
      return;
    }
    setCreating(true);
    try {
      const res = await projectAPI.create({
        name: newProject.name.trim(),
        category_id: parseInt(newProject.category_id),
      });
      toast.success('Project created!');
      setShowCreate(false);
      setNewProject({ name: '', category_id: '' });
      navigate(`/projects/${res.data.project.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  const filtered = projects.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || 
      (p.category && String(p.category.id) === categoryFilter);
    return matchesSearch && matchesCategory;
  });

  // Count projects per category for the filter badges
  const categoryCounts = categories.reduce((acc, cat) => {
    acc[cat.id] = projects.filter(p => p.category && p.category.id === cat.id).length;
    return acc;
  }, {});

  if (loading) {
    return (
      <Layout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-slate-100 rounded w-40" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1,2,3].map(i => <div key={i} className="h-36 bg-slate-100 rounded-lg" />)}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8" data-testid="projects-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Projects
            </h1>
            <p className="text-muted-foreground mt-1">Manage your JavaScript hosting projects</p>
          </div>
          <Button
            onClick={() => setShowCreate(true)}
            className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
            data-testid="create-project-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Project
          </Button>
        </div>

        {/* Search and Filter */}
        {projects.length > 0 && (
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search projects..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="search-projects-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-[180px]" data-testid="category-filter-select">
                  <SelectValue placeholder="Filter by category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" data-testid="filter-all">
                    All Categories ({projects.length})
                  </SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat.id} value={String(cat.id)} data-testid={`filter-category-${cat.id}`}>
                      {cat.name} ({categoryCounts[cat.id] || 0})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {categoryFilter !== 'all' && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setCategoryFilter('all')}
                  className="h-8 w-8"
                  data-testid="clear-filter-btn"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Project Grid */}
        {filtered.length === 0 ? (
          <Card className="border border-dashed border-border bg-white">
            <CardContent className="p-12 text-center">
              <FolderKanban className="w-10 h-10 text-muted-foreground mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-muted-foreground">
                {search ? 'No projects match your search.' : 'No projects yet. Create your first project to get started.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="projects-grid">
            {filtered.map((project) => (
              <Card
                key={project.id}
                className="border border-border bg-white shadow-sm card-interactive cursor-pointer"
                onClick={() => navigate(`/projects/${project.id}`)}
                data-testid={`project-card-${project.id}`}
              >
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-medium text-foreground truncate pr-2">{project.name}</h3>
                    <Badge
                      variant="secondary"
                      className={project.status === 'active' ? 'status-active' : 'status-paused'}
                    >
                      {project.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono mb-3" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    /{project.slug}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileCode className="w-3.5 h-3.5" />{project.script_count || 0} scripts
                    </span>
                    <span className="flex items-center gap-1">
                      <Globe className="w-3.5 h-3.5" />{project.whitelist_count || 0} domains
                    </span>
                  </div>
                  {project.category && (
                    <Badge variant="outline" className="mt-3 text-xs">{project.category.name}</Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Create Dialog */}
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogContent data-testid="create-project-dialog">
            <DialogHeader>
              <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>Create New Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="label-caps">Project Name</Label>
                <Input
                  placeholder="My Awesome Widget"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  data-testid="project-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Category</Label>
                <Select
                  value={newProject.category_id}
                  onValueChange={(val) => setNewProject({ ...newProject, category_id: val })}
                >
                  <SelectTrigger data-testid="project-category-select">
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={String(cat.id)} data-testid={`category-option-${cat.id}`}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreate(false)} data-testid="cancel-create-btn">Cancel</Button>
              <Button
                onClick={handleCreate}
                disabled={creating}
                className="bg-[#0F172A] hover:bg-[#1E293B] text-white"
                data-testid="confirm-create-btn"
              >
                {creating ? 'Creating...' : 'Create Project'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
