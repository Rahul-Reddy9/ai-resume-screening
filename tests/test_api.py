from tests.conftest import login, make_docx

JD = "We need a backend engineer with Python, FastAPI, PostgreSQL and Docker skills for APIs."


def _job(client, h):
    r = client.post("/jobs", headers=h, json={"title": "Backend Engineer", "description": JD,
                                              "required_skills": ["python", "docker", "kubernetes"],
                                              "min_years_experience": 2})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_full_flow(client, admin):
    jid = _job(client, admin)
    strong = make_docx(["Backend engineer, 6 years of experience.", "Built Python and FastAPI services with Docker."])
    weak = make_docx(["Graphic designer with 3 years of experience in branding and illustration work."])
    r = client.post(f"/jobs/{jid}/resumes", headers=admin, files=[
        ("files", ("strong.docx", strong, "application/octet-stream")),
        ("files", ("weak.docx", weak, "application/octet-stream")),
        ("files", ("virus.exe", b"MZ", "application/octet-stream"))])
    res = {x["filename"]: x for x in r.json()["results"]}
    assert res["strong.docx"]["status"] == "screened" and res["virus.exe"]["status"] == "rejected"

    ranked = client.get(f"/jobs/{jid}/candidates", headers=admin).json()
    assert [c["candidate_reference"] for c in ranked] == ["strong", "weak"]
    assert "kubernetes" in ranked[0]["missing_skills"]

    aid = ranked[0]["application_id"]
    detail = client.get(f"/applications/{aid}/result", headers=admin).json()
    assert detail["evidence"]
    before = detail["final_score"]
    rv = client.patch(f"/applications/{aid}/review", headers=admin,
                      json={"decision": "shortlisted", "verified_skills": ["kubernetes"], "note": "ok"})
    assert rv.json()["review_status"] == "shortlisted" and rv.json()["final_score"] > before
    assert client.get(f"/jobs/{jid}/candidates?review_status=shortlisted", headers=admin).json()[0]["application_id"] == aid
