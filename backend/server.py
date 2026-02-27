from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import selectinload
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from slugify import slugify

from database import get_db, init_db, async_session_maker
from models import User, Category, Project, Script, ScriptWhitelist, AccessLog, Role, CustomDomain, PopunderCampaign, CampaignAnalytics
from auth import hash_password, verify_password, create_token, get_current_user, require_permission
from validators import validate_domain_pattern, normalize_domain, is_domain_allowed

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ─── App Setup ───
app = FastAPI(title="JSHost Platform")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NOOP_JS = "/* unauthorized or inactive */\n/* noop */"

JS_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=60",
    "Vary": "Origin, Referer",
}


# ─── CDN Domain Middleware ───
# CDN domains should ONLY serve JS files, not the full app UI
@app.middleware("http")
async def cdn_domain_middleware(request: Request, call_next):
    """
    Detect if request is coming from a configured CDN domain.
    CDN domains should only serve /api/js/* endpoints - all other paths return a CDN info page.
    This allows separation of: Main App (login, dashboard) vs CDN (script delivery only).
    """
    host = request.headers.get("host", "").split(":")[0].lower()  # Remove port if present
    path = request.url.path
    
    # Skip for empty host
    if not host:
        return await call_next(request)
    
    # Check if this is a CDN domain (not the main app domain)
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(CustomDomain).where(
                    and_(
                        CustomDomain.domain == host,
                        CustomDomain.is_active == True,
                        CustomDomain.status == 'verified'
                    )
                )
            )
            cdn_domain = result.scalar_one_or_none()
            
            if cdn_domain:
                # This is a CDN domain - only allow /api/js/* paths
                if path.startswith("/api/js/"):
                    # Allow JS delivery
                    return await call_next(request)
                else:
                    # Return a nice CDN info page for all other paths
                    cdn_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDN - {host}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e2e8f0;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            max-width: 500px;
        }}
        .icon {{
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            font-size: 36px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #f8fafc;
        }}
        p {{
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 24px;
        }}
        .domain {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 12px 20px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: #60a5fa;
        }}
        .note {{
            margin-top: 24px;
            font-size: 12px;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⚡</div>
        <h1>CDN Endpoint</h1>
        <p>This domain is configured as a CDN endpoint for JavaScript delivery only.</p>
        <div class="domain">{host}</div>
        <p class="note">Scripts are available at: /api/js/[project]/[script].js</p>
    </div>
</body>
</html>'''
                    return HTMLResponse(content=cdn_html, status_code=200)
    except Exception as e:
        # If database error, proceed normally
        logger.error(f"CDN middleware error: {e}")
        pass
    
    # Not a CDN domain - proceed normally (full app access)
    return await call_next(request)


# ─── Pydantic Schemas ───
class UserLogin(BaseModel):
    email: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    category_id: int
    status: Optional[str] = 'active'

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = None

class WhitelistCreate(BaseModel):
    domain_pattern: str

class WhitelistUpdate(BaseModel):
    domain_pattern: Optional[str] = None
    is_active: Optional[bool] = None

class SecondaryScriptLink(BaseModel):
    url: str
    keyword: str

class ScriptCreate(BaseModel):
    name: str
    js_code: str
    status: Optional[str] = 'active'
    secondary_script: Optional[str] = None
    secondary_script_mode: Optional[str] = 'js'
    secondary_script_links: Optional[List[SecondaryScriptLink]] = None

class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    js_code: Optional[str] = None
    status: Optional[str] = None
    secondary_script: Optional[str] = None
    secondary_script_mode: Optional[str] = None
    secondary_script_links: Optional[List[SecondaryScriptLink]] = None

class DomainTestRequest(BaseModel):
    domain: str

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserCreate(BaseModel):
    name: Optional[str] = None
    email: str
    password: str
    role: Optional[str] = 'user'

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class CustomDomainCreate(BaseModel):
    domain: str

class CustomDomainUpdate(BaseModel):
    is_active: Optional[bool] = None


class PopunderCampaignSettings(BaseModel):
    url_list: str  # newline-separated URLs to open in popunder (random selection)
    timer: Optional[int] = 0  # delay in seconds before popunder opens
    frequency: Optional[int] = 1  # max shows per user per day
    devices: Optional[List[str]] = ["desktop", "mobile", "tablet"]  # targeted devices
    countries: Optional[List[str]] = []  # targeted countries (ISO codes), empty = all
    floating_banner: Optional[str] = ""  # HTML code for floating banner
    html_body: Optional[str] = ""  # Custom HTML to inject in body

class PopunderCampaignCreate(BaseModel):
    name: str
    settings: PopunderCampaignSettings
    status: Optional[str] = 'active'

class PopunderCampaignUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[PopunderCampaignSettings] = None
    status: Optional[str] = None

class CampaignAnalyticsEvent(BaseModel):
    campaign_id: int
    event_type: str  # 'impression' or 'click'
    referer_url: Optional[str] = None
    target_url: Optional[str] = None
    device_type: Optional[str] = None


# ─── Helpers ───
def user_to_dict(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None}

def category_to_dict(c: Category) -> dict:
    return {"id": c.id, "name": c.name, "description": c.description, "is_active": c.is_active}

def project_to_dict(p: Project, include_relations: bool = False) -> dict:
    d = {
        "id": p.id, "user_id": p.user_id, "category_id": p.category_id,
        "name": p.name, "slug": p.slug, "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if include_relations:
        d["category"] = category_to_dict(p.category) if p.category else None
        d["scripts"] = [script_to_dict(s, include_whitelists=True) for s in p.scripts] if p.scripts else []
        d["script_count"] = len(p.scripts) if p.scripts else 0
    return d

def whitelist_to_dict(w: ScriptWhitelist) -> dict:
    return {"id": w.id, "script_id": w.script_id, "domain_pattern": w.domain_pattern, "is_active": w.is_active, "created_at": w.created_at.isoformat() if w.created_at else None}

def script_to_dict(s: Script, include_whitelists: bool = False) -> dict:
    d = {"id": s.id, "project_id": s.project_id, "name": s.name, "slug": s.slug, "js_code": s.js_code, "status": s.status, "secondary_script": s.secondary_script or "", "secondary_script_mode": s.secondary_script_mode or "js", "secondary_script_links": s.secondary_script_links or [], "created_at": s.created_at.isoformat() if s.created_at else None}
    if include_whitelists:
        d["whitelists"] = [whitelist_to_dict(w) for w in s.whitelists] if s.whitelists else []
        d["whitelist_count"] = len(s.whitelists) if s.whitelists else 0
    return d

def log_to_dict(l: AccessLog) -> dict:
    return {"id": l.id, "project_id": l.project_id, "script_id": l.script_id, "ref_domain": l.ref_domain, "referer_url": l.referer_url, "allowed": l.allowed, "ip": l.ip, "user_agent": l.user_agent, "created_at": l.created_at.isoformat() if l.created_at else None}

def role_to_dict(r: Role) -> dict:
    return {"id": r.id, "name": r.name, "description": r.description, "is_system": r.is_system, "permissions": r.permissions or [], "created_at": r.created_at.isoformat() if r.created_at else None}

def custom_domain_to_dict(d: CustomDomain) -> dict:
    return {
        "id": d.id, "domain": d.domain, "status": d.status,
        "is_active": d.is_active, "platform_ip": d.platform_ip,
        "resolved_ip": d.resolved_ip,
        "verified_at": d.verified_at.isoformat() if d.verified_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def popunder_campaign_to_dict(p: PopunderCampaign) -> dict:
    return {
        "id": p.id, "user_id": p.user_id, "name": p.name,
        "slug": p.slug, "status": p.status, "settings": p.settings or {},
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# System menu definitions - when new menus are added here, they auto-appear in role management
SYSTEM_MENUS = [
    {"key": "dashboard", "label": "Dashboard", "description": "View dashboard and stats"},
    {"key": "projects", "label": "Projects", "description": "Manage JS hosting projects"},
    {"key": "popunders", "label": "Popunder Campaigns", "description": "Manage popunder ad campaigns"},
    {"key": "settings", "label": "Settings", "description": "Manage categories"},
    {"key": "user_management", "label": "User Management", "description": "Manage users and roles"},
    {"key": "custom_domains", "label": "Custom Domains", "description": "Manage custom domains for JS delivery"},
]


async def is_user_admin(db: AsyncSession, user_id: int) -> bool:
    """Check if the user has admin role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    return user.role == 'admin'


async def generate_unique_slug(db: AsyncSession, name: str) -> str:
    """Generate a unique numeric slug for projects."""
    import random
    while True:
        # Generate a random 8-digit number
        slug = str(random.randint(10000000, 99999999))
        result = await db.execute(select(Project).where(Project.slug == slug))
        if not result.scalar_one_or_none():
            return slug


async def generate_script_slug(db: AsyncSession, project_id: int, name: str) -> str:
    """Generate a unique alphanumeric slug for scripts within a project."""
    import random
    import string
    while True:
        # Generate a random alphanumeric string (5 letters + 5 digits)
        letters = ''.join(random.choices(string.ascii_lowercase, k=5))
        digits = ''.join(random.choices(string.digits, k=5))
        slug = letters + digits
        result = await db.execute(select(Script).where(and_(Script.project_id == project_id, Script.slug == slug)))
        if not result.scalar_one_or_none():
            return slug


async def get_user_project(db: AsyncSession, project_id: int, user_id: int, is_admin: bool = False) -> Project:
    """Get a project by ID. If is_admin is True, bypasses user ownership check."""
    if is_admin:
        # Admin can access any project
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
            .where(Project.id == project_id)
        )
    else:
        # Regular users can only access their own projects
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
            .where(and_(Project.id == project_id, Project.user_id == user_id))
        )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def generate_popunder_slug(db: AsyncSession, name: str) -> str:
    """Generate unique slug for popunder campaign (globally unique now)."""
    base = slugify(name, max_length=200)
    slug = base
    counter = 1
    while True:
        result = await db.execute(select(PopunderCampaign).where(PopunderCampaign.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


async def get_user_campaign(db: AsyncSession, campaign_id: int, user_id: int, is_admin: bool = False) -> PopunderCampaign:
    """Get a popunder campaign by ID. If is_admin is True, bypasses user ownership check."""
    if is_admin:
        # Admin can access any campaign
        result = await db.execute(
            select(PopunderCampaign)
            .where(PopunderCampaign.id == campaign_id)
        )
    else:
        # Regular users can only access their own campaigns
        result = await db.execute(
            select(PopunderCampaign)
            .where(and_(PopunderCampaign.id == campaign_id, PopunderCampaign.user_id == user_id))
        )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Popunder campaign not found")
    return campaign


# ─── Auth Routes ───
@api_router.post("/auth/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Get role permissions
    role_result = await db.execute(select(Role).where(Role.name == user.role))
    role = role_result.scalar_one_or_none()
    user_dict = user_to_dict(user)
    user_dict["permissions"] = role.permissions if role else []

    token = create_token(user.id, user.email)
    return {"token": token, "user": user_dict}


@api_router.get("/auth/me")
async def get_me(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == current_user['user_id']))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Get role permissions
    role_result = await db.execute(select(Role).where(Role.name == user.role))
    role = role_result.scalar_one_or_none()
    permissions = role.permissions if role else []
    user_dict = user_to_dict(user)
    user_dict["permissions"] = permissions
    return {"user": user_dict}


# ─── Category Routes ───
@api_router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.is_active == True).order_by(Category.name))
    categories = result.scalars().all()
    return {"categories": [category_to_dict(c) for c in categories]}


@api_router.get("/categories/all")
async def list_all_categories(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all categories with project counts (for settings/admin)."""
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    cat_list = []
    for c in categories:
        # Count projects using this category
        count_result = await db.execute(select(func.count(Project.id)).where(Project.category_id == c.id))
        project_count = count_result.scalar() or 0
        d = category_to_dict(c)
        d["project_count"] = project_count
        cat_list.append(d)

    return {"categories": cat_list}


@api_router.post("/categories")
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Category name is required")

    # Check duplicate
    result = await db.execute(select(Category).where(Category.name == data.name.strip()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category name already exists")

    cat = Category(name=data.name.strip(), description=data.description)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"category": category_to_dict(cat)}


@api_router.patch("/categories/{category_id}")
async def update_category(category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Category name cannot be empty")
        # Check duplicate (exclude current)
        dup = await db.execute(select(Category).where(and_(Category.name == name, Category.id != category_id)))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category name already exists")
        cat.name = name

    if data.description is not None:
        cat.description = data.description

    if data.is_active is not None:
        cat.is_active = data.is_active

    await db.commit()
    await db.refresh(cat)
    return {"category": category_to_dict(cat)}


@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category is used by any project
    count_result = await db.execute(select(func.count(Project.id)).where(Project.category_id == category_id))
    project_count = count_result.scalar() or 0
    if project_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: category is used by {project_count} project(s)")

    await db.delete(cat)
    await db.commit()
    return {"message": "Category deleted"}


# ─── Project Routes ───
@api_router.post("/projects")
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Verify category exists
    cat = await db.execute(select(Category).where(Category.id == data.category_id))
    if not cat.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid category")

    if data.status and data.status not in ('active', 'paused'):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")

    slug = await generate_unique_slug(db, data.name)
    project = Project(
        user_id=current_user['user_id'],
        category_id=data.category_id,
        name=data.name,
        slug=slug,
        status=data.status or 'active'
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    result = await db.execute(
        select(Project).options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
        .where(Project.id == project.id)
    )
    project = result.scalar_one()
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    
    if is_admin:
        # Admin can see all projects
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
            .order_by(desc(Project.created_at))
        )
    else:
        # Regular users only see their own projects
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
            .where(Project.user_id == user_id)
            .order_by(desc(Project.created_at))
        )
    projects = result.scalars().all()
    return {"projects": [project_to_dict(p, include_relations=True) for p in projects]}


@api_router.get("/projects/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.patch("/projects/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)

    if data.name is not None:
        project.name = data.name
        # Note: slug is NOT changed on update to preserve embed URLs
    if data.category_id is not None:
        cat = await db.execute(select(Category).where(Category.id == data.category_id))
        if not cat.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid category")
        project.category_id = data.category_id
    if data.status is not None:
        if data.status not in ('active', 'paused'):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")
        project.status = data.status

    await db.commit()
    await db.refresh(project)

    result = await db.execute(
        select(Project).options(selectinload(Project.category), selectinload(Project.scripts).selectinload(Script.whitelists))
        .where(Project.id == project.id)
    )
    project = result.scalar_one()
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}


# ─── Whitelist Routes (per Script) ───
@api_router.get("/projects/{project_id}/scripts/{script_id}/whitelist")
async def list_whitelist(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    # Verify script belongs to project
    result = await db.execute(select(Script).where(and_(Script.id == script_id, Script.project_id == project_id)))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Script not found")
    
    result = await db.execute(
        select(ScriptWhitelist).where(ScriptWhitelist.script_id == script_id).order_by(desc(ScriptWhitelist.created_at))
    )
    entries = result.scalars().all()
    return {"whitelists": [whitelist_to_dict(w) for w in entries]}


@api_router.post("/projects/{project_id}/scripts/{script_id}/whitelist")
async def add_whitelist(project_id: int, script_id: int, data: WhitelistCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    # Verify script belongs to project
    result = await db.execute(select(Script).where(and_(Script.id == script_id, Script.project_id == project_id)))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Script not found")

    pattern = data.domain_pattern.lower().strip()
    is_valid, msg = validate_domain_pattern(pattern)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # Check duplicate
    result = await db.execute(
        select(ScriptWhitelist).where(and_(ScriptWhitelist.script_id == script_id, ScriptWhitelist.domain_pattern == pattern))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain pattern already exists for this script")

    entry = ScriptWhitelist(script_id=script_id, domain_pattern=pattern)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"whitelist": whitelist_to_dict(entry)}


@api_router.patch("/projects/{project_id}/scripts/{script_id}/whitelist/{whitelist_id}")
async def update_whitelist(project_id: int, script_id: int, whitelist_id: int, data: WhitelistUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)

    result = await db.execute(select(ScriptWhitelist).where(and_(ScriptWhitelist.id == whitelist_id, ScriptWhitelist.script_id == script_id)))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")

    if data.domain_pattern is not None:
        pattern = data.domain_pattern.lower().strip()
        is_valid, msg = validate_domain_pattern(pattern)
        if not is_valid:
            raise HTTPException(status_code=400, detail=msg)
        entry.domain_pattern = pattern

    if data.is_active is not None:
        entry.is_active = data.is_active

    await db.commit()
    await db.refresh(entry)
    return {"whitelist": whitelist_to_dict(entry)}


@api_router.delete("/projects/{project_id}/scripts/{script_id}/whitelist/{whitelist_id}")
async def delete_whitelist(project_id: int, script_id: int, whitelist_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)

    result = await db.execute(select(ScriptWhitelist).where(and_(ScriptWhitelist.id == whitelist_id, ScriptWhitelist.script_id == script_id)))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")

    await db.delete(entry)
    await db.commit()
    return {"message": "Whitelist entry deleted"}


# ─── Script Routes ───
@api_router.get("/projects/{project_id}/scripts")
async def list_scripts(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(Script.project_id == project_id).order_by(desc(Script.created_at))
    )
    scripts = result.scalars().all()
    return {"scripts": [script_to_dict(s, include_whitelists=True) for s in scripts]}


@api_router.post("/projects/{project_id}/scripts")
async def create_script(project_id: int, data: ScriptCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)

    if data.status and data.status not in ('active', 'disabled'):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'disabled'")

    slug = await generate_script_slug(db, project_id, data.name)
    script = Script(
        project_id=project_id, 
        name=data.name, 
        slug=slug, 
        js_code=data.js_code, 
        status=data.status or 'active',
        secondary_script=data.secondary_script if data.secondary_script else None,
        secondary_script_mode=data.secondary_script_mode or 'js',
        secondary_script_links=[link.model_dump() for link in data.secondary_script_links] if data.secondary_script_links else None
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    
    # Reload with whitelists relationship
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(Script.id == script.id)
    )
    script = result.scalar_one()
    return {"script": script_to_dict(script, include_whitelists=True)}


@api_router.get("/projects/{project_id}/scripts/{script_id}")
async def get_script(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"script": script_to_dict(script, include_whitelists=True)}


@api_router.patch("/projects/{project_id}/scripts/{script_id}")
async def update_script(project_id: int, script_id: int, data: ScriptUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if data.name is not None:
        script.name = data.name
    if data.js_code is not None:
        script.js_code = data.js_code
    if data.status is not None:
        if data.status not in ('active', 'disabled'):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'disabled'")
        script.status = data.status
    if data.secondary_script is not None:
        script.secondary_script = data.secondary_script if data.secondary_script.strip() else None
    if data.secondary_script_mode is not None:
        if data.secondary_script_mode not in ('js', 'links'):
            raise HTTPException(status_code=400, detail="Secondary script mode must be 'js' or 'links'")
        script.secondary_script_mode = data.secondary_script_mode
    if data.secondary_script_links is not None:
        script.secondary_script_links = [link.model_dump() for link in data.secondary_script_links]

    await db.commit()
    
    # Reload with whitelists relationship after commit
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(Script.id == script.id)
    )
    script = result.scalar_one()
    return {"script": script_to_dict(script, include_whitelists=True)}


@api_router.delete("/projects/{project_id}/scripts/{script_id}")
async def delete_script(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    result = await db.execute(select(Script).where(and_(Script.id == script_id, Script.project_id == project_id)))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    await db.delete(script)
    await db.commit()
    return {"message": "Script deleted"}


# ─── Dashboard Stats ───
@api_router.get("/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user['user_id']

    project_count = await db.execute(select(func.count(Project.id)).where(Project.user_id == uid))
    total_projects = project_count.scalar() or 0

    script_count = await db.execute(
        select(func.count(Script.id)).join(Project).where(Project.user_id == uid)
    )
    total_scripts = script_count.scalar() or 0

    whitelist_count = await db.execute(
        select(func.count(ScriptWhitelist.id)).join(Script).join(Project).where(Project.user_id == uid)
    )
    total_whitelists = whitelist_count.scalar() or 0

    log_count = await db.execute(
        select(func.count(AccessLog.id)).join(Project).where(Project.user_id == uid)
    )
    total_requests = log_count.scalar() or 0

    allowed_count = await db.execute(
        select(func.count(AccessLog.id)).join(Project).where(and_(Project.user_id == uid, AccessLog.allowed == True))
    )
    total_allowed = allowed_count.scalar() or 0

    # Recent projects
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.category), selectinload(Project.scripts))
        .where(Project.user_id == uid)
        .order_by(desc(Project.created_at))
        .limit(5)
    )
    recent_projects = result.scalars().all()

    return {
        "stats": {
            "total_projects": total_projects,
            "total_scripts": total_scripts,
            "total_whitelists": total_whitelists,
            "total_requests": total_requests,
            "total_allowed": total_allowed,
            "total_denied": total_requests - total_allowed,
        },
        "recent_projects": [project_to_dict(p, include_relations=True) for p in recent_projects]
    }


# ─── Access Logs ───
@api_router.get("/projects/{project_id}/logs")
async def get_access_logs(project_id: int, limit: int = 50, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)

    result = await db.execute(
        select(AccessLog).where(AccessLog.project_id == project_id).order_by(desc(AccessLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()

    # Stats
    total = await db.execute(select(func.count(AccessLog.id)).where(AccessLog.project_id == project_id))
    allowed = await db.execute(select(func.count(AccessLog.id)).where(and_(AccessLog.project_id == project_id, AccessLog.allowed == True)))

    total_val = total.scalar() or 0
    allowed_val = allowed.scalar() or 0

    return {
        "logs": [log_to_dict(l) for l in logs],
        "stats": {
            "total": total_val,
            "allowed": allowed_val,
            "denied": total_val - allowed_val,
        }
    }


@api_router.delete("/projects/{project_id}/logs")
async def clear_access_logs(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Clear all access logs for a project."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    
    await db.execute(
        AccessLog.__table__.delete().where(AccessLog.project_id == project_id)
    )
    await db.commit()
    
    return {"message": "Access logs cleared"}


# ─── Analytics ───
@api_router.get("/projects/{project_id}/analytics")
async def get_analytics(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)

    # Get scripts for URL mapping
    scripts_result = await db.execute(select(Script).where(Script.project_id == project_id))
    scripts = {s.id: s for s in scripts_result.scalars().all()}

    # Overall stats
    total = await db.execute(select(func.count(AccessLog.id)).where(AccessLog.project_id == project_id))
    allowed = await db.execute(select(func.count(AccessLog.id)).where(and_(AccessLog.project_id == project_id, AccessLog.allowed == True)))
    total_val = total.scalar() or 0
    allowed_val = allowed.scalar() or 0

    # Requests by day
    daily_result = await db.execute(
        select(
            func.date(AccessLog.created_at).label('date'),
            func.count(AccessLog.id).label('total'),
            func.sum(case((AccessLog.allowed == True, 1), else_=0)).label('allowed'),
            func.sum(case((AccessLog.allowed == False, 1), else_=0)).label('denied'),
        )
        .where(AccessLog.project_id == project_id)
        .group_by(func.date(AccessLog.created_at))
        .order_by(func.date(AccessLog.created_at))
        .limit(30)
    )
    daily_data = [{"date": str(row.date), "total": row.total, "allowed": int(row.allowed or 0), "denied": int(row.denied or 0)} for row in daily_result]

    # Top domains
    domain_result = await db.execute(
        select(
            AccessLog.ref_domain,
            func.count(AccessLog.id).label('count'),
            func.sum(case((AccessLog.allowed == True, 1), else_=0)).label('allowed'),
            func.sum(case((AccessLog.allowed == False, 1), else_=0)).label('denied'),
        )
        .where(and_(AccessLog.project_id == project_id, AccessLog.ref_domain != None, AccessLog.ref_domain != ''))
        .group_by(AccessLog.ref_domain)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(10)
    )
    domain_data = [{"domain": row.ref_domain, "count": row.count, "allowed": int(row.allowed or 0), "denied": int(row.denied or 0)} for row in domain_result]

    # Analytics by script (which script URL was used)
    script_result = await db.execute(
        select(
            AccessLog.script_id,
            func.count(AccessLog.id).label('count'),
            func.sum(case((AccessLog.allowed == True, 1), else_=0)).label('allowed'),
            func.sum(case((AccessLog.allowed == False, 1), else_=0)).label('denied'),
        )
        .where(and_(AccessLog.project_id == project_id, AccessLog.script_id != None))
        .group_by(AccessLog.script_id)
        .order_by(desc(func.count(AccessLog.id)))
    )
    script_data = []
    for row in script_result:
        script = scripts.get(row.script_id)
        if script:
            script_url = f"/api/js/{project.slug}/{script.slug}.js"
            script_data.append({
                "script_id": row.script_id,
                "script_name": script.name,
                "script_url": script_url,
                "count": row.count,
                "allowed": int(row.allowed or 0),
                "denied": int(row.denied or 0)
            })

    # Detailed breakdown: Full Referrer URL + Script URL combinations
    # Shows which specific pages (full URL) accessed which specific script URLs
    referer_url_result = await db.execute(
        select(
            AccessLog.script_id,
            AccessLog.referer_url,
            AccessLog.ref_domain,
            AccessLog.allowed,
            func.count(AccessLog.id).label('request_count'),
            func.max(AccessLog.created_at).label('last_access'),
        )
        .where(and_(
            AccessLog.project_id == project_id,
            AccessLog.script_id != None,
            AccessLog.referer_url != None,
            AccessLog.referer_url != ''
        ))
        .group_by(AccessLog.script_id, AccessLog.referer_url, AccessLog.ref_domain, AccessLog.allowed)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(50)
    )
    referer_url_data = []
    for row in referer_url_result:
        script = scripts.get(row.script_id)
        if script:
            script_url = f"/api/js/{project.slug}/{script.slug}.js"
            referer_url_data.append({
                "script_id": row.script_id,
                "script_name": script.name,
                "script_url": script_url,
                "referer_url": row.referer_url,
                "domain": row.ref_domain,
                "status": "allowed" if row.allowed else "denied",
                "request_count": row.request_count,
                "last_access": row.last_access.isoformat() if row.last_access else None
            })

    # Legacy: Domain + Script URL combinations (kept for backward compatibility)
    script_domain_result = await db.execute(
        select(
            AccessLog.script_id,
            AccessLog.ref_domain,
            AccessLog.allowed,
            func.count(AccessLog.id).label('request_count'),
            func.max(AccessLog.created_at).label('last_access'),
        )
        .where(and_(
            AccessLog.project_id == project_id,
            AccessLog.script_id != None,
            AccessLog.ref_domain != None,
            AccessLog.ref_domain != ''
        ))
        .group_by(AccessLog.script_id, AccessLog.ref_domain, AccessLog.allowed)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(50)
    )
    script_domain_data = []
    for row in script_domain_result:
        script = scripts.get(row.script_id)
        if script:
            script_url = f"/api/js/{project.slug}/{script.slug}.js"
            script_domain_data.append({
                "script_id": row.script_id,
                "script_name": script.name,
                "script_url": script_url,
                "domain": row.ref_domain,
                "status": "allowed" if row.allowed else "denied",
                "request_count": row.request_count,
                "last_access": row.last_access.isoformat() if row.last_access else None
            })

    return {
        "summary": {"total": total_val, "allowed": allowed_val, "denied": total_val - allowed_val},
        "daily": daily_data,
        "top_domains": domain_data,
        "by_script": script_data,
        "referer_url_details": referer_url_data,  # New: Full referrer URL breakdown
        "script_domain_details": script_domain_data,  # Legacy: Domain-only breakdown
    }


# ─── Individual Access Logs for Analytics Tab ───
@api_router.get("/projects/{project_id}/analytics/logs")
async def get_analytics_logs(project_id: int, page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get individual access log entries for the Analytics tab with pagination and per-row delete capability."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)

    # Ensure valid pagination params
    page = max(1, page)
    per_page = min(max(1, per_page), 100)  # Max 100 per page
    offset = (page - 1) * per_page

    # Get scripts for URL mapping
    scripts_result = await db.execute(select(Script).where(Script.project_id == project_id))
    scripts = {s.id: s for s in scripts_result.scalars().all()}

    # Get individual log entries (most recent first) with pagination
    result = await db.execute(
        select(AccessLog)
        .where(AccessLog.project_id == project_id)
        .order_by(desc(AccessLog.created_at))
        .offset(offset)
        .limit(per_page)
    )
    logs = result.scalars().all()

    # Build flat list of individual log entries
    log_entries = []
    for log in logs:
        script = scripts.get(log.script_id) if log.script_id else None
        script_url = f"/api/js/{project.slug}/{script.slug}.js" if script else None
        
        log_entries.append({
            "id": log.id,
            "referer_url": log.referer_url or log.ref_domain or "Direct/Unknown",
            "script_url": script_url,
            "script_name": script.name if script else "Unknown",
            "status": "allowed" if log.allowed else "denied",
            "requests": 1,  # Individual log entry = 1 request
            "last_access": log.created_at.isoformat() if log.created_at else None,
        })

    # Summary stats (total counts for entire project)
    total = await db.execute(select(func.count(AccessLog.id)).where(AccessLog.project_id == project_id))
    allowed = await db.execute(select(func.count(AccessLog.id)).where(and_(AccessLog.project_id == project_id, AccessLog.allowed == True)))
    total_val = total.scalar() or 0
    allowed_val = allowed.scalar() or 0
    
    # Calculate total pages
    total_pages = (total_val + per_page - 1) // per_page if total_val > 0 else 1

    return {
        "logs": log_entries,
        "summary": {
            "total": total_val,
            "allowed": allowed_val,
            "denied": total_val - allowed_val
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_val,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ─── Blacklisted Domains (non-whitelisted) ───
@api_router.get("/projects/{project_id}/blacklisted-domains")
async def get_blacklisted_domains(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get list of domains that were denied access (not whitelisted)."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)

    # Get denied domains with count, most recent first
    result = await db.execute(
        select(
            AccessLog.ref_domain,
            func.count(AccessLog.id).label('request_count'),
            func.max(AccessLog.created_at).label('last_seen'),
        )
        .where(and_(
            AccessLog.project_id == project_id,
            AccessLog.allowed == False,
            AccessLog.ref_domain != None,
            AccessLog.ref_domain != ''
        ))
        .group_by(AccessLog.ref_domain)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(100)
    )
    
    blacklisted = [
        {
            "domain": row.ref_domain,
            "request_count": row.request_count,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None
        }
        for row in result
    ]

    # Total denied count
    total_denied = await db.execute(
        select(func.count(AccessLog.id)).where(and_(
            AccessLog.project_id == project_id,
            AccessLog.allowed == False
        ))
    )
    
    return {
        "blacklisted_domains": blacklisted,
        "total_denied_requests": total_denied.scalar() or 0,
    }


# ─── Script-Specific Analytics ───
@api_router.get("/projects/{project_id}/scripts/{script_id}/analytics")
async def get_script_analytics(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get analytics for a specific script - which domains and pages accessed it."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)
    
    # Get the script
    result = await db.execute(
        select(Script).where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_url = f"/api/js/{project.slug}/{script.slug}.js"
    
    # Total stats for this script
    total_result = await db.execute(
        select(func.count(AccessLog.id)).where(AccessLog.script_id == script_id)
    )
    total_val = total_result.scalar() or 0
    
    allowed_result = await db.execute(
        select(func.count(AccessLog.id)).where(and_(AccessLog.script_id == script_id, AccessLog.allowed == True))
    )
    allowed_val = allowed_result.scalar() or 0
    
    # Domains that accessed this script (include direct/unknown access)
    domain_result = await db.execute(
        select(
            AccessLog.ref_domain,
            AccessLog.allowed,
            func.count(AccessLog.id).label('request_count'),
            func.max(AccessLog.created_at).label('last_access'),
        )
        .where(AccessLog.script_id == script_id)
        .group_by(AccessLog.ref_domain, AccessLog.allowed)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(50)
    )
    
    domains = []
    for row in domain_result:
        domains.append({
            "domain": row.ref_domain if row.ref_domain else "Direct/Unknown",
            "status": "allowed" if row.allowed else "denied",
            "request_count": row.request_count,
            "last_access": row.last_access.isoformat() if row.last_access else None
        })
    
    # Full referrer URLs that accessed this script (include direct/unknown access)
    referer_url_result = await db.execute(
        select(
            AccessLog.referer_url,
            AccessLog.ref_domain,
            AccessLog.allowed,
            func.count(AccessLog.id).label('request_count'),
            func.max(AccessLog.created_at).label('last_access'),
        )
        .where(AccessLog.script_id == script_id)
        .group_by(AccessLog.referer_url, AccessLog.ref_domain, AccessLog.allowed)
        .order_by(desc(func.count(AccessLog.id)))
        .limit(50)
    )
    
    referer_urls = []
    for row in referer_url_result:
        referer_urls.append({
            "referer_url": row.referer_url if row.referer_url else "Direct/Unknown",
            "domain": row.ref_domain if row.ref_domain else "Direct/Unknown",
            "status": "allowed" if row.allowed else "denied",
            "request_count": row.request_count,
            "last_access": row.last_access.isoformat() if row.last_access else None
        })
    
    return {
        "script": {
            "id": script.id,
            "name": script.name,
            "slug": script.slug,
            "url": script_url,
        },
        "summary": {
            "total": total_val,
            "allowed": allowed_val,
            "denied": total_val - allowed_val
        },
        "domains": domains,
        "referer_urls": referer_urls  # New: Full referrer URL breakdown
    }


# ─── Domain Tester (for scripts) ───
@api_router.post("/projects/{project_id}/scripts/{script_id}/test-domain")
async def test_domain(project_id: int, script_id: int, data: DomainTestRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    normalized = normalize_domain(data.domain)
    active_patterns = [w.domain_pattern for w in script.whitelists if w.is_active]

    allowed = is_domain_allowed(normalized, active_patterns)

    # Find which pattern matched
    matched_pattern = None
    if allowed:
        exact = {p for p in active_patterns if not p.startswith('*.')}
        wildcards = [p for p in active_patterns if p.startswith('*.')]
        if normalized in exact:
            matched_pattern = normalized
        else:
            for p in wildcards:
                suffix = p[2:]
                if normalized.endswith('.' + suffix) and normalized != suffix:
                    matched_pattern = p
                    break

    return {
        "domain": data.domain,
        "normalized_domain": normalized,
        "allowed": allowed,
        "matched_pattern": matched_pattern,
        "active_patterns_count": len(active_patterns),
    }


# ─── Clear Script Logs ───
@api_router.delete("/projects/{project_id}/scripts/{script_id}/logs")
async def clear_script_logs(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Clear all access logs for a specific script."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    
    # Verify script belongs to project
    result = await db.execute(
        select(Script).where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    await db.execute(
        AccessLog.__table__.delete().where(AccessLog.script_id == script_id)
    )
    await db.commit()
    
    return {"message": f"Access logs cleared for script '{script.name}'"}


# ─── Get Individual Script Logs (with IDs for deletion) ───
@api_router.get("/projects/{project_id}/scripts/{script_id}/logs")
async def get_script_logs(project_id: int, script_id: int, page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get individual access log entries for a specific script with pagination and per-row deletion."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    project = await get_user_project(db, project_id, user_id, is_admin)
    
    # Verify script belongs to project
    result = await db.execute(
        select(Script).where(and_(Script.id == script_id, Script.project_id == project_id))
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Ensure valid pagination params
    page = max(1, page)
    per_page = min(max(1, per_page), 100)  # Max 100 per page
    offset = (page - 1) * per_page
    
    script_url = f"/api/js/{project.slug}/{script.slug}.js"
    
    # Get individual log entries with pagination
    result = await db.execute(
        select(AccessLog)
        .where(AccessLog.script_id == script_id)
        .order_by(desc(AccessLog.created_at))
        .offset(offset)
        .limit(per_page)
    )
    logs = result.scalars().all()
    
    log_entries = []
    for log in logs:
        log_entries.append({
            "id": log.id,
            "referer_url": log.referer_url if log.referer_url else (log.ref_domain if log.ref_domain else "Direct/Unknown"),
            "script_url": script_url,
            "status": "allowed" if log.allowed else "denied",
            "requests": 1,
            "last_access": log.created_at.isoformat() if log.created_at else None,
        })
    
    # Summary stats (total counts for script)
    total_result = await db.execute(
        select(func.count(AccessLog.id)).where(AccessLog.script_id == script_id)
    )
    total_val = total_result.scalar() or 0
    
    allowed_result = await db.execute(
        select(func.count(AccessLog.id)).where(and_(AccessLog.script_id == script_id, AccessLog.allowed == True))
    )
    allowed_val = allowed_result.scalar() or 0
    
    # Calculate total pages
    total_pages = (total_val + per_page - 1) // per_page if total_val > 0 else 1
    
    return {
        "script": {
            "id": script.id,
            "name": script.name,
            "slug": script.slug,
            "url": script_url,
        },
        "logs": log_entries,
        "summary": {
            "total": total_val,
            "allowed": allowed_val,
            "denied": total_val - allowed_val
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_val,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ─── Delete Individual Log Entry ───
@api_router.delete("/projects/{project_id}/logs/{log_id}")
async def delete_single_log(project_id: int, log_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete a single access log entry by ID."""
    # Verify project belongs to user (or admin)
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_project(db, project_id, user_id, is_admin)
    
    # Find the log entry
    result = await db.execute(
        select(AccessLog).where(and_(AccessLog.id == log_id, AccessLog.project_id == project_id))
    )
    log_entry = result.scalar_one_or_none()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    await db.delete(log_entry)
    await db.commit()
    
    return {"message": "Log entry deleted"}


# ─── Public Popunder JS Delivery (must come before general JS delivery) ───

# Self-contained popunder engine JavaScript template
POPUNDER_ENGINE_TEMPLATE = '''(function(){
var c = __CONFIG__;
var apiBase = __API_BASE__;

// Storage key for frequency tracking
var sk = 'popunder_' + c.id;

// Get today's date as string for daily cap
function getToday() {
    var d = new Date();
    return d.getFullYear() + '-' + (d.getMonth()+1) + '-' + d.getDate();
}

// Check frequency cap (per user per day)
function checkFrequency() {
    try {
        var data = JSON.parse(localStorage.getItem(sk) || '{}');
        var today = getToday();
        if (data.date !== today) {
            data = { date: today, count: 0 };
        }
        if (data.count >= c.freq) return false;
        return true;
    } catch(e) { return true; }
}

// Mark show count
function markShown() {
    try {
        var data = JSON.parse(localStorage.getItem(sk) || '{}');
        var today = getToday();
        if (data.date !== today) {
            data = { date: today, count: 0 };
        }
        data.count++;
        localStorage.setItem(sk, JSON.stringify(data));
    } catch(e) {}
}

// Detect device type
function getDeviceType() {
    var ua = navigator.userAgent.toLowerCase();
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) return 'tablet';
    if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua)) return 'mobile';
    return 'desktop';
}

// Check device targeting
function checkDevice() {
    if (!c.devices || c.devices.length === 0) return true;
    return c.devices.indexOf(getDeviceType()) !== -1;
}

// Get random URL from list
function getUrl() {
    if (!c.urls || c.urls.length === 0) return null;
    return c.urls[Math.floor(Math.random() * c.urls.length)];
}

// Track analytics event
function trackEvent(eventType, targetUrl) {
    try {
        var data = {
            campaign_id: c.id,
            event_type: eventType,
            referer_url: window.location.href,
            target_url: targetUrl || '',
            device_type: getDeviceType()
        };
        var xhr = new XMLHttpRequest();
        xhr.open('POST', apiBase + '/api/popunder-analytics', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify(data));
    } catch(e) {}
}

// Check country targeting via IP API (client-side)
function checkCountry(callback) {
    if (!c.countries || c.countries.length === 0) {
        callback(true);
        return;
    }
    try {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'https://ip-api.com/json/?fields=countryCode', true);
        xhr.timeout = 3000;
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        var userCountry = data.countryCode || '';
                        callback(c.countries.indexOf(userCountry) !== -1);
                    } catch(e) { callback(true); }
                } else {
                    callback(true); // Allow on error
                }
            }
        };
        xhr.ontimeout = function() { callback(true); };
        xhr.onerror = function() { callback(true); };
        xhr.send();
    } catch(e) { callback(true); }
}

