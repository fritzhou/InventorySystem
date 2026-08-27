import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.security import hash_password, normalize_email


def _create_first_admin(db: Session, email: str, display_name: str, password: str, confirmation: str) -> User:
    if password != confirmation:
        raise ValueError("Passwords do not match")
    display_name = display_name.strip()
    if not display_name:
        raise ValueError("Display name must not be blank")
    if db.scalar(select(User).where(User.role == "ADMIN", User.is_active.is_(True), User.password_hash.is_not(None))):
        raise ValueError("An active administrator already exists; use the Users page")
    normalized = normalize_email(email)
    existing = db.scalar(select(User).where(User.email == normalized))
    if existing:
        if existing.role == "ADMIN" and not existing.is_active and existing.password_hash is None:
            existing.display_name = display_name
            existing.password_hash = hash_password(password)
            existing.is_active = True
            existing.must_change_password = False
            db.commit()
            db.refresh(existing)
            return existing
        raise ValueError("That email is already in use")
    user = User(email=normalized, display_name=display_name, password_hash=hash_password(password),
                role="ADMIN", is_active=True, must_change_password=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_first_admin(email: str, display_name: str, password: str, confirmation: str) -> User:
    with SessionLocal() as db:
        return _create_first_admin(db, email, display_name, password, confirmation)


def main() -> None:
    email = input("Email: ")
    display_name = input("Display name: ")
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    try:
        user = create_first_admin(email, display_name, password, confirmation)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Created administrator {user.email}")


if __name__ == "__main__": main()
