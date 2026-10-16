from tests.conftest import login


def test_requires_auth(client):
    assert client.get("/jobs").status_code in (401, 403)
    assert client.post("/jobs", json={}).status_code in (401, 403)


def test_bad_login_and_token(client):
    assert client.post("/auth/login", json={"email": "admin@test.com", "password": "wrong"}).status_code == 401
    assert client.get("/jobs", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_role_and_job_isolation(client, admin):
    for email in ("r1@test.com", "r2@test.com"):
        assert client.post("/auth/users", headers=admin,
                           json={"email": email, "password": "RecruiterPw123"}).status_code == 201
    r1, r2 = login(client, "r1@test.com", "RecruiterPw123"), login(client, "r2@test.com", "RecruiterPw123")
    assert client.post("/auth/users", headers=r1,
                       json={"email": "x@test.com", "password": "RecruiterPw123"}).status_code == 403
    jid = client.post("/jobs", headers=r1, json={"title": "Data Analyst", "description": "SQL and Excel analysis role " * 3}).json()["id"]
    assert client.get(f"/jobs/{jid}/candidates", headers=r2).status_code == 404
    assert client.get("/jobs", headers=r2).json() == []


def test_oversized_upload_rejected(client, admin):
    jid = client.post("/jobs", headers=admin, json={"title": "Any Role", "description": "Python developer needed " * 3}).json()["id"]
    big = b"%PDF" + b"0" * (6 * 1024 * 1024)
    r = client.post(f"/jobs/{jid}/resumes", headers=admin, files=[("files", ("big.pdf", big, "application/pdf"))])
    assert r.json()["results"][0]["status"] == "rejected"
