"""Evaluate (1) the category classifier and (2) resume-job ranking quality. Writes ml/artifacts/eval_report.json."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score

from backend.services.ranking_engine import screen_resume

ART, PROC = Path("ml/artifacts"), Path("data/processed")


def eval_classifier(report: dict):
    if not (ART / "classifier.joblib").exists() or not (PROC / "test.csv").exists():
        return
    test = pd.read_csv(PROC / "test.csv")
    pred = joblib.load(ART / "classifier.joblib").predict(joblib.load(ART / "vectorizer.joblib")
                                                          .transform(test["resume_text"]))
    rep = classification_report(test["category_label"], pred, output_dict=True, zero_division=0)
    report["classifier"] = rep
    print(classification_report(test["category_label"], pred, zero_division=0))
    errs = test[test["category_label"] != pred].assign(predicted=pred[test["category_label"] != pred])
    report["classifier_errors"] = errs[["resume_id", "category_label", "predicted"]].head(25).to_dict("records")


def eval_ranking(report: dict, k: int = 10, max_rows: int = 3000):
    p = PROC / "pairs.csv"
    if not p.exists():
        return
    df = pd.read_csv(p).dropna(subset=["relevance_label"]).head(max_rows)
    scores = [screen_resume(r.resume_text, r.job_description,
                            str(r.required_skills).split("|") if isinstance(r.required_skills, str) else [])["final_score"]
              for r in df.itertuples()]
    df["score"] = scores
    y = (df["relevance_label"] > 0).astype(int)
    out = {"pairs": len(df)}
    if y.nunique() == 2:
        out["roc_auc"] = float(roc_auc_score(y, df["score"]))
    pk = [g.sort_values("score", ascending=False).head(k)["relevance_label"].gt(0).mean()
          for _, g in df.groupby("job_id")]
    out[f"precision_at_{k}"] = float(np.mean(pk)) if pk else None
    report["ranking"] = out
    print("Ranking:", out)


if __name__ == "__main__":
    rep: dict = {}
    eval_classifier(rep)
    eval_ranking(rep)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "eval_report.json").write_text(json.dumps(rep, indent=2, default=str))
    print("Wrote", ART / "eval_report.json")
