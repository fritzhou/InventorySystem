import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

HEAD = "20260827_0009"
TABLES = {"users", "user_sessions", "categories", "products", "sales", "sale_items",
          "inventory_movements", "sale_returns", "sale_return_items", "suppliers",
          "purchase_orders", "purchase_order_items", "expense_categories", "expenses", "audit_events"}


def disposable_url() -> str:
    url = os.getenv("TEST_POSTGRES_URL")
    if not url or os.getenv("ALLOW_DESTRUCTIVE_POSTGRES_TESTS", "").lower() != "true":
        pytest.skip("requires an explicitly opted-in disposable TEST_POSTGRES_URL")
    return url


def alembic_config(url: str) -> Config:
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def reset(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def test_postgres_clean_upgrade_downgrade_reupgrade(monkeypatch):
    url = disposable_url()
    reset(url)
    monkeypatch.setenv("DATABASE_URL", url)
    config = alembic_config(url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert TABLES <= set(inspect(connection).get_table_names())
    command.downgrade(config, "20260827_0007")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
