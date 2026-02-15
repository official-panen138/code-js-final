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
- [x] **Script Access Details**: Detailed breakdown of domain + script URL combinations
  - Shows which specific domains accessed which specific script URLs
  - Includes status (Allowed/Denied), request count, and last access time
  - Helps identify exactly which domains are using which scripts
- [x] **Clear Access Logs**: Button to clear all access logs for a project
  - Confirmation dialog before deletion
  - DELETE /api/projects/{id}/logs endpoint

### Phase 6 - Full Referrer URL Tracking (Feb 15, 2026)
- [x] **Full Referrer URL Capture**: Captures complete referrer URL, not just domain
  - New `referer_url` column in access_logs table (VARCHAR 2048)
  - _log_access function captures full Referer header from requests
  - Enables tracking exactly which pages load your scripts

### Phase 7 - Analytics Tab Redesign with Per-Row Delete (Feb 15, 2026)
- [x] **Global Analytics Tab Restored**: Analytics tab back in main project view
  - Three tabs: Scripts, Embed, Analytics
  - Summary stats: Total Requests, Allowed, Denied
- [x] **Individual Log Entries Table**: Shows flat list of individual access log entries
  - Columns: Source URL, Link Script, Status, Requests, Last Access, Action
  - Source URL and Link Script are clickable links
  - Status shows "Allowed" (green) or "Denied" (red) badge
  - Row colors: green background for Allowed, red for Denied
- [x] **Per-Row Delete**: Each log entry has delete button
  - DELETE /api/projects/{id}/logs/{log_id} endpoint
  - Removes specific log entry without affecting others
  - Updates summary stats after deletion
- [x] **New API Endpoint**: GET /api/projects/{id}/analytics/logs
  - Returns flat list of individual log entries with IDs
  - Response: { logs: [...], summary: { total, allowed, denied }, pagination: {...} }
- [x] **Pagination for Large Datasets**: 
  - 20 logs per page with Prev/Next navigation
  - Shows "Showing X - Y of Z logs" info
  - Works in both Analytics tab and Script modal
  - API params: page, per_page with proper offset/limit

### Phase 8 - Ownership & Visibility Rules (Feb 15, 2026)
- [x] **Project Ownership**: Projects are scoped to the creating user
  - Regular users can only see/access/modify their own projects
  - Admin users can see and manage ALL projects
  - 404 returned for unauthorized access attempts (no info leak)
- [x] **Popunder Campaign Ownership**: Campaigns are scoped to the creating user
  - Regular users can only see/access/modify their own campaigns
  - Admin users can see and manage ALL campaigns
  - Same 404 pattern for unauthorized access
- [x] **Helper Functions**: 
  - `is_user_admin(db, user_id)` - Checks if user has admin role
  - `get_user_project(db, project_id, user_id, is_admin)` - Gets project with ownership check
  - `get_user_campaign(db, campaign_id, user_id, is_admin)` - Gets campaign with ownership check
- [x] **Backend Testing**: 22/22 tests passed (100% coverage)

### Phase 9 - User Name Field (Feb 15, 2026)
- [x] **User Name**: Added optional name field to users
  - Database: Added `name` VARCHAR(100) column to users table
  - Registration: Users can optionally provide their name during signup
  - User Management: Admin can set/edit user names when creating/editing users
  - UI: User list shows name prominently with email below
  - API: Name included in all user-related responses

## Database Schema

### Tables
- **users**: id, email, password_hash, role, is_active
- **roles**: id, name, permissions (JSON)
- **categories**: id, name, description
- **projects**: id, user_id, category_id, name, slug, status
- **scripts**: id, project_id, name, slug, js_code, status, secondary_script, secondary_script_mode, secondary_script_links (JSON)
- **script_whitelists**: id, script_id, domain_pattern, is_active (NEW - per-script whitelists)
- **access_logs**: id, project_id, script_id, ref_domain, referer_url, allowed, ip, user_agent
- **popunder_campaigns**: id, user_id, name, slug, status, settings (JSON)

## API Endpoints

### Projects
- GET/POST `/api/projects` - List/Create
- GET/PATCH/DELETE `/api/projects/{id}` - CRUD
- GET/POST `/api/projects/{id}/scripts` - Script management
- GET `/api/projects/{id}/analytics` - Aggregated analytics (charts)
- GET `/api/projects/{id}/analytics/logs` - Individual log entries with IDs (for Analytics tab)
- GET `/api/projects/{id}/logs` - Access logs
- DELETE `/api/projects/{id}/logs` - Clear all access logs
- DELETE `/api/projects/{id}/logs/{log_id}` - Delete single log entry (NEW)
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
- **Admin**: admin@jshost.com / Admin@123 (role=admin, can see all projects/campaigns)
- **User**: user@jshost.com / User@123 (role=user, can only see own projects/campaigns)

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