// True popunder - opens behind the current window
// The popup opens first, but the main tab stays on screen (popup goes behind)
function openPopunder() {
    var url = getUrl();
    if (!url) return;
    if (!checkFrequency()) return;
    if (!checkDevice()) return;
    
    try {
        // Enhanced popunder technique
        // Step 1: Calculate window position (same as current window)
        var w = window.innerWidth || document.documentElement.clientWidth || screen.width;
        var h = window.innerHeight || document.documentElement.clientHeight || screen.height;
        var left = (screen.width - w) / 2;
        var top = (screen.height - h) / 2;
        
        // Step 2: Window features - open as a normal window, not a tab
        var features = 'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top;
        features += ',toolbar=yes,location=yes,directories=yes,status=yes,menubar=yes,scrollbars=yes,resizable=yes';
        
        // Step 3: Open the popunder window
        var popunder = window.open(url, '_blank', features);
        
        if (popunder) {
            // Step 4: Immediately blur the popup
            popunder.blur();
            
            // Step 5: Focus back to main window using multiple techniques
            window.focus();
            
            // Technique 1: Click simulation to regain focus
            if (document.body) {
                var clickEvent = document.createEvent('MouseEvents');
                clickEvent.initMouseEvent('click', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                document.body.dispatchEvent(clickEvent);
            }
            
            // Technique 2: Use self.focus() for some browsers
            self.focus();
            
            // Technique 3: Focus an input element temporarily
            var tempInput = document.createElement('input');
            tempInput.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;';
            document.body.appendChild(tempInput);
            tempInput.focus();
            setTimeout(function() {
                document.body.removeChild(tempInput);
            }, 10);
            
            // Technique 4: Use opener reference if in frame
            if (window.opener && window.opener !== window) {
                window.opener.focus();
            }
            
            // Technique 5: Async focus with multiple timeouts
            setTimeout(function() { window.focus(); }, 0);
            setTimeout(function() { window.focus(); }, 1);
            setTimeout(function() { 
                window.focus();
                // Re-blur the popunder in case it got focus back
                try { popunder.blur(); } catch(e) {}
            }, 10);
            setTimeout(function() { 
                window.focus();
                self.focus();
            }, 50);
            setTimeout(function() { 
                window.focus();
                // Final attempt to push popunder back
                try { popunder.blur(); } catch(e) {}
            }, 100);
            
            // Technique 6: Use window.top if in iframe
            if (window.self !== window.top) {
                try { window.top.focus(); } catch(e) {}
            }
            
            markShown();
            trackEvent('click', url);
        }
    } catch(e) {
        // Fallback method: open about:blank first then redirect
        try {
            var features2 = 'width=' + (screen.width/2) + ',height=' + (screen.height/2);
            var pop = window.open('about:blank', '_blank', features2);
            if (pop) {
                pop.blur();
                window.focus();
                self.focus();
                pop.location.href = url;
                setTimeout(function() { window.focus(); }, 0);
                setTimeout(function() { window.focus(); pop.blur(); }, 10);
                markShown();
                trackEvent('click', url);
            }
        } catch(e2) {}
    }
}

// Inject floating banner if present
function injectBanner() {
    if (!c.banner) return;
    try {
        var div = document.createElement('div');
        div.innerHTML = c.banner;
        document.body.appendChild(div);
    } catch(e) {}
}

// Inject custom HTML if present
function injectHtml() {
    if (!c.html) return;
    try {
        var div = document.createElement('div');
        div.innerHTML = c.html;
        document.body.appendChild(div);
    } catch(e) {}
}

// Trigger handler with country check
var triggered = false;
function onUserAction(e) {
    if (triggered) return;
    triggered = true;
    
    // Check country first (async)
    checkCountry(function(allowed) {
        if (!allowed) {
            triggered = false; // Reset for next attempt
            return;
        }
        
        // Apply timer delay if set
        if (c.timer > 0) {
            setTimeout(openPopunder, c.timer * 1000);
        } else {
            openPopunder();
        }
    });
    
    document.removeEventListener('click', onUserAction, true);
    document.removeEventListener('touchstart', onUserAction, true);
}

// Initialize - listen for user interaction
document.addEventListener('click', onUserAction, true);
document.addEventListener('touchstart', onUserAction, true);

// Track impression on load
trackEvent('impression', '');

// Inject extras on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        injectBanner();
        injectHtml();
    });
} else {
    injectBanner();
    injectHtml();
}
})();'''


@api_router.get("/test/popunder/{campaign_slug}", response_class=HTMLResponse)
async def get_popunder_test_page(campaign_slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Test page for pop-under campaigns.
    Allows testing the pop-under behavior without authentication.
    """
    # Verify campaign exists
    result = await db.execute(
        select(PopunderCampaign).where(PopunderCampaign.slug == campaign_slug)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get API base URL from request
    api_base = f"{request.base_url.scheme}://{request.headers.get('host', 'localhost')}"
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pop-under Test: {campaign.name}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e8e8e8;
        }}
        h1 {{ color: #00d9ff; font-size: 2rem; }}
        .test-card {{
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-top: 20px;
        }}
        .instructions {{
            background: rgba(0, 217, 255, 0.1);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            border-left: 4px solid #00d9ff;
        }}
        .instructions h3 {{ margin-top: 0; color: #00d9ff; }}
        .instructions ol {{ margin: 0; padding-left: 20px; }}
        .instructions li {{ margin: 8px 0; line-height: 1.6; }}
        button {{
            background: linear-gradient(135deg, #00d9ff 0%, #0099cc 100%);
            color: #1a1a2e;
            padding: 15px 40px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 217, 255, 0.3);
        }}
        .status {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }}
        .status.success {{ 
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
            display: block;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }}
        .campaign-info {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            font-size: 14px;
        }}
        .campaign-info code {{
            background: rgba(0,0,0,0.3);
            padding: 2px 6px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <h1>Pop-under Test Page</h1>
    <p style="opacity: 0.7;">Campaign: <strong>{campaign.name}</strong></p>
    
    <div class="test-card">
        <div class="instructions">
            <h3>Test Instructions:</h3>
            <ol>
                <li><strong>Click anywhere on this page</strong> to trigger the pop-under</li>
                <li>A new browser window should open with the target URL</li>
                <li><strong>Expected behavior:</strong> The new window opens, but <em>this page remains visible on your screen</em></li>
                <li>The pop-under window should appear "behind" this main window</li>
            </ol>
        </div>
        
        <p style="margin-bottom: 20px;">Click the button below or anywhere on the page to test:</p>
        <button id="testBtn">Click to Test Pop-under</button>
        
        <div id="status" class="status"></div>
        
        <div class="campaign-info">
            <p><strong>Campaign ID:</strong> <code>{campaign.id}</code></p>
            <p><strong>Script URL:</strong> <code>{api_base}/api/js/popunder/{campaign_slug}.js</code></p>
        </div>
    </div>
    
    <!-- Load the popunder script -->
    <script src="{api_base}/api/js/popunder/{campaign_slug}.js"></script>
    
    <script>
        document.getElementById('testBtn').addEventListener('click', function() {{
            var status = document.getElementById('status');
            status.innerHTML = '✓ Pop-under triggered! Check if a new window opened behind this one.';
            status.className = 'status success';
        }});
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html_content)


@api_router.get("/js/popunder/{campaign_file}")
async def deliver_popunder_js(campaign_file: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Public Popunder JS delivery endpoint.
    Delivers the full popunder engine with campaign configuration.
    No whitelist check - serves to any domain.
    """

    def noop_response():
        return Response(content=NOOP_JS, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)

    # Must end with .js
    if not campaign_file.endswith('.js'):
        return noop_response()

    campaign_slug = campaign_file[:-3]  # Remove .js extension

    # Resolve campaign by slug
    result = await db.execute(
        select(PopunderCampaign).where(PopunderCampaign.slug == campaign_slug)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        return noop_response()

    # Check campaign status
    if campaign.status == 'paused':
        return noop_response()

    # Build configuration from campaign settings
    settings = campaign.settings or {}
    
    # Parse URL list (newline separated)
    url_list_str = settings.get("url_list", "")
    urls = [u.strip() for u in url_list_str.split('\n') if u.strip()]
    
    config = {
        "id": campaign.id,
        "urls": urls,
        "timer": settings.get("timer", 0),
        "freq": settings.get("frequency", 1),
        "devices": settings.get("devices", ["desktop", "mobile", "tablet"]),
        "countries": settings.get("countries", []),
        "banner": settings.get("floating_banner", ""),
        "html": settings.get("html_body", ""),
    }

    # Get the API base URL from the request
    api_base = str(request.base_url).rstrip('/')
    
    js_code = POPUNDER_ENGINE_TEMPLATE.replace('__CONFIG__', json.dumps(config))
    js_code = js_code.replace('__API_BASE__', json.dumps(api_base))
    return Response(content=js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)


# ─── Public JS Delivery ───
def generate_link_injection_js(links: list) -> str:
    """Generate JavaScript that injects hidden HTML links into the page."""
    if not links:
        return NOOP_JS
    
    # Build the HTML content with <p> tags as row separators inside a single hidden div
    link_parts = []
    for link in links:
        url = link.get('url', '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', '').replace('\r', '')
        keyword = link.get('keyword', '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', '').replace('\r', '')
        if url and keyword:
            link_parts.append(f'<p><a href=\\"{url}\\">{keyword}</a></p>')
    
    if not link_parts:
        return NOOP_JS
    
    # Wrap all links in a single hidden div (escape quotes for JS string)
    html_content = '<div style=\\"display:none;\\">' + ''.join(link_parts) + '</div>'
    
    # Generate JS that injects this HTML
    js_code = f'''(function(){{
var h="{html_content}";
if(document.readyState==="loading"){{
document.addEventListener("DOMContentLoaded",function(){{
var d=document.createElement("div");d.innerHTML=h;document.body.appendChild(d);
}});
}}else{{
var d=document.createElement("div");d.innerHTML=h;document.body.appendChild(d);
}}
}})();'''
    return js_code


@api_router.get("/js/{project_slug}/{script_file}")
async def deliver_js(project_slug: str, script_file: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Public JS delivery endpoint.
    - Direct browser access: Returns HTML error page (not allowed)
    - Script tag loading from non-whitelisted domain: Returns secondary script
    - Script tag loading from whitelisted domain: Returns main script
    """

    def noop_response():
        return Response(content=NOOP_JS, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)

    def direct_access_response():
        """Response for direct browser access - show error page."""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e8e8e8;
        }
        .container { text-align: center; padding: 40px; max-width: 500px; }
        .icon {
            width: 80px; height: 80px;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 24px; font-size: 36px;
        }
        h1 { font-size: 28px; margin-bottom: 12px; color: #f8fafc; }
        p { color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 16px; }
        code {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 12px 20px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #fca5a5;
            display: block;
            margin-top: 20px;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⛔</div>
        <h1>Direct Access Not Allowed</h1>
        <p>This script cannot be accessed directly via browser.</p>
        <p>Scripts must be loaded via <strong>&lt;script&gt;</strong> tag from an authorized domain.</p>
        <code>&lt;script src="...this-url..."&gt;&lt;/script&gt;</code>
    </div>
</body>
</html>'''
        return HTMLResponse(content=html, status_code=403)

    def is_script_request() -> bool:
        """Check if request is from a <script> tag, not direct browser access."""
        # Sec-Fetch-Dest header indicates how the resource will be used
        # 'script' = loaded via <script> tag
        # 'document' = direct browser navigation
        sec_fetch_dest = request.headers.get('sec-fetch-dest', '').lower()
        if sec_fetch_dest == 'script':
            return True
        if sec_fetch_dest == 'document':
            return False
        
        # Sec-Fetch-Mode can also help
        sec_fetch_mode = request.headers.get('sec-fetch-mode', '').lower()
        if sec_fetch_mode == 'navigate':
            return False
        if sec_fetch_mode in ['cors', 'no-cors']:
            return True
        
        # Fallback: check Accept header
        # Direct browser access typically accepts text/html
        accept = request.headers.get('accept', '')
        if 'text/html' in accept and '*/*' not in accept:
            return False
        
        # If Origin or Referer is present, it's likely from a page
        if request.headers.get('origin') or request.headers.get('referer'):
            return True
        
        # No referer and accepts html = likely direct access
        if 'text/html' in accept:
            return False
        
        return True  # Default to allowing if we can't determine

    def secondary_response(script: Script):
        """Generate secondary response based on script's secondary settings."""
        mode = script.secondary_script_mode or 'js'
        
        if mode == 'links':
            # Link injection mode
            links = script.secondary_script_links or []
            if links:
                js_code = generate_link_injection_js(links)
                return Response(content=js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)
            return noop_response()
        else:
            # JavaScript mode (default)
            if script.secondary_script:
                return Response(content=script.secondary_script, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)
            return noop_response()

    # Check for direct browser access FIRST
    if not is_script_request():
        return direct_access_response()

    # Must end with .js
    if not script_file.endswith('.js'):
        return noop_response()

    script_slug = script_file[:-3]

    # Resolve project
    result = await db.execute(
        select(Project).where(Project.slug == project_slug)
    )
    project = result.scalar_one_or_none()

    if not project:
        return noop_response()

    if project.status == 'paused':
        # Log denied
        await _log_access(db, project.id, None, request, False)
        return noop_response()

    # Resolve script with whitelists
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(and_(Script.project_id == project.id, Script.slug == script_slug))
    )
    script = result.scalar_one_or_none()

    if not script:
        await _log_access(db, project.id, None, request, False)
        return noop_response()

    if script.status == 'disabled':
        await _log_access(db, project.id, script.id, request, False)
        return noop_response()

    # Extract domain from Origin or Referer
    origin = request.headers.get('origin', '')
    referer = request.headers.get('referer', '')
    raw_domain = origin if origin else referer
    domain = normalize_domain(raw_domain)

    # Load active whitelist patterns from SCRIPT (not project)
    active_patterns = [w.domain_pattern for w in script.whitelists if w.is_active]

    # If whitelist is configured, check domain
    if active_patterns:
        if is_domain_allowed(domain, active_patterns):
            # Domain is whitelisted - serve main script
            await _log_access(db, project.id, script.id, request, True, domain)
            return Response(content=script.js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)
        else:
            # Domain NOT whitelisted - serve SECONDARY script
            await _log_access(db, project.id, script.id, request, False, domain)
            return secondary_response(script)
    else:
        # No whitelist configured = Allow ALL domains (for testing/development)
        await _log_access(db, project.id, script.id, request, True, domain)
        return Response(content=script.js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)


