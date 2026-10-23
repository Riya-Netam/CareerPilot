"""Test setup: an isolated SQLite file database; production data is never touched.

Environment variables are set BEFORE the app is imported so settings pick them up.
"""
import io
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="careerpilot_test_")
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "SECRET_KEY": "test-secret-key-test-secret-key-test-secret-key",
    "UPLOAD_DIR": f"{_tmp}/uploads",
    "RATE_LIMIT_ENABLED": "false",
    "AI_ENABLED": "false",
    "EMAIL_MODE": "console",
})

import docx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.deps import CSRF_COOKIE  # noqa: E402
from app.core.ratelimit import reset_rate_limits  # noqa: E402
from app.core.security import hash_password, utcnow  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.models import User  # noqa: E402

PASSWORD = "Sup3rSecret99"
SENT: list[dict] = []


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    reset_rate_limits()
    SENT.clear()
    monkeypatch.setattr("app.api.routes.auth.send_email",
                        lambda to, subject, body, dev_link=None: SENT.append({"to": to, "subject": subject, "link": dev_link}))
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


class Client:
    """TestClient wrapper that sends the CSRF header like the real frontend does."""

    def __init__(self):
        self.c = TestClient(app)

    def _h(self):
        t = self.c.cookies.get(CSRF_COOKIE)
        return {"X-CSRF-Token": t} if t else {}

    def get(self, url, **kw): return self.c.get("/api/v1" + url, **kw)
    def post(self, url, **kw): return self.c.post("/api/v1" + url, headers=self._h(), **kw)
    def patch(self, url, **kw): return self.c.patch("/api/v1" + url, headers=self._h(), **kw)
    def delete(self, url, **kw): return self.c.request("DELETE", "/api/v1" + url, headers=self._h(), **kw)


def make_user(db, email="user@example.com", role="USER", verified=True, active=True, name="Test User"):
    u = User(email=email, password_hash=hash_password(PASSWORD), full_name=name, role=role, is_active=active,
             email_verified_at=utcnow() if verified else None)
    db.add(u); db.commit(); db.refresh(u)
    return u


def login(email="user@example.com", password=PASSWORD) -> Client:
    c = Client()
    r = c.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def user_client(db):
    make_user(db)
    return login()


RESUME_LINES = [
    "Riya Sample", "riya@example.com | +91 98765 43210", "Education",
    "B.Tech in Computer Science (AI), CSVTU Bhilai, 2022-2026", "Skills", "Python, SQL, Git, React, Docker",
    "Projects", "Quizora AI", "- Built a quiz generator using Python and FastAPI with PostgreSQL.",
    "- Responsible for the testing setup and a React dashboard for students and teachers using the platform daily.",
]
JD_TEXT = ("Requirements:\n- Strong proficiency in Python.\n- Hands-on experience with machine learning.\n- Knowledge of Git.\n"
           "- Bachelor's degree in Computer Science.\nNice to have:\n- Docker\n- RAG is a plus.\nFamiliarity with Kubernetes.\n")


def resume_docx() -> bytes:
    d = docx.Document()
    for line in RESUME_LINES:
        d.add_paragraph(line)
    b = io.BytesIO(); d.save(b)
    return b.getvalue()


def upload_resume(client: Client, data: bytes | None = None, name="resume.docx"):
    return client.post("/resumes", files={"file": (name, data if data is not None else resume_docx(), "application/octet-stream")})


def make_analysis(client: Client, resume_id: str):
    return client.post("/job-analyses", json={"resume_id": resume_id, "title": "AI Intern", "company": "Acme", "description": JD_TEXT})
