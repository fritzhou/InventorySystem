from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StockFlow API"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./stockflow.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    trusted_origins: list[str] = []
    api_docs_enabled: bool | None = None
    frontend_dist_dir: str | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout: int = 30
    product_lookup_timeout_seconds: float = 4.0
    open_food_facts_base_url: str = "https://world.openfoodfacts.org"
    reporting_timezone: str = "Asia/Manila"
    session_cookie_name: str = "stockflow_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_expiration_hours: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", "allowed_hosts", "trusted_origins", mode="before")
    @classmethod
    def parse_lists(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @model_validator(mode="after")
    def production_safety(self) -> "Settings":
        if self.api_docs_enabled is None:
            self.api_docs_enabled = self.app_env != "production"
        for origin in self.cors_origins + self.trusted_origins:
            if origin != "*" and urlsplit(origin).scheme not in {"http", "https"}:
                raise ValueError("Origins must be explicit http(s) URLs")
        if self.app_env == "production":
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production DATABASE_URL must use PostgreSQL with psycopg")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if "*" in self.cors_origins:
                raise ValueError("Credentialed production CORS cannot use a wildcard")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("Production ALLOWED_HOSTS must be explicit")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
