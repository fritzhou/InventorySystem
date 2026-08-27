import getpass

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.user import User
from app.security import hash_password, normalize_email


def create_first_admin(email: str, display_name: str, password: str, confirmation: str) -> User:
    if password != confirmation:
        raise ValueError("Passwords do not match")
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN")):
            raise ValueError("An administrator already exists; use the Users page")
        normalized = normalize_email(email)
        if db.scalar(select(User).where(User.email == normalized)):
            raise ValueError("That email is already in use")
        user = User(email=normalized, display_name=display_name.strip(), password_hash=hash_password(password),
                    role="ADMIN", is_active=True, must_change_password=False)
        db.add(user); db.commit(); db.refresh(user); return user


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
