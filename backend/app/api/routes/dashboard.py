from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import (CoverLetter, JobAnalysis, JobApplication, LearningRoadmap, Resume, ResumeAnalysis, RoadmapItem, User)
from app.models.career import APPLICATION_STATUSES

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every figure here is computed from the user's own persisted rows."""
    uid = user.id
    count = lambda model: db.scalar(select(func.count()).select_from(model).where(model.user_id == uid))  # noqa: E731

    analyses = db.scalars(select(JobAnalysis).where(JobAnalysis.user_id == uid).order_by(JobAnalysis.created_at.desc())).all()
    matched, gaps = Counter(), Counter()
    for a in analyses:
        for i in a.comparison.get("items", []):
            if i["status"] != "not_found":
                matched[i["skill"]] += 1
            elif i["level"] == "required":
                gaps[i["skill"]] += 1

    items = db.execute(select(RoadmapItem.status, func.count()).join(LearningRoadmap, RoadmapItem.roadmap_id == LearningRoadmap.id)
                       .where(LearningRoadmap.user_id == uid).group_by(RoadmapItem.status)).all()
    rm = {s: n for s, n in items}
    rm_total = sum(rm.values())

    app_counts = dict(db.execute(select(JobApplication.status, func.count()).where(JobApplication.user_id == uid).group_by(JobApplication.status)).all())
    today = date.today()
    deadlines = db.scalars(select(JobApplication).where(JobApplication.user_id == uid, JobApplication.deadline >= today,
                                                        JobApplication.deadline <= today + timedelta(days=30),
                                                        JobApplication.status.in_(("SAVED", "APPLIED", "ASSESSMENT")))
                           .order_by(JobApplication.deadline).limit(5)).all()

    recent_resumes = db.scalars(select(Resume).where(Resume.user_id == uid).order_by(Resume.created_at.desc()).limit(3)).all()
    events = ([{"type": "resume", "label": f"Uploaded {r.original_filename}", "at": r.created_at} for r in recent_resumes]
              + [{"type": "analysis", "label": f"Analysed {a.job.title}", "at": a.created_at} for a in analyses[:3]]
              + [{"type": "application", "label": f"Application: {x.job_title} at {x.company}", "at": x.created_at}
                 for x in db.scalars(select(JobApplication).where(JobApplication.user_id == uid).order_by(JobApplication.created_at.desc()).limit(3))])
    events.sort(key=lambda e: e["at"], reverse=True)

    return {
        "counts": {"resumes": count(Resume), "job_analyses": count(JobAnalysis), "cover_letters": count(CoverLetter),
                   "applications": count(JobApplication), "roadmaps": count(LearningRoadmap)},
        "recent_analyses": [{"id": a.id, "job_title": a.job.title, "company": a.job.company, "score": a.score, "created_at": a.created_at} for a in analyses[:5]],
        "top_matched_skills": [{"skill": s, "count": n} for s, n in matched.most_common(8)],
        "important_gaps": [{"skill": s, "count": n} for s, n in gaps.most_common(8)],
        "roadmap_progress": {"total": rm_total, "completed": rm.get("completed", 0), "in_progress": rm.get("in_progress", 0),
                             "percent": round(100 * rm.get("completed", 0) / rm_total) if rm_total else 0},
        "application_status": {s: app_counts.get(s, 0) for s in APPLICATION_STATUSES},
        "upcoming_deadlines": [{"id": a.id, "company": a.company, "job_title": a.job_title, "deadline": a.deadline, "status": a.status} for a in deadlines],
        "recent_activity": events[:8],
    }
