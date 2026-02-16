#!/bin/bash

#############################################
# JSHost VPS Quick Setup Script
# For Ubuntu 22.04/24.04
# Run as root or with sudo
#############################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "=================================================="
echo "       JSHost VPS Quick Setup Script"
echo "=================================================="
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Get domain name
read -p "Enter your domain name (e.g., example.com): " DOMAIN
read -p "Enter database password: " DB_PASSWORD
read -p "Enter admin email: " ADMIN_EMAIL

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)

echo -e "\n${YELLOW}[1/8] Updating system packages...${NC}"
apt update && apt upgrade -y

echo -e "\n${YELLOW}[2/8] Installing dependencies...${NC}"

# Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Yarn
npm install -g yarn

# Python
apt install -y python3 python3-pip python3-venv

# MariaDB
apt install -y mariadb-server mariadb-client
systemctl start mariadb
systemctl enable mariadb

# Nginx
apt install -y nginx
systemctl start nginx
systemctl enable nginx

# Other tools
apt install -y git curl wget unzip certbot python3-certbot-nginx ufw

echo -e "\n${YELLOW}[3/8] Setting up MariaDB database...${NC}"
mysql -e "CREATE DATABASE IF NOT EXISTS jshost_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS 'jshost'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "GRANT ALL PRIVILEGES ON jshost_db.* TO 'jshost'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

echo -e "\n${YELLOW}[4/8] Creating application directory...${NC}"
mkdir -p /var/www/jshost
cd /var/www/jshost

# If code doesn't exist, show message
if [ ! -f "backend/server.py" ]; then
    echo -e "${YELLOW}Please upload your JSHost code to /var/www/jshost${NC}"
    echo "You can use: scp -r /local/path/* root@server:/var/www/jshost/"
    read -p "Press Enter after uploading code..."
fi

echo -e "\n${YELLOW}[5/8] Setting up Backend...${NC}"
cd /var/www/jshost/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MYSQL_URL=mysql+aiomysql://jshost:${DB_PASSWORD}@localhost/jshost_db
JWT_SECRET=${JWT_SECRET}
CORS_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
EOF

echo -e "\n${YELLOW}[6/8] Setting up Frontend...${NC}"
cd /var/www/jshost/frontend

# Create .env file
cat > .env << EOF
REACT_APP_BACKEND_URL=https://${DOMAIN}
EOF

# Install and build
yarn install
yarn build

echo -e "\n${YELLOW}[7/8] Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/jshost << EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        root /var/www/jshost/frontend/build;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        root /var/www/jshost/frontend/build;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

ln -sf /etc/nginx/sites-available/jshost /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo -e "\n${YELLOW}[8/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/jshost-backend.service << EOF
[Unit]
Description=JSHost Backend API
After=network.target mariadb.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/jshost/backend
Environment="PATH=/var/www/jshost/backend/venv/bin"
ExecStart=/var/www/jshost/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jshost-backend
systemctl start jshost-backend

echo -e "\n${YELLOW}Setting up firewall...${NC}"
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "\n${YELLOW}Creating admin user...${NC}"
cd /var/www/jshost/backend
source venv/bin/activate

# Wait for backend to initialize database
sleep 5

python3 << EOF
import asyncio
import bcrypt
from sqlalchemy import text
from database import async_session_maker

async def create_admin():
    password = "Admin@123"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    async with async_session_maker() as db:
        await db.execute(text("""
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (:name, :email, :hash, 'admin', 1)
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """), {"name": "Admin User", "email": "${ADMIN_EMAIL}", "hash": hashed})
        await db.commit()

asyncio.run(create_admin())
EOF

echo -e "\n${GREEN}=================================================="
echo "       Setup Complete!"
echo "==================================================${NC}"
echo ""
echo -e "Domain: ${GREEN}http://${DOMAIN}${NC}"
echo -e "Admin Email: ${GREEN}${ADMIN_EMAIL}${NC}"
echo -e "Admin Password: ${GREEN}Admin@123${NC} (change this!)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Make sure DNS points to this server"
echo "2. Run: sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "3. Login and change admin password"
echo ""
echo -e "View logs: ${GREEN}sudo journalctl -u jshost-backend -f${NC}"
echo ""
