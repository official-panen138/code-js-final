import { useEffect, useState, useCallback } from 'react';
import { customDomainAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { Globe, Plus, Trash2, RefreshCw, AlertCircle, CheckCircle, XCircle, Copy, Check, Server, Cloud, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

export default function CustomDomainsPage() {
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newDomain, setNewDomain] = useState('');
  const [adding, setAdding] = useState(false);
  const [verifying, setVerifying] = useState(null);
  const [forceActivating, setForceActivating] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [copied, setCopied] = useState(null);
  const [lastVerification, setLastVerification] = useState(null);

  const loadDomains = useCallback(async () => {
    try {
      const res = await customDomainAPI.list();
      setDomains(res.data.domains);
    } catch (err) {
      console.error('Failed to load domains:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDomains(); }, [loadDomains]);

  const handleAdd = async () => {
    if (!newDomain.trim()) { toast.error('Domain is required'); return; }
    setAdding(true);
    try {
      await customDomainAPI.add(newDomain.trim());
      toast.success('Domain added! Configure your DNS A record, then verify.');
      setShowAdd(false);
      setNewDomain('');
      loadDomains();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add domain');
    } finally {
      setAdding(false);
    }
  };

  const handleVerify = async (id) => {
    setVerifying(id);
    try {
      const res = await customDomainAPI.verify(id);
      const v = res.data.verification;
      setLastVerification({ domainId: id, ...v });
      
      if (v.match) {
        toast.success(v.message || 'DNS verified! Domain is now active.');
      } else if (v.is_cloudflare) {
        toast.warning('Cloudflare detected! See instructions below to complete setup.', { duration: 6000 });
      } else {
        toast.error(v.message || `DNS mismatch. Expected IP: ${v.platform_ip || 'unknown'}, Got: ${v.resolved_ip || 'no record found'}`);
      }
      loadDomains();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed');
    } finally {
      setVerifying(null);
    }
  };

  const handleForceActivate = async (id) => {
    setForceActivating(id);
    try {
      await customDomainAPI.forceActivate(id);
      toast.success('Domain force-activated! You can now use it for JS delivery.');
      loadDomains();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Force activation failed');
    } finally {
      setForceActivating(null);
    }
  };

  const handleToggle = async (domain) => {
    try {
      await customDomainAPI.update(domain.id, { is_active: !domain.is_active });
      toast.success(domain.is_active ? 'Domain deactivated' : 'Domain activated');
      loadDomains();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await customDomainAPI.delete(deleteTarget.id);
      toast.success('Domain removed');
      setDeleteTarget(null);
      loadDomains();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied');
    setTimeout(() => setCopied(null), 2000);
  };

  const statusConfig = {
    pending: { color: 'bg-yellow-50 text-yellow-700 border-yellow-200', icon: AlertCircle, label: 'Pending' },
    verified: { color: 'bg-green-50 text-green-700 border-green-200', icon: CheckCircle, label: 'Verified' },
    failed: { color: 'bg-red-50 text-red-700 border-red-200', icon: XCircle, label: 'Failed' },
    cloudflare_pending: { color: 'bg-orange-50 text-orange-700 border-orange-200', icon: Cloud, label: 'Cloudflare Detected' },
  };

  if (loading) {
    return (
      <Layout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-slate-100 rounded w-56" />
          <div className="h-64 bg-slate-100 rounded-lg" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8" data-testid="custom-domains-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Custom Domains
            </h1>
            <p className="text-muted-foreground mt-1">Connect your own domains to serve JS through this platform</p>
          </div>
          <Button
            onClick={() => setShowAdd(true)}
            className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
            data-testid="add-domain-btn"
          >
            <Plus className="w-4 h-4 mr-2" /> Add Domain
          </Button>
        </div>

        {/* Instructions */}
        <Card className="border border-blue-100 bg-blue-50/50">
          <CardContent className="p-5">
            <div className="flex gap-3">
              <Server className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-2">
                <p className="text-sm font-medium text-blue-800">How to connect your custom domain:</p>
                <ol className="text-xs text-blue-700 space-y-1 list-decimal list-inside">
                  <li>Add your domain below (e.g. <code className="bg-blue-100 px-1 rounded">cdn.yourdomain.com</code>)</li>
                  <li>Go to your DNS provider and create a <strong>CNAME record</strong> pointing to:
                    <code className="bg-blue-100 px-1 rounded block mt-1">log-manager-3.preview.emergentagent.com</code>
                    <span className="text-blue-600 text-[10px]">(Or use an A record to the platform IP if CNAME is not supported)</span>
                  </li>
                  <li>Click <strong>Verify DNS</strong> to check the record is configured</li>
                  <li>Once verified, use the custom domain in your embed URLs:
                    <code className="bg-blue-100 px-1 rounded block mt-1">&lt;script src="https://cdn.yourdomain.com/api/js/project/script.js"&gt;&lt;/script&gt;</code>
                  </li>
                </ol>
                <p className="text-[10px] text-blue-600 mt-2">
                  <strong>Note:</strong> For HTTPS to work on your CDN domain, you may need to configure SSL through Cloudflare or similar CDN service.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Domains List */}
        {domains.length === 0 ? (
          <Card className="border border-dashed bg-white">
            <CardContent className="p-12 text-center">
              <Globe className="w-10 h-10 text-muted-foreground mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-muted-foreground">No custom domains configured yet. Add your first domain to get started.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4" data-testid="domains-list">
            {domains.map((domain) => {
              const sc = statusConfig[domain.status] || statusConfig.pending;
              const StatusIcon = sc.icon;
              return (
                <Card key={domain.id} className="border border-border bg-white shadow-sm" data-testid={`domain-card-${domain.id}`}>
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between">
                      <div className="space-y-3 flex-1">
                        {/* Domain name + status */}
                        <div className="flex items-center gap-3">
                          <Globe className="w-5 h-5 text-muted-foreground" />
                          <span className="text-lg font-medium font-mono" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                            {domain.domain}
                          </span>
                          <Badge className={`text-xs border ${sc.color}`}>
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {sc.label}
                          </Badge>
                          {domain.is_active && (
                            <Badge className="status-active text-xs">Active</Badge>
                          )}
                        </div>

                        {/* IP Information */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div className="bg-slate-50 rounded-md px-4 py-3 border border-border">
                            <p className="label-caps mb-1">Platform IP (Point A Record Here)</p>
                            <div className="flex items-center gap-2">
                              <code className="text-sm font-mono font-medium" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                                {domain.platform_ip || 'Detecting...'}
                              </code>
                              {domain.platform_ip && (
                                <Button
                                  variant="ghost" size="sm" className="h-6 w-6 p-0"
                                  onClick={() => copyText(domain.platform_ip, `ip-${domain.id}`)}
                                  data-testid={`copy-ip-${domain.id}`}
                                >
                                  {copied === `ip-${domain.id}` ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
                                </Button>
                              )}
                            </div>
                          </div>
                          <div className="bg-slate-50 rounded-md px-4 py-3 border border-border">
                            <p className="label-caps mb-1">Resolved IP (Your Domain)</p>
                            <code className="text-sm font-mono" style={{ fontFamily: 'JetBrains Mono, monospace', color: domain.resolved_ip ? (domain.resolved_ip === domain.platform_ip ? '#16A34A' : '#DC2626') : '#64748B' }}>
                              {domain.resolved_ip || 'Not checked yet'}
                            </code>
                          </div>
                        </div>

                        {/* Embed URL preview */}
                        {domain.status === 'verified' && domain.is_active && (
                          <div className="bg-[#0F172A] rounded-lg p-3 flex items-center gap-3">
                            <code className="text-xs text-slate-300 flex-1 break-all" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                              &lt;script src="https://{domain.domain}/api/js/&#123;project&#125;/&#123;script&#125;.js"&gt;&lt;/script&gt;
                            </code>
                            <Button
                              variant="ghost" size="sm" className="text-slate-400 hover:text-white flex-shrink-0"
                              onClick={() => copyText(`<script src="https://${domain.domain}/api/js/{project}/{script}.js"></script>`, `embed-${domain.id}`)}
                              data-testid={`copy-embed-${domain.id}`}
                            >
                              {copied === `embed-${domain.id}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                            </Button>
                          </div>
                        )}

                        {domain.verified_at && (
                          <p className="text-xs text-muted-foreground">
                            Verified: {new Date(domain.verified_at).toLocaleString()}
                          </p>
                        )}

                        {/* Cloudflare Detection Info */}
                        {(domain.status === 'cloudflare_pending' || domain.status === 'failed') && lastVerification?.domainId === domain.id && lastVerification?.is_cloudflare && (
                          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mt-3">
                            <div className="flex items-start gap-3">
                              <Cloud className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                              <div className="space-y-2 flex-1">
                                <p className="text-sm font-medium text-orange-800">Cloudflare Proxy Detected</p>
                                <p className="text-xs text-orange-700">
                                  Your domain is using Cloudflare proxy. To complete verification:
                                </p>
                                <ol className="text-xs text-orange-700 list-decimal list-inside space-y-1">
                                  <li>Go to Cloudflare dashboard → DNS settings</li>
                                  <li>Make sure your domain has a <strong>CNAME</strong> or <strong>A</strong> record configured</li>
                                  <li>Ensure traffic is proxied (orange cloud enabled)</li>
                                  <li>Set origin server to point to this platform</li>
                                </ol>
                                <p className="text-xs text-orange-600 mt-2">
                                  Or click <strong>"Force Activate"</strong> if you're sure Cloudflare is configured correctly.
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                        <Button
                          variant="outline" size="sm"
                          onClick={() => handleVerify(domain.id)}
                          disabled={verifying === domain.id}
                          data-testid={`verify-domain-${domain.id}`}
                        >
                          <RefreshCw className={`w-4 h-4 mr-1.5 ${verifying === domain.id ? 'animate-spin' : ''}`} />
                          {verifying === domain.id ? 'Verifying...' : 'Verify DNS'}
                        </Button>
                        
                        {/* Force Activate for Cloudflare/Failed domains */}
                        {(domain.status === 'cloudflare_pending' || domain.status === 'failed') && (
                          <Button
                            variant="outline" size="sm"
                            className="border-orange-300 text-orange-700 hover:bg-orange-50"
                            onClick={() => handleForceActivate(domain.id)}
                            disabled={forceActivating === domain.id}
                            data-testid={`force-activate-domain-${domain.id}`}
                          >
                            <ShieldCheck className={`w-4 h-4 mr-1.5 ${forceActivating === domain.id ? 'animate-pulse' : ''}`} />
                            {forceActivating === domain.id ? 'Activating...' : 'Force Activate'}
                          </Button>
                        )}
                        
                        {domain.status === 'verified' && (
                          <Switch
                            checked={domain.is_active}
                            onCheckedChange={() => handleToggle(domain)}
                            data-testid={`toggle-domain-${domain.id}`}
                          />
                        )}
                        <Button
                          variant="ghost" size="sm" className="text-destructive"
                          onClick={() => setDeleteTarget(domain)}
                          data-testid={`delete-domain-${domain.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Add Domain Dialog */}
        <Dialog open={showAdd} onOpenChange={(open) => { setShowAdd(open); if (!open) setNewDomain(''); }}>
          <DialogContent data-testid="add-domain-dialog">
            <DialogHeader>
              <DialogTitle style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>Add Custom Domain</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="label-caps">Domain</Label>
                <Input
                  placeholder="e.g. cdn.yourdomain.com"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                  data-testid="new-domain-input"
                />
                <p className="text-xs text-muted-foreground">
                  Enter the domain you want to use for JS delivery. You'll need to configure the DNS A record after adding.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button
                onClick={handleAdd}
                disabled={adding}
                className="bg-[#0F172A] hover:bg-[#1E293B] text-white"
                data-testid="confirm-add-domain-btn"
              >
                {adding ? 'Adding...' : 'Add Domain'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
          <DialogContent data-testid="delete-domain-dialog">
            <DialogHeader>
              <DialogTitle>Remove Domain</DialogTitle>
            </DialogHeader>
            <div className="flex gap-3 py-2">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground">
                Remove <strong>{deleteTarget?.domain}</strong>? Embed URLs using this domain will stop working.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
              <Button variant="destructive" onClick={handleDelete} data-testid="confirm-delete-domain-btn">Remove</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
