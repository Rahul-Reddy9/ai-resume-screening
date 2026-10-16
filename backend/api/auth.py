from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut, UserCreate
from ..security import audit, create_token, hash_password, require_admin, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        audit(db, None, "login_failed", "")
        raise HTTPException(401, "Invalid credentials")
    audit(db, user.id, "login", "")
    return TokenOut(access_token=create_token(user), role=user.role)


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    audit(db, admin.id, "user_created", f"user_id={user.id} role={user.role}")
    return {"id": user.id, "email": user.email, "role": user.role}
