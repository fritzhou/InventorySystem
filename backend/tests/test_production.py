from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine

from app.core.config import Settings
from app.main import create_app
from app.scripts.migrate_database import TransferError, validate_source_file


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


def test_comma_separated_environment_lists(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://stockflow.example.com")
    monkeypatch.setenv("ALLOWED_HOSTS", "stockflow.example.com,www.stockflow.example.com")
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://stockflow.example.com")
    settings = Settings()
    assert settings.cors_origins == ["https://stockflow.example.com"]
    assert settings.allowed_hosts == ["stockflow.example.com", "www.stockflow.example.com"]
    assert settings.trusted_origins == ["https://stockflow.example.com"]


def test_development_environment_list_values(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
    monkeypatch.setenv("TRUSTED_ORIGINS", "http://localhost:5173")
    settings = Settings()
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]
    assert settings.trusted_origins == ["http://localhost:5173"]


def test_missing_sqlite_source_is_rejected(tmp_path):
    with pytest.raises(TransferError, match="does not exist"):
        validate_source_file(f"sqlite:///{tmp_path / 'missing-file.db'}")


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


def test_production_origin_protection():
    settings = production(cors_origins=["https://stockflow.example.com"],
                          trusted_origins=["https://stockflow.example.com"])
    client = TestClient(create_app(settings), base_url="https://stockflow.example.com")
    assert client.post("/api/nonexistent", headers={"origin": "https://stockflow.example.com"}).status_code == 404
    assert client.post("/api/nonexistent", headers={"origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/nonexistent").status_code == 403
    assert client.post("/api/nonexistent", headers={"referer": "https://stockflow.example.com/dashboard"}).status_code == 404
    assert client.get("/api/nonexistent").status_code == 404


def test_ready_database_success():
    ready_engine = create_engine("sqlite://")
    try:
        response = TestClient(create_app(Settings(app_env="test"), db_engine=ready_engine)).get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    finally:
        ready_engine.dispose()


def test_ready_database_failure_is_sanitized():
    class BrokenEngine:
        def connect(self):
            raise RuntimeError("postgresql://user:secret@private-project.example")

    response = TestClient(create_app(Settings(app_env="test"), db_engine=BrokenEngine())).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
