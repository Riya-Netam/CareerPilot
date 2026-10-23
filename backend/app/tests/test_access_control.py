from app.tests.conftest import JD_TEXT, login, make_analysis, make_user, upload_resume


def two_users(db):
    make_user(db, "a@example.com"); make_user(db, "b@example.com")
    return login("a@example.com"), login("b@example.com")


def test_user_cannot_touch_another_users_resume_or_analysis(db):
    a, b = two_users(db)
    rid = upload_resume(a).json()["id"]
    aid = make_analysis(a, rid).json()["id"]
    for r in (b.get(f"/resumes/{rid}"), b.get(f"/resumes/{rid}/download"), b.delete(f"/resumes/{rid}"),
              b.get(f"/job-analyses/{aid}"), b.delete(f"/job-analyses/{aid}"),
              b.patch(f"/job-analyses/{aid}/requirements", json={"requirements": []}),
              b.post("/roadmaps", json={"analysis_id": aid}), b.post("/cover-letters/generate", json={"analysis_id": aid})):
        assert r.status_code == 404, r.text
    # B cannot analyse against A's resume either
    r = b.post("/job-analyses", json={"resume_id": rid, "title": "x", "description": JD_TEXT})
    assert r.status_code == 404
    # and A's data is intact
    assert a.get(f"/resumes/{rid}").status_code == 200
    assert b.get("/resumes").json()["total"] == 0


def test_user_cannot_touch_another_users_application(db):
    a, b = two_users(db)
    app_id = a.post("/applications", json={"company": "Acme", "job_title": "Dev"}).json()["id"]
    assert b.get(f"/applications/{app_id}").status_code == 404
    assert b.patch(f"/applications/{app_id}", json={"status": "OFFER"}).status_code == 404
    assert b.delete(f"/applications/{app_id}").status_code == 404
    assert b.get("/applications").json()["total"] == 0


def test_application_cannot_link_to_foreign_analysis(db):
    a, b = two_users(db)
    aid = make_analysis(a, upload_resume(a).json()["id"]).json()["id"]
    r = b.post("/applications", json={"company": "X", "job_title": "Y", "analysis_id": aid})
    assert r.status_code == 404


def test_regular_user_cannot_reach_admin_api(user_client):
    for url in ("/admin/overview", "/admin/users", "/admin/audit-logs", "/admin/ai", "/admin/errors", "/admin/health", "/admin/taxonomy"):
        assert user_client.get(url).status_code == 403


def test_user_cannot_self_promote(db, user_client):
    r = user_client.patch("/users/me", json={"full_name": "Hacker", "role": "SUPER_ADMIN"})
    assert r.status_code == 200 and r.json()["role"] == "USER"
    assert user_client.get("/admin/overview").status_code == 403


def test_malformed_ids_and_inputs_are_rejected(user_client):
    assert user_client.get("/resumes/not-a-uuid").status_code == 422
    assert user_client.post("/job-analyses/extract", json={"description": "too short"}).status_code == 422
    assert user_client.post("/applications", json={"company": "", "job_title": "x"}).status_code == 422
