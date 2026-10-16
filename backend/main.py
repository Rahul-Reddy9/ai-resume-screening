import logging
import os
import time
from collections import defaultdict, deque

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from . import models  # noqa: F401  (register tables)
from .api import auth, candidates, jobs, resumes
from .database import Base, SessionLocal, engine
from .models import User
from .security import hash_password

logging.basicConfig(level=logging.INFO)

_hits: dict[str, deque] = defaultdict(deque)


def startup():
    Base.metadata.create_all(engine)
    email, pw = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if email and pw:
        with SessionLocal() as db:
            if not db.scalar(select(User).where(User.email == email.lower())):
                db.add(User(email=email.lower(), password_hash=hash_password(pw), role="admin"))
                db.commit()


@asynccontextmanager
async def lifespan(_app):
    startup()
    yield


app = FastAPI(title="AI Resume Screening API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    login = request.url.path == "/auth/login"
    limit = int(os.getenv("LOGIN_RATE_LIMIT_PER_MIN" if login else "RATE_LIMIT_PER_MIN",
                          "10" if login else "120"))
    key = f"{request.client.host if request.client else 'x'}:{'login' if login else 'api'}"
    now, q = time.time(), _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    q.append(now)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


for r in (auth.router, jobs.router, resumes.router, candidates.router):
    app.include_router(r)
