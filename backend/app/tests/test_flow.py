"""End-to-end happy path: resume -> job analysis -> corrections -> roadmap -> cover letter -> dashboard."""
from app.tests.conftest import JD_TEXT, make_analysis, upload_resume


def test_resume_upload_and_analysis(user_client):
    r = upload_resume(user_client)
    assert r.status_code == 201
    body = r.json()
    assert body["file_type"] == "docx" and "Python" in body["analysis"]["skills_detected"]
    assert "sections" not in body["analysis"]  # raw text is not sent back in analysis JSON
    assert user_client.get("/resumes").json()["total"] == 1
    assert user_client.get(f"/resumes/{body['id']}/download").status_code == 200
    assert "Resume analysis" in user_client.get(f"/resumes/{body['id']}/report").text


def test_invalid_uploads_rejected_safely(user_client):
    for name, data in (("a.pdf", b"not a pdf"), ("a.docx", b"PK\x03\x04junk"), ("a.txt", b"hello"), ("empty.docx", b"")):
        r = upload_resume(user_client, data, name)
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_document"
    assert user_client.get("/resumes").json()["total"] == 0


def test_oversize_upload_rejected(user_client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_MB", 0)
    assert upload_resume(user_client).status_code == 422


def test_extract_then_compare(user_client):
    ex = user_client.post("/job-analyses/extract", json={"description": JD_TEXT}).json()
    levels = {r["skill"]: r["level"] for r in ex["requirements"]}
    assert levels["Python"] == "required" and levels["Docker"] == "preferred" and levels["Kubernetes"] == "preferred"
    assert any(q["type"] == "education" for q in ex["qualifications"])
    rid = upload_resume(user_client).json()["id"]
    a = make_analysis(user_client, rid).json()
    items = {i["skill"]: i for i in a["comparison"]["items"]}
    assert items["Python"]["status"] == "demonstrated" and items["Python"]["evidence"]
    assert items["Machine Learning"]["status"] == "not_found"
    assert items["Git"]["status"] == "listed"
    assert 0 <= a["score"] <= 100 and "not a prediction" in a["comparison"]["score_explanation"]["disclaimer"].lower()
    assert a["comparison"]["manual_confirmation"]
    assert user_client.get(f"/job-analyses/{a['id']}/report").status_code == 200


def test_user_can_correct_requirements_and_score_updates(user_client):
    rid = upload_resume(user_client).json()["id"]
    a = make_analysis(user_client, rid).json()
    before = a["score"]
    reqs = [{"skill": r["skill"], "level": r["level"]} for r in a["requirements"] if r["skill"] != "Machine Learning"]
    reqs.append({"skill": "scikit learn", "level": "preferred"})  # alias is normalised
    upd = user_client.patch(f"/job-analyses/{a['id']}/requirements", json={"requirements": reqs}).json()
    assert upd["user_adjusted"] is True and upd["score"] != before
    names = {r["skill"] for r in upd["requirements"]}
    assert "Machine Learning" not in names and "scikit-learn" in names


def test_analysis_with_reviewed_requirements(user_client):
    rid = upload_resume(user_client).json()["id"]
    r = user_client.post("/job-analyses", json={"resume_id": rid, "title": "Dev", "description": JD_TEXT,
                                                "requirements": [{"skill": "Python", "level": "required"}]})
    assert r.status_code == 201 and len(r.json()["requirements"]) == 1 and r.json()["score"] == 100.0


def test_roadmap_persists_progress(user_client):
    a = make_analysis(user_client, upload_resume(user_client).json()["id"]).json()
    r = user_client.post("/roadmaps", json={"analysis_id": a["id"]})
    assert r.status_code == 201
    rm = r.json()
    assert rm["items"][0]["priority"] == "high" and rm["progress"]["percent"] == 0
    assert user_client.post("/roadmaps", json={"analysis_id": a["id"]}).json()["id"] == rm["id"]  # no duplicate
    item = rm["items"][0]
    upd = user_client.patch(f"/roadmaps/{rm['id']}/items/{item['id']}", json={"status": "completed"}).json()
    assert upd["progress"]["completed"] == 1
    fresh = user_client.get(f"/roadmaps/{rm['id']}").json()  # persisted
    assert fresh["items"][0]["status"] == "completed" and fresh["items"][0]["completed_at"]
    tasks = fresh["items"][1]["tasks"]; tasks[0]["done"] = True
    r = user_client.patch(f"/roadmaps/{rm['id']}/items/{fresh['items'][1]['id']}", json={"tasks": tasks}).json()
    assert r["items"][1]["status"] == "in_progress"
    assert user_client.patch(f"/roadmaps/{rm['id']}/items/{item['id']}", json={"status": "bogus"}).status_code == 422


def test_cover_letter_fallback_edit_save_download(user_client):
    a = make_analysis(user_client, upload_resume(user_client).json()["id"]).json()
    r = user_client.post("/cover-letters/generate", json={"analysis_id": a["id"], "notes": "I am available from June."})
    assert r.status_code == 201
    out = r.json()
    assert out["letter"]["source"] == "fallback_template" and "no AI model" in out["label"]
    assert "available from June" in out["letter"]["content"] and "Acme" in out["letter"]["content"]
    lid = out["letter"]["id"]
    edited = user_client.patch(f"/cover-letters/{lid}", json={"content": "My edited letter text."}).json()
    assert edited["source"] == "user_edited"
    assert user_client.get(f"/cover-letters/{lid}").json()["content"] == "My edited letter text."
    assert user_client.get(f"/cover-letters/{lid}/download").text == "My edited letter text."
    assert user_client.delete(f"/cover-letters/{lid}").status_code == 200


def test_dashboard_reflects_real_data(user_client):
    empty = user_client.get("/dashboard").json()
    assert empty["counts"]["resumes"] == 0 and empty["top_matched_skills"] == [] and empty["recent_activity"] == []
    rid = upload_resume(user_client).json()["id"]
    a = make_analysis(user_client, rid).json()
    user_client.post("/roadmaps", json={"analysis_id": a["id"]})
    user_client.post("/applications", json={"company": "Acme", "job_title": "Dev", "status": "APPLIED"})
    d = user_client.get("/dashboard").json()
    assert d["counts"] == {"resumes": 1, "job_analyses": 1, "cover_letters": 0, "applications": 1, "roadmaps": 1}
    assert any(s["skill"] == "Python" for s in d["top_matched_skills"])
    assert any(g["skill"] == "Machine Learning" for g in d["important_gaps"])
    assert d["application_status"]["APPLIED"] == 1 and d["roadmap_progress"]["total"] > 0


def test_deleting_resume_removes_related_analyses_and_file(user_client):
    rid = upload_resume(user_client).json()["id"]
    make_analysis(user_client, rid)
    assert user_client.delete(f"/resumes/{rid}").status_code == 200
    assert user_client.get("/job-analyses").json()["total"] == 0
    assert user_client.get(f"/resumes/{rid}/download").status_code == 404
