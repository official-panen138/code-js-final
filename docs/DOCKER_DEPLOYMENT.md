# JSHost Docker Deployment

Alternative deployment using Docker and Docker Compose.

---

## Prerequisites

Install Docker and Docker Compose on your Ubuntu server:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER
```

---

## Quick Start

### 1. Create project directory
```bash
mkdir -p /opt/jshost
cd /opt/jshost
```

### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  mariadb:
    image: mariadb:10.11
    container_name: jshost-db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: jshost_db
      MYSQL_USER: jshost
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mariadb_data:/var/lib/mysql
    networks:
      - jshost-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: jshost-backend
    restart: always
    depends_on:
      - mariadb
    environment:
      MYSQL_URL: mysql+aiomysql://jshost:${DB_PASSWORD}@mariadb/jshost_db
      JWT_SECRET: ${JWT_SECRET}
      CORS_ORIGINS: ${CORS_ORIGINS}
    ports:
      - "8001:8001"
    networks:
      - jshost-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        REACT_APP_BACKEND_URL: ${REACT_APP_BACKEND_URL}
    container_name: jshost-frontend
    restart: always
    ports:
      - "3000:80"
    networks:
      - jshost-network

  nginx:
    image: nginx:alpine
    container_name: jshost-nginx
    restart: always
    depends_on:
      - backend
      - frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - certbot_data:/var/www/certbot
    networks:
      - jshost-network

volumes:
  mariadb_data:
  certbot_data:

networks:
  jshost-network:
    driver: bridge
```

### 3. Create .env file
```bash
nano .env
```

```env
# Database
DB_ROOT_PASSWORD=your_root_password_here
DB_PASSWORD=your_db_password_here

# JWT
JWT_SECRET=your_very_long_random_secret_key_minimum_32_chars

# Domain
DOMAIN=yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
REACT_APP_BACKEND_URL=https://yourdomain.com
```

### 4. Create Backend Dockerfile
```bash
mkdir -p backend
nano backend/Dockerfile
```

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 5. Create Frontend Dockerfile
```bash
mkdir -p frontend
nano frontend/Dockerfile
```

```dockerfile
# Build stage
FROM node:20-alpine as build

WORKDIR /app

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .
RUN yarn build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 6. Create Nginx configuration
```bash
mkdir -p nginx
nano nginx/nginx.conf
```

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream backend {
        server backend:8001;
    }

    upstream frontend {
        server frontend:80;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 7. Upload your code
Copy your backend and frontend code to the respective directories.

### 8. Build and start
```bash
# Build images
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

---

## Useful Commands

```bash
# Stop all services
docker compose down

# Restart a service
docker compose restart backend

# View logs for specific service
docker compose logs -f backend

# Enter a container
docker compose exec backend bash

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d

# Clean up unused images
docker system prune -a
```

---

## SSL with Let's Encrypt

### Initial setup (without SSL)
First, start without SSL to get the certificate:

1. Temporarily modify nginx.conf to only listen on port 80
2. Run: `docker compose up -d`
3. Get certificate:
```bash
docker run -it --rm \
  -v certbot_data:/var/www/certbot \
  -v ./nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com
```
4. Copy certificates:
```bash
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```
5. Enable SSL in nginx.conf and restart

---

## Backup & Restore

### Backup database
```bash
docker compose exec mariadb mysqldump -u jshost -p jshost_db > backup.sql
```

### Restore database
```bash
cat backup.sql | docker compose exec -T mariadb mysql -u jshost -p jshost_db
```

---
