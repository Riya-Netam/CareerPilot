"""Deterministic cover-letter fallback. Uses ONLY facts found in the resume or typed by the user."""
from __future__ import annotations

import re

FALLBACK_LABEL = "Generated from a fixed template (no AI model was used). Review and edit before sending."


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _first_project_lines(projects_block: str, n: int = 2) -> list[str]:
    lines = [re.sub(r"^\s*[-\u2022*\u25cf]\s*", "", l).strip() for l in projects_block.splitlines() if l.strip()]
    names = [l for l in lines if len(l.split()) <= 8 and not l.endswith(".")]
    return names[:n]


def fallback_cover_letter(*, full_name: str, job_title: str, company: str | None, matched_skills: list[str],
                          sections: dict[str, str], user_notes: str | None = None) -> dict:
    company_txt = company or "your company"
    greeting = f"Dear {company} Hiring Team," if company else "Dear Hiring Team,"
    skills = matched_skills[:6]
    edu = next((l.strip() for l in sections.get("education", "").splitlines() if l.strip()), "")
    projects = _first_project_lines(sections.get("projects", ""))

    p1 = f"I am writing to apply for the {job_title} position at {company_txt}."
    if edu:
        p1 += f" My background is: {edu}."
    paras = [p1]
    if skills:
        paras.append(f"The posting asks for skills that appear in my resume, including {_join(skills)}.")
    if projects:
        paras.append(f"My resume describes project work such as {_join(projects)}, where I applied these skills in practice.")
    if user_notes and user_notes.strip():
        paras.append(user_notes.strip())
    paras.append(f"I would welcome the chance to discuss how I can contribute to {company_txt}. Thank you for your time and consideration.")
    body = "\n\n".join([greeting, *paras, f"Sincerely,\n{full_name}"])
    return {"content": body, "source": "fallback_template", "label": FALLBACK_LABEL}
