import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { popunderAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  ArrowLeft, Copy, Check, Plus, Trash2, Pencil, Layers, Shield, ExternalLink,
  Settings2, Globe, AlertCircle, CheckCircle, XCircle, Search
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PopunderDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [whitelists, setWhitelists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(null);

  // Edit form
  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  // Whitelist form
  const [newDomain, setNewDomain] = useState('');
  const [addingDomain, setAddingDomain] = useState(false);

  // Domain tester
  const [testDomain, setTestDomain] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const loadCampaign = useCallback(async () => {
    try {
      const res = await popunderAPI.get(campaignId);
      setCampaign(res.data.popunder);
      setWhitelists(res.data.whitelists || []);
    } catch (err) {
      toast.error('Failed to load campaign');
      navigate('/popunders');
    } finally {
      setLoading(false);
    }
  }, [campaignId, navigate]);

  useEffect(() => {
    loadCampaign();
  }, [loadCampaign]);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(null), 2000);
  };

  const getEmbedUrl = () => `${BACKEND_URL}/api/js/popunder/${campaign?.slug}.js`;

  const openEditDialog = () => {
    setEditForm({
      name: campaign.name,
      target_url: campaign.settings?.target_url || '',
      frequency: campaign.settings?.frequency || 1,
      frequency_unit: campaign.settings?.frequency_unit || 'session',
      delay: campaign.settings?.delay || 0,
      width: campaign.settings?.width || 800,
      height: campaign.settings?.height || 600,
    });
    setShowEdit(true);
  };

  const handleUpdate = async () => {
    if (!editForm.name?.trim()) {
      toast.error('Campaign name is required');
      return;
    }
    if (!editForm.target_url?.trim()) {
      toast.error('Target URL is required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: editForm.name.trim(),
        settings: {
          target_url: editForm.target_url.trim(),
          frequency: parseInt(editForm.frequency) || 1,
          frequency_unit: editForm.frequency_unit,
          delay: parseInt(editForm.delay) || 0,
          width: parseInt(editForm.width) || 800,
          height: parseInt(editForm.height) || 600,
        },
      };
      await popunderAPI.update(campaignId, payload);
      toast.success('Campaign updated');
      setShowEdit(false);
      loadCampaign();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update campaign');
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async () => {
    try {
      const newStatus = campaign.status === 'active' ? 'paused' : 'active';
      await popunderAPI.update(campaignId, { status: newStatus });
      toast.success(`Campaign ${newStatus}`);
      loadCampaign();
    } catch (err) {
      toast.error('Failed to update status');
    }
  };

  const handleAddDomain = async () => {
    if (!newDomain.trim()) {
      toast.error('Enter a domain pattern');
      return;
    }
    setAddingDomain(true);
    try {
      await popunderAPI.addWhitelist(campaignId, { domain_pattern: newDomain.trim() });
      toast.success('Domain added');
      setNewDomain('');
      loadCampaign();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add domain');
    } finally {
      setAddingDomain(false);
    }
  };

  const toggleWhitelistStatus = async (whitelist) => {
    try {
      await popunderAPI.updateWhitelist(campaignId, whitelist.id, { is_active: !whitelist.is_active });
      toast.success(whitelist.is_active ? 'Domain disabled' : 'Domain enabled');
      loadCampaign();
    } catch (err) {
      toast.error('Failed to update domain');
    }
  };

  const handleDeleteWhitelist = async (id) => {
    try {
      await popunderAPI.deleteWhitelist(campaignId, id);
      toast.success('Domain removed');
      loadCampaign();
    } catch (err) {
      toast.error('Failed to remove domain');
    }
  };

  const handleTestDomain = async () => {
    if (!testDomain.trim()) {
      toast.error('Enter a domain to test');
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await popunderAPI.testDomain(campaignId, testDomain.trim());
      setTestResult(res.data);
    } catch (err) {
      toast.error('Failed to test domain');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </Layout>
    );
  }

  if (!campaign) return null;

  const embedTag = `<script src="${getEmbedUrl()}"></script>`;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/popunders')} className="gap-2">
            <ArrowLeft className="w-4 h-4" /> Back
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center">
              <Layers className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                  {campaign.name}
                </h1>
                <Badge className={campaign.status === 'active' ? 'status-active' : 'status-paused'}>
                  {campaign.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground font-mono">slug: {campaign.slug}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={campaign.status === 'active'}
              onCheckedChange={toggleStatus}
              data-testid="campaign-status-toggle"
            />
            <Button variant="outline" size="sm" onClick={openEditDialog} data-testid="edit-campaign-btn">
              <Pencil className="w-4 h-4 mr-2" /> Edit
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="settings" className="space-y-6">
          <TabsList data-testid="campaign-tabs">
            <TabsTrigger value="settings" data-testid="settings-tab">
              <Settings2 className="w-4 h-4 mr-2" /> Settings
            </TabsTrigger>
            <TabsTrigger value="whitelist" data-testid="whitelist-tab">
              <Shield className="w-4 h-4 mr-2" /> Whitelist
            </TabsTrigger>
            <TabsTrigger value="embed" data-testid="embed-tab">
              <ExternalLink className="w-4 h-4 mr-2" /> Embed
            </TabsTrigger>
          </TabsList>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <Card className="border border-border bg-white">
              <CardHeader>
                <CardTitle className="text-lg">Campaign Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <span className="label-caps block mb-1">Target URL</span>
                    <code className="text-sm text-slate-700 break-all">{campaign.settings?.target_url || '—'}</code>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Frequency</span>
                    <span className="text-slate-700">{campaign.settings?.frequency || 1} per {campaign.settings?.frequency_unit || 'session'}</span>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Delay</span>
                    <span className="text-slate-700">{campaign.settings?.delay || 0} ms</span>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Window Size</span>
                    <span className="text-slate-700">{campaign.settings?.width || 800} x {campaign.settings?.height || 600}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Whitelist Tab */}
          <TabsContent value="whitelist">
            <div className="space-y-6">
              <Card className="border border-border bg-white">
                <CardHeader>
                  <CardTitle className="text-lg">Domain Whitelist</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder="example.com or *.example.com"
                      value={newDomain}
                      onChange={(e) => setNewDomain(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddDomain()}
                      data-testid="add-domain-input"
                    />
                    <Button onClick={handleAddDomain} disabled={addingDomain} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="add-domain-btn">
                      <Plus className="w-4 h-4 mr-2" /> Add
                    </Button>
                  </div>

                  {whitelists.length === 0 ? (
                    <div className="text-center py-6 text-muted-foreground">
                      <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No domains whitelisted. Add at least one domain to enable the popunder.</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {whitelists.map((w) => (
                        <div key={w.id} className="flex items-center justify-between py-3" data-testid={`whitelist-item-${w.id}`}>
                          <div className="flex items-center gap-3">
                            <Globe className="w-4 h-4 text-muted-foreground" />
                            <code className="text-sm">{w.domain_pattern}</code>
                            <Badge variant={w.is_active ? 'default' : 'secondary'} className="text-xs">
                              {w.is_active ? 'Active' : 'Disabled'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={w.is_active}
                              onCheckedChange={() => toggleWhitelistStatus(w)}
                              data-testid={`whitelist-toggle-${w.id}`}
                            />
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteWhitelist(w.id)} className="text-destructive" data-testid={`whitelist-delete-${w.id}`}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Domain Tester */}
              <Card className="border border-border bg-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Search className="w-5 h-5" /> Domain Tester
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">Test if a domain would be allowed by your whitelist.</p>
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://test.example.com"
                      value={testDomain}
                      onChange={(e) => setTestDomain(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleTestDomain()}
                      data-testid="test-domain-input"
                    />
                    <Button onClick={handleTestDomain} disabled={testing} variant="outline" data-testid="test-domain-btn">
                      {testing ? 'Testing...' : 'Test'}
                    </Button>
                  </div>

                  {testResult && (
                    <div className={`p-4 rounded-lg ${testResult.allowed ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`} data-testid="test-result">
                      <div className="flex items-center gap-2 mb-2">
                        {testResult.allowed ? (
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-600" />
                        )}
                        <span className={`font-medium ${testResult.allowed ? 'text-green-700' : 'text-red-700'}`}>
                          {testResult.allowed ? 'Allowed' : 'Denied'}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Normalized: <code>{testResult.domain}</code>
                      </p>
                      {testResult.matched_patterns?.length > 0 && (
                        <p className="text-sm text-green-700 mt-1">
                          Matched: {testResult.matched_patterns.join(', ')}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Embed Tab */}
          <TabsContent value="embed">
            <Card className="border border-border bg-white">
              <CardHeader>
                <CardTitle className="text-lg">Embed Code</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Add this script tag to pages on your whitelisted domains to enable the popunder.
                </p>
                <div className="bg-[#0F172A] rounded-lg p-4 flex items-center justify-between gap-3">
                  <code className="text-sm text-slate-300 break-all" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    {embedTag}
                  </code>
                  <Button
                    variant="ghost" size="sm"
                    className="text-slate-400 hover:text-white flex-shrink-0"
                    onClick={() => copyToClipboard(embedTag, 'embed')}
                    data-testid="copy-embed-btn"
                  >
                    {copied === 'embed' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Direct URL: <code className="text-xs">{getEmbedUrl()}</code>
                </p>

                {whitelists.length === 0 && (
                  <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>Add at least one domain to your whitelist for the popunder to work.</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Edit Dialog */}
      <Dialog open={showEdit} onOpenChange={(open) => setShowEdit(open)}>
        <DialogContent className="max-w-lg" data-testid="edit-campaign-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Edit Campaign
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="label-caps">Campaign Name</Label>
              <Input
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                data-testid="edit-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Target URL</Label>
              <Input
                value={editForm.target_url || ''}
                onChange={(e) => setEditForm({ ...editForm, target_url: e.target.value })}
                data-testid="edit-url-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Frequency</Label>
                <Input
                  type="number"
                  min="1"
                  value={editForm.frequency || 1}
                  onChange={(e) => setEditForm({ ...editForm, frequency: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Per</Label>
                <Select value={editForm.frequency_unit || 'session'} onValueChange={(v) => setEditForm({ ...editForm, frequency_unit: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="session">Session</SelectItem>
                    <SelectItem value="hour">Hour</SelectItem>
                    <SelectItem value="day">Day</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Delay (ms)</Label>
              <Input
                type="number"
                min="0"
                value={editForm.delay || 0}
                onChange={(e) => setEditForm({ ...editForm, delay: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Width</Label>
                <Input
                  type="number"
                  min="200"
                  value={editForm.width || 800}
                  onChange={(e) => setEditForm({ ...editForm, width: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Height</Label>
                <Input
                  type="number"
                  min="200"
                  value={editForm.height || 600}
                  onChange={(e) => setEditForm({ ...editForm, height: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEdit(false)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={saving} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="save-edit-btn">
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
