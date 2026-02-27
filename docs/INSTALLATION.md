# JSHost - Installation Guide

Complete installation guide for JSHost JavaScript Hosting Platform.

---

## Table of Contents
1. [Requirements](#requirements)
2. [Quick Install (Ubuntu)](#quick-install-ubuntu)
3. [Manual Installation](#manual-installation)
4. [Docker Installation](#docker-installation)
5. [Configuration](#configuration)
6. [First Run](#first-run)
7. [Troubleshooting](#troubleshooting)

---

## Requirements

### System Requirements
- **OS**: Ubuntu 22.04 LTS / 24.04 LTS (recommended) or Debian 11+
- **RAM**: Minimum 2GB, recommended 4GB
- **CPU**: 1 vCPU minimum, 2 vCPU recommended
- **Storage**: 20GB SSD minimum
- **Network**: Public IP address with ports 80/443 open

### Software Requirements
- Node.js 20.x
- Python 3.11+
- MariaDB 10.6+ or MySQL 8.0+
- Nginx (for production)

---

## Quick Install (Ubuntu)

### One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/jshost/main/install.sh | sudo bash
```

Or download and run manually:
```bash
wget https://raw.githubusercontent.com/your-repo/jshost/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

The script will:
- Install all dependencies
- Setup MariaDB database
- Configure Nginx
- Create systemd service
- Generate admin credentials

---

## Manual Installation

### Step 1: Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Node.js 20.x
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version  # Should show v20.x.x
```

### Step 3: Install Yarn
```bash
sudo npm install -g yarn
```

### Step 4: Install Python 3.11
```bash
sudo apt install -y python3 python3-pip python3-venv
python3 --version  # Should show 3.11+
```

### Step 5: Install MariaDB
```bash
sudo apt install -y mariadb-server mariadb-client
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure installation
sudo mysql_secure_installation
```

### Step 6: Create Database
```bash
sudo mysql -u root -p
```
```sql
CREATE DATABASE jshost_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jshost'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON jshost_db.* TO 'jshost'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 7: Clone Repository
```bash
sudo mkdir -p /var/www/jshost
cd /var/www/jshost
git clone https://github.com/your-repo/jshost.git .
```

### Step 8: Setup Backend
```bash
cd /var/www/jshost/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 9: Configure Backend Environment
```bash
nano /var/www/jshost/backend/.env
```
```env
MYSQL_URL=mysql+aiomysql://jshost:your_secure_password@localhost/jshost_db
JWT_SECRET=your_random_32_char_secret_key_here
CORS_ORIGINS=https://yourdomain.com
```

Generate JWT secret:
```bash
openssl rand -hex 32
```

### Step 10: Setup Frontend
```bash
cd /var/www/jshost/frontend

# Configure environment
nano .env
```
```env
REACT_APP_BACKEND_URL=https://yourdomain.com
```

```bash
# Install and build
yarn install
yarn build
```

### Step 11: Install Nginx
```bash
sudo apt install -y nginx
```

Create Nginx config:
```bash
sudo nano /etc/nginx/sites-available/jshost
```

**Konfigurasi Nginx (Support Multi CDN Domain Otomatis):**
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

    listen 80;
}

# ============================================
# CATCH-ALL SERVER BLOCK - Semua CDN Domains
# Domain baru otomatis berfungsi tanpa edit nginx!
# ============================================
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    server_name _;

    # SSL - akan diupdate setelah certbot
    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

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

    # Analytics tracking endpoint
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
        return 200 '<!DOCTYPE html><html><head><title>CDN Endpoint</title><style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#0f172a;color:#fff;margin:0;}.c{text-align:center;}h1{margin-bottom:10px;}code{background:rgba(59,130,246,0.2);padding:8px 16px;border-radius:6px;}</style></head><body><div class="c"><h1>CDN Endpoint</h1><p>JavaScript delivery only</p><code>/api/js/{project}/{script}.js</code></div></body></html>';
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/jshost /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

**Setelah SSL (Certbot), update ssl_certificate di catch-all block:**
```bash
sudo nano /etc/nginx/sites-available/jshost
# Ganti ssl_certificate dengan:
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

### Step 12: Create Systemd Service
```bash
sudo nano /etc/systemd/system/jshost.service
```
```ini
[Unit]
Description=JSHost Backend
After=network.target mariadb.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/jshost/backend
Environment="PATH=/var/www/jshost/backend/venv/bin"
ExecStart=/var/www/jshost/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jshost
sudo systemctl start jshost
```

### Step 13: SSL Certificate (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Docker Installation

### Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin
```

### Setup
```bash
mkdir -p /opt/jshost
cd /opt/jshost
```

### Create docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: mariadb:10.11
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: jshost_db
      MYSQL_USER: jshost
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql

  backend:
    build: ./backend
    restart: always
    depends_on:
      - db
    environment:
      MYSQL_URL: mysql+aiomysql://jshost:${DB_PASSWORD}@db/jshost_db
      JWT_SECRET: ${JWT_SECRET}
    ports:
      - "8001:8001"

  frontend:
    build:
      context: ./frontend
      args:
        REACT_APP_BACKEND_URL: ${APP_URL}
    restart: always
    ports:
      - "3000:80"

volumes:
  db_data:
```

### Create .env
```bash
nano .env
```
```env
DB_ROOT_PASSWORD=your_root_password
DB_PASSWORD=your_db_password
JWT_SECRET=your_jwt_secret_32_chars
APP_URL=https://yourdomain.com
```

### Build and Run
```bash
docker compose up -d
```

---

## Configuration

### Environment Variables

#### Backend (.env)
| Variable | Description | Example |
|----------|-------------|---------|
| `MYSQL_URL` | Database connection string | `mysql+aiomysql://user:pass@localhost/db` |
| `JWT_SECRET` | Secret key for JWT tokens (min 32 chars) | `your_random_secret` |
| `CORS_ORIGINS` | Allowed origins for CORS | `https://yourdomain.com` |

#### Frontend (.env)
| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_BACKEND_URL` | Backend API URL | `https://yourdomain.com` |

---

## First Run

### Create Admin User
After first run, create admin user:

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
            VALUES ('Admin', 'admin@yourdomain.com', :hash, 'admin', 1)
            ON DUPLICATE KEY UPDATE name=name
        """), {"hash": hashed})
        await db.commit()

asyncio.run(create_admin())
print("Admin user created!")
print("Email: admin@yourdomain.com")
print("Password: Admin@123")
EOF
```

### Access Dashboard
1. Open `https://yourdomain.com` in browser
2. Login with admin credentials
3. **Important**: Change password immediately in Settings!

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
sudo journalctl -u jshost -f

# Common fixes:
# 1. Database connection error
sudo systemctl status mariadb

# 2. Port already in use
sudo lsof -i :8001
sudo kill -9 PID
```

### 502 Bad Gateway
```bash
# Check backend status
sudo systemctl status jshost

# Check nginx config
sudo nginx -t
```

### Database connection error
```bash
# Test connection
mysql -u jshost -p jshost_db -e "SELECT 1"

# Check credentials in .env
cat /var/www/jshost/backend/.env
```

### Permission errors
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/jshost
sudo chmod -R 755 /var/www/jshost
```

---

## Maintenance

### Backup Database
```bash
mysqldump -u jshost -p jshost_db > backup_$(date +%Y%m%d).sql
```

### Update Application
```bash
cd /var/www/jshost
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Update frontend  
cd ../frontend
yarn install
yarn build

# Restart service
sudo systemctl restart jshost
```

### View Logs
```bash
# Backend logs
sudo journalctl -u jshost -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start backend | `sudo systemctl start jshost` |
| Stop backend | `sudo systemctl stop jshost` |
| Restart backend | `sudo systemctl restart jshost` |
| View backend logs | `sudo journalctl -u jshost -f` |
| Restart nginx | `sudo systemctl restart nginx` |
| Test nginx config | `sudo nginx -t` |
| Renew SSL | `sudo certbot renew` |

---

*Documentation version: 1.0 | Last updated: February 2026*
