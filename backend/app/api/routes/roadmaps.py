import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import api_error, get_current_user, owned_or_404
from app.core.security import utcnow
from app.db.session import get_db
from app.models import JobAnalysis, LearningRoadmap, RoadmapItem, User
from app.schemas.career import RoadmapCreate, RoadmapItemUpdate
from app.schemas.common import Message
from app.services.roadmap import build_roadmap
from app.services.taxonomy_store import get_taxonomy

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


def _item(i: RoadmapItem) -> dict:
    return {"id": i.id, "position": i.position, "skill": i.skill, "category": i.category, "priority": i.priority,
            "why": i.why, "status": i.status, "tasks": i.tasks, "content": i.content, "completed_at": i.completed_at}


def _out(r: LearningRoadmap, with_items: bool = True) -> dict:
    total = len(r.items)
    done = sum(i.status == "completed" for i in r.items)
    out = {"id": r.id, "analysis_id": r.analysis_id, "title": r.title, "created_at": r.created_at,
           "progress": {"total": total, "completed": done, "in_progress": sum(i.status == "in_progress" for i in r.items),
                        "percent": round(100 * done / total) if total else 0}}
    if with_items:
        out["items"] = [_item(i) for i in r.items]
    return out


@router.post("", status_code=201)
def create_roadmap(body: RoadmapCreate, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = owned_or_404(db.get(JobAnalysis, body.analysis_id), user)
    existing = db.scalar(select(LearningRoadmap).where(LearningRoadmap.analysis_id == a.id))
    if existing:  # keep the user's progress instead of regenerating
        response.status_code = 200
        return _out(existing)
    plan = build_roadmap(a.comparison["priorities"], a.comparison["items"], get_taxonomy())
    r = LearningRoadmap(user_id=user.id, analysis_id=a.id,
                        title=f"Roadmap for {a.job.title}" + (f" at {a.job.company}" if a.job.company else ""))
    for pos, p in enumerate(plan):
        r.items.append(RoadmapItem(
            position=pos, skill=p["skill"], category=p["category"], priority=p["priority"], why=p["why"],
            content={k: p[k] for k in ("explanation", "prerequisites", "project_idea", "resources", "estimated_hours_min",
                                       "estimated_hours_max", "effort_note", "learn_after")},
            tasks=[{"text": t, "done": False} for t in p["exercises"]] + [{"text": "Build: " + p["project_idea"], "done": False}],
            status="not_started"))
    db.add(r)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.get("")
def list_roadmaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(LearningRoadmap).where(LearningRoadmap.user_id == user.id).order_by(LearningRoadmap.created_at.desc())).all()
    return {"items": [_out(r, with_items=False) for r in rows]}


@router.get("/{roadmap_id}")
def get_roadmap(roadmap_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(owned_or_404(db.get(LearningRoadmap, roadmap_id), user))


@router.patch("/{roadmap_id}/items/{item_id}")
def update_item(roadmap_id: uuid.UUID, item_id: uuid.UUID, body: RoadmapItemUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    r = owned_or_404(db.get(LearningRoadmap, roadmap_id), user)
    item = db.get(RoadmapItem, item_id)
    if item is None or item.roadmap_id != r.id:
        raise api_error(404, "not_found", "Not found.")
    if body.tasks is not None:
        if len(body.tasks) != len(item.tasks):
            raise api_error(422, "validation_error", "The number of tasks cannot change.")
        item.tasks = [{"text": old["text"], "done": new.done} for old, new in zip(item.tasks, body.tasks)]
        if body.status is None:  # keep status consistent with ticked tasks
            ticked = sum(t["done"] for t in item.tasks)
            item.status = "completed" if ticked == len(item.tasks) else ("in_progress" if ticked else item.status)
    if body.status is not None:
        item.status = body.status
    item.completed_at = utcnow() if item.status == "completed" else None
    db.commit()
    db.refresh(r)
    return _out(r)


@router.delete("/{roadmap_id}", response_model=Message)
def delete_roadmap(roadmap_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = owned_or_404(db.get(LearningRoadmap, roadmap_id), user)
    db.delete(r)
    db.commit()
    return Message(message="Roadmap deleted.")
