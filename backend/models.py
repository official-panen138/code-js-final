from sqlalchemy import Column, Integer, String, Text, Boolean, Enum, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy import func
from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    projects = relationship('Project', back_populates='user', cascade='all, delete-orphan')
    popunder_campaigns = relationship('PopunderCampaign', back_populates='user', cascade='all, delete-orphan')


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    projects = relationship('Project', back_populates='category')


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum('active', 'paused', name='project_status'), default='active', nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship('User', back_populates='projects')
    category = relationship('Category', back_populates='projects')
    scripts = relationship('Script', back_populates='project', cascade='all, delete-orphan')
    access_logs = relationship('AccessLog', back_populates='project', cascade='all, delete-orphan')


class ScriptWhitelist(Base):
    __tablename__ = 'script_whitelists'

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False, index=True)
    domain_pattern = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    script = relationship('Script', back_populates='whitelists')


class Script(Base):
    __tablename__ = 'scripts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    js_code = Column(Text, nullable=False)
    status = Column(Enum('active', 'disabled', name='script_status'), default='active', nullable=False)
    secondary_script = Column(Text, nullable=True)
    secondary_script_mode = Column(String(20), default='js', nullable=False)
    secondary_script_links = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    project = relationship('Project', back_populates='scripts')
    whitelists = relationship('ScriptWhitelist', back_populates='script', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('project_id', 'slug', name='uq_project_script_slug'),
    )


class AccessLog(Base):
    __tablename__ = 'access_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    script_id = Column(Integer, ForeignKey('scripts.id', ondelete='SET NULL'), nullable=True)
    ref_domain = Column(String(255), nullable=True)
    referer_url = Column(String(2048), nullable=True)  # Full referrer URL (e.g., https://example.com/page.html)
    allowed = Column(Boolean, nullable=False)
    ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    project = relationship('Project', back_populates='access_logs')


class CustomDomain(Base):
    __tablename__ = 'custom_domains'

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), default='pending', nullable=False)  # pending, verified, failed
    is_active = Column(Boolean, default=False, nullable=False)
    platform_ip = Column(String(45), nullable=True)
    resolved_ip = Column(String(45), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class PopunderCampaign(Base):
    __tablename__ = 'popunder_campaigns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum('active', 'paused', name='popunder_status'), default='active', nullable=False)
    settings = Column(JSON, nullable=False, default=dict)
    # Settings JSON structure:
    # {
    #   "popunder_type": "popunder" | "popup",
    #   "url_list": "url1\nurl2\nurl3",  # newline separated URLs
    #   "frequency_cap": 1,  # per user per day
    #   "rt_enable": false,  # referer targeting
    #   "referer_se": false,  # search engine
    #   "referer_sm": false,  # social media
    #   "referer_empty": false,
    #   "referer_not_empty": false,
    #   "floating_banner": "",  # HTML code
    #   "html_body": ""  # HTML to inject in body
    # }
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='popunder_campaigns')

