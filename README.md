# JSHost - Project-Based JavaScript Hosting Platform

A secure platform for hosting, managing, and delivering JavaScript snippets to whitelisted domains with per-project access control.

## Architecture

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI + SQLAlchemy (async) |
| **Database** | MySQL (MariaDB) via aiomysql |
| **Frontend** | React 19 + Shadcn/UI + Tailwind CSS |
| **Auth** | JWT (PyJWT + bcrypt) |

## Features

- **Project Management**: Create and manage JavaScript hosting projects
- **Script Hosting**: Add, edit, and version JavaScript code per project
- **Domain Whitelisting**: Per-project domain access control (exact + wildcard matching)
- **Public JS Delivery**: Embed URL generation with domain-validated delivery
- **Access Analytics**: Track allowed/denied requests with detailed logs
- **Domain Tester**: Test if a domain would be allowed before deploying

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL/MariaDB

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations
alembic upgrade head

# Start the server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Configure environment
# Edit .env with your backend URL

# Start development server
yarn start
```

### Environment Variables

**Backend** (`backend/.env`):
```
MYSQL_URL=mysql+aiomysql://user:password@localhost/jshost_db
JWT_SECRET=your-secret-key
CORS_ORIGINS=*
```

**Frontend** (`frontend/.env`):
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user profile |

### Categories (Read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | List all active categories |

Seeded categories: Website, Landing Page, AMP, Partner, Internal

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List user's projects |
| GET | `/api/projects/{id}` | Get project detail |
| PATCH | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

### Domain Whitelist

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/whitelist` | List whitelist entries |
| POST | `/api/projects/{id}/whitelist` | Add domain pattern |
| PATCH | `/api/projects/{id}/whitelist/{wid}` | Update entry |
| DELETE | `/api/projects/{id}/whitelist/{wid}` | Remove entry |

### Scripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/scripts` | List scripts |
| POST | `/api/projects/{id}/scripts` | Create script |
| GET | `/api/projects/{id}/scripts/{sid}` | Get script |
| PATCH | `/api/projects/{id}/scripts/{sid}` | Update script |
| DELETE | `/api/projects/{id}/scripts/{sid}` | Delete script |

### JS Delivery (Public)

```
GET /api/js/{projectSlug}/{scriptSlug}.js
```

**Delivery Logic:**
1. Resolve project by slug (not found → noop)
2. Check project status (paused → noop)
3. Resolve script by slug (not found → noop)
4. Check script status (disabled → noop)
5. Extract domain from `Origin` or `Referer` header
6. Match domain against project's active whitelist
7. Empty whitelist → deny (noop)
8. Match → serve real JS | No match → noop

**Noop response** (always HTTP 200):
```javascript
/* unauthorized or inactive */
/* noop */
```

**Response Headers:**
```
Content-Type: application/javascript; charset=utf-8
Cache-Control: public, max-age=60
Vary: Origin, Referer
```

### Domain Tester

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/{id}/test-domain` | Test if domain matches whitelist |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/logs` | Get access logs |
| GET | `/api/projects/{id}/analytics` | Get aggregated analytics |

## Domain Pattern Rules

### Allowed Patterns
- `example.com` — exact match
- `sub.example.com` — exact subdomain match
- `*.example.com` — wildcard (matches any subdomain)

### Rejected Patterns
- `https://example.com` — no protocol
- `example.com/path` — no path
- `example.com:8080` — no port
- `*` — bare wildcard
- `a.*.com` — wildcard only as leading `*.`
- `localhost` — no single-label domains

## Embed Usage

```html
<script src="https://your-host.com/api/js/{projectSlug}/{scriptSlug}.js"></script>
```

The script will only load on domains in the project's whitelist. Unauthorized domains receive an empty noop response (200 OK).

## Running Tests

```bash
# Unit tests (validators)
cd /app && python -m pytest tests/test_validators.py -v

# Integration tests (delivery endpoint)
cd /app && python -m pytest tests/test_delivery.py -v

# All tests
cd /app && python -m pytest tests/ -v
```

## Database Migrations

```bash
cd backend

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# View current revision
alembic current
```

## Project Structure

```
/app/
├── backend/
│   ├── server.py          # FastAPI app + all API routes
│   ├── models.py          # SQLAlchemy ORM models
│   ├── database.py        # Async engine + session setup
│   ├── auth.py            # JWT auth utilities
│   ├── validators.py      # Domain validation + matching
│   ├── alembic/           # Database migrations
│   └── .env               # Backend config
├── frontend/
│   ├── src/
│   │   ├── App.js         # Routes
│   │   ├── lib/api.js     # Axios API client
│   │   ├── contexts/      # Auth context
│   │   ├── components/    # Shadcn/UI + Layout
│   │   └── pages/         # Login, Dashboard, Projects, ProjectDetail
│   └── .env               # Frontend config
├── tests/
│   ├── test_validators.py # Unit tests
│   └── test_delivery.py   # Integration tests
└── README.md
```