async def _log_access(db: AsyncSession, project_id: int, script_id, request: Request, allowed: bool, domain: str = None, referer_url: str = None):
    """Log access attempt with full referrer URL."""
    try:
        # Get full referrer URL from request headers
        full_referer = referer_url or request.headers.get('referer', '') or request.headers.get('origin', '')
        
        log = AccessLog(
            project_id=project_id,
            script_id=script_id,
            ref_domain=domain or normalize_domain(full_referer),
            referer_url=full_referer[:2048] if full_referer else None,  # Truncate to column max length
            allowed=allowed,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent', '')
        )
        db.add(log)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log access: {e}")


# ─── Health Check ───
@api_router.get("/")
async def root():
    return {"message": "JSHost Platform API", "status": "running"}


# ─── Menu System ───
@api_router.get("/menus")
async def get_system_menus(current_user: dict = Depends(get_current_user)):
    """Return all available system menus."""
    return {"menus": SYSTEM_MENUS}


# ─── Role Management ───
@api_router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    # Count users per role
    role_list = []
    for r in roles:
        count_result = await db.execute(select(func.count(User.id)).where(User.role == r.name))
        user_count = count_result.scalar() or 0
        d = role_to_dict(r)
        d["user_count"] = user_count
        role_list.append(d)
    return {"roles": role_list, "available_menus": SYSTEM_MENUS}


