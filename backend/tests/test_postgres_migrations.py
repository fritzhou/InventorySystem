import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="requires an isolated disposable TEST_POSTGRES_URL")
def test_empty_postgresql_upgrade_downgrade_upgrade(monkeypatch):
    url = os.environ["TEST_POSTGRES_URL"]
    engine = create_engine(url)
    # TEST_POSTGRES_URL must identify a disposable database: this deliberately clears it.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260827_0009"
        assert {"users", "user_sessions", "sales", "expenses", "audit_events"} <= set(inspect(connection).get_table_names())
    command.downgrade(config, "20260827_0007")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260827_0009"
