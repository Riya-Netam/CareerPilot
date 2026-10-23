"""Transparent resume <-> job comparison and scoring (deterministic).

Score = 100 * sum(weight * credit) / sum(weight)
  weight: required=3, uncertain=2, preferred=1
  credit: demonstrated=1.0 (appears in experience/projects/certifications/achievements),
          listed=0.6 (appears only in skills/summary), not_found=0.0
This is an alignment measure between two texts. It is NOT a chance of getting an
interview or offer, and missing resume evidence does not prove a missing skill.
"""
from __future__ import annotations

from .resume_parser import evidence_for_term
from .taxonomy import Taxonomy

WEIGHTS = {"required": 3, "uncertain": 2, "preferred": 1}
CREDITS = {"demonstrated": 1.0, "listed": 0.6, "not_found": 0.0}
DEMONSTRATING_SECTIONS = {"experience", "projects", "certifications", "achievements", "education"}


def status_from_evidence(evidence: list[dict]) -> str:
    if not evidence:
        return "not_found"
    if any(e["section"] in DEMONSTRATING_SECTIONS for e in evidence):
        return "demonstrated"
    return "listed"


def compare(requirements: list[dict], resume_sections: dict[str, str], taxonomy: Taxonomy,
            qualifications: list[dict] | None = None) -> dict:
    items: list[dict] = []
    for req in requirements:
        ev = evidence_for_term(resume_sections, req["skill"], taxonomy)
        st = status_from_evidence(ev)
        w = WEIGHTS.get(req["level"], 2)
        items.append({**req, "status": st, "evidence": ev, "weight": w, "credit": CREDITS[st],
                      "points": round(w * CREDITS[st], 2)})

    total_w = sum(i["weight"] for i in items)
    score = round(100 * sum(i["points"] for i in items) / total_w, 1) if total_w else None

    def coverage(level: str) -> dict:
        grp = [i for i in items if i["level"] == level]
        if not grp:
            return {"total": 0, "demonstrated": 0, "listed": 0, "not_found": 0, "percent": None}
        c = {s: sum(i["status"] == s for i in grp) for s in CREDITS}
        pct = round(100 * sum(i["credit"] for i in grp) / len(grp), 1)
        return {"total": len(grp), **c, "percent": pct}

    manual: list[dict] = []
    for i in items:
        if i["level"] == "uncertain":
            manual.append({"kind": "skill_level", "skill": i["skill"],
                           "note": "The posting does not clearly say whether this is required. Check the original posting."})
        elif i["status"] == "listed":
            manual.append({"kind": "needs_evidence", "skill": i["skill"],
                           "note": "Listed in your skills but not shown in a project or experience. Consider adding real evidence."})
    for q in qualifications or []:
        manual.append({"kind": q["type"], "skill": None, "note": f'Confirm yourself: "{q["text"]}"'})

    missing_req = [i for i in items if i["level"] == "required" and i["status"] == "not_found"]
    missing_unc = [i for i in items if i["level"] == "uncertain" and i["status"] == "not_found"]
    missing_pref = [i for i in items if i["level"] == "preferred" and i["status"] == "not_found"]
    priorities = ([{"skill": i["skill"], "priority": "high", "why": "Required by the posting and not found in your resume."} for i in missing_req]
                  + [{"skill": i["skill"], "priority": "medium", "why": "Mentioned in the posting (unclear if required) and not found in your resume."} for i in missing_unc]
                  + [{"skill": i["skill"], "priority": "low", "why": "Preferred by the posting and not found in your resume."} for i in missing_pref])

    return {
        "score": score,
        "score_explanation": {
            "formula": "100 x (sum of weight x credit) / (sum of weights)",
            "weights": WEIGHTS, "credits": CREDITS,
            "total_weight": total_w,
            "earned_points": round(sum(i["points"] for i in items), 2),
            "disclaimer": "This measures how much of the posting's skill wording is supported by your resume text. "
                          "It is not a prediction of interviews or job offers, and a skill that was not found may still be one you have.",
        },
        "coverage": {lvl: coverage(lvl) for lvl in ("required", "preferred", "uncertain")},
        "items": items,
        "matched": [i for i in items if i["status"] != "not_found"],
        "not_found": [i for i in items if i["status"] == "not_found"],
        "manual_confirmation": manual,
        "priorities": priorities,
    }
