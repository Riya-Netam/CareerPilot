"""Admin API. Every route requires ADMIN/SUPER_ADMIN on the backend.

Privacy: user lists and details expose account metadata and aggregate counts only. No resumes,
cover letters, job text, notes or tokens are ever returned by these routes.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.ai.provider import get_provider
from app.core.config import INSECURE_KEYS, get_settings
from app.core.deps import api_error, require_admin
from app.core.security import utcnow
from app.db.session import get_db
from app.models import (AIUsageRecord, AuditLog, CoverLetter, ErrorEvent, JobAnalysis, JobApplication, Resume, SkillAlias,
                        SkillTaxonomyEntry, User, UserSession)
from app.schemas.common import Message, Page
from app.services.audit import audit
from app.services.skills.taxonomy import CATEGORY_LABELS, normalize_text
from app.services.storage import get_storage
from app.services.taxonomy_store import reload_taxonomy

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _user_row(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
            "email_verified": u.email_verified_at is not None, "created_at": u.created_at, "last_login_at": u.last_login_at}


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    n = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where))  # noqa: E731
    since = utcnow() - timedelta(days=7)
    day = utcnow() - timedelta(days=1)
    return {
        "users": {"total": n(User), "active": n(User, User.is_active.is_(True)), "verified": n(User, User.email_verified_at.is_not(None)),
                  "new_last_7_days": n(User, User.created_at >= since)},
        "usage": {"resumes": n(Resume), "job_analyses": n(JobAnalysis), "cover_letters": n(CoverLetter), "applications": n(JobApplication)},
        "ai": {"requests_total": n(AIUsageRecord), "failures_total": n(AIUsageRecord, AIUsageRecord.success.is_(False)),
               "requests_last_24h": n(AIUsageRecord, AIUsageRecord.created_at >= day),
               "failures_last_24h": n(AIUsageRecord, AIUsageRecord.created_at >= day, AIUsageRecord.success.is_(False))},
        "errors_last_24h": n(ErrorEvent, ErrorEvent.created_at >= day),
    }


@router.get("/users", response_model=Page[dict])
def list_users(q: str | None = Query(None, max_length=100), role: str | None = None, active: bool | None = None,
               page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(User)
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(User.email.ilike(like) | User.full_name.ilike(like))
    if role:
        stmt = stmt.where(User.role == role)
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[_user_row(u) for u in rows], total=total, page=page, page_size=page_size)


@router.get("/users/{user_id}")
def user_detail(user_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise api_error(404, "not_found", "Not found.")
    c = lambda model: db.scalar(select(func.count()).select_from(model).where(model.user_id == u.id))  # noqa: E731
    audit(db, admin.id, "admin.view_user", "user", u.id)
    db.commit()
    return {**_user_row(u), "counts": {"resumes": c(Resume), "job_analyses": c(JobAnalysis), "cover_letters": c(CoverLetter),
                                         "applications": c(JobApplication)}}


def _set_active(db: Session, admin: User, user_id: uuid.UUID, active: bool) -> dict:
    u = db.get(User, user_id)
    if not u:
        raise api_error(404, "not_found", "Not found.")
    if u.id == admin.id:
        raise api_error(400, "self_action", "You cannot change your own account status.")
    if u.role == "SUPER_ADMIN" or (u.role == "ADMIN" and admin.role != "SUPER_ADMIN"):
        raise api_error(403, "forbidden", "You do not have permission to change this account.")
    u.is_active = active
    if not active:  # force sign-out everywhere
        db.execute(update(UserSession).where(UserSession.user_id == u.id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    audit(db, admin.id, "admin.reactivate_user" if active else "admin.disable_user", "user", u.id)
    db.commit()
    return _user_row(u)


@router.post("/users/{user_id}/disable")
def disable_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _set_active(db, admin, user_id, False)


@router.post("/users/{user_id}/reactivate")
def reactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _set_active(db, admin, user_id, True)


@router.get("/audit-logs", response_model=Page[dict])
def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), action: str | None = None,
               db: Session = Depends(get_db)):
    stmt = select(AuditLog, User.email).outerjoin(User, AuditLog.actor_id == User.id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(select(AuditLog.id).where(*( [AuditLog.action == action] if action else [])).subquery()))
    rows = db.execute(stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items = [{"id": a.id, "actor": email, "action": a.action, "target_type": a.target_type, "target_id": a.target_id,
              "created_at": a.created_at} for a, email in rows]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/ai")
def ai_status(db: Session = Depends(get_db)):
    p = get_provider()
    available, detail = (p.is_available() if p else (False, "AI is disabled (AI_ENABLED=false)"))
    recent = db.scalars(select(AIUsageRecord).order_by(AIUsageRecord.created_at.desc()).limit(20)).all()
    return {"provider": p.name if p else None, "model": p.model if p else None, "available": available, "detail": detail,
            "recent": [{"feature": r.feature, "success": r.success, "error": r.error, "duration_ms": r.duration_ms,
                        "created_at": r.created_at} for r in recent],
            "note": "When the model is unavailable, resume parsing, skill matching, scoring, roadmaps and template cover letters still work."}


@router.get("/errors", response_model=Page[dict])
def errors(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(ErrorEvent))
    rows = db.scalars(select(ErrorEvent).order_by(ErrorEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[{"id": e.id, "request_id": e.request_id, "method": e.method, "path": e.path, "error_type": e.error_type,
                        "created_at": e.created_at} for e in rows], total=total, page=page, page_size=page_size)


@router.get("/health")
def health_detail(db: Session = Depends(get_db)):
    s = get_settings()
    try:
        db.execute(text("SELECT 1")); db_ok = True
    except Exception:
        db_ok = False
    p = get_provider()
    ai_ok, ai_detail = (p.is_available() if p else (False, "disabled"))
    return {
        "database": {"ok": db_ok}, "storage": {"ok": get_storage().writable(), "retains_original_files": s.STORE_ORIGINAL_FILES},
        "ai": {"ok": ai_ok, "detail": ai_detail},
        # Booleans only. Secret values are never returned.
        "config_checks": {
            "environment": s.ENVIRONMENT,
            "secret_key_is_strong": s.SECRET_KEY not in INSECURE_KEYS and len(s.SECRET_KEY) >= 32,
            "cookie_secure": s.COOKIE_SECURE, "email_mode": s.EMAIL_MODE,
            "smtp_configured": bool(s.SMTP_HOST), "cors_origins_set": bool(s.cors_origins_list),
            "rate_limiting_enabled": s.RATE_LIMIT_ENABLED, "api_docs_exposed": s.is_dev,
        },
    }


class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str
    aliases: list[str] = Field(default_factory=list, max_length=20)
    resource_url: str | None = Field(default=None, max_length=300, pattern=r"^https://")


@router.get("/taxonomy")
def taxonomy_list(q: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(SkillTaxonomyEntry)
    if q:
        stmt = stmt.where(SkillTaxonomyEntry.name.ilike(f"%{q.strip()}%"))
    if category:
        stmt = stmt.where(SkillTaxonomyEntry.category == category)
    rows = db.scalars(stmt.order_by(SkillTaxonomyEntry.category, SkillTaxonomyEntry.name).limit(300)).all()
    return {"categories": CATEGORY_LABELS,
            "items": [{"id": r.id, "name": r.name, "category": r.category, "aliases": [a.alias for a in r.aliases],
                       "is_custom": r.is_custom} for r in rows]}


@router.post("/taxonomy", status_code=201)
def taxonomy_add(body: SkillIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if body.category not in CATEGORY_LABELS:
        raise api_error(422, "validation_error", "Unknown category.")
    if db.scalar(select(SkillTaxonomyEntry).where(func.lower(SkillTaxonomyEntry.name) == body.name.strip().lower())):
        raise api_error(409, "exists", "A skill with this name already exists.")
    entry = SkillTaxonomyEntry(name=body.name.strip(), category=body.category, resource_url=body.resource_url, is_custom=True,
                               prerequisites=[])
    taken = set(db.scalars(select(SkillAlias.alias)))
    for a in {normalize_text(x) for x in body.aliases + [body.name]} - taken:
        if a:
            entry.aliases.append(SkillAlias(alias=a))
    db.add(entry)
    audit(db, admin.id, "admin.add_skill", "skill", body.name.strip())
    db.commit()
    reload_taxonomy(db)
    return {"id": entry.id, "name": entry.name}
