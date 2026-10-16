from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, ReviewRecord, ScreeningResult, User
from ..schemas import CandidateOut, ReviewIn
from ..security import audit, current_user
from ..services import ranking_engine
from .jobs import get_job_for_user

router = APIRouter(tags=["candidates"])


def _out(app: Application) -> dict:
    r = app.results[0]
    return {"application_id": app.id, "candidate_reference": app.candidate_reference,
            "final_score": r.final_score, "skill_score": r.skill_score,
            "similarity_score": r.similarity_score, "experience_score": r.experience_score,
            "matched_skills": r.matched_skills, "missing_skills": r.missing_skills,
            "review_status": app.review_status, "model_version": r.model_version,
            "predicted_category": r.predicted_category}


def _get_app(db: Session, app_id: int, user: User) -> Application:
    app = db.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "Application not found")
    get_job_for_user(db, app.job_id, user)
    return app


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateOut])
def ranked_candidates(job_id: int, min_score: float = 0, review_status: str | None = None,
                      skill: str | None = None, db: Session = Depends(get_db),
                      user: User = Depends(current_user)):
    job = get_job_for_user(db, job_id, user)
    rows = [_out(a) for a in job.applications if a.results]
    if min_score:
        rows = [r for r in rows if r["final_score"] >= min_score]
    if review_status:
        rows = [r for r in rows if r["review_status"] == review_status]
    if skill:
        s = skill.lower()
        rows = [r for r in rows if s in r["matched_skills"]]
    audit(db, user.id, "candidates_viewed", f"job_id={job.id}")
    return ranking_engine.rank(rows)


@router.get("/applications/{app_id}/result")
def application_result(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    app = _get_app(db, app_id, user)
    audit(db, user.id, "result_viewed", f"application_id={app.id}")
    return {**_out(app), "evidence": app.results[0].evidence,
            "runs": len(app.results),
            "reviews": [{"decision": r.decision, "note": r.note, "verified_skills": r.verified_skills,
                         "reviewer_id": r.reviewer_id, "at": r.created_at.isoformat()}
                        for r in app.reviews]}


@router.patch("/applications/{app_id}/review")
def review(app_id: int, body: ReviewIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    app = _get_app(db, app_id, user)
    latest = app.results[0]
    if body.verified_skills:
        corrected = ranking_engine.apply_corrections(
            {"skill_score": latest.skill_score, "similarity_score": latest.similarity_score,
             "experience_score": latest.experience_score, "final_score": latest.final_score,
             "matched_skills": latest.matched_skills, "missing_skills": latest.missing_skills,
             "evidence": latest.evidence, "model_version": latest.model_version,
             "predicted_category": latest.predicted_category}, body.verified_skills)
        if corrected["final_score"] != latest.final_score:
            app.results.insert(0, ScreeningResult(**corrected))
            audit(db, user.id, "score_corrected",
                  f"application_id={app.id} {latest.final_score}->{corrected['final_score']}")
    app.review_status = body.decision
    db.add(ReviewRecord(application_id=app.id, reviewer_id=user.id, decision=body.decision,
                        note=body.note, verified_skills=body.verified_skills))
    db.commit()
    audit(db, user.id, "review_recorded", f"application_id={app.id} decision={body.decision}")
    db.refresh(app)
    return _out(app)
