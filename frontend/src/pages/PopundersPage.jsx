import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { popunderAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Layers, Pencil, Trash2, ExternalLink, Settings2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PopundersPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '',
    target_url: '',
    frequency: 1,
    frequency_unit: 'session',
    delay: 0,
    width: 800,
    height: 600,
  });
  const [saving, setSaving] = useState(false);

  const loadCampaigns = async () => {
    try {
      const res = await popunderAPI.list();
      setCampaigns(res.data.popunders);
    } catch (err) {
      toast.error('Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  const resetForm = () => {
    setForm({
      name: '',
      target_url: '',
      frequency: 1,
      frequency_unit: 'session',
      delay: 0,
      width: 800,
      height: 600,
    });
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error('Campaign name is required');
      return;
    }
    if (!form.target_url.trim()) {
      toast.error('Target URL is required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        settings: {
          target_url: form.target_url.trim(),
          frequency: parseInt(form.frequency) || 1,
          frequency_unit: form.frequency_unit,
          delay: parseInt(form.delay) || 0,
          width: parseInt(form.width) || 800,
          height: parseInt(form.height) || 600,
        },
      };
      await popunderAPI.create(payload);
      toast.success('Campaign created');
      setShowCreate(false);
      resetForm();
      loadCampaigns();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create campaign');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this campaign?')) return;
    try {
      await popunderAPI.delete(id);
      toast.success('Campaign deleted');
      loadCampaigns();
    } catch (err) {
      toast.error('Failed to delete campaign');
    }
  };

  const toggleStatus = async (campaign) => {
    try {
      const newStatus = campaign.status === 'active' ? 'paused' : 'active';
      await popunderAPI.update(campaign.id, { status: newStatus });
      toast.success(`Campaign ${newStatus}`);
      loadCampaigns();
    } catch (err) {
      toast.error('Failed to update campaign');
    }
  };

  const getEmbedUrl = (slug) => `${BACKEND_URL}/api/js/popunder/${slug}.js`;

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Popunder Campaigns
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your popunder advertising campaigns
            </p>
          </div>
          <Button
            onClick={() => { resetForm(); setShowCreate(true); }}
            className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
            data-testid="create-campaign-btn"
          >
            <Plus className="w-4 h-4 mr-2" /> Create Campaign
          </Button>
        </div>

        {/* Info Card */}
        <Card className="border border-purple-100 bg-purple-50/50">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Layers className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-purple-800 space-y-1">
                <p className="font-medium">How Popunders Work:</p>
                <ul className="list-disc list-inside text-xs space-y-0.5 text-purple-700">
                  <li>Opens target URL in a new window behind the current page</li>
                  <li>Triggers on first user click/keypress after page load</li>
                  <li>Each campaign has its own domain whitelist</li>
                  <li>Embed the script on whitelisted domains to activate</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Campaigns List */}
        {campaigns.length === 0 ? (
          <Card className="border border-dashed bg-white">
            <CardContent className="p-10 text-center">
              <Layers className="w-10 h-10 text-muted-foreground mx-auto mb-3" strokeWidth={1.5} />
              <h3 className="font-medium text-lg mb-1">No campaigns yet</h3>
              <p className="text-muted-foreground text-sm mb-4">Create your first popunder campaign to get started.</p>
              <Button onClick={() => setShowCreate(true)} className="bg-[#0F172A] hover:bg-[#1E293B] text-white">
                <Plus className="w-4 h-4 mr-2" /> Create Campaign
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {campaigns.map((campaign) => (
              <Card key={campaign.id} className="border border-border bg-white shadow-sm hover:shadow-md transition-shadow" data-testid={`campaign-card-${campaign.id}`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                        <Layers className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <h3 className="font-medium text-lg">{campaign.name}</h3>
                        <p className="text-xs text-muted-foreground font-mono">slug: {campaign.slug}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={campaign.status === 'active' ? 'status-active' : 'status-paused'}>
                        {campaign.status}
                      </Badge>
                      <Switch
                        checked={campaign.status === 'active'}
                        onCheckedChange={() => toggleStatus(campaign)}
                        data-testid={`campaign-toggle-${campaign.id}`}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-4">
                    <div>
                      <span className="label-caps block mb-1">Target URL</span>
                      <code className="text-slate-700 text-xs truncate block">{campaign.settings?.target_url || '—'}</code>
                    </div>
                    <div>
                      <span className="label-caps block mb-1">Frequency</span>
                      <span className="text-slate-700">{campaign.settings?.frequency || 1} / {campaign.settings?.frequency_unit || 'session'}</span>
                    </div>
                    <div>
                      <span className="label-caps block mb-1">Delay</span>
                      <span className="text-slate-700">{campaign.settings?.delay || 0}ms</span>
                    </div>
                    <div>
                      <span className="label-caps block mb-1">Window Size</span>
                      <span className="text-slate-700">{campaign.settings?.width || 800}x{campaign.settings?.height || 600}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/popunders/${campaign.id}`)}
                      className="flex-1"
                      data-testid={`manage-campaign-${campaign.id}`}
                    >
                      <Settings2 className="w-4 h-4 mr-2" /> Manage Campaign
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(campaign.id)} className="text-destructive" data-testid={`delete-campaign-${campaign.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-lg" data-testid="create-campaign-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              New Popunder Campaign
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="label-caps">Campaign Name</Label>
              <Input
                placeholder="e.g. Main Offer Campaign"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="campaign-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Target URL</Label>
              <Input
                placeholder="https://example.com/landing-page"
                value={form.target_url}
                onChange={(e) => setForm({ ...form, target_url: e.target.value })}
                data-testid="campaign-url-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Frequency</Label>
                <Input
                  type="number"
                  min="1"
                  value={form.frequency}
                  onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                  data-testid="campaign-frequency-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Per</Label>
                <Select value={form.frequency_unit} onValueChange={(v) => setForm({ ...form, frequency_unit: v })}>
                  <SelectTrigger data-testid="campaign-frequency-unit">
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
                value={form.delay}
                onChange={(e) => setForm({ ...form, delay: e.target.value })}
                data-testid="campaign-delay-input"
              />
              <p className="text-xs text-muted-foreground">Milliseconds to wait after user interaction</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Width</Label>
                <Input
                  type="number"
                  min="200"
                  value={form.width}
                  onChange={(e) => setForm({ ...form, width: e.target.value })}
                  data-testid="campaign-width-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Height</Label>
                <Input
                  type="number"
                  min="200"
                  value={form.height}
                  onChange={(e) => setForm({ ...form, height: e.target.value })}
                  data-testid="campaign-height-input"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowCreate(false); resetForm(); }}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving} className="bg-[#0F172A] hover:bg-[#1E293B] text-white" data-testid="save-campaign-btn">
              {saving ? 'Creating...' : 'Create Campaign'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
