import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.security import hash_password

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session) -> TestClient:
    db.add(User(email="test-admin@example.com", display_name="Test Admin", password_hash=hash_password("test-password-123"), role="ADMIN", is_active=True, must_change_password=False))
    db.commit()
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        response = test_client.post("/api/auth/login", json={"email": "test-admin@example.com", "password": "test-password-123"})
        assert response.status_code == 200
        yield test_client
    app.dependency_overrides.clear()
