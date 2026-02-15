from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
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
from models import User, Category, Project, Script, ScriptWhitelist, AccessLog, Role, CustomDomain, PopunderCampaign
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


# ─── Pydantic Schemas ───
class UserRegister(BaseModel):
    email: str
    password: str

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
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserCreate(BaseModel):
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


# ─── Helpers ───
def user_to_dict(u: User) -> dict:
    return {"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None}

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
        d["scripts"] = [script_to_dict(s) for s in p.scripts] if p.scripts else []
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
    return {"id": l.id, "project_id": l.project_id, "script_id": l.script_id, "ref_domain": l.ref_domain, "allowed": l.allowed, "ip": l.ip, "user_agent": l.user_agent, "created_at": l.created_at.isoformat() if l.created_at else None}

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


async def get_user_project(db: AsyncSession, project_id: int, user_id: int) -> Project:
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.category), selectinload(Project.whitelists), selectinload(Project.scripts))
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


async def get_user_campaign(db: AsyncSession, campaign_id: int, user_id: int) -> PopunderCampaign:
    """Get a popunder campaign owned by the user."""
    result = await db.execute(
        select(PopunderCampaign)
        .where(and_(PopunderCampaign.id == campaign_id, PopunderCampaign.user_id == user_id))
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Popunder campaign not found")
    return campaign


# ─── Auth Routes ───
@api_router.post("/auth/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Get role permissions
    role_result = await db.execute(select(Role).where(Role.name == user.role))
    role = role_result.scalar_one_or_none()
    user_dict = user_to_dict(user)
    user_dict["permissions"] = role.permissions if role else []

    token = create_token(user.id, user.email)
    return {"token": token, "user": user_dict}


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
        select(Project).options(selectinload(Project.category), selectinload(Project.whitelists), selectinload(Project.scripts))
        .where(Project.id == project.id)
    )
    project = result.scalar_one()
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.category), selectinload(Project.whitelists), selectinload(Project.scripts))
        .where(Project.user_id == current_user['user_id'])
        .order_by(desc(Project.created_at))
    )
    projects = result.scalars().all()
    return {"projects": [project_to_dict(p, include_relations=True) for p in projects]}


@api_router.get("/projects/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.patch("/projects/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])

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
        select(Project).options(selectinload(Project.category), selectinload(Project.whitelists), selectinload(Project.scripts))
        .where(Project.id == project.id)
    )
    project = result.scalar_one()
    return {"project": project_to_dict(project, include_relations=True)}


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}


# ─── Whitelist Routes (per Script) ───
@api_router.get("/projects/{project_id}/scripts/{script_id}/whitelist")
async def list_whitelist(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
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
    await get_user_project(db, project_id, current_user['user_id'])
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
    await get_user_project(db, project_id, current_user['user_id'])

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
    await get_user_project(db, project_id, current_user['user_id'])

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
    await get_user_project(db, project_id, current_user['user_id'])
    result = await db.execute(
        select(Script).options(selectinload(Script.whitelists))
        .where(Script.project_id == project_id).order_by(desc(Script.created_at))
    )
    scripts = result.scalars().all()
    return {"scripts": [script_to_dict(s, include_whitelists=True) for s in scripts]}


@api_router.post("/projects/{project_id}/scripts")
async def create_script(project_id: int, data: ScriptCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])

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
    return {"script": script_to_dict(script, include_whitelists=True)}


