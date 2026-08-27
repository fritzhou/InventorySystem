"""Delete only expired or already-revoked sessions."""
from sqlalchemy import delete, or_

from app.database import SessionLocal
from app.models.user import UserSession
from app.security import utcnow

with SessionLocal.begin() as session:
    result = session.execute(delete(UserSession).where(or_(UserSession.expires_at <= utcnow(), UserSession.revoked_at.is_not(None))))
print(f"Removed {result.rowcount} expired or revoked sessions.")
