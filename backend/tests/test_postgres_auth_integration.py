from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.database import get_db
from app.main import create_app
from app.models.user import User, UserSession
from app.scripts.postgres_safety import destructive_test_database_url
from app.security import hash_password
from tests.test_postgres_integration import alembic_config, reset
from alembic import command


def _url_or_skip() -> str:
    try:
        return destructive_test_database_url()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def test_postgres_phase11_authentication_smoke():
    url = _url_or_skip()
    reset(url)
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    password_hash = hash_password("postgres-password-123")
    with session_factory.begin() as session:
        session.add(User(email="postgres-auth@example.com", display_name="Postgres Admin", password_hash=password_hash,
                         role="ADMIN", is_active=True, must_change_password=False))

    def override_db():
        with Session(engine) as session:
            yield session

    application = create_app(Settings(app_env="test", database_url=url, _env_file=None), engine)
    application.dependency_overrides[get_db] = override_db
    with TestClient(application) as client:
        login = client.post("/api/auth/login", json={"email": "postgres-auth@example.com", "password": "postgres-password-123"})
        assert login.status_code == 200
        assert "password" not in login.text.lower()
        raw_token = client.cookies.get("stockflow_session")
        assert raw_token
        me = client.get("/api/auth/me")
        assert me.status_code == 200 and me.json()["email"] == "postgres-auth@example.com"
        assert "password" not in me.text.lower()
        with session_factory() as session:
            stored = session.scalar(select(UserSession))
            assert stored is not None and stored.token_hash != raw_token
            assert len(stored.token_hash) == 64
        assert client.post("/api/auth/logout").status_code == 204
        with session_factory() as session:
            assert session.scalar(select(UserSession)).revoked_at is not None
            assert session.scalar(select(User).where(User.email == "postgres-auth@example.com")).password_hash == password_hash
    application.dependency_overrides.clear()
    engine.dispose()
