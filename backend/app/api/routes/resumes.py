import re
import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import api_error, get_current_user, owned_or_404
from app.core.ratelimit import rate_limit
from app.core.security import utcnow
from app.db.session import get_db
from app.models import JobAnalysis, Resume, ResumeAnalysis, User
from app.schemas.career import ResumeDetail, ResumeOut
from app.schemas.common import Message, Page
from app.services.ai_features import ai_resume_suggestions
from app.ai.provider import AIUnavailable
from app.services.document_text import DocumentError, ScannedDocumentError, extract_text
from app.services.skills.resume_parser import parse_resume
from app.services.storage import get_storage
from app.services.taxonomy_store import get_taxonomy

router = APIRouter(prefix="/resumes", tags=["resumes"])
MAX_RESUMES_PER_USER = 20


def _clean_name(name: str | None) -> str:
    base = (name or "resume").replace("\\", "/").split("/")[-1]
    return re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:120] or "resume"


def _public_analysis(result: dict) -> dict:
    """Drop the raw section text from API responses; keep extracted facts and checks."""
    return {k: v for k, v in result.items() if k != "sections"}


def _detail(resume: Resume) -> ResumeDetail:
    latest = resume.analyses[0] if resume.analyses else None
    d = ResumeDetail.model_validate(resume)
    d.analysis = _public_analysis(latest.result) if latest else None
    d.ai_suggestions = latest.ai_suggestions if latest else None
    return d


@router.post("", response_model=ResumeDetail, status_code=201, dependencies=[Depends(rate_limit("upload", 20, 3600))])
async def upload_resume(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    count = db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user.id))
    if count >= MAX_RESUMES_PER_USER:
        raise api_error(400, "limit_reached", f"You can keep up to {MAX_RESUMES_PER_USER} resumes. Delete one to upload another.")
    data = await file.read(s.max_upload_bytes + 1)  # never read more than the limit + 1 byte
    try:
        text, kind = extract_text(data, s.max_upload_bytes)
    except ScannedDocumentError as e:
        raise api_error(422, "scanned_document", str(e))
    except DocumentError as e:
        raise api_error(422, "invalid_document", str(e))
    stored = get_storage().save(user.id, data, kind) if s.STORE_ORIGINAL_FILES else None
    parsed = parse_resume(text, get_taxonomy())
    resume = Resume(user_id=user.id, original_filename=_clean_name(file.filename), stored_name=stored, file_type=kind,
                    size_bytes=len(data), extracted_text=text)
    db.add(resume)
    db.flush()
    db.add(ResumeAnalysis(resume_id=resume.id, user_id=user.id, result=parsed, created_at=utcnow()))
    db.commit()
    db.refresh(resume)
    return _detail(resume)


@router.get("", response_model=Page[ResumeOut])
def list_resumes(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Resume).where(Resume.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Resume.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[ResumeOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(owned_or_404(db.get(Resume, resume_id), user))


@router.get("/{resume_id}/download")
def download_resume(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = owned_or_404(db.get(Resume, resume_id), user)
    if not r.stored_name:
        raise api_error(404, "file_not_stored", "The original file was not kept. Only the extracted text is stored.")
    try:
        data = get_storage().read(user.id, r.stored_name)
    except (FileNotFoundError, ValueError):
        raise api_error(404, "file_missing", "The stored file could not be found.")
    mime = "application/pdf" if r.file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{_clean_name(r.original_filename)}"'})


@router.post("/{resume_id}/ai-suggestions", response_model=ResumeDetail, dependencies=[Depends(rate_limit("ai", 20, 3600))])
def generate_ai_suggestions(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = owned_or_404(db.get(Resume, resume_id), user)
    try:
        suggestions = ai_resume_suggestions(db, user_id=user.id, resume_text=r.extracted_text, jd_text=None)
    except AIUnavailable as e:
        raise api_error(503, "ai_unavailable", f"AI suggestions are unavailable right now ({e}). The rule-based checks above still apply.")
    r.analyses[0].ai_suggestions = suggestions
    db.commit()
    return _detail(r)


@router.get("/{resume_id}/report")
def resume_report(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = owned_or_404(db.get(Resume, resume_id), user)
    a = r.analyses[0].result
    lines = [f"# Resume analysis: {r.original_filename}", "", "_Rule-based checks. Not a guarantee of any hiring outcome._", "",
             f"Sections detected: {', '.join(a['sections_found']) or 'none'}", "", "## Warnings"]
    lines += [f"- {w}" for w in a["warnings"]] or ["- None"]
    lines += ["", "## Skills detected (with where they appear)"]
    for skill, ev in a["skills_detected"].items():
        lines.append(f"- {skill}: " + ", ".join(sorted({e['section'] for e in ev})))
    lines += ["", "## Suggestions"] + ([f"- {s['advice']}" for s in a["suggestions"]] or ["- None"])
    return Response("\n".join(lines), media_type="text/markdown",
                    headers={"Content-Disposition": 'attachment; filename="resume-analysis.md"'})


@router.delete("/{resume_id}", response_model=Message)
def delete_resume(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = owned_or_404(db.get(Resume, resume_id), user)
    in_use = db.scalar(select(func.count()).select_from(JobAnalysis).where(JobAnalysis.resume_id == r.id))
    if r.stored_name:
        get_storage().delete(user.id, r.stored_name)
    db.delete(r)  # cascades to its analyses and job analyses
    db.commit()
    return Message(message="Resume deleted." + (f" {in_use} related job analysis(es) were deleted with it." if in_use else ""))
