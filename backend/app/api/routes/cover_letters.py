import re
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, owned_or_404
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import CoverLetter, JobAnalysis, User
from app.schemas.career import CoverLetterGenerate, CoverLetterOut, CoverLetterUpdate
from app.schemas.common import Message
from app.services.ai_features import generate_cover_letter
from app.services.skills.resume_parser import split_sections

router = APIRouter(prefix="/cover-letters", tags=["cover letters"])


@router.post("/generate", status_code=201, dependencies=[Depends(rate_limit("cover", 20, 3600))])
def generate(body: CoverLetterGenerate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = owned_or_404(db.get(JobAnalysis, body.analysis_id), user)
    matched = [i["skill"] for i in a.comparison["items"] if i["status"] != "not_found" and i["category"] != "soft_skill"]
    out = generate_cover_letter(db, user_id=user.id, full_name=user.full_name, job_title=a.job.title, company=a.job.company,
                                resume_text=a.resume.extracted_text, jd_text=a.job.text,
                                sections=split_sections(a.resume.extracted_text), matched_skills=matched, notes=body.notes)
    cl = CoverLetter(user_id=user.id, analysis_id=a.id, title=f"{a.job.title}" + (f" - {a.job.company}" if a.job.company else ""),
                     company=a.job.company, job_title=a.job.title, content=out["content"], source=out["source"], ai_model=out.get("model"))
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return {"letter": CoverLetterOut.model_validate(cl), "label": out["label"]}


@router.get("", response_model=list[CoverLetterOut])
def list_letters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(CoverLetter).where(CoverLetter.user_id == user.id).order_by(CoverLetter.updated_at.desc())).all()


@router.get("/{letter_id}", response_model=CoverLetterOut)
def get_letter(letter_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_or_404(db.get(CoverLetter, letter_id), user)


@router.patch("/{letter_id}", response_model=CoverLetterOut)
def update_letter(letter_id: uuid.UUID, body: CoverLetterUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cl = owned_or_404(db.get(CoverLetter, letter_id), user)
    if body.title is not None:
        cl.title = body.title.strip()
    if body.content is not None and body.content != cl.content:
        cl.content = body.content
        cl.source = "user_edited"
    db.commit()
    return cl


@router.get("/{letter_id}/download")
def download_letter(letter_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cl = owned_or_404(db.get(CoverLetter, letter_id), user)
    fname = re.sub(r"[^A-Za-z0-9_-]+", "-", cl.title)[:60].strip("-") or "cover-letter"
    return Response(cl.content, media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{fname}.txt"'})


@router.delete("/{letter_id}", response_model=Message)
def delete_letter(letter_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cl = owned_or_404(db.get(CoverLetter, letter_id), user)
    db.delete(cl)
    db.commit()
    return Message(message="Cover letter deleted.")
