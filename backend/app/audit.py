from sqlalchemy.orm import Session

from app.models.user import AuditEvent, User


def record_audit(db: Session, actor: User, action: str, entity_type: str, entity_id: object = None, metadata: dict | None = None) -> AuditEvent:
    event = AuditEvent(actor_user_id=actor.id, actor_email=actor.email, actor_display_name=actor.display_name,
                       action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id else None,
                       event_metadata=metadata)
    db.add(event)
    return event
