from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StockFlow API"
    database_url: str = "sqlite:///./stockflow.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    product_lookup_timeout_seconds: float = 4.0
    open_food_facts_base_url: str = "https://world.openfoodfacts.org"
    reporting_timezone: str = "Asia/Manila"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
