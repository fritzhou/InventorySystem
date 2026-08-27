"""One-time, transactional SQLite-to-PostgreSQL application data transfer."""
import argparse
import os
import sys

from sqlalchemy import MetaData, create_engine, func, inspect, select

HEAD = "20260827_0009"
EXCLUDED = {"alembic_version", "user_sessions"}
SEEDED = {"expense_categories"}
DEFAULT_EXPENSE_CATEGORIES = {"Rent", "Utilities", "Salaries/Wages", "Transportation", "Supplies", "Maintenance", "Marketing", "Communication", "Miscellaneous"}


def fail(message: str) -> None:
    print(f"Migration aborted: {message}", file=sys.stderr)
    raise SystemExit(2)


def ordered_tables(metadata: MetaData):
    return [table for table in metadata.sorted_tables if table.name not in EXCLUDED]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate and display counts without copying")
    args = parser.parse_args()
    source_url, target_url = os.getenv("SOURCE_DATABASE_URL"), os.getenv("TARGET_DATABASE_URL")
    if not source_url or not target_url:
        fail("SOURCE_DATABASE_URL and TARGET_DATABASE_URL are required")
    if not source_url.startswith("sqlite"):
        fail("source must be SQLite")
    if target_url.startswith("postgres://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgres://")
    elif target_url.startswith("postgresql://"):
        target_url = "postgresql+psycopg://" + target_url.removeprefix("postgresql://")
    if not target_url.startswith("postgresql+psycopg://"):
        fail("target must be PostgreSQL")

    source, target = create_engine(source_url), create_engine(target_url, pool_pre_ping=True)
    source_meta, target_meta = MetaData(), MetaData()
    source_meta.reflect(bind=source)
    target_meta.reflect(bind=target)
    if not target_meta.tables or "alembic_version" not in target_meta.tables:
        fail("target schema is missing; run alembic upgrade head first")
    with target.connect() as connection:
        revision = connection.scalar(select(target_meta.tables["alembic_version"].c.version_num))
        if revision != HEAD:
            fail(f"target schema is not at required Alembic head {HEAD}")

    common = [table for table in ordered_tables(target_meta) if table.name in source_meta.tables]
    with target.connect() as connection:
        populated = [table.name for table in common if table.name not in SEEDED and connection.scalar(select(func.count()).select_from(table))]
        if populated:
            fail("target contains application data; refusing to overwrite it")
        if "expense_categories" in target_meta.tables:
            category_table = target_meta.tables["expense_categories"]
            seeded_names = set(connection.scalars(select(category_table.c.name)))
            if seeded_names != DEFAULT_EXPENSE_CATEGORIES:
                fail("target expense categories are not the untouched migration seed set")

    source_counts = {}
    with source.connect() as connection:
        for target_table in common:
            source_counts[target_table.name] = connection.scalar(select(func.count()).select_from(source_meta.tables[target_table.name])) or 0
    if args.dry_run:
        for name, count in source_counts.items():
            print(f"{name}: source {count} / target validation only")
        print("Dry run complete; no data was changed and active sessions will not be copied.")
        return

    # A single transaction ensures that a failure leaves the freshly migrated target unchanged.
    with source.connect() as source_connection, target.begin() as target_connection:
        for target_table in common:
            if target_table.name in SEEDED:
                target_connection.execute(target_table.delete())
            source_table = source_meta.tables[target_table.name]
            rows = [dict(row) for row in source_connection.execute(select(source_table)).mappings()]
            if rows:
                target_connection.execute(target_table.insert(), rows)

    failed = False
    with target.connect() as connection:
        for table in common:
            target_count = connection.scalar(select(func.count()).select_from(table)) or 0
            source_count = source_counts[table.name]
            print(f"{table.name}: source {source_count} / target {target_count}")
            failed |= source_count != target_count
    if failed:
        fail("post-transfer count verification failed")
    print("Transfer complete. User sessions were intentionally excluded; all users must log in again.")


if __name__ == "__main__":
    main()
