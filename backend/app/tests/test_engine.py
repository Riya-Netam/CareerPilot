"""Pure-Python engine tests (no database or web server needed)."""
import io

import docx
import pytest

from app.services.cover_letter import fallback_cover_letter
from app.services.document_text import DocumentError, ScannedDocumentError, extract_text
from app.services.roadmap import build_roadmap
from app.services.skills.comparison import compare
from app.services.skills.jd_parser import analyze_job_description, extract_qualifications
from app.services.skills.resume_parser import parse_resume, split_sections
from app.services.skills.taxonomy import Taxonomy, normalize_text

T = Taxonomy.load()

RESUME = """Riya Sample
riya@example.com | +91 98765 43210

Education
B.Tech in Computer Science (AI), CSVTU Bhilai, 2022-2026

Skills
Python, SQL, Git, React, Docker

Projects
Quizora AI
- Built a quiz generator using Python and FastAPI with PostgreSQL.
- Responsible for the testing setup.
"""

JD = """AI Engineer Intern
Responsibilities:
- Build REST APIs using FastAPI.
- Excellent communication.

Requirements:
- Bachelor's degree in Computer Science.
- Strong proficiency in Python.
- Hands-on experience with machine learning.
- Knowledge of Git.
- 2+ years of experience building web applications.

Nice to have:
- Docker
- RAG is a plus.
Familiarity with Kubernetes.
"""


def names(text):
    return {m.skill for m in T.find(text)}


def test_aliases_normalise_to_one_skill():
    assert names("scikit learn") == names("scikit-learn") == names("sklearn") == {"scikit-learn"}


def test_no_substring_false_positives():
    assert names("JavaScript developer") == {"JavaScript"}
    assert "SQL" not in names("NoSQL stores") and "NoSQL" in names("NoSQL stores")
    assert names("Go getter, will excel, send your CV, the rest of the team") == set()


def test_special_character_skills():
    assert {"C++", "C#", "Node.js", ".NET"} <= names("C++, C#, Node.js and ASP.NET")


def test_ambiguous_words_need_unambiguous_alias():
    assert names("We write golang services") == {"Go"}
    assert names("R programming and Go, Python") == {"R", "Python"}


def test_required_preferred_uncertain_classification():
    r = {x["skill"]: x for x in analyze_job_description(JD, T)["requirements"]}
    assert r["Python"]["level"] == "required"
    assert r["Machine Learning"]["level"] == "required"
    assert r["Docker"]["level"] == "preferred"
    assert r["RAG"]["level"] == "preferred"
    assert r["Kubernetes"]["level"] == "preferred"  # "familiarity with" cue
    assert r["FastAPI"]["level"] == "uncertain" and r["FastAPI"]["confidence"] == "low"


def test_qualifications_need_manual_confirmation():
    q = extract_qualifications(JD)
    kinds = {x["type"] for x in q}
    assert {"education", "experience"} <= kinds


def test_resume_sections_and_evidence():
    p = parse_resume(RESUME, T)
    assert {"education", "skills", "projects"} <= set(p["sections_found"])
    assert "FastAPI" in p["skills_detected"]
    assert p["skills_detected"]["FastAPI"][0]["section"] == "projects"
    assert any("experience" in w for w in p["warnings"])
    assert any(s["kind"] == "weak_opening" for s in p["suggestions"])


def test_comparison_score_is_transparent_and_correct():
    a = analyze_job_description(JD, T)
    sections = split_sections(RESUME)
    c = compare(a["requirements"], sections, T, a["qualifications"])
    by = {i["skill"]: i for i in c["items"]}
    assert by["Python"]["status"] == "demonstrated"
    assert by["Git"]["status"] == "listed"
    assert by["Machine Learning"]["status"] == "not_found"
    expected = round(100 * sum(i["weight"] * i["credit"] for i in c["items"]) / sum(i["weight"] for i in c["items"]), 1)
    assert c["score"] == expected
    assert "not a prediction" in c["score_explanation"]["disclaimer"].lower()
    assert any(m["kind"] == "education" for m in c["manual_confirmation"])
    assert c["priorities"][0]["priority"] == "high"


def test_compare_handles_custom_user_skill():
    c = compare([{"skill": "Quantum Basket Weaving", "category": "other", "level": "required",
                  "confidence": "high", "reason": "user added", "evidence": ""}], split_sections(RESUME), T)
    assert c["items"][0]["status"] == "not_found"


def test_empty_requirements_gives_no_score():
    assert compare([], split_sections(RESUME), T)["score"] is None


def test_roadmap_is_prioritised_and_has_no_invented_urls():
    a = analyze_job_description(JD, T)
    c = compare(a["requirements"], split_sections(RESUME), T)
    rm = build_roadmap(c["priorities"], c["items"], T)
    assert rm[0]["priority"] == "high"
    taxonomy_urls = {s.resource_url for s in T.skills.values() if s.resource_url}
    for item in rm:
        for res in item["resources"]:
            assert res["url"] is None or res["url"] in taxonomy_urls
        assert item["status"] == "not_started" and item["estimated_hours_max"] >= item["estimated_hours_min"]


def test_cover_letter_fallback_only_uses_supplied_facts():
    out = fallback_cover_letter(full_name="Riya Sample", job_title="AI Intern", company="Acme",
                                matched_skills=["Python"], sections=split_sections(RESUME))
    assert out["source"] == "fallback_template" and "no AI model" in out["label"]
    assert "Python" in out["content"] and "Acme" in out["content"]
    assert "years of experience" not in out["content"]


def _docx_bytes(paragraphs):
    d = docx.Document()
    for p in paragraphs:
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def test_docx_extraction_ok():
    text, kind = extract_text(_docx_bytes(["Skills", "Python SQL Git React Docker and building small web apps with databases. " * 4]), 5_000_000)
    assert kind == "docx" and "Python" in text


@pytest.mark.parametrize("bad", [b"", b"hello world", b"PK\x03\x04junk"])
def test_invalid_files_rejected(bad):
    with pytest.raises(DocumentError):
        extract_text(bad, 5_000_000)


def test_oversize_rejected():
    with pytest.raises(DocumentError):
        extract_text(b"%PDF-" + b"0" * 100, 50)


def test_normalize_text_keeps_symbols():
    assert "c++" in normalize_text("C/C++ & Node.js") and "node.js" in normalize_text("C/C++ & Node.js")
