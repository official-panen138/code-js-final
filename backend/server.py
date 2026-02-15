from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import selectinload
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from slugify import slugify

from database import get_db, init_db, async_session_maker
from models import User, Category, Project, ProjectWhitelist, Script, AccessLog, Role
from auth import hash_password, verify_password, create_token, get_current_user
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

class ScriptCreate(BaseModel):
    name: str
    js_code: str
    status: Optional[str] = 'active'

class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    js_code: Optional[str] = None
    status: Optional[str] = None

class DomainTestRequest(BaseModel):
    domain: str

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


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
        d["whitelists"] = [whitelist_to_dict(w) for w in p.whitelists] if p.whitelists else []
        d["scripts"] = [script_to_dict(s) for s in p.scripts] if p.scripts else []
        d["script_count"] = len(p.scripts) if p.scripts else 0
        d["whitelist_count"] = len(p.whitelists) if p.whitelists else 0
    return d

def whitelist_to_dict(w: ProjectWhitelist) -> dict:
    return {"id": w.id, "project_id": w.project_id, "domain_pattern": w.domain_pattern, "is_active": w.is_active, "created_at": w.created_at.isoformat() if w.created_at else None}

def script_to_dict(s: Script) -> dict:
    return {"id": s.id, "project_id": s.project_id, "name": s.name, "slug": s.slug, "js_code": s.js_code, "status": s.status, "created_at": s.created_at.isoformat() if s.created_at else None}

def log_to_dict(l: AccessLog) -> dict:
    return {"id": l.id, "project_id": l.project_id, "script_id": l.script_id, "ref_domain": l.ref_domain, "allowed": l.allowed, "ip": l.ip, "user_agent": l.user_agent, "created_at": l.created_at.isoformat() if l.created_at else None}


async def generate_unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name, max_length=200)
    slug = base
    counter = 1
    while True:
        result = await db.execute(select(Project).where(Project.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


async def generate_script_slug(db: AsyncSession, project_id: int, name: str) -> str:
    base = slugify(name, max_length=200)
    slug = base
    counter = 1
    while True:
        result = await db.execute(select(Script).where(and_(Script.project_id == project_id, Script.slug == slug)))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


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

    token = create_token(user.id, user.email)
    return {"token": token, "user": user_to_dict(user)}


@api_router.post("/auth/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_token(user.id, user.email)
    return {"token": token, "user": user_to_dict(user)}


@api_router.get("/auth/me")
async def get_me(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == current_user['user_id']))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user_to_dict(user)}


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
        project.slug = await generate_unique_slug(db, data.name)
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


# ─── Whitelist Routes ───
@api_router.get("/projects/{project_id}/whitelist")
async def list_whitelist(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
    result = await db.execute(
        select(ProjectWhitelist).where(ProjectWhitelist.project_id == project_id).order_by(desc(ProjectWhitelist.created_at))
    )
    entries = result.scalars().all()
    return {"whitelists": [whitelist_to_dict(w) for w in entries]}


@api_router.post("/projects/{project_id}/whitelist")
async def add_whitelist(project_id: int, data: WhitelistCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])

    pattern = data.domain_pattern.lower().strip()
    is_valid, msg = validate_domain_pattern(pattern)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # Check duplicate
    result = await db.execute(
        select(ProjectWhitelist).where(and_(ProjectWhitelist.project_id == project_id, ProjectWhitelist.domain_pattern == pattern))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain pattern already exists for this project")

    entry = ProjectWhitelist(project_id=project_id, domain_pattern=pattern)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"whitelist": whitelist_to_dict(entry)}


@api_router.patch("/projects/{project_id}/whitelist/{whitelist_id}")
async def update_whitelist(project_id: int, whitelist_id: int, data: WhitelistUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])

    result = await db.execute(select(ProjectWhitelist).where(and_(ProjectWhitelist.id == whitelist_id, ProjectWhitelist.project_id == project_id)))
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


@api_router.delete("/projects/{project_id}/whitelist/{whitelist_id}")
async def delete_whitelist(project_id: int, whitelist_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])

    result = await db.execute(select(ProjectWhitelist).where(and_(ProjectWhitelist.id == whitelist_id, ProjectWhitelist.project_id == project_id)))
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
    result = await db.execute(select(Script).where(Script.project_id == project_id).order_by(desc(Script.created_at)))
    scripts = result.scalars().all()
    return {"scripts": [script_to_dict(s) for s in scripts]}


