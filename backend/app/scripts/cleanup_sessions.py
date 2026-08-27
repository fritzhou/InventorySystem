"""Delete only expired or revoked sessions: python -m app.scripts.cleanup_sessions."""
from datetime import datetime, timezone

from sqlalchemy import delete, or_

from app.database import SessionLocal
from app.models.user import UserSession


def main() -> None:
    with SessionLocal.begin() as session:
        result = session.execute(delete(UserSession).where(or_(UserSession.expires_at <= datetime.now(timezone.utc),
                                                               UserSession.revoked_at.is_not(None))))
    print(f"Removed {result.rowcount or 0} expired or revoked sessions")


if __name__ == "__main__":
    main()
