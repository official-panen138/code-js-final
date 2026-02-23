import { useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { 
  BookOpen, FolderKanban, FileCode, Globe, Zap, Users, Shield, 
  ChevronRight, Copy, Check, ExternalLink, Settings, BarChart3
} from 'lucide-react';
import { Button } from '../components/ui/button';

export default function UserGuidePage() {
  const [copied, setCopied] = useState(null);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const CodeBlock = ({ code, id }) => (
    <div className="relative bg-slate-900 rounded-lg p-4 mt-2">
      <pre className="text-sm text-slate-300 overflow-x-auto">
        <code>{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-2 right-2 h-8 w-8 p-0 text-slate-400 hover:text-white"
        onClick={() => copyToClipboard(code, id)}
      >
        {copied === id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      </Button>
    </div>
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="user-guide-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold tracking-tight flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-primary" />
            User Guide
          </h1>
          <p className="text-muted-foreground mt-1">
            Panduan lengkap penggunaan JSHost Platform
          </p>
        </div>

        <Tabs defaultValue="getting-started" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5 h-auto gap-2 bg-transparent p-0">
            <TabsTrigger value="getting-started" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <Zap className="w-4 h-4 mr-2" /> Mulai
            </TabsTrigger>
            <TabsTrigger value="projects" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <FolderKanban className="w-4 h-4 mr-2" /> Projects
            </TabsTrigger>
            <TabsTrigger value="scripts" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <FileCode className="w-4 h-4 mr-2" /> Scripts
            </TabsTrigger>
            <TabsTrigger value="domains" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <Globe className="w-4 h-4 mr-2" /> Domains
            </TabsTrigger>
            <TabsTrigger value="popunder" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <ExternalLink className="w-4 h-4 mr-2" /> Popunder
            </TabsTrigger>
          </TabsList>

          {/* Getting Started */}
          <TabsContent value="getting-started" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  Selamat Datang di JSHost
                </CardTitle>
                <CardDescription>
                  Platform hosting JavaScript dengan fitur CDN custom domain
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium flex items-center gap-2 mb-2">
                      <span className="w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center text-sm">1</span>
                      Buat Project
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Project adalah wadah untuk mengelompokkan script-script Anda berdasarkan website atau kategori.
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium flex items-center gap-2 mb-2">
                      <span className="w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center text-sm">2</span>
                      Tambah Script
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Upload kode JavaScript Anda dan dapatkan URL embed yang bisa dipasang di website manapun.
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium flex items-center gap-2 mb-2">
                      <span className="w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center text-sm">3</span>
                      Setup Domain CDN
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Tambahkan domain Anda sendiri untuk serve script dengan branding custom.
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium flex items-center gap-2 mb-2">
                      <span className="w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center text-sm">4</span>
                      Embed di Website
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Copy kode embed dan pasang di website target. Script akan di-load dari CDN Anda.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Projects */}
          <TabsContent value="projects" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FolderKanban className="w-5 h-5 text-blue-500" />
                  Mengelola Projects
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <h4 className="font-medium">Membuat Project Baru</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Klik menu <strong>Projects</strong> di sidebar</li>
                    <li>Klik tombol <strong>New Project</strong></li>
                    <li>Isi nama project (contoh: "Website Utama")</li>
                    <li>Pilih kategori yang sesuai</li>
                    <li>Klik <strong>Create Project</strong></li>
                  </ol>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Struktur Project</h4>
                  <p className="text-sm text-muted-foreground">
                    Setiap project memiliki:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    <li><strong>Slug</strong> - ID unik untuk URL (auto-generated)</li>
                    <li><strong>Scripts</strong> - Kumpulan file JavaScript</li>
                    <li><strong>Whitelist Domains</strong> - Domain yang diizinkan load script</li>
                    <li><strong>Analytics</strong> - Statistik penggunaan script</li>
                  </ul>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Filter by Category</h4>
                  <p className="text-sm text-muted-foreground">
                    Gunakan dropdown "All Categories" untuk memfilter project berdasarkan kategori.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Scripts */}
          <TabsContent value="scripts" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-green-500" />
                  Mengelola Scripts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <h4 className="font-medium">Menambah Script</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Buka project yang diinginkan</li>
                    <li>Di tab <strong>Scripts</strong>, klik <strong>Add Script</strong></li>
                    <li>Isi nama script</li>
                    <li>Paste kode JavaScript di editor</li>
                    <li>Klik <strong>Create Script</strong></li>
                  </ol>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Embed Code</h4>
                  <p className="text-sm text-muted-foreground">
                    Setelah script dibuat, Anda akan mendapat embed code:
                  </p>
                  <CodeBlock 
                    code={`<script src="https://cdn.yourdomain.com/api/js/{project}/{script}.js"></script>`}
                    id="embed-example"
                  />
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Memilih Domain CDN</h4>
                  <p className="text-sm text-muted-foreground">
                    Gunakan dropdown "Domain" di sebelah tombol Add Script untuk memilih domain CDN yang akan digunakan pada URL embed.
                  </p>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Domain Whitelist</h4>
                  <p className="text-sm text-muted-foreground">
                    Batasi script hanya dapat di-load dari domain tertentu:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    <li>Buka detail script</li>
                    <li>Tambah domain di bagian "Whitelisted Domains"</li>
                    <li>Script akan menolak request dari domain lain</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Domains */}
          <TabsContent value="domains" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-purple-500" />
                  Custom CDN Domains
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <h4 className="font-medium">Menambah Domain</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Klik menu <strong>Domains</strong> di sidebar</li>
                    <li>Klik <strong>Add Domain</strong></li>
                    <li>Masukkan domain Anda (contoh: cdn.yourdomain.com)</li>
                    <li>Klik <strong>Add</strong></li>
                  </ol>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Konfigurasi DNS</h4>
                  <p className="text-sm text-muted-foreground">
                    Setelah menambah domain, konfigurasikan DNS:
                  </p>
                  <div className="bg-slate-100 rounded-lg p-4 space-y-2">
                    <p className="text-sm font-medium">Opsi 1: CNAME Record (Recommended)</p>
                    <CodeBlock 
                      code={`cdn.yourdomain.com  CNAME  [platform-domain]`}
                      id="cname-example"
                    />
                    <p className="text-sm font-medium mt-4">Opsi 2: A Record</p>
                    <CodeBlock 
                      code={`cdn.yourdomain.com  A  [platform-ip]`}
                      id="a-record-example"
                    />
                  </div>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Verifikasi Domain</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Setelah DNS dikonfigurasi, tunggu propagasi (1-24 jam)</li>
                    <li>Klik tombol <strong>Verify DNS</strong></li>
                    <li>Jika berhasil, status akan berubah menjadi "Verified"</li>
                    <li>Aktifkan domain dengan toggle</li>
                  </ol>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Cloudflare Users</h4>
                  <p className="text-sm text-muted-foreground">
                    Jika menggunakan Cloudflare proxy (orange cloud):
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    <li>Verifikasi otomatis mungkin gagal karena IP Cloudflare</li>
                    <li>Gunakan tombol <strong>Force Activate</strong> (admin only)</li>
                    <li>Pastikan Cloudflare sudah dikonfigurasi dengan benar</li>
                  </ul>
                </div>

                <div className="space-y-3 pt-4 border-t bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium flex items-center gap-2">
                    <Shield className="w-4 h-4 text-blue-600" />
                    CDN Domain Behavior
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Domain CDN <strong>hanya dapat digunakan untuk serve script</strong> di path <code>/api/js/*</code>. 
                    Login dan dashboard hanya tersedia di domain utama.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Popunder */}
          <TabsContent value="popunder" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ExternalLink className="w-5 h-5 text-orange-500" />
                  Popunder Campaigns
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <h4 className="font-medium">Membuat Campaign</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Klik menu <strong>Popunders</strong> di sidebar</li>
                    <li>Klik <strong>New Campaign</strong></li>
                    <li>Isi nama campaign</li>
                    <li>Masukkan URL target (satu per baris)</li>
                    <li>Konfigurasi pengaturan (frequency, devices, dll)</li>
                    <li>Klik <strong>Create Campaign</strong></li>
                  </ol>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Pengaturan Campaign</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    <li><strong>URL List</strong> - Daftar URL yang akan dibuka (random)</li>
                    <li><strong>Timer</strong> - Delay sebelum popunder muncul (detik)</li>
                    <li><strong>Frequency</strong> - Maksimal tampil per user per hari</li>
                    <li><strong>Devices</strong> - Target device (desktop/mobile/tablet)</li>
                  </ul>
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium">Embed Popunder</h4>
                  <p className="text-sm text-muted-foreground">
                    Pasang script popunder di website:
                  </p>
                  <CodeBlock 
                    code={`<script src="https://yourdomain.com/api/js/popunder/{campaign-slug}.js"></script>`}
                    id="popunder-embed"
                  />
                </div>

                <div className="space-y-3 pt-4 border-t">
                  <h4 className="font-medium flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" />
                    Analytics
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Lihat statistik campaign di tab Analytics:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    <li><strong>Impressions</strong> - Berapa kali script di-load</li>
                    <li><strong>Clicks</strong> - Berapa kali popunder terbuka</li>
                    <li><strong>CTR</strong> - Click-through rate</li>
                    <li><strong>Devices</strong> - Breakdown per device</li>
                    <li><strong>Referrers</strong> - Sumber traffic teratas</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
