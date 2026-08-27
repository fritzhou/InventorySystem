from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


CsvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    app_name: str = "StockFlow API"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./stockflow.db"
    cors_origins: CsvList = ["http://localhost:5173"]
    trusted_origins: CsvList = ["http://localhost:5173"]
    allowed_hosts: CsvList = ["localhost", "127.0.0.1", "testserver"]
    product_lookup_timeout_seconds: float = 4.0
    open_food_facts_base_url: str = "https://world.openfoodfacts.org"
    reporting_timezone: str = "Asia/Manila"
    session_cookie_name: str = "stockflow_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_expiration_hours: int = 12
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout: int = 30
    api_docs_enabled: bool | None = None
    frontend_dist_dir: str = "static"
    proxy_forwarded_allow_ips: str = "127.0.0.1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @field_validator("cors_origins", "trusted_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires a secure session cookie")
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("production requires PostgreSQL")
            if not self.session_cookie_secure:
                raise ValueError("production requires secure session cookies")
            if "*" in self.cors_origins:
                raise ValueError("production CORS origins must be explicit")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("production allowed hosts must be explicit")
            if not self.trusted_origins or "*" in self.trusted_origins:
                raise ValueError("production trusted origins must be explicit")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.api_docs_enabled if self.api_docs_enabled is not None else self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
