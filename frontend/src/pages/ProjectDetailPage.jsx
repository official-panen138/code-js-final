import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectAPI, scriptAPI, whitelistAPI, logsAPI, analyticsAPI, domainTestAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeft, Copy, Check, Plus, Trash2, Pencil, FileCode, Globe,
  Shield, Activity, ExternalLink, AlertCircle, CheckCircle, XCircle, Search, SaveAll
} from 'lucide-react';
import { toast } from 'sonner';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [scripts, setScripts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [logStats, setLogStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(null);

  const loadProject = useCallback(async () => {
    try {
      const [projRes, scriptRes, logRes, analyticsRes] = await Promise.all([
        projectAPI.get(projectId),
        scriptAPI.list(projectId),
        logsAPI.list(projectId),
        analyticsAPI.get(projectId),
      ]);
      setProject(projRes.data.project);
      setScripts(scriptRes.data.scripts);
      setLogs(logRes.data.logs);
      setLogStats(logRes.data.stats);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      toast.error('Failed to load project');
      navigate('/projects');
    } finally {
      setLoading(false);
    }
  }, [projectId, navigate]);

  useEffect(() => { loadProject(); }, [loadProject]);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(null), 2000);
  };

  const getEmbedUrl = (scriptSlug) => `${BACKEND_URL}/api/js/${project?.slug}/${scriptSlug}.js`;

  if (loading) {
    return (
      <Layout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-slate-100 rounded w-64" />
          <div className="h-48 bg-slate-100 rounded-lg" />
        </div>
      </Layout>
    );
  }

  if (!project) return null;

  return (
    <Layout>
      <div className="space-y-6" data-testid="project-detail-page">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/projects')} data-testid="back-to-projects-btn">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                {project.name}
              </h1>
              <Badge className={project.status === 'active' ? 'status-active' : 'status-paused'} data-testid="project-status-badge">
                {project.status}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground font-mono mt-1" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              slug: {project.slug}
            </p>
          </div>
          <ProjectSettings project={project} onUpdate={loadProject} />
        </div>

        <Separator />

        {/* Tabs */}
        <Tabs defaultValue="scripts" className="space-y-6">
          <TabsList data-testid="project-tabs">
            <TabsTrigger value="scripts" data-testid="scripts-tab">
              <FileCode className="w-4 h-4 mr-2" /> Scripts
            </TabsTrigger>
            <TabsTrigger value="whitelist" data-testid="whitelist-tab">
              <Shield className="w-4 h-4 mr-2" /> Whitelist
            </TabsTrigger>
            <TabsTrigger value="embed" data-testid="embed-tab">
              <ExternalLink className="w-4 h-4 mr-2" /> Embed
            </TabsTrigger>
            <TabsTrigger value="analytics" data-testid="analytics-tab">
              <Activity className="w-4 h-4 mr-2" /> Analytics
            </TabsTrigger>
          </TabsList>

          {/* Scripts Tab */}
          <TabsContent value="scripts">
            <ScriptsTab
              projectId={projectId}
              scripts={scripts}
              onRefresh={loadProject}
              getEmbedUrl={getEmbedUrl}
              copied={copied}
              copyToClipboard={copyToClipboard}
            />
          </TabsContent>

          {/* Whitelist Tab */}
          <TabsContent value="whitelist">
            <WhitelistTab projectId={projectId} whitelists={whitelists} onRefresh={loadProject} />
            <div className="mt-6">
              <DomainTester projectId={projectId} />
            </div>
          </TabsContent>

          {/* Embed Tab */}
          <TabsContent value="embed">
            <EmbedTab 
              project={project} 
              scripts={scripts} 
              getEmbedUrl={getEmbedUrl} 
              copied={copied} 
              copyToClipboard={copyToClipboard} 
            />
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics">
            <AnalyticsTab logs={logs} logStats={logStats} analytics={analytics} projectId={projectId} />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}


