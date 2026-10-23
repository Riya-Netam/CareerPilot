import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl

Level = Literal["required", "preferred", "uncertain"]
AppStatus = Literal["SAVED", "APPLIED", "ASSESSMENT", "INTERVIEWING", "OFFER", "REJECTED", "WITHDRAWN"]
RoadmapStatus = Literal["not_started", "in_progress", "completed"]


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    original_filename: str
    file_type: str
    size_bytes: int
    created_at: datetime


class ResumeDetail(ResumeOut):
    analysis: dict | None = None
    ai_suggestions: list | None = None


class JobInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    experience_level: str | None = Field(default=None, max_length=60)
    description: str = Field(min_length=50, max_length=20000)

    @field_validator("title", "company", "location", "experience_level", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) and v.strip() else (None if isinstance(v, str) else v)


class ExtractIn(BaseModel):
    description: str = Field(min_length=50, max_length=20000)


class RequirementIn(BaseModel):
    skill: str = Field(min_length=1, max_length=100)
    level: Level


class AnalysisCreate(JobInput):
    resume_id: uuid.UUID
    # Optional user-reviewed requirement list (from the review step). If omitted, extraction is used as-is.
    requirements: list[RequirementIn] | None = Field(default=None, max_length=80)


class RequirementsUpdate(BaseModel):
    requirements: list[RequirementIn] = Field(max_length=80)


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    job_title: str
    company: str | None
    resume_id: uuid.UUID
    resume_filename: str
    score: float | None
    user_adjusted: bool
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    location: str | None
    experience_level: str | None
    extracted: dict
    requirements: list
    comparison: dict


class RoadmapCreate(BaseModel):
    analysis_id: uuid.UUID


class RoadmapTask(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    done: bool


class RoadmapItemUpdate(BaseModel):
    status: RoadmapStatus | None = None
    tasks: list[RoadmapTask] | None = Field(default=None, max_length=20)


class CoverLetterGenerate(BaseModel):
    analysis_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=1500)


class CoverLetterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    content: str | None = Field(default=None, min_length=1, max_length=8000)


class CoverLetterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    analysis_id: uuid.UUID | None
    title: str
    company: str | None
    job_title: str
    content: str
    source: str
    ai_model: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationIn(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    job_url: HttpUrl | None = None
    status: AppStatus = "SAVED"
    applied_on: date | None = None
    deadline: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    analysis_id: uuid.UUID | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    job_url: HttpUrl | None = None
    status: AppStatus | None = None
    applied_on: date | None = None
    deadline: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    analysis_id: uuid.UUID | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company: str
    job_title: str
    job_url: str | None
    status: str
    applied_on: date | None
    deadline: date | None
    notes: str | None
    analysis_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
