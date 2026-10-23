"""Skill taxonomy and alias matcher (pure Python, no web/DB dependencies).

Matching is word-boundary based on normalised text, so "java" does not match
"javascript" and "sql" does not match "nosql". Ambiguous words such as "go",
"r" or "excel" are not bare aliases; they need an unambiguous alias.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TAXONOMY_PATH = Path(__file__).with_name("taxonomy.json")

CATEGORY_LABELS = {
    "programming_language": "Programming languages",
    "framework": "Frameworks & libraries",
    "database": "Databases",
    "ai_ml": "AI & machine learning",
    "genai_nlp": "Generative AI & NLP",
    "cloud_devops": "Cloud & deployment",
    "tools": "Developer tools",
    "data": "Data analysis",
    "concept": "Software engineering concepts",
    "soft_skill": "Soft skills",
}


def normalize_text(text: str) -> str:
    """Lowercase, unify quotes/dashes, and turn separators into spaces.

    Keeps '+', '#', and '.' inside tokens so c++, c#, node.js survive.
    """
    t = text.lower()
    t = t.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    t = re.sub(r"[-_/\\|]", " ", t)
    t = re.sub(r"[^a-z0-9+#.\s']", " ", t)
    return re.sub(r"\s+", " ", t)


@dataclass
class Skill:
    name: str
    category: str
    aliases: list[str]
    resource_url: str | None = None
    effort_hours: tuple[int, int] = (10, 20)
    prerequisites: list[str] = field(default_factory=list)
    ambiguous_name: bool = False  # True when the bare name is a common word (Go, R, C)


@dataclass
class Mention:
    skill: str
    start: int
    end: int


class Taxonomy:
    def __init__(self, skills: list[Skill]):
        self.skills: dict[str, Skill] = {s.name: s for s in skills}
        self._compile()

    @classmethod
    def load(cls, path: Path | str = TAXONOMY_PATH, extra: list[dict] | None = None) -> "Taxonomy":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = list(data["skills"]) + list(extra or [])
        skills = [
            Skill(
                name=e["name"],
                category=e["category"],
                aliases=list(e.get("aliases", [])),
                resource_url=e.get("resource_url"),
                effort_hours=tuple(e.get("effort_hours", (10, 20))),
                prerequisites=list(e.get("prerequisites", [])),
                ambiguous_name=bool(e.get("ambiguous_name", False)),
            )
            for e in entries
        ]
        return cls(skills)

    def _compile(self) -> None:
        # Longest aliases first so "spring boot" wins over "spring"
        pairs: list[tuple[str, str]] = []
        for s in self.skills.values():
            names = [] if s.ambiguous_name else [normalize_text(s.name)]
            for a in {*names, *(normalize_text(x) for x in s.aliases)}:
                if a:
                    pairs.append((a, s.name))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._alias_to_skill: dict[str, str] = {}
        for a, n in pairs:
            self._alias_to_skill.setdefault(a, n)
        alts = "|".join(re.escape(a) for a in self._alias_to_skill)
        self._regex = re.compile(rf"(?<![a-z0-9+#.]){'(' + alts + ')'}(?![a-z0-9+#])") if alts else None

    def find(self, text: str) -> list[Mention]:
        """Return non-overlapping skill mentions in `text` (positions refer to normalised text)."""
        if not self._regex:
            return []
        norm = normalize_text(text)
        out: list[Mention] = []
        for m in self._regex.finditer(norm):
            out.append(Mention(self._alias_to_skill[m.group(1)], m.start(), m.end()))
        return out

    def skills_in(self, text: str) -> set[str]:
        return {m.skill for m in self.find(text)}

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def resolve(self, name: str) -> str:
        """Map a user-typed skill to its canonical name if known, else return it cleaned."""
        key = normalize_text(name).strip()
        return self._alias_to_skill.get(key, name.strip())
