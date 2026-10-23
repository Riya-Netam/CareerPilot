"""AI-assisted features with validation and deterministic fallbacks. Every call is recorded in
ai_usage_records so admins can see availability and failures (no prompt or document content stored)."""
from __future__ import annotations

import re
import time
import uuid

from sqlalchemy.orm import Session

from app.ai.prompts import SYSTEM_GUARD, cover_letter_prompt, resume_suggestions_prompt
from app.ai.provider import AIUnavailable, get_provider, parse_json_object
from app.models import AIUsageRecord
from app.services.cover_letter import fallback_cover_letter

_NUM = re.compile(r"\d[\d,.]*\s*%?")
_BAD = re.compile(r"ignore (all |previous |the )|system prompt|as an ai|\[(your|insert)", re.I)


def _record(db: Session, user_id, feature: str, provider, ok: bool, started: float, error: str | None = None):
    db.add(AIUsageRecord(user_id=user_id, feature=feature, provider=provider.name if provider else "none",
                         model=provider.model if provider else "-", success=ok, error=(error or None) and error[:290],
                         duration_ms=int((time.monotonic() - started) * 1000)))
    db.commit()


def _numbers(text: str) -> set[str]:
    return {m.group(0).strip().rstrip(".,") for m in _NUM.finditer(text) if len(re.sub(r"\D", "", m.group(0))) >= 2}


def validate_cover_letter(output: str, allowed_text: str) -> str:
    """Reject output that is too short/long, looks like leaked instructions, or contains figures not in the inputs."""
    text = re.sub(r"^```\w*|```$", "", output.strip(), flags=re.M).strip()
    if not (400 <= len(text) <= 3500):
        raise AIUnavailable("Generated letter had an unexpected length")
    if _BAD.search(text):
        raise AIUnavailable("Generated letter failed safety checks")
    invented = _numbers(text) - _numbers(allowed_text)
    if invented:
        raise AIUnavailable("Generated letter contained figures not found in your resume")
    return text


def generate_cover_letter(db: Session, *, user_id: uuid.UUID, full_name: str, job_title: str, company: str | None,
                          resume_text: str, jd_text: str, sections: dict, matched_skills: list[str],
                          notes: str | None) -> dict:
    provider = get_provider()
    if provider:
        started = time.monotonic()
        try:
            ok, detail = provider.is_available()
            if not ok:
                raise AIUnavailable(detail)
            raw = provider.generate(SYSTEM_GUARD, cover_letter_prompt(resume_text, jd_text, job_title, company, full_name, notes), max_tokens=700)
            text = validate_cover_letter(raw, resume_text + "\n" + (notes or "") + "\n" + jd_text)
            _record(db, user_id, "cover_letter", provider, True, started)
            return {"content": text, "source": "ai", "label": f"Drafted by a local AI model ({provider.model}). Check every statement is true before using it.", "model": provider.model}
        except AIUnavailable as e:
            _record(db, user_id, "cover_letter", provider, False, started, str(e))
    out = fallback_cover_letter(full_name=full_name, job_title=job_title, company=company, matched_skills=matched_skills,
                                sections=sections, user_notes=notes)
    out["model"] = None
    return out


def ai_resume_suggestions(db: Session, *, user_id: uuid.UUID, resume_text: str, jd_text: str | None) -> list[dict]:
    provider = get_provider()
    if not provider:
        raise AIUnavailable("AI is disabled on this server")
    started = time.monotonic()
    try:
        ok, detail = provider.is_available()
        if not ok:
            raise AIUnavailable(detail)
        data = parse_json_object(provider.generate(SYSTEM_GUARD, resume_suggestions_prompt(resume_text, jd_text), json_mode=True, max_tokens=700))
        clean: list[dict] = []
        for s in data.get("suggestions", [])[:5]:
            if isinstance(s, dict) and isinstance(s.get("original"), str) and isinstance(s.get("advice"), str):
                # Keep only suggestions that quote a real line from the resume
                if s["original"].strip() and s["original"].strip()[:60] in resume_text and not _BAD.search(s["advice"]):
                    clean.append({"original": s["original"][:300], "advice": s["advice"][:400], "source": "ai", "model": provider.model})
        _record(db, user_id, "resume_suggestions", provider, True, started)
        return clean
    except AIUnavailable as e:
        _record(db, user_id, "resume_suggestions", provider, False, started, str(e))
        raise
