from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_comma_separated_lists_are_read_from_real_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://one.example, https://two.example")
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://one.example,https://two.example")
    monkeypatch.setenv("ALLOWED_HOSTS", "one.example,two.example")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://one.example", "https://two.example"]
    assert settings.trusted_origins == ["https://one.example", "https://two.example"]
    assert settings.allowed_hosts == ["one.example", "two.example"]


@pytest.mark.parametrize("overrides", [
    {"database_url": "sqlite:///bad.db"},
    {"session_cookie_secure": False},
    {"cors_origins": ["*"]},
    {"allowed_hosts": ["*"]},
])
def test_unsafe_production_configuration_fails(overrides):
    base = dict(app_env="production", database_url="postgresql://u:p@db/test",
                session_cookie_secure=True, cors_origins=["https://app.example"],
                trusted_origins=["https://app.example"], allowed_hosts=["app.example"])
    with pytest.raises(ValidationError):
        Settings(**(base | overrides), _env_file=None)


def test_invalid_samesite_and_insecure_none_fail():
    with pytest.raises(ValidationError):
        Settings(session_cookie_samesite="invalid", _env_file=None)
    with pytest.raises(ValidationError):
        Settings(session_cookie_samesite="none", session_cookie_secure=False, _env_file=None)


def production_settings(**kwargs):
    return Settings(app_env="production", database_url="postgresql://u:p@db/test",
                    session_cookie_secure=True, cors_origins=["https://app.example"],
                    trusted_origins=["https://app.example"], allowed_hosts=["testserver"],
                    **kwargs)


def test_origin_protection_headers_and_docs():
    client = TestClient(create_app(production_settings(), create_engine("sqlite://")))
    assert client.get("/health").status_code == 200
    assert client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/auth/logout").status_code == 403
    allowed = client.post("/api/auth/logout", headers={"Origin": "https://app.example"})
    assert allowed.status_code != 403
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" in response.headers
    assert client.get("/docs").status_code == 404


def test_development_does_not_require_origin():
    client = TestClient(create_app(Settings(_env_file=None), create_engine("sqlite://")))
    assert client.post("/api/auth/logout").status_code != 403


def test_readiness_is_sanitized():
    good = TestClient(create_app(Settings(_env_file=None), create_engine("sqlite://")))
    assert good.get("/ready").status_code == 200
    broken = create_engine("sqlite:////definitely/missing/parent/db.sqlite")
    response = TestClient(create_app(Settings(_env_file=None), broken)).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "sqlite" not in response.text.lower()


def test_spa_routes_and_api_404(tmp_path: Path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>stockflow spa</html>")
    (tmp_path / "assets" / "app-abc.js").write_text("ok")
    settings = Settings(frontend_dist_dir=str(tmp_path), _env_file=None)
    client = TestClient(create_app(settings, create_engine("sqlite://")))
    for route in ("/", "/login", "/dashboard"):
        assert "stockflow spa" in client.get(route).text
        assert client.get(route).headers["cache-control"] == "no-store"
    assert "immutable" in client.get("/assets/app-abc.js").headers["cache-control"]
    api = client.get("/api/nonexistent")
    assert api.status_code == 404 and "stockflow spa" not in api.text
