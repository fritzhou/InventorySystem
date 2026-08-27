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
def unauthenticated_client(db: Session) -> TestClient:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def authenticated_client(db: Session, client: TestClient, role: str) -> tuple[TestClient, User]:
    email = f"test-{role.lower()}@example.com"
    user = User(email=email, display_name=f"Test {role.title()}", password_hash=hash_password("test-password-123"), role=role, is_active=True, must_change_password=False)
    db.add(user)
    db.commit()
    assert client.post("/api/auth/login", json={"email": email, "password": "test-password-123"}).status_code == 200
    return client, user


@pytest.fixture
def admin_client(unauthenticated_client: TestClient, db: Session) -> TestClient:
    return authenticated_client(db, unauthenticated_client, "ADMIN")[0]


@pytest.fixture
def manager_client(unauthenticated_client: TestClient, db: Session) -> TestClient:
    return authenticated_client(db, unauthenticated_client, "MANAGER")[0]


@pytest.fixture
def cashier_client(unauthenticated_client: TestClient, db: Session) -> TestClient:
    return authenticated_client(db, unauthenticated_client, "CASHIER")[0]


@pytest.fixture
def client(admin_client: TestClient) -> TestClient:
    return admin_client
