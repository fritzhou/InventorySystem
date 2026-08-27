import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import admin_role
from app.models.user import AuditEvent
from app.schemas.auth import AuditPage

router = APIRouter(prefix="/api/audit-events", tags=["audit"], dependencies=[Depends(admin_role)])


@router.get("", response_model=AuditPage)
def audit_events(actor_user_id: uuid.UUID | None = None, action: str = "", entity_type: str = "",
                 start_date: datetime | None = None, end_date: datetime | None = None,
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    query = select(AuditEvent)
    if actor_user_id: query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if action: query = query.where(AuditEvent.action == action)
    if entity_type: query = query.where(AuditEvent.entity_type == entity_type)
    if start_date: query = query.where(AuditEvent.created_at >= start_date)
    if end_date: query = query.where(AuditEvent.created_at <= end_date)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(db.scalars(query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return AuditPage(items=items, total=total, page=page, page_size=page_size)
