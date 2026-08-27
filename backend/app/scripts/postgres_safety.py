"""Safety gates shared by destructive PostgreSQL integration tooling."""
import os
from urllib.parse import unquote, urlsplit


def postgres_database_identity(url: str) -> tuple[str, int, str]:
    normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
    if not normalized.startswith("postgresql://"):
        raise RuntimeError("destructive tests require a PostgreSQL TEST_POSTGRES_URL")
    parsed = urlsplit(normalized)
    database = unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not database:
        raise RuntimeError("TEST_POSTGRES_URL must identify a PostgreSQL host and database")
    return parsed.hostname.lower(), parsed.port or 5432, database


def destructive_test_database_url(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    test_url = env.get("TEST_POSTGRES_URL")
    if not test_url:
        raise RuntimeError("TEST_POSTGRES_URL is required")
    if env.get("ALLOW_DESTRUCTIVE_POSTGRES_TESTS", "").lower() != "true":
        raise RuntimeError("ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true is required")
    test_identity = postgres_database_identity(test_url)
    application_url = env.get("DATABASE_URL")
    if application_url:
        try:
            application_identity = postgres_database_identity(application_url)
        except RuntimeError:
            application_identity = None
        if application_identity == test_identity:
            raise RuntimeError("TEST_POSTGRES_URL must not identify the application database")
    return test_url
