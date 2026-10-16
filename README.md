# AI-Based Resume Screening System

FastAPI + Streamlit + spaCy/scikit-learn + PostgreSQL + Docker + GitHub Actions.
Scores are **recommendations for human review**, not automated hiring decisions.

## Quick start (local, SQLite)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)
python -m ml.prepare_datasets --synthetic && python -m ml.train_classifier   # optional: trained artifacts
uvicorn backend.main:app --reload                 # API docs: http://localhost:8000/docs
streamlit run frontend/app.py                     # UI: http://localhost:8501
```
Log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`, create recruiters in the Admin tab.

## Docker (PostgreSQL)
```bash
cp .env.example .env   # set SECRET_KEY and ADMIN_PASSWORD
docker compose up --build
```

## Real datasets
Check licences and columns first, then:
```bash
python -m ml.prepare_datasets --kaggle data/raw/Resume.csv
python -m ml.prepare_datasets --fit data/raw/fit.csv --fit-resume-col <col> --fit-job-col <col> --fit-label-col <col>
python -m ml.train_classifier --model logreg   # or svm
python -m ml.evaluate_model                     # writes ml/artifacts/eval_report.json
```
Note: the `--kaggle` and `--fit` runs overwrite the processed files; pass `--synthetic` too to mix in controlled samples.
The Job Skill Set dataset can be used to extend `ml/artifacts/skills.json` (the skill dictionary; defaults are built in).
Resume category labels are NOT relevance labels: the classifier and the matching score are separate tasks.

## Scoring
`S = 0.50*K + 0.30*J + 0.20*E` (skill coverage, TF-IDF cosine similarity, experience evidence; each 0-100).
Weights are configurable via `W_SKILLS`, `W_SIMILARITY`, `W_EXPERIENCE`. This is an unvalidated baseline.

## Security and privacy
JWT auth with admin/recruiter roles enforced on the backend; PBKDF2 password hashing; file type/size/magic-byte
validation; private random-key file storage; rate limiting; audit log (IDs only, no resume text); sensitive
attributes are never used in scoring. Define a retention/deletion policy before real use.

## Layout
`backend/` API + services, `frontend/` Streamlit, `ml/` dataset prep/training/evaluation, `tests/` pytest, `.github/workflows/ci.yml` CI.
