from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def production(**overrides):
    values = dict(app_env="production", database_url="postgresql://user:secret@db.example/app?sslmode=require",
                  session_cookie_secure=True, allowed_hosts=["stockflow.example.com"], cors_origins=[])
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize("overrides", [
    {"database_url": "sqlite:///unsafe.db"},
    {"session_cookie_secure": False},
    {"cors_origins": ["*"]},
    {"allowed_hosts": ["*"]},
    {"allowed_hosts": []},
])
def test_unsafe_production_configuration_is_rejected(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_database_url_normalization_and_samesite_validation():
    assert production().database_url.startswith("postgresql+psycopg://")
    with pytest.raises(ValidationError):
        Settings(session_cookie_samesite="invalid")


def test_production_disables_api_documentation():
    client = TestClient(create_app(production()))
    assert client.get("/docs", headers={"host": "stockflow.example.com"}).status_code == 404
    assert client.get("/openapi.json", headers={"host": "stockflow.example.com"}).status_code == 404


def test_static_spa_and_api_fallback(tmp_path: Path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<main>StockFlow</main>")
    (tmp_path / "assets" / "app.js").write_text("console.log('ok')")
    settings = Settings(app_env="test", frontend_dist_dir=str(tmp_path))
    client = TestClient(create_app(settings))
    for path in ("/", "/login", "/dashboard"):
        response = client.get(path)
        assert response.status_code == 200 and "StockFlow" in response.text
        assert "no-store" in response.headers["cache-control"]
    assert "immutable" in client.get("/assets/app.js").headers["cache-control"]
    response = client.get("/api/nonexistent")
    assert response.status_code == 404 and response.headers["content-type"].startswith("application/json")


def test_health_is_safe(unauthenticated_client):
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert "database" not in response.text.lower() and "password" not in response.text.lower()


def test_ready_database_failure_is_sanitized(monkeypatch):
    class BrokenEngine:
        def connect(self):
            raise RuntimeError("postgresql://user:secret@private-project.example")

    monkeypatch.setattr("app.main.engine", BrokenEngine())
    response = TestClient(create_app(Settings(app_env="test"))).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
