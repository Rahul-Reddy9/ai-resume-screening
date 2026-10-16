import json
import logging
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skill_extractor import normalize_skill

ART = Path(__file__).resolve().parents[2] / "ml" / "artifacts"
log = logging.getLogger("matching")


@lru_cache(maxsize=1)
def _vectorizer():
    p = ART / "vectorizer.joblib"
    if p.exists():
        try:
            return joblib.load(p)
        except Exception as exc:
            log.warning("Could not load vectorizer artifact: %s", exc)
    return None


@lru_cache(maxsize=1)
def _classifier():
    p = ART / "classifier.joblib"
    if p.exists() and _vectorizer() is not None:
        try:
            return joblib.load(p)
        except Exception:
            return None
    return None


def artifact_version() -> str:
    meta = ART / "metadata.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text()).get("version", "untrained")
        except Exception:
            pass
    return "untrained"


def skill_coverage(required: list[str], found: set[str]) -> tuple[float, list[str], list[str]]:
    req = sorted({normalize_skill(s) for s in required if s.strip()})
    if not req:
        return 0.0, [], []
    matched = [s for s in req if s in found]
    missing = [s for s in req if s not in found]
    return 100.0 * len(matched) / len(req), matched, missing


def similarity(job_description: str, resume_text: str) -> float:
    """TF-IDF cosine similarity (0-100). Uses the trained vectorizer if available."""
    if not job_description.strip() or not resume_text.strip():
        return 0.0
    vec = _vectorizer()
    try:
        if vec is not None:
            m = vec.transform([job_description, resume_text])
        else:
            m = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(
                [job_description, resume_text])
        return float(cosine_similarity(m[0], m[1])[0][0]) * 100
    except ValueError:  # empty vocabulary
        return 0.0


def predict_category(resume_text: str) -> str | None:
    clf = _classifier()
    if clf is None:
        return None
    try:
        return str(clf.predict(_vectorizer().transform([resume_text]))[0])
    except Exception:
        return None


def experience_score(years: int, min_years: int, evidence_count: int) -> float:
    target = max(min_years, 1)
    years_part = min(years / target, 1.0) * 60
    evidence_part = min(evidence_count, 4) / 4 * 40
    return years_part + evidence_part
