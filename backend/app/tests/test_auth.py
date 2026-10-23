from sqlalchemy import select

from app.core.ratelimit import reset_rate_limits
from app.core.config import get_settings
from app.models import EmailVerificationToken, PasswordResetToken, User
from app.core.security import hash_password, verify_password
from app.tests.conftest import PASSWORD, SENT, Client, login, make_user


def register(c, email="new@example.com", password=PASSWORD):
    return c.post("/auth/register", json={"email": email, "password": password, "full_name": "New User"})


def token_from_link(link: str) -> str:
    return link.split("token=")[1]


def test_argon2id_hash_and_verify():
    h = hash_password("Another1Password")
    assert h.startswith("$argon2id$") and verify_password("Another1Password", h) and not verify_password("wrong", h)
    assert not verify_password("anything", None)


def test_register_verify_login_flow(db):
    c = Client()
    r = register(c)
    assert r.status_code == 202 and len(SENT) == 1
    raw = token_from_link(SENT[0]["link"])
    # only a hash is stored, never the raw token
    stored = db.scalar(select(EmailVerificationToken))
    assert stored.token_hash != raw and len(stored.token_hash) == 64
    assert c.post("/auth/login", json={"email": "new@example.com", "password": PASSWORD}).json()["error"]["code"] == "email_not_verified"
    assert c.post("/auth/verify-email", json={"token": raw}).status_code == 200
    assert c.post("/auth/verify-email", json={"token": raw}).status_code == 400  # single use
    r = c.post("/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["role"] == "USER"
    assert "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/auth/me").json()["email"] == "new@example.com"


def test_weak_password_rejected():
    r = register(Client(), password="short1")
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_duplicate_registration_does_not_reveal_account(db):
    make_user(db, "taken@example.com")
    a = register(Client(), "taken@example.com")
    b = register(Client(), "fresh@example.com")
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    assert db.scalar(select(User).where(User.email == "taken@example.com")) is not None


def test_invalid_credentials_are_generic(db):
    make_user(db)
    c = Client()
    wrong_pw = c.post("/auth/login", json={"email": "user@example.com", "password": "WrongPass123"})
    no_user = c.post("/auth/login", json={"email": "nobody@example.com", "password": "WrongPass123"})
    assert wrong_pw.status_code == no_user.status_code == 401 and wrong_pw.json() == no_user.json()


def test_disabled_account_cannot_login(db):
    make_user(db, active=False)
    r = Client().post("/auth/login", json={"email": "user@example.com", "password": PASSWORD})
    assert r.status_code == 403


def test_logout_requires_csrf_and_invalidates_session(user_client):
    r = user_client.c.post("/api/v1/auth/logout")  # no CSRF header
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
    assert user_client.post("/auth/logout").status_code == 200
    user_client.c.cookies.clear()
    assert user_client.get("/auth/me").status_code == 401


def test_unauthenticated_requests_rejected():
    c = Client()
    for url in ("/auth/me", "/resumes", "/applications", "/dashboard", "/roadmaps"):
        assert c.get(url).status_code == 401


def test_password_reset_flow_single_use_and_signs_out(db):
    make_user(db)
    other_device = login()
    c = Client()
    assert c.post("/auth/forgot-password", json={"email": "user@example.com"}).status_code == 200
    assert c.post("/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 200  # same answer
    assert len(SENT) == 1
    raw = token_from_link(SENT[0]["link"])
    assert db.scalar(select(PasswordResetToken)).token_hash != raw
    assert c.post("/auth/reset-password", json={"token": raw, "password": "BrandNew123x"}).status_code == 200
    assert c.post("/auth/reset-password", json={"token": raw, "password": "BrandNew123y"}).status_code == 400
    assert other_device.get("/auth/me").status_code == 401  # old sessions revoked
    assert login(password="BrandNew123x").get("/auth/me").status_code == 200


def test_expired_reset_token_rejected(db):
    from datetime import timedelta
    from app.core.security import utcnow
    make_user(db)
    Client().post("/auth/forgot-password", json={"email": "user@example.com"})
    raw = token_from_link(SENT[0]["link"])
    t = db.scalar(select(PasswordResetToken)); t.expires_at = utcnow() - timedelta(minutes=1); db.commit()
    assert Client().post("/auth/reset-password", json={"token": raw, "password": "BrandNew123x"}).status_code == 400


def test_login_rate_limit(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_ENABLED", True)
    reset_rate_limits()
    make_user(db)
    c = Client()
    codes = [c.post("/auth/login", json={"email": "user@example.com", "password": "WrongPass123"}).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and 429 in codes[10:]


def test_change_password_requires_current(user_client):
    assert user_client.post("/auth/change-password", json={"current_password": "nope", "new_password": "Another1Pass99"}).status_code == 400
    assert user_client.post("/auth/change-password", json={"current_password": PASSWORD, "new_password": "Another1Pass99"}).status_code == 200


def test_account_deletion_removes_user_data(db, user_client):
    from app.tests.conftest import upload_resume, make_analysis
    from app.models import Resume, JobAnalysis
    rid = upload_resume(user_client).json()["id"]
    assert make_analysis(user_client, rid).status_code == 201
    assert user_client.delete("/users/me", json={"password": "wrong"}).status_code == 400
    assert user_client.delete("/users/me", json={"password": PASSWORD}).status_code == 200
    db.expire_all()
    assert db.scalar(select(User).where(User.email == "user@example.com")) is None
    assert db.scalars(select(Resume)).all() == [] and db.scalars(select(JobAnalysis)).all() == []
