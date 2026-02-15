# JSHost - Project-Based JavaScript Hosting Platform

## Problem Statement
Build a platform that allows users to create projects, add JavaScript scripts, configure per-project domain whitelists, and generate public embed URLs. The JS delivery endpoint validates requesting domains against project whitelists, serving real JS to allowed domains and noop JS (200 status) to denied ones.

## Architecture
- **Backend**: FastAPI + SQLAlchemy (async) + MySQL (MariaDB)
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Database**: MySQL via aiomysql async driver
- **Auth**: JWT (PyJWT + bcrypt)

## What's Been Implemented

### Phase 1 - Core Platform (Feb 14, 2026)
- [x] MySQL database with SQLAlchemy models
- [x] JWT authentication (register, login, token verification)
- [x] Categories seeding
- [x] Full CRUD for Projects, Scripts, Whitelists
- [x] Public JS delivery endpoint with domain matching
- [x] Domain validation (exact match, wildcard)
- [x] Access logging for JS delivery requests
- [x] Dashboard with stats and recent projects
- [x] Domain Tester tool

### Phase 2 - Admin Features (Feb 14, 2026)
- [x] Dynamic Role-Based Access Control (RBAC)
- [x] Role management with customizable permissions
- [x] User management
- [x] Category management
- [x] Global custom domain management

### Phase 3 - Popunder Campaign Module V4 (Feb 15, 2026)
- [x] Standalone popunder campaigns
- [x] Multiple URLs with random selection
- [x] Frequency cap (per user per day)
- [x] Device targeting (desktop/mobile/tablet)
- [x] Country targeting (client-side IP detection)
- [x] Floating Banner HTML injection
- [x] Custom HTML Body injection

### Phase 4 - Analytics & Secondary Script (Feb 15, 2026)
- [x] **Blacklisted Domains List**: Analytics tab shows domains that were denied access (not whitelisted)
  - Domain name, request count, last seen timestamp
  - Real-time tracking from access_logs
- [x] **Secondary Script**: Fallback JS for non-whitelisted domains
  - Per-project configurable JS code
  - Served instead of noop response when domain not whitelisted
  - Configurable via project settings dialog

## Database Schema

### Tables
- **users**: id, email, password_hash, role, is_active
- **roles**: id, name, permissions (JSON)
- **categories**: id, name, description
- **projects**: id, user_id, category_id, name, slug, status, **secondary_script (NEW)**
- **project_whitelists**: id, project_id, domain_pattern, is_active
- **scripts**: id, project_id, name, slug, js_code, status
- **access_logs**: id, project_id, script_id, ref_domain, allowed, ip, user_agent
- **popunder_campaigns**: id, user_id, name, slug, status, settings (JSON)

## API Endpoints

### Projects
- GET/POST `/api/projects` - List/Create
- GET/PATCH/DELETE `/api/projects/{id}` - CRUD
- GET/POST `/api/projects/{id}/whitelist` - Whitelist management
- GET/POST `/api/projects/{id}/scripts` - Script management
- **GET `/api/projects/{id}/blacklisted-domains`** - Get denied domains (NEW)

### Public JS Delivery
- GET `/api/js/{projectSlug}/{scriptFile}` - Serves script or secondary_script or noop
- GET `/api/js/popunder/{campaignSlug}.js` - Popunder JS

## Credentials
- **Admin**: admin@jshost.com / Admin@123
- **User**: user@jshost.com / User@123

## Prioritized Backlog

### P1 (Next)
- Script versioning backend
- Campaign analytics (impressions, clicks)

### P2 (Future)
- Server-side geo-targeting
- Rate limiting
- Bulk domain import
