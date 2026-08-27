import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str, monkeypatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def assert_phase11_schema(engine) -> None:
    inspector = inspect(engine)
    assert {"user_sessions", "audit_events"} <= set(inspector.get_table_names())
    expected = {
        "users": {"display_name", "password_hash", "is_active", "must_change_password", "updated_at", "last_login_at"},
        "sales": {"processed_by_user_id"},
        "sale_returns": {"processed_by_user_id"},
        "inventory_movements": {"actor_user_id"},
        "expenses": {"created_by_user_id", "updated_by_user_id", "voided_by_user_id"},
    }
    for table, columns in expected.items():
        assert columns <= {column["name"] for column in inspector.get_columns(table)}
    expected_foreign_keys = {
        "user_sessions": {"fk_user_sessions_user_id_users"},
        "audit_events": {"fk_audit_events_actor_user_id_users"},
        "sales": {"fk_sales_processed_by_user_id_users"},
        "sale_returns": {"fk_sale_returns_processed_by_user_id_users"},
        "inventory_movements": {"fk_inventory_movements_actor_user_id_users"},
        "expenses": {
            "fk_expenses_created_by_user_id_users",
            "fk_expenses_updated_by_user_id_users",
            "fk_expenses_voided_by_user_id_users",
        },
    }
    for table, names in expected_foreign_keys.items():
        assert names <= {foreign_key["name"] for foreign_key in inspector.get_foreign_keys(table)}


def test_sqlite_upgrade_from_0008_and_round_trip(tmp_path, monkeypatch):
    database_path = tmp_path / "stockflow-migration.db"
    database_url = f"sqlite:///{database_path}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, "20260827_0008")

    engine = create_engine(database_url)
    legacy_id = uuid.uuid4().hex
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email, full_name, role) VALUES (:id, :email, :name, 'ADMIN')"),
                           {"id": legacy_id, "email": "legacy@example.com", "name": "Legacy Admin"})

    command.upgrade(config, "head")
    assert_phase11_schema(engine)
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == "20260827_0009"
        legacy = connection.execute(text("SELECT email, display_name, is_active FROM users WHERE id = :id"), {"id": legacy_id}).one()
        assert legacy.email == "legacy@example.com" and legacy.display_name == "Legacy Admin" and not legacy.is_active

    command.downgrade(config, "20260827_0008")
    command.upgrade(config, "20260827_0009")
    assert_phase11_schema(engine)
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == "20260827_0009"
    get_settings.cache_clear()
