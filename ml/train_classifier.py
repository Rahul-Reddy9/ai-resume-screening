"""Train TF-IDF + Logistic Regression / Linear SVM; save versioned artifacts to ml/artifacts/."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

from backend.services.skill_extractor import skill_dictionary

ART = Path("ml/artifacts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["logreg", "svm"], default="logreg")
    ap.add_argument("--train", default="data/processed/train.csv")
    a = ap.parse_args()
    df = pd.read_csv(a.train).dropna(subset=["resume_text", "category_label"])
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=30000,
                          sublinear_tf=True, min_df=1)
    X = vec.fit_transform(df["resume_text"])
    clf = LogisticRegression(max_iter=1000, class_weight="balanced") if a.model == "logreg" \
        else LinearSVC(class_weight="balanced")
    clf.fit(X, df["category_label"])
    ART.mkdir(parents=True, exist_ok=True)
    joblib.dump(vec, ART / "vectorizer.joblib")
    joblib.dump(clf, ART / "classifier.joblib")
    (ART / "skills.json").write_text(json.dumps(sorted(skill_dictionary())))
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    (ART / "metadata.json").write_text(json.dumps(
        {"version": version, "model": a.model, "n_train": len(df), "classes": sorted(clf.classes_.tolist())}, indent=2))
    print(f"Saved artifacts, version {version}, trained on {len(df)} resumes")


if __name__ == "__main__":
    main()
