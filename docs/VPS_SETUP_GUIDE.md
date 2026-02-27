# JSHost Platform - VPS Setup Guide (Ubuntu 22.04/24.04)

Complete guide to deploy JSHost on an Ubuntu VPS server.

---

## Table of Contents
1. [Server Requirements](#1-server-requirements)
2. [Initial Server Setup](#2-initial-server-setup)
3. [Install Dependencies](#3-install-dependencies)
4. [Setup MariaDB Database](#4-setup-mariadb-database)
5. [Deploy Application](#5-deploy-application)
6. [Configure Environment](#6-configure-environment)
7. [Setup Nginx Reverse Proxy](#7-setup-nginx-reverse-proxy)
8. [SSL Certificate (HTTPS)](#8-ssl-certificate-https)
9. [Setup Systemd Services](#9-setup-systemd-services)
10. [Firewall Configuration](#10-firewall-configuration)
11. [First Login & Admin Setup](#11-first-login--admin-setup)
12. [Maintenance & Troubleshooting](#12-maintenance--troubleshooting)

---

## 1. Server Requirements

### Minimum Specs
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS
- **RAM**: 2 GB (4 GB recommended)
- **CPU**: 1 vCPU (2 vCPU recommended)
- **Storage**: 20 GB SSD
- **Network**: Public IP address

### Domain Setup
Point your domain to your server's IP address:
```
A Record: yourdomain.com -> YOUR_SERVER_IP
A Record: www.yourdomain.com -> YOUR_SERVER_IP
```

---

## 2. Initial Server Setup

### Connect to your server
```bash
ssh root@YOUR_SERVER_IP
```

### Update system packages
```bash
apt update && apt upgrade -y
```

### Create a non-root user (recommended)
```bash
adduser jshost
usermod -aG sudo jshost
su - jshost
```

### Set timezone
```bash
sudo timedatectl set-timezone Asia/Jakarta  # Change to your timezone
```

---

## 3. Install Dependencies

### Install Node.js 20.x
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version  # Should show v20.x.x
```

### Install Yarn
```bash
sudo npm install -g yarn
yarn --version
```

### Install Python 3.11+ and pip
```bash
sudo apt install -y python3 python3-pip python3-venv
python3 --version  # Should show 3.11+
```

### Install MariaDB
```bash
sudo apt install -y mariadb-server mariadb-client
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

### Install Nginx
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Install Git
```bash
sudo apt install -y git
```

### Install additional tools
```bash
sudo apt install -y curl wget unzip htop
```

---

## 4. Setup MariaDB Database

### Secure MariaDB installation
```bash
sudo mysql_secure_installation
```
- Set root password: YES (create a strong password)
- Remove anonymous users: YES
- Disallow root login remotely: YES
- Remove test database: YES
- Reload privilege tables: YES

### Create database and user
```bash
sudo mysql -u root -p
```

Run these SQL commands:
```sql
CREATE DATABASE jshost_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jshost'@'localhost' IDENTIFIED BY 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON jshost_db.* TO 'jshost'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Test connection
```bash
mysql -u jshost -p jshost_db
# Enter your password, then type: SHOW TABLES; EXIT;
```

---

## 5. Deploy Application

### Create application directory
```bash
sudo mkdir -p /var/www/jshost
sudo chown $USER:$USER /var/www/jshost
cd /var/www/jshost
```

### Clone or upload your code
**Option A: Clone from Git**
```bash
git clone https://github.com/YOUR_USERNAME/jshost.git .
```

**Option B: Upload via SCP**
```bash
# From your local machine:
scp -r /path/to/jshost/* jshost@YOUR_SERVER_IP:/var/www/jshost/
```

### Setup Backend
```bash
cd /var/www/jshost/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print('FastAPI OK')"
```

### Setup Frontend
```bash
cd /var/www/jshost/frontend

# Install dependencies
yarn install

# Build for production
yarn build
```

---

## 6. Configure Environment

### Backend Environment (.env)
```bash
cd /var/www/jshost/backend
nano .env
```

Add these variables:
```env
# Database
MYSQL_URL=mysql+aiomysql://jshost:YOUR_SECURE_PASSWORD@localhost/jshost_db

# JWT Secret (generate a random string)
JWT_SECRET=your_very_long_random_secret_key_here_minimum_32_chars

# CORS (your domain)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional: MongoDB (if using)
MONGO_URL=mongodb://localhost:27017
DB_NAME=jshost
```

Generate a secure JWT secret:
```bash
openssl rand -hex 32
```

### Frontend Environment (.env)
```bash
cd /var/www/jshost/frontend
nano .env
```

Add:
```env
REACT_APP_BACKEND_URL=https://yourdomain.com
```

### Rebuild frontend after .env changes
```bash
cd /var/www/jshost/frontend
yarn build
```

---

## 7. Setup Nginx Reverse Proxy

### Create Nginx configuration
```bash
sudo nano /etc/nginx/sites-available/jshost
```

Add this configuration (supports multiple CDN domains automatically):
```nginx
# ============================================
# SERVER BLOCK UTAMA - yourdomain.com
# Full access (login, dashboard, API)
# ============================================
server {
    server_name yourdomain.com www.yourdomain.com;

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
        proxy_read_timeout 300;
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
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# Redirect HTTP to HTTPS
server {
    if ($host = yourdomain.com) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
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
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # HANYA izinkan /api/js/ untuk CDN domains
    location ^~ /api/js/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;

        # CORS untuk cross-domain script loading
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
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

**Catatan Penting:**
- Domain utama (`yourdomain.com`) → Full access (login, dashboard, semua fitur)
- Domain CDN lainnya → Otomatis hanya serve `/api/js/*` tanpa perlu edit nginx
- Setiap domain baru yang ditambahkan di dashboard langsung berfungsi!

### Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/jshost /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

---

## 8. SSL Certificate (HTTPS)

### Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Obtain SSL certificate
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts:
- Enter your email address
- Agree to terms of service
- Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### Auto-renewal (already configured by Certbot)
```bash
# Test renewal
sudo certbot renew --dry-run
```

---

## 9. Setup Systemd Services

### Backend Service
```bash
sudo nano /etc/systemd/system/jshost-backend.service
```

Add:
```ini
[Unit]
Description=JSHost Backend API
After=network.target mariadb.service

[Service]
Type=simple
User=jshost
Group=jshost
WorkingDirectory=/var/www/jshost/backend
Environment="PATH=/var/www/jshost/backend/venv/bin"
ExecStart=/var/www/jshost/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and start services
```bash
sudo systemctl daemon-reload
sudo systemctl enable jshost-backend
sudo systemctl start jshost-backend

# Check status
sudo systemctl status jshost-backend
```

### View logs
```bash
# Backend logs
sudo journalctl -u jshost-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 10. Firewall Configuration

### Setup UFW
```bash
sudo apt install -y ufw

# Allow SSH (important! Don't lock yourself out)
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 11. First Login & Admin Setup

### Initialize the database
The backend will automatically create tables on first run. Check logs:
```bash
sudo journalctl -u jshost-backend | grep -i "seeded"
```

### Create Admin User
Since public registration is disabled, you need to create the admin user manually:

```bash
cd /var/www/jshost/backend
source venv/bin/activate
python3 << 'EOF'
import asyncio
import bcrypt
from sqlalchemy import text
from database import async_session_maker

async def create_admin():
    password = "Admin@123"  # Change this!
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    async with async_session_maker() as db:
        await db.execute(text("""
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (:name, :email, :hash, 'admin', 1)
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """), {"name": "Admin User", "email": "admin@yourdomain.com", "hash": hashed})
        await db.commit()
        print("Admin user created!")
        print("Email: admin@yourdomain.com")
        print("Password: Admin@123")

asyncio.run(create_admin())
EOF
```

### Access the application
1. Open: `https://yourdomain.com`
2. Login with admin credentials
3. **Change your password immediately** in Settings

---

## 12. Maintenance & Troubleshooting

### Common Commands

```bash
# Restart backend
sudo systemctl restart jshost-backend

# Restart Nginx
sudo systemctl restart nginx

# View backend logs
sudo journalctl -u jshost-backend -f --no-pager -n 100

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
htop
```

### Update Application

```bash
cd /var/www/jshost

# Pull latest code
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Update frontend
cd ../frontend
yarn install
yarn build

# Restart backend
sudo systemctl restart jshost-backend
```

### Database Backup

```bash
# Create backup
mysqldump -u jshost -p jshost_db > backup_$(date +%Y%m%d).sql

# Restore backup
mysql -u jshost -p jshost_db < backup_20260215.sql
```

### Common Issues

#### Backend won't start
```bash
# Check logs
sudo journalctl -u jshost-backend -n 50

# Common fixes:
# 1. Database connection error - check MYSQL_URL in .env
# 2. Port already in use - kill existing process
sudo lsof -i :8001
sudo kill -9 PID
```

#### 502 Bad Gateway
```bash
# Backend not running
sudo systemctl status jshost-backend

# Wrong proxy settings
sudo nginx -t
sudo systemctl reload nginx
```

#### Permission denied
```bash
# Fix ownership
sudo chown -R jshost:jshost /var/www/jshost

# Fix permissions
chmod -R 755 /var/www/jshost
```

---

## Quick Reference

| Service | Command |
|---------|---------|
| Start Backend | `sudo systemctl start jshost-backend` |
| Stop Backend | `sudo systemctl stop jshost-backend` |
| Restart Backend | `sudo systemctl restart jshost-backend` |
| Backend Logs | `sudo journalctl -u jshost-backend -f` |
| Restart Nginx | `sudo systemctl restart nginx` |
| Nginx Logs | `sudo tail -f /var/log/nginx/error.log` |
| Renew SSL | `sudo certbot renew` |

---

## Security Checklist

- [ ] Change default admin password
- [ ] Use strong database password
- [ ] Enable firewall (UFW)
- [ ] Install SSL certificate
- [ ] Disable root SSH login
- [ ] Setup SSH key authentication
- [ ] Regular backups
- [ ] Keep system updated (`sudo apt update && sudo apt upgrade`)

---

## Support

For issues and questions:
- Check logs first: `sudo journalctl -u jshost-backend -f`
- Review Nginx error log: `sudo tail -f /var/log/nginx/error.log`

---

*Last updated: February 2026*
