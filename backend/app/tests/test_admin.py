from sqlalchemy import select

from app.core.config import get_settings
from app.models import AuditLog
from app.tests.conftest import PASSWORD, Client, login, make_analysis, make_user, upload_resume


def test_admin_overview_and_user_list(db):
    make_user(db, "admin@example.com", role="ADMIN"); make_user(db, "u1@example.com"); make_user(db, "u2@example.com")
    admin = login("admin@example.com")
    assert admin.get("/admin/overview").json()["users"]["total"] == 3
    page = admin.get("/admin/users?q=u1").json()
    assert page["total"] == 1 and page["items"][0]["email"] == "u1@example.com"
    assert "password_hash" not in page["items"][0]
    assert admin.get("/admin/users?role=ADMIN").json()["total"] == 1


def test_admin_never_sees_private_content(db):
    make_user(db, "admin@example.com", role="ADMIN"); u = make_user(db, "u1@example.com")
    uc = login("u1@example.com")
    aid = make_analysis(uc, upload_resume(uc).json()["id"]).json()["id"]
    uc.post("/cover-letters/generate", json={"analysis_id": aid})
    uc.post("/applications", json={"company": "SecretCo", "job_title": "Dev", "notes": "private note"})
    admin = login("admin@example.com")
    detail = admin.get(f"/admin/users/{u.id}")
    assert detail.json()["counts"]["resumes"] == 1
    blob = detail.text + admin.get("/admin/users").text + admin.get("/admin/overview").text
    for secret in ("Riya", "SecretCo", "private note", "Quizora", "Dear"):
        assert secret not in blob


def test_disable_and_reactivate_with_audit_log(db):
    make_user(db, "admin@example.com", role="ADMIN"); u = make_user(db, "u1@example.com")
    uc = login("u1@example.com")
    admin = login("admin@example.com")
    assert admin.post(f"/admin/users/{u.id}/disable").json()["is_active"] is False
    assert uc.get("/auth/me").status_code in (401, 403)  # existing session revoked
    assert Client().post("/auth/login", json={"email": "u1@example.com", "password": PASSWORD}).status_code == 403
    assert admin.post(f"/admin/users/{u.id}/reactivate").json()["is_active"] is True
    actions = [a.action for a in db.scalars(select(AuditLog))]
    assert "admin.disable_user" in actions and "admin.reactivate_user" in actions
    logs = admin.get("/admin/audit-logs").json()
    assert logs["total"] >= 2 and logs["items"][0]["actor"] == "admin@example.com"


def test_admin_privilege_boundaries(db):
    a1 = make_user(db, "a1@example.com", role="ADMIN"); a2 = make_user(db, "a2@example.com", role="ADMIN")
    sa = make_user(db, "sa@example.com", role="SUPER_ADMIN")
    admin = login("a1@example.com")
    assert admin.post(f"/admin/users/{a1.id}/disable").status_code == 400   # not yourself
    assert admin.post(f"/admin/users/{a2.id}/disable").status_code == 403   # not another admin
    assert admin.post(f"/admin/users/{sa.id}/disable").status_code == 403   # not a super admin
    assert login("sa@example.com").post(f"/admin/users/{a2.id}/disable").status_code == 200
    # there is no API route that changes roles
    assert admin.patch(f"/admin/users/{a1.id}", json={"role": "SUPER_ADMIN"}).status_code in (404, 405)


def test_admin_health_does_not_expose_secrets(db):
    make_user(db, "admin@example.com", role="ADMIN")
    body = login("admin@example.com").get("/admin/health").text
    assert get_settings().SECRET_KEY not in body and "DATABASE_URL" not in body and "sqlite" not in body.lower()
    assert '"database":{"ok":true}' in body.replace(" ", "")


def test_admin_ai_status_when_ai_disabled(db):
    make_user(db, "admin@example.com", role="ADMIN")
    r = login("admin@example.com").get("/admin/ai").json()
    assert r["available"] is False and "still work" in r["note"]


def test_taxonomy_extension_changes_extraction(db):
    make_user(db, "admin@example.com", role="ADMIN")
    admin = login("admin@example.com")
    assert admin.post("/admin/taxonomy", json={"name": "Quantum Basket Weaving", "category": "tools", "aliases": ["qbw"]}).status_code == 201
    ex = admin.post("/job-analyses/extract", json={"description": "Requirements:\n- Must know Quantum Basket Weaving and Python for this role at our company."}).json()
    assert "Quantum Basket Weaving" in {r["skill"] for r in ex["requirements"]}
    assert admin.post("/admin/taxonomy", json={"name": "quantum basket weaving", "category": "tools"}).status_code == 409
