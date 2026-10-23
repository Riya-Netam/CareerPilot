import csv
import io
import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import api_error, get_current_user, owned_or_404
from app.db.session import get_db
from app.models import JobAnalysis, JobApplication, User
from app.models.career import APPLICATION_STATUSES
from app.schemas.career import ApplicationIn, ApplicationOut, ApplicationUpdate
from app.schemas.common import Message, Page

router = APIRouter(prefix="/applications", tags=["applications"])
SORTS = {"created": JobApplication.created_at, "deadline": JobApplication.deadline, "company": JobApplication.company,
         "applied": JobApplication.applied_on, "status": JobApplication.status}


def _check_analysis(db: Session, analysis_id, user: User):
    if analysis_id is not None:
        owned_or_404(db.get(JobAnalysis, analysis_id), user)


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # block spreadsheet formula injection


def _dump(data) -> dict:
    d = data.model_dump(exclude_unset=True)
    if "job_url" in d and d["job_url"] is not None:
        d["job_url"] = str(d["job_url"])
    return d


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(body: ApplicationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_analysis(db, body.analysis_id, user)
    app = JobApplication(user_id=user.id, **{**_dump(body)})
    db.add(app)
    db.commit()
    return app


@router.get("", response_model=Page[ApplicationOut])
def list_applications(q: str | None = Query(None, max_length=100), status: str | None = None,
                      sort: Literal["created", "deadline", "company", "applied", "status"] = "created",
                      order: Literal["asc", "desc"] = "desc", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if status and status not in APPLICATION_STATUSES:
        raise api_error(422, "validation_error", "Unknown status.")
    stmt = select(JobApplication).where(JobApplication.user_id == user.id)
    if status:
        stmt = stmt.where(JobApplication.status == status)
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(JobApplication.company.ilike(like), JobApplication.job_title.ilike(like), JobApplication.notes.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    col = SORTS[sort]
    stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), JobApplication.id)
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[ApplicationOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(JobApplication.status, func.count()).where(JobApplication.user_id == user.id)
                             .group_by(JobApplication.status)).all())
    today = date.today()
    upcoming = db.scalars(select(JobApplication).where(
        JobApplication.user_id == user.id, JobApplication.deadline >= today, JobApplication.deadline <= today + timedelta(days=30),
        JobApplication.status.in_(("SAVED", "APPLIED", "ASSESSMENT"))).order_by(JobApplication.deadline).limit(10)).all()
    return {"total": sum(counts.values()), "by_status": {s: counts.get(s, 0) for s in APPLICATION_STATUSES},
            "upcoming_deadlines": [ApplicationOut.model_validate(a) for a in upcoming]}


@router.get("/export.csv")
def export_csv(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["company", "job_title", "status", "applied_on", "deadline", "job_url", "notes"])
    for a in db.scalars(select(JobApplication).where(JobApplication.user_id == user.id).order_by(JobApplication.created_at)):
        w.writerow([_csv_safe(x) for x in (a.company, a.job_title, a.status, a.applied_on, a.deadline, a.job_url, a.notes)])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="applications.csv"'})


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_or_404(db.get(JobApplication, app_id), user)


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: uuid.UUID, body: ApplicationUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = owned_or_404(db.get(JobApplication, app_id), user)
    data = _dump(body)
    if "analysis_id" in data:
        _check_analysis(db, data["analysis_id"], user)
    for k, v in data.items():
        if k in ("company", "job_title") and v is None:
            continue
        setattr(app, k, v)
    db.commit()
    return app


@router.delete("/{app_id}", response_model=Message)
def delete_application(app_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(owned_or_404(db.get(JobApplication, app_id), user))
    db.commit()
    return Message(message="Application deleted.")