@api_router.post("/projects/{project_id}/scripts")
async def create_script(project_id: int, data: ScriptCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])

    if data.status and data.status not in ('active', 'disabled'):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'disabled'")

    slug = await generate_script_slug(db, project_id, data.name)
    script = Script(project_id=project_id, name=data.name, slug=slug, js_code=data.js_code, status=data.status or 'active')
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return {"script": script_to_dict(script)}


@api_router.get("/projects/{project_id}/scripts/{script_id}")
async def get_script(project_id: int, script_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
    result = await db.execute(select(Script).where(and_(Script.id == script_id, Script.project_id == project_id)))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"script": script_to_dict(script)}


@api_router.patch("/projects/{project_id}/scripts/{script_id}")
async def update_script(project_id: int, script_id: int, data: ScriptUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])
    result = await db.execute(select(Script).where(and_(Script.id == script_id, Script.project_id == project_id)))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if data.name is not None:
        script.name = data.name
        script.slug = await generate_script_slug(db, project_id, data.name)
    if data.js_code is not None:
        script.js_code = data.js_code
    if data.status is not None:
        if data.status not in ('active', 'disabled'):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'disabled'")
        script.status = data.status

    await db.commit()
    await db.refresh(script)
    return {"script": script_to_dict(script)}


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
        select(func.count(ProjectWhitelist.id)).join(Project).where(Project.user_id == uid)
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
        .options(selectinload(Project.category), selectinload(Project.whitelists), selectinload(Project.scripts))
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


# ─── Analytics ───
@api_router.get("/projects/{project_id}/analytics")
async def get_analytics(project_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_user_project(db, project_id, current_user['user_id'])

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

    return {
        "summary": {"total": total_val, "allowed": allowed_val, "denied": total_val - allowed_val},
        "daily": daily_data,
        "top_domains": domain_data,
    }


# ─── Domain Tester ───
@api_router.post("/projects/{project_id}/test-domain")
async def test_domain(project_id: int, data: DomainTestRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    project = await get_user_project(db, project_id, current_user['user_id'])

    normalized = normalize_domain(data.domain)
    active_patterns = [w.domain_pattern for w in project.whitelists if w.is_active]

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


# ─── Public JS Delivery ───
@api_router.get("/js/{project_slug}/{script_file}")
async def deliver_js(project_slug: str, script_file: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Public JS delivery endpoint. Returns noop for any unauthorized request (always 200)."""

    def noop_response():
        return Response(content=NOOP_JS, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)

    # Must end with .js
    if not script_file.endswith('.js'):
        return noop_response()

    script_slug = script_file[:-3]

    # Resolve project
    result = await db.execute(
        select(Project).options(selectinload(Project.whitelists)).where(Project.slug == project_slug)
    )
    project = result.scalar_one_or_none()

    if not project:
        return noop_response()

    if project.status == 'paused':
        # Log denied
        await _log_access(db, project.id, None, request, False)
        return noop_response()

    # Resolve script
    result = await db.execute(
        select(Script).where(and_(Script.project_id == project.id, Script.slug == script_slug))
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

    # Load active whitelist patterns
    active_patterns = [w.domain_pattern for w in project.whitelists if w.is_active]

    # Empty whitelist = deny
    if not active_patterns:
        await _log_access(db, project.id, script.id, request, False, domain)
        return noop_response()

    # Match domain
    if is_domain_allowed(domain, active_patterns):
        await _log_access(db, project.id, script.id, request, True, domain)
        return Response(content=script.js_code, media_type="application/javascript; charset=utf-8", headers=JS_CACHE_HEADERS)
    else:
        await _log_access(db, project.id, script.id, request, False, domain)
        return noop_response()


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


# ─── Seed Data ───
SEED_CATEGORIES = [
    {"name": "Website", "description": "General website scripts"},
    {"name": "Landing Page", "description": "Landing page specific scripts"},
    {"name": "AMP", "description": "AMP (Accelerated Mobile Pages) scripts"},
    {"name": "Partner", "description": "Partner integration scripts"},
    {"name": "Internal", "description": "Internal tooling scripts"},
]


async def seed_categories():
    async with async_session_maker() as db:
        for cat_data in SEED_CATEGORIES:
            result = await db.execute(select(Category).where(Category.name == cat_data['name']))
            if not result.scalar_one_or_none():
                db.add(Category(**cat_data))
        await db.commit()
        logger.info("Categories seeded successfully")


# ─── Startup / Shutdown ───
@app.on_event("startup")
async def startup():
    await init_db()
    await seed_categories()
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
