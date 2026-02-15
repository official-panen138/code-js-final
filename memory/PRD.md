# JSHost - Project-Based JavaScript Hosting Platform

## Problem Statement
Build a platform that allows users to create projects, add JavaScript scripts, configure per-project domain whitelists, and generate public embed URLs. The JS delivery endpoint validates requesting domains against project whitelists, serving real JS to allowed domains and noop JS (200 status) to denied ones.

## Architecture
- **Backend**: FastAPI + SQLAlchemy (async) + MySQL (MariaDB)
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Database**: MySQL via aiomysql async driver
- **Auth**: JWT (PyJWT + bcrypt)

## User Personas
- **Web Developer**: Creates projects, adds scripts, manages whitelists
- **Agency**: Manages multiple projects for different clients
- **Admin**: Manages system categories, users, roles, and custom domains

## Core Requirements (Static)
1. Per-project domain whitelists (NOT global/user-level)
2. JWT authentication
3. Public JS delivery with domain validation
4. Noop JS (200 status) for denied/unauthorized requests
5. System-seeded categories (read-only)
6. Slug-based routing for projects and scripts

## What's Been Implemented

### Phase 1 - Core Platform (Feb 14, 2026)
- [x] MySQL database with SQLAlchemy models (Users, Categories, Projects, Whitelists, Scripts, AccessLogs)
- [x] JWT authentication (register, login, token verification)
- [x] Categories seeding (Website, Landing Page, AMP, Partner, Internal)
- [x] Full CRUD for Projects, Scripts, Whitelists
- [x] Public JS delivery endpoint with domain matching
- [x] Domain validation (exact match, wildcard *.example.com)
- [x] Access logging for JS delivery requests
- [x] Dashboard with stats and recent projects
- [x] Frontend: Login/Register pages, Dashboard, Projects list, Project detail with tabs
- [x] Script code editor with monospace styling
- [x] Embed URL generation and copy-to-clipboard
- [x] Project/script status toggles
- [x] Analytics tab with access logs
- [x] Analytics charts with recharts (pie chart, bar chart, top domains)
- [x] Domain Tester tool in UI (test any domain against project whitelist)
- [x] Unit tests: 45 tests for domain validator, normalizer, matcher
- [x] Alembic database migrations

### Phase 2 - Admin Features (Feb 14, 2026)
- [x] Dynamic Role-Based Access Control (RBAC) system
- [x] Role management with customizable permissions
- [x] User management (create, edit role, activate/deactivate)
- [x] Category management (CRUD)
- [x] Global custom domain management with DNS verification

### Phase 3 - Popunder Campaign Module (Feb 15, 2026)
- [x] PopunderCampaign database model with JSON settings field
- [x] Alembic migration for popunder_campaigns table
- [x] Full CRUD API: `/api/projects/{projectId}/popunders`
  - POST: Create campaign with name, settings (target_url, frequency, delay, dimensions)
  - GET: List campaigns, get single campaign
  - PATCH: Update campaign name, status, settings
  - DELETE: Remove campaign
- [x] Public JS delivery endpoint: `GET /api/js/popunder/{projectSlug}/{campaignSlug}.js`
- [x] Strict server-side validation order:
  1. Resolve project by slug
  2. Check project status (deny if paused)
  3. **Enforce project whitelist** (deny if domain not allowed)
  4. Resolve campaign by slug
  5. Check campaign status (deny if paused)
- [x] Returns noop JS (200 OK) for any validation failure
- [x] Popunder JS engine with localStorage-based frequency tracking
- [x] 15 unit/integration tests for popunder module (all passing)

## Database Schema

### Tables
- **users**: id, email, password_hash, role, is_active, created_at
- **roles**: id, name, description, is_system, permissions (JSON), created_at
- **categories**: id, name, description, is_active
- **projects**: id, user_id, category_id, name, slug, status, created_at
- **project_whitelists**: id, project_id, domain_pattern, is_active, created_at
- **scripts**: id, project_id, name, slug, js_code, status, created_at
- **access_logs**: id, project_id, script_id, ref_domain, allowed, ip, user_agent, created_at
- **custom_domains**: id, domain, status, is_active, platform_ip, resolved_ip, verified_at, created_by, created_at
- **popunder_campaigns**: id, project_id, name, slug, status, settings (JSON), created_at, updated_at

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login
- GET `/api/auth/me` - Get current user

### Projects
- GET/POST `/api/projects` - List/Create projects
- GET/PATCH/DELETE `/api/projects/{id}` - Single project ops
- GET/POST `/api/projects/{id}/whitelist` - Whitelist management
- GET/POST `/api/projects/{id}/scripts` - Script management
- GET `/api/projects/{id}/logs` - Access logs
- GET `/api/projects/{id}/analytics` - Analytics data
- POST `/api/projects/{id}/test-domain` - Domain tester

### Popunder Campaigns
- GET `/api/projects/{id}/popunders` - List campaigns
- POST `/api/projects/{id}/popunders` - Create campaign
- GET `/api/projects/{id}/popunders/{campaignId}` - Get campaign
- PATCH `/api/projects/{id}/popunders/{campaignId}` - Update campaign
- DELETE `/api/projects/{id}/popunders/{campaignId}` - Delete campaign

### Public JS Delivery
- GET `/api/js/{projectSlug}/{scriptFile}` - Regular script delivery
- GET `/api/js/popunder/{projectSlug}/{campaignFile}` - Popunder JS delivery

### Admin
- GET/POST/PATCH/DELETE `/api/categories/*` - Category management
- GET/POST/PATCH/DELETE `/api/roles/*` - Role management
- GET/POST/PATCH `/api/users/*` - User management
- GET/POST/PATCH/DELETE `/api/custom-domains/*` - Domain management

## Test Coverage
- **Total tests**: 82 (all passing)
- **Validator tests**: 45 tests
- **Delivery tests**: 22 tests
- **Popunder tests**: 15 tests

## Credentials
- **Admin**: admin@jshost.com / Admin@123
- **User**: user@jshost.com / User@123

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- All core features implemented

### P1 (Important) - COMPLETED
- Popunder Campaign module
- RBAC system
- Custom domain management

### P2 (Nice to have) - FUTURE
- Frontend UI for popunder management
- Script versioning
- Rate limiting on JS delivery
- Bulk domain import
- Script minification option
- API key authentication as alternative to JWT

## Next Tasks
1. Frontend UI for popunder campaign management (if requested)
2. Script versioning
3. Rate limiting on JS delivery endpoints
