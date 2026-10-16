import os

import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="AI Resume Screening", layout="wide")


def call(method, path, **kw):
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if "token" in st.session_state else {}
    try:
        r = requests.request(method, f"{API}{path}", headers=headers, timeout=120, **kw)
    except requests.RequestException as exc:
        st.error(f"API unreachable: {exc}")
        st.stop()
    if r.status_code == 401 and "token" in st.session_state:
        st.session_state.pop("token")
        st.rerun()
    return r


def login_page():
    st.title("AI Resume Screening")
    with st.form("login"):
        email, pw = st.text_input("Email"), st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
            if r.ok:
                st.session_state.token, st.session_state.role = r.json()["access_token"], r.json()["role"]
                st.rerun()
            st.error("Invalid credentials" if r.status_code == 401 else r.text)


def jobs_tab():
    with st.expander("Create a job", expanded=False):
        with st.form("job"):
            title = st.text_input("Job title")
            desc = st.text_area("Job description", height=150)
            skills = st.text_input("Required skills (comma separated; blank = derive from description)")
            years = st.number_input("Minimum years of experience", 0, 40, 0)
            if st.form_submit_button("Create"):
                r = call("POST", "/jobs", json={"title": title, "description": desc, "min_years_experience": years,
                                                "required_skills": [s.strip() for s in skills.split(",") if s.strip()]})
                st.success("Job created") if r.ok else st.error(r.text)


def screening_tab(job):
    files = st.file_uploader("Upload resumes (PDF/DOCX)", type=["pdf", "docx"], accept_multiple_files=True)
    if files and st.button("Screen resumes"):
        r = call("POST", f"/jobs/{job['id']}/resumes",
                 files=[("files", (f.name, f.getvalue(), f.type)) for f in files])
        if r.ok:
            st.dataframe(pd.DataFrame(r.json()["results"]), use_container_width=True)
        else:
            st.error(r.text)

    st.subheader("Ranked candidates")
    c1, c2, c3 = st.columns(3)
    min_score = c1.slider("Minimum score", 0, 100, 0)
    status = c2.selectbox("Review status", ["", "pending", "shortlisted", "hold", "rejected"])
    skill = c3.text_input("Must have skill")
    params = {"min_score": min_score, **({"review_status": status} if status else {}),
              **({"skill": skill} if skill else {})}
    r = call("GET", f"/jobs/{job['id']}/candidates", params=params)
    if not r.ok:
        return st.error(r.text)
    rows = r.json()
    if not rows:
        return st.info("No candidates yet.")
    df = pd.DataFrame(rows)
    st.dataframe(df[["application_id", "candidate_reference", "final_score", "skill_score", "similarity_score",
                     "experience_score", "review_status", "predicted_category"]], use_container_width=True)
    st.download_button("Export CSV", df.to_csv(index=False), f"job_{job['id']}_candidates.csv")

    st.subheader("Review a candidate")
    app_id = st.selectbox("Application", df["application_id"],
                          format_func=lambda i: f"#{i} {df.set_index('application_id').loc[i, 'candidate_reference']}")
    d = call("GET", f"/applications/{app_id}/result").json()
    st.metric("Final score", d["final_score"])
    st.write("**Matched skills:**", ", ".join(d["matched_skills"]) or "-")
    st.write("**Missing / unverified skills:**", ", ".join(d["missing_skills"]) or "-")
    for ev in d["evidence"]:
        st.caption(f"[{', '.join(ev['skills'])}] {ev['snippet']}")
    with st.form("review"):
        decision = st.selectbox("Decision", ["shortlisted", "hold", "rejected", "pending"])
        verified = st.multiselect("Mark missing skills as verified (extraction error)", d["missing_skills"])
        note = st.text_area("Note")
        if st.form_submit_button("Save review"):
            rr = call("PATCH", f"/applications/{app_id}/review",
                      json={"decision": decision, "note": note, "verified_skills": verified})
            st.success("Saved") if rr.ok else st.error(rr.text)
            st.rerun() if rr.ok else None
    st.caption("Scores are recommendations for human review, not automated hiring decisions.")


def admin_tab():
    with st.form("newuser"):
        email, pw = st.text_input("New user email"), st.text_input("Password (10+ chars)", type="password")
        role = st.selectbox("Role", ["recruiter", "admin"])
        if st.form_submit_button("Create user"):
            r = call("POST", "/auth/users", json={"email": email, "password": pw, "role": role})
            st.success("User created") if r.ok else st.error(r.text)


if "token" not in st.session_state:
    login_page()
    st.stop()

st.sidebar.write(f"Role: **{st.session_state.role}**")
if st.sidebar.button("Log out"):
    st.session_state.clear()
    st.rerun()

tabs = ["Jobs & Screening"] + (["Admin"] if st.session_state.role == "admin" else [])
for tab, name in zip(st.tabs(tabs), tabs):
    with tab:
        if name == "Admin":
            admin_tab()
        else:
            jobs_tab()
            jobs = call("GET", "/jobs").json()
            if jobs:
                job = st.selectbox("Select job", jobs, format_func=lambda j: f"#{j['id']} {j['title']}")
                screening_tab(job)
            else:
                st.info("Create a job to begin.")
