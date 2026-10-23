"""Skill taxonomy = bundled taxonomy.json + custom skills added by admins (stored in the DB)."""
from __future__ import annotations

import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SkillAlias, SkillTaxonomyEntry
from app.services.skills.taxonomy import TAXONOMY_PATH, Taxonomy
import json

_lock = threading.Lock()
_cache: Taxonomy | None = None


def get_taxonomy() -> Taxonomy:
    global _cache
    with _lock:
        if _cache is None:
            _cache = Taxonomy.load()
        return _cache


def reload_taxonomy(db: Session) -> Taxonomy:
    """Rebuild the cache from the bundled file plus custom DB entries."""
    global _cache
    extra = []
    for e in db.scalars(select(SkillTaxonomyEntry).where(SkillTaxonomyEntry.is_custom.is_(True))):
        extra.append({"name": e.name, "category": e.category, "aliases": [a.alias for a in e.aliases],
                      "resource_url": e.resource_url, "effort_hours": [e.effort_min, e.effort_max],
                      "prerequisites": e.prerequisites or []})
    with _lock:
        _cache = Taxonomy.load(extra=extra)
        return _cache


def seed_taxonomy(db: Session) -> int:
    """Copy bundled skills into the DB (idempotent) so admins can browse them; returns number added."""
    data = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    existing = set(db.scalars(select(SkillTaxonomyEntry.name)))
    used_aliases = set(db.scalars(select(SkillAlias.alias)))
    added = 0
    for s in data["skills"]:
        if s["name"] in existing:
            continue
        entry = SkillTaxonomyEntry(name=s["name"], category=s["category"], effort_min=s["effort_hours"][0],
                                   effort_max=s["effort_hours"][1], resource_url=s.get("resource_url"),
                                   prerequisites=s.get("prerequisites", []), ambiguous_name=s.get("ambiguous_name", False),
                                   is_custom=False)
        for a in s.get("aliases", []):
            if a not in used_aliases:
                entry.aliases.append(SkillAlias(alias=a)); used_aliases.add(a)
        db.add(entry); added += 1
    db.commit()
    return added
