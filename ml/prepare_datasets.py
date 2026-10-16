"""Normalize datasets into a common schema. Inspect each dataset's columns/licence first.

Usage:
  python -m ml.prepare_datasets --synthetic                      # runs without downloads
  python -m ml.prepare_datasets --kaggle data/raw/Resume.csv     # Resume Classification (Kaggle)
  python -m ml.prepare_datasets --fit data/raw/fit.csv --fit-resume-col resume_text \
      --fit-job-col job_description_text --fit-label-col label  # Resume-Job Fit (check real column names)
Outputs in data/processed/: resumes.csv, train.csv, test.csv, pairs.csv
Schema: resume_id, resume_text, skills, job_id, job_description, required_skills, category_label, relevance_label
"""
import argparse
import random
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from backend.services.skill_extractor import extract_skills
from backend.services.text_preprocessor import clean_text

RAW, PROC = Path("data/raw"), Path("data/processed")
COLS = ["resume_id", "resume_text", "skills", "job_id", "job_description", "required_skills",
        "category_label", "relevance_label"]


def finalize(df: pd.DataFrame) -> pd.DataFrame:
    for c in COLS:
        if c not in df:
            df[c] = None
    df = df[COLS].dropna(subset=["resume_text"]).copy()
    df["resume_text"] = df["resume_text"].map(clean_text)
    df = df[df["resume_text"].str.len() > 30].drop_duplicates(subset=["resume_text"])
    df["skills"] = df["resume_text"].map(lambda t: "|".join(sorted(extract_skills(t))))
    return df.reset_index(drop=True)


def load_kaggle(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = {"Resume_str", "Category"} - set(df.columns)
    if missing:
        raise SystemExit(f"Unexpected schema, columns found: {list(df.columns)}")
    return pd.DataFrame({"resume_id": df.get("ID", df.index).astype(str),
                         "resume_text": df["Resume_str"], "category_label": df["Category"]})


def load_fit(path, rcol, jcol, lcol) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in (rcol, jcol, lcol):
        if c not in df.columns:
            raise SystemExit(f"Column '{c}' not found. Columns: {list(df.columns)}")
    return pd.DataFrame({"resume_id": "fit-" + df.index.astype(str), "resume_text": df[rcol],
                         "job_id": df[jcol].factorize()[0], "job_description": df[jcol],
                         "relevance_label": df[lcol]})


ROLES = {
    "Data Science": ["python", "pandas", "scikit-learn", "machine learning", "sql", "tensorflow"],
    "Web Development": ["javascript", "react", "node.js", "html", "css", "mongodb"],
    "DevOps": ["docker", "kubernetes", "terraform", "aws", "linux", "ci/cd", "jenkins"],
    "Java Developer": ["java", "spring boot", "mysql", "microservices", "git", "rest api"],
}


def synthetic(n_per_role: int = 40, seed: int = 7) -> pd.DataFrame:
    rnd, rows = random.Random(seed), []
    for cat, sk in ROLES.items():
        for i in range(n_per_role):
            have = rnd.sample(sk, k=rnd.randint(3, len(sk)))
            noise = rnd.sample(["excel", "communication", "agile", "jira"], k=2)
            yrs = rnd.randint(1, 9)
            text = (f"Experienced {cat} professional with {yrs} years of experience. "
                    f"Built production systems using {', '.join(have)}. "
                    f"Worked with {', '.join(noise)} in cross-functional teams.")
            rows.append({"resume_id": f"syn-{cat[:3]}-{i}", "resume_text": text, "category_label": cat})
    return pd.DataFrame(rows)


def synthetic_pairs(resumes: pd.DataFrame) -> pd.DataFrame:
    jobs = {c: f"We are hiring a {c} engineer. Required: {', '.join(s)}." for c, s in ROLES.items()}
    rows = []
    for _, r in resumes.iterrows():
        for j, (cat, jd) in enumerate(jobs.items()):
            rows.append({"resume_id": r.resume_id, "resume_text": r.resume_text, "job_id": j,
                         "job_description": jd, "required_skills": "|".join(ROLES[cat]),
                         "relevance_label": int(r.category_label == cat)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle"); ap.add_argument("--fit"); ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--fit-resume-col", default="resume_text")
    ap.add_argument("--fit-job-col", default="job_description_text")
    ap.add_argument("--fit-label-col", default="label")
    a = ap.parse_args()
    PROC.mkdir(parents=True, exist_ok=True)
    frames = []
    if a.kaggle:
        frames.append(load_kaggle(a.kaggle))
    if a.synthetic or not (a.kaggle or a.fit):
        frames.append(synthetic())
    resumes = finalize(pd.concat(frames, ignore_index=True))
    resumes.to_csv(PROC / "resumes.csv", index=False)
    labeled = resumes.dropna(subset=["category_label"])
    train, test = train_test_split(labeled, test_size=0.2, random_state=42,
                                   stratify=labeled["category_label"])
    train.to_csv(PROC / "train.csv", index=False); test.to_csv(PROC / "test.csv", index=False)
    pairs = [synthetic_pairs(test)] if (a.synthetic or not a.fit) else []
    if a.fit:
        pairs.append(finalize(load_fit(a.fit, a.fit_resume_col, a.fit_job_col, a.fit_label_col)))
    pd.concat(pairs, ignore_index=True).to_csv(PROC / "pairs.csv", index=False)
    print(f"resumes={len(resumes)} train={len(train)} test={len(test)} pairs={sum(map(len, pairs))}")


if __name__ == "__main__":
    main()
