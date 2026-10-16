"""S = w_k*K + w_j*J + w_e*E  (all components normalized 0-100). Baseline, not a validated hiring model."""
import os

from . import matching_engine as me
from .skill_extractor import evidence_snippets, extract_skills, extract_years, normalize_skill

W_K = float(os.getenv("W_SKILLS", "0.50"))
W_J = float(os.getenv("W_SIMILARITY", "0.30"))
W_E = float(os.getenv("W_EXPERIENCE", "0.20"))
if abs(W_K + W_J + W_E - 1.0) > 1e-6:
    raise RuntimeError("Scoring weights must sum to 1")


def model_version() -> str:
    return f"baseline-v1|{me.artifact_version()}|{W_K}/{W_J}/{W_E}"


def final_score(k: float, j: float, e: float) -> float:
    return round(W_K * k + W_J * j + W_E * e, 2)


def screen_resume(resume_text: str, job_description: str, required_skills: list[str],
                  min_years: int = 0) -> dict:
    required = [normalize_skill(s) for s in required_skills if s.strip()] or sorted(extract_skills(job_description))
    found = extract_skills(resume_text)
    k, matched, missing = me.skill_coverage(required, found)
    j = me.similarity(job_description, resume_text)
    evidence = evidence_snippets(resume_text, set(required))
    e = me.experience_score(extract_years(resume_text), min_years, len(evidence))
    return {
        "skill_score": round(k, 2), "similarity_score": round(j, 2), "experience_score": round(e, 2),
        "final_score": final_score(k, j, e), "matched_skills": matched, "missing_skills": missing,
        "evidence": evidence, "model_version": model_version(),
        "predicted_category": me.predict_category(resume_text),
    }


def apply_corrections(result: dict, verified_skills: list[str]) -> dict:
    """Recruiter marks 'missing' skills as verified (extraction error) -> recompute K and S."""
    verified = {normalize_skill(s) for s in verified_skills}
    moved = [s for s in result["missing_skills"] if s in verified]
    if not moved:
        return result
    matched = sorted(set(result["matched_skills"]) | set(moved))
    missing = [s for s in result["missing_skills"] if s not in verified]
    total = len(matched) + len(missing)
    k = round(100.0 * len(matched) / total, 2)
    return {**result, "matched_skills": matched, "missing_skills": missing, "skill_score": k,
            "final_score": final_score(k, result["similarity_score"], result["experience_score"]),
            "model_version": result["model_version"] + "+manual"}


def rank(candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=lambda c: c["final_score"], reverse=True)
