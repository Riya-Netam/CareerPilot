import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import api_error, get_current_user, owned_or_404
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import JobAnalysis, JobDescription, Resume, User
from app.schemas.career import (AnalysisCreate, AnalysisDetail, AnalysisSummary, ExtractIn, RequirementIn,
                                RequirementsUpdate)
from app.schemas.common import Message, Page
from app.services.skills.comparison import compare
from app.services.skills.jd_parser import analyze_job_description
from app.services.skills.resume_parser import split_sections
from app.services.taxonomy_store import get_taxonomy

router = APIRouter(prefix="/job-analyses", tags=["job analysis"])


def _reqs_from_input(items: list[RequirementIn]) -> list[dict]:
    """User-corrected list -> internal requirement dicts (canonical names where known)."""
    tax = get_taxonomy()
    out, seen = [], set()
    for r in items:
        name = tax.resolve(r.skill)
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        sk = tax.get(name)
        out.append({"skill": name, "category": sk.category if sk else "other", "level": r.level, "confidence": "high",
                    "reason": "Set or confirmed by you", "evidence": ""})
    return out


def _summary(a: JobAnalysis) -> dict:
    return {"id": a.id, "job_title": a.job.title, "company": a.job.company, "resume_id": a.resume_id,
            "resume_filename": a.resume.original_filename, "score": a.score, "user_adjusted": a.user_adjusted,
            "created_at": a.created_at}


def _detail(a: JobAnalysis) -> AnalysisDetail:
    return AnalysisDetail(**_summary(a), location=a.job.location, experience_level=a.job.experience_level,
                          extracted=a.extracted, requirements=a.requirements, comparison=a.comparison)


@router.post("/extract", dependencies=[Depends(get_current_user), Depends(rate_limit("extract", 60, 3600))])
def extract_only(body: ExtractIn):
    """Step 1: analyse the job description on its own (nothing is saved) so the user can review it."""
    return analyze_job_description(body.description, get_taxonomy())


@router.post("", response_model=AnalysisDetail, status_code=201, dependencies=[Depends(rate_limit("analyse", 60, 3600))])
def create_analysis(body: AnalysisCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = owned_or_404(db.get(Resume, body.resume_id), user)
    tax = get_taxonomy()
    extracted = analyze_job_description(body.description, tax)
    adjusted = body.requirements is not None
    reqs = _reqs_from_input(body.requirements) if adjusted else extracted["requirements"]
    job = JobDescription(user_id=user.id, title=body.title, company=body.company, location=body.location,
                         experience_level=body.experience_level, text=body.description)
    db.add(job)
    db.flush()
    comparison = compare(reqs, split_sections(resume.extracted_text), tax, extracted["qualifications"])
    a = JobAnalysis(user_id=user.id, job_id=job.id, resume_id=resume.id, extracted=extracted, requirements=reqs,
                    comparison=comparison, score=comparison["score"], user_adjusted=adjusted)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _detail(a)


@router.get("", response_model=Page[AnalysisSummary])
def list_analyses(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(JobAnalysis).where(JobAnalysis.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(JobAnalysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[AnalysisSummary(**_summary(a)) for a in rows], total=total, page=page, page_size=page_size)


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(owned_or_404(db.get(JobAnalysis, analysis_id), user))


@router.patch("/{analysis_id}/requirements", response_model=AnalysisDetail)
def update_requirements(analysis_id: uuid.UUID, body: RequirementsUpdate, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Let the user correct extracted requirements; the comparison and score are recalculated."""
    a = owned_or_404(db.get(JobAnalysis, analysis_id), user)
    reqs = _reqs_from_input(body.requirements)
    a.requirements = reqs
    a.comparison = compare(reqs, split_sections(a.resume.extracted_text), get_taxonomy(), a.extracted.get("qualifications"))
    a.score = a.comparison["score"]
    a.user_adjusted = True
    db.commit()
    db.refresh(a)
    return _detail(a)


@router.get("/{analysis_id}/report")
def analysis_report(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = owned_or_404(db.get(JobAnalysis, analysis_id), user)
    c = a.comparison
    lines = [f"# Job skill analysis: {a.job.title}" + (f" at {a.job.company}" if a.job.company else ""), "",
             f"Resume: {a.resume.original_filename}", f"Alignment score: {c['score']}" if c["score"] is not None else "Alignment score: not available",
             "", f"_{c['score_explanation']['disclaimer']}_", "", "## Skills and evidence"]
    for i in c["items"]:
        lines.append(f"- [{i['level']}] {i['skill']}: {i['status'].replace('_', ' ')}")
    lines += ["", "## Priorities"] + [f"- ({p['priority']}) {p['skill']}: {p['why']}" for p in c["priorities"]]
    lines += ["", "## Please confirm manually"] + [f"- {m['note']}" for m in c["manual_confirmation"]]
    return Response("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="job-analysis.md"'})


@router.delete("/{analysis_id}", response_model=Message)
def delete_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = owned_or_404(db.get(JobAnalysis, analysis_id), user)
    job = a.job
    db.delete(a)
    db.flush()
    db.delete(job)
    db.commit()
    return Message(message="Analysis deleted.")
