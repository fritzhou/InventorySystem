from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models.user import User, UserSession
from app.security import token_digest, utcnow
settings = get_settings()


def get_current_session(stockflow_session: str | None = Cookie(None, alias=settings.session_cookie_name), db: Session = Depends(get_db)) -> UserSession:
    if not stockflow_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(stockflow_session)))
    now = utcnow()
    if not session or session.revoked_at or _aware(session.expires_at) <= now or not session.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    session.last_seen_at = now
    return session


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_current_user(session: UserSession = Depends(get_current_session)) -> User:
    return session.user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.must_change_password:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Password change required")
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return dependency


any_role = require_roles("ADMIN", "MANAGER", "CASHIER")
manager_role = require_roles("ADMIN", "MANAGER")
admin_role = require_roles("ADMIN")
