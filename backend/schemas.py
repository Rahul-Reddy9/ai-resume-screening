from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10)
    role: Literal["admin", "recruiter"] = "recruiter"


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20)
    required_skills: list[str] = []
    min_years_experience: int = Field(default=0, ge=0, le=40)


class JobOut(JobCreate):
    id: int
    model_config = {"from_attributes": True}


class ReviewIn(BaseModel):
    decision: Literal["shortlisted", "hold", "rejected", "pending"]
    note: str = Field(default="", max_length=2000)
    verified_skills: list[str] = []  # manual correction of extraction errors


class CandidateOut(BaseModel):
    application_id: int
    candidate_reference: str
    final_score: float
    skill_score: float
    similarity_score: float
    experience_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    review_status: str
    model_version: str
    predicted_category: str | None = None
