"""Job description analysis: required vs preferred skills, qualifications, experience.

Everything here is deterministic and explainable. Each extracted skill carries the
reason it was classified (a sentence cue or a section heading). When neither is
present the level is "uncertain" instead of being guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .taxonomy import Taxonomy

REQUIRED_SECTION = re.compile(
    r"^(?:key |minimum |basic |essential |mandatory |required |technical )?"
    r"(?:requirements?|qualifications?|must[- ]haves?|what you(?:'|\u2019)?ll need|what we(?:'|\u2019)?re looking for|"
    r"who you are|skills? required|required skills?|you have|you bring|your profile|skills(?: and experience)?)\b",
    re.I,
)
PREFERRED_SECTION = re.compile(
    r"^(?:preferred|nice[- ]to[- ]haves?|bonus|good to have|desirable|a plus|plus points?|optional|"
    r"additional (?:skills|qualifications)|extra credit)\b",
    re.I,
)
RESPONSIBILITY_SECTION = re.compile(
    r"^(?:key )?(?:responsibilit|what you(?:'|\u2019)?ll do|duties|the role|about the role|role overview|your role|day[- ]to[- ]day)",
    re.I,
)
NEUTRAL_SECTION = re.compile(
    r"^(?:about|who we are|our company|company|benefits|perks|what we offer|why join|compensation|equal opportunity)", re.I
)

PREFERRED_CUES = re.compile(
    r"\b(preferred|nice to have|nice-to-have|a plus|is a plus|are a plus|bonus|ideally|desirable|an advantage|"
    r"good to have|familiarity with|exposure to|would be great|beneficial|not required|optional)\b",
    re.I,
)
REQUIRED_CUES = re.compile(
    r"\b(must|required|requires?|mandatory|proficien\w*|strong|solid|expert\w*|hands[- ]on|minimum|at least|"
    r"essential|you have|you will have|need to|should have|deep understanding|working knowledge)\b",
    re.I,
)
DEGREE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|b\.?\s?sc|bachelor(?:'s)?|master(?:'s)?|m\.?\s?tech|m\.?\s?sc|mba|ph\.?\s?d|doctorate|"
    r"computer science|engineering degree|degree in)\b",
    re.I,
)
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|-|to|\u2013)?\s*(\d{1,2})?\s*\+?\s*years?", re.I)
EXPERIENCE_LEVELS = re.compile(r"\b(intern(?:ship)?|fresher|entry[- ]level|junior|associate|mid[- ]level|senior|lead|principal|staff)\b", re.I)


@dataclass
class Requirement:
    skill: str
    category: str
    level: str  # "required" | "preferred" | "uncertain"
    confidence: str  # "high" | "low"
    reason: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


def _split_units(text: str) -> list[tuple[str, str]]:
    """Return (section_kind, sentence) pairs. section_kind in required/preferred/responsibility/neutral/none."""
    section = "none"
    units: list[tuple[str, str]] = []
    for raw in re.split(r"\r?\n", text):
        line = raw.strip(" \t-\u2022*\u00b7\u25cf\u25aa>")
        if not line:
            continue
        header = line.rstrip(":").strip()
        is_header = len(header) <= 60 and (line.endswith(":") or (raw == raw.strip() and not re.search(r"[.;,]$", line) and len(header.split()) <= 6 and not raw.lstrip().startswith(("-", "\u2022", "*"))))
        if is_header:
            if PREFERRED_SECTION.match(header):
                section = "preferred"; continue
            if REQUIRED_SECTION.match(header):
                section = "required"; continue
            if RESPONSIBILITY_SECTION.match(header):
                section = "responsibility"; continue
            if NEUTRAL_SECTION.match(header):
                section = "neutral"; continue
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line):
            sent = sent.strip()
            if sent:
                units.append((section, sent))
    return units


def extract_requirements(text: str, taxonomy: Taxonomy) -> list[Requirement]:
    found: dict[str, Requirement] = {}
    rank = {"required": 3, "preferred": 2, "uncertain": 1}
    for section, sent in _split_units(text):
        skills = taxonomy.skills_in(sent)
        if not skills:
            continue
        if PREFERRED_CUES.search(sent):
            level, conf = "preferred", "high"
            cue = PREFERRED_CUES.search(sent).group(0)
            reason = f'Sentence contains "{cue.lower()}"'
        elif REQUIRED_CUES.search(sent):
            level, conf = "required", "high"
            cue = REQUIRED_CUES.search(sent).group(0)
            reason = f'Sentence contains "{cue.lower()}"'
        elif section == "required":
            level, conf, reason = "required", "high", "Listed under a requirements section"
        elif section == "preferred":
            level, conf, reason = "preferred", "high", "Listed under a preferred / nice-to-have section"
        elif section == "responsibility":
            level, conf, reason = "uncertain", "low", "Mentioned in responsibilities; not clearly required or preferred"
        else:
            level, conf, reason = "uncertain", "low", "No wording or section that shows whether it is required"
        for name in skills:
            sk = taxonomy.get(name)
            cand = Requirement(name, sk.category if sk else "other", level, conf, reason, sent[:240])
            cur = found.get(name)
            if cur is None or rank[cand.level] > rank[cur.level]:
                found[name] = cand
    return sorted(found.values(), key=lambda r: (-rank[r.level], r.category, r.skill))


def extract_qualifications(text: str) -> list[dict]:
    """Degrees, years of experience and seniority hints. These always need manual confirmation."""
    out: list[dict] = []
    seen: set[str] = set()
    for _, sent in _split_units(text):
        s = sent[:240]
        if DEGREE.search(sent) and re.search(r"\b(degree|bachelor|master|b\.?tech|m\.?tech|b\.?e|ph\.?d|mba|b\.?sc|m\.?sc|computer science)\b", sent, re.I):
            if s not in seen:
                out.append({"type": "education", "text": s}); seen.add(s)
        m = YEARS.search(sent)
        if m and re.search(r"experience|working|industry|professional", sent, re.I) and s not in seen:
            years = f"{m.group(1)}" + (f"-{m.group(2)}" if m.group(2) else "") + " years"
            out.append({"type": "experience", "text": s, "years": years}); seen.add(s)
        lv = EXPERIENCE_LEVELS.search(sent)
        if lv and re.search(r"\b(role|position|looking for|seeking|candidates?)\b", sent, re.I) and s not in seen:
            out.append({"type": "seniority", "text": s, "level": lv.group(1).lower()}); seen.add(s)
    return out


def extract_responsibilities(text: str, limit: int = 8) -> list[str]:
    out = [s for sec, s in _split_units(text) if sec == "responsibility" and 15 <= len(s) <= 240]
    return out[:limit]


def analyze_job_description(text: str, taxonomy: Taxonomy) -> dict:
    reqs = extract_requirements(text, taxonomy)
    return {
        "requirements": [r.to_dict() for r in reqs],
        "qualifications": extract_qualifications(text),
        "responsibilities": extract_responsibilities(text),
        "stats": {
            "required": sum(r.level == "required" for r in reqs),
            "preferred": sum(r.level == "preferred" for r in reqs),
            "uncertain": sum(r.level == "uncertain" for r in reqs),
        },
    }
