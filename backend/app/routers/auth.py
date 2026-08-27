from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user
from app.models.user import User, UserSession
from app.schemas.auth import ChangePasswordInput, LoginInput, UserRead
from app.security import hash_password, new_session_secret, normalize_email, token_digest, utcnow, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])
settings = get_settings()
DUMMY_PASSWORD_HASH = hash_password("stockflow-dummy-password-verification")


@router.post("/login", response_model=UserRead)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    password_valid = verify_password(payload.password, user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH)
    if not user or not user.is_active or not user.password_hash or not password_valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    secret = new_session_secret()
    now = utcnow()
    db.add(UserSession(user_id=user.id, token_hash=token_digest(secret), expires_at=now + timedelta(hours=settings.session_expiration_hours)))
    user.last_login_at = now
    db.commit()
    response.set_cookie(settings.session_cookie_name, secret, max_age=settings.session_expiration_hours * 3600,
                        httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")
    return user


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.session_cookie_secure, httponly=True, samesite="lax")


@router.post("/change-password", response_model=UserRead)
def change_password(payload: ChangePasswordInput, session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    user = session.user
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.id != session.id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.commit()
    return user
