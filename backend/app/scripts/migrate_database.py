"""One-time, transactional SQLite-to-PostgreSQL application data transfer."""
import argparse
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import MetaData, Uuid, create_engine, func, select
from sqlalchemy.engine import make_url

HEAD = "20260827_0009"
EXCLUDED = {"alembic_version", "user_sessions"}
SEEDED = {"expense_categories"}
REQUIRED_TABLES = {
    "users", "user_sessions", "categories", "products", "sales", "sale_items",
    "sale_returns", "sale_return_items", "inventory_movements", "suppliers",
    "purchase_orders", "purchase_order_items", "expense_categories", "expenses", "audit_events",
}
DEFAULT_EXPENSE_CATEGORIES = {"Rent", "Utilities", "Salaries/Wages", "Transportation", "Supplies", "Maintenance", "Marketing", "Communication", "Miscellaneous"}


class TransferError(RuntimeError):
    pass


def abort(message: str) -> None:
    raise TransferError(message)


def ordered_tables(metadata: MetaData):
    return [table for table in metadata.sorted_tables if table.name not in EXCLUDED]


def convert_row_for_target(row, target_table) -> dict:
    """Coerce reflected SQLite UUID strings for native PostgreSQL UUID binds."""
    converted = dict(row)
    for column in target_table.columns:
        value = converted.get(column.name)
        if value is not None and isinstance(column.type, Uuid) and not isinstance(value, uuid.UUID):
            converted[column.name] = uuid.UUID(str(value))
    return converted


def validate_source_file(source_url: str) -> None:
    url = make_url(source_url)
    if url.drivername != "sqlite" and not url.drivername.startswith("sqlite+"):
        abort("source must be SQLite")
    database = url.database
    if database and database != ":memory:" and not Path(database).expanduser().is_file():
        abort("source SQLite database file does not exist")


def validate_revision(connection, metadata: MetaData, label: str) -> None:
    if "alembic_version" not in metadata.tables:
        abort(f"{label} is missing alembic_version")
    revision = connection.scalar(select(metadata.tables["alembic_version"].c.version_num))
    if revision != HEAD:
        abort(f"{label} schema is not at required Alembic head {HEAD}")


def transfer_database(source_url: str, target_url: str, *, dry_run: bool = False) -> dict[str, int]:
    validate_source_file(source_url)
    if target_url.startswith("postgres://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgres://")
    elif target_url.startswith("postgresql://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgresql://")
    if not target_url.startswith("postgresql+psycopg://"):
        abort("target must be PostgreSQL")

    source, target = create_engine(source_url), create_engine(target_url, pool_pre_ping=True)
    try:
        source_meta, target_meta = MetaData(), MetaData()
        source_meta.reflect(bind=source)
        target_meta.reflect(bind=target)
        source_names, target_names = set(source_meta.tables), set(target_meta.tables)
        if not REQUIRED_TABLES <= source_names:
            abort(f"source is missing required application tables: {', '.join(sorted(REQUIRED_TABLES - source_names))}")
        if not REQUIRED_TABLES <= target_names:
            abort(f"target is missing required application tables: {', '.join(sorted(REQUIRED_TABLES - target_names))}")
        source_application = source_names - {"alembic_version"}
        target_application = target_names - {"alembic_version"}
        if source_application != target_application:
            abort("source and target application table sets are incompatible")

        with source.connect() as connection:
            validate_revision(connection, source_meta, "source")
        with target.connect() as connection:
            validate_revision(connection, target_meta, "target")
            populated = [table.name for table in ordered_tables(target_meta) if table.name not in SEEDED
                         and connection.scalar(select(func.count()).select_from(table))]
            if populated:
                abort("target contains application data; refusing to overwrite it")
            category_table = target_meta.tables["expense_categories"]
            if set(connection.scalars(select(category_table.c.name))) != DEFAULT_EXPENSE_CATEGORIES:
                abort("target expense categories are not the untouched migration seed set")

        copied_tables = ordered_tables(target_meta)
        source_counts: dict[str, int] = {}
        with source.connect() as connection:
            for table in copied_tables:
                source_counts[table.name] = connection.scalar(
                    select(func.count()).select_from(source_meta.tables[table.name])) or 0
        if dry_run:
            for name, count in source_counts.items():
                print(f"{name}: source {count} / target validation only")
            print("Dry run complete; no data was changed and active sessions will not be copied.")
            return source_counts

        # Copy and verification share one transaction. Any exception, including a
        # count mismatch, rolls back the rows and restores migration seeds.
        with source.connect() as source_connection, target.begin() as target_connection:
            for target_table in copied_tables:
                if target_table.name in SEEDED:
                    target_connection.execute(target_table.delete())
                rows = list(source_connection.execute(
                    select(source_meta.tables[target_table.name])).mappings())
                if rows:
                    target_connection.execute(target_table.insert(), [convert_row_for_target(row, target_table) for row in rows])
            for table in copied_tables:
                target_count = target_connection.scalar(select(func.count()).select_from(table)) or 0
                source_count = source_counts[table.name]
                print(f"{table.name}: source {source_count} / target {target_count}")
                if source_count != target_count:
                    abort(f"post-transfer count verification failed for {table.name}")
        print("Transfer complete. User sessions were intentionally excluded; all users must log in again.")
        return source_counts
    finally:
        source.dispose()
        target.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate and display counts without copying")
    args = parser.parse_args()
    source_url, target_url = os.getenv("SOURCE_DATABASE_URL"), os.getenv("TARGET_DATABASE_URL")
    if not source_url or not target_url:
        print("Migration aborted: SOURCE_DATABASE_URL and TARGET_DATABASE_URL are required", file=sys.stderr)
        raise SystemExit(2)
    try:
        transfer_database(source_url, target_url, dry_run=args.dry_run)
    except TransferError as error:
        print(f"Migration aborted: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
