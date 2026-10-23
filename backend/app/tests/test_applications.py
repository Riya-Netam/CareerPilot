from datetime import date, timedelta


def add(c, company, title, **kw):
    return c.post("/applications", json={"company": company, "job_title": title, **kw})


def test_crud_and_status_flow(user_client):
    r = add(user_client, "Acme", "Backend Dev", job_url="https://acme.example/jobs/1", notes="referred by a friend")
    assert r.status_code == 201 and r.json()["status"] == "SAVED"
    aid = r.json()["id"]
    u = user_client.patch(f"/applications/{aid}", json={"status": "INTERVIEWING", "applied_on": "2026-09-01"}).json()
    assert u["status"] == "INTERVIEWING" and u["applied_on"] == "2026-09-01" and u["company"] == "Acme"
    assert user_client.patch(f"/applications/{aid}", json={"status": "MAYBE"}).status_code == 422
    assert user_client.delete(f"/applications/{aid}").status_code == 200
    assert user_client.get(f"/applications/{aid}").status_code == 404


def test_invalid_url_rejected(user_client):
    assert add(user_client, "A", "B", job_url="javascript:alert(1)").status_code == 422


def test_search_filter_sort_paginate(user_client):
    for i, (co, st) in enumerate([("Zeta", "APPLIED"), ("Alpha", "SAVED"), ("Beta", "APPLIED"), ("Gamma", "OFFER")]):
        add(user_client, co, f"Role {i}", status=st)
    assert user_client.get("/applications?status=APPLIED").json()["total"] == 2
    assert user_client.get("/applications?q=alp").json()["items"][0]["company"] == "Alpha"
    names = [a["company"] for a in user_client.get("/applications?sort=company&order=asc").json()["items"]]
    assert names == sorted(names)
    p = user_client.get("/applications?page=2&page_size=3").json()
    assert p["total"] == 4 and len(p["items"]) == 1
    assert user_client.get("/applications?status=BOGUS").status_code == 422


def test_summary_counts_and_upcoming_deadlines(user_client):
    soon = (date.today() + timedelta(days=3)).isoformat()
    far = (date.today() + timedelta(days=90)).isoformat()
    add(user_client, "Soon", "Dev", deadline=soon)
    add(user_client, "Far", "Dev", deadline=far)
    add(user_client, "Done", "Dev", deadline=soon, status="REJECTED")
    s = user_client.get("/applications/summary").json()
    assert s["total"] == 3 and s["by_status"]["SAVED"] == 2 and s["by_status"]["REJECTED"] == 1
    assert [d["company"] for d in s["upcoming_deadlines"]] == ["Soon"]


def test_csv_export_blocks_formula_injection(user_client):
    add(user_client, "=HYPERLINK(\"http://evil\")", "Dev", notes="+cmd")
    text = user_client.get("/applications/export.csv").text
    assert "'=HYPERLINK" in text and "'+cmd" in text
