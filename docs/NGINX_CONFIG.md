# JSHost - Nginx Configuration

Konfigurasi Nginx untuk JSHost dengan support multi CDN domain otomatis.

## Fitur:
- Domain utama: Full access (login, dashboard, API)
- Domain CDN: Hanya serve `/api/js/*` - tanpa akses dashboard
- Domain baru otomatis berfungsi tanpa edit nginx

---

## Full Configuration

Simpan ke `/etc/nginx/sites-available/jshost`:

```nginx
# ============================================
# SERVER BLOCK UTAMA - js.yourdomain.com
# Full access (login, dashboard, API)
# ============================================
server {
    server_name js.yourdomain.com;

    # Backend API - PENTING: gunakan ^~ untuk prioritas tinggi
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    # Frontend (React build)
    location / {
        root /var/www/jshost/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Static files caching - EXCLUDE /api/ paths
    location ~* ^(?!/api/).*\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        root /var/www/jshost/frontend/build;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/js.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/js.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# Redirect HTTP to HTTPS untuk domain utama
server {
    if ($host = js.yourdomain.com) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name js.yourdomain.com;
    return 404;
}

# ============================================
# CATCH-ALL SERVER BLOCK - Semua CDN Domains
# Otomatis handle domain baru tanpa edit nginx!
# ============================================
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    server_name _;

    # SSL - gunakan certificate domain utama
    ssl_certificate /etc/letsencrypt/live/js.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/js.yourdomain.com/privkey.pem;

    # HANYA izinkan /api/js/ untuk CDN domains - NO CACHE
    location ^~ /api/js/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;

        # NO CACHE - script changes are immediately visible
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        
        # CORS untuk cross-domain script loading
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
        
        # Disable nginx proxy cache
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }

    # Popunder JS endpoint
    location ^~ /api/js/popunder/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        add_header Access-Control-Allow-Origin "*" always;
    }

    # Analytics tracking endpoint untuk popunder
    location = /api/popunder-analytics {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type" always;
    }

    # Semua path lain - tampilkan halaman CDN info
    location / {
        default_type text/html;
        return 200 '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDN Endpoint</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e2e8f0;
        }
        .container { text-align: center; padding: 40px; }
        .icon {
            width: 80px; height: 80px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 24px; font-size: 36px;
        }
        h1 { font-size: 24px; margin-bottom: 12px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 8px; }
        code { background: rgba(59,130,246,0.2); padding: 8px 16px; border-radius: 6px; display: inline-block; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⚡</div>
        <h1>CDN Endpoint</h1>
        <p>This domain is configured for JavaScript delivery only.</p>
        <code>/api/js/{project}/{script}.js</code>
    </div>
</body>
</html>';
    }
}
```

---

## Quick Setup Commands

```bash
# 1. Copy konfigurasi
sudo nano /etc/nginx/sites-available/jshost
# Paste konfigurasi di atas

# 2. Enable site
sudo ln -sf /etc/nginx/sites-available/jshost /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 3. Test konfigurasi
sudo nginx -t

# 4. Reload nginx
sudo systemctl reload nginx
```

---

## Behavior Summary

| Domain | Access Level |
|--------|--------------|
| `js.yourdomain.com` | Full (login, dashboard, API) |
| `cdn.example.com` | `/api/js/*` only |
| `cdn.anydomain.com` | `/api/js/*` only |
| `any-new-domain.com` | `/api/js/*` only (auto!) |

---

## Troubleshooting

### API returns 404
Pastikan `location ^~ /api/` ada di konfigurasi dan nginx sudah di-reload.

### Static file .js 404
Pastikan menggunakan regex `^(?!/api/)` untuk exclude `/api/` dari static file caching.

### CDN domain tidak berfungsi
1. Cek DNS domain mengarah ke IP server
2. Cek catch-all server block ada dengan `server_name _;`
3. Cek `listen 80 default_server;` dan `listen 443 ssl default_server;`

### SSL error pada CDN domain
CDN domain menggunakan SSL certificate domain utama. Jika error:
- Gunakan Cloudflare proxy (mereka handle SSL)
- Atau generate wildcard certificate

---

## Disable Cache (Cloudflare)

Jika menggunakan Cloudflare dan script masih di-cache, lakukan konfigurasi berikut:

### Option 1: Page Rules
1. Cloudflare Dashboard → Rules → Page Rules
2. Create Page Rule:
   - URL: `*cdn.yourdomain.com/api/js/*`
   - Setting: Cache Level → **Bypass**
3. Save and Deploy

### Option 2: Cache Rules (Recommended)
1. Cloudflare Dashboard → Caching → Cache Rules
2. Create Rule:
   - Name: "Bypass JS API Cache"
   - Expression: `(http.host contains "cdn" and starts_with(http.request.uri.path, "/api/js/"))`
   - Action: **Bypass cache**
3. Save

### Option 3: Browser Cache TTL
1. Cloudflare Dashboard → Caching → Configuration
2. Browser Cache TTL → **Respect Existing Headers**

### Verify No Cache
```bash
curl -sI "https://cdn.yourdomain.com/api/js/project/script.js" | grep -i cache
# Should show:
# cache-control: no-cache, no-store, must-revalidate
# cf-cache-status: DYNAMIC atau BYPASS
```
