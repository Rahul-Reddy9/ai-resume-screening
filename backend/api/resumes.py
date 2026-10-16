import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, ScreeningResult, User
from ..security import audit, current_user
from ..services import ranking_engine
from ..services.resume_parser import MAX_BYTES, extract_text, validate_file
from ..storage import save_file
from .jobs import get_job_for_user

router = APIRouter(tags=["resumes"])


@router.post("/jobs/{job_id}/resumes")
def upload_resumes(job_id: int, files: list[UploadFile] = File(...),
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    job = get_job_for_user(db, job_id, user)
    report = []
    for f in files:
        name = os.path.basename(f.filename or "resume")
        data = f.file.read(MAX_BYTES + 1)
        try:
            ext = validate_file(name, data)
            text = extract_text(data, name)
            if len(text) < 30:
                raise ValueError("No extractable text (scanned PDF? set ENABLE_OCR=1)")
        except ValueError as exc:
            report.append({"filename": name, "status": "rejected", "detail": str(exc)})
            continue
        key = save_file(data, ext)
        app = Application(job_id=job.id, resume_file_key=key,
                          candidate_reference=os.path.splitext(name)[0][:100] or f"CAND-{uuid4().hex[:6]}")
        res = ranking_engine.screen_resume(text, job.description, job.required_skills,
                                           job.min_years_experience)
        app.results.append(ScreeningResult(**res))
        db.add(app)
        db.commit()
        audit(db, user.id, "resume_screened", f"job_id={job.id} application_id={app.id}")
        report.append({"filename": name, "status": "screened", "application_id": app.id,
                       "final_score": res["final_score"]})
    return {"job_id": job.id, "results": report}
