"""Resume structure parsing (pure Python): sections, skill evidence, quality checks."""
from __future__ import annotations

import re

from .taxonomy import Taxonomy

SECTION_PATTERNS = {
    "summary": r"(?:professional |career )?(?:summary|profile|objective|about me)",
    "education": r"education(?:al)?(?: background| qualifications?)?|academics?",
    "experience": r"(?:work |professional |relevant )?experience|employment(?: history)?|internships?|work history",
    "projects": r"(?:academic |personal |key |major |technical )?projects?",
    "skills": r"(?:technical |core |key )?skills?(?: summary| & tools| and tools)?|technologies|tech stack|competenc(?:y|ies)",
    "certifications": r"certifications?(?: & courses)?|licenses?|courses?|training",
    "achievements": r"achievements?|awards?|honou?rs|accomplishments?|extracurricular(?:s| activities)?|positions of responsibility",
}
_SECTION_RE = {k: re.compile(rf"^\s*(?:{v})\s*:?\s*$", re.I) for k, v in SECTION_PATTERNS.items()}
EXPECTED_SECTIONS = ["education", "skills", "projects", "experience"]
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
METRIC_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|x|k\b|\+|users|ms|seconds|hours|students|requests|records|rows)|\b\d{2,}\b")
BULLET_RE = re.compile(r"^\s*[-\u2022*\u25cf\u25aa\u00b7>]\s+")
WEAK_STARTERS = ("responsible for", "worked on", "helped with", "involved in", "assisted in", "duties included")


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        stripped = line.strip()
        hit = None
        if stripped and len(stripped) <= 45:
            for name, rx in _SECTION_RE.items():
                if rx.match(stripped.rstrip(":")):
                    hit = name
                    break
        if hit:
            current = hit
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _sentences(block: str) -> list[str]:
    parts: list[str] = []
    for line in block.splitlines():
        line = BULLET_RE.sub("", line).strip()
        if not line:
            continue
        parts.extend(p.strip() for p in re.split(r"(?<=[.!?])\s+", line) if p.strip())
    return parts


def skill_evidence(sections: dict[str, str], taxonomy: Taxonomy) -> dict[str, list[dict]]:
    """canonical skill -> [{section, snippet}] (max 3 snippets per skill)."""
    ev: dict[str, list[dict]] = {}
    for sec, block in sections.items():
        if sec == "header":
            continue
        for sent in _sentences(block) or [block]:
            for skill in taxonomy.skills_in(sent):
                items = ev.setdefault(skill, [])
                if len(items) < 3 and not any(i["snippet"] == sent[:220] for i in items):
                    items.append({"section": sec, "snippet": sent[:220]})
    return ev


def evidence_for_term(sections: dict[str, str], term: str, taxonomy: Taxonomy) -> list[dict]:
    """Evidence for a skill name that may not be in the taxonomy (user-added)."""
    sk = taxonomy.get(term)
    if sk:
        return skill_evidence(sections, taxonomy).get(term, [])
    needle = re.compile(rf"(?<![A-Za-z0-9+#]){re.escape(term.strip())}(?![A-Za-z0-9+#])", re.I)
    out: list[dict] = []
    for sec, block in sections.items():
        for sent in _sentences(block) or [block]:
            if needle.search(sent) and len(out) < 3:
                out.append({"section": sec, "snippet": sent[:220]})
    return out


def parse_resume(text: str, taxonomy: Taxonomy) -> dict:
    sections = split_sections(text)
    words = re.findall(r"\b\w+\b", text)
    lines = [l for l in text.splitlines() if l.strip()]
    bullets = [l for l in lines if BULLET_RE.match(l)]
    evidence = skill_evidence(sections, taxonomy)

    warnings: list[str] = []
    for sec in EXPECTED_SECTIONS:
        if sec not in sections:
            warnings.append(f"No '{sec}' section was detected. If you have one, check that its heading is on its own line.")
    if not EMAIL_RE.search(text):
        warnings.append("No email address was detected.")
    if not PHONE_RE.search(text):
        warnings.append("No phone number was detected.")
    if len(words) < 150:
        warnings.append("The resume is very short (under 150 words); add detail about projects and skills.")
    if len(words) > 1400:
        warnings.append("The resume is long (over 1,400 words); consider trimming it for readability.")
    if bullets and not any(METRIC_RE.search(b) for b in bullets):
        warnings.append("No numbers or measurable results were found in bullet points. Add real figures only where they are true.")

    suggestions: list[dict] = []
    for b in bullets:
        low = BULLET_RE.sub("", b).strip().lower()
        if low.startswith(WEAK_STARTERS):
            suggestions.append({"kind": "weak_opening", "text": BULLET_RE.sub("", b).strip()[:200],
                                "advice": "Start with a specific action verb and say what you built or changed. Do not add facts that are not true."})
        if len(suggestions) >= 6:
            break
    proj = sections.get("projects", "")
    if proj and not any(METRIC_RE.search(l) for l in proj.splitlines()):
        suggestions.append({"kind": "project_detail", "text": "Projects section",
                            "advice": "Describe each project with the tools you used, what you built, and a real result (users, accuracy, speed) if you have one."})

    sentences = _sentences(text)
    avg_len = round(sum(len(s.split()) for s in sentences) / len(sentences), 1) if sentences else 0
    return {
        "sections_found": [k for k in sections if k != "header"],
        "sections": sections,
        "education": [l.strip() for l in sections.get("education", "").splitlines() if l.strip()][:8],
        "certifications": [BULLET_RE.sub("", l).strip() for l in sections.get("certifications", "").splitlines() if l.strip()][:10],
        "skills_detected": {k: v for k, v in sorted(evidence.items())},
        "stats": {"word_count": len(words), "bullet_count": len(bullets), "avg_sentence_words": avg_len,
                  "has_email": bool(EMAIL_RE.search(text)), "has_phone": bool(PHONE_RE.search(text))},
        "warnings": warnings,
        "suggestions": suggestions,
    }
