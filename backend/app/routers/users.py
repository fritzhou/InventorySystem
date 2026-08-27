import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.dependencies.auth import admin_role
from app.models.user import User, UserSession
from app.schemas.auth import PasswordReset, UserCreate, UserRead, UserUpdate
from app.security import hash_password, normalize_email, utcnow

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(admin_role)])
ROLES = {"ADMIN", "MANAGER", "CASHIER"}


def _user(db, user_id):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    return user


def _commit(db):
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A user with this email already exists")


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)): return list(db.scalars(select(User).order_by(User.display_name)))


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    if payload.role not in ROLES: raise HTTPException(422, "Invalid role")
    user = User(email=normalize_email(payload.email), display_name=payload.display_name.strip(), role=payload.role,
                password_hash=hash_password(payload.temporary_password), is_active=True, must_change_password=True)
    try:
        db.add(user)
        db.flush()
        record_audit(db, actor, "USER_CREATED", "USER", user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A user with this email already exists") from exc
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)): return _user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def patch_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    user = _user(db, user_id); changes = payload.model_dump(exclude_unset=True)
    if user.id == actor.id and (changes.get("is_active") is False or ("role" in changes and changes["role"] != "ADMIN")):
        raise HTTPException(409, "You cannot deactivate or change your own administrative role")
    if changes.get("role") not in ROLES and "role" in changes: raise HTTPException(422, "Invalid role")
    removing_admin = user.is_active and user.role == "ADMIN" and (changes.get("is_active") is False or changes.get("role", "ADMIN") != "ADMIN")
    if removing_admin and db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN", User.is_active.is_(True))) <= 1:
        raise HTTPException(409, "The final active administrator cannot be removed or demoted")
    if "email" in changes: changes["email"] = normalize_email(changes["email"])
    revoke_sessions = changes.get("is_active") is False or ("role" in changes and changes["role"] != user.role)
    for key, value in changes.items(): setattr(user, key, value)
    if revoke_sessions:
        db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    action = "USER_DEACTIVATED" if changes.get("is_active") is False else "USER_UPDATED"
    record_audit(db, actor, action, "USER", user.id); _commit(db); db.refresh(user); return user


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_password(user_id: uuid.UUID, payload: PasswordReset, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    user = _user(db, user_id); user.password_hash = hash_password(payload.temporary_password); user.must_change_password = True
    db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    record_audit(db, actor, "USER_PASSWORD_RESET", "USER", user.id); db.commit(); return user
