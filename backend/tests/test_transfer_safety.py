from pathlib import Path

import pytest

from app.scripts.migrate_database import transfer


def test_transfer_refuses_missing_sqlite_file(tmp_path: Path):
    missing = tmp_path / "typo.db"
    with pytest.raises(RuntimeError, match="existing SQLite"):
        transfer(f"sqlite:///{missing}", "postgresql+psycopg://user:pass@localhost/test", dry_run=True)
    assert not missing.exists()


def test_transfer_refuses_non_postgres_target(tmp_path: Path):
    source = tmp_path / "source.db"
    source.touch()
    with pytest.raises(RuntimeError, match="target must be PostgreSQL"):
        transfer(f"sqlite:///{source}", "sqlite:///:memory:", dry_run=True)