/* ─── Project Settings ─── */
function ProjectSettings({ project, onUpdate }) {
  const [showDelete, setShowDelete] = useState(false);
  const navigate = useNavigate();

  const toggleStatus = async () => {
    try {
      const newStatus = project.status === 'active' ? 'paused' : 'active';
      await projectAPI.update(project.id, { status: newStatus });
      toast.success(`Project ${newStatus}`);
      onUpdate();
    } catch (err) {
      toast.error('Failed to update status');
    }
  };

  const handleDelete = async () => {
    try {
      await projectAPI.delete(project.id);
      toast.success('Project deleted');
      navigate('/projects');
    } catch (err) {
      toast.error('Failed to delete project');
    }
  };

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <Label className="text-xs text-muted-foreground">Active</Label>
        <Switch
          checked={project.status === 'active'}
          onCheckedChange={toggleStatus}
          data-testid="project-status-toggle"
        />
      </div>
      <Button variant="outline" size="sm" className="text-destructive border-destructive/30 hover:bg-destructive/10" onClick={() => setShowDelete(true)} data-testid="delete-project-btn">
        <Trash2 className="w-4 h-4" />
      </Button>

      {/* Delete Dialog */}
      <Dialog open={showDelete} onOpenChange={setShowDelete}>
        <DialogContent data-testid="delete-project-dialog">
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete "{project.name}"? This action cannot be undone. All scripts, whitelists, and logs will be permanently removed.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDelete(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} data-testid="confirm-delete-btn">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


/* ─── Scripts Tab ─── */
function ScriptsTab({ projectId, scripts, onRefresh, getEmbedUrl, copied, copyToClipboard }) {
  const [showCreate, setShowCreate] = useState(false);
  const [editScript, setEditScript] = useState(null);
  const [form, setForm] = useState({ name: '', js_code: '', secondary_script_mode: 'js', secondary_script: '', secondary_script_links: [] });
  const [saving, setSaving] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);
  const [showSecondary, setShowSecondary] = useState(false);
  const [secondaryScript, setSecondaryScript] = useState(null);
  const [secondaryMode, setSecondaryMode] = useState('js');
  const [secondaryCode, setSecondaryCode] = useState('');
  const [secondaryLinks, setSecondaryLinks] = useState([]);
  const [savingSecondary, setSavingSecondary] = useState(false);

  const resetForm = () => { 
    setForm({ name: '', js_code: '', secondary_script_mode: 'js', secondary_script: '', secondary_script_links: [] }); 
    setEditScript(null); 
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.js_code.trim()) {
      toast.error('Name and code are required');
      return;
    }
    setSaving(true);
    try {
      if (editScript) {
        await scriptAPI.update(projectId, editScript.id, { name: form.name, js_code: form.js_code });
        toast.success('Script updated');
      } else {
        await scriptAPI.create(projectId, { name: form.name, js_code: form.js_code });
        toast.success('Script created');
      }
      setShowCreate(false);
      resetForm();
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save script');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAsNewVersion = async () => {
    if (!form.name.trim() || !form.js_code.trim()) {
      toast.error('Name and code are required');
      return;
    }
    setSavingVersion(true);
    try {
      const baseName = form.name.replace(/\s*\(v\d+\)$/, '');
      const existingVersions = scripts.filter(s => 
        s.name === baseName || s.name.match(new RegExp(`^${baseName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\(v\\d+\\)$`))
      );
      const nextVersion = existingVersions.length + 1;
      const newName = `${baseName} (v${nextVersion})`;
      
      await scriptAPI.create(projectId, { name: newName, js_code: form.js_code });
      toast.success(`Saved as new version: ${newName}`);
      setShowCreate(false);
      resetForm();
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save new version');
    } finally {
      setSavingVersion(false);
    }
  };

  const handleDelete = async (scriptId) => {
    try {
      await scriptAPI.delete(projectId, scriptId);
      toast.success('Script deleted');
      onRefresh();
    } catch (err) {
      toast.error('Failed to delete script');
    }
  };

  const toggleStatus = async (script) => {
    try {
      const newStatus = script.status === 'active' ? 'disabled' : 'active';
      await scriptAPI.update(projectId, script.id, { status: newStatus });
      toast.success(`Script ${newStatus}`);
      onRefresh();
    } catch (err) {
      toast.error('Failed to update script');
    }
  };

  const openEdit = (script) => {
    setEditScript(script);
    setForm({ name: script.name, js_code: script.js_code });
    setShowCreate(true);
  };

  const openSecondaryDialog = (script) => {
    setSecondaryScript(script);
    setSecondaryMode(script.secondary_script_mode || 'js');
    setSecondaryCode(script.secondary_script || '');
    setSecondaryLinks(script.secondary_script_links || []);
    setShowSecondary(true);
  };

  const handleSaveSecondary = async () => {
    setSavingSecondary(true);
    try {
      const updateData = {
        secondary_script_mode: secondaryMode,
      };
      
      if (secondaryMode === 'js') {
        updateData.secondary_script = secondaryCode;
        updateData.secondary_script_links = [];
      } else {
        updateData.secondary_script = '';
        updateData.secondary_script_links = secondaryLinks.filter(l => l.url && l.keyword);
      }

      await scriptAPI.update(projectId, secondaryScript.id, updateData);
      toast.success('Secondary script settings saved');
      setShowSecondary(false);
      onRefresh();
    } catch (err) {
      toast.error('Failed to save secondary script settings');
    } finally {
      setSavingSecondary(false);
    }
  };

  const addLink = () => {
    setSecondaryLinks([...secondaryLinks, { url: '', keyword: '' }]);
  };

  const removeLink = (index) => {
    setSecondaryLinks(secondaryLinks.filter((_, i) => i !== index));
  };

  const updateLink = (index, field, value) => {
    const updated = [...secondaryLinks];
    updated[index] = { ...updated[index], [field]: value };
    setSecondaryLinks(updated);
  };

  return (
    <div className="space-y-4" data-testid="scripts-section">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-medium tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          Scripts ({scripts.length})
        </h2>
        <Button
          onClick={() => { resetForm(); setShowCreate(true); }}
          className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
          data-testid="add-script-btn"
        >
          <Plus className="w-4 h-4 mr-2" /> Add Script
        </Button>
      </div>

      {scripts.length === 0 ? (
        <Card className="border border-dashed bg-white">
          <CardContent className="p-10 text-center">
            <FileCode className="w-8 h-8 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
            <p className="text-muted-foreground text-sm">No scripts yet. Add your first JavaScript snippet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {scripts.map((script) => (
            <Card key={script.id} className="border border-border bg-white shadow-sm" data-testid={`script-card-${script.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium">{script.name}</h3>
                    <Badge className={script.status === 'active' ? 'status-active' : 'status-disabled'}>
                      {script.status}
                    </Badge>
                    {(script.secondary_script || (script.secondary_script_links && script.secondary_script_links.length > 0)) && (
                      <Badge variant="outline" className="text-xs">
                        {script.secondary_script_mode === 'links' ? 'Links' : 'JS'} Fallback
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={script.status === 'active'}
                      onCheckedChange={() => toggleStatus(script)}
                      data-testid={`script-toggle-${script.id}`}
                    />
                    <Button variant="ghost" size="sm" onClick={() => openSecondaryDialog(script)} data-testid={`secondary-script-${script.id}`} title="Secondary Script">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => openEdit(script)} data-testid={`edit-script-${script.id}`}>
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(script.id)} data-testid={`delete-script-${script.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground font-mono mb-2" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  slug: {script.slug}
                </div>
                <div className="embed-box flex items-center justify-between gap-2 mt-2">
                  <code className="text-xs truncate">&lt;script src="{getEmbedUrl(script.slug)}"&gt;&lt;/script&gt;</code>
                  <Button
                    variant="ghost" size="sm"
                    onClick={() => copyToClipboard(`<script src="${getEmbedUrl(script.slug)}"></script>`, `script-${script.id}`)}
                    data-testid={`copy-embed-${script.id}`}
                  >
                    {copied === `script-${script.id}` ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Script Create/Edit Dialog */}
      <Dialog open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-2xl" data-testid="script-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              {editScript ? 'Edit Script' : 'New Script'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="label-caps">Script Name</Label>
              <Input
                placeholder="e.g. Analytics Tracker"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="script-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="label-caps">JavaScript Code</Label>
              <textarea
                className="code-editor"
                placeholder="// Your JavaScript code here..."
                rows={12}
                value={form.js_code}
                onChange={(e) => setForm({ ...form, js_code: e.target.value })}
                spellCheck={false}
                data-testid="script-code-input"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => { setShowCreate(false); resetForm(); }}>Cancel</Button>
            {editScript && (
              <Button 
                variant="outline" 
                onClick={handleSaveAsNewVersion} 
                disabled={savingVersion || saving}
                className="border-blue-200 text-blue-700 hover:bg-blue-50"
                data-testid="save-as-version-btn"
              >
                <SaveAll className="w-4 h-4 mr-2" />
                {savingVersion ? 'Saving...' : 'Save as New Version'}
              </Button>
            )}
            <Button onClick={handleSave} disabled={saving || savingVersion} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="save-script-btn">
              {saving ? 'Saving...' : editScript ? 'Update Script' : 'Create Script'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Secondary Script Dialog */}
      <Dialog open={showSecondary} onOpenChange={setShowSecondary}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="secondary-script-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Secondary Script - {secondaryScript?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
              <p className="text-sm text-amber-800">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                This content will be served to domains that are <strong>NOT whitelisted</strong>, instead of an empty noop response.
              </p>
            </div>

            {/* Mode Selector */}
            <div className="space-y-2">
              <Label className="label-caps">Mode</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={secondaryMode === 'js' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSecondaryMode('js')}
                  className={secondaryMode === 'js' ? 'bg-[#0F172A] hover:bg-[#1E293B] text-white' : ''}
                  data-testid="mode-js-btn"
                >
                  <FileCode className="w-4 h-4 mr-1" /> Full JS Script
                </Button>
                <Button
                  type="button"
                  variant={secondaryMode === 'links' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSecondaryMode('links')}
                  className={secondaryMode === 'links' ? 'bg-[#0F172A] hover:bg-[#1E293B] text-white' : ''}
                  data-testid="mode-links-btn"
                >
                  <ExternalLink className="w-4 h-4 mr-1" /> Link Injection
                </Button>
              </div>
            </div>

            {/* JS Mode Content */}
            {secondaryMode === 'js' && (
              <div className="space-y-2">
                <Label className="label-caps">JavaScript Code</Label>
                <Textarea
                  value={secondaryCode}
                  onChange={(e) => setSecondaryCode(e.target.value)}
                  placeholder="// JavaScript code for non-whitelisted domains..."
                  rows={12}
                  className="font-mono text-sm"
                  style={{ fontFamily: 'JetBrains Mono, monospace' }}
                  data-testid="secondary-script-input"
                />
                <p className="text-xs text-muted-foreground">Leave empty to serve noop response (default behavior)</p>
              </div>
            )}

            {/* Links Mode Content */}
            {secondaryMode === 'links' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="label-caps">URL / Keyword Pairs</Label>
                  <Button type="button" variant="outline" size="sm" onClick={addLink} data-testid="add-link-btn">
                    <Plus className="w-4 h-4 mr-1" /> Add Link
                  </Button>
                </div>
                
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-xs text-blue-800">
                    Each pair will be injected as: <code className="bg-blue-100 px-1 rounded">&lt;p&gt;&lt;a href="URL"&gt;keyword&lt;/a&gt;&lt;/p&gt;</code> inside a single hidden div
                  </p>
                </div>

                {secondaryLinks.length === 0 ? (
                  <div className="text-center py-6 border border-dashed rounded-lg">
                    <ExternalLink className="w-6 h-6 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
                    <p className="text-sm text-muted-foreground">No links added yet. Click "Add Link" to get started.</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                    {secondaryLinks.map((link, index) => (
                      <div key={index} className="flex gap-2 items-start p-3 bg-slate-50 rounded-lg border" data-testid={`link-entry-${index}`}>
                        <div className="flex-1 space-y-2">
                          <Input
                            placeholder="https://example.com/"
                            value={link.url}
                            onChange={(e) => updateLink(index, 'url', e.target.value)}
                            className="text-sm"
                            data-testid={`link-url-${index}`}
                          />
                          <Input
                            placeholder="keyword"
                            value={link.keyword}
                            onChange={(e) => updateLink(index, 'keyword', e.target.value)}
                            className="text-sm"
                            data-testid={`link-keyword-${index}`}
                          />
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 mt-1"
                          onClick={() => removeLink(index)}
                          data-testid={`remove-link-${index}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  {secondaryLinks.filter(l => l.url && l.keyword).length} valid link{secondaryLinks.filter(l => l.url && l.keyword).length !== 1 ? 's' : ''} will be injected
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSecondary(false)}>Cancel</Button>
            <Button onClick={handleSaveSecondary} disabled={savingSecondary} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="save-secondary-script-btn">
              {savingSecondary ? 'Saving...' : 'Save Settings'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


/* ─── Whitelist Tab ─── */
function WhitelistTab({ projectId, whitelists, onRefresh }) {
  const [newDomain, setNewDomain] = useState('');
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!newDomain.trim()) {
      toast.error('Please enter a domain pattern');
      return;
    }
    setAdding(true);
    try {
      await whitelistAPI.add(projectId, { domain_pattern: newDomain.trim() });
      toast.success('Domain added to whitelist');
      setNewDomain('');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid domain pattern');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await whitelistAPI.delete(projectId, id);
      toast.success('Domain removed');
      onRefresh();
    } catch (err) {
      toast.error('Failed to remove domain');
    }
  };

  const toggleActive = async (entry) => {
    try {
      await whitelistAPI.update(projectId, entry.id, { is_active: !entry.is_active });
      toast.success(entry.is_active ? 'Domain disabled' : 'Domain enabled');
      onRefresh();
    } catch (err) {
      toast.error('Failed to update domain');
    }
  };

  return (
    <div className="space-y-4" data-testid="whitelist-section">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-medium tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          Domain Whitelist ({whitelists.length})
        </h2>
      </div>

      {/* Info box */}
      <Card className="border border-blue-100 bg-blue-50/50">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 space-y-1">
              <p className="font-medium">Domain pattern rules:</p>
              <ul className="list-disc list-inside text-xs space-y-0.5 text-blue-700">
                <li>Exact domain: <code className="bg-blue-100 px-1 rounded">example.com</code></li>
                <li>Wildcard: <code className="bg-blue-100 px-1 rounded">*.example.com</code> (matches sub.example.com)</li>
                <li>No protocol, port, or path (e.g., no https://, no :8080, no /path)</li>
                <li>Empty whitelist = all requests denied</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add domain */}
      <div className="flex gap-3">
        <Input
          placeholder="e.g. example.com or *.example.com"
          value={newDomain}
          onChange={(e) => setNewDomain(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          className="max-w-md"
          data-testid="add-domain-input"
        />
        <Button onClick={handleAdd} disabled={adding} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="add-domain-btn">
          <Plus className="w-4 h-4 mr-2" /> {adding ? 'Adding...' : 'Add Domain'}
        </Button>
      </div>

      {/* Whitelist entries */}
      {whitelists.length === 0 ? (
        <Card className="border border-dashed bg-white">
          <CardContent className="p-10 text-center">
            <Globe className="w-8 h-8 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
            <p className="text-muted-foreground text-sm">
              No domains whitelisted. Scripts will not be served until you add allowed domains.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {whitelists.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center justify-between px-4 py-3 bg-white border border-border rounded-lg"
              data-testid={`whitelist-entry-${entry.id}`}
            >
              <div className="flex items-center gap-3">
                <Globe className="w-4 h-4 text-muted-foreground" />
                <code className="text-sm font-mono" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  {entry.domain_pattern}
                </code>
                {!entry.is_active && (
                  <Badge variant="secondary" className="text-xs text-orange-600 bg-orange-50">disabled</Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={entry.is_active}
                  onCheckedChange={() => toggleActive(entry)}
                  data-testid={`whitelist-toggle-${entry.id}`}
                />
                <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(entry.id)} data-testid={`whitelist-delete-${entry.id}`}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ─── Embed Tab ─── */
/* ─── Embed Tab ─── */
function EmbedTab({ project, scripts, getEmbedUrl, copied, copyToClipboard }) {
  return (
    <div className="space-y-6" data-testid="embed-section">
      <div>
        <h2 className="text-xl font-medium tracking-tight mb-2" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          Embed URLs
        </h2>
        <p className="text-sm text-muted-foreground">
          Copy these embed codes to include your scripts on whitelisted domains.
        </p>
      </div>

      {scripts.length === 0 ? (
        <Card className="border border-dashed bg-white">
          <CardContent className="p-10 text-center">
            <FileCode className="w-8 h-8 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
            <p className="text-muted-foreground text-sm">No scripts to embed. Create a script first.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {scripts.map((script) => {
            const embedTag = `<script src="${getEmbedUrl(script.slug)}"></script>`;
            return (
              <Card key={script.id} className="border border-border bg-white" data-testid={`embed-card-${script.id}`}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{script.name}</h3>
                    <Badge className={script.status === 'active' ? 'status-active' : 'status-disabled'}>
                      {script.status}
                    </Badge>
                  </div>
                  <div className="bg-[#0F172A] rounded-lg p-4 flex items-center justify-between gap-3">
                    <code className="text-sm text-slate-300 break-all" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {embedTag}
                    </code>
                    <Button
                      variant="ghost" size="sm"
                      className="text-slate-400 hover:text-white flex-shrink-0"
                      onClick={() => copyToClipboard(embedTag, `embed-${script.id}`)}
                      data-testid={`copy-embed-full-${script.id}`}
                    >
                      {copied === `embed-${script.id}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Direct URL: <code className="text-xs">{getEmbedUrl(script.slug)}</code>
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}


/* ─── Analytics Tab ─── */
const CHART_COLORS = ['#16A34A', '#DC2626', '#2563EB', '#F59E0B', '#8B5CF6'];

function AnalyticsTab({ logs, logStats, analytics, projectId }) {
  const [blacklisted, setBlacklisted] = useState([]);
  const [loadingBlacklisted, setLoadingBlacklisted] = useState(false);

  useEffect(() => {
    const loadBlacklisted = async () => {
      setLoadingBlacklisted(true);
      try {
        const res = await analyticsAPI.getBlacklistedDomains(projectId);
        setBlacklisted(res.data.blacklisted_domains || []);
      } catch (err) {
        console.error('Failed to load blacklisted domains', err);
      } finally {
        setLoadingBlacklisted(false);
      }
    };
    loadBlacklisted();
  }, [projectId]);

  const pieData = logStats ? [
    { name: 'Allowed', value: logStats.allowed },
    { name: 'Denied', value: logStats.denied },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6" data-testid="analytics-section">
      {/* Summary Stats */}
      {logStats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="border bg-white shadow-sm">
            <CardContent className="p-5 text-center">
              <Activity className="w-5 h-5 text-blue-600 mx-auto mb-2" />
              <p className="text-2xl font-semibold font-mono" style={{ fontFamily: 'JetBrains Mono, monospace' }}>{logStats.total}</p>
              <p className="text-xs text-muted-foreground label-caps mt-1">Total Requests</p>
            </CardContent>
          </Card>
          <Card className="border bg-white shadow-sm">
            <CardContent className="p-5 text-center">
              <CheckCircle className="w-5 h-5 text-green-600 mx-auto mb-2" />
              <p className="text-2xl font-semibold font-mono text-green-700" style={{ fontFamily: 'JetBrains Mono, monospace' }}>{logStats.allowed}</p>
              <p className="text-xs text-muted-foreground label-caps mt-1">Allowed</p>
            </CardContent>
          </Card>
          <Card className="border bg-white shadow-sm">
            <CardContent className="p-5 text-center">
              <XCircle className="w-5 h-5 text-red-600 mx-auto mb-2" />
              <p className="text-2xl font-semibold font-mono text-red-700" style={{ fontFamily: 'JetBrains Mono, monospace' }}>{logStats.denied}</p>
              <p className="text-xs text-muted-foreground label-caps mt-1">Denied</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Row */}
      {logStats && logStats.total > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pie Chart - Allowed vs Denied */}
          {pieData.length > 0 && (
            <Card className="border bg-white shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-medium" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                  Request Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value">
                      {pieData.map((entry, idx) => (
                        <Cell key={idx} fill={CHART_COLORS[idx]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '13px' }}
                      formatter={(value, name) => [`${value} requests`, name]}
                    />
                    <Legend wrapperStyle={{ fontSize: '13px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Bar Chart - Daily Requests */}
          {analytics?.daily?.length > 0 && (
            <Card className="border bg-white shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-medium" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                  Daily Requests
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={analytics.daily}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11 }} tickLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '13px' }} />
                    <Bar dataKey="allowed" stackId="a" fill="#16A34A" radius={[0, 0, 0, 0]} name="Allowed" />
                    <Bar dataKey="denied" stackId="a" fill="#DC2626" radius={[4, 4, 0, 0]} name="Denied" />
                    <Legend wrapperStyle={{ fontSize: '13px' }} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Top Domains */}
      {analytics?.top_domains?.length > 0 && (
        <Card className="border bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-medium" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Top Domains
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(180, analytics.top_domains.length * 36)}>
              <BarChart data={analytics.top_domains} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis type="number" tick={{ fontSize: 11 }} tickLine={false} allowDecimals={false} />
                <YAxis type="category" dataKey="domain" tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }} width={150} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '13px' }} />
                <Bar dataKey="allowed" stackId="a" fill="#16A34A" name="Allowed" />
                <Bar dataKey="denied" stackId="a" fill="#DC2626" name="Denied" />
                <Legend wrapperStyle={{ fontSize: '13px' }} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Blacklisted Domains (non-whitelisted) */}
      <Card className="border bg-white shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-medium flex items-center gap-2" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            <XCircle className="w-4 h-4 text-red-600" /> Blacklisted Domains
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Domains that tried to access your scripts but were denied (not whitelisted)
          </p>
        </CardHeader>
        <CardContent>
          {loadingBlacklisted ? (
            <div className="text-center py-6">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-slate-900 mx-auto" />
            </div>
          ) : blacklisted.length === 0 ? (
            <div className="text-center py-6">
              <Shield className="w-8 h-8 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
              <p className="text-muted-foreground text-sm">No denied requests detected yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="blacklisted-domains-table">
                <thead>
                  <tr className="border-b border-border bg-slate-50/80">
                    <th className="text-left px-4 py-3 table-header">Domain</th>
                    <th className="text-left px-4 py-3 table-header">Requests</th>
                    <th className="text-left px-4 py-3 table-header">Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {blacklisted.map((item, idx) => (
                    <tr key={idx} className="border-b border-border/50 hover:bg-red-50/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                        <div className="flex items-center gap-2">
                          <XCircle className="w-3 h-3 text-red-500" />
                          {item.domain}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-red-700" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                        {item.request_count}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {item.last_seen ? new Date(item.last_seen).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Logs table */}
      <div>
        <h2 className="text-xl font-medium tracking-tight mb-4" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          Access Logs
        </h2>
        {logs.length === 0 ? (
          <Card className="border border-dashed bg-white">
            <CardContent className="p-10 text-center">
              <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2" strokeWidth={1.5} />
              <p className="text-muted-foreground text-sm">No access logs yet. Logs appear when someone requests your scripts.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto border border-border rounded-lg bg-white">
            <table className="w-full text-sm" data-testid="access-logs-table">
              <thead>
                <tr className="border-b border-border bg-slate-50/80">
                  <th className="text-left px-4 py-3 table-header">Domain</th>
                  <th className="text-left px-4 py-3 table-header">Status</th>
                  <th className="text-left px-4 py-3 table-header">IP</th>
                  <th className="text-left px-4 py-3 table-header">Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-border/50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {log.ref_domain || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={log.allowed ? 'status-active' : 'status-disabled'}>
                        {log.allowed ? 'Allowed' : 'Denied'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {log.ip || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


/* ─── Domain Tester ─── */
function DomainTester({ projectId }) {
  const [testDomain, setTestDomain] = useState('');
  const [result, setResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    if (!testDomain.trim()) {
      toast.error('Enter a domain to test');
      return;
    }
    setTesting(true);
    setResult(null);
    try {
      const res = await domainTestAPI.test(projectId, testDomain.trim());
      setResult(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Test failed');
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card className="border border-border bg-white shadow-sm" data-testid="domain-tester">
      <CardHeader>
        <CardTitle className="text-base font-medium flex items-center gap-2" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          <Search className="w-4 h-4 text-[#2563EB]" />
          Domain Tester
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Test if a domain would be allowed by this project's current whitelist.
        </p>
        <div className="flex gap-3">
          <Input
            placeholder="e.g. sub.example.com or https://mysite.com/page"
            value={testDomain}
            onChange={(e) => { setTestDomain(e.target.value); setResult(null); }}
            onKeyDown={(e) => e.key === 'Enter' && handleTest()}
            className="max-w-md"
            data-testid="domain-tester-input"
          />
          <Button
            onClick={handleTest}
            disabled={testing}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white"
            data-testid="domain-tester-btn"
          >
            {testing ? 'Testing...' : 'Test'}
          </Button>
        </div>
        {result && (
          <div
            className={`flex items-start gap-3 p-4 rounded-lg border ${
              result.allowed
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}
            data-testid="domain-tester-result"
          >
            {result.allowed ? (
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="space-y-1">
              <p className={`text-sm font-medium ${result.allowed ? 'text-green-800' : 'text-red-800'}`}>
                {result.allowed ? 'Allowed' : 'Denied'}
              </p>
              <p className="text-xs text-slate-600">
                Normalized: <code className="bg-white/60 px-1 rounded" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  {result.normalized_domain}
                </code>
              </p>
              {result.matched_pattern && (
                <p className="text-xs text-slate-600">
                  Matched pattern: <code className="bg-white/60 px-1 rounded" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    {result.matched_pattern}
                  </code>
                </p>
              )}
              <p className="text-xs text-slate-500">
                {result.active_patterns_count} active pattern{result.active_patterns_count !== 1 ? 's' : ''} checked
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
