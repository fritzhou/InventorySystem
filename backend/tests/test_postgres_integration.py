from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from app.scripts.postgres_safety import (destructive_test_database_url,
                                         postgres_database_identity)

HEAD = "20260827_0009"
TABLES = {"users", "user_sessions", "categories", "products", "sales", "sale_items",
          "inventory_movements", "sale_returns", "sale_return_items", "suppliers",
          "purchase_orders", "purchase_order_items", "expense_categories", "expenses", "audit_events"}


def disposable_url() -> str:
    try:
        return destructive_test_database_url()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def alembic_config(url: str) -> Config:
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def reset(url: str) -> None:
    guarded_url = destructive_test_database_url()
    if postgres_database_identity(url) != postgres_database_identity(guarded_url):
        raise RuntimeError("refusing to reset a database not approved by the destructive-test guard")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def test_postgres_clean_upgrade_downgrade_reupgrade():
    url = disposable_url()
    reset(url)
    get_settings.cache_clear()
    try:
        config = alembic_config(url)
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as connection:
            assert connection.dialect.name == "postgresql"
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
            assert TABLES <= set(inspect(connection).get_table_names())
        command.downgrade(config, "20260827_0007")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        engine.dispose()
    finally:
        get_settings.cache_clear()
