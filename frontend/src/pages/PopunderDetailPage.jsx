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
import { Checkbox } from '../components/ui/checkbox';
import {
  ArrowLeft, Copy, Check, Pencil, Layers, ExternalLink,
  Settings2, Monitor, Smartphone, Tablet, Globe
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
  { code: 'KR', label: 'South Korea' },
  { code: 'ID', label: 'Indonesia' },
  { code: 'MX', label: 'Mexico' },
  { code: 'PH', label: 'Philippines' },
  { code: 'TH', label: 'Thailand' },
  { code: 'VN', label: 'Vietnam' },
  { code: 'RU', label: 'Russia' },
  { code: 'PL', label: 'Poland' },
];

export default function PopunderDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(null);

  // Edit form
  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  const loadCampaign = useCallback(async () => {
    try {
      const res = await popunderAPI.get(campaignId);
      setCampaign(res.data.popunder);
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
    const settings = campaign.settings || {};
    setEditForm({
      name: campaign.name,
      direct_link: settings.direct_link || '',
      timer: settings.timer || 0,
      interval: settings.interval || 24,
      devices: settings.devices || ['desktop', 'mobile', 'tablet'],
      countries: settings.countries || [],
    });
    setShowEdit(true);
  };

  const handleDeviceToggle = (device) => {
    const current = editForm.devices || [];
    if (current.includes(device)) {
      setEditForm({ ...editForm, devices: current.filter(d => d !== device) });
    } else {
      setEditForm({ ...editForm, devices: [...current, device] });
    }
  };

  const handleCountryToggle = (countryCode) => {
    const current = editForm.countries || [];
    if (countryCode === '') {
      // "All Countries" selected - clear the list
      setEditForm({ ...editForm, countries: [] });
    } else if (current.includes(countryCode)) {
      setEditForm({ ...editForm, countries: current.filter(c => c !== countryCode) });
    } else {
      setEditForm({ ...editForm, countries: [...current, countryCode] });
    }
  };

  const handleUpdate = async () => {
    if (!editForm.name?.trim()) {
      toast.error('Campaign name is required');
      return;
    }
    if (!editForm.direct_link?.trim()) {
      toast.error('Direct link URL is required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: editForm.name.trim(),
        settings: {
          direct_link: editForm.direct_link.trim(),
          timer: parseInt(editForm.timer) || 0,
          interval: parseInt(editForm.interval) || 24,
          devices: editForm.devices || ['desktop', 'mobile', 'tablet'],
          countries: editForm.countries || [],
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
  const settings = campaign.settings || {};

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
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <span className="label-caps block mb-1">Direct Link</span>
                    <code className="text-sm text-slate-700 break-all" data-testid="direct-link-value">
                      {settings.direct_link || '—'}
                    </code>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Timer</span>
                    <span className="text-slate-700" data-testid="timer-value">
                      {settings.timer || 0} seconds
                    </span>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Interval</span>
                    <span className="text-slate-700" data-testid="interval-value">
                      {settings.interval || 24} hours between shows
                    </span>
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Devices</span>
                    <div className="flex gap-2 flex-wrap" data-testid="devices-value">
                      {(settings.devices || ['desktop', 'mobile', 'tablet']).map((device) => {
                        const opt = DEVICE_OPTIONS.find(d => d.value === device);
                        const Icon = opt?.icon || Monitor;
                        return (
                          <Badge key={device} variant="secondary" className="flex items-center gap-1">
                            <Icon className="w-3 h-3" /> {opt?.label || device}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                  <div className="md:col-span-2">
                    <span className="label-caps block mb-1">Countries</span>
                    <div className="flex gap-2 flex-wrap" data-testid="countries-value">
                      {(!settings.countries || settings.countries.length === 0) ? (
                        <Badge variant="secondary" className="flex items-center gap-1">
                          <Globe className="w-3 h-3" /> All Countries
                        </Badge>
                      ) : (
                        settings.countries.map((code) => {
                          const country = COUNTRY_OPTIONS.find(c => c.code === code);
                          return (
                            <Badge key={code} variant="secondary">
                              {country?.label || code}
                            </Badge>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Embed Tab */}
          <TabsContent value="embed">
            <Card className="border border-border bg-white">
              <CardHeader>
                <CardTitle className="text-lg">Embed Code</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Add this script tag to any page to enable the popunder.
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
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Edit Dialog */}
      <Dialog open={showEdit} onOpenChange={(open) => setShowEdit(open)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="edit-campaign-dialog">
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
              <Label className="label-caps">Direct Link</Label>
              <Input
                value={editForm.direct_link || ''}
                onChange={(e) => setEditForm({ ...editForm, direct_link: e.target.value })}
                placeholder="https://example.com"
                data-testid="edit-direct-link-input"
              />
              <p className="text-xs text-muted-foreground">URL to open in the popunder window</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="label-caps">Timer (seconds)</Label>
                <Input
                  type="number"
                  min="0"
                  value={editForm.timer || 0}
                  onChange={(e) => setEditForm({ ...editForm, timer: e.target.value })}
                  data-testid="edit-timer-input"
                />
                <p className="text-xs text-muted-foreground">Delay before popunder opens</p>
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Interval (hours)</Label>
                <Input
                  type="number"
                  min="1"
                  value={editForm.interval || 24}
                  onChange={(e) => setEditForm({ ...editForm, interval: e.target.value })}
                  data-testid="edit-interval-input"
                />
                <p className="text-xs text-muted-foreground">Hours between shows for same user</p>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Devices</Label>
              <div className="flex gap-4">
                {DEVICE_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const isSelected = (editForm.devices || []).includes(opt.value);
                  return (
                    <div key={opt.value} className="flex items-center gap-2">
                      <Checkbox
                        id={`device-${opt.value}`}
                        checked={isSelected}
                        onCheckedChange={() => handleDeviceToggle(opt.value)}
                        data-testid={`device-checkbox-${opt.value}`}
                      />
                      <label htmlFor={`device-${opt.value}`} className="flex items-center gap-1 text-sm cursor-pointer">
                        <Icon className="w-4 h-4" /> {opt.label}
                      </label>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="space-y-2">
              <Label className="label-caps">Countries</Label>
              <p className="text-xs text-muted-foreground mb-2">Leave empty for all countries</p>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 border rounded-md">
                {COUNTRY_OPTIONS.map((country) => {
                  const isAllSelected = editForm.countries?.length === 0;
                  const isSelected = country.code === '' 
                    ? isAllSelected 
                    : (editForm.countries || []).includes(country.code);
                  return (
                    <div key={country.code || 'all'} className="flex items-center gap-2">
                      <Checkbox
                        id={`country-${country.code || 'all'}`}
                        checked={isSelected}
                        onCheckedChange={() => handleCountryToggle(country.code)}
                        data-testid={`country-checkbox-${country.code || 'all'}`}
                      />
                      <label htmlFor={`country-${country.code || 'all'}`} className="text-sm cursor-pointer">
                        {country.label}
                      </label>
                    </div>
                  );
                })}
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
