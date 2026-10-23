import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(db: Session, actor_id: uuid.UUID | None, action: str, target_type: str | None = None,
          target_id: str | uuid.UUID | None = None, meta: dict | None = None) -> None:
    """Record an important action. Never put passwords, tokens or user content in `meta`."""
    db.add(AuditLog(actor_id=actor_id, action=action, target_type=target_type,
                    target_id=str(target_id) if target_id else None, meta=meta))