@api_router.get("/projects/{project_id}/scripts/{script_id}")
async def get_script(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
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
    await get_user_project(db, project_id, current_user['user_id'])
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
    await db.refresh(script)
    return {"script": script_to_dict(script, include_whitelists=True)}


@api_router.delete("/projects/{project_id}/scripts/{script_id}")
async def delete_script(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
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
    await get_user_project(db, project_id, current_user['user_id'])

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
    await get_user_project(db, project_id, current_user['user_id'])
    
    await db.execute(
        AccessLog.__table__.delete().where(AccessLog.project_id == project_id)
    )
    await db.commit()
    
    return {"message": "Access logs cleared"}


# ─── Analytics ───
@api_router.get("/projects/{project_id}/analytics")
async def get_analytics(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])

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

    return {
        "summary": {"total": total_val, "allowed": allowed_val, "denied": total_val - allowed_val},
        "daily": daily_data,
        "top_domains": domain_data,
        "by_script": script_data,
    }


# ─── Blacklisted Domains (non-whitelisted) ───
@api_router.get("/projects/{project_id}/blacklisted-domains")
async def get_blacklisted_domains(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get list of domains that were denied access (not whitelisted)."""
    await get_user_project(db, project_id, current_user['user_id'])

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


# ─── Domain Tester (for scripts) ───
@api_router.post("/projects/{project_id}/scripts/{script_id}/test-domain")
async def test_domain(project_id: int, script_id: int, data: DomainTestRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
    
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


# ─── Public Popunder JS Delivery (must come before general JS delivery) ───

# Self-contained popunder engine JavaScript template
POPUNDER_ENGINE_TEMPLATE = '''(function(){
var c = __CONFIG__;

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

// Open popunder
function openPopunder() {
    var url = getUrl();
    if (!url) return;
    if (!checkFrequency()) return;
    if (!checkDevice()) return;
    
    var w = screen.width;
    var h = screen.height;
    var features = 'width=' + w + ',height=' + h + ',top=0,left=0,scrollbars=yes,resizable=yes,toolbar=no,menubar=no,location=no,status=no';
    
    try {
        var win = window.open(url, '_blank', features);
        if (win) {
            win.blur();
            window.focus();
            markShown();
        }
    } catch(e) {}
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

    js_code = POPUNDER_ENGINE_TEMPLATE.replace('__CONFIG__', json.dumps(config))
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
    """Public JS delivery endpoint. Returns noop or secondary script for any unauthorized request (always 200)."""

    def noop_response():
        return Response(content=NOOP_JS, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)

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
        
        # Fallback: check Accept header
        # Direct browser access typically accepts text/html
        # Script loading typically accepts */*
        accept = request.headers.get('accept', '')
        if 'text/html' in accept:
            return False
        
        # If Origin or Referer is present, it's likely from a page
        if request.headers.get('origin') or request.headers.get('referer'):
            return True
        
        return False

    def secondary_response(script: Script):
        """Generate secondary response based on script's secondary settings."""
        # Only serve secondary content when loaded as a script, not direct browser access
        if not is_script_request():
            return noop_response()
        
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

    # Empty whitelist = deny (serve secondary script if configured)
    if not active_patterns:
        await _log_access(db, project.id, script.id, request, False, domain)
        return secondary_response(script)

    # Match domain
    if is_domain_allowed(domain, active_patterns):
        await _log_access(db, project.id, script.id, request, True, domain)
        return Response(content=script.js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)
    else:
        # Domain not whitelisted - serve secondary response
        await _log_access(db, project.id, script.id, request, False, domain)
        return secondary_response(script)


async def _log_access(db: AsyncSession, project_id: int, script_id, request: Request, allowed: bool, domain: str = None):
    """Log access attempt."""
    try:
        log = AccessLog(
            project_id=project_id,
            script_id=script_id,
            ref_domain=domain or normalize_domain(request.headers.get('origin', '') or request.headers.get('referer', '')),
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

    user = User(email=email, password_hash=hash_password(data.password), role=role_name)
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

def resolve_domain_ip(domain: str) -> str:
    """Resolve a domain to its A record IP address."""
    try:
        result = socket.getaddrinfo(domain, None, socket.AF_INET)
        if result:
            return result[0][4][0]
    except (socket.gaierror, socket.herror, OSError):
        pass
    return None


def get_platform_ip() -> str:
    """Get the platform's public IP."""
    try:
        result = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        if result:
            return result[0][4][0]
    except Exception:
        pass
    # Fallback: try to get external IP
    try:
        import urllib.request
        return urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf-8')
    except Exception:
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

    entry.resolved_ip = resolved_ip
    entry.platform_ip = platform_ip

    if resolved_ip and platform_ip and resolved_ip == platform_ip:
        entry.status = 'verified'
        entry.is_active = True
        entry.verified_at = datetime.now(timezone.utc)
    else:
        entry.status = 'failed'
        entry.is_active = False

    await db.commit()
    await db.refresh(entry)
    return {
        "domain": custom_domain_to_dict(entry),
        "verification": {
            "platform_ip": platform_ip,
            "resolved_ip": resolved_ip,
            "match": resolved_ip == platform_ip if (resolved_ip and platform_ip) else False,
        }
    }


@api_router.patch("/custom-domains/{domain_id}")
async def update_custom_domain(domain_id: int, data: CustomDomainUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission('custom_domains'))):
    result = await db.execute(select(CustomDomain).where(CustomDomain.id == domain_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domain not found")

    if data.is_active is not None:
        if data.is_active and entry.status != 'verified':
            raise HTTPException(status_code=400, detail="Cannot activate unverified domain. Verify DNS first.")
        entry.is_active = data.is_active

    await db.commit()
    await db.refresh(entry)
    return {"domain": custom_domain_to_dict(entry)}


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
    """List all popunder campaigns for the current user."""
    result = await db.execute(
        select(PopunderCampaign)
        .where(PopunderCampaign.user_id == current_user['user_id'])
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
    campaign = await get_user_campaign(db, campaign_id, current_user['user_id'])
    return {"popunder": popunder_campaign_to_dict(campaign)}


@api_router.patch("/popunders/{campaign_id}")
async def update_popunder_campaign(campaign_id: int, data: PopunderCampaignUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Update a popunder campaign."""
    campaign = await get_user_campaign(db, campaign_id, current_user['user_id'])

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
    campaign = await get_user_campaign(db, campaign_id, current_user['user_id'])
    await db.delete(campaign)
    await db.commit()
    return {"message": "Popunder campaign deleted"}


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
    {"name": "user", "description": "Standard user with project access", "is_system": True, "permissions": ["dashboard", "projects", "popunders"]},
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
