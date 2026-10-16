from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Job, User
from ..schemas import JobCreate, JobOut
from ..security import audit, current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_for_user(db: Session, job_id: int, user: User) -> Job:
    job = db.get(Job, job_id)
    if job is None or (user.role != "admin" and job.created_by != user.id):
        raise HTTPException(404, "Job not found")  # 404 avoids leaking existence
    return job


@router.post("", response_model=JobOut, status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job = Job(created_by=user.id, **body.model_dump())
    db.add(job)
    db.commit()
    audit(db, user.id, "job_created", f"job_id={job.id}")
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Job).order_by(Job.id.desc())
    if user.role != "admin":
        q = q.where(Job.created_by == user.id)
    return db.scalars(q).all()
