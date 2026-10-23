import uuid
from datetime import date, datetime

from sqlalchemy import (JSON, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, Uuid, Boolean)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin

APPLICATION_STATUSES = ("SAVED", "APPLIED", "ASSESSMENT", "INTERVIEWING", "OFFER", "REJECTED", "WITHDRAWN")
ROADMAP_STATUSES = ("not_started", "in_progress", "completed")


def _uid(table: str, nullable: bool = False, ondelete: str = "CASCADE", index: bool = True):
    return mapped_column(ForeignKey(f"{table}.id", ondelete=ondelete), nullable=nullable, index=index)


class Resume(IdMixin, TimestampMixin, Base):
    __tablename__ = "resumes"
    user_id: Mapped[uuid.UUID] = _uid("users")
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str | None] = mapped_column(String(80), nullable=True)  # None if files are not retained
    file_type: Mapped[str] = mapped_column(String(10))
    size_bytes: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(cascade="all, delete-orphan", order_by="ResumeAnalysis.created_at.desc()")


class ResumeAnalysis(IdMixin, Base):
    __tablename__ = "resume_analyses"
    resume_id: Mapped[uuid.UUID] = _uid("resumes")
    user_id: Mapped[uuid.UUID] = _uid("users")
    result: Mapped[dict] = mapped_column(JSON)  # sections_found, skills_detected, warnings, suggestions, stats
    ai_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)  # clearly separate from extracted facts
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JobDescription(IdMixin, TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    user_id: Mapped[uuid.UUID] = _uid("users")
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(60), nullable=True)
    text: Mapped[str] = mapped_column(Text)


class JobAnalysis(IdMixin, TimestampMixin, Base):
    __tablename__ = "job_analyses"
    __table_args__ = (Index("ix_job_analyses_user_created", "user_id", "created_at"),)
    user_id: Mapped[uuid.UUID] = _uid("users")
    job_id: Mapped[uuid.UUID] = _uid("job_descriptions")
    resume_id: Mapped[uuid.UUID] = _uid("resumes")
    extracted: Mapped[dict] = mapped_column(JSON)  # raw JD analysis (requirements, qualifications, responsibilities)
    requirements: Mapped[list] = mapped_column(JSON)  # current list, possibly corrected by the user
    comparison: Mapped[dict] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped[JobDescription] = relationship()
    resume: Mapped[Resume] = relationship()


class SkillTaxonomyEntry(IdMixin, TimestampMixin, Base):
    __tablename__ = "skill_taxonomy"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    effort_min: Mapped[int] = mapped_column(Integer, default=10)
    effort_max: Mapped[int] = mapped_column(Integer, default=20)
    resource_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    ambiguous_name: Mapped[bool] = mapped_column(Boolean, default=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    aliases: Mapped[list["SkillAlias"]] = relationship(cascade="all, delete-orphan")


class SkillAlias(IdMixin, Base):
    __tablename__ = "skill_aliases"
    skill_id: Mapped[uuid.UUID] = _uid("skill_taxonomy")
    alias: Mapped[str] = mapped_column(String(100), unique=True)


class LearningRoadmap(IdMixin, TimestampMixin, Base):
    __tablename__ = "learning_roadmaps"
    __table_args__ = (UniqueConstraint("analysis_id", name="uq_roadmap_per_analysis"),)
    user_id: Mapped[uuid.UUID] = _uid("users")
    analysis_id: Mapped[uuid.UUID] = _uid("job_analyses")
    title: Mapped[str] = mapped_column(String(250))
    items: Mapped[list["RoadmapItem"]] = relationship(cascade="all, delete-orphan", order_by="RoadmapItem.position")


class RoadmapItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "roadmap_items"
    __table_args__ = (
        CheckConstraint("status IN ('not_started','in_progress','completed')", name="status_valid"),
        CheckConstraint("priority IN ('high','medium','low')", name="priority_valid"),
    )
    roadmap_id: Mapped[uuid.UUID] = _uid("learning_roadmaps")
    position: Mapped[int] = mapped_column(Integer)
    skill: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(10))
    why: Mapped[str] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSON)  # explanation, prerequisites, project_idea, resources, effort
    tasks: Mapped[list] = mapped_column(JSON)  # [{"text": "...", "done": false}]
    status: Mapped[str] = mapped_column(String(15), default="not_started")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CoverLetter(IdMixin, TimestampMixin, Base):
    __tablename__ = "cover_letters"
    user_id: Mapped[uuid.UUID] = _uid("users")
    analysis_id: Mapped[uuid.UUID | None] = _uid("job_analyses", nullable=True, ondelete="SET NULL")
    title: Mapped[str] = mapped_column(String(250))
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    job_title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30))  # "ai" | "fallback_template" | "user_edited"
    ai_model: Mapped[str | None] = mapped_column(String(80), nullable=True)


class JobApplication(IdMixin, TimestampMixin, Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        CheckConstraint("status IN ('SAVED','APPLIED','ASSESSMENT','INTERVIEWING','OFFER','REJECTED','WITHDRAWN')", name="status_valid"),
        Index("ix_applications_user_status", "user_id", "status"),
        Index("ix_applications_user_deadline", "user_id", "deadline"),
    )
    user_id: Mapped[uuid.UUID] = _uid("users")
    analysis_id: Mapped[uuid.UUID | None] = _uid("job_analyses", nullable=True, ondelete="SET NULL")
    company: Mapped[str] = mapped_column(String(200))
    job_title: Mapped[str] = mapped_column(String(200))
    job_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(15), default="SAVED")
    applied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
