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
- **Admin** (future): Manages system categories and users

## Core Requirements (Static)
1. Per-project domain whitelists (NOT global/user-level)
2. JWT authentication
3. Public JS delivery with domain validation
4. Noop JS (200 status) for denied/unauthorized requests
5. System-seeded categories (read-only)
6. Slug-based routing for projects and scripts

## What's Been Implemented (Feb 14, 2026)
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
- [x] Unit tests: 45 tests for domain validator, normalizer, matcher (all passing)
- [x] Integration tests: 22 tests for delivery endpoint, domain validation API, domain tester (all passing)
- [x] Alembic database migrations (initial schema)
- [x] README with setup & run instructions
- [x] Analytics charts with recharts (pie chart, bar chart, top domains)
- [x] Domain Tester tool in UI (test any domain against project whitelist)

## Prioritized Backlog
### P0 (Critical)
- All core features implemented

### P1 (Important)
- Unit tests for domain validator and delivery logic
- README with setup & run instructions
- Alembic database migrations

### P2 (Nice to have)
- Admin role with user management
- Script versioning
- Rate limiting on JS delivery
- Wildcard domain testing tool in UI
- Chart visualization for access analytics (recharts)
- Bulk domain import
- Script minification option
- API key authentication as alternative to JWT

## Next Tasks
1. Add unit tests for validators and delivery logic
2. Create Alembic migrations
3. Add README with setup instructions
4. Implement analytics charts with recharts
5. Add domain testing tool (test if a domain would match whitelist)
