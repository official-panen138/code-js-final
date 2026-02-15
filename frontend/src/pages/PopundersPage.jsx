import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { popunderAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Checkbox } from '../components/ui/checkbox';
import { Textarea } from '../components/ui/textarea';
import { Plus, Layers, Trash2, Settings2, Monitor, Smartphone, Tablet, Globe, Link2 } from 'lucide-react';
import { toast } from 'sonner';

const DEVICE_OPTIONS = [
  { value: 'desktop', label: 'Desktop', icon: Monitor },
  { value: 'mobile', label: 'Mobile', icon: Smartphone },
  { value: 'tablet', label: 'Tablet', icon: Tablet },
];

const COUNTRY_OPTIONS = [
  { code: '', label: 'All Countries' },
  { code: 'US', label: 'United States' },
  { code: 'GB', label: 'United Kingdom' },
  { code: 'CA', label: 'Canada' },
  { code: 'AU', label: 'Australia' },
  { code: 'DE', label: 'Germany' },
  { code: 'FR', label: 'France' },
  { code: 'IT', label: 'Italy' },
  { code: 'ES', label: 'Spain' },
  { code: 'BR', label: 'Brazil' },
  { code: 'IN', label: 'India' },
  { code: 'JP', label: 'Japan' },
];

export default function PopundersPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '',
    url_list: '',
    timer: 0,
    frequency: 1,
    devices: ['desktop', 'mobile', 'tablet'],
    countries: [],
    floating_banner: '',
    html_body: '',
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
      url_list: '',
      timer: 0,
      interval: 24,
      devices: ['desktop', 'mobile', 'tablet'],
      countries: [],
      floating_banner: '',
      html_body: '',
    });
  };

  const handleDeviceToggle = (device) => {
    const current = form.devices || [];
    if (current.includes(device)) {
      setForm({ ...form, devices: current.filter(d => d !== device) });
    } else {
      setForm({ ...form, devices: [...current, device] });
    }
  };

  const handleCountryToggle = (countryCode) => {
    const current = form.countries || [];
    if (countryCode === '') {
      setForm({ ...form, countries: [] });
    } else if (current.includes(countryCode)) {
      setForm({ ...form, countries: current.filter(c => c !== countryCode) });
    } else {
      setForm({ ...form, countries: [...current, countryCode] });
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error('Campaign name is required');
      return;
    }
    if (!form.url_list.trim()) {
      toast.error('At least one URL is required');
      return;
    }
    if (form.devices.length === 0) {
      toast.error('Select at least one device');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        settings: {
          url_list: form.url_list.trim(),
          timer: parseInt(form.timer) || 0,
          interval: parseInt(form.interval) || 24,
          devices: form.devices,
          countries: form.countries,
          floating_banner: form.floating_banner || '',
          html_body: form.html_body || '',
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
                  <li>Opens a random URL from your list in a new window behind the current page</li>
                  <li>Triggers on first user click/touch after page load</li>
                  <li>Timer controls delay before opening (in seconds)</li>
                  <li>Interval controls hours between shows for same user</li>
                  <li>Country detection uses visitor's IP address</li>
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
            {campaigns.map((campaign) => {
              const settings = campaign.settings || {};
              const urlCount = (settings.url_list || '').split('\n').filter(u => u.trim()).length;
              return (
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

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm mb-4">
                      <div>
                        <span className="label-caps block mb-1">URLs</span>
                        <div className="flex items-center gap-1 text-slate-700">
                          <Link2 className="w-3 h-3" />
                          <span>{urlCount} URL(s)</span>
                        </div>
                      </div>
                      <div>
                        <span className="label-caps block mb-1">Timer</span>
                        <span className="text-slate-700">{settings.timer || 0}s</span>
                      </div>
                      <div>
                        <span className="label-caps block mb-1">Interval</span>
                        <span className="text-slate-700">{settings.interval || 24}h</span>
                      </div>
                      <div>
                        <span className="label-caps block mb-1">Devices</span>
                        <div className="flex gap-1">
                          {(settings.devices || ['desktop', 'mobile', 'tablet']).map(device => {
                            const opt = DEVICE_OPTIONS.find(d => d.value === device);
                            const Icon = opt?.icon || Monitor;
                            return <Icon key={device} className="w-4 h-4 text-slate-500" />;
                          })}
                        </div>
                      </div>
                      <div>
                        <span className="label-caps block mb-1">Countries</span>
                        <div className="flex items-center gap-1 text-slate-700">
                          <Globe className="w-3 h-3" />
                          <span>{settings.countries?.length || 0 > 0 ? settings.countries.length : 'All'}</span>
                        </div>
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
              );
            })}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="create-campaign-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              New Popunder Campaign
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 py-2">
            {/* Campaign Name */}
            <div className="space-y-2">
              <Label className="label-caps">Campaign Name</Label>
              <Input
                placeholder="e.g. Main Offer Campaign"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="campaign-name-input"
              />
            </div>

            {/* URL List */}
            <div className="space-y-2">
              <Label className="label-caps">Target URLs (one per line)</Label>
              <Textarea
                placeholder="https://example.com/offer1&#10;https://example.com/offer2&#10;https://example.com/offer3"
                value={form.url_list}
                onChange={(e) => setForm({ ...form, url_list: e.target.value })}
                rows={4}
                data-testid="campaign-url-list-input"
              />
              <p className="text-xs text-muted-foreground">Enter multiple URLs, one per line. A random URL will be selected on each trigger.</p>
            </div>

            {/* Timer & Interval */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Timer (seconds)</Label>
                <Input
                  type="number"
                  min="0"
                  value={form.timer}
                  onChange={(e) => setForm({ ...form, timer: e.target.value })}
                  data-testid="campaign-timer-input"
                />
                <p className="text-xs text-muted-foreground">Delay before popunder opens</p>
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Interval (hours)</Label>
                <Input
                  type="number"
                  min="1"
                  value={form.interval}
                  onChange={(e) => setForm({ ...form, interval: e.target.value })}
                  data-testid="campaign-interval-input"
                />
                <p className="text-xs text-muted-foreground">Hours between shows</p>
              </div>
            </div>

            {/* Devices */}
            <div className="space-y-2">
              <Label className="label-caps">Devices</Label>
              <div className="flex gap-4">
                {DEVICE_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const isSelected = (form.devices || []).includes(opt.value);
                  return (
                    <div key={opt.value} className="flex items-center gap-2">
                      <Checkbox
                        id={`create-device-${opt.value}`}
                        checked={isSelected}
                        onCheckedChange={() => handleDeviceToggle(opt.value)}
                        data-testid={`create-device-checkbox-${opt.value}`}
                      />
                      <label htmlFor={`create-device-${opt.value}`} className="flex items-center gap-1 text-sm cursor-pointer">
                        <Icon className="w-4 h-4" /> {opt.label}
                      </label>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Countries */}
            <div className="space-y-2">
              <Label className="label-caps">Countries (IP-based detection)</Label>
              <p className="text-xs text-muted-foreground mb-2">Leave empty for all countries</p>
              <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto p-2 border rounded-md">
                {COUNTRY_OPTIONS.map((country) => {
                  const isAllSelected = form.countries?.length === 0;
                  const isSelected = country.code === '' 
                    ? isAllSelected 
                    : (form.countries || []).includes(country.code);
                  return (
                    <div key={country.code || 'all'} className="flex items-center gap-2">
                      <Checkbox
                        id={`create-country-${country.code || 'all'}`}
                        checked={isSelected}
                        onCheckedChange={() => handleCountryToggle(country.code)}
                        data-testid={`create-country-checkbox-${country.code || 'all'}`}
                      />
                      <label htmlFor={`create-country-${country.code || 'all'}`} className="text-sm cursor-pointer">
                        {country.label}
                      </label>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Floating Banner */}
            <div className="space-y-2">
              <Label className="label-caps">Floating Banner (HTML) - Optional</Label>
              <Textarea
                value={form.floating_banner}
                onChange={(e) => setForm({ ...form, floating_banner: e.target.value })}
                placeholder='<div style="position:fixed;bottom:0;...">Banner HTML</div>'
                rows={2}
                className="font-mono text-sm"
                data-testid="campaign-floating-banner-input"
              />
            </div>

            {/* Custom HTML Body */}
            <div className="space-y-2">
              <Label className="label-caps">Custom HTML Body - Optional</Label>
              <Textarea
                value={form.html_body}
                onChange={(e) => setForm({ ...form, html_body: e.target.value })}
                placeholder='<div id="custom">Custom HTML</div>'
                rows={2}
                className="font-mono text-sm"
                data-testid="campaign-html-body-input"
              />
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