@api_router.post("/roles")
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Role name is required")

    result = await db.execute(select(Role).where(Role.name == data.name.strip().lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role name already exists")

    # Validate permissions against system menus
    valid_keys = {m["key"] for m in SYSTEM_MENUS}
    for p in (data.permissions or []):
        if p not in valid_keys:
            raise HTTPException(status_code=400, detail=f"Invalid permission: {p}")

    role = Role(name=data.name.strip().lower(), description=data.description, permissions=data.permissions or [])
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"role": role_to_dict(role)}


@api_router.patch("/roles/{role_id}")
async def update_role(role_id: int, data: RoleUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if data.name is not None:
        name = data.name.strip().lower()
        if not name:
            raise HTTPException(status_code=400, detail="Role name cannot be empty")
        dup = await db.execute(select(Role).where(and_(Role.name == name, Role.id != role_id)))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role name already exists")
        # Update users with old role name
        if role.name != name:
            await db.execute(
                User.__table__.update().where(User.role == role.name).values(role=name)
            )
        role.name = name

    if data.description is not None:
        role.description = data.description

    if data.permissions is not None:
        valid_keys = {m["key"] for m in SYSTEM_MENUS}
        for p in data.permissions:
            if p not in valid_keys:
                raise HTTPException(status_code=400, detail=f"Invalid permission: {p}")
        role.permissions = data.permissions

    await db.commit()
    await db.refresh(role)
    return {"role": role_to_dict(role)}


@api_router.delete("/roles/{role_id}")
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role")

    # Check if any users have this role
    count = await db.execute(select(func.count(User.id)).where(User.role == role.name))
    if (count.scalar() or 0) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete: role is assigned to users")

    await db.delete(role)
    await db.commit()
    return {"message": "Role deleted"}


# ─── User Management ───
@api_router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(User).order_by(desc(User.created_at)))
    users = result.scalars().all()

    # Get all roles for reference
    roles_result = await db.execute(select(Role).order_by(Role.name))
    roles = roles_result.scalars().all()

    return {
        "users": [user_to_dict(u) for u in users],
        "roles": [role_to_dict(r) for r in roles],
    }


@api_router.post("/users")
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not data.email or not data.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not data.password or len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    email = data.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    role_name = (data.role or 'user').strip().lower()
    role_check = await db.execute(select(Role).where(Role.name == role_name))
    if not role_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Role '{role_name}' does not exist")

    user = User(
        name=data.name.strip() if data.name else None,
        email=email, 
        password_hash=hash_password(data.password), 
        role=role_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"user": user_to_dict(user)}


@api_router.patch("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name.strip() if data.name else None

    if data.role is not None:
        # Verify role exists
        role_check = await db.execute(select(Role).where(Role.name == data.role))
        if not role_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Role '{data.role}' does not exist")
        user.role = data.role

    if data.is_active is not None:
        # Prevent deactivating self
        if user.id == current_user['user_id'] and not data.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return {"user": user_to_dict(user)}


# ─── Custom Domains ───
import socket
import subprocess

# Known Cloudflare IP ranges (partial list - most common ranges)
CLOUDFLARE_IP_RANGES = [
    "103.21.244.", "103.22.200.", "103.31.4.", "104.16.", "104.17.", "104.18.", "104.19.", 
    "104.20.", "104.21.", "104.22.", "104.23.", "104.24.", "104.25.", "104.26.", "104.27.",
    "108.162.", "131.0.72.", "141.101.", "162.158.", "172.64.", "172.65.", "172.66.", 
    "172.67.", "173.245.", "188.114.", "190.93.", "197.234.", "198.41.", "184.21.", "184.72."
]

def is_cloudflare_ip(ip: str) -> bool:
    """Check if an IP belongs to Cloudflare."""
    if not ip:
        return False
    for cf_range in CLOUDFLARE_IP_RANGES:
        if ip.startswith(cf_range):
            return True
    return False


def resolve_domain_ip(domain: str) -> str:
    """Resolve a domain to its A record IP address."""
    try:
        result = socket.getaddrinfo(domain, None, socket.AF_INET)
        if result:
            return result[0][4][0]
    except (socket.gaierror, socket.herror, OSError):
        pass
    return None


def resolve_domain_cname(domain: str) -> str:
    """Try to resolve CNAME record for a domain."""
    try:
        result = subprocess.run(
            ['dig', '+short', 'CNAME', domain],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().rstrip('.')
    except Exception:
        pass
    return None


def verify_domain_via_http(domain: str, platform_domain: str) -> bool:
    """
    Verify domain by making an HTTP request to check if traffic routes correctly.
    This works for Cloudflare-proxied domains.
    """
    import urllib.request
    import ssl
    
    try:
        # Create an SSL context that doesn't verify certificates (for testing)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Try to access a health endpoint on the custom domain
        url = f"https://{domain}/api/health"
        req = urllib.request.Request(url, headers={'Host': domain})
        
        response = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = response.read().decode('utf-8')
        
        # Check if response contains expected data
        if 'status' in data.lower() or 'ok' in data.lower():
            return True
    except Exception:
        pass
    
    try:
        # Try HTTP as fallback
        url = f"http://{domain}/api/health"
        req = urllib.request.Request(url, headers={'Host': domain})
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('utf-8')
        if 'status' in data.lower() or 'ok' in data.lower():
            return True
    except Exception:
        pass
    
    return False


def get_platform_ip() -> str:
    """Get the platform's public IP by resolving the main domain or using external IP service."""
    # First, try to resolve from environment variable (if set)
    env_ip = os.environ.get('PLATFORM_PUBLIC_IP')
    if env_ip:
        return env_ip
    
    # Try to get the IP of our main preview domain
    try:
        backend_url = os.environ.get('REACT_APP_BACKEND_URL', '')
        if backend_url:
            from urllib.parse import urlparse
            hostname = urlparse(backend_url).hostname
            if hostname:
                result = socket.getaddrinfo(hostname, None, socket.AF_INET)
                if result:
                    return result[0][4][0]
    except Exception:
        pass
    
    # Fallback: try to get external IP from service
    try:
        import urllib.request
        return urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf-8')
    except Exception:
        pass
    
    # Last resort: return local IP (not ideal)
    try:
        result = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        if result:
            return result[0][4][0]
    except Exception:
        pass
    
    return None


@api_router.get("/custom-domains")
async def list_custom_domains(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    result = await db.execute(select(CustomDomain).order_by(desc(CustomDomain.created_at)))
    domains = result.scalars().all()
    return {"domains": [custom_domain_to_dict(d) for d in domains]}


@api_router.get("/custom-domains/active")
async def list_active_domains(db: AsyncSession = Depends(get_db)):
    """Public endpoint: returns active verified domains for embed URL selection."""
    result = await db.execute(
        select(CustomDomain).where(and_(CustomDomain.is_active == True, CustomDomain.status == 'verified'))
    )
    domains = result.scalars().all()
    return {"domains": [{"id": d.id, "domain": d.domain} for d in domains]}


@api_router.post("/custom-domains", status_code=status.HTTP_201_CREATED)
async def add_custom_domain(data: CustomDomainCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    domain = data.domain.lower().strip()

    # Validate domain format
    if not domain or '/' in domain or ':' in domain or ' ' in domain:
        raise HTTPException(status_code=400, detail="Invalid domain format")
    if '.' not in domain:
        raise HTTPException(status_code=400, detail="Domain must contain at least one dot")

    # Check duplicate
    result = await db.execute(select(CustomDomain).where(CustomDomain.domain == domain))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain already added")

    # Get platform IP
    platform_ip = get_platform_ip()

    entry = CustomDomain(
        domain=domain,
        status='pending',
        platform_ip=platform_ip,
        created_by=current_user['user_id'],
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"domain": custom_domain_to_dict(entry)}


@api_router.post("/custom-domains/{domain_id}/verify")
async def verify_custom_domain(domain_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    result = await db.execute(select(CustomDomain).where(CustomDomain.id == domain_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Resolve domain A record
    resolved_ip = resolve_domain_ip(entry.domain)
    platform_ip = get_platform_ip()
    
    # Get platform hostname for CNAME verification
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', '')
    platform_hostname = None
    if backend_url:
        from urllib.parse import urlparse
        platform_hostname = urlparse(backend_url).hostname

    entry.resolved_ip = resolved_ip
    entry.platform_ip = platform_ip
    
    verification_method = "ip_match"
    is_verified = False
    is_cloudflare = False
    cname_target = None
    
    # Method 1: Direct IP match
    if resolved_ip and platform_ip and resolved_ip == platform_ip:
        is_verified = True
        verification_method = "ip_match"
    
    # Method 2: Check if using Cloudflare proxy
    elif resolved_ip and is_cloudflare_ip(resolved_ip):
        is_cloudflare = True
        
        # Check CNAME record
        cname_target = resolve_domain_cname(entry.domain)
        
        # If CNAME points to our platform domain, consider it valid
        if cname_target and platform_hostname and platform_hostname in cname_target:
            is_verified = True
            verification_method = "cname_match"
        else:
            # Try HTTP verification (domain routes traffic to us via Cloudflare)
            if verify_domain_via_http(entry.domain, platform_hostname):
                is_verified = True
                verification_method = "http_verify"
            else:
                # Cloudflare detected but not properly configured
                # We'll allow it if user has set up Cloudflare to proxy to us
                # Mark as "cloudflare_pending" for manual verification
                entry.status = 'cloudflare_pending'
                verification_method = "cloudflare_detected"
    
    # Method 3: CNAME verification for non-Cloudflare CDNs
    elif not is_verified:
        cname_target = resolve_domain_cname(entry.domain)
        if cname_target and platform_hostname and platform_hostname in cname_target:
            is_verified = True
            verification_method = "cname_match"
    
    if is_verified:
        entry.status = 'verified'
        entry.is_active = True
        entry.verified_at = datetime.now(timezone.utc)
    elif entry.status != 'cloudflare_pending':
        entry.status = 'failed'
        entry.is_active = False

    await db.commit()
    await db.refresh(entry)
    
    return {
        "domain": custom_domain_to_dict(entry),
        "verification": {
            "platform_ip": platform_ip,
            "resolved_ip": resolved_ip,
            "cname_target": cname_target,
            "is_cloudflare": is_cloudflare,
            "verification_method": verification_method,
            "match": is_verified,
            "message": get_verification_message(is_verified, is_cloudflare, verification_method, platform_hostname, platform_ip)
        }
    }


def get_verification_message(is_verified: bool, is_cloudflare: bool, method: str, platform_hostname: str, platform_ip: str) -> str:
    """Generate a helpful message based on verification result."""
    if is_verified:
        if method == "ip_match":
            return "DNS verified! Your domain points directly to the platform IP."
        elif method == "cname_match":
            return "DNS verified via CNAME! Your domain correctly points to the platform."
        elif method == "http_verify":
            return "Verified via Cloudflare! Traffic is correctly routed through Cloudflare to the platform."
        return "Domain verified successfully!"
    
    if is_cloudflare:
        return f"Cloudflare proxy detected. Please configure Cloudflare to proxy traffic to: {platform_hostname or platform_ip}. You can either: 1) Create a CNAME record pointing to {platform_hostname}, or 2) In Cloudflare, set the origin server to {platform_ip}"
    
    return f"DNS verification failed. Please point your domain's A record to {platform_ip} or create a CNAME to {platform_hostname}"


@api_router.patch("/custom-domains/{domain_id}")
async def update_custom_domain(domain_id: int, data: CustomDomainUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    result = await db.execute(select(CustomDomain).where(CustomDomain.id == domain_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domain not found")

    if data.is_active is not None:
        # Allow activation for verified domains OR cloudflare_pending domains (manual override)
        if data.is_active and entry.status not in ['verified', 'cloudflare_pending']:
            raise HTTPException(status_code=400, detail="Cannot activate unverified domain. Verify DNS first.")
        entry.is_active = data.is_active
        
        # If activating a cloudflare_pending domain, mark it as verified (manual override)
        if data.is_active and entry.status == 'cloudflare_pending':
            entry.status = 'verified'
            entry.verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(entry)
    return {"domain": custom_domain_to_dict(entry)}


@api_router.post("/custom-domains/{domain_id}/force-activate")
async def force_activate_domain(domain_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    """
    Force activate a domain (admin override).
    Useful for Cloudflare-proxied domains where automatic verification may fail.
    """
    result = await db.execute(select(CustomDomain).where(CustomDomain.id == domain_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Check if user is admin
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can force-activate domains")
    
    entry.status = 'verified'
    entry.is_active = True
    entry.verified_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(entry)
    return {
        "domain": custom_domain_to_dict(entry),
        "message": "Domain force-activated by admin"
    }


@api_router.delete("/custom-domains/{domain_id}")
async def delete_custom_domain(domain_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    result = await db.execute(select(CustomDomain).where(CustomDomain.id == domain_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domain not found")

    await db.delete(entry)
    await db.commit()
    return {"message": "Domain deleted"}


# ─── Standalone Popunder Campaign Routes ───
@api_router.get("/popunders")
async def list_popunder_campaigns(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all popunder campaigns for the current user. Admins can see all campaigns."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    
    if is_admin:
        # Admin can see all campaigns
        result = await db.execute(
            select(PopunderCampaign)
            .order_by(desc(PopunderCampaign.created_at))
        )
    else:
        # Regular users only see their own campaigns
        result = await db.execute(
            select(PopunderCampaign)
            .where(PopunderCampaign.user_id == user_id)
            .order_by(desc(PopunderCampaign.created_at))
        )
    campaigns = result.scalars().all()
    return {"popunders": [popunder_campaign_to_dict(c) for c in campaigns]}


@api_router.post("/popunders")
async def create_popunder_campaign(data: PopunderCampaignCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create a new popunder campaign."""
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Campaign name is required")

    if not data.settings or not data.settings.url_list or not data.settings.url_list.strip():
        raise HTTPException(status_code=400, detail="At least one URL is required")

    if data.status and data.status not in ('active', 'paused'):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")

    slug = await generate_popunder_slug(db, data.name.strip())
    settings_dict = data.settings.model_dump() if data.settings else {}

    campaign = PopunderCampaign(
        user_id=current_user['user_id'],
        name=data.name.strip(),
        slug=slug,
        status=data.status or 'active',
        settings=settings_dict,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"popunder": popunder_campaign_to_dict(campaign)}


@api_router.get("/popunders/{campaign_id}")
async def get_popunder_campaign(campaign_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get a specific popunder campaign."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    campaign = await get_user_campaign(db, campaign_id, user_id, is_admin)
    return {"popunder": popunder_campaign_to_dict(campaign)}


@api_router.patch("/popunders/{campaign_id}")
async def update_popunder_campaign(campaign_id: int, data: PopunderCampaignUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Update a popunder campaign."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    campaign = await get_user_campaign(db, campaign_id, user_id, is_admin)

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Campaign name cannot be empty")
        campaign.name = name
        campaign.slug = await generate_popunder_slug(db, name)

    if data.settings is not None:
        if not data.settings.url_list or not data.settings.url_list.strip():
            raise HTTPException(status_code=400, detail="At least one URL is required")
        campaign.settings = data.settings.model_dump()

    if data.status is not None:
        if data.status not in ('active', 'paused'):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")
        campaign.status = data.status

    await db.commit()
    await db.refresh(campaign)
    return {"popunder": popunder_campaign_to_dict(campaign)}


@api_router.delete("/popunders/{campaign_id}")
async def delete_popunder_campaign(campaign_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete a popunder campaign."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    campaign = await get_user_campaign(db, campaign_id, user_id, is_admin)
    await db.delete(campaign)
    await db.commit()
    return {"message": "Popunder campaign deleted"}


# ─── Campaign Analytics Endpoints ───
@api_router.post("/popunder-analytics")
async def track_popunder_event(data: CampaignAnalyticsEvent, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint to track popunder impressions and clicks."""
    # Validate event type
    if data.event_type not in ('impression', 'click'):
        raise HTTPException(status_code=400, detail="Invalid event type")
    
    # Verify campaign exists
    result = await db.execute(select(PopunderCampaign).where(PopunderCampaign.id == data.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get IP and hash it for privacy
    client_ip = request.client.host if request.client else None
    ip_hash = None
    if client_ip:
        import hashlib
        ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:32]
    
    # Get user agent
    user_agent = request.headers.get('user-agent', '')[:512]
    
    # Create analytics entry
    analytics = CampaignAnalytics(
        campaign_id=data.campaign_id,
        event_type=data.event_type,
        referer_url=data.referer_url[:2048] if data.referer_url else None,
        target_url=data.target_url[:2048] if data.target_url else None,
        user_agent=user_agent,
        ip_hash=ip_hash,
        device_type=data.device_type
    )
    db.add(analytics)
    await db.commit()
    
    return {"status": "ok"}


@api_router.get("/popunders/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get analytics summary for a campaign."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    campaign = await get_user_campaign(db, campaign_id, user_id, is_admin)
    
    # Get total impressions
    impressions_result = await db.execute(
        select(func.count(CampaignAnalytics.id))
        .where(and_(CampaignAnalytics.campaign_id == campaign_id, CampaignAnalytics.event_type == 'impression'))
    )
    total_impressions = impressions_result.scalar() or 0
    
    # Get total clicks
    clicks_result = await db.execute(
        select(func.count(CampaignAnalytics.id))
        .where(and_(CampaignAnalytics.campaign_id == campaign_id, CampaignAnalytics.event_type == 'click'))
    )
    total_clicks = clicks_result.scalar() or 0
    
    # Get unique impressions (by ip_hash)
    unique_impressions_result = await db.execute(
        select(func.count(func.distinct(CampaignAnalytics.ip_hash)))
        .where(and_(CampaignAnalytics.campaign_id == campaign_id, CampaignAnalytics.event_type == 'impression'))
    )
    unique_impressions = unique_impressions_result.scalar() or 0
    
    # Get clicks by device
    device_clicks = await db.execute(
        select(CampaignAnalytics.device_type, func.count(CampaignAnalytics.id))
        .where(and_(CampaignAnalytics.campaign_id == campaign_id, CampaignAnalytics.event_type == 'click'))
        .group_by(CampaignAnalytics.device_type)
    )
    clicks_by_device = {row[0] or 'unknown': row[1] for row in device_clicks.fetchall()}
    
    # Get top referers
    top_referers = await db.execute(
        select(CampaignAnalytics.referer_url, func.count(CampaignAnalytics.id).label('count'))
        .where(and_(CampaignAnalytics.campaign_id == campaign_id, CampaignAnalytics.referer_url != None))
        .group_by(CampaignAnalytics.referer_url)
        .order_by(desc('count'))
        .limit(10)
    )
    referers = [{"url": row[0], "count": row[1]} for row in top_referers.fetchall()]
    
    # Calculate CTR
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "summary": {
            "total_impressions": total_impressions,
            "unique_impressions": unique_impressions,
            "total_clicks": total_clicks,
            "ctr": round(ctr, 2)
        },
        "clicks_by_device": clicks_by_device,
        "top_referers": referers
    }


@api_router.get("/popunders/{campaign_id}/analytics/logs")
async def get_campaign_analytics_logs(campaign_id: int, page: int = 1, per_page: int = 20, event_type: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get individual analytics log entries with pagination."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_campaign(db, campaign_id, user_id, is_admin)
    
    # Build query
    query = select(CampaignAnalytics).where(CampaignAnalytics.campaign_id == campaign_id)
    count_query = select(func.count(CampaignAnalytics.id)).where(CampaignAnalytics.campaign_id == campaign_id)
    
    if event_type and event_type in ('impression', 'click'):
        query = query.where(CampaignAnalytics.event_type == event_type)
        count_query = count_query.where(CampaignAnalytics.event_type == event_type)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = query.order_by(desc(CampaignAnalytics.created_at)).offset(offset).limit(per_page)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "referer_url": log.referer_url,
                "target_url": log.target_url,
                "device_type": log.device_type,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }


@api_router.delete("/popunders/{campaign_id}/analytics")
async def clear_campaign_analytics(campaign_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Clear all analytics for a campaign."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_campaign(db, campaign_id, user_id, is_admin)
    
    await db.execute(
        CampaignAnalytics.__table__.delete().where(CampaignAnalytics.campaign_id == campaign_id)
    )
    await db.commit()
    
    return {"message": "Analytics cleared"}


@api_router.delete("/popunders/{campaign_id}/analytics/{log_id}")
async def delete_campaign_analytics_log(campaign_id: int, log_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete a single analytics log entry."""
    user_id = current_user['user_id']
    is_admin = await is_user_admin(db, user_id)
    await get_user_campaign(db, campaign_id, user_id, is_admin)
    
    result = await db.execute(
        select(CampaignAnalytics).where(and_(CampaignAnalytics.id == log_id, CampaignAnalytics.campaign_id == campaign_id))
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    await db.delete(log)
    await db.commit()
    
    return {"message": "Log entry deleted"}


# ─── Seed Data ───
SEED_CATEGORIES = [
    {"name": "Website", "description": "General website scripts"},
    {"name": "Landing Page", "description": "Landing page specific scripts"},
    {"name": "AMP", "description": "AMP (Accelerated Mobile Pages) scripts"},
    {"name": "Partner", "description": "Partner integration scripts"},
    {"name": "Internal", "description": "Internal tooling scripts"},
]

SEED_ROLES = [
    {"name": "admin", "description": "Full access to all features", "is_system": True, "permissions": ["dashboard", "projects", "popunders", "settings", "user_management", "custom_domains"]},
    {"name": "user", "description": "Standard user with project access", "is_system": True, "permissions": ["dashboard", "projects", "popunders", "settings", "custom_domains"]},
]


async def seed_categories():
    async with async_session_maker() as db:
        for cat_data in SEED_CATEGORIES:
            result = await db.execute(select(Category).where(Category.name == cat_data['name']))
            if not result.scalar_one_or_none():
                db.add(Category(**cat_data))
        await db.commit()
        logger.info("Categories seeded successfully")


async def seed_roles():
    async with async_session_maker() as db:
        for role_data in SEED_ROLES:
            result = await db.execute(select(Role).where(Role.name == role_data['name']))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(Role(**role_data))
            else:
                # Update permissions for system roles to include any new menus
                if existing.is_system:
                    existing.permissions = role_data['permissions']
        await db.commit()
        logger.info("Roles seeded successfully")


# ─── Startup / Shutdown ───
@app.on_event("startup")
async def startup():
    await init_db()
    await seed_categories()
    await seed_roles()
    logger.info("Database initialized and seeded")


@app.on_event("shutdown")
async def shutdown():
    from database import engine
    await engine.dispose()


# ─── Include Routers & Middleware ───
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for test pages
static_dir = ROOT_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
