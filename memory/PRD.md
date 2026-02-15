# JSHost - Project-Based JavaScript Hosting Platform

## Problem Statement
Build a platform that allows users to create projects, add JavaScript scripts, configure per-project domain whitelists, and generate public embed URLs. The JS delivery endpoint validates requesting domains against project whitelists, serving real JS to allowed domains and noop JS (200 status) to denied ones.

## Architecture
- **Backend**: FastAPI + SQLAlchemy (async) + MySQL (MariaDB)
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Database**: MySQL via aiomysql async driver
- **Auth**: JWT (PyJWT + bcrypt)

## User Personas
- **Web Developer**: Creates projects and popunder campaigns
- **Agency**: Manages multiple projects/campaigns for different clients
- **Admin**: Manages system categories, users, roles, and custom domains

## Core Requirements (Static)
1. Per-project domain whitelists for JS scripts
2. JWT authentication
3. Public JS delivery with domain validation
4. Noop JS (200 status) for denied/unauthorized requests
5. Standalone popunder campaigns with device/country targeting

## What's Been Implemented

### Phase 1 - Core Platform (Feb 14, 2026)
- [x] MySQL database with SQLAlchemy models
- [x] JWT authentication (register, login, token verification)
- [x] Categories seeding (Website, Landing Page, AMP, Partner, Internal)
- [x] Full CRUD for Projects, Scripts, Whitelists
- [x] Public JS delivery endpoint with domain matching
- [x] Domain validation (exact match, wildcard *.example.com)
- [x] Access logging for JS delivery requests
- [x] Dashboard with stats and recent projects
- [x] Frontend with full UI for all features
- [x] Analytics tab with access logs and charts
- [x] Domain Tester tool

### Phase 2 - Admin Features (Feb 14, 2026)
- [x] Dynamic Role-Based Access Control (RBAC) system
- [x] Role management with customizable permissions
- [x] User management (create, edit role, activate/deactivate)
- [x] Category management (CRUD)
- [x] Global custom domain management with DNS verification

### Phase 3 - Popunder Campaign Module V3 (Feb 15, 2026)
- [x] Standalone popunder campaigns (independent from projects)
- [x] **No domain whitelist** - campaigns serve to any domain
- [x] New settings schema:
  - `direct_link` - URL to open in popunder window (required)
  - `timer` - delay in seconds before popunder opens
  - `interval` - hours between shows for same user
  - `devices` - targeted devices (desktop, mobile, tablet)
  - `countries` - targeted countries (ISO codes)
- [x] Self-contained JS payload at `/api/js/popunder/{slug}.js`
- [x] Campaign detail page with Settings and Embed tabs only
- [x] Device detection and interval tracking in JS
- [x] Create/Edit campaign with new settings form
- [x] "Save as New Version" button in script editor (UI only, backend pending)

## Database Schema

### Tables
- **users**: id, email, password_hash, role, is_active, created_at
- **roles**: id, name, description, is_system, permissions (JSON)
- **categories**: id, name, description, is_active
- **projects**: id, user_id, category_id, name, slug, status, created_at
- **project_whitelists**: id, project_id, domain_pattern, is_active
- **scripts**: id, project_id, name, slug, js_code, status
- **access_logs**: id, project_id, script_id, ref_domain, allowed, ip, user_agent
- **custom_domains**: id, domain, status, is_active, platform_ip, resolved_ip
- **popunder_campaigns**: id, user_id, name, slug, status, settings (JSON)

### Popunder Campaign Settings (JSON)
```json
{
  "direct_link": "https://example.com/offer",
  "timer": 0,
  "interval": 24,
  "devices": ["desktop", "mobile", "tablet"],
  "countries": []
}
```

## API Endpoints

### Projects
- GET/POST `/api/projects` - List/Create projects
- GET/PATCH/DELETE `/api/projects/{id}` - Single project ops
- GET/POST `/api/projects/{id}/whitelist` - Whitelist management
- GET/POST `/api/projects/{id}/scripts` - Script management

### Standalone Popunder Campaigns
- GET/POST `/api/popunders` - List/Create campaigns
- GET/PATCH/DELETE `/api/popunders/{id}` - Campaign management

### Public JS Delivery
- GET `/api/js/{projectSlug}/{scriptFile}` - Regular script delivery (with whitelist check)
- GET `/api/js/popunder/{campaignSlug}.js` - Popunder JS delivery (no whitelist check)

## URL Structure
- `/projects` - Projects list
- `/projects/:id` - Project detail (Scripts, Whitelist, Embed, Analytics)
- `/popunders` - Campaigns list
- `/popunders/:id` - Campaign detail (Settings, Embed)

## Test Coverage
- Backend: 13+ pytest tests for popunder V3
- Frontend: UI tests passing

## Credentials
- **Admin**: admin@jshost.com / Admin@123
- **User**: user@jshost.com / User@123

## Prioritized Backlog

### P1 (Next Priority)
- Script versioning backend implementation ("Save as New Version")
- Campaign analytics (impressions, clicks)

### P2 (Nice to have) - FUTURE
- Rate limiting on JS delivery
- Bulk domain import
- Script minification option
- API key authentication as alternative to JWT
- Geo-targeting implementation for popunder JS (server-side country detection)

## Next Tasks
1. Script versioning backend implementation
2. Campaign analytics (impressions, clicks tracking)
3. Geo-targeting for popunders (server-side IP to country detection)
