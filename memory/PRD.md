# JSHost - Project-Based JavaScript Hosting Platform

## Problem Statement
Build a platform that allows users to create projects, add JavaScript scripts, configure per-script domain whitelists, and generate public embed URLs. The JS delivery endpoint validates requesting domains against script whitelists, serving real JS to allowed domains and noop JS (200 status) to denied ones.

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
- [x] Full CRUD for Projects, Scripts
- [x] Public JS delivery endpoint with domain matching
- [x] Domain validation (exact match, wildcard)
- [x] Access logging for JS delivery requests
- [x] Dashboard with stats and recent projects

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
- [x] **Blacklisted Domains List**: Analytics tab shows domains that were denied access
- [x] **Secondary Script V2 - Two-Mode Feature**: Enhanced fallback content for non-whitelisted domains
  - **Mode A (Full JS Script)**: Raw JavaScript code served to non-whitelisted domains
  - **Mode B (Link Injection)**: Generates hidden HTML links for SEO/backlink purposes
- [x] **Per-Script Secondary Script**: Moved from project-level to script-level
- [x] **Secondary Script Security**: Blocks direct browser access, only allows script tag loading

### Phase 5 - Per-Script Whitelist & Enhanced Analytics (Feb 15, 2026)
- [x] **Per-Script Domain Whitelists**: Each script has its own whitelist
  - Whitelist management moved from project-level to script-level
  - ScriptWhitelist model with script_id foreign key
  - Whitelist dialog accessible from shield button on each script card
  - Domain tester integrated into each script's whitelist dialog
  - Whitelist count badge shown on script cards
- [x] **Script URL in Analytics**: Analytics by_script section shows which script URLs were accessed
  - Table with Script Name, URL, Allowed count, Denied count, Total
  - Format: /api/js/{project_slug}/{script_slug}.js
- [x] **Clear Access Logs**: Button to clear all access logs for a project
  - Confirmation dialog before deletion
  - DELETE /api/projects/{id}/logs endpoint

## Database Schema

### Tables
- **users**: id, email, password_hash, role, is_active
- **roles**: id, name, permissions (JSON)
- **categories**: id, name, description
- **projects**: id, user_id, category_id, name, slug, status
- **scripts**: id, project_id, name, slug, js_code, status, secondary_script, secondary_script_mode, secondary_script_links (JSON)
- **script_whitelists**: id, script_id, domain_pattern, is_active (NEW - per-script whitelists)
- **access_logs**: id, project_id, script_id, ref_domain, allowed, ip, user_agent
- **popunder_campaigns**: id, user_id, name, slug, status, settings (JSON)

## API Endpoints

### Projects
- GET/POST `/api/projects` - List/Create
- GET/PATCH/DELETE `/api/projects/{id}` - CRUD
- GET/POST `/api/projects/{id}/scripts` - Script management
- GET `/api/projects/{id}/analytics` - Analytics with by_script section
- GET `/api/projects/{id}/logs` - Access logs
- DELETE `/api/projects/{id}/logs` - Clear all access logs
- GET `/api/projects/{id}/blacklisted-domains` - Denied domains

### Per-Script Whitelist
- GET `/api/projects/{id}/scripts/{sid}/whitelist` - List script whitelists
- POST `/api/projects/{id}/scripts/{sid}/whitelist` - Add whitelist entry
- PATCH `/api/projects/{id}/scripts/{sid}/whitelist/{wid}` - Update (toggle is_active)
- DELETE `/api/projects/{id}/scripts/{sid}/whitelist/{wid}` - Remove whitelist entry
- POST `/api/projects/{id}/scripts/{sid}/test-domain` - Test domain against script whitelist

### Public JS Delivery
- GET `/api/js/{projectSlug}/{scriptFile}` - Serves script or secondary_script or noop
- GET `/api/js/popunder/{campaignSlug}.js` - Popunder JS

## Credentials
- **Admin**: admin@jshost.com / Admin@123
- **User**: user@jshost.com / User@123

## Known Issues
- **MariaDB Instability**: The MariaDB service in this environment has crashed multiple times. If backend fails, check: `sudo supervisorctl status` and restart MariaDB if needed.

## Prioritized Backlog

### P1 (Next)
- Script versioning backend ("Save as new version" feature)
- Campaign analytics (impressions, clicks)

### P2 (Future)
- Server-side geo-targeting
- Rate limiting
- Bulk domain import
