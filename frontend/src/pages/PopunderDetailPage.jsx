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
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeft, Copy, Check, Pencil, Layers, ExternalLink,
  Settings2, Monitor, Smartphone, Tablet, Globe, Link2, Code,
  BarChart3, Eye, MousePointerClick, Percent, Trash2, ChevronLeft, ChevronRight
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

  // Analytics state
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLogs, setAnalyticsLogs] = useState([]);
  const [analyticsPage, setAnalyticsPage] = useState(1);
  const [analyticsPagination, setAnalyticsPagination] = useState({});
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

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

  const loadAnalytics = useCallback(async () => {
    try {
      const res = await popunderAPI.getAnalytics(campaignId);
      setAnalytics(res.data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  }, [campaignId]);

  const loadAnalyticsLogs = useCallback(async (page = 1) => {
    setAnalyticsLoading(true);
    try {
      const res = await popunderAPI.getAnalyticsLogs(campaignId, page);
      setAnalyticsLogs(res.data.logs);
      setAnalyticsPagination(res.data.pagination);
      setAnalyticsPage(page);
    } catch (err) {
      console.error('Failed to load analytics logs:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    loadCampaign();
    loadAnalytics();
    loadAnalyticsLogs(1);
  }, [loadCampaign, loadAnalytics, loadAnalyticsLogs]);

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
      url_list: settings.url_list || '',
      timer: settings.timer || 0,
      frequency: settings.frequency || 1,
      devices: settings.devices || ['desktop', 'mobile', 'tablet'],
      countries: settings.countries || [],
      floating_banner: settings.floating_banner || '',
      html_body: settings.html_body || '',
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
    if (!editForm.url_list?.trim()) {
      toast.error('At least one URL is required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: editForm.name.trim(),
        settings: {
          url_list: editForm.url_list.trim(),
          timer: parseInt(editForm.timer) || 0,
          frequency: parseInt(editForm.frequency) || 1,
          devices: editForm.devices || ['desktop', 'mobile', 'tablet'],
          countries: editForm.countries || [],
          floating_banner: editForm.floating_banner || '',
          html_body: editForm.html_body || '',
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

  const deleteAnalyticsLog = async (logId) => {
    try {
      await popunderAPI.deleteAnalyticsLog(campaignId, logId);
      toast.success('Log entry deleted');
      loadAnalyticsLogs(analyticsPage);
      loadAnalytics();
    } catch (err) {
      toast.error('Failed to delete log');
    }
  };

  const clearAllAnalytics = async () => {
    if (!window.confirm('Are you sure you want to clear all analytics data?')) return;
    try {
      await popunderAPI.clearAnalytics(campaignId);
      toast.success('Analytics cleared');
      loadAnalytics();
      loadAnalyticsLogs(1);
    } catch (err) {
      toast.error('Failed to clear analytics');
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
  
  // Parse URL list for display
  const urlList = (settings.url_list || '').split('\n').filter(u => u.trim());

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
            <div className="space-y-6">
              {/* URLs & Timing */}
              <Card className="border border-border bg-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Link2 className="w-5 h-5" /> URLs & Timing
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <span className="label-caps block mb-2">Target URLs</span>
                    <div className="space-y-1" data-testid="url-list-value">
                      {urlList.length > 0 ? urlList.map((url, i) => (
                        <code key={i} className="text-sm text-slate-700 block bg-slate-50 p-2 rounded">
                          {url}
                        </code>
                      )) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {urlList.length} URL(s) - Random selection on each trigger
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <span className="label-caps block mb-1">Timer</span>
                      <span className="text-slate-700" data-testid="timer-value">
                        {settings.timer || 0} seconds delay
                      </span>
                    </div>
                    <div>
                      <span className="label-caps block mb-1">Frequency</span>
                      <span className="text-slate-700" data-testid="frequency-value">
                        {settings.frequency || 1}x per user per day
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Targeting */}
              <Card className="border border-border bg-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Globe className="w-5 h-5" /> Targeting
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
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
                  <div>
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
                    <p className="text-xs text-muted-foreground mt-1">
                      Country detection via IP (client-side)
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Custom Code */}
              <Card className="border border-border bg-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Code className="w-5 h-5" /> Custom Code
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <span className="label-caps block mb-1">Floating Banner</span>
                    {settings.floating_banner ? (
                      <pre className="text-xs text-slate-700 bg-slate-50 p-3 rounded overflow-x-auto max-h-32" data-testid="floating-banner-value">
                        {settings.floating_banner}
                      </pre>
                    ) : (
                      <span className="text-muted-foreground text-sm">No floating banner configured</span>
                    )}
                  </div>
                  <div>
                    <span className="label-caps block mb-1">Custom HTML Body</span>
                    {settings.html_body ? (
                      <pre className="text-xs text-slate-700 bg-slate-50 p-3 rounded overflow-x-auto max-h-32" data-testid="html-body-value">
                        {settings.html_body}
                      </pre>
                    ) : (
                      <span className="text-muted-foreground text-sm">No custom HTML configured</span>
                    )}
                  </div>
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
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="edit-campaign-dialog">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Edit Campaign
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 py-2">
            {/* Campaign Name */}
            <div className="space-y-2">
              <Label className="label-caps">Campaign Name</Label>
              <Input
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                data-testid="edit-name-input"
              />
            </div>

            {/* URL List */}
            <div className="space-y-2">
              <Label className="label-caps">Target URLs (one per line)</Label>
              <Textarea
                value={editForm.url_list || ''}
                onChange={(e) => setEditForm({ ...editForm, url_list: e.target.value })}
                placeholder="https://example.com/offer1&#10;https://example.com/offer2&#10;https://example.com/offer3"
                rows={4}
                data-testid="edit-url-list-input"
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
                  value={editForm.timer || 0}
                  onChange={(e) => setEditForm({ ...editForm, timer: e.target.value })}
                  data-testid="edit-timer-input"
                />
                <p className="text-xs text-muted-foreground">Delay before popunder opens</p>
              </div>
              <div className="space-y-2">
                <Label className="label-caps">Frequency (per day)</Label>
                <Input
                  type="number"
                  min="1"
                  value={editForm.frequency || 1}
                  onChange={(e) => setEditForm({ ...editForm, frequency: e.target.value })}
                  data-testid="edit-frequency-input"
                />
                <p className="text-xs text-muted-foreground">Max shows per user per day</p>
              </div>
            </div>

            {/* Devices */}
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

            {/* Countries */}
            <div className="space-y-2">
              <Label className="label-caps">Countries (IP-based detection)</Label>
              <p className="text-xs text-muted-foreground mb-2">Leave empty for all countries</p>
              <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 border rounded-md">
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

            {/* Floating Banner */}
            <div className="space-y-2">
              <Label className="label-caps">Floating Banner (HTML)</Label>
              <Textarea
                value={editForm.floating_banner || ''}
                onChange={(e) => setEditForm({ ...editForm, floating_banner: e.target.value })}
                placeholder='<div style="position:fixed;bottom:0;left:0;right:0;background:#000;color:#fff;padding:10px;text-align:center;">Your banner here</div>'
                rows={3}
                className="font-mono text-sm"
                data-testid="edit-floating-banner-input"
              />
              <p className="text-xs text-muted-foreground">HTML code to inject as a floating element on the page</p>
            </div>

            {/* Custom HTML Body */}
            <div className="space-y-2">
              <Label className="label-caps">Custom HTML Body</Label>
              <Textarea
                value={editForm.html_body || ''}
                onChange={(e) => setEditForm({ ...editForm, html_body: e.target.value })}
                placeholder='<div id="my-custom-element">Custom content here</div>'
                rows={3}
                className="font-mono text-sm"
                data-testid="edit-html-body-input"
              />
              <p className="text-xs text-muted-foreground">HTML code to inject into the page body</p>
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
