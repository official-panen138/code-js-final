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
2. Per-campaign independent whitelists for popunders
3. JWT authentication
4. Public JS delivery with domain validation
5. Noop JS (200 status) for denied/unauthorized requests

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

### Phase 3 - Popunder Campaign Module (Feb 15, 2026)
- [x] PopunderCampaign database model (independent from projects)
- [x] PopunderWhitelist table for campaign-specific whitelists
- [x] Full CRUD API: `/api/popunders`
- [x] Public JS delivery: `GET /api/js/popunder/{campaignSlug}.js`
- [x] Campaign-specific whitelist management
- [x] Domain tester for campaigns

### Phase 4 - Separation of Projects & Campaigns (Feb 15, 2026)
- [x] **Separate sidebar menus**: Projects and Popunders as independent modules
- [x] **Popunders List Page** (`/popunders`): Create, list, delete campaigns
- [x] **Popunder Detail Page** (`/popunders/:id`): Settings, Whitelist, Embed tabs
- [x] **Independent whitelists**: Campaigns have their own domain whitelists
- [x] **Removed Popunders tab** from Project detail page
- [x] **Script versioning**: "Save as New Version" button in script editor

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
- **popunder_whitelists**: id, campaign_id, domain_pattern, is_active

## API Endpoints

### Projects
- GET/POST `/api/projects` - List/Create projects
- GET/PATCH/DELETE `/api/projects/{id}` - Single project ops
- GET/POST `/api/projects/{id}/whitelist` - Whitelist management
- GET/POST `/api/projects/{id}/scripts` - Script management

### Standalone Popunder Campaigns
- GET/POST `/api/popunders` - List/Create campaigns
- GET/PATCH/DELETE `/api/popunders/{id}` - Campaign management
- GET/POST/DELETE `/api/popunders/{id}/whitelist` - Campaign whitelist
- POST `/api/popunders/{id}/test-domain` - Domain tester

### Public JS Delivery
- GET `/api/js/{projectSlug}/{scriptFile}` - Regular script delivery
- GET `/api/js/popunder/{campaignSlug}.js` - Popunder JS delivery

## URL Structure
- `/projects` - Projects list
- `/projects/:id` - Project detail (Scripts, Whitelist, Embed, Analytics)
- `/popunders` - Campaigns list
- `/popunders/:id` - Campaign detail (Settings, Whitelist, Embed)

## Test Coverage
- Backend: 21 pytest tests (100% passing)
- Frontend: 15 UI tests (100% passing)

## Credentials
- **Admin**: admin@jshost.com / Admin@123
- **User**: user@jshost.com / User@123

## Prioritized Backlog

### P2 (Nice to have) - FUTURE
- Rate limiting on JS delivery
- Bulk domain import
- Script minification option
- API key authentication as alternative to JWT
- Campaign analytics/tracking

## Next Tasks
1. Rate limiting on JS delivery endpoints
2. Bulk domain import feature
3. Campaign analytics (impressions, clicks)
