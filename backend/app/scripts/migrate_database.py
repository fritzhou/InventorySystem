"""One-time, transactional SQLite-to-PostgreSQL transfer utility."""
import argparse
import os
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import UUID

from sqlalchemy import MetaData, create_engine, func, inspect, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

HEAD = "20260827_0009"
SKIP = {"alembic_version", "user_sessions"}
REQUIRED = {"users", "categories", "products", "sales", "sale_items", "inventory_movements",
            "sale_returns", "sale_return_items", "suppliers", "purchase_orders", "purchase_order_items",
            "expense_categories", "expenses", "audit_events"}
SEED_NAMES = {"Rent", "Utilities", "Salaries/Wages", "Transportation", "Supplies", "Maintenance",
              "Marketing", "Communication", "Miscellaneous"}


def _sqlite_path(url: str) -> Path | None:
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        return Path(unquote(urlparse(url).path))
    return None


def _revision(connection) -> str:
    if "alembic_version" not in inspect(connection).get_table_names():
        raise RuntimeError("database has no Alembic version table")
    return connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()


def transfer(source_url: str, target_url: str, dry_run: bool = False) -> dict[str, int]:
    path = _sqlite_path(source_url)
    if not source_url.startswith("sqlite:") or (path is not None and not path.is_file()):
        raise RuntimeError("source must be an existing SQLite database")
    if target_url.startswith("postgres://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgres://")
    elif target_url.startswith("postgresql://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgresql://")
    if not target_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("target must be PostgreSQL")
    source_engine, target_engine = create_engine(source_url), create_engine(target_url)
    with source_engine.connect() as source, target_engine.connect() as target:
        if _revision(source) != HEAD or _revision(target) != HEAD:
            raise RuntimeError(f"source and target must both be at revision {HEAD}")
        source_names = set(inspect(source).get_table_names())
        if not REQUIRED <= source_names:
            raise RuntimeError("source application schema is incomplete")
        source_meta, target_meta = MetaData(), MetaData()
        source_meta.reflect(bind=source)
        target_meta.reflect(bind=target)
        tables = [t for t in target_meta.sorted_tables if t.name in source_names and t.name not in SKIP]
        for table in tables:
            count = target.execute(select(func.count()).select_from(table)).scalar_one()
            if table.name == "expense_categories" and count:
                names = set(target.execute(select(table.c.name)).scalars())
                if not names <= SEED_NAMES:
                    raise RuntimeError("target contains established expense categories")
            elif count:
                raise RuntimeError(f"target contains data in {table.name}")
        counts: dict[str, int] = {}
        if dry_run:
            return {t.name: source.execute(select(func.count()).select_from(source_meta.tables[t.name])).scalar_one() for t in tables}
        # End the implicit read-only validation transaction before the single
        # all-or-nothing transfer transaction begins.
        target.rollback()
        transaction = target.begin()
        try:
            expense = target_meta.tables.get("expense_categories")
            if expense is not None:
                target.execute(expense.delete())
            for table in tables:
                src = source_meta.tables[table.name]
                rows = [dict(row) for row in source.execute(select(src)).mappings()]
                for row in rows:
                    for column in table.columns:
                        if isinstance(column.type, PG_UUID) and row.get(column.name) is not None and not isinstance(row[column.name], UUID):
                            row[column.name] = UUID(str(row[column.name]))
                if rows:
                    target.execute(table.insert(), rows)
                actual = target.execute(select(func.count()).select_from(table)).scalar_one()
                if actual != len(rows):
                    raise RuntimeError(f"count verification failed for {table.name}")
                counts[table.name] = actual
            transaction.commit()
            return counts
        except Exception:
            transaction.rollback()
            raise
        finally:
            source_engine.dispose(); target_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source, target = os.getenv("SOURCE_DATABASE_URL"), os.getenv("TARGET_DATABASE_URL")
    if not source or not target:
        raise SystemExit("SOURCE_DATABASE_URL and TARGET_DATABASE_URL are required")
    counts = transfer(source, target, args.dry_run)
    print(("Validated" if args.dry_run else "Transferred") + f" {sum(counts.values())} rows across {len(counts)} tables")


if __name__ == "__main__":
    main()
